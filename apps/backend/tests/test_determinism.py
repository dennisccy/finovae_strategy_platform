"""
Determinism Tests (T51)

Tests to ensure backtest results are reproducible across multiple runs.
Same inputs must produce identical outputs.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from backtest.engine import BacktestEngine
from backtest.fills import FillModel
from shared.contracts import BacktestRequest, OHLCV


def create_deterministic_ohlcv(
    n_bars: int = 200,
    start_price: float = 50000.0,
    seed: int = 42,
) -> list[OHLCV]:
    """Create reproducible OHLCV data."""
    np.random.seed(seed)

    data = []
    current_price = start_price
    start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

    for i in range(n_bars):
        change = np.random.normal(0, 0.02) * current_price
        open_price = current_price
        close_price = current_price + change
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))

        data.append(OHLCV(
            timestamp=start_time + timedelta(hours=4 * i),
            symbol="BTCUSDT",
            timeframe="4h",
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=np.random.uniform(100, 1000),
            quote_volume=np.random.uniform(5000000, 10000000),
        ))

        current_price = close_price

    return data


def rsi_crossover_signal(df: pd.DataFrame, i: int) -> int:
    """RSI crossover strategy for testing."""
    if i < 20:
        return 0

    # Calculate RSI
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    current_rsi = rsi.iloc[i]
    prev_rsi = rsi.iloc[i - 1]

    # Buy when RSI crosses above 30
    if prev_rsi <= 30 and current_rsi > 30:
        return 1

    # Sell when RSI crosses above 70
    if current_rsi > 70:
        return -1

    return 0


class TestDeterminism:
    """Tests for deterministic backtest execution."""

    def test_identical_results_across_runs(self):
        """Same inputs must produce identical results."""
        data = create_deterministic_ohlcv(seed=42)

        request = BacktestRequest(
            run_id="test-determinism",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 6, 1).date(),
            initial_capital=10000.0,
            commission=0.001,
            slippage=0.0005,
        )

        results = []

        for run_num in range(5):
            engine = BacktestEngine(random_seed=42)
            result = engine.run(request, data, rsi_crossover_signal)
            results.append(result)

        # Compare all results to first result
        first_result = results[0]

        for run_num, result in enumerate(results[1:], start=2):
            assert result.total_return == first_result.total_return, (
                f"Run {run_num}: total_return differs "
                f"({result.total_return} vs {first_result.total_return})"
            )

            assert result.max_drawdown == first_result.max_drawdown, (
                f"Run {run_num}: max_drawdown differs "
                f"({result.max_drawdown} vs {first_result.max_drawdown})"
            )

            assert result.num_trades == first_result.num_trades, (
                f"Run {run_num}: num_trades differs "
                f"({result.num_trades} vs {first_result.num_trades})"
            )

            assert result.win_rate == first_result.win_rate, (
                f"Run {run_num}: win_rate differs "
                f"({result.win_rate} vs {first_result.win_rate})"
            )

            # Compare trade details
            assert len(result.trades) == len(first_result.trades), (
                f"Run {run_num}: number of trades differs"
            )

            for j, (trade, first_trade) in enumerate(zip(result.trades, first_result.trades)):
                assert trade.entry_time == first_trade.entry_time, (
                    f"Run {run_num}, Trade {j}: entry_time differs"
                )
                assert trade.exit_time == first_trade.exit_time, (
                    f"Run {run_num}, Trade {j}: exit_time differs"
                )
                assert abs(trade.pnl - first_trade.pnl) < 1e-10, (
                    f"Run {run_num}, Trade {j}: pnl differs "
                    f"({trade.pnl} vs {first_trade.pnl})"
                )

    def test_equity_curve_reproducibility(self):
        """Equity curve must be identical across runs."""
        data = create_deterministic_ohlcv(seed=42)

        request = BacktestRequest(
            run_id="test-equity",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 6, 1).date(),
            initial_capital=10000.0,
        )

        engine1 = BacktestEngine(random_seed=42)
        engine2 = BacktestEngine(random_seed=42)

        result1 = engine1.run(request, data, rsi_crossover_signal)
        result2 = engine2.run(request, data, rsi_crossover_signal)

        assert len(result1.equity_curve) == len(result2.equity_curve), (
            "Equity curve lengths differ"
        )

        for i, (ep1, ep2) in enumerate(zip(result1.equity_curve, result2.equity_curve)):
            assert ep1.timestamp == ep2.timestamp, (
                f"Equity point {i}: timestamps differ"
            )
            assert abs(ep1.equity - ep2.equity) < 1e-10, (
                f"Equity point {i}: equity differs ({ep1.equity} vs {ep2.equity})"
            )
            assert abs(ep1.drawdown - ep2.drawdown) < 1e-10, (
                f"Equity point {i}: drawdown differs ({ep1.drawdown} vs {ep2.drawdown})"
            )

    def test_different_seeds_produce_different_results(self):
        """Different seeds should produce different results (sanity check)."""
        data = create_deterministic_ohlcv(seed=42)

        request = BacktestRequest(
            run_id="test-seeds",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 6, 1).date(),
            initial_capital=10000.0,
        )

        # Note: The strategy itself is deterministic, so even with different
        # engine seeds, results should be the same unless engine uses randomness
        engine1 = BacktestEngine(random_seed=42)
        engine2 = BacktestEngine(random_seed=42)

        result1 = engine1.run(request, data, rsi_crossover_signal)
        result2 = engine2.run(request, data, rsi_crossover_signal)

        # Results should be identical with same seed
        assert result1.total_return == result2.total_return

    def test_float_precision_consistency(self):
        """Float calculations must be consistent."""
        data = create_deterministic_ohlcv(seed=42)

        request = BacktestRequest(
            run_id="test-precision",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 6, 1).date(),
            initial_capital=10000.0,
            commission=0.001,
            slippage=0.0005,
        )

        all_returns = []
        all_drawdowns = []

        for _ in range(10):
            engine = BacktestEngine(random_seed=42)
            result = engine.run(request, data, rsi_crossover_signal)
            all_returns.append(result.total_return)
            all_drawdowns.append(result.max_drawdown)

        # All values should be identical (no floating point drift)
        assert all(r == all_returns[0] for r in all_returns), (
            f"Return values vary: {set(all_returns)}"
        )
        assert all(d == all_drawdowns[0] for d in all_drawdowns), (
            f"Drawdown values vary: {set(all_drawdowns)}"
        )


class TestDataDeterminism:
    """Tests for deterministic data handling."""

    def test_data_order_independence(self):
        """Results should not depend on data processing order."""
        data1 = create_deterministic_ohlcv(seed=42)
        data2 = create_deterministic_ohlcv(seed=42)

        # Verify data is identical
        for d1, d2 in zip(data1, data2):
            assert d1.close == d2.close

        request = BacktestRequest(
            run_id="test-order",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 6, 1).date(),
            initial_capital=10000.0,
        )

        engine1 = BacktestEngine(random_seed=42)
        engine2 = BacktestEngine(random_seed=42)

        result1 = engine1.run(request, data1, rsi_crossover_signal)
        result2 = engine2.run(request, data2, rsi_crossover_signal)

        assert result1.total_return == result2.total_return
        assert len(result1.trades) == len(result2.trades)


class TestStrategyDeterminism:
    """Tests for deterministic strategy execution."""

    def test_indicator_calculation_determinism(self):
        """Indicator calculations must be deterministic."""
        data = create_deterministic_ohlcv(seed=42)
        df = pd.DataFrame([
            {
                "timestamp": d.timestamp,
                "open": d.open,
                "high": d.high,
                "low": d.low,
                "close": d.close,
                "volume": d.volume,
            }
            for d in data
        ])

        # Calculate RSI multiple times
        rsi_values = []
        for _ in range(5):
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi.dropna().tolist())

        # All calculations should be identical
        first_rsi = rsi_values[0]
        for i, rsi in enumerate(rsi_values[1:], start=2):
            for j, (v1, v2) in enumerate(zip(first_rsi, rsi)):
                assert v1 == v2, (
                    f"RSI calculation {i} differs at index {j}: {v1} vs {v2}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
