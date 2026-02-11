"""
Lookahead Bias / Leakage Tests (T50)

Tests to ensure the backtesting engine does not use future data
when generating signals or executing trades.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from backtest.engine import BacktestEngine
from backtest.fills import FillModel
from shared.contracts import BacktestRequest, OHLCV


def create_test_ohlcv(n_bars: int = 100, start_price: float = 50000.0) -> list[OHLCV]:
    """Create synthetic OHLCV data for testing."""
    data = []
    current_price = start_price
    start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

    for i in range(n_bars):
        # Random walk
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


class TestNoLookahead:
    """Tests that verify no lookahead bias exists."""

    def test_signal_receives_only_historical_data(self):
        """Signal function should only receive data up to current bar."""
        np.random.seed(42)
        data = create_test_ohlcv(100)
        engine = BacktestEngine(random_seed=42)

        received_lengths = []

        def tracking_signal(df: pd.DataFrame, i: int) -> int:
            """Track the length of data received."""
            received_lengths.append(len(df))
            return 0  # No trades, just track

        request = BacktestRequest(
            run_id="test-lookahead",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 3, 1).date(),
            initial_capital=10000.0,
        )

        engine.run(request, data, tracking_signal)

        # Each call should receive exactly i+1 rows (0 to i inclusive)
        for idx, length in enumerate(received_lengths):
            assert length == idx + 1, (
                f"At bar {idx}, received {length} rows instead of {idx + 1}. "
                "This indicates potential lookahead bias."
            )

    def test_signal_cannot_see_future_close_prices(self):
        """Ensure signal function cannot access future close prices."""
        np.random.seed(42)
        data = create_test_ohlcv(100)
        engine = BacktestEngine(random_seed=42)

        # Create data with known future values
        for i in range(50, 100):
            data[i] = OHLCV(
                timestamp=data[i].timestamp,
                symbol="BTCUSDT",
                timeframe="4h",
                open=data[i].open,
                high=data[i].high,
                low=data[i].low,
                close=99999.99,  # Distinctive future price
                volume=data[i].volume,
                quote_volume=data[i].quote_volume,
            )

        seen_future_price = []

        def check_future_signal(df: pd.DataFrame, i: int) -> int:
            """Check if any future price is visible."""
            close_values = df["close"].values
            # Check if we can see the distinctive future price
            if any(close >= 99999.0 for close in close_values):
                # We should only see it if i >= 50
                if i < 50:
                    seen_future_price.append(i)
            return 0

        request = BacktestRequest(
            run_id="test-future",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 3, 1).date(),
            initial_capital=10000.0,
        )

        engine.run(request, data, check_future_signal)

        assert len(seen_future_price) == 0, (
            f"Future prices visible at bars: {seen_future_price}. "
            "This is a critical lookahead bias."
        )

    def test_next_bar_execution(self):
        """Verify signals execute on next bar's open, not current bar."""
        np.random.seed(42)
        data = create_test_ohlcv(100)
        engine = BacktestEngine(random_seed=42)

        signal_bars = []
        execution_bars = []

        def signal_on_bar_50(df: pd.DataFrame, i: int) -> int:
            """Generate buy signal only on bar 50."""
            if i == 50:
                signal_bars.append(i)
                return 1
            return 0

        # Track executions by inspecting trades
        request = BacktestRequest(
            run_id="test-nextbar",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 3, 1).date(),
            initial_capital=10000.0,
        )

        result = engine.run(request, data, signal_on_bar_50)

        # If we signaled on bar 50, trade should execute at bar 51's timestamp
        if result.trades:
            trade = result.trades[0]
            expected_entry_time = data[51].timestamp

            assert trade.entry_time == expected_entry_time, (
                f"Trade entered at {trade.entry_time}, expected {expected_entry_time}. "
                "Signals should execute on next bar, not current bar."
            )

    def test_execution_uses_open_price(self):
        """Verify trades execute at open price, not close price."""
        np.random.seed(42)

        # Create data with distinct open/close prices
        data = []
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

        for i in range(100):
            open_price = 50000.0 + i * 100
            close_price = open_price + 500  # Always +500 from open

            data.append(OHLCV(
                timestamp=start_time + timedelta(hours=4 * i),
                symbol="BTCUSDT",
                timeframe="4h",
                open=open_price,
                high=open_price + 600,
                low=open_price - 100,
                close=close_price,
                volume=1000,
                quote_volume=50000000,
            ))

        engine = BacktestEngine(random_seed=42)

        def buy_signal(df: pd.DataFrame, i: int) -> int:
            """Buy on bar 50."""
            return 1 if i == 50 else 0

        request = BacktestRequest(
            run_id="test-openprice",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 3, 1).date(),
            initial_capital=10000.0,
            commission=0.0,
            slippage=0.0,  # No slippage for this test
        )

        result = engine.run(request, data, buy_signal)

        if result.trades:
            trade = result.trades[0]
            expected_entry_price = data[51].open  # Execute at bar 51's open

            # With zero slippage, entry should be exactly at open
            assert abs(trade.entry_price - expected_entry_price) < 0.01, (
                f"Entry price {trade.entry_price} != expected {expected_entry_price}. "
                "Executions should use open price of execution bar."
            )


class TestDataIsolation:
    """Tests for proper data isolation between strategy and engine."""

    def test_strategy_cannot_modify_original_data(self):
        """Ensure strategy receives a copy and cannot corrupt original."""
        np.random.seed(42)
        data = create_test_ohlcv(100)
        original_closes = [d.close for d in data]

        engine = BacktestEngine(random_seed=42)

        def malicious_signal(df: pd.DataFrame, i: int) -> int:
            """Try to modify the DataFrame."""
            try:
                df.iloc[0, df.columns.get_loc("close")] = -99999
            except Exception:
                pass
            return 0

        request = BacktestRequest(
            run_id="test-isolation",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 3, 1).date(),
            initial_capital=10000.0,
        )

        engine.run(request, data, malicious_signal)

        # Original data should be unchanged
        for i, (original, current) in enumerate(zip(original_closes, [d.close for d in data])):
            assert original == current, (
                f"Original data corrupted at index {i}. "
                "Strategy should receive copies, not references."
            )


class TestFutureDataInjection:
    """Test that injected future data is properly rejected."""

    def test_reject_strategy_using_future_index(self):
        """Strategy attempting to access future indices should fail gracefully."""
        np.random.seed(42)
        data = create_test_ohlcv(100)
        engine = BacktestEngine(random_seed=42)

        errors_caught = []

        def future_access_signal(df: pd.DataFrame, i: int) -> int:
            """Attempt to access future data."""
            try:
                # This should fail as df only has i+1 rows
                future_value = df.iloc[i + 10]["close"]
                return 1 if future_value > df.iloc[i]["close"] else -1
            except (IndexError, KeyError):
                errors_caught.append(i)
                return 0

        request = BacktestRequest(
            run_id="test-future-access",
            strategy_code="",
            symbol="BTCUSDT",
            timeframe="4h",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 3, 1).date(),
            initial_capital=10000.0,
        )

        engine.run(request, data, future_access_signal)

        # Most accesses should fail (except last 10 bars where i+10 >= len)
        assert len(errors_caught) >= 80, (
            f"Only {len(errors_caught)} errors caught. "
            "Future data access should fail for most bars."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
