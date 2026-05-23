"""Unit + controller tests for backend/auto_session.py (Layer-1 Foundation).

Hermetic: a deterministic injected FakePipeline replaces the live LLM/backtest
steps so the loop is testable cheaply.  A real on-disk temp store is used (no
store mocking), matching the style of test_session_store.py / test_session_routes.py.

Covers the iter-1 anti-goals:
  * robust-best (WFE-gated + min-trades floor + drawdown-penalized)
  * hard budget (immutable tracker; never starts a round past the cap)
  * same-artifacts (loop-produced iterations byte-shape-compatible with a manual run)
  * persisted-status (autoRun round-trips through session.json; orphan reconciliation)
And the J-09 terminal/best-marking journey.
"""

import asyncio
import dataclasses

import pytest

import backend.auto_session as auto_session_mod
import backend.session_store as ss
from backend.auto_session import (
    AutoSessionController,
    BudgetTracker,
    IterationMetrics,
    RobustScorer,
    has_targets,
    is_terminal,
    reconcile_orphaned_sessions,
    targets_satisfied,
)
from backend.result_serialization import rating_to_dict, result_to_dict
from tests.auto_session_helpers import (
    FakePipeline,
    FakeSpec,
    build_config,
    make_backtest_result,
    make_rating,
)


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Redirect the file store to a temp dir (resolved at call time)."""
    monkeypatch.setattr(ss, "BASE_DIR", tmp_path / "store")
    ss.initialize()
    return ss


# =============================================================================
# BudgetTracker — immutable, hard caps
# =============================================================================

def test_budget_tracker_is_frozen():
    b = BudgetTracker(max_iterations=2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        b.iterations_done = 5  # type: ignore[misc]


def test_with_round_completed_returns_new_instance():
    b = BudgetTracker(max_iterations=3)
    b2 = b.with_round_completed()
    assert b.iterations_done == 0          # original unchanged (no in-place mutation)
    assert b2.iterations_done == 1
    assert b2 is not b


def test_budget_exceeded_on_iterations():
    assert BudgetTracker(max_iterations=2, iterations_done=1).exceeded() is False
    assert BudgetTracker(max_iterations=2, iterations_done=2).exceeded() is True
    assert BudgetTracker(max_iterations=2, iterations_done=3).exceeded() is True


def test_budget_exceeded_on_wall_clock():
    b = BudgetTracker(max_iterations=99, max_wall_clock_sec=10.0)
    assert b.with_wall_clock(9.9).exceeded() is False
    assert b.with_wall_clock(10.0).exceeded() is True
    # No wall-clock cap → never wall-clock-exceeded.
    assert BudgetTracker(max_iterations=99).with_wall_clock(1e9).exceeded() is False


def test_budget_to_dict_shape():
    d = BudgetTracker(max_iterations=2, iterations_done=1, wall_clock_sec=1.2345,
                      max_wall_clock_sec=60.0, tokens=5, usd=0.01).to_dict()
    assert d == {
        "iterationsDone": 1,
        "maxIterations": 2,
        "wallClockSec": 1.234,   # rounded to 3dp
        "maxWallClockSec": 60.0,
        "tokens": 5,
        "usd": 0.01,
    }


# =============================================================================
# RobustScorer — ported in-browser scoring + WFE gate + dd penalty
# =============================================================================

def test_score_matches_inbrowser_formula():
    # base = (total_return + max(0,sharpe)*0.05) * min(1, 0.5 + n/100)
    #        - dd_penalty_weight * max_drawdown
    s = RobustScorer(dd_penalty_weight=0.5)
    m = IterationMetrics("i", total_return=0.2, sharpe=2.0, num_trades=10, max_drawdown=0.1)
    # freq = 0.6 ; sharpe_bonus = 0.1 ; base = (0.2+0.1)*0.6 = 0.18 ; -0.5*0.1 = 0.13
    assert s.score(m) == pytest.approx(0.13)


def test_score_zero_trades_is_negative_infinity():
    s = RobustScorer()
    m = IterationMetrics("i", total_return=5.0, sharpe=3.0, num_trades=0, max_drawdown=0.0)
    assert s.score(m) == float("-inf")
    assert s.is_eligible(m) is False


def test_negative_sharpe_gives_no_bonus():
    s = RobustScorer(dd_penalty_weight=0.0)
    m = IterationMetrics("i", total_return=0.1, sharpe=-3.0, num_trades=100, max_drawdown=0.0)
    # freq=1.0, sharpe_bonus=0 → base = 0.1
    assert s.score(m) == pytest.approx(0.1)


def test_drawdown_penalty_lowers_score():
    s = RobustScorer(dd_penalty_weight=0.5)
    low_dd = IterationMetrics("a", 0.2, 1.0, 50, max_drawdown=0.05)
    high_dd = IterationMetrics("b", 0.2, 1.0, 50, max_drawdown=0.40)
    assert s.score(low_dd) > s.score(high_dd)


def test_wfe_gate_eligibility():
    s = RobustScorer(wf_accept_threshold=0.3)
    assert s.is_eligible(IterationMetrics("a", 0.2, 1.0, 10, 0.1, wfe=0.29)) is False
    assert s.is_eligible(IterationMetrics("b", 0.2, 1.0, 10, 0.1, wfe=0.30)) is True
    # No WFV ran (wfe None) → gate does not reject.
    assert s.is_eligible(IterationMetrics("c", 0.2, 1.0, 10, 0.1, wfe=None)) is True


def test_margin_called_is_ineligible():
    s = RobustScorer()
    assert s.is_eligible(
        IterationMetrics("a", 5.0, 3.0, 50, 0.1, margin_called=True, wfe=0.9)) is False


def test_select_best_excludes_wfe_failing_high_return():
    """Robust-best anti-goal: a higher raw-return but WFE-failing candidate is
    NOT selected; a lower-return WFE-passing one is."""
    s = RobustScorer(wf_accept_threshold=0.3)
    high_return_wfe_fail = IterationMetrics("A", total_return=0.9, sharpe=1.0,
                                            num_trades=10, max_drawdown=0.1, wfe=0.1)
    lower_return_eligible = IterationMetrics("B", total_return=0.2, sharpe=1.0,
                                             num_trades=10, max_drawdown=0.1, wfe=0.6)
    best = s.select_best([high_return_wfe_fail, lower_return_eligible])
    assert best is not None and best.iteration_id == "B"


def test_select_best_none_when_all_ineligible():
    s = RobustScorer()
    assert s.select_best([IterationMetrics("a", 0.5, 1.0, 0, 0.1)]) is None


# =============================================================================
# targets_satisfied
# =============================================================================

def test_targets_absent_is_not_satisfied():
    assert has_targets({}) is False
    assert has_targets(None) is False
    assert targets_satisfied({}, IterationMetrics("i", 5.0, 5.0, 99, 0.0, wfe=0.9)) is False


def test_targets_all_supplied_satisfied():
    t = {"min_total_return": 0.1, "min_sharpe": 1.0, "max_drawdown": 0.3,
         "min_trades": 5, "min_wfe": 0.3}
    m = IterationMetrics("i", total_return=0.2, sharpe=1.5, num_trades=20,
                         max_drawdown=0.2, wfe=0.5)
    assert targets_satisfied(t, m) is True


def test_targets_one_unmet_fails():
    t = {"min_total_return": 0.5}
    m = IterationMetrics("i", total_return=0.2, sharpe=1.5, num_trades=20, max_drawdown=0.2)
    assert targets_satisfied(t, m) is False


def test_targets_min_wfe_unsatisfiable_without_wfe():
    t = {"min_wfe": 0.3}
    m = IterationMetrics("i", total_return=0.2, sharpe=1.5, num_trades=20,
                         max_drawdown=0.2, wfe=None)
    assert targets_satisfied(t, m) is False


# =============================================================================
# Controller — J-09 terminal + best marking
# =============================================================================

async def test_criteria_met_when_baseline_satisfies_targets(store):
    cfg = build_config(targets={"min_total_return": 0.0})
    fake = FakePipeline(sequence=[FakeSpec(total_return=0.5, num_trades=10)])
    ctrl = AutoSessionController("auto-cm", cfg, BudgetTracker(max_iterations=3), fake)

    auto_run = await ctrl.run()

    assert auto_run["status"] == "criteria-met"
    assert auto_run["stopReason"] == "criteria-met"
    assert auto_run["budget"]["iterationsDone"] == 0          # met before any round
    assert auto_run["endedAt"] is not None
    # Best is marked and satisfies the supplied target.
    best = ss.read_iteration_full("auto-cm", auto_run["bestIterationId"])
    assert best is not None
    assert best["result"]["total_return"] >= 0.0
    # Baseline ran a plain backtest (no walk-forward).
    assert fake.execute_calls[0]["wfv_enabled"] is False


async def test_budget_exhausted_runs_exactly_max_iterations(store):
    cfg = build_config(targets={})  # no targets → run to budget
    seq = [
        FakeSpec(total_return=0.1, num_trades=10, wfe=0.6),  # baseline
        FakeSpec(total_return=0.2, num_trades=10, wfe=0.6),  # round 1 candidate
        FakeSpec(total_return=0.3, num_trades=10, wfe=0.6),  # round 2 candidate
    ]
    fake = FakePipeline(sequence=seq, suggestions_per_round=1)
    ctrl = AutoSessionController("auto-be", cfg, BudgetTracker(max_iterations=2), fake)

    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"
    assert auto_run["stopReason"] == "budget-exhausted"
    # Hard budget: exactly max_iterations rounds, no "one more round".
    assert auto_run["budget"]["iterationsDone"] == 2
    # baseline + 2 candidates = 3 iterations; nothing appended past the cap.
    assert len(ss.list_iteration_dirs("auto-be")) == 3
    assert len(fake.execute_calls) == 3
    # Candidate backtests ran walk-forward (for the WFE gate); baseline did not.
    assert [c["wfv_enabled"] for c in fake.execute_calls] == [False, True, True]
    # Best advanced to the strongest (eligible) candidate.
    best = ss.read_iteration_full("auto-be", auto_run["bestIterationId"])
    assert best["result"]["total_return"] == pytest.approx(0.3)


async def test_best_is_wfe_gated_not_highest_raw_return(store):
    """Robust-best anti-goal end-to-end: a higher raw-return but WFE-failing
    candidate is persisted (browsable) but NOT marked best."""
    cfg = build_config(targets={})
    seq = [
        FakeSpec(total_return=0.1, num_trades=10, wfe=0.6),  # baseline (eligible)
        FakeSpec(total_return=0.9, num_trades=10, wfe=0.1),  # candidate A: high return, WFE fail
        FakeSpec(total_return=0.2, num_trades=10, wfe=0.6),  # candidate B: lower, eligible
    ]
    fake = FakePipeline(sequence=seq, suggestions_per_round=2)
    ctrl = AutoSessionController("auto-rb", cfg, BudgetTracker(max_iterations=1), fake)

    auto_run = await ctrl.run()

    best = ss.read_iteration_full("auto-rb", auto_run["bestIterationId"])
    assert best["result"]["total_return"] == pytest.approx(0.2)   # B, not A
    # All three candidates were persisted (no parallel store, browsable history).
    returns = sorted(
        ss.read_iteration_full("auto-rb", d.name.split("_", 1)[1])["result"]["total_return"]
        for d in ss.list_iteration_dirs("auto-rb")
    )
    assert returns == pytest.approx([0.1, 0.2, 0.9])


# =============================================================================
# Controller — same-artifacts anti-goal
# =============================================================================

async def test_artifacts_are_byte_shape_compatible_with_manual_run(store):
    cfg = build_config(targets={})
    baseline_spec = FakeSpec(total_return=0.1, sharpe=1.0, num_trades=5, max_drawdown=0.1, wfe=0.6)
    fake = FakePipeline(sequence=[baseline_spec, FakeSpec(total_return=0.2, num_trades=5, wfe=0.6)],
                        suggestions_per_round=1, with_rating=True)
    ctrl = AutoSessionController("auto-art", cfg, BudgetTracker(max_iterations=1), fake)

    await ctrl.run()

    dirs = ss.list_iteration_dirs("auto-art")
    baseline_id = dirs[0].name.split("_", 1)[1]
    baseline = ss.read_iteration_full("auto-art", baseline_id)

    # result/rating round-trip through the per-iteration endpoint shape, and are
    # byte-identical to the canonical serializer the manual SSE path uses.
    assert baseline["result"] == result_to_dict(
        make_backtest_result(run_id="scr-1", total_return=0.1, sharpe=1.0,
                             num_trades=5, max_drawdown=0.1))
    assert baseline["rating"] == rating_to_dict(make_rating())
    # Trade rows carry the v0.7/v0.8 additive fields (execute-backtest shape).
    assert baseline["result"]["trades"][0]["direction"] == "long"
    assert "margin" in baseline["result"]["trades"][0]
    # Lightweight summary fields the UI tree needs.
    assert baseline["totalReturn"] == pytest.approx(0.1)
    assert baseline["numTrades"] == 5
    assert baseline["params"]["symbol"] == "BTC/USDT"
    # Insights (suggestions) present on the baseline; activity log written.
    assert baseline["insights"]["suggestions"]
    activity = ss.read_activity_log("auto-art")
    assert any(e["type"] == "user-prompt" for e in activity)
    assert any(e["type"] == "complete" for e in activity)


async def test_no_secrets_in_artifacts(store):
    cfg = build_config(targets={})
    fake = FakePipeline(sequence=[FakeSpec()], suggestions_per_round=1)
    ctrl = AutoSessionController("auto-sec", cfg, BudgetTracker(max_iterations=1), fake)
    await ctrl.run()

    meta = ss.read_session_meta("auto-sec")
    activity = ss.read_activity_log("auto-sec")
    blob = repr(meta) + repr(activity)
    for needle in ("api_key", "apiKey", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "sk-"):
        assert needle not in blob


# =============================================================================
# Controller — persisted-status anti-goal + reconciliation
# =============================================================================

async def test_auto_run_status_round_trips_through_session_json(store):
    cfg = build_config(targets={"min_total_return": 0.0})
    fake = FakePipeline(sequence=[FakeSpec(total_return=0.3, num_trades=8)])
    ctrl = AutoSessionController("auto-rt", cfg, BudgetTracker(max_iterations=2), fake)
    auto_run = await ctrl.run()

    # A fresh store read (simulated worker restart) still shows the persisted status.
    meta = ss.read_session_meta("auto-rt")
    assert meta["autoRun"]["status"] == auto_run["status"]
    assert is_terminal(meta["autoRun"]["status"])
    assert meta["autoRun"]["bestIterationId"] == auto_run["bestIterationId"]
    assert meta["autoRun"]["budget"]["maxIterations"] == 2


def test_reconcile_orphaned_running_to_interrupted(store):
    # Orphaned in-flight run (worker died mid-run).
    ss.write_session_meta("orphan", {
        "name": "Orphan",
        "autoRun": {"status": "running", "stopReason": None, "stopRequested": False,
                    "bestIterationId": "i1", "budget": {}, "startedAt": "t0", "endedAt": None},
    })
    # A queued one also reconciles.
    ss.write_session_meta("queued", {
        "name": "Queued",
        "autoRun": {"status": "queued", "stopReason": None, "stopRequested": False,
                    "bestIterationId": None, "budget": {}, "startedAt": "t0", "endedAt": None},
    })
    # A finished auto-session and a plain manual session must be left alone.
    ss.write_session_meta("done", {"name": "Done", "autoRun": {"status": "criteria-met"}})
    ss.write_session_meta("manual", {"name": "Manual"})

    reconciled = reconcile_orphaned_sessions()

    assert set(reconciled) == {"orphan", "queued"}
    assert ss.read_session_meta("orphan")["autoRun"]["status"] == "interrupted"
    assert ss.read_session_meta("orphan")["autoRun"]["stopReason"] == "interrupted"
    assert ss.read_session_meta("queued")["autoRun"]["status"] == "interrupted"
    assert ss.read_session_meta("done")["autoRun"]["status"] == "criteria-met"   # untouched
    assert ss.read_session_meta("manual").get("autoRun") is None


# =============================================================================
# Controller — stop infrastructure (J-11 cancellation primitive)
# =============================================================================

async def test_stop_request_transitions_to_stopped_keeping_best(store):
    sid = "auto-stop"
    cfg = build_config(targets={})

    def request_stop_after_baseline(call_index: int) -> None:
        if call_index == 1:  # right after the baseline backtest
            meta = ss.read_session_meta(sid) or {}
            auto_run = dict(meta.get("autoRun", {}))
            auto_run["stopRequested"] = True
            ss.write_session_meta(sid, {"autoRun": auto_run})

    seq = [FakeSpec(total_return=0.1, num_trades=10, wfe=0.6)] + \
          [FakeSpec(total_return=0.9, num_trades=10, wfe=0.6)] * 5
    fake = FakePipeline(sequence=seq, suggestions_per_round=1,
                        on_exec=request_stop_after_baseline)
    ctrl = AutoSessionController(sid, cfg, BudgetTracker(max_iterations=5), fake)

    auto_run = await ctrl.run()

    assert auto_run["status"] == "stopped"
    assert auto_run["stopReason"] == "stopped"
    assert auto_run["bestIterationId"] is not None          # best-so-far retained
    # No iterations appended after the stop (only the baseline ran).
    assert len(ss.list_iteration_dirs(sid)) == 1
    assert len(fake.execute_calls) == 1


# =============================================================================
# B1+B2 co-design regression — a /stop racing a controller _save_auto_run must
# NOT be dropped once the autoRun store I/O moves off the event loop.
# =============================================================================

async def test_stop_racing_save_auto_run_is_not_dropped(store, monkeypatch):
    """B1 (off-loop autoRun I/O) and B2 (single-writer serialization) are ONE
    design.  This forces the exact TOCTOU the iter-1 lesson warned about: a
    ``/stop`` issued while the controller is between its autoRun READ and WRITE.

    The controller's ``_save_auto_run`` and the competing stop share the SAME
    per-session ``asyncio.Lock``.  Holding it across the off-loop read+write means
    the stop must queue behind the controller's RMW instead of interleaving into
    it — so the persisted ``stopRequested=True`` is preserved (not clobbered) and
    the loop reaches ``stopped`` retaining the best-so-far.

    (Verified during development that REMOVING the shared lock — leaving only the
    off-loop ``to_thread`` — drops the stop and the loop runs to
    ``budget-exhausted``, which is precisely the regression this guards.)
    """
    sid = "auto-race"
    cfg = build_config(targets={})
    lock = asyncio.Lock()

    # The competing /stop, mirroring stop_auto_session's locked RMW (shares `lock`).
    async def fire_stop():
        async with lock:
            meta = await asyncio.to_thread(ss.read_session_meta, sid)
            auto_run = dict((meta or {}).get("autoRun", {}))
            auto_run["stopRequested"] = True
            await asyncio.to_thread(ss.write_session_meta, sid, {"autoRun": auto_run})

    armed = {"on": True}
    real_off_loop = auto_session_mod._run_off_loop

    async def racing_off_loop(fn, *args):
        result = await real_off_loop(fn, *args)
        # Fire the race exactly once, right after the controller's first autoRun
        # READ — i.e. inside _save_auto_run, before its WRITE, while it holds the
        # shared lock. The stop must wait for the lock here; without it, the stop
        # would complete now and the controller's stale write would clobber it.
        if armed["on"] and fn is ss.read_session_meta:
            armed["on"] = False
            asyncio.ensure_future(fire_stop())
            await asyncio.sleep(0.05)  # let fire_stop reach (and block on) the lock
        return result

    monkeypatch.setattr(auto_session_mod, "_run_off_loop", racing_off_loop)

    fake = FakePipeline(
        sequence=[FakeSpec(total_return=0.1, num_trades=10, wfe=0.6)] * 8,
        suggestions_per_round=1,
    )
    ctrl = AutoSessionController(
        sid, cfg, BudgetTracker(max_iterations=5), fake, auto_run_lock=lock,
    )

    auto_run = await ctrl.run()

    # The concurrent stop was honored, not dropped.
    assert auto_run["status"] == "stopped"
    assert auto_run["stopReason"] == "stopped"
    assert ss.read_session_meta(sid)["autoRun"]["stopRequested"] is True
    # Best-so-far retained; loop stopped at its first checkpoint (only baseline ran).
    assert auto_run["bestIterationId"] is not None
    assert len(ss.list_iteration_dirs(sid)) == 1
