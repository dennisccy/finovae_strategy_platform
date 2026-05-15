"""
Strategy Rating Calculator

Computes 5-category rating system from backtest results and raw OHLCV data.
Categories: Profitability, Risk Resistance, Risk-Reward, Win Rate & EV, Liquidity.
"""

import bisect
import math
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Optional

import numpy as np
import pandas as pd

from backtest.metrics import MetricsCalculator
from shared.contracts import (
    BacktestResult,
    CapacityLevel,
    CategoryRating,
    DrawdownPeriod,
    EquityPoint,
    HistogramBin,
    MonthlyReturn,
    OHLCV,
    RollingMetric,
    SimulatedStopLevel,
    StrategyRating,
    Trade,
    TradeExcursion,
)


def _safe_round(v: float, ndigits: int = 2) -> float:
    """Round a float, replacing inf/nan with safe values."""
    if math.isinf(v) or math.isnan(v):
        return 9999.99 if v > 0 else -9999.99
    return round(v, ndigits)


class RatingCalculator:
    """Computes all 5 rating categories from backtest results + raw OHLCV data."""

    @classmethod
    def calculate(
        cls,
        result: BacktestResult,
        ohlcv_data: list[OHLCV],
        initial_capital: float,
        timeframe_hours: float,
        step_callback: Optional[Callable[[str, int], None]] = None,
    ) -> tuple[StrategyRating, dict[str, float]]:
        """Returns (StrategyRating, per-step timings dict)."""
        step_timings: dict[str, float] = {}

        if not ohlcv_data or not result.equity_curve:
            return cls._empty_rating(), step_timings

        # Step 1: Benchmark
        if step_callback:
            step_callback("benchmark_ms", 0)
        t0 = time.perf_counter()
        benchmark_equity, benchmark_return = cls._compute_benchmark(
            ohlcv_data, initial_capital
        )
        step_timings["benchmark_ms"] = (time.perf_counter() - t0) * 1000

        # Step 2: Monthly & annual returns
        if step_callback:
            step_callback("returns_ms", 1)
        t0 = time.perf_counter()
        monthly_returns = cls._compute_monthly_returns(result.equity_curve)
        annual_returns = cls._compute_annual_returns(result.equity_curve)
        benchmark_annual_returns = cls._compute_annual_returns(benchmark_equity)
        annual_long_returns, annual_short_returns = cls._compute_annual_returns_by_direction(
            result.trades, initial_capital, result.equity_curve
        )
        step_timings["returns_ms"] = (time.perf_counter() - t0) * 1000

        # Step 3: MAE/MFE
        if step_callback:
            step_callback("mae_mfe_ms", 2)
        t0 = time.perf_counter()
        trade_excursions = cls._compute_mae_mfe(result.trades, ohlcv_data)
        step_timings["mae_mfe_ms"] = (time.perf_counter() - t0) * 1000

        # Step 4: Drawdown periods
        if step_callback:
            step_callback("drawdowns_ms", 3)
        t0 = time.perf_counter()
        drawdown_periods = cls._compute_drawdown_periods(result.equity_curve)
        step_timings["drawdowns_ms"] = (time.perf_counter() - t0) * 1000

        # Step 5: Rolling Sharpe
        if step_callback:
            step_callback("rolling_sharpe_ms", 4)
        t0 = time.perf_counter()
        rolling_sharpe = cls._compute_rolling_sharpe(
            result.equity_curve, 90, timeframe_hours
        )
        rolling_sharpe_bm = cls._compute_rolling_sharpe(
            benchmark_equity, 90, timeframe_hours
        )
        step_timings["rolling_sharpe_ms"] = (time.perf_counter() - t0) * 1000

        # Step 6: Return distribution
        if step_callback:
            step_callback("distribution_ms", 5)
        t0 = time.perf_counter()
        return_distribution = cls._compute_return_distribution(result.trades)
        step_timings["distribution_ms"] = (time.perf_counter() - t0) * 1000

        # Step 7: Risk-adjusted ratios (alpha, beta, Sortino, Calmar, VaR, CVaR, tail ratio)
        if step_callback:
            step_callback("ratios_ms", 6)
        t0_ratios = time.perf_counter()

        # Total duration in years
        if len(result.equity_curve) >= 2:
            duration_secs = (
                result.equity_curve[-1].timestamp - result.equity_curve[0].timestamp
            ).total_seconds()
            years = max(duration_secs / (365.25 * 86400), 1 / 365.25)
        else:
            years = 1.0

        # Guard against negative base (total_return < -1 with leverage/shorts blows up)
        _growth = 1 + result.total_return
        annualized_return = _growth ** (1 / years) - 1 if (years > 0 and _growth > 0) else max(result.total_return, -1.0)

        # Alpha / Beta vs benchmark
        alpha, beta = cls._compute_alpha_beta(
            result.equity_curve, benchmark_equity, timeframe_hours
        )

        # Sortino / Calmar
        sortino = MetricsCalculator.calculate_sortino(
            result.equity_curve, timeframe_hours
        )
        calmar = MetricsCalculator.calculate_calmar(
            result.total_return, result.max_drawdown, years
        )

        # Avg trade duration in days
        avg_duration_days = 0.0
        if result.trades:
            durations = [
                (t.exit_time - t.entry_time).total_seconds() / 86400
                for t in result.trades
            ]
            avg_duration_days = float(np.mean(durations))

        # Avg drawdown
        avg_drawdown = float(np.mean([ep.drawdown for ep in result.equity_curve]))

        # Avg recovery time
        recovery_times = [
            dp.recovery_days for dp in drawdown_periods if dp.recovery_days is not None
        ]
        avg_recovery_days = float(np.mean(recovery_times)) if recovery_times else 0.0

        # VaR / CVaR from daily returns
        var_5, cvar_5 = cls._compute_var_cvar(result.equity_curve)

        # Tail ratio
        tail_ratio = cls._compute_tail_ratio(result.equity_curve)

        step_timings["ratios_ms"] = (time.perf_counter() - t0_ratios) * 1000

        # Step 8: Simulated stop-loss
        if step_callback:
            step_callback("sim_stops_ms", 7)
        t0_stops = time.perf_counter()
        simulated_stops = cls._compute_simulated_stops(
            result.trades, ohlcv_data, "stop", excursions=trade_excursions,
        )
        step_timings["sim_stops_ms"] = (time.perf_counter() - t0_stops) * 1000

        # Step 9: Simulated take-profit
        if step_callback:
            step_callback("sim_tp_ms", 8)
        t0_tp = time.perf_counter()
        simulated_tps = cls._compute_simulated_stops(
            result.trades, ohlcv_data, "take_profit", excursions=trade_excursions,
        )
        step_timings["sim_tp_ms"] = (time.perf_counter() - t0_tp) * 1000

        # Step 10: Liquidity & capacity
        if step_callback:
            step_callback("liquidity_ms", 9)
        t0_liq = time.perf_counter()
        liq_metrics = cls._compute_liquidity_metrics(result.trades, ohlcv_data, initial_capital)
        capacity_levels = cls._compute_capacity(result.trades, ohlcv_data, initial_capital, liq_metrics=liq_metrics)
        step_timings["liquidity_ms"] = (time.perf_counter() - t0_liq) * 1000

        # Win rate & EV
        win_rate = result.win_rate
        ev_per_trade = 0.0
        if result.trades:
            ev_per_trade = float(np.mean([t.pnl_percent for t in result.trades]))

        # Monthly beat benchmark rate
        bm_monthly = cls._compute_monthly_returns(benchmark_equity)
        monthly_beat_rate = cls._compute_monthly_beat_rate(monthly_returns, bm_monthly)

        # MAE/MFE averages
        avg_mae = float(np.mean([te.mae for te in trade_excursions])) if trade_excursions else 0.0
        avg_mfe = float(np.mean([te.mfe for te in trade_excursions])) if trade_excursions else 0.0

        # Build category ratings
        total_commission = sum(t.commission_paid for t in result.trades)
        commission_pct_capital = total_commission / initial_capital * 100

        # Return contribution by direction
        long_pnl = sum(t.pnl for t in result.trades if getattr(t, "direction", "long") == "long")
        short_pnl = sum(t.pnl for t in result.trades if getattr(t, "direction", "long") == "short")
        return_from_long = round(long_pnl / initial_capital * 100, 2)
        return_from_short = round(short_pnl / initial_capital * 100, 2)

        profitability = CategoryRating(
            name="profitability",
            label="Profitability",
            stars=cls._rate_profitability(annualized_return, alpha),
            key_metrics={
                "annual_return": round(annualized_return * 100, 2),
                "alpha": round(alpha * 100, 2),
                "beta": round(beta, 2),
                "avg_trade_duration_days": round(avg_duration_days, 1),
                "total_trades": result.num_trades,
                "total_commission": round(total_commission, 2),
                "commission_pct_capital": round(commission_pct_capital, 2),
                "return_from_long": return_from_long,
                "return_from_short": return_from_short,
            },
            analyses={
                "excess_return": round((annualized_return - benchmark_return / max(years, 1)) * 100, 2),
            },
        )

        risk_resistance = CategoryRating(
            name="risk_resistance",
            label="Risk Resistance",
            stars=cls._rate_risk_resistance(result.max_drawdown, avg_drawdown),
            key_metrics={
                "max_drawdown": round(result.max_drawdown * 100, 2),
                "avg_drawdown": round(avg_drawdown * 100, 2),
                "avg_recovery_days": round(avg_recovery_days, 1),
                "var_5": round(var_5 * 100, 2),
                "cvar_5": round(cvar_5 * 100, 2),
            },
            analyses={},
        )

        risk_reward = CategoryRating(
            name="risk_reward",
            label="Risk/Reward",
            stars=cls._rate_risk_reward(result.sharpe_ratio, sortino),
            key_metrics={
                "sharpe_ratio": _safe_round(result.sharpe_ratio, 2),
                "sortino_ratio": _safe_round(sortino, 2),
                "calmar_ratio": _safe_round(calmar, 2),
                "profit_factor": _safe_round(result.profit_factor, 2),
                "tail_ratio": _safe_round(tail_ratio, 2),
            },
            analyses={},
        )

        win_rate_ev_rating = CategoryRating(
            name="win_rate_ev",
            label="Win Rate & EV",
            stars=cls._rate_win_rate_ev(win_rate, ev_per_trade),
            key_metrics={
                "win_rate": round(win_rate * 100, 1),
                "monthly_beat_rate": round(monthly_beat_rate * 100, 1),
                "expected_value": round(ev_per_trade * 100, 2),
                "avg_mae": round(avg_mae * 100, 2),
                "avg_mfe": round(avg_mfe * 100, 2),
            },
            analyses={},
        )

        liquidity_rating = CategoryRating(
            name="liquidity",
            label="Liquidity",
            stars=cls._rate_liquidity(
                liq_metrics.get("volume_participation_rate", 1.0),
                liq_metrics.get("estimated_capacity", 0),
            ),
            key_metrics={
                "avg_daily_volume": round(liq_metrics.get("avg_daily_volume", 0), 0),
                "volume_participation_rate": round(liq_metrics.get("volume_participation_rate", 0) * 100, 2),
                "estimated_capacity": round(liq_metrics.get("estimated_capacity", 0), 0),
                "avg_spread_impact": round(liq_metrics.get("avg_spread_impact", 0) * 100, 4),
                "entry_exit_volume_ratio": round(liq_metrics.get("entry_exit_volume_ratio", 1.0), 2),
            },
            analyses={},
        )

        rating = StrategyRating(
            profitability=profitability,
            risk_resistance=risk_resistance,
            risk_reward=risk_reward,
            win_rate_ev=win_rate_ev_rating,
            liquidity=liquidity_rating,
            benchmark_equity=benchmark_equity,
            benchmark_total_return=benchmark_return,
            monthly_returns=monthly_returns,
            trade_excursions=trade_excursions,
            drawdown_periods=drawdown_periods[:5],  # top 5
            rolling_sharpe=rolling_sharpe,
            rolling_sharpe_benchmark=rolling_sharpe_bm,
            return_distribution=return_distribution,
            simulated_stops=simulated_stops,
            simulated_take_profits=simulated_tps,
            capacity_levels=capacity_levels,
            annual_returns=annual_returns,
            benchmark_annual_returns=benchmark_annual_returns,
            annual_long_returns=annual_long_returns,
            annual_short_returns=annual_short_returns,
        )

        return rating, step_timings

    # =========================================================================
    # Benchmark
    # =========================================================================

    @classmethod
    def _compute_benchmark(
        cls, ohlcv_data: list[OHLCV], initial_capital: float
    ) -> tuple[list[EquityPoint], float]:
        """Buy-and-hold benchmark from OHLCV data."""
        if not ohlcv_data:
            return [], 0.0

        entry_price = ohlcv_data[0].open
        if entry_price <= 0:
            return [], 0.0

        quantity = initial_capital / entry_price
        peak = initial_capital
        equity_curve: list[EquityPoint] = []

        for bar in ohlcv_data:
            equity = quantity * bar.close
            peak = max(peak, equity)
            dd = (peak - equity) / peak if peak > 0 else 0.0
            equity_curve.append(
                EquityPoint(timestamp=bar.timestamp, equity=equity, drawdown=dd)
            )

        total_return = (equity_curve[-1].equity - initial_capital) / initial_capital if equity_curve else 0.0
        return equity_curve, total_return

    # =========================================================================
    # Alpha / Beta
    # =========================================================================

    @classmethod
    def _compute_alpha_beta(
        cls,
        strategy_equity: list[EquityPoint],
        benchmark_equity: list[EquityPoint],
        timeframe_hours: float,
    ) -> tuple[float, float]:
        """Compute alpha and beta vs benchmark using period returns."""
        if len(strategy_equity) < 2 or len(benchmark_equity) < 2:
            return 0.0, 0.0

        # Align by length (take min)
        n = min(len(strategy_equity), len(benchmark_equity))
        s_eq = [ep.equity for ep in strategy_equity[:n]]
        b_eq = [ep.equity for ep in benchmark_equity[:n]]

        s_returns = np.diff(s_eq) / np.array(s_eq[:-1])
        b_returns = np.diff(b_eq) / np.array(b_eq[:-1])

        if len(s_returns) == 0 or np.std(b_returns) == 0:
            return 0.0, 0.0

        # Beta = cov(s, b) / var(b)
        beta = float(np.cov(s_returns, b_returns)[0, 1] / np.var(b_returns))

        # Alpha (annualized) = annualized(mean(s) - beta * mean(b))
        periods_per_year = (24 * 365) / timeframe_hours
        alpha_per_period = float(np.mean(s_returns) - beta * np.mean(b_returns))
        alpha = alpha_per_period * periods_per_year

        return alpha, beta

    # =========================================================================
    # VaR / CVaR
    # =========================================================================

    @classmethod
    def _compute_var_cvar(cls, equity_curve: list[EquityPoint]) -> tuple[float, float]:
        """Compute Value at Risk (5th percentile) and Conditional VaR."""
        if len(equity_curve) < 2:
            return 0.0, 0.0

        equities = [ep.equity for ep in equity_curve]
        returns = np.diff(equities) / np.array(equities[:-1])

        if len(returns) == 0:
            return 0.0, 0.0

        var_5 = float(np.percentile(returns, 5))
        cvar_5 = float(np.mean(returns[returns <= var_5])) if np.any(returns <= var_5) else var_5
        return abs(var_5), abs(cvar_5)

    # =========================================================================
    # Tail Ratio
    # =========================================================================

    @classmethod
    def _compute_tail_ratio(cls, equity_curve: list[EquityPoint]) -> float:
        """Tail ratio: 95th percentile / abs(5th percentile)."""
        if len(equity_curve) < 2:
            return 0.0

        equities = [ep.equity for ep in equity_curve]
        returns = np.diff(equities) / np.array(equities[:-1])

        if len(returns) == 0:
            return 0.0

        p95 = float(np.percentile(returns, 95))
        p5 = float(np.percentile(returns, 5))

        if p5 == 0:
            return 0.0

        return abs(p95 / p5)

    # =========================================================================
    # MAE / MFE
    # =========================================================================

    @classmethod
    def _compute_mae_mfe(
        cls, trades: list[Trade], ohlcv_data: list[OHLCV]
    ) -> list[TradeExcursion]:
        """Compute MAE/MFE for each trade from OHLCV bars."""
        if not trades or not ohlcv_data:
            return []

        # Build timestamp index for quick lookup
        bars_by_time = {bar.timestamp: bar for bar in ohlcv_data}
        sorted_times = sorted(bars_by_time.keys())

        excursions: list[TradeExcursion] = []

        for trade in trades:
            # Find bars between entry and exit
            entry_price = trade.entry_price
            if entry_price <= 0:
                excursions.append(
                    TradeExcursion(
                        trade_id=trade.trade_id,
                        pnl_percent=trade.pnl_percent,
                        mae=0.0,
                        mfe=0.0,
                    )
                )
                continue

            # Get bars in trade period via binary search
            left = bisect.bisect_left(sorted_times, trade.entry_time)
            right = bisect.bisect_right(sorted_times, trade.exit_time)
            trade_lows = []
            trade_highs = []
            for idx in range(left, right):
                bar = bars_by_time[sorted_times[idx]]
                trade_lows.append(bar.low)
                trade_highs.append(bar.high)

            if not trade_lows:
                excursions.append(
                    TradeExcursion(
                        trade_id=trade.trade_id,
                        pnl_percent=trade.pnl_percent,
                        mae=0.0,
                        mfe=0.0,
                    )
                )
                continue

            min_low = min(trade_lows)
            max_high = max(trade_highs)

            # Direction-aware MAE/MFE (v0.7)
            # Long: adverse = price falling (low), favorable = price rising (high)
            # Short: adverse = price rising (high), favorable = price falling (low)
            is_short = getattr(trade, "direction", "long") == "short"
            if is_short:
                mae = max(0.0, (max_high - entry_price) / entry_price)
                mfe = max(0.0, (entry_price - min_low) / entry_price)
            else:
                mae = max(0.0, (entry_price - min_low) / entry_price)
                mfe = max(0.0, (max_high - entry_price) / entry_price)

            excursions.append(
                TradeExcursion(
                    trade_id=trade.trade_id,
                    pnl_percent=trade.pnl_percent,
                    mae=mae,
                    mfe=mfe,
                )
            )

        return excursions

    # =========================================================================
    # Drawdown Periods
    # =========================================================================

    @classmethod
    def _compute_drawdown_periods(
        cls, equity_curve: list[EquityPoint]
    ) -> list[DrawdownPeriod]:
        """Identify and rank drawdown periods."""
        if not equity_curve:
            return []

        periods: list[DrawdownPeriod] = []
        in_drawdown = False
        dd_start: Optional[datetime] = None
        dd_peak_time: Optional[datetime] = None
        max_depth = 0.0
        trough_time: Optional[datetime] = None

        for i, ep in enumerate(equity_curve):
            if ep.drawdown > 0:
                if not in_drawdown:
                    in_drawdown = True
                    dd_start = ep.timestamp
                    max_depth = ep.drawdown
                    trough_time = ep.timestamp
                elif ep.drawdown > max_depth:
                    max_depth = ep.drawdown
                    trough_time = ep.timestamp
            else:
                if in_drawdown and dd_start is not None and trough_time is not None:
                    duration_days = (trough_time - dd_start).total_seconds() / 86400
                    recovery_days = (ep.timestamp - trough_time).total_seconds() / 86400
                    periods.append(
                        DrawdownPeriod(
                            start_time=dd_start,
                            end_time=trough_time,
                            recovery_time=ep.timestamp,
                            depth=max_depth,
                            duration_days=duration_days,
                            recovery_days=recovery_days,
                        )
                    )
                    in_drawdown = False
                    max_depth = 0.0

        # Handle ongoing drawdown
        if in_drawdown and dd_start is not None and trough_time is not None:
            duration_days = (trough_time - dd_start).total_seconds() / 86400
            periods.append(
                DrawdownPeriod(
                    start_time=dd_start,
                    end_time=trough_time,
                    recovery_time=None,
                    depth=max_depth,
                    duration_days=duration_days,
                    recovery_days=None,
                )
            )

        # Sort by depth descending, return top 5
        periods.sort(key=lambda p: p.depth, reverse=True)
        return periods[:5]

    # =========================================================================
    # Monthly Returns
    # =========================================================================

    @classmethod
    def _compute_monthly_returns(
        cls, equity_curve: list[EquityPoint]
    ) -> list[MonthlyReturn]:
        """Compute monthly returns from equity curve."""
        if len(equity_curve) < 2:
            return []

        # Group equity by (year, month) - take first and last of each month
        monthly: dict[tuple[int, int], list[EquityPoint]] = defaultdict(list)
        for ep in equity_curve:
            monthly[(ep.timestamp.year, ep.timestamp.month)].append(ep)

        results: list[MonthlyReturn] = []
        sorted_keys = sorted(monthly.keys())

        for i, key in enumerate(sorted_keys):
            points = monthly[key]
            if i == 0:
                # First month: use the first point as the starting equity
                start_eq = points[0].equity
            else:
                # Use last equity from previous month
                prev_key = sorted_keys[i - 1]
                start_eq = monthly[prev_key][-1].equity

            end_eq = points[-1].equity

            if start_eq > 0:
                ret = (end_eq - start_eq) / start_eq
            else:
                ret = 0.0

            results.append(
                MonthlyReturn(year=key[0], month=key[1], return_pct=ret)
            )

        return results

    # =========================================================================
    # Annual Returns
    # =========================================================================

    @classmethod
    def _compute_annual_returns(
        cls, equity_curve: list[EquityPoint]
    ) -> dict[int, float]:
        """Compute annual returns from equity curve."""
        if len(equity_curve) < 2:
            return {}

        yearly: dict[int, list[EquityPoint]] = defaultdict(list)
        for ep in equity_curve:
            yearly[ep.timestamp.year].append(ep)

        results: dict[int, float] = {}
        sorted_years = sorted(yearly.keys())

        for i, year in enumerate(sorted_years):
            points = yearly[year]
            if i == 0:
                start_eq = points[0].equity
            else:
                prev_year = sorted_years[i - 1]
                start_eq = yearly[prev_year][-1].equity

            end_eq = points[-1].equity
            if start_eq > 0:
                results[year] = (end_eq - start_eq) / start_eq
            else:
                results[year] = 0.0

        return results

    @classmethod
    def _compute_annual_returns_by_direction(
        cls,
        trades: list,
        initial_capital: float,
        equity_curve: list,
    ) -> tuple[dict[int, float], dict[int, float]]:
        """Compute per-year PnL contribution from long and short trades as fraction of year-start equity.

        Uses the same year-start equity denominator as _compute_annual_returns so that
        long% + short% is comparable to the equity-curve annual return for each year.
        Falls back to initial_capital for any year not found in the equity curve.
        """
        if initial_capital <= 0:
            return {}, {}

        # Build year-start equity from equity curve (mirrors _compute_annual_returns logic)
        yearly: dict[int, list] = defaultdict(list)
        for ep in equity_curve:
            yearly[ep.timestamp.year].append(ep)

        sorted_years = sorted(yearly.keys())
        year_start_equity: dict[int, float] = {}
        for i, year in enumerate(sorted_years):
            if i == 0:
                year_start_equity[year] = yearly[year][0].equity
            else:
                prev_year = sorted_years[i - 1]
                year_start_equity[year] = yearly[prev_year][-1].equity

        long_by_year: dict[int, float] = defaultdict(float)
        short_by_year: dict[int, float] = defaultdict(float)
        for t in trades:
            year = t.exit_time.year
            direction = getattr(t, "direction", "long")
            if direction == "long":
                long_by_year[year] += t.pnl
            else:
                short_by_year[year] += t.pnl

        long_annual = {
            yr: round(pnl / year_start_equity.get(yr, initial_capital), 6)
            for yr, pnl in long_by_year.items()
        }
        short_annual = {
            yr: round(pnl / year_start_equity.get(yr, initial_capital), 6)
            for yr, pnl in short_by_year.items()
        }
        return long_annual, short_annual

    # =========================================================================
    # Rolling Sharpe
    # =========================================================================

    @classmethod
    def _compute_rolling_sharpe(
        cls,
        equity_curve: list[EquityPoint],
        window_periods: int,
        timeframe_hours: float,
    ) -> list[RollingMetric]:
        """Compute rolling Sharpe ratio (vectorized)."""
        if len(equity_curve) < window_periods + 1:
            return []

        equities = np.array([ep.equity for ep in equity_curve])
        returns = np.diff(equities) / equities[:-1]

        periods_per_year = (24 * 365) / timeframe_hours
        rf_per_period = 0.05 / periods_per_year

        excess = pd.Series(returns - rf_per_period)
        roll_mean = excess.rolling(window=window_periods).mean()
        roll_std = excess.rolling(window=window_periods).std(ddof=0)

        # Sharpe = mean / std * sqrt(annualization), 0 where std == 0
        sqrt_ann = np.sqrt(periods_per_year)
        sharpe_series = np.where(
            roll_std > 0, roll_mean / roll_std * sqrt_ann, 0.0
        )

        # pandas rolling at index j covers [j-w+1..j], original loop at i used [i-w..i-1]
        # so sharpe_series[i-1] matches the original window for loop index i
        results: list[RollingMetric] = []
        for i in range(window_periods, len(returns)):
            results.append(
                RollingMetric(
                    timestamp=equity_curve[i + 1].timestamp,
                    value=float(sharpe_series[i - 1]),
                )
            )

        return results

    # =========================================================================
    # Return Distribution
    # =========================================================================

    @classmethod
    def _compute_return_distribution(cls, trades: list[Trade]) -> list[HistogramBin]:
        """Compute histogram of trade returns."""
        if not trades:
            return []

        returns = [t.pnl_percent for t in trades]
        if not returns:
            return []

        # Auto-bin using numpy
        counts, bin_edges = np.histogram(returns, bins=min(20, max(5, len(returns) // 3)))

        bins: list[HistogramBin] = []
        for i in range(len(counts)):
            bins.append(
                HistogramBin(
                    bin_start=float(bin_edges[i]),
                    bin_end=float(bin_edges[i + 1]),
                    count=int(counts[i]),
                )
            )

        return bins

    # =========================================================================
    # Simulated Stop-Loss / Take-Profit
    # =========================================================================

    @classmethod
    def _compute_simulated_stops(
        cls,
        trades: list[Trade],
        ohlcv_data: list[OHLCV],
        mode: str,  # "stop" or "take_profit"
        excursions: list[TradeExcursion] | None = None,
    ) -> list[SimulatedStopLevel]:
        """Simulate how different stop-loss/take-profit levels affect results."""
        if not trades:
            return []

        if excursions is None:
            excursions = cls._compute_mae_mfe(trades, ohlcv_data)
        if not excursions:
            return []

        levels = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
        results: list[SimulatedStopLevel] = []

        for level in levels:
            adjusted_returns = []
            affected = 0

            for exc in excursions:
                if mode == "stop":
                    # If MAE exceeds stop level, trade is stopped out at -level
                    if exc.mae >= level:
                        adjusted_returns.append(-level)
                        affected += 1
                    else:
                        adjusted_returns.append(exc.pnl_percent)
                else:  # take_profit
                    # If MFE exceeds TP level, trade exits at +level
                    if exc.mfe >= level:
                        adjusted_returns.append(level)
                        affected += 1
                    else:
                        adjusted_returns.append(exc.pnl_percent)

            if adjusted_returns:
                adj_total = float(np.sum(adjusted_returns))
                adj_wins = sum(1 for r in adjusted_returns if r > 0)
                adj_wr = adj_wins / len(adjusted_returns)
            else:
                adj_total = 0.0
                adj_wr = 0.0

            results.append(
                SimulatedStopLevel(
                    level_pct=level * 100,
                    adjusted_return=round(adj_total * 100, 2),
                    adjusted_win_rate=round(adj_wr * 100, 1),
                    trades_affected=affected,
                )
            )

        return results

    # =========================================================================
    # Capacity / Liquidity
    # =========================================================================

    @classmethod
    def _compute_liquidity_metrics(
        cls,
        trades: list[Trade],
        ohlcv_data: list[OHLCV],
        initial_capital: float,
    ) -> dict:
        """Compute liquidity-related metrics."""
        if not trades or not ohlcv_data:
            return {
                "avg_daily_volume": 0,
                "volume_participation_rate": 0,
                "estimated_capacity": 0,
                "avg_spread_impact": 0,
                "entry_exit_volume_ratio": 1.0,
            }

        bars_by_time = {bar.timestamp: bar for bar in ohlcv_data}

        entry_volumes = []
        exit_volumes = []
        participation_rates = []
        spread_impacts = []

        for trade in trades:
            # Entry bar volume
            entry_bar = bars_by_time.get(trade.entry_time)
            exit_bar = bars_by_time.get(trade.exit_time)

            if entry_bar and entry_bar.quote_volume > 0:
                entry_volumes.append(entry_bar.quote_volume)
                trade_value = trade.entry_price * trade.quantity
                pr = trade_value / entry_bar.quote_volume
                participation_rates.append(pr)
                # Spread impact: (high - low) / close as proxy
                if entry_bar.close > 0:
                    spread = (entry_bar.high - entry_bar.low) / entry_bar.close
                    spread_impacts.append(spread)

            if exit_bar and exit_bar.quote_volume > 0:
                exit_volumes.append(exit_bar.quote_volume)

        avg_daily_volume = float(np.mean(entry_volumes)) if entry_volumes else 0.0
        avg_participation = float(np.mean(participation_rates)) if participation_rates else 0.0
        avg_spread = float(np.mean(spread_impacts)) if spread_impacts else 0.0

        # Estimated capacity: capital where participation rate reaches 5%
        estimated_capacity = 0.0
        if avg_participation > 0:
            estimated_capacity = initial_capital * (0.05 / avg_participation)

        # Entry/exit volume ratio
        avg_entry_vol = float(np.mean(entry_volumes)) if entry_volumes else 1.0
        avg_exit_vol = float(np.mean(exit_volumes)) if exit_volumes else 1.0
        ratio = avg_entry_vol / avg_exit_vol if avg_exit_vol > 0 else 1.0

        return {
            "avg_daily_volume": avg_daily_volume,
            "volume_participation_rate": avg_participation,
            "estimated_capacity": estimated_capacity,
            "avg_spread_impact": avg_spread,
            "entry_exit_volume_ratio": ratio,
        }

    @classmethod
    def _compute_capacity(
        cls,
        trades: list[Trade],
        ohlcv_data: list[OHLCV],
        initial_capital: float,
        liq_metrics: dict | None = None,
    ) -> list[CapacityLevel]:
        """Estimate performance at different capital levels."""
        if not trades or not ohlcv_data:
            return []

        liq = liq_metrics if liq_metrics is not None else cls._compute_liquidity_metrics(trades, ohlcv_data, initial_capital)
        base_vpr = liq["volume_participation_rate"]

        if base_vpr <= 0:
            return []

        capital_levels = [10_000, 50_000, 100_000, 500_000, 1_000_000, 5_000_000]
        results: list[CapacityLevel] = []

        for cap in capital_levels:
            scale = cap / initial_capital if initial_capital > 0 else 1.0
            vpr = base_vpr * scale
            # Simple slippage model: slippage grows with participation rate
            slippage_bps = min(vpr * 100 * 10, 500)  # cap at 500 bps

            results.append(
                CapacityLevel(
                    capital=cap,
                    volume_participation_pct=round(vpr * 100, 2),
                    estimated_slippage_bps=round(slippage_bps, 1),
                )
            )

        return results

    # =========================================================================
    # Monthly Beat Benchmark Rate
    # =========================================================================

    @classmethod
    def _compute_monthly_beat_rate(
        cls,
        strategy_monthly: list[MonthlyReturn],
        benchmark_monthly: list[MonthlyReturn],
    ) -> float:
        """Compute percentage of months where strategy beats benchmark."""
        if not strategy_monthly or not benchmark_monthly:
            return 0.0

        bm_dict = {(m.year, m.month): m.return_pct for m in benchmark_monthly}
        beat_count = 0
        total = 0

        for sm in strategy_monthly:
            bm_ret = bm_dict.get((sm.year, sm.month))
            if bm_ret is not None:
                total += 1
                if sm.return_pct > bm_ret:
                    beat_count += 1

        return beat_count / total if total > 0 else 0.0

    # =========================================================================
    # Star Rating Logic
    # =========================================================================

    @classmethod
    def _rate_profitability(cls, annual_return: float, alpha: float) -> int:
        if annual_return > 0.50 and alpha > 0.20:
            return 5
        if annual_return > 0.25 and alpha > 0.10:
            return 4
        if annual_return > 0.10 and alpha > 0.0:
            return 3
        if annual_return > 0.0:
            return 2
        return 1

    @classmethod
    def _rate_risk_resistance(cls, max_dd: float, avg_dd: float) -> int:
        if max_dd < 0.10 and avg_dd < 0.03:
            return 5
        if max_dd < 0.20 and avg_dd < 0.05:
            return 4
        if max_dd < 0.30 and avg_dd < 0.08:
            return 3
        if max_dd < 0.50:
            return 2
        return 1

    @classmethod
    def _rate_risk_reward(cls, sharpe: float, sortino: float) -> int:
        if sharpe > 2.0 and sortino > 3.0:
            return 5
        if sharpe > 1.5 and sortino > 2.0:
            return 4
        if sharpe > 1.0 and sortino > 1.0:
            return 3
        if sharpe > 0.5:
            return 2
        return 1

    @classmethod
    def _rate_win_rate_ev(cls, win_rate: float, ev: float) -> int:
        if win_rate > 0.60 and ev > 0.03:
            return 5
        if win_rate > 0.50 and ev > 0.02:
            return 4
        if win_rate > 0.40 and ev > 0.01:
            return 3
        if win_rate > 0.30 and ev > 0.0:
            return 2
        return 1

    @classmethod
    def _rate_liquidity(cls, vpr: float, capacity: float) -> int:
        if vpr < 0.01 and capacity > 1_000_000:
            return 5
        if vpr < 0.05 and capacity > 500_000:
            return 4
        if vpr < 0.10 and capacity > 100_000:
            return 3
        if vpr < 0.25:
            return 2
        return 1

    # =========================================================================
    # Empty Rating (edge case)
    # =========================================================================

    @classmethod
    def _empty_rating(cls) -> StrategyRating:
        """Return a minimal rating when there's insufficient data."""
        empty_cat = lambda name, label: CategoryRating(
            name=name, label=label, stars=1, key_metrics={}, analyses={}
        )
        return StrategyRating(
            profitability=empty_cat("profitability", "Profitability"),
            risk_resistance=empty_cat("risk_resistance", "Risk Resistance"),
            risk_reward=empty_cat("risk_reward", "Risk/Reward"),
            win_rate_ev=empty_cat("win_rate_ev", "Win Rate & EV"),
            liquidity=empty_cat("liquidity", "Liquidity"),
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
