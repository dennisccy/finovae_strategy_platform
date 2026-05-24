"""J-15 — global-history warm start for the open-universe search (opt-out-able).

Hermetic: a deterministic fake planner is injected via the same ``FakePipeline``
the controller already accepts (no live LLM). The canonical journey is:

  * Run #1 — ``this-run``/default open-universe, tiny budget — seeds prior families.
  * Run #2 — ``history_scope="global"`` — MUST warm-start: emit ONE planner-decision
    Activity-Log entry citing run #1's performance, and screen + promote the
    historically-strongest in-seed family FIRST.
  * Run #3 — ``history_scope="this-run"`` — MUST NOT cite cross-run history
    (opt-out honored); the SCREEN ordering + promotion ranking stay byte-equivalent
    to today's deterministic behavior.

Read-only mining is verified by a before/after artifact-unchanged assertion.
The planner is asserted invoked ≤ once per run, threaded into the budget (J-13),
non-fatal on failure, and the search never leaves the bounded seed universe.
"""

from __future__ import annotations

import pytest

import backend.auto_session as auto_session_mod
import backend.session_store as ss
from backend.auto_session import (
    SEED_SYMBOLS,
    SEED_TIMEFRAMES,
    SEED_UNIVERSE_MAX,
    AutoSessionConfig,
    AutoSessionController,
    BudgetTracker,
    RobustScorer,
    mine_history_families,
)
from shared.model_catalog import TokenUsage
from tests.auto_session_helpers import FakePipeline, FakeSpec, build_config


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Redirect the file store to a temp dir (resolved at call time)."""
    monkeypatch.setattr(ss, "BASE_DIR", tmp_path / "store")
    ss.initialize()
    return ss


def _ou_config(**overrides):
    base = dict(symbol=None, timeframe=None, natural_language="")
    base.update(overrides)
    return build_config(**base)


def _fam(node) -> tuple:
    """The ``(symbol, timeframe)`` family of an iteration node/meta (``params``)
    or a recorded execute-call (``symbol``/``timeframe`` at top level)."""
    p = node.get("params", node)
    return p["symbol"], p["timeframe"]


def _warm_entries(sid: str) -> list:
    """Warm-start planner-decision Activity-Log entries for a session."""
    return [e["content"] for e in ss.read_activity_log(sid)
            if e["type"] == "auto-run" and e["content"].startswith("WARM-START")]


# Specs that make ETH/USDT 1h the historically-strongest family in run #1.
# SCREEN order follows the seed grid (symbol fastest): BTC/USDT 1h, ETH/USDT 1h.
_RUN1_SPECS = [
    FakeSpec(total_return=0.10, max_drawdown=0.05),          # SCREEN BTC/USDT 1h
    FakeSpec(total_return=0.50, max_drawdown=0.05),          # SCREEN ETH/USDT 1h (top)
    FakeSpec(total_return=0.50, max_drawdown=0.05, wfe=0.6),  # PROMOTE ETH/USDT 1h
]


async def _seed_run_one(sid: str = "run1", *, name: str = "Run One") -> str:
    """Drive a this-run open-universe run to terminal, seeding prior families."""
    cfg = _ou_config()
    fake = FakePipeline(sequence=_RUN1_SPECS)
    ctrl = AutoSessionController(sid, cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    await ctrl.run()
    # A route-launched session carries a human name; set it so the citation is legible.
    ss.write_session_meta(sid, {"name": name})
    return sid


# =============================================================================
# Config default — opt-out (this-run) is the default
# =============================================================================

def test_history_scope_defaults_to_this_run():
    """Omitted history_scope resolves to the opt-out value so J-12/J-13/J-14
    hermetic runs (which set no history_scope) keep today's behavior."""
    assert AutoSessionConfig(
        natural_language="x", symbol=None, timeframe=None,
        start_date="2023-01-01", end_date="2023-06-01",
    ).history_scope == "this-run"
    assert build_config().history_scope == "this-run"
    assert _ou_config().history_scope == "this-run"


# =============================================================================
# J-15 acceptance — global warm-start cites prior + promotes the top family first
# =============================================================================

async def test_global_warm_start_cites_prior_and_promotes_top_family(store):
    await _seed_run_one()

    # Run #2: global. The planner (fake) returns the historically-correct order.
    cfg = _ou_config(history_scope="global")
    run2_specs = [
        FakeSpec(total_return=0.50, max_drawdown=0.05),          # SCREEN ETH 1h (first)
        FakeSpec(total_return=0.10, max_drawdown=0.05),          # SCREEN BTC 1h
        FakeSpec(total_return=0.50, max_drawdown=0.05, wfe=0.6),  # PROMOTE ETH 1h
    ]
    fake = FakePipeline(
        sequence=run2_specs,
        planner_order=[("ETH/USDT", "1h"), ("BTC/USDT", "1h")],
        planner_rationale="ETH/USDT 1h had the strongest prior robust score",
    )
    ctrl = AutoSessionController("run2", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"
    # The planner ran exactly once (≤ once per run; leaderboard not re-sent each round).
    assert len(fake.plan_warmstart_calls) == 1

    # ONE warm-start planner-decision Activity-Log entry (existing auto-run type)
    # citing run #1's family + performance.
    warm = _warm_entries("run2")
    assert len(warm) == 1, warm
    content = warm[0]
    assert "ETH/USDT 1h" in content
    assert "robust score" in content
    assert "Run One" in content                       # cites the prior session

    # The FIRST promoted iteration's family equals run #1's top performer (ETH/USDT 1h).
    nodes = [ss.read_iteration_full("run2", d.name.split("_", 1)[1])
             for d in ss.list_iteration_dirs("run2")]
    promoted = [n for n in nodes if n["walkForwardStatus"] == "complete"]
    assert len(promoted) == 1
    assert _fam(promoted[0]) == ("ETH/USDT", "1h")
    # And the bounded seed was respected (no fan-out).
    assert all(n["params"]["symbol"] in set(SEED_SYMBOLS) for n in nodes)
    assert all(n["params"]["timeframe"] in set(SEED_TIMEFRAMES) for n in nodes)


async def test_global_endpoint_layer_activity_log_and_iteration_family(store):
    """Endpoint-shape proof (the canonical surface the UI polls): the warm-start
    entry is visible in the activity log and the first promoted node's family is
    discoverable from per-iteration meta — no full result/rating parse needed."""
    await _seed_run_one(name="Prior Search")
    cfg = _ou_config(history_scope="global")
    fake = FakePipeline(
        sequence=[
            FakeSpec(total_return=0.50, num_trades=10, max_drawdown=0.05),
            FakeSpec(total_return=0.10, num_trades=10, max_drawdown=0.05),
            FakeSpec(total_return=0.50, num_trades=10, max_drawdown=0.05, wfe=0.6),
        ],
        planner_order=[("ETH/USDT", "1h"), ("BTC/USDT", "1h")],
    )
    ctrl = AutoSessionController("run2", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    await ctrl.run()

    # activityLog (read_activity_log == GET /api/sessions/{id}.activityLog) has the citation.
    assert _warm_entries("run2")
    # iterationHistory (read_iteration_meta == GET /api/sessions/{id}.iterationHistory):
    # the first promoted node's family is discoverable from META ONLY.
    metas = [ss.read_iteration_meta("run2", d.name.split("_", 1)[1])
             for d in ss.list_iteration_dirs("run2")]
    promoted = [m for m in metas if m.get("walkForwardStatus") == "complete"]
    assert len(promoted) == 1
    assert _fam(promoted[0]) == ("ETH/USDT", "1h")


# =============================================================================
# Opt-out — this-run (and the omitted default) cite no cross-run history
# =============================================================================

async def test_this_run_opt_out_no_cross_run_citation(store):
    await _seed_run_one()

    cfg = _ou_config(history_scope="this-run")
    fake = FakePipeline(sequence=[
        FakeSpec(total_return=0.10, max_drawdown=0.05),          # SCREEN BTC/USDT 1h (grid order)
        FakeSpec(total_return=0.50, max_drawdown=0.05),          # SCREEN ETH/USDT 1h
        FakeSpec(total_return=0.50, max_drawdown=0.05, wfe=0.6),  # PROMOTE ETH/USDT 1h
    ])
    ctrl = AutoSessionController("run3", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"
    # Opt-out: the planner is never called and NO warm-start entry is emitted.
    assert len(fake.plan_warmstart_calls) == 0
    assert not _warm_entries("run3")
    # SCREEN order is the deterministic seed-grid order (BTC/USDT 1h screened first).
    assert [(c["symbol"], c["timeframe"]) for c in fake.execute_calls[:2]] == [
        ("BTC/USDT", "1h"), ("ETH/USDT", "1h")]


async def test_omitted_history_scope_behaves_byte_equivalent_to_today(store):
    """The omitted default (no field) screens + ranks identically to the current
    deterministic open-universe behavior even when prior history exists (locks in
    J-12/J-14 no-regression)."""
    await _seed_run_one()
    cfg = _ou_config()  # no history_scope → default this-run
    fake = FakePipeline(sequence=[
        FakeSpec(total_return=0.10, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.50, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.50, num_trades=10, max_drawdown=0.05, wfe=0.6),
    ])
    ctrl = AutoSessionController("run3b", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    await ctrl.run()

    assert len(fake.plan_warmstart_calls) == 0
    # SCREEN in grid order; PROMOTE the highest screen score (ETH/USDT 1h, return 0.5).
    assert [(c["symbol"], c["timeframe"]) for c in fake.execute_calls] == [
        ("BTC/USDT", "1h"), ("ETH/USDT", "1h"), ("ETH/USDT", "1h")]
    assert [c["wfv_enabled"] for c in fake.execute_calls] == [False, False, True]


# =============================================================================
# Read-only mining — prior artifacts are byte-identical before/after
# =============================================================================

def _snapshot(root) -> dict:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


async def test_read_only_mining_leaves_prior_artifacts_byte_identical(store):
    run1 = await _seed_run_one()
    before = _snapshot(ss.BASE_DIR / "live" / run1)
    assert before  # sanity: run #1 actually persisted artifacts

    cfg = _ou_config(history_scope="global")
    fake = FakePipeline(
        sequence=[FakeSpec(total_return=0.5, num_trades=10, max_drawdown=0.05),
                  FakeSpec(total_return=0.1, num_trades=10, max_drawdown=0.05),
                  FakeSpec(total_return=0.5, num_trades=10, max_drawdown=0.05, wfe=0.6)],
        planner_order=[("ETH/USDT", "1h"), ("BTC/USDT", "1h")],
    )
    ctrl = AutoSessionController("run2", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    await ctrl.run()

    after = _snapshot(ss.BASE_DIR / "live" / run1)
    assert after == before  # read-only: no prior-session artifact mutated/deleted/added


async def test_mining_is_meta_only_does_not_parse_full_iteration(store, monkeypatch):
    """The miner reads lightweight iteration META only — never the heavy
    result.json/rating.json payload (iter-0 anti-eager-parse lesson)."""
    await _seed_run_one()

    def _boom(*a, **k):
        raise AssertionError("mining must not call read_iteration_full (meta-only)")

    monkeypatch.setattr(ss, "read_iteration_full", _boom)
    families = mine_history_families("run2", RobustScorer())
    assert ("ETH/USDT", "1h") in families
    assert ("BTC/USDT", "1h") in families


def test_mine_history_families_excludes_current_session(store):
    """The in-flight session is never mined into its own warm-start leaderboard."""
    # Hand-write a couple of iteration metas under "self" and "other".
    node = {"id": "n1", "params": {"symbol": "BTC/USDT", "timeframe": "1h"},
            "totalReturn": 0.4, "sharpe": 1.0, "numTrades": 10, "maxDrawdown": 0.05,
            "strategyName": "x", "status": "complete", "walkForwardResult": None}
    ss.write_iteration("self", 1, node)
    ss.write_iteration("other", 1, {**node, "id": "n2"})
    families = mine_history_families("self", RobustScorer())
    assert ("BTC/USDT", "1h") in families
    assert families[("BTC/USDT", "1h")].session_id == "other"   # never "self"


def test_mine_history_families_keeps_max_score_per_family(store):
    """A family's strength is the MAX robust score across its prior iterations."""
    scorer = RobustScorer()
    lo = {"id": "lo", "params": {"symbol": "ETH/USDT", "timeframe": "4h"},
          "totalReturn": 0.10, "sharpe": 1.0, "numTrades": 10, "maxDrawdown": 0.05,
          "status": "complete", "walkForwardResult": None}
    hi = {"id": "hi", "params": {"symbol": "ETH/USDT", "timeframe": "4h"},
          "totalReturn": 0.80, "sharpe": 1.0, "numTrades": 10, "maxDrawdown": 0.05,
          "status": "complete", "walkForwardResult": None}
    ss.write_iteration("prior", 1, lo)
    ss.write_iteration("prior", 2, hi)
    families = mine_history_families("cur", scorer)
    fam = families[("ETH/USDT", "4h")]
    expected = scorer.score(auto_session_mod.IterationMetrics(
        iteration_id="hi", total_return=0.80, sharpe=1.0, num_trades=10, max_drawdown=0.05))
    assert fam.score == pytest.approx(expected)


# =============================================================================
# Planner robustness — best-effort, budgeted, bounded, ≤ once
# =============================================================================

async def test_planner_failure_falls_back_to_deterministic_order(store):
    """On ANY planner failure the run falls back to the deterministic mined-family
    ordering (strongest first), still warm-starts, and reaches a terminal state."""
    await _seed_run_one()
    cfg = _ou_config(history_scope="global")
    fake = FakePipeline(
        sequence=[FakeSpec(total_return=0.5, max_drawdown=0.05),
                  FakeSpec(total_return=0.1, max_drawdown=0.05),
                  FakeSpec(total_return=0.5, max_drawdown=0.05, wfe=0.6)],
        planner_raises=True,
    )
    ctrl = AutoSessionController("run2", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"     # terminal — never crashed
    assert len(fake.plan_warmstart_calls) == 1          # attempted once, then fell back
    # Deterministic fallback still orders ETH/USDT 1h (strongest mined) FIRST.
    assert _fam(fake.execute_calls[0]) == ("ETH/USDT", "1h")
    # Citation still emitted (the deterministic warm-start decision).
    assert _warm_entries("run2")
    promoted = [ss.read_iteration_meta("run2", d.name.split("_", 1)[1])
                for d in ss.list_iteration_dirs("run2")]
    promoted = [m for m in promoted if m.get("walkForwardStatus") == "complete"]
    assert _fam(promoted[0]) == ("ETH/USDT", "1h")


async def test_planner_token_usage_threaded_into_budget(store):
    """J-13: the planner's real token usage accumulates onto the immutable budget."""
    await _seed_run_one()
    cfg = _ou_config(history_scope="global")
    planner_usage = TokenUsage(input_tokens=600, output_tokens=400, model="gpt-5.4-mini")
    fake = FakePipeline(
        sequence=[FakeSpec(total_return=0.5, num_trades=10, max_drawdown=0.05),
                  FakeSpec(total_return=0.1, num_trades=10, max_drawdown=0.05),
                  FakeSpec(total_return=0.5, num_trades=10, max_drawdown=0.05, wfe=0.6)],
        planner_order=[("ETH/USDT", "1h"), ("BTC/USDT", "1h")],
        planner_usage=planner_usage,
        usage=None,  # SCREEN/PROMOTE generates book nothing → budget == planner spend
    )
    ctrl = AutoSessionController("run2", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    auto_run = await ctrl.run()

    from shared.model_catalog import cost_usd
    assert auto_run["budget"]["tokens"] == 1000
    assert auto_run["budget"]["usd"] == pytest.approx(cost_usd("gpt-5.4-mini", 600, 400))


async def test_pre_exhausted_budget_terminates_before_planner_and_screen(store):
    """A pre-exhausted token budget terminates budget-exhausted BEFORE the planner
    AND before SCREEN — no planner call, no iterations (exactly like a pre-exhausted
    SCREEN, J-13)."""
    await _seed_run_one()
    cfg = _ou_config(history_scope="global")
    budget = BudgetTracker(max_iterations=9, max_configs=2, max_tokens=1000).with_usage(tokens=1000)
    assert budget.exceeded()
    fake = FakePipeline(sequence=[FakeSpec(num_trades=10, wfe=0.6)],
                        planner_order=[("ETH/USDT", "1h"), ("BTC/USDT", "1h")])
    ctrl = AutoSessionController("run2", cfg, budget, fake, open_universe=True)
    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"
    assert len(fake.plan_warmstart_calls) == 0          # planner never started past the cap
    assert len(ss.list_iteration_dirs("run2")) == 0     # SCREEN never started
    assert len(fake.execute_calls) == 0


async def test_global_empty_store_degrades_gracefully(store):
    """global with an EMPTY store (no prior sessions): no planner call, no citation,
    deterministic seed ordering, no crash, terminal state reached."""
    cfg = _ou_config(history_scope="global")
    fake = FakePipeline(sequence=[
        FakeSpec(total_return=0.10, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.50, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.50, num_trades=10, max_drawdown=0.05, wfe=0.6),
    ])
    ctrl = AutoSessionController("solo", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"
    assert len(fake.plan_warmstart_calls) == 0
    assert not _warm_entries("solo")
    # Deterministic seed-grid order preserved (BTC/USDT 1h screened first).
    assert [(c["symbol"], c["timeframe"]) for c in fake.execute_calls[:2]] == [
        ("BTC/USDT", "1h"), ("ETH/USDT", "1h")]


async def test_global_run_never_enumerates_outside_seed_universe(store):
    """Warm-start reprioritizes WITHIN the bounded seed; it never fans out beyond
    SEED_UNIVERSE_MAX or enumerates a non-seed (symbol, timeframe)."""
    await _seed_run_one()
    cfg = _ou_config(history_scope="global")
    # Large budget would let it explore the full grid — still bounded by the seed.
    fake = FakePipeline(sequence=[FakeSpec(num_trades=10, max_drawdown=0.05, wfe=0.6)] * 12,
                        planner_order=[("ETH/USDT", "1h"), ("BTC/USDT", "1h")])
    ctrl = AutoSessionController("run2", cfg,
                                 BudgetTracker(max_iterations=99, max_configs=99),
                                 fake, open_universe=True)
    await ctrl.run()

    screened = [c for c in fake.execute_calls if not c["wfv_enabled"]]
    assert len(screened) <= SEED_UNIVERSE_MAX
    seed_set = {(s, t) for s in SEED_SYMBOLS for t in SEED_TIMEFRAMES}
    assert all((c["symbol"], c["timeframe"]) in seed_set for c in fake.execute_calls)


# =============================================================================
# Coherence + secrets
# =============================================================================

async def test_warm_start_uses_single_robust_scorer_instance(store):
    """Coherence: mining scores prior families through the controller's ONE
    canonical RobustScorer — the same instance, no second scoring path."""
    await _seed_run_one()
    cfg = _ou_config(history_scope="global")
    fake = FakePipeline(sequence=[FakeSpec(num_trades=10, max_drawdown=0.05, wfe=0.6)] * 4,
                        planner_order=[("ETH/USDT", "1h"), ("BTC/USDT", "1h")])
    sentinel = RobustScorer()
    ctrl = AutoSessionController("run2", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, scorer=sentinel, open_universe=True)
    await ctrl.run()

    # The controller holds the one scorer it was given (used for both screen
    # ranking and history mining); the leaderboard it produced is consistent.
    assert ctrl.scorer is sentinel
    families = mine_history_families("run2", ctrl.scorer)
    assert ("ETH/USDT", "1h") in families and ("BTC/USDT", "1h") in families


async def test_no_secrets_in_warm_start_artifacts(store):
    await _seed_run_one()
    cfg = _ou_config(history_scope="global")
    fake = FakePipeline(
        sequence=[FakeSpec(total_return=0.5, num_trades=10, max_drawdown=0.05),
                  FakeSpec(total_return=0.1, num_trades=10, max_drawdown=0.05),
                  FakeSpec(total_return=0.5, num_trades=10, max_drawdown=0.05, wfe=0.6)],
        planner_order=[("ETH/USDT", "1h"), ("BTC/USDT", "1h")],
        planner_rationale="ETH/USDT 1h had the strongest prior robust score",
    )
    ctrl = AutoSessionController("run2", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    await ctrl.run()
    blob = repr(ss.read_session_meta("run2")) + repr(ss.read_activity_log("run2"))
    for needle in ("api_key", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "sk-"):
        assert needle not in blob


# =============================================================================
# HistoryPlanner — prompt-cached system prompt (Anthropic path)
# =============================================================================

class _StubMessages:
    def __init__(self, captured, text):
        self._captured = captured
        self._text = text

    def create(self, **kwargs):
        self._captured.update(kwargs)

        class _Usage:
            input_tokens = 12
            output_tokens = 8

        class _Block:
            pass

        block = _Block()
        block.text = self._text

        class _Resp:
            usage = _Usage()
            content = [block]

        return _Resp()


class _StubAnthropic:
    def __init__(self, captured, text):
        self.messages = _StubMessages(captured, text)


def test_history_planner_system_prompt_carries_ephemeral_cache_control():
    """The planner's Anthropic system prompt MUST carry the ephemeral cache_control
    marker (match insights_generator) so the leaderboard/history is prompt-cached
    and never re-sent uncached."""
    from strategy.history_planner import HistoryPlanner

    captured: dict = {}
    text = '{"order": [["ETH/USDT", "1h"], ["BTC/USDT", "1h"]], "rationale": "ETH 1h strongest"}'
    planner = HistoryPlanner(api_key="test-key", model="claude-haiku-4-5")
    planner._client = _StubAnthropic(captured, text)

    order, rationale = planner.plan(
        seed_families=[("BTC/USDT", "1h"), ("ETH/USDT", "1h")],
        history=[{"symbol": "ETH/USDT", "timeframe": "1h", "score": 0.5, "session": "Run One"}],
        model="claude-haiku-4-5",
    )

    assert order == [("ETH/USDT", "1h"), ("BTC/USDT", "1h")]
    assert rationale == "ETH 1h strongest"
    system_blocks = captured["system"]
    assert any(b.get("cache_control") == {"type": "ephemeral"} for b in system_blocks)
    assert planner.last_usage is not None and planner.last_usage.total_tokens == 20


def test_history_planner_malformed_output_raises_for_deterministic_fallback():
    """Malformed planner output raises so the controller falls back to the
    deterministic mined-family ordering (best-effort contract)."""
    from strategy.history_planner import HistoryPlanner

    captured: dict = {}
    planner = HistoryPlanner(api_key="test-key", model="claude-haiku-4-5")
    planner._client = _StubAnthropic(captured, "not json at all")
    with pytest.raises(Exception):
        planner.plan(
            seed_families=[("BTC/USDT", "1h")],
            history=[{"symbol": "BTC/USDT", "timeframe": "1h", "score": 0.1, "session": "s"}],
            model="claude-haiku-4-5",
        )
