"""
Core Backtest Engine

Single-asset, long-only backtesting engine with proper order execution.
Implements next-bar execution to prevent lookahead bias.
"""

import uuid
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


@dataclass
class Position:
    """Current position state."""
    is_open: bool = False
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    quantity: float = 0.0
    trade_id: Optional[str] = None


class BacktestEngine:
    """
    Core backtesting engine for single-asset, long-only strategies.

    Features:
    - Next-bar execution (prevents lookahead bias)
    - Configurable slippage and commission
    - Deterministic execution with seed control
    - Equity curve tracking
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

        Returns:
            BacktestResult with metrics, equity curve, and trades
        """
        self._reset()

        # Convert to DataFrame for easier manipulation
        df = self._prepare_dataframe(data)

        if len(df) < 2:
            return self._empty_result(request.run_id)

        # Initialize state
        cash = request.initial_capital
        position = Position()
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []
        pending_signal: Optional[int] = None

        # Track peak equity for drawdown
        peak_equity = request.initial_capital

        for i in range(len(df)):
            current_bar = df.iloc[i]
            timestamp = current_bar.name

            # Calculate current equity
            if position.is_open:
                current_equity = cash + position.quantity * current_bar["close"]
            else:
                current_equity = cash

            # Update peak and calculate drawdown
            peak_equity = max(peak_equity, current_equity)
            drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0

            # Record equity point
            equity_curve.append(EquityPoint(
                timestamp=timestamp,
                equity=current_equity,
                drawdown=drawdown,
            ))

            # Execute pending signal from previous bar (next-bar execution)
            if pending_signal is not None and i > 0:
                execution_price = current_bar["open"]  # Execute at open of new bar

                if pending_signal == 1 and not position.is_open:
                    # Buy signal - open long position
                    fill_result = self.fill_model.calculate_buy_fill(
                        price=execution_price,
                        available_cash=cash,
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
                        )
                        cash -= fill_result.total_cost

                elif pending_signal == -1 and position.is_open:
                    # Sell signal - close long position
                    fill_result = self.fill_model.calculate_sell_fill(
                        price=execution_price,
                        quantity=position.quantity,
                        commission_rate=request.commission,
                        slippage_rate=request.slippage,
                    )

                    # Record trade
                    pnl = fill_result.net_proceeds - (
                        position.entry_price * position.quantity
                    )
                    pnl_percent = pnl / (position.entry_price * position.quantity)

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
                    ))

                    cash += fill_result.net_proceeds
                    position = Position()

                pending_signal = None

            # Generate signal for next bar (only if not at last bar)
            if i < len(df) - 1:
                # Pass only data up to current bar (prevent lookahead)
                df_slice = df.iloc[: i + 1].copy()
                try:
                    signal = signal_func(df_slice, i)
                    if signal in (1, -1):
                        pending_signal = signal
                except Exception:
                    # Strategy error - no signal
                    pending_signal = None

        # Force close any open position at end
        if position.is_open:
            final_bar = df.iloc[-1]
            fill_result = self.fill_model.calculate_sell_fill(
                price=final_bar["close"],
                quantity=position.quantity,
                commission_rate=request.commission,
                slippage_rate=request.slippage,
            )

            pnl = fill_result.net_proceeds - (position.entry_price * position.quantity)
            pnl_percent = pnl / (position.entry_price * position.quantity)

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
            ))

            cash += fill_result.net_proceeds

        # Calculate final metrics
        final_equity = cash
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
        )

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
