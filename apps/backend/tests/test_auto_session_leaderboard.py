"""J-16 — robust-objective overfit-gating leaderboard (the final journey).

Hermetic controller + route tests for the per-candidate ``autoRun.leaderboard``
the open-universe loop now serves, and the bounded optional ``promote_k`` knob
that makes the WFE-gating demonstrable with real promoted candidates.

The binding J-16 assertion (``test_overfit_gating_higher_return_wfe_fail_not_best``):
a higher-raw-return / higher-robust-score but WFE-failing candidate sits in the
leaderboard with ``eligible: False`` and a gating reason citing WFE, and is NOT
the marked best — the lower-return, WFE-passing candidate is. The leaderboard
reads the ONE canonical ``RobustScorer`` (no second scorer, no FE recompute) and
marks best solely by the one ``bestIterationId``.

Coherence guardrails enforced here:
  * ``robustScore`` equals ``RobustScorer.score(metrics)`` for that candidate.
  * no second ``best`` field — best is ``entry.iterationId == bestIterationId``.
  * one row per family (a promoted family shows its PROMOTE node, not both).
  * the leaderboard rides ``autoRun`` (persisted, reload-survivable) and the
    open/list path does NOT eager-parse ``result.json`` to build it.
  * ``promote_k`` omitted ⇒ byte-identical to today (J-12/J-13/J-14 locked).
"""

import pytest
from fastapi.testclient import TestClient

import backend.session_store as ss
from backend.auto_session import (
    WF_ACCEPT_THRESHOLD,
    AutoSessionController,
    BudgetTracker,
    IterationMetrics,
    RobustScorer,
    _json_safe_score,
)
from tests.auto_session_helpers import FakePipeline, FakeSpec, build_config


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Redirect the file store to a temp dir (resolved at call time)."""
    monkeypatch.setattr(ss, "BASE_DIR", tmp_path / "store")
    ss.initialize()
    return ss


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ou_config(**overrides):
    """A base open-universe config (no pinned symbol/timeframe)."""
    base = dict(symbol=None, timeframe=None, natural_language="")
    base.update(overrides)
    return build_config(**base)


def _metrics_from_node(node: dict) -> IterationMetrics:
    """Rebuild the metrics the robust scorer reads off a persisted node — the
    SAME values the controller used, so a recompute must match verbatim."""
    wf = node.get("walkForwardResult") or {}
    wfe = wf.get("wfe") if isinstance(wf, dict) else None
    return IterationMetrics(
        iteration_id=node["id"],
        total_return=float(node["totalReturn"]),
        sharpe=float(node["sharpe"]),
        num_trades=int(node["numTrades"]),
        max_drawdown=float(node["maxDrawdown"]),
        margin_called=bool((node.get("result") or {}).get("margin_called", False)),
        wfe=(float(wfe) if wfe is not None else None),
    )


def _read_nodes(sid: str) -> dict:
    """All persisted nodes keyed by iteration id."""
    return {
        d.name.split("_", 1)[1]: ss.read_iteration_full(sid, d.name.split("_", 1)[1])
        for d in ss.list_iteration_dirs(sid)
    }


def _entries_by_family(auto_run: dict, nodes_by_id: dict) -> dict:
    """Map each leaderboard entry to its (symbol, timeframe) family via the node
    it points at — proving the FE join key (iterationId → iterationHistory) is
    sound and that the leaderboard carries NO duplicated display metric."""
    out = {}
    for e in auto_run["leaderboard"]:
        n = nodes_by_id[e["iterationId"]]
        out[(n["params"]["symbol"], n["params"]["timeframe"])] = (e, n)
    return out


# =============================================================================
# canonical-score: every leaderboard score IS the one RobustScorer's output
# =============================================================================

async def test_leaderboard_scores_are_the_canonical_robust_score(store):
    cfg = _ou_config()
    seq = [
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05),  # screen 1
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05),  # screen 2
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),  # promo
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController("lb-canon", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)

    auto_run = await ctrl.run()

    lb = auto_run["leaderboard"]
    assert lb, "leaderboard must be populated after an open-universe run"
    nodes_by_id = _read_nodes("lb-canon")
    canonical = RobustScorer()
    for e in lb:
        node = nodes_by_id[e["iterationId"]]
        expected = _json_safe_score(canonical.score(_metrics_from_node(node)))
        assert e["robustScore"] == expected, e
        # eligibility is also the one scorer's verbatim output.
        assert e["eligible"] == canonical.is_eligible(_metrics_from_node(node))


# =============================================================================
# overfit-gating — THE binding J-16 assertion
# =============================================================================

async def test_overfit_gating_higher_return_wfe_fail_not_best(store):
    """With promote_k=2, two candidates reach walk-forward: A (higher raw return,
    higher robust score) FAILS the WFE gate; B (lower return) passes. The marked
    best is B; A sits in the leaderboard with eligible:false and a WFE gating
    reason — a flashier candidate visibly rejected. (The third seed config is
    screened-only and never promoted, so k=2 < n_screened=3.)"""
    cfg = _ou_config(promote_k=2)
    # SCREEN (seed order BTC/1h, ETH/1h, BTC/4h), ranked by robust score; then
    # PROMOTE the top-2 survivors in screen-score order: A then B.
    seq = [
        FakeSpec(total_return=0.9, sharpe=1.0, num_trades=10, max_drawdown=0.05),  # A top screen
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05),  # B 2nd
        FakeSpec(total_return=0.1, sharpe=1.0, num_trades=10, max_drawdown=0.05),  # C screen-only
        FakeSpec(total_return=0.9, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.10),  # A
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.60),  # B
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController("lb-overfit", cfg, BudgetTracker(max_iterations=9, max_configs=3),
                                 fake, open_universe=True)

    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"
    nodes_by_id = _read_nodes("lb-overfit")
    fam = _entries_by_family(auto_run, nodes_by_id)
    # One row per family (dedup): exactly 3 families, 3 entries (not 5 nodes).
    assert len(auto_run["leaderboard"]) == 3
    assert set(fam) == {("BTC/USDT", "1h"), ("ETH/USDT", "1h"), ("BTC/USDT", "4h")}

    a_entry, a_node = fam[("BTC/USDT", "1h")]
    b_entry, b_node = fam[("ETH/USDT", "1h")]
    c_entry, c_node = fam[("BTC/USDT", "4h")]

    # Best is B (lower return, WFE-passing) — the ONE bestIterationId.
    assert auto_run["bestIterationId"] == b_entry["iterationId"]
    assert b_node["result"]["total_return"] == pytest.approx(0.3)
    assert b_node["walkForwardStatus"] == "complete"
    assert b_entry["stage"] == "promote"
    assert b_entry["eligible"] is True
    assert b_entry["gatingReason"] == "best"

    # A (higher return AND higher robust score) is promoted but WFE-failing →
    # eligible:false, gating reason cites WFE, and it is NOT best.
    assert a_node["result"]["total_return"] == pytest.approx(0.9)
    assert a_node["walkForwardStatus"] == "complete"        # promote node (dedup)
    assert a_entry["stage"] == "promote"
    assert a_entry["eligible"] is False
    assert "WFE" in a_entry["gatingReason"]
    assert a_entry["iterationId"] != auto_run["bestIterationId"]
    # The overfit-gating made visible: A outranks B by robust score yet is not best.
    assert a_entry["robustScore"] > b_entry["robustScore"]

    # C never promoted → appears as its SCREEN node, no WFE.
    assert c_entry["stage"] == "screen"
    assert c_node["walkForwardStatus"] is None
    assert "screened" in c_entry["gatingReason"].lower()


async def test_overfit_gating_over_leveraged_not_best(store):
    """Over-leverage variant: a high-return candidate that blew up (margin called)
    is ineligible — gating reason cites over-leverage — and is not best."""
    cfg = _ou_config(promote_k=2)
    seq = [
        FakeSpec(total_return=0.9, sharpe=1.0, num_trades=10, max_drawdown=0.05),  # A top screen
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05),  # B
        FakeSpec(total_return=0.1, sharpe=1.0, num_trades=10, max_drawdown=0.05),  # C screen-only
        # A promote: passes WFE but margin-called → ineligible (over-leveraged).
        FakeSpec(total_return=0.9, sharpe=1.0, num_trades=10, max_drawdown=0.05,
                 wfe=0.60, margin_called=True),
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.60),  # B
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController("lb-lever", cfg, BudgetTracker(max_iterations=9, max_configs=3),
                                 fake, open_universe=True)

    auto_run = await ctrl.run()

    nodes_by_id = _read_nodes("lb-lever")
    fam = _entries_by_family(auto_run, nodes_by_id)
    a_entry, _ = fam[("BTC/USDT", "1h")]
    b_entry, _ = fam[("ETH/USDT", "1h")]

    assert auto_run["bestIterationId"] == b_entry["iterationId"]
    assert a_entry["eligible"] is False
    reason = a_entry["gatingReason"].lower()
    assert "leverage" in reason or "margin" in reason
    assert a_entry["iterationId"] != auto_run["bestIterationId"]


# =============================================================================
# gating-reason correctness (each branch of the ONE is_eligible outcome)
# =============================================================================

def test_gating_reason_matches_eligibility_outcome(store):
    cfg = _ou_config()
    ctrl = AutoSessionController("g", cfg, BudgetTracker(max_iterations=1),
                                 FakePipeline(sequence=[FakeSpec()]), open_universe=True)
    ctrl.best_id = "BEST"

    # best — the marked best.
    assert ctrl._gating_reason(
        IterationMetrics("BEST", 0.2, 1.0, 10, 0.1, wfe=0.6),
        stage="promote", iteration_id="BEST") == "best"
    # WFE-fail.
    r = ctrl._gating_reason(IterationMetrics("x", 0.2, 1.0, 10, 0.1, wfe=0.21),
                            stage="promote", iteration_id="x")
    assert "WFE" in r and "0.21" in r and f"{WF_ACCEPT_THRESHOLD:.2f}" in r
    # margin-called (over-leveraged) takes priority over a passing WFE.
    assert "leverage" in ctrl._gating_reason(
        IterationMetrics("x", 0.2, 1.0, 10, 0.1, margin_called=True, wfe=0.9),
        stage="promote", iteration_id="x").lower()
    # below-trades-floor.
    assert "0 trades" == ctrl._gating_reason(
        IterationMetrics("x", 0.2, 1.0, 0, 0.1), stage="screen", iteration_id="x")
    # screened-only (eligible, but never walk-forward validated).
    assert "screened" in ctrl._gating_reason(
        IterationMetrics("x", 0.2, 1.0, 10, 0.1, wfe=None),
        stage="screen", iteration_id="x").lower()
    # eligible promoted, but not the top score.
    assert ctrl._gating_reason(
        IterationMetrics("x", 0.2, 1.0, 10, 0.1, wfe=0.6),
        stage="promote", iteration_id="x") == "lower robust score"


# =============================================================================
# best == bestIterationId — no separate best field is served
# =============================================================================

async def test_best_marked_solely_by_best_iteration_id(store):
    cfg = _ou_config(promote_k=2)
    seq = [
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.1, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController("lb-bestid", cfg, BudgetTracker(max_iterations=9, max_configs=3),
                                 fake, open_universe=True)

    auto_run = await ctrl.run()

    lb = auto_run["leaderboard"]
    best_id = auto_run["bestIterationId"]
    # Exactly one entry is the best, identified ONLY by iterationId; the entry
    # carries no separate "best" field (the FE marks best by id, never a 2nd flag).
    marked = [e for e in lb if e["iterationId"] == best_id]
    assert len(marked) == 1
    assert marked[0]["gatingReason"] == "best"
    assert all("best" not in e for e in lb)  # no boolean best field on any entry
    # The marked best is the WFE-gated select_best result.
    best_node = ss.read_iteration_full("lb-bestid", best_id)
    assert best_node["walkForwardStatus"] == "complete"
    assert RobustScorer().is_eligible(_metrics_from_node(best_node)) is True


# =============================================================================
# no-regression lock — default promote_k keeps J-12/J-14 byte-identical
# =============================================================================

async def test_default_promote_k_preserves_screen_promote_pattern(store):
    """promote_k omitted ⇒ default 1: the SCREEN→PROMOTE wfv pattern and marked
    best are unchanged from HEAD, and a leaderboard is now additionally served
    (screened-only families + the one promoted family, deduped)."""
    cfg = _ou_config()  # no promote_k → DEFAULT_PROMOTE_K (1)
    seq = [
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.1, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController("lb-default", cfg, BudgetTracker(max_iterations=9, max_configs=3),
                                 fake, open_universe=True)

    auto_run = await ctrl.run()

    # Unchanged behavior: 3 SCREEN (no WF) + exactly 1 PROMOTE (WF) → k=1<3.
    assert [c["wfv_enabled"] for c in fake.execute_calls] == [False, False, False, True]
    best = ss.read_iteration_full("lb-default", auto_run["bestIterationId"])
    assert best["result"]["total_return"] == pytest.approx(0.5)
    assert best["walkForwardStatus"] == "complete"
    # New surface: a leaderboard with one row per family (2 screened-only + 1
    # promoted = 3 families), deduped (the promoted family's screen node is gone).
    lb = auto_run["leaderboard"]
    assert len(lb) == 3
    promote_rows = [e for e in lb if e["stage"] == "promote"]
    screen_rows = [e for e in lb if e["stage"] == "screen"]
    assert len(promote_rows) == 1
    assert len(screen_rows) == 2
    assert promote_rows[0]["iterationId"] == auto_run["bestIterationId"]


async def test_promote_k_two_promotes_two_of_three(store):
    """promote_k=2 with 3 screened ⇒ k=min(2,3)=2 promoted (two WF backtests),
    k<n_screened preserved."""
    cfg = _ou_config(promote_k=2)
    seq = [
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.4, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.1, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
        FakeSpec(total_return=0.4, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController("lb-k2", cfg, BudgetTracker(max_iterations=9, max_configs=3),
                                 fake, open_universe=True)

    auto_run = await ctrl.run()

    # 3 SCREEN + 2 PROMOTE → two WF backtests (k=2 < n_screened=3).
    assert [c["wfv_enabled"] for c in fake.execute_calls] == [False, False, False, True, True]
    lb = auto_run["leaderboard"]
    promote_rows = [e for e in lb if e["stage"] == "promote"]
    assert len(promote_rows) == 2
    assert len(lb) == 3   # 2 promoted families + 1 screened-only


# =============================================================================
# promote_k still budget-gated mid-promote (cost cap halts even with k>=2)
# =============================================================================

async def test_promote_k_cost_cap_halts_mid_promote(store):
    """A token cap still halts PROMOTE between survivors even when promote_k=2 —
    the per-promote cost gate is preserved."""
    from shared.model_catalog import TokenUsage
    cfg = _ou_config(promote_k=2)
    usage = TokenUsage(input_tokens=600, output_tokens=400, model="gpt-5.4-mini")  # 1000/generate
    seq = [
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.4, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.1, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
        FakeSpec(total_return=0.4, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
    ]
    fake = FakePipeline(sequence=seq, usage=usage)
    # 3 SCREEN = 3000 tokens; cap 3500 → promote1 (→4000) runs, promote2 gate halts.
    budget = BudgetTracker(max_iterations=99, max_configs=3, max_tokens=3500)
    ctrl = AutoSessionController("lb-cost", cfg, budget, fake, open_universe=True)

    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"
    # Only one PROMOTE backtest ran (the second halted at its cost checkpoint).
    assert sum(1 for c in fake.execute_calls if c["wfv_enabled"]) == 1
    best = ss.read_iteration_full("lb-cost", auto_run["bestIterationId"])
    assert best["result"]["total_return"] == pytest.approx(0.5)
    assert best["walkForwardStatus"] == "complete"


# =============================================================================
# terminal-with-zero-candidates → empty leaderboard, no crash
# =============================================================================

async def test_all_configs_fail_yields_empty_leaderboard(store):
    cfg = _ou_config()
    fake = FakePipeline(sequence=[FakeSpec(), FakeSpec()], fail_exec_indices={1, 2})
    ctrl = AutoSessionController("lb-empty", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)

    auto_run = await ctrl.run()

    assert auto_run["status"] == "budget-exhausted"
    assert auto_run["bestIterationId"] is None
    assert auto_run["leaderboard"] == []   # empty placeholder, no crash


# =============================================================================
# persistence + reload survival; no eager parse on the open path
# =============================================================================

async def test_leaderboard_persists_and_survives_reload(store):
    cfg = _ou_config(promote_k=2)
    seq = [
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.1, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController("lb-reload", cfg, BudgetTracker(max_iterations=9, max_configs=3),
                                 fake, open_universe=True)

    auto_run = await ctrl.run()

    # A fresh store read (simulated worker restart) shows the persisted leaderboard.
    meta = ss.read_session_meta("lb-reload")
    assert meta["autoRun"]["leaderboard"] == auto_run["leaderboard"]
    assert len(meta["autoRun"]["leaderboard"]) == 3


def test_get_session_serves_leaderboard_without_eager_parse(store, monkeypatch):
    """GET /api/sessions/{id} returns ``autoRun.leaderboard`` (built from in-memory
    metrics, persisted on the autoRun block) and the lightweight join targets in
    ``iterationHistory`` — WITHOUT eager-parsing any iteration's heavy result.json
    (the open-path anti-goal). read_iteration_full is monkeypatched to explode as a
    tripwire; the route uses read_iteration_meta only, so it must not fire."""
    sid = "lb-noeager"
    ss.write_session_meta(sid, {
        "name": "Auto · open-universe search",
        "autoRun": {
            "status": "budget-exhausted", "stopReason": "budget-exhausted",
            "stopRequested": False, "bestIterationId": "itB",
            "budget": {}, "startedAt": "t0", "endedAt": "t1",
            "leaderboard": [
                {"iterationId": "itA", "stage": "promote", "robustScore": 0.545,
                 "eligible": False, "gatingReason": "WFE 0.10 < 0.30"},
                {"iterationId": "itB", "stage": "promote", "robustScore": 0.185,
                 "eligible": True, "gatingReason": "best"},
            ],
        },
    })
    ss.write_iteration(sid, 1, {"id": "itA", "status": "complete",
                                "params": {"symbol": "BTC/USDT", "timeframe": "1h"},
                                "totalReturn": 0.9, "sharpe": 1.0, "numTrades": 10,
                                "maxDrawdown": 0.05,
                                "walkForwardResult": {"wfe": 0.1}, "walkForwardStatus": "complete"})
    ss.write_iteration(sid, 2, {"id": "itB", "status": "complete",
                                "params": {"symbol": "ETH/USDT", "timeframe": "1h"},
                                "totalReturn": 0.3, "sharpe": 1.0, "numTrades": 10,
                                "maxDrawdown": 0.05,
                                "walkForwardResult": {"wfe": 0.6}, "walkForwardStatus": "complete"})

    def _boom(*a, **k):
        raise AssertionError("open path eager-parsed a full iteration payload")

    monkeypatch.setattr(ss, "read_iteration_full", _boom)

    from backend.api import app
    with TestClient(app) as client:
        sess = client.get(f"/api/sessions/{sid}").json()

    lb = sess["autoRun"]["leaderboard"]
    assert [e["iterationId"] for e in lb] == ["itA", "itB"]
    assert sess["autoRun"]["bestIterationId"] == "itB"
    # FE join: display metrics live on the lightweight iterationHistory node, NOT
    # duplicated into the leaderboard entry (no heavy result payload served).
    by_id = {n["id"]: n for n in sess["iterationHistory"]}
    assert by_id["itA"]["walkForwardResult"]["wfe"] == 0.1
    assert by_id["itA"]["totalReturn"] == 0.9
    assert by_id["itA"].get("result") is None     # lightweight: no eager result.json
    for e in lb:                                   # no duplicated display metric on the entry
        assert "totalReturn" not in e and "wfe" not in e and "symbol" not in e


# =============================================================================
# no secrets in the leaderboard / gating strings
# =============================================================================

async def test_no_secrets_in_leaderboard(store):
    cfg = _ou_config(promote_k=2)
    seq = [
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05),
        FakeSpec(total_return=0.5, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.6),
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController("lb-sec", cfg, BudgetTracker(max_iterations=9, max_configs=2),
                                 fake, open_universe=True)
    auto_run = await ctrl.run()

    blob = repr(auto_run["leaderboard"])
    for needle in ("api_key", "apiKey", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "sk-"):
        assert needle not in blob
