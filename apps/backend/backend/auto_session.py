"""Headless auto-session loop (Layer-1 Foundation).

A server-side, budget-bounded strategy search that **reuses the existing
``BacktestPipeline``** for every LLM / backtest / walk-forward step (no sandbox
or engine bypass) and writes the **same** session / iteration / activity /
suggestion artifacts the UI renders, through ``backend.session_store`` (no
parallel store, no schema fork).  A headless run is therefore indistinguishable
in the UI from a manual one.

Key pieces (all canonical for the automated session, registered in the session
blueprint Data Contract):

* :class:`BudgetTracker` — immutable budget value object.  ``max_iterations``
  and ``max_wall_clock_sec`` are **hard-enforced** (the loop checks
  :meth:`BudgetTracker.exceeded` *before* starting each round and never starts
  "one more round" past a cap).  Token / USD counters are best-effort in iter-1
  (their hard cap is J-13 / Layer-2).
* :class:`RobustScorer` — the canonical "best" definition.  WFE-gated (reuses
  the in-browser ``0.3`` accept threshold), min-trades-floored, drawdown-
  penalized.  Ported from the in-browser ``scoreIteration`` in
  ``apps/frontend/src/hooks/useBacktest.ts`` (do not reinvent the scoring).
* :func:`targets_satisfied` — does the current best satisfy every supplied
  robust target?
* :class:`AutoSessionController` — runs the loop as an awaitable background task.

Anti-goal compliance notes:
* API keys / secrets are never written to the activity log or the ``autoRun``
  block — only NL prompt, config, metrics, ids, and counters are persisted.
* The loop acquires the shared one-backtest-per-worker semaphore for each
  backtest so it never blocks the API event loop.
* The durable ``autoRun`` status lives on ``session.json`` (the in-memory task
  handle is ephemeral; :func:`reconcile_orphaned_sessions` repairs runs orphaned
  by a worker restart).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Callable, Optional

from backend import session_store
from backend.result_serialization import (
    rating_to_dict,
    result_to_dict,
    walk_forward_to_dict,
)
from shared.model_catalog import DEFAULT_MODEL

logger = logging.getLogger(__name__)

# WFE accept threshold — ported verbatim from the in-browser auto-run loop
# (useBacktest.ts: ``const WF_ACCEPT_THRESHOLD = 0.3``).
WF_ACCEPT_THRESHOLD = 0.3
# Minimum completed trades for a candidate to be eligible as "best".  The
# in-browser scorer treats ``trades === 0`` as ineligible (-Infinity); a floor
# of 1 reproduces that and is the documented "min-trades floor".
DEFAULT_MIN_TRADES_FLOOR = 1
# Drawdown penalty coefficient applied to the ported base score so the robust
# objective is "drawdown-penalized" as the Data Contract requires.
DEFAULT_DD_PENALTY_WEIGHT = 0.5

# Default exchange/commission for headless runs (Binance BNB taker), matching
# BacktestPipeline defaults.  No ``exchange`` field is accepted in iter-1.
DEFAULT_EXCHANGE = "binance"
DEFAULT_COMMISSION = 0.00075

# ---- Run lifecycle states (served on autoRun.status) -----------------------
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_CRITERIA_MET = "criteria-met"
STATUS_BUDGET_EXHAUSTED = "budget-exhausted"
STATUS_STOPPED = "stopped"
STATUS_INTERRUPTED = "interrupted"
STATUS_ERROR = "error"

TERMINAL_STATUSES = frozenset({
    STATUS_CRITERIA_MET,
    STATUS_BUDGET_EXHAUSTED,
    STATUS_STOPPED,
    STATUS_INTERRUPTED,
    STATUS_ERROR,
})
# Statuses that mean "still in flight" and so are reconcilable to interrupted on
# a worker restart.
ACTIVE_STATUSES = frozenset({STATUS_QUEUED, STATUS_RUNNING})


def is_terminal(status: Optional[str]) -> bool:
    return status in TERMINAL_STATUSES


# =============================================================================
# Budget tracker (immutable)
# =============================================================================

@dataclass(frozen=True)
class BudgetTracker:
    """Immutable budget value object for one automated session.

    ``max_iterations`` (improvement rounds) and ``max_wall_clock_sec`` are
    hard-enforced caps; ``tokens`` / ``usd`` are best-effort counters in iter-1.
    "Incrementing" returns a NEW instance (frozen — never mutated in place).
    """

    max_iterations: int
    iterations_done: int = 0
    wall_clock_sec: float = 0.0
    max_wall_clock_sec: Optional[float] = None
    tokens: int = 0
    usd: float = 0.0

    def with_round_completed(self) -> "BudgetTracker":
        """Return a copy with one more improvement round counted."""
        return replace(self, iterations_done=self.iterations_done + 1)

    def with_wall_clock(self, wall_clock_sec: float) -> "BudgetTracker":
        """Return a copy with the elapsed wall-clock recorded."""
        return replace(self, wall_clock_sec=wall_clock_sec)

    def with_usage(self, *, tokens: int = 0, usd: float = 0.0) -> "BudgetTracker":
        """Return a copy with token/USD usage accumulated (best-effort)."""
        return replace(self, tokens=self.tokens + tokens, usd=self.usd + usd)

    def exceeded(self) -> bool:
        """True when any HARD-enforced cap (iterations or wall-clock) is reached.

        Checked *before* each round so the loop never starts a round past a cap.
        """
        if self.iterations_done >= self.max_iterations:
            return True
        if self.max_wall_clock_sec is not None and self.wall_clock_sec >= self.max_wall_clock_sec:
            return True
        return False

    def to_dict(self) -> dict:
        """Serialize for the ``autoRun.budget`` block."""
        return {
            "iterationsDone": self.iterations_done,
            "maxIterations": self.max_iterations,
            "wallClockSec": round(self.wall_clock_sec, 3),
            "maxWallClockSec": self.max_wall_clock_sec,
            "tokens": self.tokens,
            "usd": self.usd,
        }


# =============================================================================
# Robust scorer (canonical "best" definition)
# =============================================================================

@dataclass(frozen=True)
class IterationMetrics:
    """The metrics the robust objective reads off a canonical ``BacktestResult``
    (plus the WFE from the canonical ``WalkForwardResult``).  Never recomputes a
    metric — it only reads the values already computed by ``MetricsCalculator`` /
    ``walk_forward``."""

    iteration_id: str
    total_return: float
    sharpe: float
    num_trades: int
    max_drawdown: float
    margin_called: bool = False
    wfe: Optional[float] = None


@dataclass(frozen=True)
class RobustScorer:
    """Selects the single best iteration by the robust objective.

    Scalar (ported from the in-browser ``scoreIteration``)::

        freq      = min(1, 0.5 + num_trades / 100)      # ramps 0.5x→1x
        sharpe+   = max(0, sharpe) * 0.05
        base      = (total_return + sharpe+) * freq
        score     = base - dd_penalty_weight * max_drawdown   # drawdown penalty

    Eligibility (a candidate may only be marked best if all hold):
        * num_trades >= min_trades_floor      (zero/under-floor ineligible)
        * not margin_called                   (blew up / over-leveraged)
        * wfe is None or wfe >= wf_accept_threshold   (WFE gate, when WFV ran)
    """

    wf_accept_threshold: float = WF_ACCEPT_THRESHOLD
    min_trades_floor: int = DEFAULT_MIN_TRADES_FLOOR
    dd_penalty_weight: float = DEFAULT_DD_PENALTY_WEIGHT

    def score(self, m: IterationMetrics) -> float:
        if m.num_trades < self.min_trades_floor:
            return float("-inf")
        freq_multiplier = min(1.0, 0.5 + (m.num_trades / 100.0))
        sharpe_bonus = m.sharpe * 0.05 if m.sharpe > 0 else 0.0
        base = (m.total_return + sharpe_bonus) * freq_multiplier
        return base - self.dd_penalty_weight * m.max_drawdown

    def is_eligible(self, m: IterationMetrics) -> bool:
        if m.num_trades < self.min_trades_floor:
            return False
        if m.margin_called:
            return False
        if m.wfe is not None and m.wfe < self.wf_accept_threshold:
            return False
        return True

    def select_best(self, candidates: list[IterationMetrics]) -> Optional[IterationMetrics]:
        """Return the highest-scoring ELIGIBLE candidate (or None)."""
        eligible = [c for c in candidates if self.is_eligible(c)]
        if not eligible:
            return None
        return max(eligible, key=self.score)


# =============================================================================
# Targets-satisfaction predicate
# =============================================================================

# Effective target keys (all optional).  An empty / all-None targets dict means
# "no success criteria" → never criteria-met (the run goes to budget exhaustion).
_TARGET_KEYS = ("min_total_return", "min_sharpe", "min_wfe", "max_drawdown", "min_trades")


def has_targets(targets: Optional[dict]) -> bool:
    """True when at least one robust target field is supplied (non-None)."""
    if not targets:
        return False
    return any(targets.get(k) is not None for k in _TARGET_KEYS)


def targets_satisfied(targets: Optional[dict], m: IterationMetrics) -> bool:
    """Whether ``m`` satisfies EVERY supplied robust target.

    Returns ``False`` when no targets are supplied — absent targets are not a
    success condition (per J-09: absent/unsatisfiable targets → budget-exhausted,
    not criteria-met).  ``min_wfe`` is unsatisfiable when ``m`` has no WFE.
    """
    if not has_targets(targets):
        return False
    assert targets is not None  # for type-checkers; has_targets guards None
    if targets.get("min_total_return") is not None and m.total_return < targets["min_total_return"]:
        return False
    if targets.get("min_sharpe") is not None and m.sharpe < targets["min_sharpe"]:
        return False
    if targets.get("max_drawdown") is not None and m.max_drawdown > targets["max_drawdown"]:
        return False
    if targets.get("min_trades") is not None and m.num_trades < targets["min_trades"]:
        return False
    if targets.get("min_wfe") is not None:
        if m.wfe is None or m.wfe < targets["min_wfe"]:
            return False
    return True


# =============================================================================
# Normalized config
# =============================================================================

@dataclass(frozen=True)
class AutoSessionConfig:
    """Resolved, framework-agnostic config for one automated session (built from
    the validated API request)."""

    natural_language: str
    symbol: str
    timeframe: str
    start_date: str            # "YYYY-MM-DD"
    end_date: str              # "YYYY-MM-DD"
    initial_capital: float = 10000.0
    leverage: float = 1.0
    allow_short: bool = False
    model: str = DEFAULT_MODEL
    objective: str = "robust"
    commission: float = DEFAULT_COMMISSION
    exchange: str = DEFAULT_EXCHANGE
    targets: dict = field(default_factory=dict)
    wfv_is_months: int = 6
    wfv_oos_months: int = 3
    session_name: Optional[str] = None

    def backtest_params(self) -> dict:
        """The ``params`` block stored on each iteration node (UI shape)."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "exchange": self.exchange,
            "allow_short": self.allow_short,
            "leverage": self.leverage,
        }


# =============================================================================
# Helpers
# =============================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


def _to_datetime(date_str: str, *, end_of_day: bool) -> datetime:
    """Parse a 'YYYY-MM-DD' string to a UTC datetime (mirrors backend.api)."""
    base = datetime.strptime(date_str, "%Y-%m-%d")
    t = datetime.max.time() if end_of_day else datetime.min.time()
    return datetime.combine(base.date(), t).replace(tzinfo=timezone.utc)


def initial_auto_run(budget: BudgetTracker, *, status: str = STATUS_RUNNING) -> dict:
    """The ``autoRun`` block written to ``session.json`` when a session starts."""
    return {
        "status": status,
        "stopReason": None,
        "stopRequested": False,
        "bestIterationId": None,
        "budget": budget.to_dict(),
        "startedAt": _now_iso(),
        "endedAt": None,
    }


# =============================================================================
# Controller
# =============================================================================

class AutoSessionController:
    """Runs the headless auto-session loop for one session.

    The pipeline is **injected** (the production route passes the shared
    ``BacktestPipeline``; tests pass a deterministic fake) so the loop is
    hermetically testable without a live LLM.
    """

    def __init__(
        self,
        session_id: str,
        config: AutoSessionConfig,
        budget: BudgetTracker,
        pipeline,
        *,
        scorer: Optional[RobustScorer] = None,
        semaphore: Optional[asyncio.Semaphore] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.session_id = session_id
        self.config = config
        self.budget = budget
        self.pipeline = pipeline
        self.scorer = scorer or RobustScorer()
        self.semaphore = semaphore or asyncio.Semaphore(1)
        self._clock = clock

        self.status = STATUS_RUNNING
        self.stop_reason: Optional[str] = None
        self.best_id: Optional[str] = None
        self.best_metrics: Optional[IterationMetrics] = None
        self.started_at = _now_iso()
        self.ended_at: Optional[str] = None

        self._start_monotonic = self._clock()
        self._next_index = 1
        self._baseline_node: Optional[dict] = None
        self._baseline_index = 1

    # ---- persistence helpers ------------------------------------------------

    def _save_auto_run(self) -> dict:
        """Write the current autoRun block to session.json, PRESERVING an
        externally-set ``stopRequested`` flag (the /stop endpoint owns it)."""
        persisted = (session_store.read_session_meta(self.session_id) or {}).get("autoRun", {})
        auto_run = {
            "status": self.status,
            "stopReason": self.stop_reason,
            "stopRequested": bool(persisted.get("stopRequested", False)),
            "bestIterationId": self.best_id,
            "budget": self.budget.to_dict(),
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
        }
        session_store.write_session_meta(self.session_id, {"autoRun": auto_run})
        return auto_run

    def _stop_requested(self) -> bool:
        meta = session_store.read_session_meta(self.session_id) or {}
        return bool(meta.get("autoRun", {}).get("stopRequested", False))

    def _append_activity(self, type_: str, content: str, *, iteration_id: Optional[str] = None,
                         status: str = "done") -> None:
        entry = {
            "id": _new_id(),
            "type": type_,
            "timestamp": _now_iso(),
            "content": content,
            "status": status,
        }
        if iteration_id is not None:
            entry["iterationId"] = iteration_id
        session_store.append_activity_entries(self.session_id, [entry])

    # ---- node construction --------------------------------------------------

    def _build_node(self, *, iteration_id: str, prompt: str, gen_result, result,
                    rating, wf_result, parent_id: Optional[str], insights: Optional[dict]) -> dict:
        """Assemble an IterationNode dict byte-shape-compatible with a manual run."""
        return {
            "id": iteration_id,
            "prompt": prompt,
            "scriptCode": gen_result.script_code,
            "scriptId": gen_result.script_id,
            "strategyName": gen_result.strategy_name,
            "status": "complete",
            "timestamp": _now_iso(),
            "params": self.config.backtest_params(),
            "parentId": parent_id,
            "totalReturn": result.total_return,
            "winRate": result.win_rate,
            "numTrades": result.num_trades,
            "sharpe": result.sharpe_ratio,
            "maxDrawdown": min(1.0, float(result.max_drawdown)),
            "modelUsed": gen_result.model_used or self.config.model,
            "result": result_to_dict(result),
            "rating": rating_to_dict(rating),
            "insights": insights,
            "walkForwardResult": walk_forward_to_dict(wf_result),
            "walkForwardStatus": "complete" if wf_result is not None else None,
        }

    @staticmethod
    def _metrics_from(node: dict, wf_result) -> IterationMetrics:
        return IterationMetrics(
            iteration_id=node["id"],
            total_return=float(node["totalReturn"]),
            sharpe=float(node["sharpe"]),
            num_trades=int(node["numTrades"]),
            max_drawdown=float(node["maxDrawdown"]),
            margin_called=bool((node.get("result") or {}).get("margin_called", False)),
            wfe=(float(wf_result.wfe) if wf_result is not None else None),
        )

    # ---- pipeline steps (semaphore-guarded backtest) ------------------------

    async def _generate(self, prompt: str, previous_script_code: Optional[str]):
        return await self.pipeline.generate_strategy(
            natural_language=prompt,
            model=self.config.model,
            previous_script_code=previous_script_code,
            symbol=self.config.symbol,
            timeframe=self.config.timeframe,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            allow_short=self.config.allow_short,
            leverage=self.config.leverage,
        )

    async def _backtest(self, gen_result, *, wfv_enabled: bool):
        """Run a backtest (reusing the pipeline). Acquires the shared
        one-backtest-per-worker semaphore so the event loop stays responsive."""
        start_dt = _to_datetime(self.config.start_date, end_of_day=False)
        end_dt = _to_datetime(self.config.end_date, end_of_day=True)
        async with self.semaphore:
            return await self.pipeline.execute_backtest(
                script_id=gen_result.script_id,
                symbol=self.config.symbol,
                timeframe=self.config.timeframe,
                start_date=start_dt,
                end_date=end_dt,
                initial_capital=self.config.initial_capital,
                commission=self.config.commission,
                script_code=gen_result.script_code,
                strategy_name=gen_result.strategy_name,
                strategy_description=gen_result.strategy_description,
                allow_short=self.config.allow_short,
                leverage=self.config.leverage,
                wfv_enabled=wfv_enabled,
                wfv_is_months=self.config.wfv_is_months,
                wfv_oos_months=self.config.wfv_oos_months,
            )

    async def _insights(self, node: dict) -> Optional[dict]:
        """Generate insights (summary + suggestions) for an iteration node."""
        try:
            summary, suggestions, errors = await self.pipeline.generate_insights(
                backtest_result=node.get("result") or {},
                strategy_name=node.get("strategyName", ""),
                strategy_description="",
                script_code=node.get("scriptCode", ""),
                natural_language_prompt=node.get("prompt", ""),
                model=self.config.model,
                symbol=self.config.symbol,
                timeframe=self.config.timeframe,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                allow_short=self.config.allow_short,
                leverage=self.config.leverage,
                initial_capital=self.config.initial_capital,
                walk_forward_result=node.get("walkForwardResult"),
            )
        except Exception as exc:  # insights are best-effort; never crash the loop
            logger.warning("auto-session %s: insights generation failed: %s", self.session_id, exc)
            return None
        if errors and not summary:
            return None
        return {
            "summary": summary or "",
            "suggestions": [
                {"title": s.get("title", ""), "description": s.get("description", ""),
                 "prompt": s.get("prompt", "")}
                for s in (suggestions or [])
            ],
        }

    # ---- main loop ----------------------------------------------------------

    async def run(self) -> dict:
        """Execute the loop to a terminal state. Returns the final autoRun block.

        Never raises out of the background task — a hard failure is captured as
        a terminal ``error`` status on the durable store.
        """
        try:
            await self._run_inner()
        except Exception as exc:  # pragma: no cover - defensive; surfaced on store
            logger.exception("auto-session %s crashed: %s", self.session_id, exc)
            self.status = STATUS_ERROR
            self.stop_reason = STATUS_ERROR
            self.ended_at = _now_iso()
            self._append_activity("error", f"Automated session failed: {exc}")
        return self._save_auto_run()

    async def _run_inner(self) -> None:
        cfg = self.config
        self.status = STATUS_RUNNING
        self._save_auto_run()
        self._append_activity("user-prompt", cfg.natural_language)

        # ---- Step 0: baseline iteration (generate → backtest → rating → insights)
        baseline = await self._create_iteration(
            prompt=cfg.natural_language,
            previous_script_code=None,
            parent_id=None,
            wfv_enabled=False,
        )
        if baseline is None:
            # Baseline could not be produced (e.g., generation/backtest error).
            self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
            return

        node, wf_result = baseline
        self._baseline_node = node
        # Best-so-far starts at the baseline (the only iteration).
        self.best_id = node["id"]
        self.best_metrics = self._metrics_from(node, wf_result)
        node["insights"] = await self._insights(node)
        self._baseline_index = self._persist_new(node)
        self._save_auto_run()

        # ---- Improvement rounds (hard-bounded by budget) ------------------
        while True:
            self.budget = self.budget.with_wall_clock(self._clock() - self._start_monotonic)

            # Terminal checks, in priority order.
            if has_targets(cfg.targets) and self.best_metrics is not None \
                    and targets_satisfied(cfg.targets, self.best_metrics):
                self._finish(STATUS_CRITERIA_MET, "criteria-met")
                return
            if self.budget.exceeded():
                self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
                return
            if self._stop_requested():
                self._finish(STATUS_STOPPED, "stopped")
                return

            suggestions = [
                s for s in (self._baseline_node.get("insights") or {}).get("suggestions", [])
                if not s.get("disabled")
            ]
            if not suggestions:
                # No remaining suggestions — documented budget-exhausted variant.
                self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
                return

            self._append_activity(
                "auto-run",
                f"Round {self.budget.iterations_done + 1}: trying "
                f"{len(suggestions)} suggestion(s)…",
                iteration_id=self._baseline_node["id"],
            )

            round_candidates: list[IterationMetrics] = []
            for suggestion in suggestions:
                created = await self._create_iteration(
                    prompt=suggestion.get("prompt", ""),
                    previous_script_code=self._baseline_node.get("scriptCode"),
                    parent_id=self._baseline_node["id"],
                    wfv_enabled=True,
                )
                if created is None:
                    continue
                cand_node, cand_wf = created
                cand_node["insights"] = None
                self._persist_new(cand_node)
                round_candidates.append(self._metrics_from(cand_node, cand_wf))

            self.budget = self.budget.with_round_completed()

            # Advance baseline to the round's best ELIGIBLE candidate iff it
            # beats the current best score (mirrors the in-browser accept gate).
            round_best = self.scorer.select_best(round_candidates)
            if round_best is not None and self.best_metrics is not None \
                    and self.scorer.score(round_best) > self.scorer.score(self.best_metrics):
                self.best_id = round_best.iteration_id
                self.best_metrics = round_best
                self._baseline_node = session_store.read_iteration_full(
                    self.session_id, round_best.iteration_id) or self._baseline_node
                self._baseline_index = self._resolve_index(self._baseline_node)
                self._append_activity(
                    "auto-run",
                    f"Kept new best (score {self.scorer.score(round_best):+.4f}).",
                    iteration_id=round_best.iteration_id,
                )

            self.budget = self.budget.with_wall_clock(self._clock() - self._start_monotonic)
            self._save_auto_run()

            # Regenerate a fresh suggestion batch for the next round, unless we
            # are about to terminate (avoids a wasted LLM call past the cap).
            terminating = (
                self.budget.exceeded()
                or self._stop_requested()
                or (has_targets(cfg.targets) and self.best_metrics is not None
                    and targets_satisfied(cfg.targets, self.best_metrics))
            )
            if not terminating:
                self._baseline_node["insights"] = await self._insights(self._baseline_node)
                session_store.write_iteration(
                    self.session_id, self._baseline_index, self._baseline_node)

    # ---- iteration creation -------------------------------------------------

    async def _create_iteration(self, *, prompt: str, previous_script_code: Optional[str],
                                parent_id: Optional[str], wfv_enabled: bool):
        """Generate + backtest one iteration. Returns (node, wf_result) or None
        on a generation/backtest failure (logged, non-fatal)."""
        gen_result = await self._generate(prompt, previous_script_code)
        if gen_result.validation_errors and not gen_result.script_code:
            self._append_activity(
                "error", f"Strategy generation failed: {gen_result.validation_errors[:1]}")
            return None
        result, errors, rating, _timings, wf_result = await self._backtest(
            gen_result, wfv_enabled=wfv_enabled)
        if result is None:
            self._append_activity("error", f"Backtest failed: {(errors or ['unknown'])[:1]}")
            return None

        iteration_id = _new_id()
        node = self._build_node(
            iteration_id=iteration_id,
            prompt=prompt,
            gen_result=gen_result,
            result=result,
            rating=rating,
            wf_result=wf_result,
            parent_id=parent_id,
            insights=None,
        )
        return node, wf_result

    def _persist_new(self, node: dict) -> int:
        """Allocate the next index, persist the node, return the index used."""
        index = self._next_index
        self._next_index += 1
        session_store.write_iteration(self.session_id, index, node)
        return index

    def _resolve_index(self, node: dict) -> int:
        """Resolve the on-disk index for an already-persisted node by id."""
        for d in session_store.list_iteration_dirs(self.session_id):
            parts = d.name.split("_", 1)
            if len(parts) == 2 and parts[1] == node["id"]:
                return int(parts[0])
        return self._baseline_index

    # ---- terminal transition ------------------------------------------------

    def _finish(self, status: str, reason: str) -> None:
        self.status = status
        self.stop_reason = reason
        self.ended_at = _now_iso()
        self._append_activity(
            "complete",
            f"Automated session finished: {reason}"
            + (f" (best score {self.scorer.score(self.best_metrics):+.4f})"
               if self.best_metrics is not None else ""),
            iteration_id=self.best_id,
        )
        self._save_auto_run()


# =============================================================================
# Startup reconciliation
# =============================================================================

def reconcile_orphaned_sessions() -> list[str]:
    """Mark any auto-session left ``running``/``queued`` (orphaned by a worker
    restart — the in-memory task handle did not survive) as terminal
    ``interrupted`` so no session is stuck "running" forever.

    Returns the list of reconciled session ids.
    """
    reconciled: list[str] = []
    try:
        tabs = session_store.derive_session_tabs()
    except Exception:  # pragma: no cover - store may be uninitialized
        return reconciled
    for tab in tabs:
        sid = tab.get("id")
        if not sid:
            continue
        meta = session_store.read_session_meta(sid) or {}
        auto_run = meta.get("autoRun")
        if not isinstance(auto_run, dict):
            continue
        if auto_run.get("status") in ACTIVE_STATUSES:
            updated = {
                **auto_run,
                "status": STATUS_INTERRUPTED,
                "stopReason": STATUS_INTERRUPTED,
                "endedAt": _now_iso(),
            }
            session_store.write_session_meta(sid, {"autoRun": updated})
            reconciled.append(sid)
            logger.info("auto-session %s reconciled running→interrupted on startup", sid)
    return reconciled
