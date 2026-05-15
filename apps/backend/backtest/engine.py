"""
Core Backtest Engine

Single-asset, long-only backtesting engine with proper order execution.
Implements next-bar execution to prevent lookahead bias.
"""

import uuid
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import pandas as pd

from backtest.fills import FillModel
from backtest.metrics import MetricsCalculator
from shared.contracts import (
    BacktestRequest,
    BacktestResult,
    EquityPoint,
    OHLCV,
    Trade,
)


def _sl_tp_exit_price(
    low: float,
    high: float,
    open_: float,
    close: float,
    sl_price: Optional[float],
    tp_price: Optional[float],
) -> Optional[float]:
    """
    Determine intra-bar SL/TP exit price using the OHLC path model.

    Assumes the canonical intra-bar path for a long position:
      - Bullish bar (close >= open):  open → low → high → close
        → SL (below) is visited before TP (above) → SL wins when both hit
      - Bearish bar (close <  open):  open → high → low → close
        → TP (above) is visited before SL (below) → TP wins when both hit

    Returns:
        The exit price (sl_price or tp_price), or None if neither triggered.
    """
    sl_hit = sl_price is not None and low <= sl_price
    tp_hit = tp_price is not None and high >= tp_price

    if not sl_hit and not tp_hit:
        return None
    if sl_hit and not tp_hit:
        return sl_price
    if tp_hit and not sl_hit:
        return tp_price

    # Both triggered — resolve order via OHLC path model
    # Bullish: SL first; Bearish: TP first
    return sl_price if close >= open_ else tp_price


def _sl_tp_exit_price_short(
    low: float,
    high: float,
    open_: float,
    close: float,
    sl_price: Optional[float],
    tp_price: Optional[float],
) -> Optional[float]:
    """
    Determine intra-bar SL/TP exit price for a short position.

    For shorts:
      sl_price = entry * (1 + sl_pct)  — triggered when price rises
      tp_price = entry * (1 - tp_pct)  — triggered when price falls

    Path model (inverted from long):
      Bullish bar (close >= open):  path visits low before high → TP wins when both hit
      Bearish bar (close <  open):  path visits high before low → SL wins when both hit

    Returns:
        The exit price (sl_price or tp_price), or None if neither triggered.
    """
    sl_hit = sl_price is not None and high >= sl_price
    tp_hit = tp_price is not None and low <= tp_price

    if not sl_hit and not tp_hit:
        return None
    if sl_hit and not tp_hit:
        return sl_price
    if tp_hit and not sl_hit:
        return tp_price

    # Both triggered — resolve order via inverted OHLC path model
    # Bullish: TP first (low visited first); Bearish: SL first (high visited first)
    return tp_price if close >= open_ else sl_price


@dataclass
class Position:
    """Current position state."""
    is_open: bool = False
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    quantity: float = 0.0
    trade_id: Optional[str] = None
    direction: str = "long"   # "long" | "short" — v0.7
    leverage: float = 1.0     # leverage multiplier — v0.7
    margin: float = 0.0       # margin posted for short positions (returned on close)


class BacktestEngine:
    """
    Core backtesting engine for single-asset strategies (long + short).

    Features:
    - Next-bar execution (prevents lookahead bias)
    - Configurable slippage and commission
    - Deterministic execution with seed control
    - Equity curve tracking
    - Short selling and leverage support (v0.7)

    Signal convention (v0.7):
      1  = go long  (open long; ignored if already long)
      -1 = go short if allow_short + flat; else close long if long
      0  = hold
      2  = flatten (close any open position)
    """

    def __init__(
        self,
        fill_model: Optional[FillModel] = None,
        random_seed: int = 42,
    ):
        """
        Initialize backtest engine.

        Args:
            fill_model: Model for slippage and commission (uses default if None)
            random_seed: Seed for deterministic execution
        """
        self.fill_model = fill_model or FillModel()
        self.random_seed = random_seed
        self._rng = np.random.default_rng(random_seed)

    def _reset(self) -> None:
        """Reset engine state for new backtest."""
        self._rng = np.random.default_rng(self.random_seed)

    def run(
        self,
        request: BacktestRequest,
        data: list[OHLCV],
        signal_func: Callable[[pd.DataFrame, int], int],
        cancel_check: Optional[Callable[[], None]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        setup_func: Optional[Callable[[pd.DataFrame], None]] = None,
        resolution_data: Optional[list[OHLCV]] = None,
        max_hold_bars: int = 100,
    ) -> BacktestResult:
        """
        Run backtest with provided strategy signal function.

        The signal function receives:
        - df: DataFrame with OHLCV + indicators (up to current bar)
        - i: Current bar index

        Returns signal:
        - 1: Buy signal
        - -1: Sell signal
        - 0: No signal (hold)

        IMPORTANT: Signal on bar[i] executes on bar[i+1] (next-bar execution).

        Args:
            request: Backtest configuration
            data: OHLCV data list
            signal_func: Strategy signal function
            stop_loss_pct: Optional stop-loss percentage (e.g. 0.03 = 3%).
                When set, an open position is closed if the bar's low
                breaches entry_price * (1 - stop_loss_pct).
            take_profit_pct: Optional take-profit percentage (e.g. 0.06 = 6%).
                When set, an open position is closed if the bar's high
                reaches entry_price * (1 + take_profit_pct).
            resolution_data: Optional list of sub-bar OHLCV data at a finer
                timeframe (e.g. 15m bars for a 4H strategy). When provided,
                each strategy bar's constituent sub-bars are walked in order to
                determine whether SL or TP is hit first, eliminating bar-path
                ambiguity. Falls back to the OHLC path model when None.
            max_hold_bars: Maximum number of bars a position may be held before
                a forced close is injected. Prevents stuck-position strategies
                from wiping the account. Default 100 bars.

        Returns:
            BacktestResult with metrics, equity curve, and trades
        """
        self._reset()

        # Convert to DataFrame for easier manipulation
        df = self._prepare_dataframe(data)

        if len(df) < 2:
            return self._empty_result(request.run_id)

        # Pre-invoke setup once on the full DataFrame (O(N) instead of O(N²))
        if setup_func is not None:
            try:
                setup_func(df)
            except Exception:
                pass

        # Build sub-bar resolution map for accurate SL/TP path resolution
        resolution_map: dict = (
            self._build_resolution_map(df.index.tolist(), resolution_data)
            if resolution_data
            else {}
        )

        # Initialize state
        cash = request.initial_capital
        position = Position()
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []
        pending_signal: Optional[int] = None
        position_entry_bar: int = -1  # bar index when position was opened
        margin_call_occurred = False

        # Daily loss circuit breaker state
        _daily_loss: dict = {}           # date → cumulative realized loss (positive = loss $)
        _cb_date = None                  # date on which CB tripped; None = inactive

        # Effective leverage: request default (may be overridden per-position via strategy attr)
        effective_leverage = max(1.0, request.leverage)

        # Track peak equity for drawdown
        peak_equity = request.initial_capital

        for i in range(len(df)):
            # Check for cancellation every 100 bars
            if cancel_check and i % 100 == 0:
                cancel_check()

            # Report progress every 100 bars
            if progress_callback and i % 100 == 0:
                progress_callback(i, len(df))

            current_bar = df.iloc[i]
            timestamp = current_bar.name

            # Calculate current equity
            if position.is_open:
                if position.direction == "long":
                    # For leveraged longs: margin (collateral) + unrealized leveraged P&L
                    unrealized_pnl = (current_bar["close"] - position.entry_price) * position.quantity
                    current_equity = cash + position.margin + unrealized_pnl
                else:
                    # Short: unrealized_pnl = (entry - current) * qty (positive when price fell)
                    # Add back the held margin so equity reflects true account value
                    unrealized_pnl = (position.entry_price - current_bar["close"]) * position.quantity
                    current_equity = cash + position.margin + unrealized_pnl
            else:
                current_equity = cash

            # Update peak and calculate drawdown
            peak_equity = max(peak_equity, current_equity)
            drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0

            # Record equity point
            equity_curve.append(EquityPoint(
                timestamp=timestamp,
                equity=max(0.0, current_equity),
                drawdown=min(1.0, drawdown),
            ))

            # Margin call detection: equity wiped → force-liquidate and end trading
            if position.is_open and current_equity <= 0:
                trades.append(Trade(
                    trade_id=position.trade_id,
                    entry_time=position.entry_time,
                    exit_time=timestamp,
                    entry_price=position.entry_price,
                    exit_price=current_bar["close"],
                    quantity=position.quantity,
                    pnl=-position.margin,
                    pnl_percent=-1.0,
                    commission_paid=0.0,
                    direction=position.direction,
                    leverage=position.leverage,
                    margin=position.margin,
                ))
                margin_call_occurred = True
                cash = 0.0
                position = Position()
                position_entry_bar = -1
                pending_signal = None

            # Execute pending signal from previous bar (next-bar execution)
            if pending_signal is not None and i > 0:
                execution_price = current_bar["open"]  # Execute at open of new bar

                # Daily loss circuit breaker: block new entries only
                _cb_active = (_cb_date is not None and timestamp.date() == _cb_date)

                # --- Signal 1: Go long ---
                if pending_signal == 1 and not position.is_open and not _cb_active:
                    trade_cash = cash * request.max_order_size_pct if request.max_order_size_pct else cash
                    fill_result = self.fill_model.calculate_buy_fill(
                        price=execution_price,
                        available_cash=trade_cash,
                        commission_rate=request.commission,
                        slippage_rate=request.slippage,
                        leverage=effective_leverage,
                    )
                    if fill_result.quantity > 0:
                        position = Position(
                            is_open=True,
                            entry_price=fill_result.fill_price,
                            entry_time=timestamp,
                            quantity=fill_result.quantity,
                            trade_id=str(uuid.uuid4())[:8],
                            direction="long",
                            leverage=effective_leverage,
                            margin=fill_result.margin,
                        )
                        cash -= fill_result.total_cost
                        position_entry_bar = i

                # --- Signal -1: Close long or open short ---
                elif pending_signal == -1:
                    if position.is_open and position.direction == "long":
                        # Close the long position
                        fill_result = self.fill_model.calculate_sell_fill(
                            price=execution_price,
                            quantity=position.quantity,
                            commission_rate=request.commission,
                            slippage_rate=request.slippage,
                        )
                        pnl_raw = (fill_result.fill_price - position.entry_price) * position.quantity
                        net_to_account = max(0.0, position.margin + pnl_raw - fill_result.commission)
                        pnl = net_to_account - position.margin
                        pnl_percent = pnl / position.margin if position.margin > 0 else 0.0
                        trades.append(Trade(
                            trade_id=position.trade_id,
                            entry_time=position.entry_time,
                            exit_time=timestamp,
                            entry_price=position.entry_price,
                            exit_price=fill_result.fill_price,
                            quantity=position.quantity,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            commission_paid=fill_result.commission,
                            direction="long",
                            leverage=position.leverage,
                            margin=position.margin,
                        ))
                        cash += net_to_account
                        if pnl < 0 and request.max_daily_loss_pct is not None:
                            d = timestamp.date()
                            _daily_loss[d] = _daily_loss.get(d, 0.0) + abs(pnl)
                            if _daily_loss[d] >= request.initial_capital * request.max_daily_loss_pct:
                                _cb_date = d
                        position = Position()
                        position_entry_bar = -1

                    elif not position.is_open and request.allow_short and not _cb_active:
                        # Open short position
                        position_size_pct = getattr(request, "_position_size_pct", 1.0)
                        fill_result = self.fill_model.calculate_short_open_fill(
                            price=execution_price,
                            available_cash=cash,
                            leverage=effective_leverage,
                            position_size_pct=position_size_pct,
                            commission_rate=request.commission,
                            slippage_rate=request.slippage,
                        )
                        if fill_result.quantity > 0:
                            position = Position(
                                is_open=True,
                                entry_price=fill_result.fill_price,
                                entry_time=timestamp,
                                quantity=fill_result.quantity,
                                trade_id=str(uuid.uuid4())[:8],
                                direction="short",
                                leverage=effective_leverage,
                                margin=fill_result.total_cost - fill_result.commission,
                            )
                            cash -= fill_result.total_cost
                            position_entry_bar = i

                # --- Signal 2: Flatten (close any open position) ---
                elif pending_signal == 2 and position.is_open:
                    if position.direction == "long":
                        fill_result = self.fill_model.calculate_sell_fill(
                            price=execution_price,
                            quantity=position.quantity,
                            commission_rate=request.commission,
                            slippage_rate=request.slippage,
                        )
                        pnl_raw = (fill_result.fill_price - position.entry_price) * position.quantity
                        net_to_account = max(0.0, position.margin + pnl_raw - fill_result.commission)
                        pnl = net_to_account - position.margin
                        pnl_percent = pnl / position.margin if position.margin > 0 else 0.0
                        trades.append(Trade(
                            trade_id=position.trade_id,
                            entry_time=position.entry_time,
                            exit_time=timestamp,
                            entry_price=position.entry_price,
                            exit_price=fill_result.fill_price,
                            quantity=position.quantity,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            commission_paid=fill_result.commission,
                            direction="long",
                            leverage=position.leverage,
                            margin=position.margin,
                        ))
                        cash += net_to_account
                        if pnl < 0 and request.max_daily_loss_pct is not None:
                            d = timestamp.date()
                            _daily_loss[d] = _daily_loss.get(d, 0.0) + abs(pnl)
                            if _daily_loss[d] >= request.initial_capital * request.max_daily_loss_pct:
                                _cb_date = d
                    else:
                        # Close short
                        fill_result = self.fill_model.calculate_short_close_fill(
                            entry_price=position.entry_price,
                            close_price=execution_price,
                            quantity=position.quantity,
                            commission_rate=request.commission,
                            slippage_rate=request.slippage,
                        )
                        pnl = fill_result.net_proceeds
                        pnl_percent = pnl / (position.entry_price * position.quantity) if position.entry_price * position.quantity != 0 else 0.0
                        trades.append(Trade(
                            trade_id=position.trade_id,
                            entry_time=position.entry_time,
                            exit_time=timestamp,
                            entry_price=position.entry_price,
                            exit_price=fill_result.fill_price,
                            quantity=position.quantity,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            commission_paid=fill_result.commission,
                            direction="short",
                            leverage=position.leverage,
                        ))
                        cash += fill_result.net_proceeds + position.margin  # return held margin
                        if pnl < 0 and request.max_daily_loss_pct is not None:
                            d = timestamp.date()
                            _daily_loss[d] = _daily_loss.get(d, 0.0) + abs(pnl)
                            if _daily_loss[d] >= request.initial_capital * request.max_daily_loss_pct:
                                _cb_date = d
                    position = Position()
                    position_entry_bar = -1

                pending_signal = None

            # Intra-bar stop-loss / take-profit check
            if position.is_open and (stop_loss_pct is not None or take_profit_pct is not None):
                if position.direction == "long":
                    sl_price = position.entry_price * (1 - stop_loss_pct) if stop_loss_pct is not None else None
                    tp_price = position.entry_price * (1 + take_profit_pct) if take_profit_pct is not None else None
                    _sl_tp_fn = _sl_tp_exit_price
                else:
                    # Short: SL triggers when price rises, TP when price falls
                    sl_price = position.entry_price * (1 + stop_loss_pct) if stop_loss_pct is not None else None
                    tp_price = position.entry_price * (1 - take_profit_pct) if take_profit_pct is not None else None
                    _sl_tp_fn = _sl_tp_exit_price_short

                exit_price_sl_tp: Optional[float] = None
                sub_bars = resolution_map.get(timestamp)
                if sub_bars:
                    for sub_bar in sub_bars:
                        exit_price_sl_tp = _sl_tp_fn(
                            sub_bar.low, sub_bar.high, sub_bar.open, sub_bar.close,
                            sl_price, tp_price,
                        )
                        if exit_price_sl_tp is not None:
                            break
                else:
                    exit_price_sl_tp = _sl_tp_fn(
                        current_bar["low"], current_bar["high"],
                        current_bar["open"], current_bar["close"],
                        sl_price, tp_price,
                    )

                if exit_price_sl_tp is not None:
                    if position.direction == "long":
                        fill_result = self.fill_model.calculate_sell_fill(
                            price=exit_price_sl_tp,
                            quantity=position.quantity,
                            commission_rate=request.commission,
                            slippage_rate=request.slippage,
                        )
                        pnl_raw = (fill_result.fill_price - position.entry_price) * position.quantity
                        net_to_account = max(0.0, position.margin + pnl_raw - fill_result.commission)
                        pnl = net_to_account - position.margin
                        pnl_percent = pnl / position.margin if position.margin > 0 else 0.0
                        trades.append(Trade(
                            trade_id=position.trade_id,
                            entry_time=position.entry_time,
                            exit_time=timestamp,
                            entry_price=position.entry_price,
                            exit_price=fill_result.fill_price,
                            quantity=position.quantity,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            commission_paid=fill_result.commission,
                            direction="long",
                            leverage=position.leverage,
                            margin=position.margin,
                        ))
                        cash += net_to_account
                        if pnl < 0 and request.max_daily_loss_pct is not None:
                            d = timestamp.date()
                            _daily_loss[d] = _daily_loss.get(d, 0.0) + abs(pnl)
                            if _daily_loss[d] >= request.initial_capital * request.max_daily_loss_pct:
                                _cb_date = d
                    else:
                        fill_result = self.fill_model.calculate_short_close_fill(
                            entry_price=position.entry_price,
                            close_price=exit_price_sl_tp,
                            quantity=position.quantity,
                            commission_rate=request.commission,
                            slippage_rate=request.slippage,
                        )
                        pnl = fill_result.net_proceeds
                        pnl_percent = pnl / (position.entry_price * position.quantity) if position.entry_price * position.quantity != 0 else 0.0
                        trades.append(Trade(
                            trade_id=position.trade_id,
                            entry_time=position.entry_time,
                            exit_time=timestamp,
                            entry_price=position.entry_price,
                            exit_price=fill_result.fill_price,
                            quantity=position.quantity,
                            pnl=pnl,
                            pnl_percent=pnl_percent,
                            commission_paid=fill_result.commission,
                            direction="short",
                            leverage=position.leverage,
                        ))
                        cash += fill_result.net_proceeds + position.margin  # return held margin
                        if pnl < 0 and request.max_daily_loss_pct is not None:
                            d = timestamp.date()
                            _daily_loss[d] = _daily_loss.get(d, 0.0) + abs(pnl)
                            if _daily_loss[d] >= request.initial_capital * request.max_daily_loss_pct:
                                _cb_date = d
                    position = Position()
                    position_entry_bar = -1
                    pending_signal = None  # Clear any pending signal

            # Generate signal for next bar (only if not at last bar)
            if i < len(df) - 1:
                # Pass only data up to current bar (prevent lookahead)
                df_slice = df.iloc[: i + 1]
                try:
                    signal = signal_func(df_slice, i)
                    if signal in (1, -1, 2):
                        pending_signal = signal
                except Exception:
                    # Strategy error - no signal
                    pending_signal = None

                # Safety net: force-close if position held for too long.
                # Prevents stuck strategies (no exit signal ever fires) from
                # holding a leveraged position until the account is wiped.
                if (
                    position.is_open
                    and position_entry_bar >= 0
                    and (i - position_entry_bar) >= max_hold_bars
                ):
                    pending_signal = 2

        # Force close any open position at end
        if position.is_open:
            final_bar = df.iloc[-1]
            if position.direction == "long":
                fill_result = self.fill_model.calculate_sell_fill(
                    price=final_bar["close"],
                    quantity=position.quantity,
                    commission_rate=request.commission,
                    slippage_rate=request.slippage,
                )
                pnl_raw = (fill_result.fill_price - position.entry_price) * position.quantity
                net_to_account = max(0.0, position.margin + pnl_raw - fill_result.commission)
                pnl = net_to_account - position.margin
                pnl_percent = pnl / position.margin if position.margin > 0 else 0.0
                trades.append(Trade(
                    trade_id=position.trade_id,
                    entry_time=position.entry_time,
                    exit_time=final_bar.name,
                    entry_price=position.entry_price,
                    exit_price=fill_result.fill_price,
                    quantity=position.quantity,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                    commission_paid=fill_result.commission,
                    direction="long",
                    leverage=position.leverage,
                    margin=position.margin,
                ))
            else:
                fill_result = self.fill_model.calculate_short_close_fill(
                    entry_price=position.entry_price,
                    close_price=final_bar["close"],
                    quantity=position.quantity,
                    commission_rate=request.commission,
                    slippage_rate=request.slippage,
                )
                pnl = fill_result.net_proceeds
                pnl_percent = pnl / (position.entry_price * position.quantity) if position.entry_price * position.quantity != 0 else 0.0
                trades.append(Trade(
                    trade_id=position.trade_id,
                    entry_time=position.entry_time,
                    exit_time=final_bar.name,
                    entry_price=position.entry_price,
                    exit_price=fill_result.fill_price,
                    quantity=position.quantity,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                    commission_paid=fill_result.commission,
                    direction="short",
                    leverage=position.leverage,
                    margin=position.margin,
                ))
            if position.direction == "long":
                cash += net_to_account
            else:
                cash += fill_result.net_proceeds + position.margin  # return held margin

        # Compute unleveraged return: replay same trade sequence at 1x with proper compounding
        unleveraged_return: Optional[float] = None
        if effective_leverage > 1 and request.initial_capital > 0:
            unlev_cash = float(request.initial_capital)
            for t in trades:
                if t.direction != "long" or t.entry_price <= 0 or unlev_cash <= 0:
                    continue
                unlev_qty = unlev_cash / t.entry_price
                gross_pnl = (t.exit_price - t.entry_price) * unlev_qty
                # Scale commission proportionally from leveraged quantity to 1x quantity
                commission = t.commission_paid * (unlev_qty / t.quantity) if t.quantity > 0 else 0.0
                unlev_cash = max(0.0, unlev_cash + gross_pnl - commission)
            unleveraged_return = (unlev_cash - request.initial_capital) / request.initial_capital

        # Calculate final metrics
        metrics = MetricsCalculator.calculate(
            equity_curve=equity_curve,
            trades=trades,
            initial_capital=request.initial_capital,
        )

        return BacktestResult(
            run_id=request.run_id,
            total_return=metrics.total_return,
            max_drawdown=metrics.max_drawdown,
            num_trades=metrics.num_trades,
            win_rate=metrics.win_rate,
            sharpe_ratio=metrics.sharpe_ratio,
            profit_factor=metrics.profit_factor,
            equity_curve=equity_curve,
            trades=trades,
            margin_called=margin_call_occurred,
            unleveraged_return=unleveraged_return,
        )

    def _build_resolution_map(
        self,
        strategy_timestamps: list,
        resolution_data: list[OHLCV],
    ) -> dict:
        """
        Build a mapping from each strategy bar timestamp to its constituent
        sub-bars from the resolution dataset.

        Uses binary search for O(M log M) construction where M = len(resolution_data).

        Args:
            strategy_timestamps: Ordered list of pd.Timestamp from df.index
            resolution_data: Sub-bar OHLCV list at a finer timeframe

        Returns:
            dict mapping strategy bar pd.Timestamp → list[OHLCV] sub-bars
        """
        if not resolution_data:
            return {}

        # Sort sub-bars and build a parallel list of pd.Timestamps for bisect
        sub_bars_sorted = sorted(resolution_data, key=lambda x: x.timestamp)
        sub_ts = [pd.Timestamp(sb.timestamp) for sb in sub_bars_sorted]

        strat_ts_sorted = sorted(strategy_timestamps)  # already pd.Timestamp
        result: dict = {}

        for i, ts in enumerate(strat_ts_sorted):
            start_idx = bisect_left(sub_ts, ts)
            if i + 1 < len(strat_ts_sorted):
                end_idx = bisect_left(sub_ts, strat_ts_sorted[i + 1])
            else:
                end_idx = len(sub_bars_sorted)
            result[ts] = sub_bars_sorted[start_idx:end_idx]

        return result

    def _prepare_dataframe(self, data: list[OHLCV]) -> pd.DataFrame:
        """Convert OHLCV list to indexed DataFrame."""
        records = [
            {
                "timestamp": ohlcv.timestamp,
                "open": ohlcv.open,
                "high": ohlcv.high,
                "low": ohlcv.low,
                "close": ohlcv.close,
                "volume": ohlcv.volume,
            }
            for ohlcv in data
        ]

        df = pd.DataFrame(records)
        df = df.set_index("timestamp")
        df = df.sort_index()

        return df

    def _empty_result(self, run_id: str) -> BacktestResult:
        """Return empty result for invalid/insufficient data."""
        return BacktestResult(
            run_id=run_id,
            total_return=0.0,
            max_drawdown=0.0,
            num_trades=0,
            win_rate=0.0,
            sharpe_ratio=0.0,
            profit_factor=0.0,
            equity_curve=[],
            trades=[],
        )
