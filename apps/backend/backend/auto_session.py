"""Server-side headless auto-session controller (Key Capability #11, Layer-1).

One ``POST /api/auto-sessions`` call starts a fully automated
generate → backtest(+walk-forward) → insights → iterate loop that runs
entirely server-side. It:

* reuses the existing :class:`backend.pipeline.BacktestPipeline` (no
  re-implementation of compile/codegen/sandbox/fetch/backtest, no sandbox
  or engine bypass);
* writes the SAME session/iteration/activity artifacts a manual run
  produces via :mod:`backend.session_store` (no parallel store, no schema
  fork) — a headless run is indistinguishable in the UI from a manual one;
* persists a small ``autoRun`` status block into ``session.json`` after
  every iteration and state transition so it survives a worker restart and
  a browser reload (durable file store only);
* honours a hard budget (``max_iterations`` always defaulted/clamped, plus
  an optional wall-clock cap) so the loop is provably bounded — it never
  takes "one more round" past the cap;
* marks ``bestIterationId`` by the robust objective
  (:mod:`backend.robust_objective`) — walk-forward, WFE-gated,
  drawdown/over-leverage-penalised — never by raw return;
* acquires the existing one-backtest-per-worker semaphore and never blocks
  the API event loop;
* plumbs the existing :class:`~backend.pipeline.CancellationToken` so the
  loop is cooperatively stoppable (the public stop endpoint is J-11/iter-2;
  only the token + a ``stopped``-capable state machine land here).

Request/response DTOs live here (Pydantic models) — the frozen
``shared/contracts.py`` is NOT touched. API keys / secrets are never
written into the activity log or any session artifact.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from backend import session_store
from backend.pipeline import CancellationToken, PipelineError
from backend.robust_objective import RobustInputs, robust_score, select_best, targets_met
from shared.model_catalog import DEFAULT_MODEL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auto-sessions", tags=["Auto Session"])

# --- Hard budget knobs (never unbounded) -------------------------------------
DEFAULT_MAX_ITERATIONS = 3
# Absolute ceiling: even a huge supplied max_iterations is clamped so an
# unbounded loop is impossible. (Full AI-token/USD cost accounting is J-13.)
HARD_MAX_ITERATIONS = 50

# Binance taker fee (matches EXCHANGE_CONFIGS['binance'] on the frontend and
# the manual-run default in api.py).
_COMMISSION = 0.00075
# Small walk-forward windows so even a short tiny-budget range can yield a
# window for the robust objective; WF is reused from the pipeline (no fork).
_WFV_IS_MONTHS = 2
_WFV_OOS_MONTHS = 1


# =============================================================================
# Request / Response DTOs  (NOT added to the frozen shared/contracts.py)
# =============================================================================

class AutoSessionTargets(BaseModel):
    """Robust stop targets. All optional; every supplied one must be met for
    a ``criteria-met`` stop."""

    min_wfe: Optional[float] = None
    min_trades: Optional[int] = None
    min_sharpe: Optional[float] = None
    min_return: Optional[float] = None


class AutoSessionBudget(BaseModel):
    """Hard budget. ``max_iterations`` is always defaulted/clamped so the
    loop is bounded; ``max_wall_clock_seconds`` is an optional extra cap."""

    max_iterations: Optional[int] = None
    max_wall_clock_seconds: Optional[float] = None


class AutoSessionRequest(BaseModel):
    """Pinned-config request. Every search-space field is optional in the
    schema (open-universe is J-12); this iteration only supports the pinned
    path, so a missing pinned dimension is rejected with a clear 4xx."""

    natural_language: str
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 10000.0
    model: str = DEFAULT_MODEL
    targets: AutoSessionTargets = Field(default_factory=AutoSessionTargets)
    budget: AutoSessionBudget = Field(default_factory=AutoSessionBudget)


class AutoSessionResponse(BaseModel):
    sessionId: str
    status: str


# =============================================================================
# Helpers
# =============================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(obj: Any) -> Any:
    """Recursively replace inf/nan floats with JSON-valid sentinels.

    ``json.dumps`` would otherwise emit ``NaN``/``Infinity`` literals that
    the browser's ``JSON.parse`` rejects. Mirrors api.py ``_safe_float``.
    """
    if isinstance(obj, float):
        if math.isinf(obj):
            return 9999.99 if obj > 0 else -9999.99
        if math.isnan(obj):
            return 0.0
        return obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _parse_date(value: str, *, end: bool) -> datetime:
    """Parse a ``YYYY-MM-DD`` string the same way api.py does for manual runs."""
    d = datetime.strptime(value, "%Y-%m-%d")
    t = datetime.max.time() if end else datetime.min.time()
    return datetime.combine(d.date(), t).replace(tzinfo=timezone.utc)


def _activity(entry_type: str, content: str, iteration_id: str,
              detail: Optional[str] = None) -> dict:
    """Build one ActivityEntry matching the frontend ActivityEntry shape."""
    entry = {
        "id": str(uuid.uuid4()),
        "type": entry_type,
        "timestamp": _now_iso(),
        "content": content,
        "status": "done",
        "iterationId": iteration_id,
    }
    if detail is not None:
        entry["detail"] = detail
    return entry


def _get_pipeline():
    """Lazily fetch the shared pipeline singleton.

    Imported lazily (not at module load) to avoid a circular import:
    ``api.py`` imports this module's router at import time. Tests
    monkeypatch this function to inject a deterministic fake pipeline.
    """
    from backend.api import get_pipeline
    return get_pipeline()


def _resolve_budget(budget: AutoSessionBudget) -> tuple[int, Optional[float]]:
    """Clamp the budget so the loop can never be unbounded.

    ``max_iterations`` absent / <= 0 -> safe small default; any value is
    clamped to HARD_MAX_ITERATIONS. ``max_wall_clock_seconds`` <= 0 is
    treated as unset (the iteration cap still bounds the run).
    """
    requested = budget.max_iterations
    if requested is None or requested <= 0:
        max_iter = DEFAULT_MAX_ITERATIONS
    else:
        max_iter = min(int(requested), HARD_MAX_ITERATIONS)

    wall = budget.max_wall_clock_seconds
    if wall is not None and wall <= 0:
        wall = None
    return max_iter, wall


def _backtest_params(req: AutoSessionRequest) -> dict:
    """The BacktestParams-shaped dict stored in session.json + each node so
    the UI config bar and detail pane render exactly like a manual run."""
    return {
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "initial_capital": req.initial_capital,
        "exchange": "binance",
        "allow_short": False,
        "leverage": 1,
    }


def _update_autorun_sync(session_id: str, **changes: Any) -> dict:
    """Synchronous read-update-write of the ``autoRun`` block in
    session.json. Runs in a worker thread (see :func:`_update_autorun`) so
    the blocking file I/O never executes on the API event-loop thread.

    write_session_meta merges at the TOP level only, so we read the current
    autoRun sub-dict, merge field changes, and write it back — keeping the
    status durable and surviving a restart/reload. Always refreshes
    ``updatedAt``.
    """
    meta = session_store.read_session_meta(session_id) or {}
    auto = dict(meta.get("autoRun") or {})
    auto.update(changes)
    auto["updatedAt"] = _now_iso()
    session_store.write_session_meta(session_id, {"autoRun": auto})
    return auto


async def _update_autorun(session_id: str, **changes: Any) -> dict:
    """Offload the durable ``autoRun`` read-update-write to a worker thread
    (``asyncio.to_thread``) so the synchronous session.json I/O never blocks
    the API event loop — the same pattern the manual ``session_routes`` path
    uses for every store mutation. The loop awaits these sequentially, so it
    remains the single ``autoRun`` writer (durability semantics unchanged —
    still a real file write, just off the event-loop thread)."""
    return await asyncio.to_thread(_update_autorun_sync, session_id, **changes)


def _serialize_artifacts(
    result: Any, rating: Any, wf: Any
) -> tuple[dict, Optional[dict], Optional[dict]]:
    """CPU-bound projection of the contract objects to JSON-safe dicts.

    ``jsonable_encoder`` over a large ``BacktestResult`` /
    ``WalkForwardResult`` plus the recursive ``_json_safe`` walk is hundreds
    of ms–seconds for a real run; it MUST run in a worker thread
    (``asyncio.to_thread``), never on the event-loop thread (anti-goal: the
    background job must not block the API event loop).
    """
    result_json = _json_safe(jsonable_encoder(result))
    rating_json = _json_safe(jsonable_encoder(rating)) if rating else None
    wf_json = _json_safe(jsonable_encoder(wf)) if wf else None
    return result_json, rating_json, wf_json


# =============================================================================
# Core loop  (directly unit-testable: pass a fake pipeline + Semaphore + token)
# =============================================================================

async def run_auto_session(
    session_id: str,
    req: AutoSessionRequest,
    *,
    pipeline: Any,
    semaphore: asyncio.Semaphore,
    cancel_token: CancellationToken,
) -> dict:
    """Run the server-side iterate loop to a terminal state.

    Returns the final ``autoRun`` status dict. Never raises out — a failure
    inside one iteration is recorded and the loop still reaches a terminal
    state (it never hangs).
    """
    max_iter, max_wall = _resolve_budget(req.budget)
    targets = req.targets.model_dump(exclude_none=True)
    started = time.monotonic()

    start_dt = _parse_date(req.start_date, end=False)
    end_dt = _parse_date(req.end_date, end=True)

    # (id, RobustInputs) for every COMPLETED iteration — the robust selector
    # picks the best from this; raw return is never used to choose.
    completed: list[tuple[str, RobustInputs]] = []
    best_id: Optional[str] = None
    stop_reason: Optional[str] = None

    prev_script_code: Optional[str] = None
    prev_summary: Optional[str] = None
    prev_suggestion_titles: list[str] = []
    next_prompt = req.natural_language

    # The loop is the durable-status owner: ensure a coherent autoRun block
    # exists even when invoked directly (not via the endpoint) or resumed
    # after a worker restart. startedAt is preserved if already set.
    _meta = await asyncio.to_thread(session_store.read_session_meta, session_id)
    _existing = (_meta or {}).get("autoRun") or {}
    await _update_autorun(session_id, status="running", currentIteration=0,
                          maxIterations=max_iter, stopReason=None,
                          bestIterationId=_existing.get("bestIterationId"),
                          startedAt=_existing.get("startedAt") or _now_iso())

    iteration_index = 0
    for i in range(1, max_iter + 1):
        # --- Budget / cancel checks BEFORE doing any work: never start a
        # round that would exceed the cap ("no one more round"). ---
        if cancel_token.is_cancelled:
            stop_reason = None  # cooperative stop (J-11 plumbing); not budget
            break
        if max_wall is not None and (time.monotonic() - started) >= max_wall:
            stop_reason = "budget-exhausted"
            break

        iteration_index = i
        iter_id = str(uuid.uuid4())
        await _update_autorun(session_id, status="running", currentIteration=i)

        try:
            gen = await pipeline.generate_strategy(
                natural_language=next_prompt,
                model=req.model,
                previous_script_code=prev_script_code,
                symbol=req.symbol,
                timeframe=req.timeframe,
                start_date=req.start_date,
                end_date=req.end_date,
            )

            if getattr(gen, "validation_errors", None) and not gen.script_code:
                await _record_failed(session_id, i, iter_id, next_prompt, req,
                                     "; ".join(gen.validation_errors))
                continue

            async with semaphore:
                cancel_token.check()
                result, errors, rating, _timings, wf = await pipeline.execute_backtest(
                    script_id=gen.script_id,
                    symbol=req.symbol,
                    timeframe=req.timeframe,
                    start_date=start_dt,
                    end_date=end_dt,
                    initial_capital=req.initial_capital,
                    commission=_COMMISSION,
                    script_code=gen.script_code,
                    strategy_name=gen.strategy_name,
                    strategy_description=gen.strategy_description,
                    cancel_token=cancel_token,
                    wfv_enabled=True,
                    wfv_is_months=_WFV_IS_MONTHS,
                    wfv_oos_months=_WFV_OOS_MONTHS,
                )

            if result is None:
                await _record_failed(session_id, i, iter_id, next_prompt, req,
                                     "; ".join(errors) if errors else "Backtest failed")
                continue

            # CPU-bound encoding offloaded — never on the event-loop thread.
            result_json, rating_json, wf_json = await asyncio.to_thread(
                _serialize_artifacts, result, rating, wf
            )

            # Insights — best-effort; a failure must not abort the loop.
            summary, suggestions = "", []
            try:
                summary, suggestions, _ierr = await pipeline.generate_insights(
                    backtest_result=result_json,
                    strategy_name=gen.strategy_name,
                    strategy_description=gen.strategy_description,
                    script_code=gen.script_code,
                    natural_language_prompt=next_prompt,
                    model=req.model,
                    symbol=req.symbol,
                    timeframe=req.timeframe,
                    start_date=req.start_date,
                    end_date=req.end_date,
                    initial_capital=req.initial_capital,
                    previous_summary=prev_summary,
                    previous_suggestions=prev_suggestion_titles or None,
                    walk_forward_result=wf_json,
                )
            except Exception as ins_err:  # noqa: BLE001 - best-effort
                logger.warning("auto-session insights failed (continuing): %s", ins_err)

            insights = {"summary": summary, "suggestions": suggestions}

            inp = _robust_inputs(result, wf, leverage=1.0)
            score = robust_score(inp)
            completed.append((iter_id, inp))

            node = _build_node(
                iter_id=iter_id,
                prompt=next_prompt,
                script_code=gen.script_code,
                script_id=gen.script_id,
                strategy_name=gen.strategy_name,
                model_used=getattr(gen, "model_used", req.model) or req.model,
                result=result,
                result_json=result_json,
                rating_json=rating_json,
                wf_json=wf_json,
                insights=insights,
                req=req,
                robust=score,
            )
            # All store I/O offloaded off the event-loop thread (same as the
            # manual session_routes path) so a continuous headless run keeps
            # GET /api/sessions and the J-08 poll responsive.
            await asyncio.to_thread(
                session_store.write_iteration, session_id, i, node
            )

            await asyncio.to_thread(
                session_store.append_activity_entries, session_id, [
                    _activity("auto-run", f"Automated iteration {i}/{max_iter}", iter_id),
                    _activity(
                        "complete",
                        f"Backtest complete — return {result.total_return * 100:.2f}%, "
                        f"{result.num_trades} trades, robust {score:.3f}",
                        iter_id,
                    ),
                ]
            )
            if summary:
                await asyncio.to_thread(
                    session_store.append_activity_entries, session_id, [
                        _activity("insights", summary, iter_id),
                    ]
                )

            # The best-so-far is always recomputed by the robust objective
            # (NOT raw return), so a higher-return-but-WFE-failing /
            # over-leveraged candidate is never marked best.
            best_id = select_best(completed)
            await _update_autorun(session_id, status="running", currentIteration=i,
                                  bestIterationId=best_id)
            # Defense in depth: yield a clean loop turn before the next
            # round so back-to-back iterations never starve pending requests.
            await asyncio.sleep(0)

            prev_script_code = gen.script_code
            prev_summary = summary or prev_summary
            prev_suggestion_titles = [s.get("title", "") for s in suggestions if s.get("title")]
            if suggestions and suggestions[0].get("prompt"):
                next_prompt = suggestions[0]["prompt"]

            if targets and targets_met(inp, targets):
                stop_reason = "criteria-met"
                break

        except PipelineError:
            # Cooperative cancellation raised inside the pipeline.
            stop_reason = None
            cancel_token.cancel()
            break
        except Exception as exc:  # noqa: BLE001 - one bad iter must not hang the loop
            logger.warning("auto-session iteration %d failed (continuing): %s", i, exc)
            await _record_failed(session_id, i, iter_id, next_prompt, req, str(exc))
            continue

    # --- Terminal state ------------------------------------------------------
    if cancel_token.is_cancelled and stop_reason is None:
        final_status = "stopped"
    else:
        if stop_reason is None:
            # Loop fell out of the for-range: the iteration cap was reached.
            stop_reason = "budget-exhausted"
        final_status = "complete"

    if stop_reason == "criteria-met":
        best_id = select_best(completed, targets=targets, require_targets=True)
    else:
        best_id = select_best(completed) if completed else best_id

    final = await _update_autorun(
        session_id,
        status=final_status,
        stopReason=stop_reason,
        currentIteration=iteration_index,
        maxIterations=max_iter,
        bestIterationId=best_id,
    )
    return final


def _robust_inputs(result: Any, wf: Any, *, leverage: float) -> RobustInputs:
    """Project a BacktestResult (+ optional WalkForwardResult) onto the
    robust objective's inputs."""
    return RobustInputs(
        total_return=float(result.total_return),
        sharpe_ratio=float(result.sharpe_ratio),
        max_drawdown=float(result.max_drawdown),
        num_trades=int(result.num_trades),
        leverage=leverage,
        wfe=float(wf.wfe) if wf is not None else None,
        oos_return=float(wf.combined_oos_return) if wf is not None else None,
        oos_sharpe=float(wf.combined_oos_sharpe) if wf is not None else None,
        num_windows=int(wf.num_windows) if wf is not None else 0,
    )


def _build_node(*, iter_id: str, prompt: str, script_code: str, script_id: str,
                strategy_name: str, model_used: str, result: Any,
                result_json: dict, rating_json: Optional[dict],
                wf_json: Optional[dict], insights: dict,
                req: AutoSessionRequest, robust: float) -> dict:
    """Build the node_dict in the EXACT shape write_iteration expects for a
    manual run (the canonical key set), so a headless run is
    indistinguishable in the UI from a manual one. The top-level summary
    fields populate the lightweight list path (cards/tree)."""
    return {
        "id": iter_id,
        "prompt": prompt,
        "scriptCode": script_code,
        "scriptId": script_id,
        "strategyName": strategy_name,
        "status": "complete",
        "result": result_json,
        "rating": rating_json,
        "insights": insights,
        "totalReturn": float(result.total_return),
        "winRate": float(result.win_rate),
        "numTrades": int(result.num_trades),
        "sharpe": float(result.sharpe_ratio),
        "maxDrawdown": float(result.max_drawdown),
        "robustScore": robust,
        "modelUsed": model_used,
        "params": _backtest_params(req),
        "timestamp": _now_iso(),
        "parentId": None,
        "walkForwardResult": wf_json,
        "walkForwardStatus": "complete" if wf_json else "idle",
    }


async def _record_failed(session_id: str, index: int, iter_id: str, prompt: str,
                         req: AutoSessionRequest, error: str) -> None:
    """Persist a failed iteration and an error activity entry. The loop
    continues (it counts toward the budget) and still reaches a terminal
    state — it never hangs on a single bad iteration. Store writes are
    offloaded (``asyncio.to_thread``) so they never block the event loop."""
    node = {
        "id": iter_id,
        "prompt": prompt,
        "scriptCode": "",
        "scriptId": "",
        "strategyName": "",
        "status": "error",
        "result": None,
        "rating": None,
        "insights": None,
        "totalReturn": 0.0,
        "winRate": 0.0,
        "numTrades": 0,
        "sharpe": 0.0,
        "maxDrawdown": 0.0,
        "error": error,
        "params": _backtest_params(req),
        "timestamp": _now_iso(),
        "parentId": None,
    }
    await asyncio.to_thread(session_store.write_iteration, session_id, index, node)
    await asyncio.to_thread(session_store.append_activity_entries, session_id, [
        _activity("error", f"Iteration {index} failed: {error}", iter_id),
    ])


# =============================================================================
# Endpoint
# =============================================================================

@router.post("", response_model=AutoSessionResponse)
async def create_auto_session(req: AutoSessionRequest, request: Request):
    """Start a headless automated strategy-search session.

    Creates the session in the existing file store synchronously (so the
    sessionId is listed by ``GET /api/sessions`` immediately, with no
    browser interaction), then launches the server-side loop as a detached
    asyncio task and returns 200 right away.
    """
    # Pinned-config validation. Open-universe (omitting symbol/timeframe) is
    # J-12 / out of scope this iteration -> reject clearly with a 4xx
    # (Pydantic already 422s a missing natural_language; never a 500).
    missing = [
        name for name, value in (
            ("symbol", req.symbol),
            ("timeframe", req.timeframe),
            ("start_date", req.start_date),
            ("end_date", req.end_date),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Missing required pinned config field(s): {', '.join(missing)}. "
                "Open-universe search (omitting symbol/timeframe) is not yet "
                "supported."
            ),
        )
    try:
        _parse_date(req.start_date, end=False)
        _parse_date(req.end_date, end=True)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="start_date and end_date must be YYYY-MM-DD.",
        )

    max_iter, _wall = _resolve_budget(req.budget)
    session_id = str(uuid.uuid4())
    now_ms = int(time.time() * 1000)
    nl = req.natural_language.strip()
    name = f"Auto: {nl[:40]}" + ("…" if len(nl) > 40 else "")

    # Create the session in the EXISTING file store BEFORE returning, so it
    # appears immediately in GET /api/sessions (derive_session_tabs keys off
    # session.json) and is openable. No parallel store / schema fork.
    await asyncio.to_thread(session_store.write_session_meta, session_id, {
        "name": name,
        "lastAccessedAt": now_ms,
        "backtestParams": _backtest_params(req),
        "autoRun": {
            "status": "running",
            "stopReason": None,
            "currentIteration": 0,
            "maxIterations": max_iter,
            "bestIterationId": None,
            "startedAt": _now_iso(),
            "updatedAt": _now_iso(),
        },
    })

    # One-backtest-per-worker semaphore (shared with manual runs). Lazily
    # create it if startup has not run (e.g. bare TestClient) so the
    # one-at-a-time guarantee still holds within the process.
    app = request.app
    if not hasattr(app.state, "backtest_semaphore"):
        app.state.backtest_semaphore = asyncio.Semaphore(1)
    semaphore: asyncio.Semaphore = app.state.backtest_semaphore

    pipeline = _get_pipeline()
    cancel_token = CancellationToken()

    async def _runner() -> None:
        try:
            await run_auto_session(
                session_id, req,
                pipeline=pipeline,
                semaphore=semaphore,
                cancel_token=cancel_token,
            )
        except Exception as exc:  # noqa: BLE001 - background task must not crash silently
            logger.exception("auto-session %s crashed: %s", session_id, exc)
            try:
                await _update_autorun(session_id, status="stopped", stopReason=None)
            except Exception:  # noqa: BLE001
                pass

    # Detached background task — same pattern as api.py's
    # asyncio.create_task(run()). Does NOT block the event loop; GET
    # /api/sessions and other requests stay responsive while it runs.
    asyncio.create_task(_runner())

    return AutoSessionResponse(sessionId=session_id, status="running")
