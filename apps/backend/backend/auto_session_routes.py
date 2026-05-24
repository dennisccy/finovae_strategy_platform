"""Headless auto-session API endpoints.

* ``POST /api/auto-sessions`` — start a server-side, budget-bounded automated
  strategy session from a pinned config.  Creates the live session in the file
  store first (so it appears immediately in ``GET /api/sessions``), then launches
  the loop as a non-blocking background task and returns 200.
* ``POST /api/auto-sessions/{session_id}/stop`` — request cancellation
  (cancellation infrastructure the loop needs; the full J-11 UI stop journey is
  iter-2).

Open-universe requests (omitted ``symbol``/``timeframe``) are rejected with a
clear 4xx — open-universe is J-12 / Layer-2.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from backend import session_store
from backend.auto_session import (
    STATUS_RUNNING,
    AutoSessionConfig,
    AutoSessionController,
    BudgetTracker,
    initial_auto_run,
    is_terminal,
)
from shared.model_catalog import DEFAULT_MODEL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auto-sessions", tags=["Auto Sessions"])

_VALID_TIMEFRAMES = {"1m", "5m", "15m", "1h", "4h", "1d"}


# =============================================================================
# Request models (pinned config)
# =============================================================================

class AutoSessionTargets(BaseModel):
    """Robust targets — all optional.  ``criteria-met`` requires the best
    iteration to satisfy every supplied target."""
    min_total_return: Optional[float] = None
    min_sharpe: Optional[float] = None
    min_wfe: Optional[float] = None
    max_drawdown: Optional[float] = Field(default=None, ge=0, le=1)
    min_trades: Optional[int] = Field(default=None, ge=0)


class AutoSessionBudget(BaseModel):
    """Hard budget — ALL caps are hard-enforced as of iter-3 (J-13).

    ``max_iterations`` bounds pinned improvement rounds; ``max_configs`` bounds
    the open-universe config search (defaults to ``max_iterations`` when an
    open-universe request omits it).  ``max_wall_clock_sec`` / ``max_tokens`` /
    ``max_usd`` are optional caps, each enforced when present."""
    max_iterations: int = Field(..., ge=1, le=50)
    max_configs: Optional[int] = Field(default=None, gt=0, le=50)
    max_wall_clock_sec: Optional[float] = Field(default=None, gt=0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    max_usd: Optional[float] = Field(default=None, gt=0)


class AutoSessionWalkForward(BaseModel):
    is_months: Optional[int] = Field(default=None, ge=1, le=60)
    oos_months: Optional[int] = Field(default=None, ge=1, le=60)


class CreateAutoSessionRequest(BaseModel):
    """Request for ``POST /api/auto-sessions`` — pinned OR open-universe.

    Pinning: provide BOTH ``symbol`` and ``timeframe`` (+ a ≥10-char
    ``natural_language``).  Open-universe (J-12): omit BOTH ``symbol`` and
    ``timeframe``; ``natural_language`` is then optional (a seed idea is drawn
    when omitted, or it pins the idea and the seed universe varies
    symbol/timeframe).  Providing exactly one of symbol/timeframe is ambiguous →
    rejected 400 in the route.  ``budget`` (with ``max_iterations``) is required.
    """
    natural_language: Optional[str] = Field(default=None, max_length=2000)
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    start_date: str
    end_date: str
    initial_capital: float = Field(default=10000.0, gt=0)
    leverage: float = Field(default=1.0, ge=1.0, le=10.0)
    allow_short: bool = False
    model: str = Field(default=DEFAULT_MODEL, pattern=r"^(claude-|gpt-)")
    objective: str = "robust"
    # J-15: opt-IN to global-history warm start with "global"; "this-run" (the
    # default / opt-out) ignores prior sessions. Open-universe only — the pinned
    # path ignores it. Any other value is rejected 422 by the validator below.
    history_scope: Optional[str] = "this-run"
    targets: Optional[AutoSessionTargets] = None
    walk_forward: Optional[AutoSessionWalkForward] = None
    budget: AutoSessionBudget

    @field_validator("start_date", "end_date")
    @classmethod
    def _valid_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be YYYY-MM-DD")
        return v

    @field_validator("history_scope")
    @classmethod
    def _valid_history_scope(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"global", "this-run"}:
            raise ValueError('history_scope must be "global" or "this-run"')
        return v

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.start_date >= self.end_date:
            raise ValueError("end_date must be after start_date")
        return self

    @model_validator(mode="after")
    def _pinned_requires_natural_language(self):
        """A fully-pinned config (both symbol + timeframe) requires a real
        ≥10-char strategy prompt; open-universe may omit it."""
        pinned = bool(self.symbol and self.timeframe)
        if pinned and (not self.natural_language or len(self.natural_language.strip()) < 10):
            raise ValueError("natural_language (min 10 chars) is required for a pinned config")
        return self


# =============================================================================
# Running-session handle (registered on app.state.auto_sessions)
# =============================================================================

@dataclass
class AutoSessionHandle:
    """In-memory handle for a launched auto-session.

    Holds the background ``task`` and the per-session ``lock`` that serializes
    every ``autoRun`` read-modify-write between the controller's ``_save_auto_run``
    and :func:`stop_auto_session` (B2 — see ``auto_session._save_auto_run``).  The
    handle is ephemeral; durability is the persisted ``autoRun`` status.
    """

    task: asyncio.Task
    lock: asyncio.Lock


# =============================================================================
# app.state helpers (robust whether or not the startup event ran)
# =============================================================================

def _resolve_pipeline(app):
    """The shared BacktestPipeline, or a test override on ``app.state``."""
    override = getattr(app.state, "auto_pipeline", None)
    if override is not None:
        return override
    from backend.api import get_pipeline  # lazy: avoids an import cycle at load
    return get_pipeline()


def _resolve_semaphore(app) -> asyncio.Semaphore:
    """The shared one-backtest-per-worker semaphore (create if startup didn't)."""
    sem = getattr(app.state, "backtest_semaphore", None)
    if sem is None:
        sem = asyncio.Semaphore(1)
        app.state.backtest_semaphore = sem
    return sem


def _registry(app) -> dict:
    reg = getattr(app.state, "auto_sessions", None)
    if reg is None:
        reg = {}
        app.state.auto_sessions = reg
    return reg


# =============================================================================
# Mapping request → controller config
# =============================================================================

def _build_config(req: CreateAutoSessionRequest, *, open_universe: bool) -> AutoSessionConfig:
    targets = req.targets.model_dump(exclude_none=True) if req.targets else {}
    wf = req.walk_forward
    stripped_nl = (req.natural_language or "").strip()
    if stripped_nl:
        session_name = f"Auto · {stripped_nl.splitlines()[0][:48]}"
    elif open_universe:
        session_name = "Auto · open-universe search"
    else:
        session_name = "Auto · session"
    return AutoSessionConfig(
        natural_language=req.natural_language or "",
        symbol=req.symbol,            # None for open-universe (seed configs vary it)
        timeframe=req.timeframe,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        leverage=req.leverage,
        allow_short=req.allow_short,
        model=req.model,
        objective=req.objective,
        targets=targets,
        wfv_is_months=(wf.is_months if wf and wf.is_months else 6),
        wfv_oos_months=(wf.oos_months if wf and wf.oos_months else 3),
        session_name=session_name,
        # Coerce an omitted/None value to the opt-out default (defense-in-depth;
        # the controller also treats any non-"global" value as opt-out).
        history_scope=(req.history_scope or "this-run"),
    )


def _build_budget(req: CreateAutoSessionRequest, *, open_universe: bool) -> BudgetTracker:
    b = req.budget
    # Open-universe needs a config cap; default it to max_iterations when the
    # request omits it (a minimal `{max_iterations: N}` budget explores N configs).
    max_configs = b.max_configs
    if open_universe and max_configs is None:
        max_configs = b.max_iterations
    return BudgetTracker(
        max_iterations=b.max_iterations,
        max_configs=max_configs,
        max_wall_clock_sec=b.max_wall_clock_sec,
        max_tokens=b.max_tokens,
        max_usd=b.max_usd,
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("")
async def create_auto_session(req: CreateAutoSessionRequest, raw_request: Request):
    """Start a headless automated strategy session — pinned (J-07) or
    open-universe (J-12).

    Pinned = both ``symbol`` and ``timeframe`` present; open-universe = both
    omitted (routes to the seed-universe search). Exactly one present is
    ambiguous → 400."""
    symbol_present = bool(req.symbol)
    timeframe_present = bool(req.timeframe)
    if symbol_present != timeframe_present:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide BOTH 'symbol' and 'timeframe' to pin a config, or NEITHER "
                "for an open-universe search (objective + budget only)."
            ),
        )
    open_universe = not symbol_present  # both omitted

    if req.objective != "robust":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported objective '{req.objective}'. "
                "Only 'robust' is available in this iteration."
            ),
        )
    if not open_universe and req.timeframe not in _VALID_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported timeframe '{req.timeframe}'. "
                f"Use one of {sorted(_VALID_TIMEFRAMES)}."
            ),
        )

    app = raw_request.app
    config = _build_config(req, open_universe=open_universe)
    budget = _build_budget(req, open_universe=open_universe)
    session_id = str(uuid.uuid4())

    # Create the live session in the store FIRST so it shows up immediately in
    # GET /api/sessions (a new session tab) with no browser interaction.
    auto_run = initial_auto_run(budget, status=STATUS_RUNNING)
    await asyncio.to_thread(
        session_store.write_session_meta,
        session_id,
        {
            "name": config.session_name,
            "backtestParams": config.backtest_params(),
            "autoRun": auto_run,
            "lastAccessedAt": int(time.time() * 1000),
        },
    )

    # Launch the loop as a non-blocking background task (no broker/queue — the
    # in-memory handle is ephemeral; durability is the persisted autoRun status).
    # The per-session lock is shared with the controller so a concurrent /stop
    # serializes against its autoRun writes (B2).
    pipeline = _resolve_pipeline(app)
    semaphore = _resolve_semaphore(app)
    lock = asyncio.Lock()
    controller = AutoSessionController(
        session_id, config, budget, pipeline, semaphore=semaphore, auto_run_lock=lock,
        open_universe=open_universe,
    )
    registry = _registry(app)
    task = asyncio.create_task(controller.run())
    registry[session_id] = AutoSessionHandle(task=task, lock=lock)
    task.add_done_callback(lambda _t, sid=session_id: registry.pop(sid, None))

    return {"sessionId": session_id, "status": auto_run["status"], "autoRun": auto_run}


@router.post("/{session_id}/stop")
async def stop_auto_session(session_id: str, raw_request: Request):
    """Request cancellation of a running automated session (J-11).

    Flips the persisted ``stopRequested`` flag; the loop honors it at its next
    checkpoint and transitions to ``stopped``.  Idempotent 200 if already
    terminal; 404 if the session is unknown / not an auto-session.

    **B2.** The read-modify-write runs under the SAME per-session lock the
    controller's ``_save_auto_run`` holds, so a stop issued mid-``_save_auto_run``
    is serialized after it and never lost (TOCTOU).  If no live handle exists on
    this worker (run already finished, or started on another worker), a transient
    lock is used — there is no local controller to race, and durability is the
    persisted flag the controller re-reads at its next checkpoint.
    """
    handle = _registry(raw_request.app).get(session_id)
    lock = handle.lock if handle is not None else asyncio.Lock()

    async with lock:
        meta = await asyncio.to_thread(session_store.read_session_meta, session_id)
        if not meta or not isinstance(meta.get("autoRun"), dict):
            raise HTTPException(status_code=404, detail=f"Auto-session {session_id} not found")

        auto_run = meta["autoRun"]
        if is_terminal(auto_run.get("status")):
            # Already finished — no-op (idempotent).
            return {"sessionId": session_id, "status": auto_run.get("status"), "autoRun": auto_run}

        updated = {**auto_run, "stopRequested": True}
        await asyncio.to_thread(
            session_store.write_session_meta, session_id, {"autoRun": updated}
        )
    return {"sessionId": session_id, "status": updated.get("status"), "autoRun": updated}
