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
import importlib
import logging
import math
import multiprocessing
import queue
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, NamedTuple, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from backend import session_store
from backend.cost_tracker import DEFAULT_MAX_CONFIGS, CostTracker
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

# --- Bounded seed universe (J-12) -------------------------------------------
# A small, hard-coded constant set of (symbol, timeframe) candidates — a few
# liquid pairs × a couple of timeframes. Open-universe exploration draws ONLY
# from this set (anti-goal: MUST NOT blindly fan out across the whole exchange
# symbol list). This is deliberately NOT the 26×6 /api/symbols × /api/timeframes
# grid, NOT env-driven, and NOT a live exchange enumeration. The deterministic
# bounded enumerator below walks it in order (the history-surrogate/bandit +
# LLM planner that would prioritise within it is J-15 / OUT OF SCOPE).
_SEED_UNIVERSE: tuple[tuple[str, str], ...] = (
    ("BTC/USDT", "4h"),
    ("ETH/USDT", "4h"),
    ("SOL/USDT", "4h"),
    ("BNB/USDT", "1h"),
    ("BTC/USDT", "1h"),
    ("ETH/USDT", "1h"),
)
# Fixed deterministic short historical window used when an open-universe
# request omits start/end (tiny-budget rule): long enough for the small WF
# IS/OOS windows above to form ≥1 window, short enough that the single-file
# OHLCV Parquet cache can serve/cache it cheaply and be reused across configs.
_OPEN_UNIVERSE_START = "2023-01-01"
_OPEN_UNIVERSE_END = "2023-06-01"


# --- In-process cancellation registry (NO new infra) -------------------------
# Maps a live session_id -> its CancellationToken so the public stop endpoint
# can reach the running loop in THIS worker. It is populated in
# create_auto_session and removed on EVERY terminal path (criteria-met,
# budget-exhausted, stopped, crash). It is intentionally best-effort and
# worker-local: a stop is ALSO recorded durably in session.json so it is
# honoured even when the live token is not in the handling worker (multi-
# WEB_CONCURRENCY) or after a restart.
_CANCEL_REGISTRY: dict[str, CancellationToken] = {}


def _register_cancel(session_id: str, token: CancellationToken) -> None:
    _CANCEL_REGISTRY[session_id] = token


def _unregister_cancel(session_id: str) -> None:
    """Idempotent removal — safe to call on any terminal path and twice."""
    _CANCEL_REGISTRY.pop(session_id, None)


# =============================================================================
# CPU-bound backtest process isolation  (anti-goal: the background job MUST
# NOT block the API event loop / starve other requests)
# =============================================================================
#
# The deterministic next-bar engine runs the RestrictedPython signal bar by
# bar — pure-Python, CPU-bound, GIL-holding work. ``pipeline.execute_backtest``
# already offloads it via ``asyncio.to_thread``, but a *thread* shares this
# worker's GIL: during a CONTINUOUS headless loop that thread holds the GIL
# almost the whole run, so every OTHER ``asyncio.to_thread`` file-IO request
# (the ``GET /api/sessions`` poll, the stop endpoint's session-store read) is
# GIL-starved for tens of seconds (QA: GET /api/sessions up to 33.7 s).
#
# Fix: run the backtest in a CHILD PROCESS. The child has its OWN GIL, so the
# API worker's event loop + every file-IO thread stay responsive while a run
# is active. The existing :class:`~backend.pipeline.BacktestPipeline` is
# reused VERBATIM inside the child — no sandbox/engine bypass, ``pipeline.py``
# is NOT modified. ``multiprocessing`` is the Python stdlib (the same kind of
# in-process offload primitive as the ThreadPoolExecutor already used here) —
# NOT new external infrastructure (no Celery/Redis/DB/broker).
#
# One long-lived ``spawn`` child is reused across iterations (the pipeline is
# constructed once child-side, mirroring the parent's singleton). The
# one-backtest-per-worker semaphore already serialises submissions. Stop is
# honoured cooperatively: cancelling terminates the child and the loop's
# existing ``except PipelineError`` path maps it to terminal ``stopped``.

# Module-level "spawn" context (fork + threads + asyncio is unsafe).
_MP_CTX = multiprocessing.get_context("spawn")

# The single reusable backtest child, keyed by its target ref so a test can
# run a deterministic CPU-bound stand-in through the SAME seam the real
# pipeline uses. Worker-local; serialised by the backtest semaphore.
_BT_WORKER: Optional["_BacktestWorker"] = None

# Real production child target. Resolved & invoked INSIDE the child only.
_REAL_BACKTEST_REF = "backend.auto_session:_real_pipeline_backtest"

# Sentinel result-tuple shape (matches pipeline.execute_backtest + the two
# pre-encoded JSON projections the loop needs):
#   (result, errors, rating, timings, wf, result_json, rating_json, wf_json)

_CHILD_PIPELINE: Any = None  # child-process-local BacktestPipeline singleton


def _real_pipeline_backtest(payload: dict) -> tuple:
    """CHILD-process entry: run ONE backtest with the REAL pipeline.

    Builds (once) and reuses a child-local :class:`BacktestPipeline` — the
    exact same compile/sandbox/fetch/engine/walk-forward code a manual run
    uses (no bypass). The CPU-bound encode is done HERE too so the parent
    event-loop thread does zero heavy work for this iteration.
    """
    global _CHILD_PIPELINE
    if _CHILD_PIPELINE is None:
        from backend.pipeline import BacktestPipeline
        _CHILD_PIPELINE = BacktestPipeline()
    result, errors, rating, timings, wf = asyncio.run(
        _CHILD_PIPELINE.execute_backtest(**payload)
    )
    if result is None:
        return (None, errors, None, timings, None, None, None, None)
    result_json, rating_json, wf_json = _serialize_artifacts(result, rating, wf)
    return (result, errors, rating, timings, wf,
            result_json, rating_json, wf_json)


def _worker_main(target_ref: str, in_q: Any, out_q: Any) -> None:
    """CHILD-process loop: resolve ``target_ref`` once, then serve backtest
    payloads until the process is terminated. Never raises out — a failed
    backtest is reported as an ``("err", traceback)`` message so the parent
    never hangs waiting on the queue."""
    mod_name, _, attr = target_ref.partition(":")
    try:
        fn = getattr(importlib.import_module(mod_name), attr)
    except Exception as exc:  # noqa: BLE001 - report import failure to parent
        # Drain one request so the parent's get() returns instead of hanging.
        try:
            in_q.get()
        except Exception:  # noqa: BLE001
            pass
        out_q.put(("err", f"backtest worker import failed: {exc!r}"))
        return
    while True:
        payload = in_q.get()
        if payload is None:  # graceful shutdown sentinel
            return
        try:
            out_q.put(("ok", fn(payload)))
        except BaseException as exc:  # noqa: BLE001 - must report, never hang
            import traceback
            out_q.put(("err", f"{exc!r}\n{traceback.format_exc()}"))


class _BacktestWorker:
    """A single long-lived ``spawn`` child running one backtest at a time.

    Daemon process: it never outlives the API worker and cannot leak past a
    server restart. Reused across iterations for throughput; terminated (and
    lazily respawned) on cancellation."""

    def __init__(self, target_ref: str):
        self.target_ref = target_ref
        self._in: Any = _MP_CTX.Queue()
        self._out: Any = _MP_CTX.Queue()
        self._proc = _MP_CTX.Process(
            target=_worker_main,
            args=(target_ref, self._in, self._out),
            daemon=True,
        )
        self._proc.start()

    def is_alive(self) -> bool:
        return self._proc.is_alive()

    def submit(self, payload: dict) -> None:
        self._in.put(payload)

    def get(self, timeout: float) -> tuple:
        """Blocking queue read (raises ``queue.Empty`` on timeout). Always
        called via ``asyncio.to_thread`` so it never blocks the event loop;
        it parks on an OS pipe (GIL released) — not CPU-bound."""
        return self._out.get(timeout=timeout)

    def kill(self) -> None:
        try:
            self._proc.terminate()
        except Exception:  # noqa: BLE001 - best-effort
            pass
        try:
            self._proc.join(5)
        except Exception:  # noqa: BLE001
            pass


def _ensure_worker(target_ref: str) -> "_BacktestWorker":
    """Return a live worker for ``target_ref`` (respawn if dead / mismatched).
    Serialised by the backtest semaphore — no concurrent creation."""
    global _BT_WORKER
    w = _BT_WORKER
    if w is None or not w.is_alive() or w.target_ref != target_ref:
        if w is not None:
            w.kill()
        w = _BacktestWorker(target_ref)
        _BT_WORKER = w
    return w


def _shutdown_backtest_worker() -> None:
    """Terminate the reusable child (idempotent). Used on cancellation and by
    tests' teardown so no child lingers across the suite."""
    global _BT_WORKER
    w = _BT_WORKER
    _BT_WORKER = None
    if w is not None:
        w.kill()


async def _run_backtest_in_subprocess(
    target_ref: str, payload: dict, cancel_token: CancellationToken
) -> tuple:
    """Run ONE backtest in the child process and return the 8-tuple.

    Cooperative cancel: while waiting we poll ``cancel_token``; on cancel the
    child is terminated and ``PipelineError`` is raised so the loop's existing
    ``except PipelineError`` path drives the run to terminal ``stopped``. The
    parent only ever parks a thread-pool thread on an OS pipe for ≤0.2 s — the
    event loop and other file-IO requests stay responsive throughout."""
    worker = _ensure_worker(target_ref)
    worker.submit(payload)
    while True:
        if cancel_token.is_cancelled:
            _shutdown_backtest_worker()
            raise PipelineError("Operation cancelled")
        try:
            kind, value = await asyncio.to_thread(worker.get, 0.2)
        except queue.Empty:
            if not worker.is_alive():
                _shutdown_backtest_worker()
                raise RuntimeError("Backtest worker exited unexpectedly")
            continue
        if kind == "ok":
            return value
        _shutdown_backtest_worker()  # poisoned child — respawn next iteration
        raise RuntimeError(f"Backtest subprocess error: {value}")


def _subprocess_backtest_executor(
    target_ref: str = _REAL_BACKTEST_REF,
) -> Callable[[dict, CancellationToken], Any]:
    """Build the ``backtest_executor`` create_auto_session passes into the
    loop. A test can pass a different ``target_ref`` to drive a deterministic
    CPU-bound stand-in through the exact same process-isolation seam."""

    async def _exec(payload: dict, cancel_token: CancellationToken) -> tuple:
        return await _run_backtest_in_subprocess(target_ref, payload, cancel_token)

    return _exec


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
    loop is bounded; the others are extra caps the immutable
    :class:`~backend.cost_tracker.CostTracker` enforces (AI tokens, USD,
    max-configs, wall-clock). All are clamped to a safe finite default + an
    absolute hard ceiling — a run is never unbounded, even with no budget."""

    max_iterations: Optional[int] = None
    max_wall_clock_seconds: Optional[float] = None
    max_ai_tokens: Optional[int] = None
    max_usd: Optional[float] = None
    max_configs: Optional[int] = None


class AutoSessionRequest(BaseModel):
    """Auto-session request.

    Pinned config: supply ``symbol`` + ``timeframe`` (+ ``start_date`` /
    ``end_date``) — the loop refines one pinned strategy (J-07–J-11).
    Open-universe (J-12): omit BOTH ``symbol`` and ``timeframe`` and supply
    only ``objective`` + ``budget`` — the deterministic bounded enumerator
    explores ≥2 distinct configs from the seed universe. ``objective`` v1
    supports only ``"robust"`` (the single-robust-scalar Non-Goal);
    ``history_scope`` is accepted & persisted but its cross-run *learning*
    is J-15 / OUT OF SCOPE this iteration."""

    natural_language: str
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 10000.0
    model: str = DEFAULT_MODEL
    objective: Optional[str] = "robust"
    history_scope: Optional[str] = None
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


class _Config(NamedTuple):
    """One resolved (symbol, timeframe, date-window) the loop runs. Pinned
    runs use a single config every iteration; an open-universe run draws a
    distinct one per round from the bounded seed universe."""

    symbol: str
    timeframe: str
    start_str: str
    end_str: str
    start_dt: datetime
    end_dt: datetime


def _is_open_universe(req: AutoSessionRequest) -> bool:
    """Open-universe iff BOTH symbol and timeframe are omitted. Exactly one
    of them present is a *partial* pin — a malformed pinned request, not an
    open-universe request (the endpoint rejects it with a clear 422)."""
    return not req.symbol and not req.timeframe


def _config_plan(req: AutoSessionRequest) -> tuple[list[_Config], bool]:
    """Return ``(ordered configs, is_open)``.

    Pinned → exactly ONE config from the pinned fields (the loop refines the
    prompt across iterations, byte-for-byte the J-07–J-11 behaviour).
    Open-universe → the bounded seed universe in deterministic order, each
    with the request's date window or the fixed default short window when
    start/end are omitted (tiny-budget rule; Parquet-cache friendly).
    """
    if not _is_open_universe(req):
        s, e = req.start_date, req.end_date
        return (
            [_Config(req.symbol, req.timeframe, s, e,
                     _parse_date(s, end=False), _parse_date(e, end=True))],
            False,
        )
    s = req.start_date or _OPEN_UNIVERSE_START
    e = req.end_date or _OPEN_UNIVERSE_END
    sd, ed = _parse_date(s, end=False), _parse_date(e, end=True)
    return (
        [_Config(sym, tf, s, e, sd, ed) for sym, tf in _SEED_UNIVERSE],
        True,
    )


def _build_cost_tracker(
    req: AutoSessionRequest, max_iter: int, is_open: bool
) -> CostTracker:
    """Construct the immutable hard cost tracker for this run.

    Pinned: the config cap is pinned to ``max_iter`` so the tracker never
    terminates a pinned run before the existing ``max_iterations`` clamp
    does — pinned termination is byte-unchanged; the token/USD caps still
    apply but default high enough not to bite a normal run. Open-universe:
    the supplied/clamped ``max_configs`` bounds the distinct configs (default
    small; hard-ceilinged to the bounded seed size — never a blind fan-out).
    """
    b = req.budget
    if is_open:
        default_cfg = min(DEFAULT_MAX_CONFIGS, len(_SEED_UNIVERSE))
        hard_cfg = len(_SEED_UNIVERSE)
        max_cfg = b.max_configs
    else:
        default_cfg = hard_cfg = max_cfg = max_iter
    return CostTracker(
        max_ai_tokens=b.max_ai_tokens,
        max_usd=b.max_usd,
        max_configs=max_cfg,
        max_wall_clock_seconds=b.max_wall_clock_seconds,
        default_max_configs=default_cfg,
        hard_max_configs=hard_cfg,
    )


def _drain_usage(tracker: CostTracker, sink: list) -> None:
    """Feed the REAL captured per-call SDK usage into the cost tracker
    (monotonic). Called right after each LLM call so the next per-round
    budget check sees actual spend."""
    for u in sink:
        tracker.record_usage(
            u.get("model", ""),
            u.get("input_tokens", 0),
            u.get("output_tokens", 0),
        )
    sink.clear()


def _backtest_params(req: AutoSessionRequest, cfg: _Config) -> dict:
    """The BacktestParams-shaped dict stored in session.json + each node so
    the UI config bar and detail pane render exactly like a manual run. The
    symbol/timeframe/date window come from the resolved config (a headless
    open-universe iteration is UI-indistinguishable from a manual run)."""
    return {
        "symbol": cfg.symbol,
        "timeframe": cfg.timeframe,
        "start_date": cfg.start_str,
        "end_date": cfg.end_str,
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


async def _perform_backtest(
    *,
    pipeline: Any,
    backtest_executor: Optional[Callable[[dict, CancellationToken], Any]],
    payload: dict,
    cancel_token: CancellationToken,
) -> tuple:
    """Run ONE backtest + artifact encode, returning
    ``(result, errors, rating, wf, result_json, rating_json, wf_json)``.

    * ``backtest_executor`` set (real run): the CPU-bound pure-Python engine
      runs in a CHILD PROCESS so it never holds this worker's GIL — the event
      loop and every other ``asyncio.to_thread`` request stay responsive while
      a headless run is active (anti-goal). The child also did the JSON encode.
    * ``backtest_executor`` is ``None`` (unit tests' fake pipeline): UNCHANGED
      in-process behaviour — await the (fake) pipeline, then offload only the
      JSON encode via ``asyncio.to_thread`` exactly as before.
    """
    if backtest_executor is not None:
        (result, errors, rating, _timings, wf,
         result_json, rating_json, wf_json) = await backtest_executor(
            payload, cancel_token
        )
        return result, errors, rating, wf, result_json, rating_json, wf_json

    result, errors, rating, _timings, wf = await pipeline.execute_backtest(
        **payload, cancel_token=cancel_token
    )
    if result is None:
        return None, errors, None, None, None, None, None
    result_json, rating_json, wf_json = await asyncio.to_thread(
        _serialize_artifacts, result, rating, wf
    )
    return result, errors, rating, wf, result_json, rating_json, wf_json


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
    backtest_executor: Optional[Callable[[dict, CancellationToken], Any]] = None,
) -> dict:
    """Run the loop to a terminal state and ALWAYS clean up the in-process
    cancellation registry entry for ``session_id`` — on every terminal path
    (criteria-met / budget-exhausted / stopped) and even if the loop crashes
    (the ``finally`` runs regardless). The thin wrapper exists so the
    registry invariant holds for one obvious reason in one place.

    ``backtest_executor`` (set by :func:`create_auto_session` for the real
    run) offloads the CPU-bound backtest to a child process. Left ``None``
    (unit tests injecting a fake pipeline) the backtest runs in-process,
    exactly as before — so the existing suite's behaviour is unchanged."""
    try:
        return await _run_auto_session_impl(
            session_id, req,
            pipeline=pipeline, semaphore=semaphore, cancel_token=cancel_token,
            backtest_executor=backtest_executor,
        )
    finally:
        _unregister_cancel(session_id)


async def _run_auto_session_impl(
    session_id: str,
    req: AutoSessionRequest,
    *,
    pipeline: Any,
    semaphore: asyncio.Semaphore,
    cancel_token: CancellationToken,
    backtest_executor: Optional[Callable[[dict, CancellationToken], Any]] = None,
) -> dict:
    """Run the server-side iterate loop to a terminal state.

    Returns the final ``autoRun`` status dict. Never raises out — a failure
    inside one iteration is recorded and the loop still reaches a terminal
    state (it never hangs).
    """
    max_iter, _legacy_wall = _resolve_budget(req.budget)
    targets = req.targets.model_dump(exclude_none=True)

    configs, is_open = _config_plan(req)
    # Immutable hard cost tracker: AI-tokens / USD / max-configs / wall-clock,
    # caps fixed at construction. The per-round check below never starts a
    # config/round once any cap is reached ("no one more round past the cap").
    tracker = _build_cost_tracker(req, max_iter, is_open)

    # (id, RobustInputs) for every COMPLETED iteration (across ALL explored
    # configs for an open-universe run) — the robust selector picks the best
    # from this; raw return is never used to choose.
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
                          startedAt=_existing.get("startedAt") or _now_iso(),
                          spend=tracker.snapshot())

    iteration_index = 0
    for i in range(1, max_iter + 1):
        # --- Budget / cancel checks BEFORE doing any work: never start a
        # round/config that would exceed the cap ("no one more round"). ---
        if cancel_token.is_cancelled:
            stop_reason = None  # cooperative stop (in-process token); not budget
            break
        if tracker.would_exceed() is not None:
            # Any hard cap reached (ai-tokens / usd / max-configs / wall-clock):
            # terminal budget-exhausted, NO further iteration/config appended.
            stop_reason = "budget-exhausted"
            break
        # Durable, worker-safe cooperative stop: the public stop endpoint
        # records `autoRun.stopRequested` in session.json, so the loop honours
        # a stop even when the live in-process token is not in THIS worker
        # (multi-WEB_CONCURRENCY) or after a restart. Read off the event-loop
        # thread (same as the manual session_routes path) so this never blocks
        # the loop (B1 anti-goal). Cancel the live token too so the in-flight
        # pipeline path (which already checks the token) winds down and the
        # existing terminal logic maps this to `status="stopped"`.
        _persisted = await asyncio.to_thread(
            session_store.read_session_meta, session_id
        )
        if ((_persisted or {}).get("autoRun") or {}).get("stopRequested"):
            cancel_token.cancel()
            stop_reason = None
            break
        # Open-universe: the bounded seed universe is finite — exhausting it
        # within budget is itself a terminal (the search space is spent). The
        # max-configs cap above normally trips first; this is the backstop.
        if is_open and (i - 1) >= len(configs):
            stop_reason = "budget-exhausted"
            break

        cfg = configs[0] if not is_open else configs[i - 1]
        tracker.start_config()
        iteration_index = i
        iter_id = str(uuid.uuid4())
        await _update_autorun(session_id, status="running", currentIteration=i,
                              spend=tracker.snapshot())
        if is_open:
            # Record EVERY explored config (symbol/timeframe) so the
            # open-universe exploration is visible/auditable in the UI.
            await asyncio.to_thread(
                session_store.append_activity_entries, session_id, [
                    _activity(
                        "auto-run",
                        f"Exploring config {i}: {cfg.symbol} {cfg.timeframe}",
                        iter_id,
                    ),
                ]
            )

        # Per-config prompt: open-universe is a deterministic enumerator (no
        # cross-config refinement / planner — that is J-15 / OUT OF SCOPE);
        # the pinned path keeps its prior-suggestion refinement chain.
        gen_prompt = req.natural_language if is_open else next_prompt
        gen_prev = None if is_open else prev_script_code

        try:
            usage_sink: list = []
            gen = await pipeline.generate_strategy(
                natural_language=gen_prompt,
                model=req.model,
                previous_script_code=gen_prev,
                symbol=cfg.symbol,
                timeframe=cfg.timeframe,
                start_date=cfg.start_str,
                end_date=cfg.end_str,
                usage_sink=usage_sink,
            )
            _drain_usage(tracker, usage_sink)

            if getattr(gen, "validation_errors", None) and not gen.script_code:
                await _record_failed(session_id, i, iter_id, gen_prompt, req,
                                     cfg, "; ".join(gen.validation_errors))
                continue

            bt_payload = dict(
                script_id=gen.script_id,
                symbol=cfg.symbol,
                timeframe=cfg.timeframe,
                start_date=cfg.start_dt,
                end_date=cfg.end_dt,
                initial_capital=req.initial_capital,
                commission=_COMMISSION,
                script_code=gen.script_code,
                strategy_name=gen.strategy_name,
                strategy_description=gen.strategy_description,
                wfv_enabled=True,
                wfv_is_months=_WFV_IS_MONTHS,
                wfv_oos_months=_WFV_OOS_MONTHS,
            )
            async with semaphore:
                cancel_token.check()
                (result, errors, rating, wf,
                 result_json, rating_json, wf_json) = await _perform_backtest(
                    pipeline=pipeline,
                    backtest_executor=backtest_executor,
                    payload=bt_payload,
                    cancel_token=cancel_token,
                )

            if result is None:
                await _record_failed(session_id, i, iter_id, gen_prompt, req,
                                     cfg, "; ".join(errors) if errors else "Backtest failed")
                continue

            # Insights — best-effort; a failure must not abort the loop.
            summary, suggestions = "", []
            try:
                ins_sink: list = []
                summary, suggestions, _ierr = await pipeline.generate_insights(
                    backtest_result=result_json,
                    strategy_name=gen.strategy_name,
                    strategy_description=gen.strategy_description,
                    script_code=gen.script_code,
                    natural_language_prompt=gen_prompt,
                    model=req.model,
                    symbol=cfg.symbol,
                    timeframe=cfg.timeframe,
                    start_date=cfg.start_str,
                    end_date=cfg.end_str,
                    initial_capital=req.initial_capital,
                    previous_summary=prev_summary,
                    previous_suggestions=prev_suggestion_titles or None,
                    walk_forward_result=wf_json,
                    usage_sink=ins_sink,
                )
                _drain_usage(tracker, ins_sink)
            except Exception as ins_err:  # noqa: BLE001 - best-effort
                logger.warning("auto-session insights failed (continuing): %s", ins_err)

            insights = {"summary": summary, "suggestions": suggestions}

            inp = _robust_inputs(result, wf, leverage=1.0)
            score = robust_score(inp)
            completed.append((iter_id, inp))

            node = _build_node(
                iter_id=iter_id,
                prompt=gen_prompt,
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
                cfg=cfg,
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
            # (NOT raw return) across ALL explored configs, so a
            # higher-return-but-WFE-failing / over-leveraged candidate is
            # never marked best.
            best_id = select_best(completed)
            await _update_autorun(session_id, status="running", currentIteration=i,
                                  bestIterationId=best_id, spend=tracker.snapshot())
            # Defense in depth: yield a clean loop turn before the next
            # round so back-to-back iterations never starve pending requests.
            await asyncio.sleep(0)

            # Prompt-refinement chain is pinned-path only (open-universe is a
            # deterministic per-config enumerator with no cross-config carry).
            if not is_open:
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
            await _record_failed(session_id, i, iter_id, gen_prompt, req, cfg, str(exc))
            continue

    # --- Terminal state ------------------------------------------------------
    if cancel_token.is_cancelled and stop_reason is None:
        final_status = "stopped"
        stop_reason = "stopped"  # visible, non-null reason for a stopped run
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
        spend=tracker.snapshot(),
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
                req: AutoSessionRequest, cfg: _Config, robust: float) -> dict:
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
        "params": _backtest_params(req, cfg),
        "timestamp": _now_iso(),
        "parentId": None,
        "walkForwardResult": wf_json,
        "walkForwardStatus": "complete" if wf_json else "idle",
    }


async def _record_failed(session_id: str, index: int, iter_id: str, prompt: str,
                         req: AutoSessionRequest, cfg: _Config,
                         error: str) -> None:
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
        "params": _backtest_params(req, cfg),
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
    # --- Validation (never a 500: every bad request is a clean 422) ------
    # Objective: v1 supports ONLY the single robust scalar (the
    # single-robust-scalar Non-Goal) — any other value is rejected clearly.
    objective = req.objective or "robust"
    if objective != "robust":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported objective {req.objective!r}. Only 'robust' is "
                "supported in this version."
            ),
        )

    if _is_open_universe(req):
        # Open-universe (J-12): symbol & timeframe BOTH omitted -> the
        # bounded seed-universe search. Dates are optional (a fixed
        # deterministic short window is used when omitted); if EITHER is
        # supplied BOTH must be valid YYYY-MM-DD.
        if req.start_date or req.end_date:
            if not (req.start_date and req.end_date):
                raise HTTPException(
                    status_code=422,
                    detail=("Provide BOTH start_date and end_date, or omit "
                            "both for the default open-universe window."),
                )
            try:
                _parse_date(req.start_date, end=False)
                _parse_date(req.end_date, end=True)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail="start_date and end_date must be YYYY-MM-DD.",
                )
    else:
        # Pinned config: symbol/timeframe/start/end are ALL required. A
        # partial pin (e.g. timeframe but no symbol) is a malformed pinned
        # request -> clear 422 (NOT silently promoted to open-universe).
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
                    f"Missing required pinned config field(s): "
                    f"{', '.join(missing)}. Provide all of "
                    "symbol/timeframe/start_date/end_date for a pinned run, "
                    "or omit BOTH symbol and timeframe for an open-universe "
                    "search."
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
    configs, _open = _config_plan(req)
    session_id = str(uuid.uuid4())
    now_ms = int(time.time() * 1000)
    nl = req.natural_language.strip()
    name = f"Auto: {nl[:40]}" + ("…" if len(nl) > 40 else "")

    # Create the session in the EXISTING file store BEFORE returning, so it
    # appears immediately in GET /api/sessions (derive_session_tabs keys off
    # session.json) and is openable. No parallel store / schema fork. The
    # durable spend is populated by the loop's first status write (within ms)
    # and survives a worker restart + browser reload from here on.
    await asyncio.to_thread(session_store.write_session_meta, session_id, {
        "name": name,
        "lastAccessedAt": now_ms,
        "backtestParams": _backtest_params(req, configs[0]),
        "autoRun": {
            "status": "running",
            "stopReason": None,
            "currentIteration": 0,
            "maxIterations": max_iter,
            "bestIterationId": None,
            "startedAt": _now_iso(),
            "updatedAt": _now_iso(),
            "spend": None,
            # Accepted-&-persisted request config (spec IN SCOPE). Written
            # into the durable autoRun block via the existing
            # write_session_meta — no parallel store, no schema fork — so it
            # survives a worker restart + browser reload and is readable from
            # GET /api/sessions/{id}. The loop's _update_autorun_sync does a
            # read-merge-write that preserves these keys every round.
            # history_scope's cross-run *learning* is J-15 / OUT OF SCOPE
            # this iteration; only accept-&-persist is in scope here.
            "objective": objective,
            "historyScope": req.history_scope,
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
    # Register BEFORE launching the detached task so the public stop endpoint
    # can reach this run's token the instant the session is listed. The token
    # is removed on every terminal path by run_auto_session's `finally`.
    _register_cancel(session_id, cancel_token)

    # Real run: the CPU-bound backtest is offloaded to a child process so it
    # never holds this API worker's GIL (anti-goal: GET /api/sessions and the
    # stop endpoint must stay responsive while a headless run is active).
    backtest_executor = _subprocess_backtest_executor()

    async def _runner() -> None:
        try:
            await run_auto_session(
                session_id, req,
                pipeline=pipeline,
                semaphore=semaphore,
                cancel_token=cancel_token,
                backtest_executor=backtest_executor,
            )
        except Exception as exc:  # noqa: BLE001 - background task must not crash silently
            logger.exception("auto-session %s crashed: %s", session_id, exc)
            # run_auto_session's finally already unregistered; this is
            # defence-in-depth for the runner crash/exception path.
            _unregister_cancel(session_id)
            try:
                await _update_autorun(
                    session_id, status="stopped", stopReason="stopped"
                )
            except Exception:  # noqa: BLE001
                pass

    # Detached background task — same pattern as api.py's
    # asyncio.create_task(run()). Does NOT block the event loop; GET
    # /api/sessions and other requests stay responsive while it runs.
    asyncio.create_task(_runner())

    return AutoSessionResponse(sessionId=session_id, status="running")


@router.post("/{session_id}/stop")
async def stop_auto_session(session_id: str):
    """Cooperatively request cancellation of a running headless auto-session.

    Returns promptly — it NEVER awaits loop completion or blocks the event
    loop. The loop owns the terminal transition; this endpoint only requests
    the stop two ways:

    * cancels the live in-process ``CancellationToken`` if it is in THIS
      worker (fast path — the in-flight pipeline checks it and winds down);
    * records ``autoRun.stopRequested`` durably in session.json so the loop's
      per-round read honours the stop even when the live token is not in the
      handling worker (multi-WEB_CONCURRENCY) or after a restart.

    Unknown / non-auto session -> clean 404. Already-terminal session ->
    idempotent no-op (no error, no extra iteration, no state regression).
    """
    meta = await asyncio.to_thread(session_store.read_session_meta, session_id)
    auto = (meta or {}).get("autoRun")
    if not meta or not isinstance(auto, dict):
        raise HTTPException(
            status_code=404,
            detail=f"Auto-session {session_id} not found.",
        )

    status = auto.get("status")
    if status in ("complete", "stopped"):
        # Idempotent: do NOT write anything — a terminal run must not regress
        # and no extra iteration may be triggered.
        return {
            "sessionId": session_id,
            "status": status,
            "stopReason": auto.get("stopReason"),
        }

    # Fast path: cancel the live token if this worker is handling the run.
    token = _CANCEL_REGISTRY.get(session_id)
    if token is not None:
        token.cancel()

    # Durable, worker-safe signal — honoured by the loop's per-round read even
    # with no live token here. Reuses the existing _update_autorun mechanism
    # (no parallel store, no schema fork, no new infra).
    await _update_autorun(session_id, stopRequested=True)

    return {"sessionId": session_id, "status": "stopping"}
