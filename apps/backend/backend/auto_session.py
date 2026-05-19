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
from shared.model_catalog import DEFAULT_MODEL, cheapest_model

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

# --- Staged SCREEN→PROMOTE knobs (J-14, open-universe ONLY) ------------------
# How many bounded-seed configs the cheap SCREEN stage evaluates, and how many
# top survivors are PROMOTEd to the full pipeline. _PROMOTE_TOP_K < the number
# screened (the spec's "k < number screened" invariant) and both are small so
# a tiny-budget run still shows ≥3 SCREEN markers and a small PROMOTE set. The
# screen set is a deterministic prefix of the finite _SEED_UNIVERSE (no blind
# fan-out); SCREEN is cheap by construction (no walk-forward, cheapest model,
# no insights, short shared window, warm Parquet cache reused across configs),
# so screening several seeds while promoting only the top-k is consistent with
# the goal's fast-and-cheap mandate.
_SCREEN_SET_SIZE = 4
_PROMOTE_TOP_K = 2

# --- Carried iter-3 B1 fix: which would_exceed() sentinels skip insights -----
# The post-`generate` insights call is skipped (the iteration node is still
# built/written and activity still recorded) ONLY when a TRUE spend cap is
# already reached between generate and insights. The cost tracker's
# would_exceed() also returns the "max-configs" sentinel — but that sentinel
# only gates *starting a new config*, NOT finishing an in-flight one. Crucially
# `_build_cost_tracker` pins the pinned-path config cap to == max_iter
# (the `default_cfg = hard_cfg = max_cfg = max_iter` branch), so on the FINAL
# pinned iteration would_exceed() returns "max-configs" right after that
# iteration's generate. Skipping insights on "max-configs" would silently
# suppress the final pinned iteration's insights + prompt-refinement chain
# (a J-04 / J-07–J-11 regression). Hence the gate is spend-caps-ONLY and
# explicitly EXCLUDES "max-configs".
_SPEND_CAPS: frozenset[str] = frozenset({"ai-tokens", "usd", "wall-clock"})


def _should_skip_insights(tracker: CostTracker) -> bool:
    """Carried B1 gate. True iff a true spend cap (AI-tokens / USD /
    wall-clock) is ALREADY reached at the moment we are about to call
    insights — never on the "max-configs" sentinel (see ``_SPEND_CAPS``)."""
    return tracker.would_exceed() in _SPEND_CAPS

# --- Bounded seed universe (J-12) -------------------------------------------
# A small, hard-coded constant set of (symbol, timeframe) candidates — a few
# liquid pairs × a couple of timeframes. Open-universe exploration draws ONLY
# from this set (anti-goal: MUST NOT blindly fan out across the whole exchange
# symbol list). This is deliberately NOT the 26×6 /api/symbols × /api/timeframes
# grid, NOT env-driven, and NOT a live exchange enumeration. The deterministic
# bounded enumerator below walks it in fixed order by default; iter-5 / J-15
# adds a read-only global-history warm start that returns it as a STABLE
# PERMUTATION (strongest historical (symbol, timeframe) family first) on an
# effective-"global" open-universe run — still ONLY this bounded set, never a
# fan-out. The explicit "this-run" opt-out keeps the fixed order; no LLM
# planner (deterministic surrogate — see _resolve_history_scope/_mine_history).
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

# --- history_scope effective semantics (J-15, open-universe ONLY) -----------
# The raw supplied request value is still persisted verbatim (``historyScope``
# in the autoRun block — null stays null); these are the EFFECTIVE resolved
# values that actually drive behaviour. Opt-out is the single explicit
# ``"this-run"``; the documented default ("learns from prior sessions to spend
# tokens where payoff is highest") is global warm-start, so an omitted /
# null / unknown-garbage value resolves to ``"global"`` (a garbage value is a
# clean default, never a 500). The effective value is recorded as the additive
# ``effectiveHistoryScope`` key on the existing autoRun dict (no schema fork,
# mirrors iter-4's additive ``stage``).
_HISTORY_SCOPE_OPT_OUT = "this-run"
_HISTORY_SCOPE_GLOBAL = "global"


def _resolve_history_scope(raw: Any) -> str:
    """Resolve the RAW supplied ``history_scope`` to its EFFECTIVE value.

    ``"this-run"`` (whitespace-tolerant) is the explicit opt-out. Everything
    else — ``None``, ``""``, ``"global"``, an unknown/garbage string, or even
    a non-string — resolves to the documented default ``"global"`` warm-start.
    Never raises (a garbage value is a clean default, not a 500).
    """
    if isinstance(raw, str) and raw.strip() == _HISTORY_SCOPE_OPT_OUT:
        return _HISTORY_SCOPE_OPT_OUT
    return _HISTORY_SCOPE_GLOBAL


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
    supports only ``"robust"`` (the single-robust-scalar Non-Goal).
    ``history_scope`` is accepted & persisted verbatim AND (iter-5 / J-15)
    now drives cross-run behaviour for an open-universe run: ``"this-run"``
    opts out (no mining, fixed seed order); anything else — omitted / null /
    ``"global"`` / unknown — resolves to global read-only warm-start (see
    :func:`_resolve_history_scope`). It is inert on the pinned path."""

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


# =============================================================================
# Read-only global-history warm start (J-15, open-universe + effective global)
#
# A dependency-light read-only surrogate (no LLM planner — the acceptance is
# satisfiable deterministically; the spec's explicit core design): mine the
# EXISTING durable session_store for prior auto-sessions' promoted,
# walk-forward-bearing iterations, aggregate the best robust score per
# (symbol, timeframe) family, and reorder the bounded seed enumeration so the
# historically strongest family is screened/promoted first. Read-only: no
# write/rename/delete/in-place mutation of any prior artifact (iter-0 / J-02).
# Best-effort: a missing/corrupt session or iteration is skipped (mirrors the
# SCREEN/PROMOTE except discipline) — mining never raises out or hangs the
# run. The "MUST NOT be re-sent uncached every round" anti-goal is satisfied
# structurally: this runs EXACTLY ONCE per run, off the event-loop thread (no
# per-round re-mining, no LLM call to cache).
# =============================================================================

def _mine_history(
    current_session_id: str,
) -> tuple[dict[tuple[str, str], float], int]:
    """Read-only mine of the existing durable store.

    Returns ``(best robust score per (symbol, timeframe) family, number of
    PRIOR sessions that contributed ≥1 usable promoted iteration)``. Only
    promoted (``stage == "promote"``), walk-forward-bearing
    (non-null ``walkForwardResult``), finite-``robustScore`` iterations
    count. The current run's own session is excluded (cross-run only). Uses
    ONLY the existing ``session_store`` read helpers; never mutates anything.
    """
    family_best: dict[tuple[str, str], float] = {}
    contributing = 0
    live_root = session_store.BASE_DIR / "live"
    try:
        session_dirs = (
            sorted(d for d in live_root.iterdir() if d.is_dir())
            if live_root.exists() else []
        )
    except OSError:
        return {}, 0

    for sdir in session_dirs:
        sid = sdir.name
        if sid == current_session_id:
            continue  # cross-run only — never the current run's own session
        try:
            contributed = False
            for itdir in session_store.list_iteration_dirs(sid):
                name = itdir.name
                if "_" not in name:
                    continue
                iter_id = name.split("_", 1)[1]
                meta = session_store.read_iteration_meta(sid, iter_id)
                if not isinstance(meta, dict):
                    continue
                if meta.get("stage") != "promote":
                    continue
                if meta.get("walkForwardResult") is None:
                    continue
                score = meta.get("robustScore")
                if not isinstance(score, (int, float)) or isinstance(
                    score, bool
                ):
                    continue
                score = float(score)
                if not math.isfinite(score):
                    continue
                params = meta.get("params") or {}
                sym = params.get("symbol")
                tf = params.get("timeframe")
                if not sym or not tf:
                    continue
                fam = (sym, tf)
                if fam not in family_best or score > family_best[fam]:
                    family_best[fam] = score
                contributed = True
            if contributed:
                contributing += 1
        except Exception:  # noqa: BLE001 - best-effort: skip a bad session
            continue
    return family_best, contributing


def _reorder_configs(
    configs: list[_Config], family_best: dict[tuple[str, str], float]
) -> list[_Config]:
    """Return ``configs`` as a STABLE PERMUTATION ordered by mined family
    strength: historically strongest ``(symbol, timeframe)`` first; families
    with no mined history keep the existing fixed seed order, after all mined
    ones; equal mined scores preserve the original seed order (stable). It is
    always a permutation of the SAME bounded set — no symbol/timeframe is
    added or dropped (no fan-out beyond the seed universe).
    """
    indexed = list(enumerate(configs))

    def _key(item: tuple[int, _Config]) -> tuple[int, float, int]:
        i, cfg = item
        fam = (cfg.symbol, cfg.timeframe)
        if fam in family_best:
            # group 0 (mined) before group 1 (unseen); strongest first;
            # original index as the stable, deterministic tie-break.
            return (0, -family_best[fam], i)
        return (1, 0.0, i)

    return [cfg for _, cfg in sorted(indexed, key=_key)]


def _strongest_family(
    family_best: dict[tuple[str, str], float],
) -> tuple[tuple[str, str], float]:
    """The cited family: highest mined robust score, tie-broken by the fixed
    seed-universe order (then lexicographically) for a deterministic citation.
    """
    seed_index = {fam: i for i, fam in enumerate(_SEED_UNIVERSE)}

    def _key(kv: tuple[tuple[str, str], float]) -> tuple[float, int, int]:
        fam, score = kv
        return (score, -seed_index.get(fam, len(_SEED_UNIVERSE)),
                -ord(fam[0][0]) if fam[0] else 0)

    fam, score = max(family_best.items(), key=_key)
    return fam, score


async def _warm_start_configs(
    session_id: str, configs: list[_Config]
) -> list[_Config]:
    """Once-per-run, off-event-loop read-only warm start (open-universe +
    effective global scope ONLY — the caller guards both).

    Mines prior sessions (via ``asyncio.to_thread`` — the blocking
    multi-session file walk MUST NOT run on the event-loop thread, iter-2
    lesson), reorders ``configs`` to a stable permutation by mined family
    strength, and appends EXACTLY ONE planner-decision activity entry citing
    the concrete prior evidence. No usable prior history → ``configs``
    returned unchanged and NO entry appended (byte-identical to the
    no-warm-start path; J-12/J-13/J-14 preserved). Plain operator language,
    no API keys/secrets, same entry shape the existing feed already renders.
    """
    family_best, n_sessions = await asyncio.to_thread(
        _mine_history, session_id
    )
    if not family_best:
        # Empty store / no prior promoted iterations → fixed seed order, no
        # citation. The fallback is byte-identical to today's enumeration.
        return configs

    reordered = _reorder_configs(configs, family_best)
    (sym, tf), top_score = _strongest_family(family_best)
    sessions_word = "session" if n_sessions == 1 else "sessions"
    await asyncio.to_thread(
        session_store.append_activity_entries, session_id, [
            _activity(
                "auto-run",
                (f"Warm start (global history): prioritising {sym} {tf} "
                 f"— prior best robust {top_score:.2f} across "
                 f"{n_sessions} prior {sessions_word}"),
                # Run-level decision, not tied to one iteration: an empty
                # iterationId lands it ungrouped at the TOP of the existing
                # feed (frontend ActivityLog.groupByIteration), fully
                # visible, no new component — UI-indistinguishable from the
                # iter-2/iter-4 auto-run markers it renders identically.
                "",
            ),
        ]
    )
    return reordered


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


class _Eval(NamedTuple):
    """Outcome of evaluating ONE config through :func:`_evaluate_one`."""

    ok: bool
    failed_reason: Optional[str]
    gen: Any
    result: Any
    wf: Any
    inp: Optional[RobustInputs]
    score: float
    summary: str
    suggestions: list
    insights_skipped: bool


class _Screened(NamedTuple):
    """One SCREEN survivor carried into the rank + PROMOTE stage. ``gen`` is
    the cheap-model generated strategy reused verbatim by PROMOTE (no
    re-generation — dedup anti-goal); ``proxy`` is the in-sample rank key."""

    cfg: _Config
    gen: Any
    proxy: float
    total_return: float
    iter_id: str


async def _evaluate_one(
    *,
    session_id: str,
    idx: int,
    iter_id: str,
    pipeline: Any,
    semaphore: asyncio.Semaphore,
    cancel_token: CancellationToken,
    backtest_executor: Optional[Callable[[dict, CancellationToken], Any]],
    tracker: CostTracker,
    req: AutoSessionRequest,
    cfg: _Config,
    gen_prompt: str,
    gen_prev: Optional[str],
    gen_model: str,
    wfv_enabled: bool,
    want_insights: bool,
    stage: Optional[str],
    reuse_gen: Any = None,
    prev_summary: Optional[str] = None,
    prev_suggestion_titles: Optional[list[str]] = None,
) -> _Eval:
    """Generate (or reuse) → backtest → B1-gated insights → build & write
    one iteration node. Shared by the pinned path (``stage=None``), the cheap
    SCREEN stage (``stage="screen"``, ``wfv_enabled=False``,
    ``want_insights=False``, cheapest ``gen_model``) and the PROMOTE stage
    (``stage="promote"``, ``wfv_enabled=True``, ``want_insights=True``,
    ``reuse_gen`` = the SCREEN candidate's strategy — NO second generate).

    Returns ``_Eval``. A generate-validation / backtest-None failure returns
    ``ok=False`` (the caller records it and continues — one bad config must
    not abort the loop); cancellation raises ``PipelineError`` to the caller.
    """
    if reuse_gen is not None:
        # PROMOTE reuses the SCREEN candidate's already-generated strategy by
        # code hash — no re-generation, and the same (symbol,timeframe,window)
        # means the warm single-file OHLCV Parquet cache is reused (no
        # re-fetch). Dedup anti-goal honoured structurally.
        gen = reuse_gen
    else:
        usage_sink: list = []
        gen = await pipeline.generate_strategy(
            natural_language=gen_prompt,
            model=gen_model,
            previous_script_code=gen_prev,
            symbol=cfg.symbol,
            timeframe=cfg.timeframe,
            start_date=cfg.start_str,
            end_date=cfg.end_str,
            usage_sink=usage_sink,
        )
        _drain_usage(tracker, usage_sink)
        if getattr(gen, "validation_errors", None) and not gen.script_code:
            return _Eval(False, "; ".join(gen.validation_errors), None, None,
                         None, 0.0, "", [], False)

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
        # SCREEN is cheap-first: NO walk-forward. PROMOTE / pinned: full WF.
        wfv_enabled=wfv_enabled,
        wfv_is_months=_WFV_IS_MONTHS,
        wfv_oos_months=_WFV_OOS_MONTHS,
    )
    # SCREEN is cheap in LLM + engine work but NOT in CPU — the
    # RestrictedPython next-bar backtest is GIL-holding whether or not WF
    # runs. It MUST still flow through the same subprocess executor seam as
    # PROMOTE (iter-2 lesson); never in-process "because it's cheap".
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
        return _Eval(False, "; ".join(errors) if errors else "Backtest failed",
                     gen, None, None, 0.0, "", [], False)
    if stage == "screen":
        # SCREEN never carries walk-forward by construction (cheap-first
        # anti-goal). Discard any WF a backtest stub might still return so a
        # screened-only iteration is unambiguously WF-free.
        wf, wf_json = None, None

    summary: str = ""
    suggestions: list = []
    insights_skipped = False
    if want_insights:
        if _should_skip_insights(tracker):
            # Carried iter-3 B1 fix: a TRUE spend cap (ai-tokens/usd/
            # wall-clock) was reached between generate and insights — skip
            # ONLY this insights call; the iteration node is STILL built &
            # written and activity STILL recorded below. NEVER skip on the
            # "max-configs" sentinel (see ``_SPEND_CAPS`` /
            # ``_should_skip_insights`` — the pinned-path final-iteration
            # trap).
            insights_skipped = True
        else:
            try:
                ins_sink: list = []
                summary, suggestions, _ierr = await pipeline.generate_insights(
                    backtest_result=result_json,
                    strategy_name=gen.strategy_name,
                    strategy_description=gen.strategy_description,
                    script_code=gen.script_code,
                    natural_language_prompt=gen_prompt,
                    # The STRONGER / requested model appears ONLY here (the
                    # promoted / pinned insights+refinement call).
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
                logger.warning(
                    "auto-session insights failed (continuing): %s", ins_err)

    insights = {"summary": summary, "suggestions": suggestions}
    inp = _robust_inputs(result, wf, leverage=1.0)
    score = robust_score(inp)

    if stage is None:
        model_used = getattr(gen, "model_used", req.model) or req.model
    elif stage == "promote":
        # The promoted iteration's representative model is the stronger
        # req.model (its insights/refinement call). The strategy CODE itself
        # was generated by the cheap SCREEN model and is reused verbatim
        # (no re-generation) — documented here so modelUsed is not
        # mis-read as "the code was regenerated by req.model".
        model_used = req.model
    else:  # screen
        model_used = getattr(gen, "model_used", gen_model) or gen_model

    node = _build_node(
        iter_id=iter_id,
        prompt=gen_prompt,
        script_code=gen.script_code,
        script_id=gen.script_id,
        strategy_name=gen.strategy_name,
        model_used=model_used,
        result=result,
        result_json=result_json,
        rating_json=rating_json,
        wf_json=wf_json,
        insights=insights,
        req=req,
        cfg=cfg,
        robust=score,
        stage=stage,
    )
    # All store I/O offloaded off the event-loop thread (same as the manual
    # session_routes path) so a continuous headless run keeps GET
    # /api/sessions and the J-08 poll responsive.
    await asyncio.to_thread(session_store.write_iteration, session_id, idx, node)
    return _Eval(True, None, gen, result, wf, inp, score, summary,
                 suggestions, insights_skipped)


async def _read_stop_requested(session_id: str) -> bool:
    """Durable, worker-safe cooperative-stop probe. The public stop endpoint
    records ``autoRun.stopRequested`` in session.json so the loop honours a
    stop even when the live in-process token is not in THIS worker
    (multi-WEB_CONCURRENCY) or after a restart. Read off the event-loop
    thread (same as the manual session_routes path) so it never blocks the
    loop (event-loop anti-goal)."""
    persisted = await asyncio.to_thread(
        session_store.read_session_meta, session_id
    )
    return bool(((persisted or {}).get("autoRun") or {}).get("stopRequested"))


async def _run_pinned(
    session_id: str,
    req: AutoSessionRequest,
    *,
    pipeline: Any,
    semaphore: asyncio.Semaphore,
    cancel_token: CancellationToken,
    backtest_executor: Optional[Callable[[dict, CancellationToken], Any]],
    tracker: CostTracker,
    cfg: _Config,
    max_iter: int,
    targets: dict,
    completed: list[tuple[str, RobustInputs]],
) -> tuple[Optional[str], int, Optional[str]]:
    """The pinned path — BYTE-UNCHANGED behaviourally vs iter-3: exactly ONE
    config every iteration, the full pipeline every iteration, the
    prior-suggestion prompt-refinement chain, NO SCREEN/PROMOTE activity.
    The only addition is the carried B1 insights gate inside
    :func:`_evaluate_one`, which is a no-op unless a true spend cap is hit
    between generate and insights (and explicitly NEVER on the "max-configs"
    sentinel returned on the final pinned iteration)."""
    best_id: Optional[str] = None
    stop_reason: Optional[str] = None
    prev_script_code: Optional[str] = None
    prev_summary: Optional[str] = None
    prev_suggestion_titles: list[str] = []
    next_prompt = req.natural_language
    iteration_index = 0

    for i in range(1, max_iter + 1):
        # Budget / cancel checks BEFORE any work: never start a round that
        # would exceed the cap ("no one more round past the cap").
        if cancel_token.is_cancelled:
            stop_reason = None
            break
        if tracker.would_exceed() is not None:
            stop_reason = "budget-exhausted"
            break
        if await _read_stop_requested(session_id):
            cancel_token.cancel()
            stop_reason = None
            break

        tracker.start_config()
        iteration_index = i
        iter_id = str(uuid.uuid4())
        await _update_autorun(session_id, status="running", currentIteration=i,
                              spend=tracker.snapshot())

        try:
            res = await _evaluate_one(
                session_id=session_id, idx=i, iter_id=iter_id,
                pipeline=pipeline, semaphore=semaphore,
                cancel_token=cancel_token,
                backtest_executor=backtest_executor, tracker=tracker,
                req=req, cfg=cfg, gen_prompt=next_prompt,
                gen_prev=prev_script_code, gen_model=req.model,
                wfv_enabled=True, want_insights=True, stage=None,
                prev_summary=prev_summary,
                prev_suggestion_titles=prev_suggestion_titles,
            )
            if not res.ok:
                await _record_failed(session_id, i, iter_id, next_prompt, req,
                                     cfg, res.failed_reason or "failed")
                continue

            completed.append((iter_id, res.inp))
            await asyncio.to_thread(
                session_store.append_activity_entries, session_id, [
                    _activity("auto-run",
                              f"Automated iteration {i}/{max_iter}", iter_id),
                    _activity(
                        "complete",
                        f"Backtest complete — "
                        f"return {res.result.total_return * 100:.2f}%, "
                        f"{res.result.num_trades} trades, "
                        f"robust {res.score:.3f}",
                        iter_id,
                    ),
                ]
            )
            if res.summary:
                await asyncio.to_thread(
                    session_store.append_activity_entries, session_id, [
                        _activity("insights", res.summary, iter_id),
                    ]
                )

            best_id = select_best(completed)
            await _update_autorun(session_id, status="running",
                                  currentIteration=i, bestIterationId=best_id,
                                  spend=tracker.snapshot())
            await asyncio.sleep(0)

            prev_script_code = res.gen.script_code
            prev_summary = res.summary or prev_summary
            prev_suggestion_titles = [
                s.get("title", "") for s in res.suggestions if s.get("title")
            ]
            if res.suggestions and res.suggestions[0].get("prompt"):
                next_prompt = res.suggestions[0]["prompt"]

            if targets and targets_met(res.inp, targets):
                stop_reason = "criteria-met"
                break

        except PipelineError:
            stop_reason = None
            cancel_token.cancel()
            break
        except Exception as exc:  # noqa: BLE001 - one bad iter must not hang
            logger.warning(
                "auto-session iteration %d failed (continuing): %s", i, exc)
            await _record_failed(session_id, i, iter_id, next_prompt, req,
                                 cfg, str(exc))
            continue

    return stop_reason, iteration_index, best_id


async def _run_staged_open_universe(
    session_id: str,
    req: AutoSessionRequest,
    *,
    pipeline: Any,
    semaphore: asyncio.Semaphore,
    cancel_token: CancellationToken,
    backtest_executor: Optional[Callable[[dict, CancellationToken], Any]],
    tracker: CostTracker,
    configs: list[_Config],
    max_iter: int,
    targets: dict,
    completed: list[tuple[str, RobustInputs]],
) -> tuple[Optional[str], int, Optional[str]]:
    """Staged SCREEN→PROMOTE controller (J-14, open-universe ONLY).

    SCREEN: cheaply evaluate a deterministic prefix of the bounded seed
    universe — ``wfv_enabled=False``, the catalog-cheapest model, NO insights
    — appending a distinct ``SCREEN`` activity marker per config. RANK the
    survivors by a cheap IN-SAMPLE proxy (Sharpe, tie-broken by return —
    explicitly NOT ``robust_score``/WFE, which need the WF SCREEN skipped).
    PROMOTE only the small top-k (k < number screened): rerun the FULL
    pipeline (``wfv_enabled=True`` + the stronger ``req.model`` + insights)
    REUSING the screened strategy by code hash + the warm Parquet cache.

    Staged ``max_configs`` semantics (documented inline per the spec): a
    "config" counted against ``max_configs`` is one **PROMOTE** (expensive,
    full-pipeline) candidate — ``tracker.start_config()`` is called once per
    PROMOTE only. SCREEN is cheap by construction and bounded by the finite
    seed universe (``_SCREEN_SET_SIZE`` ≤ ``len(_SEED_UNIVERSE)``) plus the
    AI-token/USD/wall-clock caps, so it is NOT counted against
    ``max_configs`` (the entire point of cheap-first staging is to reserve
    the expensive config budget for survivors). ``tracker.would_exceed()`` is
    still checked at the top of EVERY SCREEN candidate (token/USD/wall-clock
    gating; the configs sub-cap is simply not reached during SCREEN by
    design) and EVERY PROMOTE candidate (token/USD/wall-clock + max-configs);
    on ANY hard cap the run reaches ``budget-exhausted`` with NO further
    screen/promote config appended.
    """
    best_id: Optional[str] = None
    stop_reason: Optional[str] = None
    iteration_index = 0
    screened: list[_Screened] = []
    cheap_model = cheapest_model()

    screen_configs = configs[:_SCREEN_SET_SIZE]
    for n, cfg in enumerate(screen_configs, start=1):
        if cancel_token.is_cancelled:
            stop_reason = None
            break
        if tracker.would_exceed() is not None:
            # A true spend cap (ai-tokens/usd/wall-clock) reached: terminal
            # budget-exhausted, NO further screen — and we do NOT proceed to
            # PROMOTE (no config past the cap).
            stop_reason = "budget-exhausted"
            break
        if await _read_stop_requested(session_id):
            cancel_token.cancel()
            stop_reason = None
            break

        iteration_index += 1
        iter_id = str(uuid.uuid4())
        await _update_autorun(session_id, status="running",
                              currentIteration=iteration_index,
                              spend=tracker.snapshot())
        await asyncio.to_thread(
            session_store.append_activity_entries, session_id, [
                _activity("auto-run",
                          f"SCREEN config {n}: {cfg.symbol} {cfg.timeframe}",
                          iter_id),
            ]
        )
        try:
            res = await _evaluate_one(
                session_id=session_id, idx=iteration_index, iter_id=iter_id,
                pipeline=pipeline, semaphore=semaphore,
                cancel_token=cancel_token,
                backtest_executor=backtest_executor, tracker=tracker,
                req=req, cfg=cfg, gen_prompt=req.natural_language,
                gen_prev=None, gen_model=cheap_model,
                wfv_enabled=False, want_insights=False, stage="screen",
            )
            if not res.ok:
                await _record_failed(session_id, iteration_index, iter_id,
                                     req.natural_language, req, cfg,
                                     res.failed_reason or "failed")
                continue
            proxy = float(res.result.sharpe_ratio)
            ret = float(res.result.total_return)
            await asyncio.to_thread(
                session_store.append_activity_entries, session_id, [
                    _activity(
                        "complete",
                        f"SCREEN {n} done — {cfg.symbol} {cfg.timeframe}: "
                        f"in-sample Sharpe {proxy:.2f}, "
                        f"return {ret * 100:.2f}%, "
                        f"{res.result.num_trades} trades "
                        f"(cheap screen — no walk-forward)",
                        iter_id,
                    ),
                ]
            )
            screened.append(_Screened(cfg, res.gen, proxy, ret, iter_id))
            await asyncio.sleep(0)
        except PipelineError:
            stop_reason = None
            cancel_token.cancel()
            break
        except Exception as exc:  # noqa: BLE001 - one bad screen must not hang
            logger.warning(
                "auto-session SCREEN config %d failed (continuing): %s", n, exc)
            await _record_failed(session_id, iteration_index, iter_id,
                                 req.natural_language, req, cfg, str(exc))
            continue

    # A hard cap / cooperative stop during SCREEN is terminal: NO PROMOTE
    # config may start past it ("no one more config past the cap").
    if stop_reason is not None or cancel_token.is_cancelled:
        return stop_reason, iteration_index, best_id

    # RANK by the cheap in-sample proxy (Sharpe, tie-broken by raw return).
    # Deterministic + stable (ties keep seed order). Explicitly NOT
    # robust_score/WFE — SCREEN deliberately ran no walk-forward.
    ranked = sorted(screened, key=lambda s: (s.proxy, s.total_return),
                    reverse=True)
    # Promote only the small top-k with k < number screened (and never more
    # than the expensive iteration budget).
    k = max(0, min(_PROMOTE_TOP_K, len(ranked) - 1, max_iter))
    promote_set = ranked[:k]

    for cand in promote_set:
        cfg = cand.cfg
        if cancel_token.is_cancelled:
            stop_reason = None
            break
        if tracker.would_exceed() is not None:
            # Any hard cap (ai-tokens/usd/max-configs/wall-clock): terminal
            # budget-exhausted, NO further PROMOTE config appended.
            stop_reason = "budget-exhausted"
            break
        if await _read_stop_requested(session_id):
            cancel_token.cancel()
            stop_reason = None
            break

        # A PROMOTE is the expensive "config" counted against max_configs.
        tracker.start_config()
        iteration_index += 1
        iter_id = str(uuid.uuid4())
        await _update_autorun(session_id, status="running",
                              currentIteration=iteration_index,
                              spend=tracker.snapshot())
        await asyncio.to_thread(
            session_store.append_activity_entries, session_id, [
                _activity(
                    "auto-run",
                    f"PROMOTE config: {cfg.symbol} {cfg.timeframe} "
                    f"(top-{len(promote_set)} survivor; "
                    f"in-sample Sharpe {cand.proxy:.2f})",
                    iter_id,
                ),
            ]
        )
        try:
            res = await _evaluate_one(
                session_id=session_id, idx=iteration_index, iter_id=iter_id,
                pipeline=pipeline, semaphore=semaphore,
                cancel_token=cancel_token,
                backtest_executor=backtest_executor, tracker=tracker,
                req=req, cfg=cfg, gen_prompt=req.natural_language,
                gen_prev=None, gen_model=req.model,
                wfv_enabled=True, want_insights=True, stage="promote",
                reuse_gen=cand.gen,
            )
            if not res.ok:
                await _record_failed(session_id, iteration_index, iter_id,
                                     req.natural_language, req, cfg,
                                     res.failed_reason or "failed")
                continue

            completed.append((iter_id, res.inp))
            wfe_txt = (f"{res.wf.wfe:.2f}" if res.wf is not None
                       and res.wf.wfe is not None else "n/a")
            await asyncio.to_thread(
                session_store.append_activity_entries, session_id, [
                    _activity(
                        "complete",
                        f"PROMOTE done — {cfg.symbol} {cfg.timeframe}: "
                        f"return {res.result.total_return * 100:.2f}%, "
                        f"{res.result.num_trades} trades, "
                        f"robust {res.score:.3f}, "
                        f"walk-forward WFE {wfe_txt}",
                        iter_id,
                    ),
                ]
            )
            if res.summary:
                await asyncio.to_thread(
                    session_store.append_activity_entries, session_id, [
                        _activity("insights", res.summary, iter_id),
                    ]
                )

            best_id = select_best(completed)
            await _update_autorun(session_id, status="running",
                                  currentIteration=iteration_index,
                                  bestIterationId=best_id,
                                  spend=tracker.snapshot())
            await asyncio.sleep(0)

            if targets and targets_met(res.inp, targets):
                stop_reason = "criteria-met"
                break

        except PipelineError:
            stop_reason = None
            cancel_token.cancel()
            break
        except Exception as exc:  # noqa: BLE001 - one bad promote must not hang
            logger.warning(
                "auto-session PROMOTE config failed (continuing): %s", exc)
            await _record_failed(session_id, iteration_index, iter_id,
                                 req.natural_language, req, cfg, str(exc))
            continue

    return stop_reason, iteration_index, best_id


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
    state (it never hangs). Pinned requests refine ONE config across
    iterations (J-07–J-11, byte-unchanged); open-universe requests run the
    staged SCREEN→PROMOTE controller (J-12/J-14).
    """
    max_iter, _legacy_wall = _resolve_budget(req.budget)
    targets = req.targets.model_dump(exclude_none=True)

    configs, is_open = _config_plan(req)
    # Immutable hard cost tracker: AI-tokens / USD / max-configs / wall-clock,
    # caps fixed at construction. The per-round check below never starts a
    # config/round once any cap is reached ("no one more round past the cap").
    tracker = _build_cost_tracker(req, max_iter, is_open)

    # (id, RobustInputs) for every COMPLETED, best-eligible iteration. For an
    # open-universe run this holds ONLY the PROMOTED (walk-forward-bearing)
    # iterations — the cheap screen proxy NEVER leaks into best-selection
    # (J-09/J-16 robust-best invariant preserved); raw return is never used.
    completed: list[tuple[str, RobustInputs]] = []
    best_id: Optional[str] = None

    # The loop is the durable-status owner: ensure a coherent autoRun block
    # exists even when invoked directly (not via the endpoint) or resumed
    # after a worker restart. startedAt is preserved if already set.
    _meta = await asyncio.to_thread(session_store.read_session_meta, session_id)
    _existing = (_meta or {}).get("autoRun") or {}
    await _update_autorun(session_id, status="running", currentIteration=0,
                          maxIterations=max_iter, stopReason=None,
                          bestIterationId=_existing.get("bestIterationId"),
                          startedAt=_existing.get("startedAt") or _now_iso(),
                          # RAW history_scope, persisted verbatim (null stays
                          # null). The endpoint already wrote it; preserve
                          # that exact value (idempotent) and also record it
                          # when the loop is invoked directly so the durable
                          # record is coherent regardless of entry path.
                          historyScope=_existing.get(
                              "historyScope", req.history_scope),
                          spend=tracker.snapshot())

    if is_open:
        # iter-5 / J-15: resolve the EFFECTIVE history scope (raw value still
        # persisted verbatim by the endpoint) and record it as the additive
        # ``effectiveHistoryScope`` autoRun key — open-universe ONLY (the
        # pinned path stays byte-unchanged: no key, no mine, no reorder).
        effective_scope = _resolve_history_scope(req.history_scope)
        await _update_autorun(session_id,
                              effectiveHistoryScope=effective_scope)
        if effective_scope == _HISTORY_SCOPE_GLOBAL:
            # Read-only warm start: mine prior sessions off-thread EXACTLY
            # ONCE here (before the SCREEN loop), reorder the bounded seed
            # enumeration, and emit the planner-decision citation. Opt-out
            # ("this-run") skips this entirely → fixed seed order, no entry.
            configs = await _warm_start_configs(session_id, configs)
        stop_reason, iteration_index, best_id = await _run_staged_open_universe(
            session_id, req,
            pipeline=pipeline, semaphore=semaphore,
            cancel_token=cancel_token, backtest_executor=backtest_executor,
            tracker=tracker, configs=configs, max_iter=max_iter,
            targets=targets, completed=completed,
        )
    else:
        stop_reason, iteration_index, best_id = await _run_pinned(
            session_id, req,
            pipeline=pipeline, semaphore=semaphore,
            cancel_token=cancel_token, backtest_executor=backtest_executor,
            tracker=tracker, cfg=configs[0], max_iter=max_iter,
            targets=targets, completed=completed,
        )

    # --- Terminal state ------------------------------------------------------
    if cancel_token.is_cancelled and stop_reason is None:
        final_status = "stopped"
        stop_reason = "stopped"  # visible, non-null reason for a stopped run
    else:
        if stop_reason is None:
            # The search space / iteration budget was spent.
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
                req: AutoSessionRequest, cfg: _Config, robust: float,
                stage: Optional[str] = None) -> dict:
    """Build the node_dict in the EXACT shape write_iteration expects for a
    manual run (the canonical key set), so a headless run is
    indistinguishable in the UI from a manual one. The top-level summary
    fields populate the lightweight list path (cards/tree).

    ``stage`` ("screen" / "promote") is an additive, lightweight marker for
    the open-universe staged path so an operator/auditor can tell a cheap
    screened-only iteration from a promoted (walk-forward-bearing) one. It
    is NOT a schema fork (same write_iteration, no parallel store) and is
    OMITTED entirely on the pinned path so pinned nodes stay byte-identical.
    """
    node = {
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
    if stage is not None:
        node["stage"] = stage
    return node


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
            # ``historyScope`` is the RAW supplied value, persisted verbatim
            # (null stays null). From iter-5 / J-15 it ALSO drives behaviour:
            # the loop resolves the EFFECTIVE scope (_resolve_history_scope)
            # and records it as the additive ``effectiveHistoryScope`` key
            # (open-universe only) — read-only global warm-start vs the
            # explicit ``"this-run"`` opt-out.
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
