"""Tests for the headless auto-session controller (Key Capability #11, L1).

Covers the iter-1 DoD scenarios (a)-(f) + the enumerated error cases, plus
robust-objective unit tests. The LLM + Binance layers are stubbed for
determinism and zero cost; the real live path is exercised by browser-qa
under a tiny budget.

Store handling mirrors test_session_routes.py: a real on-disk temp store via
monkeypatching session_store.BASE_DIR (functions resolve BASE_DIR from the
module global at call time, so both the auto_session controller and the
session routes redirect to the temp dir).
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import backend.session_store as ss
from backend import auto_session
from backend.api import app
from backend.auto_session import AutoSessionRequest, run_auto_session
from backend.pipeline import CancellationToken, PipelineError
from backend.robust_objective import (
    RobustInputs,
    robust_score,
    select_best,
    targets_met,
)
from shared.contracts import (
    BacktestResult,
    EquityPoint,
    GenerateStrategyResult,
    Trade,
    WalkForwardResult,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "BASE_DIR", tmp_path / "store")
    ss.initialize()
    return ss


@pytest.fixture()
def client():
    return TestClient(app)


# =============================================================================
# Builders for realistic contract objects
# =============================================================================

_T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _equity():
    return [
        EquityPoint(timestamp=_T0, equity=10000.0, drawdown=0.0),
        EquityPoint(timestamp=_T0, equity=10500.0, drawdown=0.02),
    ]


def _trades(n: int):
    return [
        Trade(
            trade_id=f"t{i}",
            entry_time=_T0,
            exit_time=_T0,
            entry_price=100.0,
            exit_price=110.0,
            quantity=1.0,
            pnl=10.0,
            pnl_percent=0.1,
            commission_paid=0.1,
        )
        for i in range(n)
    ]


def _result(total_return=0.25, sharpe=1.5, max_dd=0.1, num_trades=20,
            win_rate=0.55, profit_factor=1.8):
    return BacktestResult(
        run_id="run-xyz",
        total_return=total_return,
        max_drawdown=max_dd,
        num_trades=num_trades,
        win_rate=win_rate,
        sharpe_ratio=sharpe,
        profit_factor=profit_factor,
        equity_curve=_equity(),
        trades=_trades(min(num_trades, 3)),
    )


def _wf(wfe=0.7, oos_return=0.18, oos_sharpe=1.2, num_windows=3):
    return WalkForwardResult(
        windows=[],
        num_windows=num_windows,
        is_months=2,
        oos_months=1,
        combined_oos_return=oos_return,
        combined_oos_sharpe=oos_sharpe,
        combined_oos_win_rate=0.52,
        combined_oos_max_drawdown=0.12,
        wfe=wfe,
        combined_oos_equity=_equity(),
        errors=[],
    )


class FakePipeline:
    """Deterministic stand-in for BacktestPipeline.

    `steps` is a list of per-iteration behaviour dicts. Recognised keys:
      gen_fail=str        -> generate_strategy returns validation_errors+no code
      gen_raise=True      -> generate_strategy raises
      bt_none=True        -> execute_backtest returns (None, [err], ...)
      bt_raise=True       -> execute_backtest raises
      cancel_raise=True   -> execute_backtest raises PipelineError (cancelled)
      otherwise: result/wf metric overrides for that iteration.
    The last step repeats if the loop runs longer than `steps`.
    """

    def __init__(self, steps):
        self.steps = steps
        self.gen_calls = 0
        self.bt_calls = 0
        self.insight_calls = 0

    def _step(self, idx):
        return self.steps[min(idx, len(self.steps) - 1)]

    async def generate_strategy(self, *, natural_language, model,
                                previous_script_code=None, symbol=None,
                                timeframe=None, start_date=None, end_date=None):
        step = self._step(self.gen_calls)
        self.gen_calls += 1
        if step.get("gen_raise"):
            raise RuntimeError("LLM exploded")
        if step.get("gen_fail"):
            return GenerateStrategyResult(
                script_id="", script_code="", strategy_name="",
                strategy_description="",
                validation_errors=[step["gen_fail"]], model_used=model,
            )
        return GenerateStrategyResult(
            script_id=f"scr-{self.gen_calls}",
            script_code="class S:\n    def signal(self, df, i):\n        return 0\n",
            strategy_name=f"Strategy {self.gen_calls}",
            strategy_description="desc",
            validation_errors=[],
            model_used=model,
        )

    async def execute_backtest(self, *, script_id, symbol, timeframe,
                               start_date, end_date, initial_capital,
                               commission, script_code, strategy_name,
                               strategy_description, cancel_token=None,
                               wfv_enabled=False, wfv_is_months=6,
                               wfv_oos_months=3):
        step = self._step(self.bt_calls)
        self.bt_calls += 1
        if step.get("cancel_raise"):
            raise PipelineError("Operation cancelled")
        if step.get("bt_raise"):
            raise RuntimeError("engine exploded")
        if step.get("bt_none"):
            return None, ["No data"], None, {}, None
        result = _result(
            total_return=step.get("total_return", 0.25),
            sharpe=step.get("sharpe", 1.5),
            max_dd=step.get("max_drawdown", 0.1),
            num_trades=step.get("num_trades", 20),
        )
        wf = None
        if step.get("num_windows", 3) > 0 and wfv_enabled:
            wf = _wf(
                wfe=step.get("wfe", 0.7),
                oos_return=step.get("oos_return", 0.18),
                oos_sharpe=step.get("oos_sharpe", 1.2),
                num_windows=step.get("num_windows", 3),
            )
        return result, [], None, {"total_ms": 1.0}, wf

    async def generate_insights(self, **kwargs):
        self.insight_calls += 1
        return (
            "Summary of performance.",
            [{"title": "Tighten stop", "description": "d", "prompt": "use a 2% stop"}],
            [],
        )


def _req(**over) -> AutoSessionRequest:
    base = dict(
        natural_language="Buy when RSI < 30, sell when RSI > 70",
        symbol="BTCUSDT",
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_capital=10000.0,
        model="gpt-5.4-mini",
    )
    base.update(over)
    return AutoSessionRequest(**base)


async def _run(session_id, req, pipeline, token=None):
    return await run_auto_session(
        session_id, req,
        pipeline=pipeline,
        semaphore=asyncio.Semaphore(1),
        cancel_token=token or CancellationToken(),
    )


# =============================================================================
# (d) Robust objective — best is by robust score, NEVER raw return
# =============================================================================

def test_robust_objective_rejects_high_return_wfe_failing_overleveraged():
    # A: huge raw return but WFE-failing and over-leveraged.
    a = RobustInputs(total_return=5.0, sharpe_ratio=4.0, max_drawdown=0.4,
                      num_trades=30, leverage=5.0, wfe=0.0, oos_return=-0.2,
                      oos_sharpe=-0.5, num_windows=2)
    # B: modest return but robustly walk-forward validated.
    b = RobustInputs(total_return=0.2, sharpe_ratio=1.1, max_drawdown=0.08,
                      num_trades=25, leverage=1.0, wfe=0.8, oos_return=0.15,
                      oos_sharpe=1.0, num_windows=3)

    assert robust_score(b) > robust_score(a)
    assert select_best([("A", a), ("B", b)]) == "B"


def test_robust_objective_gates_min_trades_and_missing_walk_forward():
    under_traded = RobustInputs(total_return=1.0, sharpe_ratio=3.0,
                                max_drawdown=0.05, num_trades=2, wfe=0.9,
                                num_windows=3)
    no_wf = RobustInputs(total_return=1.0, sharpe_ratio=3.0,
                         max_drawdown=0.05, num_trades=50, wfe=None,
                         num_windows=0)
    healthy = RobustInputs(total_return=0.1, sharpe_ratio=0.9,
                           max_drawdown=0.07, num_trades=20, wfe=0.6,
                           num_windows=3)
    assert robust_score(healthy) > robust_score(under_traded)
    assert robust_score(healthy) > robust_score(no_wf)
    assert select_best([("u", under_traded), ("n", no_wf),
                        ("h", healthy)]) == "h"


def test_targets_met_semantics():
    inp = RobustInputs(total_return=0.3, sharpe_ratio=1.2, max_drawdown=0.1,
                       num_trades=20, wfe=0.6, num_windows=3)
    assert targets_met(inp, {"min_return": 0.2, "min_trades": 10}) is True
    assert targets_met(inp, {"min_return": 0.5}) is False
    # No targets -> never criteria-met (only the hard budget can stop).
    assert targets_met(inp, {}) is False
    assert targets_met(inp, None) is False
    # min_wfe requires real walk-forward data.
    no_wf = RobustInputs(total_return=0.3, sharpe_ratio=1.2,
                         max_drawdown=0.1, num_trades=20, wfe=None,
                         num_windows=0)
    assert targets_met(no_wf, {"min_wfe": 0.1}) is False


# =============================================================================
# (b) Loop terminates exactly on max_iterations — no extra round past the cap
# =============================================================================

async def test_loop_stops_exactly_at_max_iterations(store):
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    sid = "sess-b"
    # No targets supplied -> only the hard budget can stop it.
    final = await _run(sid, _req(budget={"max_iterations": 2}), pipe)

    assert pipe.gen_calls == 2, "must run exactly max_iterations, no 'one more'"
    assert pipe.bt_calls == 2
    assert final["status"] == "complete"
    assert final["stopReason"] == "budget-exhausted"
    assert final["currentIteration"] == 2
    assert final["maxIterations"] == 2

    metas = []
    for d in ss.list_iteration_dirs(sid):
        metas.append(ss.read_iteration_meta(sid, d.name.split("_", 1)[1]))
    assert len(metas) == 2
    assert all(m["status"] == "complete" for m in metas)


# =============================================================================
# (c) Loop terminates with criteria-met; best satisfies every target
# =============================================================================

async def test_loop_stops_on_criteria_met_and_best_satisfies_targets(store):
    pipe = FakePipeline([{"total_return": 0.4, "sharpe": 2.0, "wfe": 0.8,
                          "num_trades": 30}])
    sid = "sess-c"
    targets = {"min_return": 0.1, "min_trades": 10, "min_wfe": 0.3}
    final = await _run(
        sid, _req(targets=targets, budget={"max_iterations": 5}), pipe
    )

    assert pipe.gen_calls == 1, "criteria met on iter 1 -> no extra iteration"
    assert final["status"] == "complete"
    assert final["stopReason"] == "criteria-met"
    assert final["bestIterationId"] is not None

    best = ss.read_iteration_full(sid, final["bestIterationId"])
    assert best is not None
    r = best["result"]
    assert r["total_return"] >= targets["min_return"]
    assert r["num_trades"] >= targets["min_trades"]
    assert best["walkForwardResult"]["wfe"] >= targets["min_wfe"]


# =============================================================================
# (e) autoRun status persisted into session.json; fresh read = last state
# =============================================================================

async def test_autorun_status_persisted_durably(store):
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    sid = "sess-e"
    await _run(sid, _req(budget={"max_iterations": 2}), pipe)

    # Fresh read straight off disk = the worker-restart / reload survival proxy.
    meta = ss.read_session_meta(sid)
    assert meta is not None
    auto = meta["autoRun"]
    assert auto["status"] == "complete"
    assert auto["stopReason"] == "budget-exhausted"
    assert auto["currentIteration"] == 2
    assert auto["maxIterations"] == 2
    assert auto["bestIterationId"] is not None
    assert auto["startedAt"] and auto["updatedAt"]


# =============================================================================
# (f) Iteration artifacts use the SAME shape write_iteration produces for a
#     manual run (lightweight meta, heavy detail lazy via per-iteration read)
# =============================================================================

async def test_iteration_artifacts_match_manual_shape(store):
    pipe = FakePipeline([{"total_return": 0.3, "wfe": 0.7}])
    sid = "sess-f"
    await _run(sid, _req(budget={"max_iterations": 1}), pipe)

    dirs = ss.list_iteration_dirs(sid)
    assert len(dirs) == 1
    iter_id = dirs[0].name.split("_", 1)[1]

    meta = ss.read_iteration_meta(sid, iter_id)
    for heavy in ("result", "rating", "insights", "prompt", "scriptCode"):
        assert heavy not in meta, f"heavy key {heavy!r} leaked into meta"
    assert meta["status"] == "complete"
    assert meta["strategyName"] == "Strategy 1"
    assert meta["totalReturn"] == pytest.approx(0.3)
    assert meta["params"]["symbol"] == "BTCUSDT"

    full = ss.read_iteration_full(sid, iter_id)
    assert full["result"]["total_return"] == pytest.approx(0.3)
    assert len(full["result"]["trades"]) >= 1
    assert len(full["result"]["equity_curve"]) >= 1
    assert full["prompt"]
    assert "class S" in full["scriptCode"]
    assert full["insights"]["suggestions"][0]["title"] == "Tighten stop"

    activity = ss.read_activity_log(sid)
    assert any(e["type"] == "complete" for e in activity)
    assert all(e.get("iterationId") == iter_id for e in activity)


# =============================================================================
# Error / robustness cases
# =============================================================================

async def test_absent_or_nonpositive_max_iterations_is_safely_defaulted(store):
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    final = await _run("sess-def", _req(budget={"max_iterations": 0}), pipe)
    assert pipe.gen_calls == auto_session.DEFAULT_MAX_ITERATIONS
    assert final["status"] == "complete"
    assert final["stopReason"] == "budget-exhausted"

    pipe2 = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    final2 = await _run("sess-def2", _req(budget={}), pipe2)
    assert pipe2.gen_calls == auto_session.DEFAULT_MAX_ITERATIONS
    assert final2["maxIterations"] == auto_session.DEFAULT_MAX_ITERATIONS


async def test_huge_max_iterations_is_clamped_never_unbounded(store):
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    final = await _run(
        "sess-clamp", _req(budget={"max_iterations": 100000}), pipe
    )
    assert final["maxIterations"] == auto_session.HARD_MAX_ITERATIONS
    assert pipe.gen_calls == auto_session.HARD_MAX_ITERATIONS


async def test_single_iteration_failure_does_not_hang_loop_reaches_terminal(store):
    # iter1 generate raises, iter2 backtest None, iter3 succeeds.
    pipe = FakePipeline([
        {"gen_raise": True},
        {"bt_none": True},
        {"total_return": 0.2, "wfe": 0.7},
    ])
    sid = "sess-fail"
    final = await _run(sid, _req(budget={"max_iterations": 3}), pipe)

    assert final["status"] == "complete"
    assert final["stopReason"] == "budget-exhausted"
    assert final["currentIteration"] == 3
    assert final["bestIterationId"] is not None  # the one good iteration

    statuses = sorted(
        ss.read_iteration_meta(sid, d.name.split("_", 1)[1])["status"]
        for d in ss.list_iteration_dirs(sid)
    )
    assert statuses == ["complete", "error", "error"]


async def test_cooperative_cancel_yields_stopped_terminal_state(store):
    pipe = FakePipeline([{"cancel_raise": True}])
    token = CancellationToken()
    final = await _run("sess-stop", _req(budget={"max_iterations": 5}), pipe,
                       token=token)
    assert final["status"] == "stopped"
    # No further iterations appended after a stop.
    assert pipe.gen_calls == 1


async def test_no_secrets_written_into_artifacts(store):
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    sid = "sess-sec"
    await _run(sid, _req(budget={"max_iterations": 1}), pipe)

    base = ss._live_dir(sid)
    blob = ""
    for p in base.rglob("*"):
        if p.is_file():
            blob += p.read_text(encoding="utf-8", errors="ignore")
    for needle in ("api_key", "API_KEY", "OPENAI_API_KEY",
                   "ANTHROPIC_API_KEY", "Authorization", "sk-"):
        assert needle not in blob


async def test_semaphore_serializes_and_is_not_leaked(store):
    # Two concurrent auto-sessions sharing one semaphore must both finish
    # (proves the loop yields and serialises backtests without deadlock).
    sem = asyncio.Semaphore(1)
    p1 = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    p2 = FakePipeline([{"total_return": 0.2, "wfe": 0.7}])
    f1, f2 = await asyncio.gather(
        run_auto_session("c1", _req(budget={"max_iterations": 2}),
                         pipeline=p1, semaphore=sem,
                         cancel_token=CancellationToken()),
        run_auto_session("c2", _req(budget={"max_iterations": 2}),
                         pipeline=p2, semaphore=sem,
                         cancel_token=CancellationToken()),
    )
    assert f1["status"] == "complete" and f2["status"] == "complete"
    assert sem._value == 1, "semaphore must be released, not leaked"


# =============================================================================
# (a) Endpoint: POST -> 200 + sessionId; GET /api/sessions lists it; the
#     session-open path exposes autoRun and stays lightweight (anti-goal)
# =============================================================================

_HEAVY_KEYS = ("result", "rating", "insights", "prompt", "scriptCode")


def test_post_auto_sessions_creates_listed_session(store, client, monkeypatch):
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    monkeypatch.setattr(auto_session, "_get_pipeline", lambda: pipe)

    resp = client.post("/api/auto-sessions", json={
        "natural_language": "Buy dips on BTC",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "start_date": "2024-01-01",
        "end_date": "2024-02-01",
        "initial_capital": 10000,
        "model": "gpt-5.4-mini",
        "targets": {"min_return": -1.0},
        "budget": {"max_iterations": 1},
    })
    assert resp.status_code == 200
    body = resp.json()
    sid = body["sessionId"]
    assert sid
    assert body["status"] in ("running", "queued")

    # Immediately listed by GET /api/sessions — no browser interaction.
    tabs = client.get("/api/sessions").json()["tabs"]
    assert any(t["id"] == sid for t in tabs)

    # Openable; autoRun surfaced; list path stays lightweight (anti-goal).
    opened = client.get(f"/api/sessions/{sid}")
    assert opened.status_code == 200
    data = opened.json()
    assert data["autoRun"] is not None
    assert data["autoRun"]["status"] in (
        "running", "queued", "complete", "stopped"
    )
    for entry in data["iterationHistory"]:
        for k in _HEAVY_KEYS:
            assert k not in entry


def test_post_auto_sessions_missing_pinned_field_is_4xx_not_500(client):
    # symbol omitted -> open-universe (J-12) not supported -> clear 422.
    resp = client.post("/api/auto-sessions", json={
        "natural_language": "do something",
        "timeframe": "1h",
        "start_date": "2024-01-01",
        "end_date": "2024-02-01",
    })
    assert resp.status_code == 422
    assert "symbol" in resp.json()["detail"]

    # natural_language missing -> Pydantic 422 (never a 500).
    resp2 = client.post("/api/auto-sessions", json={"symbol": "BTCUSDT"})
    assert resp2.status_code == 422


# =============================================================================
# B1 (anti-goal): the headless loop MUST NOT block the API event loop.
# Heavy per-iteration JSON encoding + store writes must be offloaded off the
# event-loop thread (asyncio.to_thread) — exactly like the manual
# session_routes path already does. With a deliberately large BacktestResult
# we run the loop while concurrently sampling the event loop; if the loop is
# starved (synchronous encode/dump/write on the loop thread) the inter-tick
# gap spikes far past the spec's responsiveness bound.
# =============================================================================

def _big_equity(n: int):
    return [EquityPoint(timestamp=_T0, equity=10000.0 + i, drawdown=0.0)
            for i in range(n)]


def _big_trades(n: int):
    return [
        Trade(trade_id=f"t{i}", entry_time=_T0, exit_time=_T0,
              entry_price=100.0, exit_price=110.0, quantity=1.0,
              pnl=10.0, pnl_percent=0.1, commission_paid=0.1)
        for i in range(n)
    ]


class YieldingBigPipeline:
    """Deterministic stand-in that *faithfully models the real pipeline's
    yield points*: ``generate_strategy`` / ``execute_backtest`` /
    ``generate_insights`` each yield to the loop via a tiny
    ``asyncio.to_thread`` (the real pipeline yields the same way — LLM
    network I/O and the engine's ``await asyncio.to_thread(engine.run,...)``).
    Every backtest returns a *large* result so the controller's
    post-backtest serialization + store writes are expensive. If those run
    synchronously on the event-loop thread (the B1 defect) the heartbeat
    gap spikes for their full duration; if they are offloaded
    (``asyncio.to_thread``, like the manual ``session_routes`` path) the
    loop stays responsive between the modelled I/O yields."""

    def __init__(self):
        self.gen_calls = 0
        self.bt_calls = 0
        self.insight_calls = 0

    async def generate_strategy(self, *, model, **kwargs):
        self.gen_calls += 1
        await asyncio.to_thread(time.sleep, 0.01)  # models LLM network I/O
        return GenerateStrategyResult(
            script_id=f"scr-{self.gen_calls}",
            script_code="class S:\n    def signal(self, df, i):\n        return 0\n",
            strategy_name=f"Strategy {self.gen_calls}",
            strategy_description="desc",
            validation_errors=[],
            model_used=model,
        )

    async def execute_backtest(self, *, wfv_enabled=False, **kwargs):
        self.bt_calls += 1
        await asyncio.to_thread(time.sleep, 0.02)  # models engine to_thread
        result = BacktestResult(
            run_id="big-run",
            total_return=0.2,
            max_drawdown=0.1,
            num_trades=8000,
            win_rate=0.5,
            sharpe_ratio=1.2,
            profit_factor=1.5,
            equity_curve=_big_equity(30000),
            trades=_big_trades(8000),
        )
        wf = _wf() if wfv_enabled else None
        return result, [], None, {"total_ms": 1.0}, wf

    async def generate_insights(self, **kwargs):
        self.insight_calls += 1
        await asyncio.to_thread(time.sleep, 0.01)
        return ("Summary.",
                [{"title": "t", "description": "d", "prompt": "p"}], [])


async def test_headless_loop_does_not_block_event_loop(store):
    import time as _time

    pipe = YieldingBigPipeline()

    max_gap = 0.0
    samples = 0
    done = asyncio.Event()

    async def heartbeat():
        nonlocal max_gap, samples
        while not done.is_set():
            t = _time.perf_counter()
            await asyncio.sleep(0.02)
            gap = _time.perf_counter() - t - 0.02
            samples += 1
            if gap > max_gap:
                max_gap = gap

    hb = asyncio.create_task(heartbeat())
    try:
        final = await _run(
            "sess-loopblock", _req(budget={"max_iterations": 2}), pipe
        )
    finally:
        done.set()
        await hb

    assert final["status"] == "complete"
    assert pipe.bt_calls == 2
    assert samples > 0, "heartbeat never sampled — harness is broken"

    # Spec bound: every probe must stay < 3 s while a run is active. We
    # assert a much stricter 0.5 s. Measured pre-fix this is ~1.2 s (the
    # synchronous jsonable_encoder + _json_safe + write_iteration json.dumps
    # of ~30k equity / 8k trades, twice, plus repeated session.json
    # read-merge-write, all on the event-loop thread between the modelled
    # I/O yields). Post-fix (every store/encode call offloaded via
    # asyncio.to_thread) the loop stays responsive: well under 0.5 s.
    assert max_gap < 0.5, (
        f"event loop blocked for {max_gap:.2f}s during a headless run "
        f"(anti-goal: the background job must not block the API event loop)"
    )
