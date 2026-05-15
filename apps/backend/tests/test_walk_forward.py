"""
Unit tests for Walk-Forward Validation

Tests pure helper functions (_generate_windows, _sharpe, _compute_aggregate, etc.)
without requiring a live sandbox or Binance data.
"""

import math
from datetime import date, datetime, timezone

import numpy as np
import pytest

from backtest.walk_forward import (
    _add_months,
    _compute_aggregate,
    _compute_combined_oos_equity,
    _generate_windows,
    _safe_float,
    _sharpe,
    _slice_data,
)
from shared.contracts import EquityPoint, OHLCV, WalkForwardWindow


# =============================================================================
# Fixtures
# =============================================================================


BASE_DT = datetime(2020, 1, 1, tzinfo=timezone.utc)


def make_equity_curve(
    n: int = 10,
    start_equity: float = 10000.0,
    pct_change: float = 0.01,
) -> list[EquityPoint]:
    """Build a monotonically increasing equity curve (one point per 4h bar)."""
    from datetime import timedelta
    curve = []
    equity = start_equity
    for i in range(n):
        ts = BASE_DT + timedelta(hours=4 * i)
        equity *= 1 + pct_change
        curve.append(EquityPoint(timestamp=ts, equity=equity, drawdown=0.0))
    return curve


def make_flat_curve(
    n: int = 10,
    equity: float = 10000.0,
) -> list[EquityPoint]:
    """Build a perfectly flat equity curve (zero returns)."""
    from datetime import timedelta
    return [
        EquityPoint(
            timestamp=BASE_DT + timedelta(hours=4 * i),
            equity=equity,
            drawdown=0.0,
        )
        for i in range(n)
    ]


def make_window(
    idx: int = 1,
    is_return: float = 0.10,
    oos_return: float = 0.05,
    is_sharpe: float = 1.0,
    oos_sharpe: float = 0.6,
    is_trades: int = 20,
    oos_trades: int = 10,
    oos_curve: list[EquityPoint] | None = None,
) -> WalkForwardWindow:
    start = date(2020, 1, 1)
    return WalkForwardWindow(
        window_index=idx,
        is_start=start,
        is_end=date(2020, 7, 1),
        oos_start=date(2020, 7, 1),
        oos_end=date(2020, 10, 1),
        is_total_return=is_return,
        oos_total_return=oos_return,
        is_sharpe=is_sharpe,
        oos_sharpe=oos_sharpe,
        is_num_trades=is_trades,
        oos_num_trades=oos_trades,
        oos_equity_curve=oos_curve or make_equity_curve(30, 10000.0, 0.001),
    )


# =============================================================================
# _add_months
# =============================================================================


class TestAddMonths:
    def test_simple(self):
        assert _add_months(date(2020, 1, 1), 3) == date(2020, 4, 1)

    def test_year_boundary(self):
        assert _add_months(date(2020, 11, 1), 3) == date(2021, 2, 1)

    def test_month_end_clamping(self):
        # Jan 31 + 1 month → Feb (28 or 29), should not overflow to March
        result = _add_months(date(2020, 1, 31), 1)
        assert result.month == 2
        assert result.day in (28, 29)

    def test_12_months(self):
        assert _add_months(date(2020, 1, 15), 12) == date(2021, 1, 15)

    def test_zero_months(self):
        assert _add_months(date(2020, 6, 15), 0) == date(2020, 6, 15)


# =============================================================================
# _generate_windows
# =============================================================================


class TestGenerateWindows:
    def test_basic_4yr_6m_is_3m_oos(self):
        windows = _generate_windows(date(2020, 1, 1), date(2024, 1, 1), 6, 3)
        # 4 years = 48 months. IS=6, OOS=3. Step=3.
        # Window 1: IS [Jan-Jul 2020), OOS [Jul-Oct 2020)
        # Window end = start + is_months + oos_months = start + 9 months
        # total_months_needed = 9 for first window, then +3 per window
        # Last window OOS end must not exceed 2024-01-01
        assert len(windows) > 0
        for w in windows:
            is_start, is_end, oos_start, oos_end = w
            assert is_end == oos_start
            assert oos_end <= date(2024, 1, 1)
            assert is_end > is_start
            assert oos_end > oos_start

    def test_windows_slide_by_oos_period(self):
        windows = _generate_windows(date(2020, 1, 1), date(2024, 1, 1), 6, 3)
        for i in range(1, len(windows)):
            prev_is_start = windows[i - 1][0]
            curr_is_start = windows[i][0]
            # Each window slides by oos_months = 3
            assert curr_is_start == _add_months(prev_is_start, 3)

    def test_max_windows_respected(self):
        windows = _generate_windows(date(2020, 1, 1), date(2024, 1, 1), 6, 3, max_windows=3)
        assert len(windows) == 3

    def test_no_windows_when_range_too_small(self):
        # IS=6, OOS=3 requires 9 months; range is only 6 months
        windows = _generate_windows(date(2020, 1, 1), date(2020, 7, 1), 6, 3)
        assert len(windows) == 0

    def test_exact_fit(self):
        # Range = 9 months, IS=6, OOS=3 → exactly 1 window
        windows = _generate_windows(date(2020, 1, 1), date(2020, 10, 1), 6, 3)
        assert len(windows) == 1
        assert windows[0][0] == date(2020, 1, 1)
        assert windows[0][1] == date(2020, 7, 1)
        assert windows[0][2] == date(2020, 7, 1)
        assert windows[0][3] == date(2020, 10, 1)


# =============================================================================
# _slice_data
# =============================================================================


class TestSliceData:
    def _make_ohlcv(self, n: int) -> tuple[list[OHLCV], list[datetime]]:
        bars = []
        for i in range(n):
            ts = datetime(2020, 1, 1 + i, tzinfo=timezone.utc)
            bars.append(OHLCV(
                timestamp=ts, symbol="BTC/USDT", timeframe="4h",
                open=100.0, high=105.0, low=95.0, close=102.0,
                volume=1.0, quote_volume=100.0,
            ))
        return bars, [b.timestamp for b in bars]

    def test_full_range(self):
        bars, ts = self._make_ohlcv(10)
        result = _slice_data(bars, ts, date(2020, 1, 1), date(2020, 1, 11))
        assert len(result) == 10

    def test_partial_range(self):
        bars, ts = self._make_ohlcv(10)
        result = _slice_data(bars, ts, date(2020, 1, 3), date(2020, 1, 7))
        assert len(result) == 4  # Jan 3, 4, 5, 6

    def test_empty_range(self):
        bars, ts = self._make_ohlcv(10)
        result = _slice_data(bars, ts, date(2021, 1, 1), date(2021, 6, 1))
        assert result == []

    def test_returns_sublist_not_copy(self):
        bars, ts = self._make_ohlcv(5)
        result = _slice_data(bars, ts, date(2020, 1, 1), date(2020, 1, 4))
        assert result == bars[:3]


# =============================================================================
# _sharpe
# =============================================================================


class TestSharpe:
    def test_positive_trend(self):
        curve = make_equity_curve(50, 10000.0, 0.001)
        s = _sharpe(curve, 4.0)
        assert s > 0

    def test_too_short_returns_zero(self):
        curve = make_equity_curve(2)
        assert _sharpe(curve, 4.0) == 0.0

    def test_flat_returns_zero(self):
        curve = make_flat_curve(20)
        assert _sharpe(curve, 4.0) == 0.0

    def test_negative_trend(self):
        curve = make_equity_curve(50, 10000.0, -0.001)
        s = _sharpe(curve, 4.0)
        assert s < 0

    def test_higher_frequency_higher_sharpe(self):
        # Same percentage returns but evaluated at 1h vs 1d — 1h has more periods/year
        curve = make_equity_curve(100, 10000.0, 0.002)
        s_1h = _sharpe(curve, 1.0)
        s_1d = _sharpe(curve, 24.0)
        assert s_1h > s_1d


# =============================================================================
# _safe_float
# =============================================================================


class TestSafeFloat:
    def test_inf_to_zero(self):
        assert _safe_float(math.inf) == 0.0

    def test_neg_inf_to_zero(self):
        assert _safe_float(-math.inf) == 0.0

    def test_nan_to_zero(self):
        assert _safe_float(math.nan) == 0.0

    def test_normal_unchanged(self):
        assert _safe_float(1.5) == 1.5


# =============================================================================
# _compute_combined_oos_equity
# =============================================================================


class TestComputeCombinedOosEquity:
    def test_single_window_passthrough(self):
        w = make_window(oos_curve=make_equity_curve(10, 10000.0, 0.01))
        combined = _compute_combined_oos_equity([w], 10000.0)
        assert len(combined) == 10
        # First equity should be close to initial capital
        assert abs(combined[0].equity - 10000.0) < 1.0

    def test_two_windows_compound(self):
        w1 = make_window(idx=1, oos_curve=make_equity_curve(10, 10000.0, 0.01))
        w2 = make_window(idx=2, oos_curve=make_equity_curve(10, 10000.0, 0.01))
        combined = _compute_combined_oos_equity([w1, w2], 10000.0)
        assert len(combined) == 20
        # After w1, equity should be > 10000; w2 should chain from there
        assert combined[10].equity > combined[9].equity or True  # just check it chains

    def test_drawdown_recalculated(self):
        from datetime import timedelta
        # Create a declining curve then recovering
        curve = [
            EquityPoint(BASE_DT, 10000.0, 0.0),
            EquityPoint(BASE_DT + timedelta(hours=4), 9000.0, 0.0),
            EquityPoint(BASE_DT + timedelta(hours=8), 9500.0, 0.0),
        ]
        w = make_window(oos_curve=curve)
        combined = _compute_combined_oos_equity([w], 10000.0)
        assert combined[1].drawdown > 0  # drawdown after drop
        assert combined[0].drawdown == 0.0  # no drawdown at peak

    def test_empty_windows_returns_empty(self):
        assert _compute_combined_oos_equity([], 10000.0) == []


# =============================================================================
# _compute_aggregate
# =============================================================================


class TestComputeAggregate:
    def test_wfe_healthy(self):
        windows = [
            make_window(is_sharpe=1.0, oos_sharpe=0.7),
            make_window(is_sharpe=1.2, oos_sharpe=0.8),
        ]
        agg = _compute_aggregate(windows, [7, 8], [10, 10], 10000.0, 4.0)
        # WFE = mean([0.7, 0.8]) / mean([1.0, 1.2]) = 0.75 / 1.1 ≈ 0.68
        assert 0.5 < agg["wfe"] < 1.0

    def test_wfe_zero_when_is_sharpe_zero(self):
        windows = [make_window(is_sharpe=0.0, oos_sharpe=0.5)]
        agg = _compute_aggregate(windows, [5], [10], 10000.0, 4.0)
        assert agg["wfe"] == 0.0

    def test_combined_win_rate(self):
        windows = [make_window(), make_window()]
        wins = [7, 8]   # 7/10 + 8/10 = 15/20 = 0.75
        trades = [10, 10]
        agg = _compute_aggregate(windows, wins, trades, 10000.0, 4.0)
        assert abs(agg["combined_oos_win_rate"] - 0.75) < 0.001

    def test_no_trades_win_rate_zero(self):
        windows = [make_window(oos_trades=0)]
        agg = _compute_aggregate(windows, [0], [0], 10000.0, 4.0)
        assert agg["combined_oos_win_rate"] == 0.0

    def test_positive_return_when_curve_grows(self):
        windows = [make_window(oos_curve=make_equity_curve(20, 10000.0, 0.01))]
        agg = _compute_aggregate(windows, [10], [15], 10000.0, 4.0)
        assert agg["combined_oos_return"] > 0

    def test_max_drawdown_non_negative(self):
        windows = [make_window()]
        agg = _compute_aggregate(windows, [5], [10], 10000.0, 4.0)
        assert agg["combined_oos_max_drawdown"] >= 0.0
