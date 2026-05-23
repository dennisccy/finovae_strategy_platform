"""Live, end-to-end smoke for the headless auto-session loop.

Exercises the REAL ``BacktestPipeline`` (real OpenAI strategy generation +
insights, real Binance OHLCV fetch, the RestrictedPython sandbox, the
deterministic next-bar engine, real walk-forward) — NOT a fake — with a tiny
real budget per docs/goal.md (1 round, short date range, cheapest default
model).  Asserts a real terminal state + a marked best.

Gated on OPENAI_API_KEY (loaded from apps/backend/.env, the same source the app
uses).  Skipped — never silently passed — when the key is absent.  Marked
``integration`` so it is excluded from the fast hermetic run via ``-m "not
integration"``.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

import backend.session_store as ss
from backend.auto_session import AutoSessionController, BudgetTracker, is_terminal
from tests.auto_session_helpers import build_config

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
_HAS_KEY = bool(os.environ.get("OPENAI_API_KEY"))
_HAS_ANTHROPIC_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_KEY, reason="OPENAI_API_KEY not set — live smoke skipped")
async def test_live_auto_session_reaches_terminal_with_best(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "BASE_DIR", tmp_path / "store")
    ss.initialize()

    from backend.pipeline import BacktestPipeline

    pipeline = BacktestPipeline()
    config = build_config(
        natural_language=("Buy when the 20-period RSI crosses below 30 and "
                          "sell when it crosses above 70."),
        symbol="BTC/USDT",
        timeframe="1h",
        start_date="2023-01-01",
        end_date="2023-04-01",   # ~3 months — tiny
        targets={},              # no targets → run to (tiny) budget
        wfv_is_months=1,
        wfv_oos_months=1,
    )
    controller = AutoSessionController(
        "live-smoke", config, BudgetTracker(max_iterations=1), pipeline)

    auto_run = await controller.run()

    # Reached a real terminal state with a marked best.
    assert is_terminal(auto_run["status"]), auto_run
    assert auto_run["bestIterationId"] is not None
    assert auto_run["endedAt"] is not None

    # The best iteration is a real, browsable backtest record.
    best = ss.read_iteration_full("live-smoke", auto_run["bestIterationId"])
    assert best is not None
    assert best["result"] is not None
    assert isinstance(best["result"]["num_trades"], int)
    assert "equity_curve" in best["result"]


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_KEY, reason="OPENAI_API_KEY not set — staged live smoke skipped")
@pytest.mark.skipif(not _HAS_ANTHROPIC_KEY,
                    reason="ANTHROPIC_API_KEY not set — staged PROMOTE model unavailable")
async def test_live_open_universe_staged_screen_promote(tmp_path, monkeypatch):
    """Live end-to-end J-14: a real open-universe run SCREENs several seed configs
    cheap (cheapest model via OpenAI, no walk-forward) and PROMOTEs only the top-k
    (k < screened) to walk-forward + the stronger model (claude-haiku-4-5 via
    Anthropic). Exercises BOTH providers and the real pipeline/sandbox/engine. The
    marked best (if any) is a promoted, WFE-bearing node — never screened-only.

    This is the spec's recommended live QA recipe, pre-validated here at the
    backend level (the layer the UI's GET /api/sessions/{id} polls)."""
    monkeypatch.setattr(ss, "BASE_DIR", tmp_path / "store")
    ss.initialize()

    from backend.pipeline import BacktestPipeline
    from shared.model_catalog import cheapest_model

    pipeline = BacktestPipeline()
    # Open-universe: no symbol/timeframe (the seed universe varies them). A pinned
    # EMA crossover reliably trades, so a promoted candidate is eligible and the
    # best-marking path is exercised (not just gated to None).
    config = build_config(
        natural_language=("Go long when the 10-period EMA crosses above the "
                          "30-period EMA; exit when it crosses back below."),
        symbol=None,
        timeframe=None,
        start_date="2023-01-01",
        end_date="2023-04-01",        # ~3 months — tiny, keeps cost low
        model="claude-haiku-4-5",     # the stronger PROMOTE model (≠ cheapest SCREEN model)
        targets={},
        wfv_is_months=1,
        wfv_oos_months=1,
    )
    # max_configs=3 → SCREEN 3 seed configs, PROMOTE top-1 (k=1<3). Generous
    # token/USD caps so screen+promote complete (the hard-cap demo is J-13, green).
    budget = BudgetTracker(max_iterations=2, max_configs=3,
                           max_tokens=2_000_000, max_usd=5.0)
    controller = AutoSessionController(
        "live-staged", config, budget, pipeline, open_universe=True)

    auto_run = await controller.run()

    assert is_terminal(auto_run["status"]), auto_run
    assert auto_run["endedAt"] is not None

    nodes = [ss.read_iteration_full("live-staged", d.name.split("_", 1)[1])
             for d in ss.list_iteration_dirs("live-staged")]
    screened = [n for n in nodes if n["walkForwardStatus"] is None]
    promoted = [n for n in nodes if n["walkForwardStatus"] == "complete"]

    # SCREEN: several cheap candidates, NO walk-forward, on the cheapest model.
    assert len(screened) >= 2
    assert all(n["modelUsed"] == cheapest_model() for n in screened)
    # PROMOTE: only the top-k (k < number screened), walk-forward + stronger model.
    assert len(promoted) >= 1
    assert len(promoted) < len(screened)
    assert all(n["modelUsed"] == "claude-haiku-4-5" for n in promoted)
    # Best (if marked) is a promoted, WFE-bearing node — never a screened-only one.
    if auto_run["bestIterationId"] is not None:
        best = ss.read_iteration_full("live-staged", auto_run["bestIterationId"])
        assert best["walkForwardStatus"] == "complete"
        assert best["modelUsed"] == "claude-haiku-4-5"

    # Both stages are legible in the Activity Log (the surface the UI renders).
    activity = ss.read_activity_log("live-staged")
    contents = [e.get("content", "") for e in activity if e["type"] == "auto-run"]
    assert any(c.startswith("SCREEN") for c in contents), contents
    assert any(c.startswith("PROMOTE") for c in contents), contents
    # No secrets leaked into the persisted artifacts.
    blob = repr(ss.read_session_meta("live-staged")) + repr(activity)
    for needle in ("api_key", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "sk-"):
        assert needle not in blob
