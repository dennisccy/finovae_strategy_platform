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
import types
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.session_store as ss
from backend import auto_session
from backend.api import app
from backend.auto_session import (
    AutoSessionRequest,
    create_auto_session,
    run_auto_session,
    stop_auto_session,
)
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


@pytest.fixture(autouse=True)
def _clean_cancel_registry():
    """The in-process cancellation registry and the reusable backtest child
    are module-level; clear/terminate them around every test so nothing leaks
    across runs (TC-10 pass criterion; no orphaned child process)."""
    auto_session._CANCEL_REGISTRY.clear()
    yield
    auto_session._CANCEL_REGISTRY.clear()
    auto_session._shutdown_backtest_worker()


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

    iter-4 extension (additive, legacy behaviour byte-unchanged when the new
    args are unused): an optional ``by_cfg`` maps ``(symbol, timeframe)`` ->
    a step dict so the staged SCREEN→PROMOTE path is exercised
    deterministically regardless of call order (a SCREEN and the later
    PROMOTE of the same config read the SAME dict; SCREEN vs PROMOTE is told
    apart by ``wfv_enabled`` — SCREEN passes ``False`` so it never gets WF).
    Per-call introspection lists (``gen_models`` / ``insight_models`` /
    ``bt_wfv`` / ``bt_cfgs``) let the staged tests assert the cheap-model,
    no-WF SCREEN vs the req.model, WF PROMOTE without timing/order guesses.
    """

    def __init__(self, steps, by_cfg=None):
        self.steps = steps
        self.by_cfg = by_cfg or {}
        self.gen_calls = 0
        self.bt_calls = 0
        self.insight_calls = 0
        # Additive per-call introspection (legacy tests never read these).
        self.gen_models: list = []
        self.gen_cfgs: list = []
        self.bt_wfv: list = []
        self.bt_cfgs: list = []
        self.insight_models: list = []

    def _step(self, idx):
        return self.steps[min(idx, len(self.steps) - 1)]

    def _cfg_step(self, symbol, timeframe, counter):
        key = (symbol, timeframe)
        if key in self.by_cfg:
            return self.by_cfg[key]
        return self._step(counter)

    async def generate_strategy(self, *, natural_language, model,
                                previous_script_code=None, symbol=None,
                                timeframe=None, start_date=None, end_date=None,
                                usage_sink=None):
        step = self._cfg_step(symbol, timeframe, self.gen_calls)
        self.gen_calls += 1
        self.gen_models.append(model)
        self.gen_cfgs.append((symbol, timeframe))
        if step.get("gen_raise"):
            raise RuntimeError("LLM exploded")
        # Deterministic fake SDK token usage flowing the PRODUCTION capture
        # path (a list the loop owns and drains into the cost tracker). A
        # genuine generation — even one that fails validation — consumed
        # tokens; only a hard exception (gen_raise) above spends nothing.
        if usage_sink is not None:
            usage_sink.append({
                "model": model,
                "input_tokens": step.get("gen_in", 100),
                "output_tokens": step.get("gen_out", 50),
            })
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
        step = self._cfg_step(symbol, timeframe, self.bt_calls)
        self.bt_calls += 1
        self.bt_wfv.append(wfv_enabled)
        self.bt_cfgs.append((symbol, timeframe))
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
        step = self._step(self.insight_calls)
        self.insight_calls += 1
        self.insight_models.append(kwargs.get("model"))
        sink = kwargs.get("usage_sink")
        if sink is not None:
            sink.append({
                "model": kwargs.get("model", "gpt-5.4-mini"),
                "input_tokens": step.get("ins_in", 200),
                "output_tokens": step.get("ins_out", 150),
            })
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


def _open_req(**over) -> AutoSessionRequest:
    """Open-universe request: NO symbol/timeframe — only objective + budget
    (and the strategy idea explored across the bounded seed configs)."""
    base = dict(
        natural_language="Trend-follow with an EMA crossover",
        objective="robust",
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

def _cpu_bound_backtest_child(payload: dict) -> tuple:
    """CHILD-process backtest stand-in that does REAL pure-Python CPU-bound,
    GIL-HOLDING work — a tight arithmetic busy-loop, NOT ``time.sleep`` (sleep
    releases the GIL, which is exactly why the old stub "passed by accident"
    and hid QA Blocker #1). This faithfully models the deterministic engine
    running the RestrictedPython signal bar-by-bar: pure Python, holds the
    GIL for its whole duration.

    It is run through the SAME production seam the real pipeline uses
    (:func:`auto_session._subprocess_backtest_executor`). It stamps its OWN
    pid into ``BacktestResult.run_id`` so the test can DETERMINISTICALLY
    assert the backtest executed in a different OS process (the fix's core
    invariant — a non-flaky guard that a single-thread timing bound cannot
    give, since the GIL round-robins every 5 ms). Resolved by import in the
    spawned child — must stay a top-level, importable function.
    """
    import os as _os
    import time as _t
    deadline = _t.perf_counter() + 0.3  # GIL-holding CPU work (real, not sleep)
    x = 0
    while _t.perf_counter() < deadline:
        for _ in range(50_000):
            x += 1
    assert x > 0  # defeat dead-code elimination of the busy-loop
    result = BacktestResult(
        run_id=f"pid-{_os.getpid()}",
        total_return=0.2, max_drawdown=0.1, num_trades=20, win_rate=0.5,
        sharpe_ratio=1.2, profit_factor=1.5,
        equity_curve=_equity(), trades=_trades(3),
    )
    wf = _wf()
    result_json, rating_json, wf_json = auto_session._serialize_artifacts(
        result, None, wf
    )
    return (result, [], None, {"total_ms": 1.0}, wf,
            result_json, rating_json, wf_json)


async def test_headless_loop_does_not_block_event_loop(store):
    """Anti-goal regression guard (QA Blocker #1, rewritten).

    A *continuously* CPU-bound headless run must NOT block the API event
    loop. The backtest is GIL-holding pure-Python work; only true process
    isolation (child has its own GIL) keeps the parent responsive. The old
    test stubbed the engine with ``await asyncio.to_thread(time.sleep, …)`` —
    ``sleep`` releases the GIL, so it could never reproduce the starvation it
    claimed to guard. This drives REAL CPU-bound work through the production
    subprocess seam and fails if that offload ever regresses to an in-process
    thread (which would GIL-starve the heartbeat for the busy-loop duration).
    """
    import time as _time

    # Fake pipeline supplies the in-process (I/O-bound, GIL-releasing)
    # generate_strategy / generate_insights; the CPU-bound backtest is
    # offloaded to a child process via the real seam.
    pipe = FakePipeline([{}])
    executor = auto_session._subprocess_backtest_executor(
        f"{__name__}:_cpu_bound_backtest_child"
    )

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

    import os as _os

    hb = asyncio.create_task(heartbeat())
    try:
        final = await run_auto_session(
            "sess-loopblock",
            _req(budget={"max_iterations": 2}),
            pipeline=pipe,
            semaphore=asyncio.Semaphore(1),
            cancel_token=CancellationToken(),
            backtest_executor=executor,
        )
    finally:
        done.set()
        await hb
        auto_session._shutdown_backtest_worker()

    assert final["status"] == "complete"
    assert final["currentIteration"] == 2
    assert pipe.gen_calls == 2 and pipe.insight_calls == 2
    assert samples > 20, "heartbeat never sampled — harness is broken"

    # DETERMINISTIC guard (non-flaky): every backtest must have executed in a
    # DIFFERENT OS process than this test/API worker. A regression to an
    # in-thread offload would stamp THIS pid here and fail instantly. (A
    # single-thread timing bound cannot guard this — the GIL round-robins
    # every 5 ms, so one in-thread CPU backtest only ~halves a concurrent
    # probe; QA's 33 s came from the *continuous* loop saturating the shared
    # thread pool, which process isolation removes at the root.)
    parent_pid = _os.getpid()
    dirs = sorted(ss.list_iteration_dirs("sess-loopblock"), key=lambda d: d.name)
    assert len(dirs) == 2
    for d in dirs:
        node = ss.read_iteration_full("sess-loopblock", d.name.split("_", 1)[1])
        run_id = (node.get("result") or {}).get("run_id", "")
        assert run_id.startswith("pid-"), f"unexpected run_id {run_id!r}"
        child_pid = int(run_id.split("-", 1)[1])
        assert child_pid != parent_pid, (
            "backtest ran IN this process (anti-goal: the CPU-bound backtest "
            "MUST run out-of-process so it never holds the API worker's GIL "
            "/ starves GET /api/sessions while a headless run is active)"
        )

    # Corroborating functional check: with the CPU work genuinely out of this
    # process, the event loop stays responsive (lenient bound — the parent
    # only parks a pool thread on an OS pipe; not the primary guard).
    assert max_gap < 0.5, (
        f"event loop blocked for {max_gap:.2f}s during a headless run "
        f"(anti-goal: the background job must not block the API event loop)"
    )


# =============================================================================
# iter-2 / J-11 — public stop endpoint + by-sessionId cancellation registry +
# durable, worker-safe cooperative stop. Stop -> terminal `stopped`, zero
# post-stop iterations, robust `bestIterationId` preserved.
# =============================================================================

def _running_autorun_meta(max_iter: int = 5) -> dict:
    """A session.json meta block for a still-running headless auto-session."""
    return {
        "name": "Auto: test",
        "lastAccessedAt": int(time.time() * 1000),
        "backtestParams": {"symbol": "BTCUSDT", "timeframe": "1h"},
        "autoRun": {
            "status": "running",
            "stopReason": None,
            "currentIteration": 1,
            "maxIterations": max_iter,
            "bestIterationId": None,
            "startedAt": auto_session._now_iso(),
            "updatedAt": auto_session._now_iso(),
        },
    }


class StopViaDurableSignalPipeline(FakePipeline):
    """FakePipeline that, while iteration ``stop_after`` is being processed,
    writes the *durable* stop flag into session.json through the very
    mechanism the loop polls (``_update_autorun_sync``). It NEVER touches the
    in-process ``CancellationToken`` — so a test using it proves the loop
    honours the persisted signal on its own, not only the live token."""

    def __init__(self, steps, sid: str, stop_after: int):
        super().__init__(steps)
        self.sid = sid
        self.stop_after = stop_after

    async def generate_insights(self, **kwargs):
        out = await super().generate_insights(**kwargs)
        if self.insight_calls == self.stop_after:
            auto_session._update_autorun_sync(self.sid, stopRequested=True)
        return out


async def test_durable_stop_signal_honored_no_post_stop_iterations(store):
    # Stop is requested (durably) during iteration 1; the loop must finish
    # that in-flight iteration, then break BEFORE starting iteration 2.
    sid = "sess-durable-stop"
    pipe = StopViaDurableSignalPipeline(
        [{"total_return": 0.3, "wfe": 0.7, "num_trades": 20}],
        sid, stop_after=1,
    )
    token = CancellationToken()  # never cancelled by the test
    final = await _run(sid, _req(budget={"max_iterations": 5}), pipe,
                       token=token)

    assert final["status"] == "stopped"
    assert final["stopReason"] == "stopped"  # visible, non-null reason
    assert pipe.gen_calls == 1, "no iteration may start after the stop request"
    dirs = ss.list_iteration_dirs(sid)
    assert len(dirs) == 1, "exactly the one in-flight iteration is persisted"
    # Best-so-far preserved by the robust objective (never re-derived by raw).
    assert final["bestIterationId"] is not None
    only_id = dirs[0].name.split("_", 1)[1]
    assert final["bestIterationId"] == only_id
    # The durable read each round drove this — the live token was untouched
    # by the test (the loop cancels it itself only AFTER it observes the flag).
    meta = ss.read_session_meta(sid)
    assert meta["autoRun"]["stopRequested"] is True


async def test_restart_safe_stop_with_no_live_token_zero_iterations(store):
    # Simulated worker restart: session.json already carries a durable stop
    # request and there is NO live in-process token anywhere. The loop must
    # still drive straight to terminal `stopped` with zero iterations.
    sid = "sess-restart-stop"
    meta = _running_autorun_meta(max_iter=3)
    meta["autoRun"]["currentIteration"] = 0
    meta["autoRun"]["stopRequested"] = True
    ss.write_session_meta(sid, meta)

    pipe = FakePipeline([{"total_return": 0.5, "wfe": 0.9}])
    fresh_token = CancellationToken()          # not in any registry
    assert sid not in auto_session._CANCEL_REGISTRY
    final = await _run(sid, _req(budget={"max_iterations": 3}), pipe,
                       token=fresh_token)

    assert final["status"] == "stopped"
    assert final["stopReason"] == "stopped"
    assert pipe.gen_calls == 0, "no iteration may run when stop is pre-requested"
    assert len(ss.list_iteration_dirs(sid)) == 0


async def test_best_on_stop_uses_robust_objective_not_raw_return(store):
    # iter-1: huge raw return but WFE-failing  -> low robust score.
    # iter-2: modest return but walk-forward validated -> high robust score.
    # Durable stop fires after iter-2; best MUST be iter-2 (robust), not the
    # higher-raw-return iter-1.
    sid = "sess-best-on-stop"
    steps = [
        {"total_return": 5.0, "sharpe": 4.0, "max_drawdown": 0.4,
         "num_trades": 30, "wfe": 0.0, "oos_return": -0.2,
         "oos_sharpe": -0.5, "num_windows": 2},
        {"total_return": 0.2, "sharpe": 1.1, "max_drawdown": 0.08,
         "num_trades": 25, "wfe": 0.8, "oos_return": 0.15,
         "oos_sharpe": 1.0, "num_windows": 3},
    ]
    pipe = StopViaDurableSignalPipeline(steps, sid, stop_after=2)
    final = await _run(sid, _req(budget={"max_iterations": 9}), pipe)

    assert final["status"] == "stopped"
    dirs = sorted(ss.list_iteration_dirs(sid), key=lambda d: d.name)
    assert len(dirs) == 2
    id_iter1 = dirs[0].name.split("_", 1)[1]
    id_iter2 = dirs[1].name.split("_", 1)[1]
    assert final["bestIterationId"] == id_iter2
    assert final["bestIterationId"] != id_iter1, (
        "the higher-raw-return WFE-failing candidate must NOT be best"
    )


async def test_cancel_registry_removed_on_every_terminal_path(store):
    # (1) budget-exhausted
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    tok = CancellationToken()
    auto_session._CANCEL_REGISTRY["t-budget"] = tok
    await _run("t-budget", _req(budget={"max_iterations": 2}), pipe, token=tok)
    assert "t-budget" not in auto_session._CANCEL_REGISTRY

    # (2) criteria-met
    pipe = FakePipeline([{"total_return": 0.4, "wfe": 0.8, "num_trades": 30}])
    tok = CancellationToken()
    auto_session._CANCEL_REGISTRY["t-crit"] = tok
    await _run("t-crit",
               _req(targets={"min_return": 0.1, "min_trades": 10},
                    budget={"max_iterations": 5}), pipe, token=tok)
    assert "t-crit" not in auto_session._CANCEL_REGISTRY

    # (3) stopped (cooperative cancel)
    pipe = FakePipeline([{"cancel_raise": True}])
    tok = CancellationToken()
    auto_session._CANCEL_REGISTRY["t-stop"] = tok
    await _run("t-stop", _req(budget={"max_iterations": 5}), pipe, token=tok)
    assert "t-stop" not in auto_session._CANCEL_REGISTRY

    # (4) crash inside run_auto_session — the `finally` must still clean up.
    tok = CancellationToken()
    auto_session._CANCEL_REGISTRY["t-crash"] = tok

    class _BoomPipeline:
        async def generate_strategy(self, **kw):
            raise AssertionError("unreachable")

    def _boom(_sid):
        raise RuntimeError("store exploded before the loop")

    import backend.session_store as _ss
    orig = _ss.read_session_meta
    _ss.read_session_meta = _boom
    try:
        with pytest.raises(RuntimeError):
            await run_auto_session(
                "t-crash", _req(budget={"max_iterations": 2}),
                pipeline=_BoomPipeline(), semaphore=asyncio.Semaphore(1),
                cancel_token=tok,
            )
    finally:
        _ss.read_session_meta = orig
    assert "t-crash" not in auto_session._CANCEL_REGISTRY, (
        "registry must be cleaned even when run_auto_session crashes"
    )


async def test_cancel_registry_populated_in_create_auto_session(store, monkeypatch):
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    monkeypatch.setattr(auto_session, "_get_pipeline", lambda: pipe)

    # Capture (and do NOT schedule) the detached runner so we can observe the
    # registry state exactly as create_auto_session leaves it.
    captured: list = []
    monkeypatch.setattr(
        auto_session.asyncio, "create_task",
        lambda coro: (captured.append(coro), types.SimpleNamespace())[1],
    )

    shim = types.SimpleNamespace(app=app)
    resp = await create_auto_session(_req(budget={"max_iterations": 1}), shim)
    sid = resp.sessionId
    try:
        assert sid in auto_session._CANCEL_REGISTRY
        assert isinstance(auto_session._CANCEL_REGISTRY[sid], CancellationToken)
    finally:
        for c in captured:
            c.close()


# --- Stop endpoint: success, idempotency, unknown, worker-safety -------------

async def test_stop_running_session_cancels_token_and_writes_durable_signal(store):
    sid = "sess-stop-running"
    ss.write_session_meta(sid, _running_autorun_meta())
    token = CancellationToken()
    auto_session._CANCEL_REGISTRY[sid] = token

    t0 = time.monotonic()
    resp = await stop_auto_session(sid)
    elapsed = time.monotonic() - t0

    assert elapsed < 1.0, "stop must return promptly, not await loop completion"
    assert resp["sessionId"] == sid
    assert token.is_cancelled, "the live in-process token must be cancelled"
    meta = ss.read_session_meta(sid)
    assert meta["autoRun"]["stopRequested"] is True
    # Status untouched here — the loop owns the terminal transition.
    assert meta["autoRun"]["status"] == "running"


async def test_stop_is_worker_safe_when_no_live_token_registered(store):
    sid = "sess-stop-noworker"
    ss.write_session_meta(sid, _running_autorun_meta())
    assert sid not in auto_session._CANCEL_REGISTRY

    resp = await stop_auto_session(sid)

    assert resp["sessionId"] == sid
    meta = ss.read_session_meta(sid)
    assert meta["autoRun"]["stopRequested"] is True, (
        "durable signal must be written even with no live token in this worker"
    )


async def test_stop_unknown_session_raises_clean_404(store):
    with pytest.raises(HTTPException) as exc:
        await stop_auto_session("does-not-exist-12345")
    assert exc.value.status_code == 404

    # A non-auto (manual) session is also not stoppable -> clean 404.
    ss.write_session_meta("manual-1", {"name": "Manual", "backtestParams": {}})
    with pytest.raises(HTTPException) as exc2:
        await stop_auto_session("manual-1")
    assert exc2.value.status_code == 404


async def test_stop_already_terminal_is_idempotent_no_state_regression(store):
    sid = "sess-stop-terminal"
    meta = _running_autorun_meta()
    meta["autoRun"]["status"] = "complete"
    meta["autoRun"]["stopReason"] = "criteria-met"
    meta["autoRun"]["bestIterationId"] = "iter-abc"
    meta["autoRun"]["currentIteration"] = 2
    ss.write_session_meta(sid, meta)
    before = dict(ss.read_session_meta(sid)["autoRun"])

    resp = await stop_auto_session(sid)
    after = dict(ss.read_session_meta(sid)["autoRun"])

    assert resp["sessionId"] == sid
    assert before == after, "an already-terminal session must not regress"
    assert "stopRequested" not in after, (
        "idempotent no-op must not mutate a terminal session"
    )


def test_stop_endpoint_http_unknown_404_and_idempotent_terminal(store, client):
    # Unknown id over HTTP -> clean 404 JSON, never a 500.
    r404 = client.post("/api/auto-sessions/nope-nope/stop")
    assert r404.status_code == 404
    assert "detail" in r404.json()

    # An already-terminal session: stopping it over HTTP is an idempotent
    # 2xx no-op — no error, no extra iteration, no state regression. Seeded
    # deterministically (the detached runner is exercised by the direct-await
    # and durable-signal tests; driving it to terminal through the sync
    # TestClient portal is racy by construction).
    sid = "http-terminal"
    meta = _running_autorun_meta()
    meta["autoRun"]["status"] = "complete"
    meta["autoRun"]["stopReason"] = "criteria-met"
    meta["autoRun"]["bestIterationId"] = "iter-xyz"
    meta["autoRun"]["currentIteration"] = 2
    ss.write_session_meta(sid, meta)
    auto_before = client.get(f"/api/sessions/{sid}").json()["autoRun"]

    stopped = client.post(f"/api/auto-sessions/{sid}/stop")
    assert stopped.status_code == 200

    after = client.get(f"/api/sessions/{sid}").json()
    assert after["autoRun"] == auto_before, "terminal autoRun must be unchanged"
    assert "stopRequested" not in after["autoRun"], "no mutation of a terminal run"


# =============================================================================
# iter-3 / J-12 — Open-universe: only an objective + budget explores ≥2
# distinct configs from the BOUNDED seed universe (no blind fan-out), best
# marked by the robust objective, headless run UI-indistinguishable.
# =============================================================================

def _distinct_cfgs(sid: str) -> set:
    cfgs = set()
    for d in ss.list_iteration_dirs(sid):
        m = ss.read_iteration_meta(sid, d.name.split("_", 1)[1])
        cfgs.add((m["params"]["symbol"], m["params"]["timeframe"]))
    return cfgs


# --- Staged-form helpers (J-14): count the stage markers in the feed -------

def _stage_markers(sid: str) -> tuple[list[dict], list[dict]]:
    """Return (SCREEN, PROMOTE) auto-run stage-marker activity entries — the
    one-per-config staging markers the operator sees in the existing feed."""
    log = ss.read_activity_log(sid)
    screen = [e for e in log
              if e["type"] == "auto-run" and e["content"].startswith("SCREEN")]
    promote = [e for e in log
               if e["type"] == "auto-run" and e["content"].startswith("PROMOTE")]
    return screen, promote


def _nodes_by_stage(sid: str) -> tuple[list[dict], list[dict]]:
    """Return (screen_nodes, promote_nodes) full iteration nodes, by the
    persisted ``stage`` marker — proves screened-only vs promoted at the
    durable-artifact level."""
    screen, promote = [], []
    for d in ss.list_iteration_dirs(sid):
        node = ss.read_iteration_full(sid, d.name.split("_", 1)[1])
        (promote if node.get("stage") == "promote" else screen).append(node)
    return screen, promote


async def test_open_universe_runs_multiple_distinct_configs(store):
    # STAGED FORM (J-12 invariant re-asserted under SCREEN→PROMOTE, NOT
    # loosened): no symbol/timeframe — only objective + budget. The cheap
    # SCREEN stage screens several bounded-seed configs; only a small top-k
    # (k < screened) is PROMOTEd to the full pipeline.
    pipe = FakePipeline([{"total_return": 0.3, "sharpe": 1.5, "wfe": 0.7,
                          "num_trades": 20}])
    sid = "sess-open"
    final = await _run(
        sid, _open_req(budget={"max_iterations": 9, "max_configs": 6}), pipe
    )

    assert final["status"] == "complete"
    assert final["stopReason"] == "budget-exhausted"

    # J-12 invariant (staged form): ≥2 DISTINCT seed configs explored,
    # drawn ONLY from the bounded seed universe (no blind fan-out).
    cfgs = _distinct_cfgs(sid)
    assert len(cfgs) >= 2, f"expected ≥2 distinct configs, got {cfgs}"
    assert cfgs <= set(auto_session._SEED_UNIVERSE)

    # J-14: ≥3 cheap SCREEN markers, exactly k PROMOTE markers, k < screened.
    screen, promote = _stage_markers(sid)
    assert len(screen) == auto_session._SCREEN_SET_SIZE >= 3
    k = len(promote)
    assert 0 < k < len(screen), f"k={k} must be < screened={len(screen)}"
    assert k == auto_session._PROMOTE_TOP_K

    # Best is marked and is a PROMOTED iteration (robust over WF-bearing
    # promoted iterations only — the cheap screen proxy never leaks in).
    screen_nodes, promote_nodes = _nodes_by_stage(sid)
    assert len(screen_nodes) == len(screen)
    assert len(promote_nodes) == k
    assert final["bestIterationId"] is not None
    assert final["bestIterationId"] in {n["id"] for n in promote_nodes}
    # Staged max_configs semantics: a "config" against the cap is one
    # PROMOTE (expensive) candidate; SCREEN is cheap and not counted.
    assert final["spend"]["configsRun"] == k


async def test_open_universe_best_is_robust_not_raw_return(store):
    # STAGED FORM: best is the robust winner over PROMOTED (WF-bearing)
    # iterations only. A higher-raw-return SCREENED-ONLY candidate (no WF)
    # and a higher-raw-return WFE-failing PROMOTED candidate must NOT be
    # best. Per-config behaviour is keyed by (symbol,timeframe) so it is
    # deterministic regardless of SCREEN/PROMOTE call order.
    seed = auto_session._SEED_UNIVERSE
    s0, s1, s2, s3 = seed[0], seed[1], seed[2], seed[3]
    by_cfg = {
        # s0: top in-sample Sharpe -> PROMOTED; huge raw return but
        # WFE-failing -> robust gate-fail (must NOT be best).
        s0: {"sharpe": 2.0, "total_return": 5.0, "max_drawdown": 0.4,
             "num_trades": 30, "wfe": 0.0, "oos_return": -0.2,
             "oos_sharpe": -0.5, "num_windows": 2},
        # s1: 2nd in-sample Sharpe -> PROMOTED; modest but walk-forward
        # validated -> highest robust score (the expected best).
        s1: {"sharpe": 1.8, "total_return": 0.2, "max_drawdown": 0.08,
             "num_trades": 25, "wfe": 0.8, "oos_return": 0.15,
             "oos_sharpe": 1.0, "num_windows": 3},
        # s2/s3: low in-sample Sharpe -> SCREENED-ONLY (never promoted).
        # s2 has the single highest raw return in the whole run but no WF.
        s2: {"sharpe": 0.5, "total_return": 9.0, "max_drawdown": 0.5,
             "num_trades": 40},
        s3: {"sharpe": 0.4, "total_return": 0.1, "max_drawdown": 0.1,
             "num_trades": 15},
    }
    sid = "sess-open-best"
    final = await _run(
        sid,
        _open_req(model="claude-sonnet-4-6",
                  budget={"max_iterations": 9, "max_configs": 6}),
        FakePipeline([{}], by_cfg=by_cfg),
    )

    screen_nodes, promote_nodes = _nodes_by_stage(sid)
    assert {n["params"]["symbol"] for n in screen_nodes
            if (n["params"]["symbol"], n["params"]["timeframe"]) == s2}
    # s0 & s1 are the two promoted (top-2 by in-sample Sharpe 2.0/1.8).
    promoted_cfgs = {(n["params"]["symbol"], n["params"]["timeframe"])
                     for n in promote_nodes}
    assert promoted_cfgs == {s0, s1}, promoted_cfgs

    by_cfg_node = {(n["params"]["symbol"], n["params"]["timeframe"]): n
                   for n in promote_nodes}
    best = final["bestIterationId"]
    assert best == by_cfg_node[s1]["id"], "robust WF winner must be best"
    assert best != by_cfg_node[s0]["id"], (
        "the higher-raw-return WFE-failing PROMOTED config must NOT be best"
    )
    # The highest-raw-return candidate of the WHOLE run is the screened-only
    # s2 (return 9.0, no WF) — it must NOT be best (screen proxy never leaks).
    s2_screen_ids = {n["id"] for n in screen_nodes
                     if (n["params"]["symbol"],
                         n["params"]["timeframe"]) == s2}
    assert best not in s2_screen_ids, (
        "a higher-raw-return SCREENED-ONLY candidate must NOT be best"
    )


async def test_max_configs_cap_stops_open_universe_no_post_cap_config(store):
    # STAGED FORM (J-13 "no one more config past the cap" re-asserted, NOT
    # loosened): under staging a "config" counted against max_configs is one
    # PROMOTE (expensive) candidate. max_configs=1 with a planned top-k of 2
    # must stop at EXACTLY 1 promoted config — no second PROMOTE appended.
    pipe = FakePipeline([{"total_return": 0.3, "sharpe": 1.5, "wfe": 0.7,
                          "num_trades": 20}])
    sid = "sess-cfgcap"
    final = await _run(
        sid, _open_req(budget={"max_iterations": 9, "max_configs": 1}), pipe
    )
    assert final["status"] == "complete"
    assert final["stopReason"] == "budget-exhausted"

    screen, promote = _stage_markers(sid)
    # SCREEN is cheap & seed-bounded — it is NOT capped by max_configs.
    assert len(screen) == auto_session._SCREEN_SET_SIZE >= 3
    # Exactly ONE promoted config — the cap stopped the 2nd (planned k=2).
    assert len(promote) == 1, "no PROMOTE config may start past max_configs"
    assert final["spend"]["configsRun"] == 1
    screen_nodes, promote_nodes = _nodes_by_stage(sid)
    assert len(promote_nodes) == 1
    # generate_strategy is called once per SCREEN only (PROMOTE reuses the
    # screened strategy — no re-generation).
    assert pipe.gen_calls == auto_session._SCREEN_SET_SIZE
    cfgs = _distinct_cfgs(sid)
    assert len(cfgs) >= 2 and cfgs <= set(auto_session._SEED_UNIVERSE)


# =============================================================================
# iter-3 / J-13 — Hard, immutable AI-token/USD/configs/wall cost tracker.
# The tracker MUST accumulate the REAL token counts the (fake) SDK usage
# returned through the production capture path — fails if hardcoded/bypassed.
# =============================================================================

async def test_hard_token_budget_exhausted_real_usage_and_durable_spend(store):
    # STAGED FORM (J-13 real-spend + budget-exhausted + durable spend
    # re-asserted, NOT loosened): SCREEN generate calls (cheapest model) AND
    # the PROMOTE insights call (req.model) BOTH feed the same real-captured
    # record_usage path. The token cap is sized so all SCREEN generates plus
    # exactly ONE PROMOTE insights call land, and the cap then stops the next
    # PROMOTE — no config past the cap.
    from shared.model_catalog import cheapest_model, usd_cost

    step = {"total_return": 0.2, "sharpe": 1.5, "wfe": 0.7, "num_trades": 20,
            "gen_in": 80, "gen_out": 20, "ins_in": 120, "ins_out": 80}
    pipe = FakePipeline([step])
    sid = "sess-tokbudget"
    n_screen = auto_session._SCREEN_SET_SIZE
    # cap = all SCREEN generates fit; the first PROMOTE insights crosses it.
    cap = n_screen * (80 + 20) + 50          # 4*100 + 50 = 450
    final = await _run(
        sid,
        _open_req(model="claude-sonnet-4-6",
                  budget={"max_iterations": 9, "max_configs": 6,
                          "max_ai_tokens": cap}),
        pipe,
    )

    assert final["status"] == "complete"
    assert final["stopReason"] == "budget-exhausted"

    # Real-usage guard tied to the EXACT counts the fake SDK emitted through
    # the capture path: n_screen cheap-model generates + ONE req.model
    # insights call. Hardcoding/never-draining the sink fails this.
    cheap = cheapest_model()
    expected_tokens = n_screen * (80 + 20) + (120 + 80)
    expected_usd = (n_screen * usd_cost(cheap, 80, 20)
                    + usd_cost("claude-sonnet-4-6", 120, 80))
    assert final["spend"]["aiTokens"] == expected_tokens
    assert final["spend"]["usd"] == pytest.approx(expected_usd)
    assert expected_usd > 0.0

    # SCREEN used the cheapest catalog model; PROMOTE insights the stronger
    # req.model — same record_usage path, distinct prices.
    assert pipe.gen_calls == n_screen
    assert all(m == cheap for m in pipe.gen_models)
    assert pipe.insight_calls == 1
    assert pipe.insight_models == ["claude-sonnet-4-6"]

    # No config appended past the cap: exactly ONE PROMOTE (the in-flight
    # crossing call) and NO further screen/promote.
    screen, promote = _stage_markers(sid)
    assert len(screen) == n_screen
    assert len(promote) == 1
    assert len(ss.list_iteration_dirs(sid)) == n_screen + 1

    # Within one-call tolerance: only the single in-flight insights call
    # crossed the cap.
    assert final["spend"]["aiTokens"] <= cap + max(80 + 20, 120 + 80)

    # Durable: a FRESH read straight off disk (worker-restart / reload
    # survival proxy) still carries the recorded staged spend.
    meta = ss.read_session_meta(sid)
    assert meta["autoRun"]["stopReason"] == "budget-exhausted"
    assert meta["autoRun"]["spend"]["aiTokens"] == expected_tokens
    assert meta["autoRun"]["spend"]["configsRun"] == 1


async def test_open_universe_multi_config_runs_in_subprocess_distinct_pids(store):
    """STAGED FORM of the iter-2 subprocess-seam lesson: BOTH the cheap
    SCREEN backtests AND the PROMOTE backtests MUST flow through the existing
    subprocess seam — asserted DETERMINISTICALLY by child_pid != os.getpid()
    (never a timing bound). SCREEN being 'cheap' in LLM/engine work does NOT
    make it cheap in CPU, so it must not regress to an in-process backtest."""
    import os as _os

    pipe = FakePipeline([{"total_return": 0.2, "sharpe": 1.5, "wfe": 0.7}])
    executor = auto_session._subprocess_backtest_executor(
        f"{__name__}:_cpu_bound_backtest_child"
    )
    sid = "sess-open-subproc"
    try:
        final = await run_auto_session(
            sid,
            _open_req(budget={"max_iterations": 9, "max_configs": 2}),
            pipeline=pipe,
            semaphore=asyncio.Semaphore(1),
            cancel_token=CancellationToken(),
            backtest_executor=executor,
        )
    finally:
        auto_session._shutdown_backtest_worker()

    assert final["status"] == "complete"
    cfgs = _distinct_cfgs(sid)
    assert len(cfgs) >= 2, "≥2 distinct configs explored"
    assert cfgs <= set(auto_session._SEED_UNIVERSE)

    screen_nodes, promote_nodes = _nodes_by_stage(sid)
    assert len(screen_nodes) == auto_session._SCREEN_SET_SIZE >= 3
    assert len(promote_nodes) == auto_session._PROMOTE_TOP_K

    parent_pid = _os.getpid()
    # EVERY node — screened-only AND promoted — must have been backtested in
    # a different OS process (the deterministic, non-flaky seam guard).
    for node in screen_nodes + promote_nodes:
        run_id = (node.get("result") or {}).get("run_id", "")
        assert run_id.startswith("pid-"), f"unexpected run_id {run_id!r}"
        assert int(run_id.split("-", 1)[1]) != parent_pid, (
            f"a {node.get('stage')} backtest ran IN this process (anti-goal: "
            "the CPU-bound backtest MUST stay in the subprocess seam)"
        )
    # SCREEN nodes never carry walk-forward even though the subprocess stub
    # always returns a WF object (SCREEN is no-WF by construction).
    for node in screen_nodes:
        assert node.get("walkForwardResult") is None


# --- Endpoint: open-universe accepted; objective/date validation ------------

def test_open_universe_endpoint_accepted_and_listed(store, client, monkeypatch):
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    monkeypatch.setattr(auto_session, "_get_pipeline", lambda: pipe)

    resp = client.post("/api/auto-sessions", json={
        "natural_language": "EMA crossover trend follow",
        "objective": "robust",
        "budget": {"max_iterations": 2, "max_configs": 2},
    })
    assert resp.status_code == 200
    sid = resp.json()["sessionId"]
    assert sid

    tabs = client.get("/api/sessions").json()["tabs"]
    assert any(t["id"] == sid for t in tabs)

    data = client.get(f"/api/sessions/{sid}").json()
    assert data["autoRun"] is not None
    assert data["autoRun"]["status"] in (
        "running", "queued", "complete", "stopped"
    )


def test_open_universe_objective_and_history_scope_persisted(
    store, client, monkeypatch
):
    # TC-07 / spec "accepted & PERSISTED": objective + history_scope must be
    # durably written to the existing session store (readable after a fresh
    # re-read — the exact path a worker restart / browser reload takes) AND
    # surfaced in the GET /api/sessions/{id} payload, not merely validated
    # then discarded. history_scope's cross-run *learning* stays J-15/OUT;
    # only accept-&-persist is in scope this iteration.
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    monkeypatch.setattr(auto_session, "_get_pipeline", lambda: pipe)

    resp = client.post("/api/auto-sessions", json={
        "natural_language": "EMA crossover trend follow",
        "objective": "robust",
        "history_scope": "this-run",
        "budget": {"max_iterations": 1, "max_configs": 1},
    })
    assert resp.status_code == 200
    sid = resp.json()["sessionId"]

    # Durable: a fresh re-read of the on-disk session meta carries both
    # values verbatim (survives a restart/reload — it is a real file read).
    auto = ss.read_session_meta(sid)["autoRun"]
    assert auto["objective"] == "robust"
    assert auto["historyScope"] == "this-run"

    # Readable from the public session payload too (what the UI / QA see).
    payload_auto = client.get(f"/api/sessions/{sid}").json()["autoRun"]
    assert payload_auto["objective"] == "robust"
    assert payload_auto["historyScope"] == "this-run"


def test_history_scope_defaults_to_none_when_omitted(store, client, monkeypatch):
    # Omitted history_scope persists as null (accepted, no implicit value);
    # objective still defaults to and persists "robust".
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    monkeypatch.setattr(auto_session, "_get_pipeline", lambda: pipe)

    resp = client.post("/api/auto-sessions", json={
        "natural_language": "EMA crossover trend follow",
        "budget": {"max_iterations": 1, "max_configs": 1},
    })
    assert resp.status_code == 200
    sid = resp.json()["sessionId"]

    auto = ss.read_session_meta(sid)["autoRun"]
    assert auto["objective"] == "robust"
    assert auto["historyScope"] is None


def test_unsupported_objective_is_422(client):
    resp = client.post("/api/auto-sessions", json={
        "natural_language": "do something",
        "objective": "sharpe",
        "budget": {"max_iterations": 1},
    })
    assert resp.status_code == 422
    assert "objective" in resp.json()["detail"]


def test_open_universe_partial_dates_is_422_not_500(client):
    # Open-universe with only one of start/end -> clean 422, never a 500.
    resp = client.post("/api/auto-sessions", json={
        "natural_language": "explore",
        "objective": "robust",
        "start_date": "2023-01-01",
        "budget": {"max_iterations": 1},
    })
    assert resp.status_code == 422

    # Garbled date with both supplied -> clean 422, never a 500.
    resp2 = client.post("/api/auto-sessions", json={
        "natural_language": "explore",
        "objective": "robust",
        "start_date": "not-a-date",
        "end_date": "2023-02-01",
        "budget": {"max_iterations": 1},
    })
    assert resp2.status_code == 422


async def test_pinned_path_unchanged_by_open_universe_addition(store):
    # Regression guard: a pinned request still pins ONE (symbol,timeframe)
    # every iteration and keeps the prompt-refinement chain (J-07–J-11).
    pipe = FakePipeline([{"total_return": 0.1, "wfe": 0.7}])
    sid = "sess-pinned-unchanged"
    final = await _run(sid, _req(budget={"max_iterations": 3}), pipe)

    assert pipe.gen_calls == 3
    assert _distinct_cfgs(sid) == {("BTCUSDT", "1h")}
    assert final["stopReason"] == "budget-exhausted"
    assert final["spend"]["configsRun"] == 3  # tracker runs for pinned too
    # No SCREEN/PROMOTE/"Exploring config" entries on the pinned path.
    log = ss.read_activity_log(sid)
    assert not any(e["content"].startswith("Exploring config") for e in log)
    assert not any(e["content"].startswith(("SCREEN", "PROMOTE")) for e in log)

    # === CARRIED B1 REGRESSION GUARD (iter-3 audit B1 / T2) ===============
    # On the FINAL pinned iteration the cost tracker's max_configs == max_iter
    # (the _build_cost_tracker pinned `max_cfg == max_iter` branch), so
    # `tracker.would_exceed()` returns the "max-configs" SENTINEL right after
    # that iteration's generate. The B1 insights gate must skip insights ONLY
    # on a true spend cap (ai-tokens/usd/wall-clock) and NEVER on
    # "max-configs" — otherwise the final pinned iteration's insights /
    # prompt-refinement chain (J-04 / J-07–J-11) is silently suppressed.
    # This assertion goes RED under a naive truthy-`would_exceed()` gate
    # (insight_calls would be 2) and GREEN with the spend-cap-only gate.
    assert pipe.insight_calls == 3, (
        "every pinned iteration — INCLUDING the final one whose "
        "would_exceed()=='max-configs' — must still call insights"
    )


async def test_b1_true_spend_cap_between_generate_and_insights_skips_one(store):
    # POSITIVE B1: a real spend cap (ai-tokens) crossed by `generate` itself
    # (round-top check passed, then generate's drained usage tips it over)
    # MUST skip exactly that one iteration's insights call while STILL
    # building/writing the iteration node + recording activity. The next
    # round-top check then terminates the run budget-exhausted.
    step = {"total_return": 0.2, "sharpe": 1.5, "wfe": 0.7, "num_trades": 20,
            "gen_in": 80, "gen_out": 20, "ins_in": 500, "ins_out": 500}
    pipe = FakePipeline([step])
    sid = "sess-b1-pos"
    # Round-top sees 0 < 90 -> proceeds; generate drains 100 >= 90 -> the
    # B1 gate (ai-tokens) skips THIS iteration's insights only.
    final = await _run(
        sid, _req(budget={"max_iterations": 3, "max_ai_tokens": 90}), pipe
    )

    assert final["status"] == "complete"
    assert final["stopReason"] == "budget-exhausted"
    assert pipe.gen_calls == 1, "round 2 must not start (cap reached)"
    assert pipe.insight_calls == 0, "the one in-flight insights call is skipped"

    # The iteration is STILL written (skip insights != skip the iteration).
    dirs = ss.list_iteration_dirs(sid)
    assert len(dirs) == 1
    node = ss.read_iteration_full(sid, dirs[0].name.split("_", 1)[1])
    assert node["status"] == "complete"
    assert node["result"]["total_return"] == pytest.approx(0.2)
    assert (node["insights"] or {}).get("suggestions") in (None, [], )
    # Spend is the real generate-only usage (insights never ran).
    assert final["spend"]["aiTokens"] == 80 + 20
    # Activity for the iteration is still recorded.
    log = ss.read_activity_log(sid)
    assert any(e["type"] == "complete" for e in log)


async def test_screen_stage_cheap_model_no_wf_no_insights(store):
    # TC-13: every screened-only config runs wfv_enabled=False, generation
    # uses the catalog-resolved CHEAPEST model (NOT req.model, NOT a
    # literal), and generate_insights is NOT called for screened-only
    # configs. req.model is a non-cheapest model so the distinction is real.
    from shared.model_catalog import MODEL_PRICING, cheapest_model

    cheap = cheapest_model()
    assert cheap == min(MODEL_PRICING,
                        key=lambda m: (sum(MODEL_PRICING[m]), m))
    assert cheap != "claude-sonnet-4-6", "req.model must differ from cheapest"

    pipe = FakePipeline([{"total_return": 0.3, "sharpe": 1.5, "wfe": 0.7,
                          "num_trades": 20}])
    sid = "sess-screen"
    final = await _run(
        sid,
        _open_req(model="claude-sonnet-4-6",
                  budget={"max_iterations": 9, "max_configs": 6}),
        pipe,
    )
    assert final["status"] == "complete"

    n_screen = auto_session._SCREEN_SET_SIZE
    k = auto_session._PROMOTE_TOP_K
    screen_nodes, promote_nodes = _nodes_by_stage(sid)
    assert len(screen_nodes) == n_screen
    assert len(promote_nodes) == k

    # generate_strategy called once per SCREEN only; ALL with the cheapest
    # model (assertion derives from MODEL_PRICING, not a string literal).
    assert pipe.gen_calls == n_screen
    assert pipe.gen_models == [cheap] * n_screen

    # The first n_screen backtests (SCREEN) are wfv_enabled=False; the
    # PROMOTE backtests are wfv_enabled=True.
    assert pipe.bt_wfv[:n_screen] == [False] * n_screen
    assert all(pipe.bt_wfv[n_screen:]) and len(pipe.bt_wfv) == n_screen + k

    # Screened-only nodes: no walk-forward, cheap model, no insights.
    promoted_cfgs = {(n["params"]["symbol"], n["params"]["timeframe"])
                     for n in promote_nodes}
    for node in screen_nodes:
        cfg = (node["params"]["symbol"], node["params"]["timeframe"])
        assert node["stage"] == "screen"
        assert node["walkForwardResult"] is None
        assert node["walkForwardStatus"] == "idle"
        assert node["modelUsed"] == cheap
        if cfg not in promoted_cfgs:  # a screened-ONLY config
            assert not (node["insights"] or {}).get("suggestions")

    # insights ran ONLY for the k promoted configs (zero for screened-only).
    assert pipe.insight_calls == k


async def test_screen_stage_failure_is_recorded_loop_continues(store):
    # TC-06/TC-13 resilience: a SCREEN-stage generate-validation failure must
    # be RECORDED and the loop must continue to a terminal state (a single
    # bad screened config must not abort the run).
    seed = auto_session._SEED_UNIVERSE
    by_cfg = {seed[1]: {"gen_fail": "uncompilable strategy code"}}
    pipe = FakePipeline([{"total_return": 0.3, "sharpe": 1.5, "wfe": 0.7,
                          "num_trades": 20}], by_cfg=by_cfg)
    sid = "sess-screen-fail"
    final = await _run(
        sid, _open_req(budget={"max_iterations": 9, "max_configs": 6}), pipe
    )

    assert final["status"] == "complete"
    assert final["stopReason"] == "budget-exhausted"

    # The failed screened config is recorded as an error iteration.
    statuses = sorted(
        ss.read_iteration_meta(sid, d.name.split("_", 1)[1])["status"]
        for d in ss.list_iteration_dirs(sid)
    )
    assert "error" in statuses, "the failed SCREEN config must be recorded"
    # The loop still screened the other seeds and promoted survivors.
    screen, promote = _stage_markers(sid)
    assert len(screen) == auto_session._SCREEN_SET_SIZE
    assert 0 < len(promote) < len(screen)
    # An error entry exists and later SCREEN/PROMOTE entries follow it.
    log = ss.read_activity_log(sid)
    err_idx = next(i for i, e in enumerate(log) if e["type"] == "error")
    assert any(e["type"] == "auto-run" and e["content"].startswith("PROMOTE")
               for e in log[err_idx:]), "loop continued past the failure"


async def test_promote_stage_reuses_screened_strategy_full_pipeline(store):
    # TC-14: each PROMOTE runs the FULL pipeline (wfv_enabled=True +
    # req.model insights) and REUSES the screened candidate's already-
    # generated strategy (same scriptId / identical code hash — NO second
    # generate_strategy); promotion is top-k with k < number screened.
    pipe = FakePipeline([{"total_return": 0.3, "sharpe": 1.5, "wfe": 0.7,
                          "num_trades": 20}])
    sid = "sess-promote"
    final = await _run(
        sid,
        _open_req(model="claude-sonnet-4-6",
                  budget={"max_iterations": 9, "max_configs": 6}),
        pipe,
    )
    assert final["status"] == "complete"

    n_screen = auto_session._SCREEN_SET_SIZE
    k = auto_session._PROMOTE_TOP_K
    screen_nodes, promote_nodes = _nodes_by_stage(sid)
    assert len(promote_nodes) == k
    assert 0 < k < len(screen_nodes) == n_screen, "k must be < screened"

    # NO second generate_strategy for promotion (reuse): generate is called
    # exactly once per SCREEN, never for a PROMOTE.
    assert pipe.gen_calls == n_screen

    screen_by_cfg = {(n["params"]["symbol"], n["params"]["timeframe"]): n
                     for n in screen_nodes}
    for pnode in promote_nodes:
        cfg = (pnode["params"]["symbol"], pnode["params"]["timeframe"])
        snode = screen_by_cfg[cfg]
        # Reuses the SCREEN candidate's strategy: identical scriptId + code
        # hash (no re-generation).
        assert pnode["scriptId"] == snode["scriptId"]
        assert pnode["scriptCode"] == snode["scriptCode"]
        # Full pipeline on the promoted config: WF present + stronger model.
        assert pnode["stage"] == "promote"
        assert pnode["walkForwardResult"] is not None
        assert pnode["walkForwardStatus"] == "complete"
        assert pnode["modelUsed"] == "claude-sonnet-4-6"
        assert (pnode["insights"] or {}).get("suggestions")

    # PROMOTE insights all used the stronger req.model.
    assert pipe.insight_calls == k
    assert pipe.insight_models == ["claude-sonnet-4-6"] * k
    # Best is a promoted iteration chosen by the robust objective.
    assert final["bestIterationId"] in {n["id"] for n in promote_nodes}
