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
