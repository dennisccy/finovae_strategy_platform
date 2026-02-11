"""
Performance Metrics Calculator

Calculates standard backtest performance metrics from equity curve and trades.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from shared.contracts import EquityPoint, Trade


@dataclass
class PerformanceMetrics:
    """Calculated performance metrics."""
    total_return: float
    max_drawdown: float
    num_trades: int
    win_rate: float
    sharpe_ratio: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration_hours: float


class MetricsCalculator:
    """
    Calculates performance metrics from backtest results.

    All calculations follow standard industry definitions.
    """

    # Risk-free rate for Sharpe ratio (annualized)
    RISK_FREE_RATE = 0.05  # 5% annual

    # Trading hours per year (crypto is 24/7)
    HOURS_PER_YEAR = 24 * 365

    @classmethod
    def calculate(
        cls,
        equity_curve: list[EquityPoint],
        trades: list[Trade],
        initial_capital: float,
        timeframe_hours: float = 4.0,
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics.

        Args:
            equity_curve: List of equity points
            trades: List of completed trades
            initial_capital: Starting capital
            timeframe_hours: Hours per candle (for Sharpe annualization)

        Returns:
            PerformanceMetrics dataclass
        """
        # Total return
        if equity_curve:
            final_equity = equity_curve[-1].equity
            total_return = (final_equity - initial_capital) / initial_capital
        else:
            total_return = 0.0

        # Max drawdown (already tracked in equity curve)
        max_drawdown = 0.0
        if equity_curve:
            max_drawdown = max(ep.drawdown for ep in equity_curve)

        # Trade statistics
        num_trades = len(trades)

        if num_trades == 0:
            return PerformanceMetrics(
                total_return=total_return,
                max_drawdown=max_drawdown,
                num_trades=0,
                win_rate=0.0,
                sharpe_ratio=0.0,
                profit_factor=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                avg_trade_duration_hours=0.0,
            )

        # Win/loss breakdown
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]

        num_winners = len(winning_trades)
        num_losers = len(losing_trades)

        win_rate = num_winners / num_trades if num_trades > 0 else 0.0

        # Average win/loss
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0.0

        # Largest win/loss
        largest_win = max((t.pnl for t in winning_trades), default=0.0)
        largest_loss = min((t.pnl for t in losing_trades), default=0.0)

        # Profit factor (gross profits / gross losses)
        gross_profits = sum(t.pnl for t in winning_trades)
        gross_losses = abs(sum(t.pnl for t in losing_trades))

        if gross_losses > 0:
            profit_factor = gross_profits / gross_losses
        else:
            profit_factor = float("inf") if gross_profits > 0 else 0.0

        # Average trade duration
        durations_hours = [
            (t.exit_time - t.entry_time).total_seconds() / 3600
            for t in trades
        ]
        avg_trade_duration_hours = np.mean(durations_hours) if durations_hours else 0.0

        # Sharpe ratio (annualized)
        sharpe_ratio = cls._calculate_sharpe(
            equity_curve=equity_curve,
            timeframe_hours=timeframe_hours,
        )

        return PerformanceMetrics(
            total_return=total_return,
            max_drawdown=max_drawdown,
            num_trades=num_trades,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_trade_duration_hours=avg_trade_duration_hours,
        )

    @classmethod
    def _calculate_sharpe(
        cls,
        equity_curve: list[EquityPoint],
        timeframe_hours: float,
    ) -> float:
        """
        Calculate annualized Sharpe ratio.

        Uses period returns from equity curve.

        Args:
            equity_curve: List of equity points
            timeframe_hours: Hours per period

        Returns:
            Annualized Sharpe ratio
        """
        if len(equity_curve) < 2:
            return 0.0

        # Calculate period returns
        equities = [ep.equity for ep in equity_curve]
        returns = np.diff(equities) / equities[:-1]

        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0

        # Annualization factor
        periods_per_year = cls.HOURS_PER_YEAR / timeframe_hours

        # Risk-free rate per period
        rf_per_period = cls.RISK_FREE_RATE / periods_per_year

        # Sharpe ratio
        excess_returns = returns - rf_per_period
        sharpe = np.mean(excess_returns) / np.std(excess_returns)

        # Annualize
        annualized_sharpe = sharpe * np.sqrt(periods_per_year)

        return float(annualized_sharpe)

    @classmethod
    def calculate_sortino(
        cls,
        equity_curve: list[EquityPoint],
        timeframe_hours: float,
    ) -> float:
        """
        Calculate Sortino ratio (downside deviation only).

        Args:
            equity_curve: List of equity points
            timeframe_hours: Hours per period

        Returns:
            Annualized Sortino ratio
        """
        if len(equity_curve) < 2:
            return 0.0

        equities = [ep.equity for ep in equity_curve]
        returns = np.diff(equities) / equities[:-1]

        if len(returns) == 0:
            return 0.0

        # Only negative returns for downside deviation
        negative_returns = returns[returns < 0]

        if len(negative_returns) == 0:
            return float("inf") if np.mean(returns) > 0 else 0.0

        downside_std = np.std(negative_returns)

        if downside_std == 0:
            return 0.0

        periods_per_year = cls.HOURS_PER_YEAR / timeframe_hours
        rf_per_period = cls.RISK_FREE_RATE / periods_per_year

        sortino = (np.mean(returns) - rf_per_period) / downside_std
        annualized_sortino = sortino * np.sqrt(periods_per_year)

        return float(annualized_sortino)

    @classmethod
    def calculate_calmar(
        cls,
        total_return: float,
        max_drawdown: float,
        years: float,
    ) -> float:
        """
        Calculate Calmar ratio (return / max drawdown).

        Args:
            total_return: Total return as decimal
            max_drawdown: Maximum drawdown as decimal
            years: Number of years in backtest

        Returns:
            Calmar ratio
        """
        if max_drawdown == 0 or years == 0:
            return 0.0

        annualized_return = (1 + total_return) ** (1 / years) - 1
        return annualized_return / max_drawdown
