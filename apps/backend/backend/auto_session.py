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
import hashlib
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
from shared.model_catalog import DEFAULT_MODEL, TokenUsage, cheapest_model, cost_usd

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

# ---- Bounded seed universe (J-12 open-universe search) ----------------------
# An EXPLICIT, hard-capped set the open-universe search enumerates a
# budget-bounded subset of.  Anti-goal: the search MUST start from this bounded
# seed and MUST NOT enumerate the full ``/api/symbols`` list or fan out
# exchange-wide.  Small + liquid on purpose; expansion is a future (history-
# justified) journey, not iter-3.
SEED_SYMBOLS: tuple[str, ...] = ("BTC/USDT", "ETH/USDT")
SEED_TIMEFRAMES: tuple[str, ...] = ("1h", "4h")
SEED_STRATEGY_IDEAS: tuple[str, ...] = (
    "Buy when RSI crosses below 30, sell when it crosses above 70",
    "Go long on a fast/slow EMA bullish crossover; exit on the bearish crossover",
)
# Hard ceiling on how many distinct configs the search may EVER enumerate,
# regardless of budget — a structural guard against exchange-wide fan-out.
SEED_UNIVERSE_MAX: int = len(SEED_SYMBOLS) * len(SEED_TIMEFRAMES)

# ---- Staged SCREEN→PROMOTE cost-tiering (J-14) ------------------------------
# How many top-scoring SCREEN survivors are escalated (PROMOTEd) to full
# evaluation (walk-forward + the stronger model). Kept deliberately small: cheap
# SCREEN triages breadth, PROMOTE spends the expensive budget on the few best.
# Whenever ≥2 configs are screened, the effective k = min(DEFAULT_PROMOTE_K,
# n_screened) MUST stay < n_screened (the cost-tiering invariant).
DEFAULT_PROMOTE_K: int = 1

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

    ALL caps are hard-enforced as of iter-3 (J-13): ``max_iterations``
    (pinned improvement rounds), ``max_configs`` (open-universe configs),
    ``max_wall_clock_sec``, ``max_tokens``, and ``max_usd``.  :meth:`exceeded`
    is checked *before* each unit of work so the loop never starts "one more"
    past a cap.  Token / USD spend is threaded from real LLM SDK usage via
    :meth:`with_usage`.  "Incrementing" returns a NEW instance (frozen — never
    mutated in place).
    """

    max_iterations: int
    iterations_done: int = 0
    max_configs: Optional[int] = None
    configs_done: int = 0
    wall_clock_sec: float = 0.0
    max_wall_clock_sec: Optional[float] = None
    tokens: int = 0
    max_tokens: Optional[int] = None
    usd: float = 0.0
    max_usd: Optional[float] = None

    def with_round_completed(self) -> "BudgetTracker":
        """Return a copy with one more improvement round counted (pinned path)."""
        return replace(self, iterations_done=self.iterations_done + 1)

    def with_config_completed(self) -> "BudgetTracker":
        """Return a copy with one more explored config counted (open-universe)."""
        return replace(self, configs_done=self.configs_done + 1)

    def with_wall_clock(self, wall_clock_sec: float) -> "BudgetTracker":
        """Return a copy with the elapsed wall-clock recorded."""
        return replace(self, wall_clock_sec=wall_clock_sec)

    def with_usage(self, *, tokens: int = 0, usd: float = 0.0) -> "BudgetTracker":
        """Return a copy with token/USD usage accumulated (real SDK usage)."""
        return replace(self, tokens=self.tokens + tokens, usd=self.usd + usd)

    def exceeded(self) -> bool:
        """True when ANY hard-enforced cap is reached.

        Checked *before* each unit of work (round / config) so the loop never
        starts one past a cap.  An unset (``None``) cap is not enforced; the
        pinned path always has ``max_iterations`` and the open-universe path
        always has ``max_configs``.
        """
        if self.iterations_done >= self.max_iterations:
            return True
        if self.max_configs is not None and self.configs_done >= self.max_configs:
            return True
        if self.max_wall_clock_sec is not None and self.wall_clock_sec >= self.max_wall_clock_sec:
            return True
        if self.max_tokens is not None and self.tokens >= self.max_tokens:
            return True
        if self.max_usd is not None and self.usd >= self.max_usd:
            return True
        return False

    def cost_exceeded(self) -> bool:
        """True when a COST cap (tokens / USD / wall-clock) is reached — the
        subset of :meth:`exceeded` that bounds a PROMOTE refinement unit (J-14).

        Deliberately does NOT check ``max_configs`` / ``max_iterations``: the
        open-universe SCREEN stage fills ``configs_done`` up to ``max_configs``
        (its breadth cap), so reusing the full :meth:`exceeded` would wrongly skip
        every PROMOTE. Promotion is a bounded escalation of already-counted
        configs, gated only on real spend (the hard token/USD/wall-clock caps).
        ``exceeded`` itself is left unchanged (the J-13 tests depend on it)."""
        if self.max_wall_clock_sec is not None and self.wall_clock_sec >= self.max_wall_clock_sec:
            return True
        if self.max_tokens is not None and self.tokens >= self.max_tokens:
            return True
        if self.max_usd is not None and self.usd >= self.max_usd:
            return True
        return False

    def to_dict(self) -> dict:
        """Serialize for the ``autoRun.budget`` block (one canonical counter set —
        the UI status strip and API read these same values, never separate tallies)."""
        return {
            "iterationsDone": self.iterations_done,
            "maxIterations": self.max_iterations,
            "configsDone": self.configs_done,
            "maxConfigs": self.max_configs,
            "wallClockSec": round(self.wall_clock_sec, 3),
            "maxWallClockSec": self.max_wall_clock_sec,
            "tokens": self.tokens,
            "maxTokens": self.max_tokens,
            "usd": round(self.usd, 6),
            "maxUsd": self.max_usd,
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


def seed_universe_configs(
    base: AutoSessionConfig, max_configs: Optional[int]
) -> list[AutoSessionConfig]:
    """Enumerate distinct ``(symbol, timeframe)`` configs from the bounded seed
    universe, in a deterministic order whose first entries differ in symbol so a
    2-config run yields two genuinely distinct configs.

    If ``base`` pins a strategy idea (non-empty ``natural_language``) every
    config reuses it and only symbol/timeframe vary; otherwise seed ideas are
    drawn round-robin.  The list is capped by BOTH ``max_configs`` and the hard
    :data:`SEED_UNIVERSE_MAX` — it is NEVER the full ``/api/symbols`` list.
    """
    pinned_idea = (base.natural_language or "").strip()
    # Vary symbol fastest so config[0] and config[1] differ in symbol.
    grid: list[tuple[str, str]] = [
        (sym, tf) for tf in SEED_TIMEFRAMES for sym in SEED_SYMBOLS
    ]
    limit = SEED_UNIVERSE_MAX
    if max_configs is not None:
        limit = min(limit, max_configs)
    configs: list[AutoSessionConfig] = []
    for idx, (sym, tf) in enumerate(grid[:limit]):
        idea = pinned_idea or SEED_STRATEGY_IDEAS[idx % len(SEED_STRATEGY_IDEAS)]
        configs.append(replace(base, symbol=sym, timeframe=tf, natural_language=idea))
    return configs


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


async def _run_off_loop(fn, *args):
    """Run a blocking ``session_store`` call in a worker thread so the headless
    loop never blocks the API event loop (anti-goal B1: the background job must
    not block the loop; the UI poll / other requests stay responsive while a run
    is active).

    Centralizing the off-loop hop here — rather than scattering ``to_thread`` —
    keeps the ``autoRun`` read-modify-write a single critical section that
    :meth:`AutoSessionController._save_auto_run` wraps in the shared per-session
    lock (B1 and B2 are co-designed; see that method).
    """
    return await asyncio.to_thread(fn, *args)


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
        auto_run_lock: Optional[asyncio.Lock] = None,
        clock: Callable[[], float] = time.monotonic,
        open_universe: bool = False,
    ) -> None:
        self.session_id = session_id
        self.config = config
        self.budget = budget
        self.pipeline = pipeline
        self.open_universe = open_universe
        self.scorer = scorer or RobustScorer()
        self.semaphore = semaphore or asyncio.Semaphore(1)
        # Per-session lock serializing every ``autoRun`` read-modify-write against
        # a concurrent ``/stop`` (B2).  The production route passes the SAME lock
        # to ``stop_auto_session``; a standalone controller (tests) gets its own.
        self._lock = auto_run_lock or asyncio.Lock()
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
        # Code-hash dedup: never re-backtest an identical generated strategy on
        # identical params (anti-goal). Keyed on (code hash, symbol, timeframe,
        # dates, leverage, allow_short, wfv); the OHLCV Parquet cache is reused
        # automatically by the shared pipeline loader (no re-fetch when covered).
        self._backtest_cache: dict[str, tuple] = {}

    # ---- persistence helpers ------------------------------------------------

    async def _save_auto_run(self) -> dict:
        """Persist the current autoRun block to session.json OFF the event loop,
        PRESERVING an externally-set ``stopRequested`` flag (the /stop endpoint
        owns it).

        **B1+B2 co-design.** The whole read-modify-write runs under the
        per-session ``self._lock`` (shared with :func:`stop_auto_session`).  That
        is what lets the blocking I/O move off-loop via :func:`_run_off_loop`
        safely: without the lock, the ``await`` between this read and write would
        let a concurrent ``/stop`` interleave and its ``stopRequested=True`` would
        be clobbered by our stale read (the TOCTOU the iter-1 lesson warned
        about).  ``write_session_meta`` top-level-merges but REPLACES the whole
        ``autoRun`` dict, so the lock — not disjoint keys — is the correctness
        guarantee here.
        """
        async with self._lock:
            meta = await _run_off_loop(session_store.read_session_meta, self.session_id)
            persisted = (meta or {}).get("autoRun", {})
            auto_run = {
                "status": self.status,
                "stopReason": self.stop_reason,
                "stopRequested": bool(persisted.get("stopRequested", False)),
                "bestIterationId": self.best_id,
                "budget": self.budget.to_dict(),
                "startedAt": self.started_at,
                "endedAt": self.ended_at,
            }
            await _run_off_loop(
                session_store.write_session_meta, self.session_id, {"autoRun": auto_run})
        return auto_run

    async def _stop_requested(self) -> bool:
        """Read the persisted stop flag under the shared lock (a torn read while
        ``/stop`` writes would otherwise mask a real stop request)."""
        async with self._lock:
            meta = await _run_off_loop(session_store.read_session_meta, self.session_id)
        return bool((meta or {}).get("autoRun", {}).get("stopRequested", False))

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

    def _account_usage(self, usage: Optional[TokenUsage]) -> None:
        """Thread one LLM call's real token usage into the immutable budget.

        Maps tokens→USD via the model-catalog rate table (single source of
        truth) and accumulates on a NEW tracker instance (frozen — never mutated
        in place). ``None`` (no LLM call / cache hit) is a no-op."""
        if usage is None:
            return
        self.budget = self.budget.with_usage(
            tokens=usage.total_tokens,
            usd=cost_usd(usage.model, usage.input_tokens, usage.output_tokens),
        )

    # ---- node construction --------------------------------------------------

    def _build_node(self, config: AutoSessionConfig, *, iteration_id: str, prompt: str,
                    gen_result, result, rating, wf_result, parent_id: Optional[str],
                    insights: Optional[dict]) -> dict:
        """Assemble an IterationNode dict byte-shape-compatible with a manual run.

        ``config`` carries this iteration's params (the pinned config, or one
        open-universe seed config) — each card already renders its own
        ``params`` symbol/timeframe, so distinct open-universe configs surface
        through the existing iteration cards with no schema fork."""
        return {
            "id": iteration_id,
            "prompt": prompt,
            "scriptCode": gen_result.script_code,
            "scriptId": gen_result.script_id,
            "strategyName": gen_result.strategy_name,
            "status": "complete",
            "timestamp": _now_iso(),
            "params": config.backtest_params(),
            "parentId": parent_id,
            "totalReturn": result.total_return,
            "winRate": result.win_rate,
            "numTrades": result.num_trades,
            "sharpe": result.sharpe_ratio,
            "maxDrawdown": min(1.0, float(result.max_drawdown)),
            "modelUsed": gen_result.model_used or config.model,
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

    async def _generate(self, config: AutoSessionConfig, prompt: str,
                        previous_script_code: Optional[str]):
        return await self.pipeline.generate_strategy(
            natural_language=prompt,
            model=config.model,
            previous_script_code=previous_script_code,
            symbol=config.symbol,
            timeframe=config.timeframe,
            start_date=config.start_date,
            end_date=config.end_date,
            allow_short=config.allow_short,
            leverage=config.leverage,
        )

    @staticmethod
    def _backtest_cache_key(config: AutoSessionConfig, script_code: str, wfv_enabled: bool) -> str:
        """Identity of an exact backtest: generated code hash + the params that
        affect its result. Two configs with identical code AND identical params
        share a result (anti-goal: never re-backtest an identical strategy)."""
        code_hash = hashlib.sha256((script_code or "").encode("utf-8")).hexdigest()[:16]
        return (f"{code_hash}:{config.symbol}:{config.timeframe}:{config.start_date}:"
                f"{config.end_date}:{config.leverage}:{config.allow_short}:{int(wfv_enabled)}")

    async def _backtest(self, config: AutoSessionConfig, gen_result, *, wfv_enabled: bool):
        """Run a backtest (reusing the pipeline). Acquires the shared
        one-backtest-per-worker semaphore so the event loop stays responsive.

        An identical generated strategy on identical params is served from the
        per-session dedup cache instead of being re-backtested; the OHLCV Parquet
        cache is reused automatically by the shared pipeline loader (no re-fetch
        when a covering cache exists)."""
        key = self._backtest_cache_key(config, gen_result.script_code, wfv_enabled)
        cached = self._backtest_cache.get(key)
        if cached is not None:
            return cached
        start_dt = _to_datetime(config.start_date, end_of_day=False)
        end_dt = _to_datetime(config.end_date, end_of_day=True)
        async with self.semaphore:
            outcome = await self.pipeline.execute_backtest(
                script_id=gen_result.script_id,
                symbol=config.symbol,
                timeframe=config.timeframe,
                start_date=start_dt,
                end_date=end_dt,
                initial_capital=config.initial_capital,
                commission=config.commission,
                script_code=gen_result.script_code,
                strategy_name=gen_result.strategy_name,
                strategy_description=gen_result.strategy_description,
                allow_short=config.allow_short,
                leverage=config.leverage,
                wfv_enabled=wfv_enabled,
                wfv_is_months=config.wfv_is_months,
                wfv_oos_months=config.wfv_oos_months,
            )
        self._backtest_cache[key] = outcome
        return outcome

    async def _insights(self, config: AutoSessionConfig, node: dict) -> Optional[dict]:
        """Generate insights (summary + suggestions) for an iteration node."""
        try:
            summary, suggestions, errors = await self.pipeline.generate_insights(
                backtest_result=node.get("result") or {},
                strategy_name=node.get("strategyName", ""),
                strategy_description="",
                script_code=node.get("scriptCode", ""),
                natural_language_prompt=node.get("prompt", ""),
                model=config.model,
                symbol=config.symbol,
                timeframe=config.timeframe,
                start_date=config.start_date,
                end_date=config.end_date,
                allow_short=config.allow_short,
                leverage=config.leverage,
                initial_capital=config.initial_capital,
                walk_forward_result=node.get("walkForwardResult"),
            )
            self._account_usage(getattr(self.pipeline, "last_insights_usage", None))
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
            if self.open_universe:
                await self._run_open_universe()
            else:
                await self._run_inner()
        except Exception as exc:  # pragma: no cover - defensive; surfaced on store
            logger.exception("auto-session %s crashed: %s", self.session_id, exc)
            self.status = STATUS_ERROR
            self.stop_reason = STATUS_ERROR
            self.ended_at = _now_iso()
            self._append_activity("error", f"Automated session failed: {exc}")
        return await self._save_auto_run()

    async def _run_inner(self) -> None:
        cfg = self.config
        self.status = STATUS_RUNNING
        await self._save_auto_run()
        self._append_activity("user-prompt", cfg.natural_language)

        # ---- Step 0: baseline iteration (generate → backtest → rating → insights)
        baseline = await self._create_iteration(
            self.config,
            prompt=cfg.natural_language,
            previous_script_code=None,
            parent_id=None,
            wfv_enabled=False,
        )
        if baseline is None:
            # Baseline could not be produced (e.g., generation/backtest error).
            await self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
            return

        node, wf_result = baseline
        self._baseline_node = node
        # Best-so-far starts at the baseline (the only iteration).
        self.best_id = node["id"]
        self.best_metrics = self._metrics_from(node, wf_result)
        node["insights"] = await self._insights(self.config, node)
        self._baseline_index = self._persist_new(node)
        await self._save_auto_run()

        # ---- Improvement rounds (hard-bounded by budget) ------------------
        while True:
            self.budget = self.budget.with_wall_clock(self._clock() - self._start_monotonic)

            # Terminal checks, in priority order.
            if has_targets(cfg.targets) and self.best_metrics is not None \
                    and targets_satisfied(cfg.targets, self.best_metrics):
                await self._finish(STATUS_CRITERIA_MET, "criteria-met")
                return
            if self.budget.exceeded():
                await self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
                return
            if await self._stop_requested():
                await self._finish(STATUS_STOPPED, "stopped")
                return

            suggestions = [
                s for s in (self._baseline_node.get("insights") or {}).get("suggestions", [])
                if not s.get("disabled")
            ]
            if not suggestions:
                # No remaining suggestions — documented budget-exhausted variant.
                await self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
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
                    self.config,
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
            await self._save_auto_run()

            # Regenerate a fresh suggestion batch for the next round, unless we
            # are about to terminate (avoids a wasted LLM call past the cap).
            terminating = (
                self.budget.exceeded()
                or await self._stop_requested()
                or (has_targets(cfg.targets) and self.best_metrics is not None
                    and targets_satisfied(cfg.targets, self.best_metrics))
            )
            if not terminating:
                self._baseline_node["insights"] = await self._insights(
                    self.config, self._baseline_node)
                session_store.write_iteration(
                    self.session_id, self._baseline_index, self._baseline_node)

    # ---- open-universe loop (J-12) ------------------------------------------

    async def _run_open_universe(self) -> None:
        """Staged SCREEN→PROMOTE cost-tiering over the bounded seed universe (J-14).

        Stage 1 — **SCREEN** (cheap): evaluate the budget-bounded seed configs on
        the *cheapest* catalog model (:func:`cheapest_model`) with **no
        walk-forward**.  Stage 2 — **PROMOTE** (expensive): re-evaluate only the
        top-``k`` SCREEN survivors (``k = min(DEFAULT_PROMOTE_K, n_screened)``,
        and ``k < n_screened`` whenever ≥2 were screened) on the *stronger*
        request model **with** walk-forward.  The cross-config best is marked from
        the **PROMOTED** candidates only (they alone carry real WFE) — screened-
        only nodes are NEVER eligible, preserving the WFE-gated-best anti-goal.

        Orchestration ONLY — it computes no new metric: every unit is evaluated
        through the SAME ``BacktestPipeline`` + ``RobustScorer`` and persisted via
        the SAME ``session_store.write_iteration`` (no parallel store, no schema
        fork), so distinct configs surface through the existing iteration cards
        and the screen→promote lineage shows in the tree (promoted node's
        ``parentId`` is its screened candidate).  Budget: ``max_configs`` is the
        SCREEN-breadth cap (the full :meth:`BudgetTracker.exceeded` gates each
        SCREEN unit); PROMOTE is a bounded refinement gated on the cost caps only
        (:meth:`BudgetTracker.cost_exceeded`) so it is not skipped once SCREEN has
        filled ``configs_done``.  B1+B2 preserved: the ``autoRun`` read-modify-
        write stays under the shared per-session lock and store I/O stays
        off-loop; backtests stay semaphore-guarded inside ``_create_iteration``.
        """
        base = self.config
        screen_model = cheapest_model()      # SCREEN tier — single source of truth
        promote_model = base.model           # PROMOTE tier — the request (full-eval) model
        self.status = STATUS_RUNNING
        await self._save_auto_run()
        if (base.natural_language or "").strip():
            self._append_activity("user-prompt", base.natural_language)

        seed_configs = seed_universe_configs(base, self.budget.max_configs)

        # ---- Stage 1: SCREEN (cheapest model, no walk-forward) ---------------
        self._append_activity(
            "auto-run",
            f"SCREEN — screening {len(seed_configs)} seed config(s) on "
            f"{screen_model}, no walk-forward.",
        )
        screened: list[tuple[dict, IterationMetrics, AutoSessionConfig]] = []
        for seed_cfg in seed_configs:
            self.budget = self.budget.with_wall_clock(self._clock() - self._start_monotonic)
            if self.budget.exceeded():
                await self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
                return
            if await self._stop_requested():
                await self._finish(STATUS_STOPPED, "stopped")
                return

            screen_cfg = replace(seed_cfg, model=screen_model)
            created = await self._create_iteration(
                screen_cfg,
                prompt=screen_cfg.natural_language,
                previous_script_code=None,
                parent_id=None,
                wfv_enabled=False,   # SCREEN is cheap: no walk-forward
            )
            # A config counts as SCREENED whether or not it produced a result — a
            # failed attempt still consumed a unit of work (non-fatal; continue).
            self.budget = self.budget.with_config_completed()

            if created is not None:
                node, wf = created   # wf is None — SCREEN runs no walk-forward
                self._persist_new(node)
                m = self._metrics_from(node, wf)
                screened.append((node, m, screen_cfg))
                self._append_activity(
                    "auto-run",
                    f"SCREEN — {screen_cfg.symbol} {screen_cfg.timeframe}: "
                    f"score {self.scorer.score(m):+.4f}",
                    iteration_id=node["id"],
                )

            self.budget = self.budget.with_wall_clock(self._clock() - self._start_monotonic)
            await self._save_auto_run()

        # A stop requested during the final SCREEN unit is honored before PROMOTE.
        if await self._stop_requested():
            await self._finish(STATUS_STOPPED, "stopped")
            return
        if not screened:
            # Nothing survived SCREEN → clean terminal, no PROMOTE, no WFE-gated best.
            await self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
            return

        # ---- Rank SCREEN survivors by the canonical score; take the top-k -----
        n_screened = len(screened)
        k = min(DEFAULT_PROMOTE_K, n_screened)
        order = sorted(
            range(n_screened),
            key=lambda i: (-self.scorer.score(screened[i][1]), i),   # ties → seed order
        )
        survivors = [screened[i] for i in order[:k]]

        # ---- Stage 2: PROMOTE (stronger model + walk-forward), best from these -
        self._append_activity(
            "auto-run",
            f"PROMOTE — escalating top-{k} of {n_screened} to {promote_model} "
            f"+ walk-forward.",
        )
        promoted: list[IterationMetrics] = []
        for screen_node, _screen_m, screen_cfg in survivors:
            self.budget = self.budget.with_wall_clock(self._clock() - self._start_monotonic)
            # PROMOTE is gated on the COST caps only (SCREEN may already have filled
            # configs_done to max_configs); a token/USD/wall-clock cap still halts it.
            if self.budget.cost_exceeded():
                await self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")
                return
            if await self._stop_requested():
                await self._finish(STATUS_STOPPED, "stopped")
                return

            promote_cfg = replace(screen_cfg, model=promote_model)
            created = await self._create_iteration(
                promote_cfg,
                prompt=promote_cfg.natural_language,
                previous_script_code=None,
                parent_id=screen_node["id"],   # screen→promote lineage in the tree
                wfv_enabled=True,              # PROMOTE runs walk-forward
            )
            if created is not None:
                node, wf = created
                self._persist_new(node)
                promoted.append(self._metrics_from(node, wf))
                # Best is selected from PROMOTED candidates ONLY (WFE-gated).
                best = self.scorer.select_best(promoted)
                if best is not None and best.iteration_id != self.best_id:
                    self.best_id = best.iteration_id
                    self.best_metrics = best
                    self._append_activity(
                        "auto-run",
                        f"PROMOTE — {promote_cfg.symbol} {promote_cfg.timeframe} "
                        f"is the new best (WFE-gated, score "
                        f"{self.scorer.score(best):+.4f}).",
                        iteration_id=best.iteration_id,
                    )

            self.budget = self.budget.with_wall_clock(self._clock() - self._start_monotonic)
            await self._save_auto_run()

        # Both stages complete within budget → terminal.
        if await self._stop_requested():
            await self._finish(STATUS_STOPPED, "stopped")
            return
        await self._finish(STATUS_BUDGET_EXHAUSTED, "budget-exhausted")

    # ---- iteration creation -------------------------------------------------

    async def _create_iteration(self, config: AutoSessionConfig, *, prompt: str,
                                previous_script_code: Optional[str],
                                parent_id: Optional[str], wfv_enabled: bool):
        """Evaluate ONE config: generate → backtest (→ walk-forward). Returns
        (node, wf_result) or None on a generation/backtest failure (logged,
        non-fatal). The single reusable per-config evaluation unit — the pinned
        improvement-rounds loop and the open-universe search both call it, and
        J-14 can wrap it in cheap-SCREEN/PROMOTE stages later without a rewrite.

        Real strategy-generation token usage is threaded into the budget right
        after the generate call (J-13)."""
        gen_result = await self._generate(config, prompt, previous_script_code)
        self._account_usage(getattr(self.pipeline, "last_strategy_usage", None))
        if gen_result.validation_errors and not gen_result.script_code:
            self._append_activity(
                "error", f"Strategy generation failed: {gen_result.validation_errors[:1]}")
            return None
        result, errors, rating, _timings, wf_result = await self._backtest(
            config, gen_result, wfv_enabled=wfv_enabled)
        if result is None:
            self._append_activity("error", f"Backtest failed: {(errors or ['unknown'])[:1]}")
            return None

        iteration_id = _new_id()
        node = self._build_node(
            config,
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

    async def _finish(self, status: str, reason: str) -> None:
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
        await self._save_auto_run()


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
