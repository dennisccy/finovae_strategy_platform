"""
SL/TP Path Model Tests

Tests for the OHLC intra-bar path model and sub-bar resolution feature
added to improve backtest accuracy on longer timeframes (4H, 1D).

Key invariant: on a bearish bar (close < open) where both SL and TP are
inside the range, TP should win for a long position — because the canonical
bearish path is open → high → low → close, so price visits the TP level
(above) before the SL level (below).

The previous behaviour always selected SL regardless of bar direction,
causing systematic pessimism on long trades with bearish bars.
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from backtest.engine import BacktestEngine, _sl_tp_exit_price
from data.loader import OHLCVLoader
from shared.contracts import BacktestRequest, OHLCV


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _ts(offset_hours: int = 0) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=offset_hours)


def _bar(
    open_: float,
    high: float,
    low: float,
    close: float,
    timestamp_hours: int = 0,
    timeframe: str = "4h",
) -> OHLCV:
    return OHLCV(
        timestamp=_ts(timestamp_hours),
        symbol="BTCUSDT",
        timeframe=timeframe,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100.0,
        quote_volume=5_000_000.0,
    )


def _make_request(commission: float = 0.0, slippage: float = 0.0) -> BacktestRequest:
    return BacktestRequest(
        run_id="test",
        strategy_code="",
        symbol="BTCUSDT",
        timeframe="4h",
        start_date=_ts().date(),
        end_date=(_ts() + timedelta(days=30)).date(),
        initial_capital=10_000.0,
        commission=commission,
        slippage=slippage,
    )


# ---------------------------------------------------------------------------
# Unit tests for the _sl_tp_exit_price helper
# ---------------------------------------------------------------------------

class TestSlTpExitPriceHelper:
    """Direct unit tests for the module-level helper."""

    def test_neither_hit_returns_none(self):
        result = _sl_tp_exit_price(
            low=99.0, high=101.0, open_=100.0, close=100.5,
            sl_price=98.0, tp_price=105.0,
        )
        assert result is None

    def test_only_sl_hit(self):
        result = _sl_tp_exit_price(
            low=96.0, high=101.0, open_=100.0, close=97.0,
            sl_price=97.0, tp_price=110.0,
        )
        assert result == 97.0

    def test_only_tp_hit(self):
        result = _sl_tp_exit_price(
            low=99.0, high=106.0, open_=100.0, close=105.0,
            sl_price=94.0, tp_price=106.0,
        )
        assert result == 106.0

    def test_both_hit_bearish_bar_tp_wins(self):
        """
        Bearish bar (close < open): path = open → high → low → close.
        TP (above) is visited before SL (below) → TP should win.
        """
        result = _sl_tp_exit_price(
            low=95.0, high=108.0, open_=101.0, close=96.0,  # bearish
            sl_price=97.0, tp_price=106.0,
        )
        assert result == 106.0, (
            f"Expected TP price 106.0 but got {result}. "
            "On a bearish bar both SL+TP inside range, TP should win for a long position."
        )

    def test_both_hit_bullish_bar_sl_wins(self):
        """
        Bullish bar (close >= open): path = open → low → high → close.
        SL (below) is visited before TP (above) → SL should win.
        """
        result = _sl_tp_exit_price(
            low=95.0, high=108.0, open_=100.0, close=107.0,  # bullish
            sl_price=97.0, tp_price=106.0,
        )
        assert result == 97.0, (
            f"Expected SL price 97.0 but got {result}. "
            "On a bullish bar both SL+TP inside range, SL should win for a long position."
        )

    def test_doji_bar_treated_as_bullish(self):
        """Doji (close == open) is classified as bullish (SL first)."""
        result = _sl_tp_exit_price(
            low=95.0, high=108.0, open_=100.0, close=100.0,  # doji
            sl_price=97.0, tp_price=106.0,
        )
        assert result == 97.0

    def test_sl_none_only_tp_checked(self):
        result = _sl_tp_exit_price(
            low=95.0, high=108.0, open_=100.0, close=96.0,
            sl_price=None, tp_price=106.0,
        )
        assert result == 106.0

    def test_tp_none_only_sl_checked(self):
        result = _sl_tp_exit_price(
            low=95.0, high=108.0, open_=100.0, close=107.0,
            sl_price=97.0, tp_price=None,
        )
        assert result == 97.0

    def test_both_none_returns_none(self):
        result = _sl_tp_exit_price(
            low=95.0, high=108.0, open_=100.0, close=96.0,
            sl_price=None, tp_price=None,
        )
        assert result is None


# ---------------------------------------------------------------------------
# Integration: engine correctly applies the path model
# ---------------------------------------------------------------------------

class TestEngineOHLCPathModel:
    """
    End-to-end tests verifying the engine uses the OHLC path model correctly.
    """

    def _build_synthetic_data(
        self,
        entry_bar_open: float,
        trigger_bar: OHLCV,
        n_pre: int = 5,
    ) -> list[OHLCV]:
        """
        Build a minimal OHLCV series:
          bars 0..n_pre-1: flat pre-bars (no signal from them)
          bar n_pre:       entry bar  (signal fires here → executes at next bar open)
          bar n_pre+1:     trigger bar (provided by caller — is the SL/TP bar)
          bar n_pre+2:     closing bar (flat, used if position still open)
        """
        base = 100.0
        bars: list[OHLCV] = []
        for k in range(n_pre):
            bars.append(_bar(base, base + 0.5, base - 0.5, base, timestamp_hours=k * 4))
        # Entry bar: signal fires
        bars.append(_bar(base, base + 1, base - 1, base + 0.5, timestamp_hours=n_pre * 4))
        # Entry executes at this bar's open; SL/TP checked this bar
        # The trigger_bar represents bar n_pre+1
        bars.append(trigger_bar)
        # Safety close bar
        bars.append(_bar(trigger_bar.close, trigger_bar.close + 1, trigger_bar.close - 1,
                         trigger_bar.close, timestamp_hours=(n_pre + 2) * 4))
        return bars

    def _run(
        self,
        trigger_bar: OHLCV,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.06,
        n_pre: int = 5,
    ):
        engine = BacktestEngine(random_seed=42)
        data = self._build_synthetic_data(
            entry_bar_open=trigger_bar.open,
            trigger_bar=trigger_bar,
            n_pre=n_pre,
        )
        # Signal: buy on the entry bar (bar n_pre), hold otherwise
        entry_bar_idx = n_pre

        def signal(df: pd.DataFrame, i: int) -> int:
            return 1 if i == entry_bar_idx else 0

        result = engine.run(
            request=_make_request(),
            data=data,
            signal_func=signal,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
        )
        return result

    def test_bearish_bar_both_hit_uses_tp(self):
        """
        Regression test for the key bug: bearish bar, both SL+TP inside range.
        With old code: SL wins → loss.
        With new code: TP wins → profit.
        """
        # Entry price ≈ 100 (open of trigger bar, executed with 0 slippage)
        # SL = 97 (−3%), TP = 106 (+6%)
        # Bar: open=101, high=108, low=95, close=96  (bearish, both levels inside)
        trigger = _bar(open_=101.0, high=108.0, low=95.0, close=96.0,
                       timestamp_hours=24)
        result = self._run(trigger, stop_loss_pct=0.03, take_profit_pct=0.06)

        assert len(result.trades) >= 1
        trade = result.trades[0]

        # Entry should be near 101 (open of trigger bar)
        # TP should be at 101 * 1.06 ≈ 107.06, which is ≤ bar high (108)
        entry = trade.entry_price
        expected_tp = entry * 1.06
        expected_sl = entry * 0.97

        assert trade.exit_price == pytest.approx(expected_tp, rel=1e-6), (
            f"Expected exit at TP ({expected_tp:.4f}) but got {trade.exit_price:.4f}. "
            f"SL would have been {expected_sl:.4f}. "
            "Bearish bar with both SL+TP inside range should exit at TP."
        )
        assert trade.pnl > 0, "Trade on bearish bar (TP wins) should be profitable."

    def test_bullish_bar_both_hit_uses_sl(self):
        """
        Bullish bar, both SL+TP inside range → SL wins (same as old behaviour).
        """
        # Entry ≈ 101, SL=97 (−3%), TP=106 (+6%)
        # Bar: open=101, high=108, low=95, close=107  (bullish)
        trigger = _bar(open_=101.0, high=108.0, low=95.0, close=107.0,
                       timestamp_hours=24)
        result = self._run(trigger, stop_loss_pct=0.03, take_profit_pct=0.06)

        assert len(result.trades) >= 1
        trade = result.trades[0]

        entry = trade.entry_price
        expected_sl = entry * 0.97

        assert trade.exit_price == pytest.approx(expected_sl, rel=1e-6), (
            f"Expected exit at SL ({expected_sl:.4f}) but got {trade.exit_price:.4f}. "
            "Bullish bar with both SL+TP inside range should exit at SL."
        )
        assert trade.pnl < 0, "Trade on bullish bar (SL wins) should be a loss."

    def test_only_sl_hit_always_sl(self):
        """Only SL triggered — result must be SL regardless of bar direction."""
        trigger = _bar(open_=101.0, high=103.0, low=95.0, close=96.0,
                       timestamp_hours=24)
        result = self._run(trigger, stop_loss_pct=0.03, take_profit_pct=0.10)

        assert len(result.trades) >= 1
        entry = result.trades[0].entry_price
        assert result.trades[0].exit_price == pytest.approx(entry * 0.97, rel=1e-6)

    def test_only_tp_hit_always_tp(self):
        """Only TP triggered — result must be TP regardless of bar direction."""
        trigger = _bar(open_=101.0, high=115.0, low=99.0, close=112.0,
                       timestamp_hours=24)
        result = self._run(trigger, stop_loss_pct=0.10, take_profit_pct=0.06)

        assert len(result.trades) >= 1
        entry = result.trades[0].entry_price
        assert result.trades[0].exit_price == pytest.approx(entry * 1.06, rel=1e-6)

    def test_neither_hit_position_stays_open(self):
        """Neither SL nor TP triggered — position closes on final bar."""
        trigger = _bar(open_=101.0, high=103.0, low=99.0, close=102.0,
                       timestamp_hours=24)
        result = self._run(trigger, stop_loss_pct=0.05, take_profit_pct=0.10)

        # Position should not close on trigger bar; closes later (force-close on last bar)
        assert len(result.trades) >= 1
        trade = result.trades[0]
        # Exit should not equal SL or TP (which are well outside the bar range)
        entry = trade.entry_price
        sl = entry * 0.95
        tp = entry * 1.10
        assert trade.exit_price != pytest.approx(sl, rel=1e-4)
        assert trade.exit_price != pytest.approx(tp, rel=1e-4)


# ---------------------------------------------------------------------------
# Sub-bar resolution tests
# ---------------------------------------------------------------------------

class TestSubBarResolution:
    """
    Tests that verify the sub-bar resolution path (Option B).

    We construct synthetic 4H strategy bars and their constituent 15m sub-bars,
    where the sub-bars provide unambiguous ordering information.
    """

    def _make_4h_bar(self, ts_hours: int, **kwargs) -> OHLCV:
        defaults = dict(open_=100.0, high=110.0, low=90.0, close=105.0)
        defaults.update(kwargs)
        return _bar(**defaults, timestamp_hours=ts_hours, timeframe="4h")

    def _make_15m_sub_bars(
        self,
        parent_ts_hours: int,
        prices: list[tuple[float, float, float, float]],  # (open, high, low, close)
    ) -> list[OHLCV]:
        """Create 15m sub-bars with explicit OHLC. Each bar is 15 minutes."""
        bars = []
        for i, (o, h, l, c) in enumerate(prices):
            bars.append(OHLCV(
                timestamp=_ts(parent_ts_hours) + timedelta(minutes=15 * i),
                symbol="BTCUSDT",
                timeframe="15m",
                open=o, high=h, low=l, close=c,
                volume=10.0, quote_volume=1_000_000.0,
            ))
        return bars

    def test_sub_bar_tp_first_then_sl(self):
        """
        Sub-bar 1 hits TP, sub-bar 2 would hit SL.
        Engine should exit at TP (from sub-bar 1) and never see SL.
        """
        engine = BacktestEngine(random_seed=42)

        # 3 4H strategy bars: pre-bar, entry bar, trigger bar
        strategy_bars = [
            self._make_4h_bar(0, open_=100.0, high=101.0, low=99.0, close=100.5),
            self._make_4h_bar(4, open_=100.0, high=101.0, low=99.0, close=100.5),
            # Trigger bar (entry executes at open=101)
            self._make_4h_bar(8, open_=101.0, high=115.0, low=90.0, close=92.0),
            # Force-close bar
            self._make_4h_bar(12, open_=92.0, high=93.0, low=91.0, close=92.5),
        ]

        # entry_price ≈ 101.0, SL = 101 * 0.97 ≈ 98.0, TP = 101 * 1.06 ≈ 107.0
        # Sub-bars for trigger bar (starts at ts=8h):
        #   sub-bar 0: flat, no trigger
        #   sub-bar 1: high=108 → TP hit (107.06)
        #   sub-bar 2: low=90 → SL would be hit (but trade already closed)
        sub_bars_trigger = self._make_15m_sub_bars(8, [
            (101.0, 103.0, 100.5, 102.0),  # flat
            (102.0, 108.0, 101.5, 107.5),  # TP hit here
            (107.5, 108.0, 90.0, 91.0),    # SL would be hit, but too late
            (91.0, 92.0, 90.5, 92.0),      # trailing
        ])

        resolution_data = sub_bars_trigger  # only provide sub-bars for the trigger bar

        def signal(df: pd.DataFrame, i: int) -> int:
            return 1 if i == 1 else 0  # buy on bar index 1 → executes at bar 2 open

        result = engine.run(
            request=_make_request(),
            data=strategy_bars,
            signal_func=signal,
            stop_loss_pct=0.03,
            take_profit_pct=0.06,
            resolution_data=resolution_data,
        )

        assert len(result.trades) >= 1
        trade = result.trades[0]
        entry = trade.entry_price
        expected_tp = entry * 1.06

        assert trade.exit_price == pytest.approx(expected_tp, rel=1e-6), (
            f"Sub-bar TP hit first: expected exit at {expected_tp:.4f}, got {trade.exit_price:.4f}"
        )
        assert trade.pnl > 0

    def test_sub_bar_sl_first_then_tp(self):
        """
        Sub-bar 1 hits SL, sub-bar 2 would hit TP.
        Engine should exit at SL (from sub-bar 1).
        """
        engine = BacktestEngine(random_seed=42)

        strategy_bars = [
            self._make_4h_bar(0, open_=100.0, high=101.0, low=99.0, close=100.5),
            self._make_4h_bar(4, open_=100.0, high=101.0, low=99.0, close=100.5),
            self._make_4h_bar(8, open_=101.0, high=115.0, low=90.0, close=105.0),
            self._make_4h_bar(12, open_=105.0, high=106.0, low=104.0, close=105.5),
        ]

        # entry ≈ 101, SL ≈ 97.97, TP ≈ 107.06
        # sub-bar 0: low=97 → SL hit
        # sub-bar 1: high=110 → TP would be hit, but trade is already closed
        sub_bars_trigger = self._make_15m_sub_bars(8, [
            (101.0, 102.0, 97.0, 98.0),   # SL hit here
            (98.0, 110.0, 97.5, 108.0),   # TP would hit, too late
            (108.0, 109.0, 107.0, 108.5),
            (108.5, 109.0, 108.0, 108.5),
        ])

        def signal(df: pd.DataFrame, i: int) -> int:
            return 1 if i == 1 else 0

        result = engine.run(
            request=_make_request(),
            data=strategy_bars,
            signal_func=signal,
            stop_loss_pct=0.03,
            take_profit_pct=0.06,
            resolution_data=sub_bars_trigger,
        )

        assert len(result.trades) >= 1
        trade = result.trades[0]
        entry = trade.entry_price
        expected_sl = entry * 0.97

        assert trade.exit_price == pytest.approx(expected_sl, rel=1e-6), (
            f"Sub-bar SL hit first: expected exit at {expected_sl:.4f}, got {trade.exit_price:.4f}"
        )
        assert trade.pnl < 0

    def test_no_resolution_data_falls_back_to_path_model(self):
        """Without resolution_data, the engine uses the OHLC path model."""
        engine = BacktestEngine(random_seed=42)

        strategy_bars = [
            _bar(100.0, 101.0, 99.0, 100.5, timestamp_hours=0),
            _bar(100.0, 101.0, 99.0, 100.5, timestamp_hours=4),
            # Bearish bar, both SL+TP inside → TP should win (path model)
            _bar(101.0, 108.0, 95.0, 96.0, timestamp_hours=8),
            _bar(96.0, 97.0, 95.0, 96.5, timestamp_hours=12),
        ]

        def signal(df: pd.DataFrame, i: int) -> int:
            return 1 if i == 1 else 0

        result = engine.run(
            request=_make_request(),
            data=strategy_bars,
            signal_func=signal,
            stop_loss_pct=0.03,
            take_profit_pct=0.06,
            resolution_data=None,  # no sub-bar data
        )

        assert len(result.trades) >= 1
        trade = result.trades[0]
        entry = trade.entry_price
        expected_tp = entry * 1.06

        # Bearish bar → TP wins via OHLC path model
        assert trade.exit_price == pytest.approx(expected_tp, rel=1e-6)


# ---------------------------------------------------------------------------
# Loader.get_resolution_timeframe tests
# ---------------------------------------------------------------------------

class TestLoaderResolutionTf:
    """Verify the resolution TF derivation mapping."""

    def test_4h_maps_to_15m(self):
        assert OHLCVLoader.get_resolution_timeframe("4h") == "15m"

    def test_1h_maps_to_5m(self):
        assert OHLCVLoader.get_resolution_timeframe("1h") == "5m"

    def test_1d_maps_to_1h(self):
        assert OHLCVLoader.get_resolution_timeframe("1d") == "1h"

    def test_15m_maps_to_1m(self):
        assert OHLCVLoader.get_resolution_timeframe("15m") == "1m"

    def test_1m_returns_none(self):
        assert OHLCVLoader.get_resolution_timeframe("1m") is None

    def test_unknown_tf_returns_none(self):
        assert OHLCVLoader.get_resolution_timeframe("2h") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
