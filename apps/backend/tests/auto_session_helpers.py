"""Shared fakes/factories for the auto-session tests.

NOT collected as a test module (filename does not match ``test_*``).  Provides a
deterministic, hermetic ``FakePipeline`` (no live LLM) plus dataclass factories
so the loop is testable cheaply and repeatably — the controller accepts an
injected pipeline expressly for this.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from shared.contracts import (
    BacktestResult,
    CategoryRating,
    EquityPoint,
    GenerateStrategyResult,
    StrategyRating,
    Trade,
    WalkForwardResult,
)
from shared.model_catalog import TokenUsage

_UTC = timezone.utc


def make_backtest_result(
    *,
    run_id: str = "run",
    total_return: float = 0.1,
    sharpe: float = 1.0,
    num_trades: int = 10,
    max_drawdown: float = 0.1,
    win_rate: float = 0.5,
    profit_factor: float = 1.5,
    margin_called: bool = False,
) -> BacktestResult:
    equity = [
        EquityPoint(timestamp=datetime(2024, 1, 1, tzinfo=_UTC), equity=10000.0, drawdown=0.0),
        EquityPoint(
            timestamp=datetime(2024, 1, 2, tzinfo=_UTC),
            equity=max(1.0, 10000.0 * (1.0 + total_return)),
            drawdown=min(0.99, max(0.0, max_drawdown)),
        ),
    ]
    trades = [
        Trade(
            trade_id=f"{run_id}-t{i}",
            entry_time=datetime(2024, 1, 1, tzinfo=_UTC),
            exit_time=datetime(2024, 1, 2, tzinfo=_UTC),
            entry_price=100.0,
            exit_price=110.0,
            quantity=1.0,
            pnl=10.0,
            pnl_percent=0.1,
            commission_paid=0.1,
        )
        for i in range(num_trades)
    ]
    return BacktestResult(
        run_id=run_id,
        total_return=total_return,
        max_drawdown=max_drawdown,
        num_trades=num_trades,
        win_rate=win_rate,
        sharpe_ratio=sharpe,
        profit_factor=profit_factor,
        equity_curve=equity,
        trades=trades,
        margin_called=margin_called,
        unleveraged_return=None,
    )


def make_rating() -> StrategyRating:
    def cat(name: str) -> CategoryRating:
        return CategoryRating(
            name=name, label=name.replace("_", " ").title(), stars=3,
            key_metrics={}, analyses={},
        )

    return StrategyRating(
        profitability=cat("profitability"),
        risk_resistance=cat("risk_resistance"),
        risk_reward=cat("risk_reward"),
        win_rate_ev=cat("win_rate_ev"),
        liquidity=cat("liquidity"),
        benchmark_equity=[],
        benchmark_total_return=0.0,
        monthly_returns=[],
        trade_excursions=[],
        drawdown_periods=[],
        rolling_sharpe=[],
        rolling_sharpe_benchmark=[],
        return_distribution=[],
        simulated_stops=[],
        simulated_take_profits=[],
        capacity_levels=[],
        annual_returns={},
        benchmark_annual_returns={},
        annual_long_returns={},
        annual_short_returns={},
    )


def make_wf_result(
    *, wfe: float = 0.6, is_months: int = 6, oos_months: int = 3
) -> WalkForwardResult:
    return WalkForwardResult(
        windows=[],
        num_windows=0,
        is_months=is_months,
        oos_months=oos_months,
        combined_oos_return=0.05,
        combined_oos_sharpe=0.5,
        combined_oos_win_rate=0.5,
        combined_oos_max_drawdown=0.1,
        wfe=wfe,
        combined_oos_equity=[],
        errors=[],
    )


@dataclass
class FakeSpec:
    """One backtest outcome the fake pipeline returns (in call order)."""
    total_return: float = 0.1
    sharpe: float = 1.0
    num_trades: int = 10
    max_drawdown: float = 0.1
    wfe: float = 0.6
    margin_called: bool = False


class FakePipeline:
    """Deterministic stand-in for ``BacktestPipeline`` (no live LLM).

    ``execute_backtest`` returns the next :class:`FakeSpec` in ``sequence`` (call
    order); ``generate_insights`` returns ``suggestions_per_round`` suggestions.
    Optional hooks: ``gate`` (an ``asyncio.Event`` awaited at the start of
    ``generate_strategy`` so a run can be parked mid-flight) and ``on_exec``
    (called with the 1-based execute-call index, e.g. to inject a stop request).

    Token accounting (J-13): when ``usage`` is given, each ``generate_strategy``
    and ``generate_insights`` exposes it on ``last_strategy_usage`` /
    ``last_insights_usage`` (the same side channel the real pipeline surfaces).
    ``fail_exec_indices`` makes the given 1-based backtest calls fail (to test
    non-fatal config failures); ``fixed_code`` makes every generated script
    identical (to exercise the code-hash backtest dedup).
    """

    def __init__(
        self,
        *,
        sequence,
        suggestions_per_round: int = 1,
        with_rating: bool = True,
        gate: Optional[asyncio.Event] = None,
        on_exec: Optional[Callable[[int], None]] = None,
        usage: Optional[TokenUsage] = None,
        fail_exec_indices: Optional[set] = None,
        fixed_code: Optional[str] = None,
    ) -> None:
        self.sequence = list(sequence)
        self.suggestions_per_round = suggestions_per_round
        self.with_rating = with_rating
        self.gate = gate
        self.on_exec = on_exec
        self.usage = usage
        self.fail_exec_indices = fail_exec_indices or set()
        self.fixed_code = fixed_code
        self.generate_calls: list[dict] = []
        self.execute_calls: list[dict] = []
        self.insights_calls = 0
        # Side channel mirrored from the real BacktestPipeline.
        self.last_strategy_usage: Optional[TokenUsage] = None
        self.last_insights_usage: Optional[TokenUsage] = None

    async def generate_strategy(self, *, natural_language, model="gpt-5.4-mini",
                                previous_script_code=None, **kwargs):
        if self.gate is not None:
            await self.gate.wait()
        self.generate_calls.append({"nl": natural_language, "prev": previous_script_code})
        sid = f"scr-{len(self.generate_calls)}"
        code = self.fixed_code if self.fixed_code is not None else (
            f"# strategy {sid}\nclass Strategy:\n    pass\n")
        self.last_strategy_usage = self.usage
        return GenerateStrategyResult(
            script_id=sid,
            script_code=code,
            strategy_name=f"Strategy {sid}",
            strategy_description="generated by fake",
            validation_errors=[],
            model_used=model,
        )

    async def execute_backtest(self, *, script_id, symbol, timeframe, start_date, end_date,
                               wfv_enabled=False, **kwargs):
        idx = len(self.execute_calls) + 1
        self.execute_calls.append({"script_id": script_id, "wfv_enabled": wfv_enabled,
                                   "symbol": symbol, "timeframe": timeframe})
        if self.on_exec is not None:
            self.on_exec(idx)
        if idx in self.fail_exec_indices:
            return None, ["forced backtest failure"], None, {"total_ms": 1.0}, None
        spec = self.sequence[min(idx - 1, len(self.sequence) - 1)]
        result = make_backtest_result(
            run_id=script_id,
            total_return=spec.total_return,
            sharpe=spec.sharpe,
            num_trades=spec.num_trades,
            max_drawdown=spec.max_drawdown,
            margin_called=spec.margin_called,
        )
        rating = make_rating() if self.with_rating else None
        wf = make_wf_result(wfe=spec.wfe) if wfv_enabled else None
        return result, [], rating, {"total_ms": 1.0}, wf

    async def generate_insights(self, *, backtest_result, **kwargs):
        self.insights_calls += 1
        self.last_insights_usage = self.usage
        suggestions = [
            {
                "title": f"S{self.insights_calls}.{j}",
                "description": "suggestion description",
                "prompt": f"improvement idea {self.insights_calls}.{j}",
            }
            for j in range(self.suggestions_per_round)
        ]
        return "summary text", suggestions, []


def build_config(**overrides):
    """Construct an AutoSessionConfig with sensible test defaults."""
    from backend.auto_session import AutoSessionConfig

    base = dict(
        natural_language="Buy when RSI < 30, sell when RSI > 70",
        symbol="BTC/USDT",
        timeframe="1h",
        start_date="2023-01-01",
        end_date="2023-06-01",
        initial_capital=10000.0,
        targets={},
    )
    base.update(overrides)
    return AutoSessionConfig(**base)
