"""
Walk-Forward Validation

Splits the full date range into rolling IS+OOS windows and tests whether
OOS performance tracks IS performance — the standard robustness check used
by professional quants.

Window type: Rolling (both IS and OOS slide forward by one OOS period)
"""

import calendar
import uuid
from bisect import bisect_left
from datetime import date, datetime, timezone
from typing import Callable, Optional

import numpy as np

from backtest.engine import BacktestEngine
from shared.contracts import (
    BacktestRequest,
    EquityPoint,
    OHLCV,
    WalkForwardResult,
    WalkForwardWindow,
)


# =============================================================================
# Helpers
# =============================================================================


def _add_months(d: date, months: int) -> date:
    """Add months to a date without requiring dateutil."""
    total_months = d.month - 1 + months
    year = d.year + total_months // 12
    month = total_months % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


def _date_to_dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _slice_data(
    full_data: list[OHLCV],
    timestamps: list[datetime],
    start: date,
    end: date,
) -> list[OHLCV]:
    """Slice OHLCV data to [start, end) using bisect on pre-built timestamp list."""
    start_dt = _date_to_dt(start)
    end_dt = _date_to_dt(end)
    lo = bisect_left(timestamps, start_dt)
    hi = bisect_left(timestamps, end_dt)
    return full_data[lo:hi]


def _sharpe(equity_curve: list[EquityPoint], timeframe_hours: float) -> float:
    """Compute annualized Sharpe ratio from an equity curve (bar returns)."""
    if len(equity_curve) < 3:
        return 0.0
    equities = np.array([ep.equity for ep in equity_curve], dtype=float)
    returns = np.diff(equities) / equities[:-1]
    if len(returns) < 2:
        return 0.0
    std = float(np.std(returns, ddof=1))
    if std == 0.0:
        return 0.0
    mean = float(np.mean(returns))
    periods_per_year = 8760.0 / max(timeframe_hours, 1.0 / 60.0)
    return mean / std * float(np.sqrt(periods_per_year))


def _safe_float(v: float) -> float:
    """Clamp inf/nan to 0.0."""
    import math
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return v


# =============================================================================
# Window generation
# =============================================================================


def _generate_windows(
    full_start: date,
    full_end: date,
    is_months: int,
    oos_months: int,
    max_windows: Optional[int] = None,
) -> list[tuple[date, date, date, date]]:
    """
    Generate rolling IS+OOS window boundaries.

    Returns list of (is_start, is_end, oos_start, oos_end).
    Stops when oos_end would exceed full_end.
    """
    windows: list[tuple[date, date, date, date]] = []
    win_start = full_start

    while True:
        is_start = win_start
        is_end = _add_months(is_start, is_months)
        oos_start = is_end
        oos_end = _add_months(oos_start, oos_months)

        if oos_end > full_end:
            break

        windows.append((is_start, is_end, oos_start, oos_end))

        # Slide window forward by one OOS period
        win_start = _add_months(win_start, oos_months)

        if max_windows is not None and len(windows) >= max_windows:
            break

    return windows


# =============================================================================
# Aggregate metrics
# =============================================================================


def _compute_combined_oos_equity(
    windows: list[WalkForwardWindow],
    initial_capital: float,
) -> list[EquityPoint]:
    """
    Build a compounded OOS equity curve by chaining all OOS windows.

    Each window's equity is scaled so it starts at the previous window's end equity.
    Drawdowns are recalculated over the combined curve.
    """
    combined: list[EquityPoint] = []
    running_equity = initial_capital

    for w in windows:
        curve = w.oos_equity_curve
        if not curve:
            continue
        w_initial = curve[0].equity
        if w_initial <= 0:
            continue
        scale = running_equity / w_initial
        for ep in curve:
            combined.append(EquityPoint(
                timestamp=ep.timestamp,
                equity=ep.equity * scale,
                drawdown=0.0,  # recalculated below
            ))
        running_equity = combined[-1].equity

    if not combined:
        return combined

    # Recalculate drawdowns over the combined compounded curve
    peak = combined[0].equity
    recalc: list[EquityPoint] = []
    for ep in combined:
        if ep.equity > peak:
            peak = ep.equity
        dd = (peak - ep.equity) / peak if peak > 0 else 0.0
        recalc.append(EquityPoint(
            timestamp=ep.timestamp,
            equity=ep.equity,
            drawdown=min(1.0, max(0.0, dd)),
        ))

    return recalc


def _compute_aggregate(
    windows: list[WalkForwardWindow],
    oos_win_counts: list[int],     # num winning trades per OOS window
    oos_trade_counts: list[int],   # num total trades per OOS window
    initial_capital: float,
    timeframe_hours: float,
) -> dict:
    """Compute aggregate metrics across all OOS windows."""
    combined_equity = _compute_combined_oos_equity(windows, initial_capital)

    combined_oos_return = (
        (combined_equity[-1].equity - initial_capital) / initial_capital
        if combined_equity else 0.0
    )

    combined_oos_sharpe = _safe_float(_sharpe(combined_equity, timeframe_hours))

    combined_oos_max_drawdown = max(
        (ep.drawdown for ep in combined_equity), default=0.0
    )

    total_oos_wins = sum(oos_win_counts)
    total_oos_trades = sum(oos_trade_counts)
    combined_oos_win_rate = (
        total_oos_wins / total_oos_trades if total_oos_trades > 0 else 0.0
    )

    oos_sharpes = [w.oos_sharpe for w in windows]
    is_sharpes = [w.is_sharpe for w in windows]
    mean_is = float(np.mean(is_sharpes)) if is_sharpes else 0.0
    mean_oos = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
    wfe = _safe_float(mean_oos / mean_is) if mean_is != 0.0 else 0.0

    return {
        "combined_oos_return": _safe_float(combined_oos_return),
        "combined_oos_sharpe": combined_oos_sharpe,
        "combined_oos_win_rate": float(combined_oos_win_rate),
        "combined_oos_max_drawdown": float(combined_oos_max_drawdown),
        "wfe": wfe,
        "combined_oos_equity": combined_equity,
    }


# =============================================================================
# Main entry point
# =============================================================================


async def run_walk_forward(
    engine: BacktestEngine,
    sandbox,
    code: str,
    symbol: str,
    timeframe: str,
    full_start: date,
    full_end: date,
    initial_capital: float,
    commission: float,
    slippage: float,
    allow_short: bool,
    leverage: float,
    is_months: int,
    oos_months: int,
    max_windows: Optional[int],
    full_data: list[OHLCV],
    timeframe_hours: float,
    status_callback: Optional[Callable],
) -> WalkForwardResult:
    """
    Run walk-forward validation over the given date range.

    full_data is pre-loaded once. A fresh strategy instance is created per
    window to ensure IS and OOS are independent. The engine runs synchronously
    per window in a thread.
    """
    import asyncio

    errors: list[str] = []

    # Build timestamp list for O(log N) slicing
    timestamps = [bar.timestamp for bar in full_data]

    windows_meta = _generate_windows(full_start, full_end, is_months, oos_months, max_windows)
    num_windows = len(windows_meta)

    if num_windows == 0:
        return WalkForwardResult(
            windows=[],
            num_windows=0,
            is_months=is_months,
            oos_months=oos_months,
            combined_oos_return=0.0,
            combined_oos_sharpe=0.0,
            combined_oos_win_rate=0.0,
            combined_oos_max_drawdown=0.0,
            wfe=0.0,
            combined_oos_equity=[],
            errors=["Not enough data to form any IS+OOS windows with the given parameters"],
        )

    completed_windows: list[WalkForwardWindow] = []
    oos_win_counts: list[int] = []
    oos_trade_counts: list[int] = []

    for idx, (is_start, is_end, oos_start, oos_end) in enumerate(windows_meta):
        if status_callback:
            await status_callback({
                "type": "status",
                "phase": "walk_forward",
                "wf_window": idx + 1,
                "wf_total": num_windows,
            })

        is_data = _slice_data(full_data, timestamps, is_start, is_end)
        oos_data = _slice_data(full_data, timestamps, oos_start, oos_end)

        if len(is_data) < 5 or len(oos_data) < 2:
            errors.append(
                f"Window {idx + 1}: insufficient data "
                f"(IS={len(is_data)}, OOS={len(oos_data)} bars) — skipped"
            )
            continue

        # Fresh IS strategy instance
        try:
            is_setup, is_signal = await asyncio.to_thread(
                sandbox.get_setup_and_signal_from_strategy, code
            )
        except Exception as e:
            errors.append(f"Window {idx + 1}: IS sandbox setup failed: {e}")
            continue

        # Run IS backtest
        try:
            is_request = BacktestRequest(
                run_id=str(uuid.uuid4())[:8],
                strategy_code=code,
                symbol=symbol,
                timeframe=timeframe,
                start_date=is_start,
                end_date=is_end,
                initial_capital=initial_capital,
                commission=commission,
                slippage=slippage,
                allow_short=allow_short,
                leverage=leverage,
            )
            is_result = await asyncio.to_thread(
                engine.run,
                request=is_request,
                data=is_data,
                signal_func=is_signal,
                setup_func=is_setup,
            )
        except Exception as e:
            errors.append(f"Window {idx + 1} IS run failed: {e}")
            continue

        # Fresh OOS strategy instance (independent of IS)
        try:
            oos_setup, oos_signal = await asyncio.to_thread(
                sandbox.get_setup_and_signal_from_strategy, code
            )
        except Exception as e:
            errors.append(f"Window {idx + 1}: OOS sandbox setup failed: {e}")
            continue

        # Run OOS backtest
        try:
            oos_request = BacktestRequest(
                run_id=str(uuid.uuid4())[:8],
                strategy_code=code,
                symbol=symbol,
                timeframe=timeframe,
                start_date=oos_start,
                end_date=oos_end,
                initial_capital=initial_capital,
                commission=commission,
                slippage=slippage,
                allow_short=allow_short,
                leverage=leverage,
            )
            oos_result = await asyncio.to_thread(
                engine.run,
                request=oos_request,
                data=oos_data,
                signal_func=oos_signal,
                setup_func=oos_setup,
            )
        except Exception as e:
            errors.append(f"Window {idx + 1} OOS run failed: {e}")
            continue

        is_sharpe = _safe_float(_sharpe(is_result.equity_curve, timeframe_hours))
        oos_sharpe = _safe_float(_sharpe(oos_result.equity_curve, timeframe_hours))

        window = WalkForwardWindow(
            window_index=idx + 1,
            is_start=is_start,
            is_end=is_end,
            oos_start=oos_start,
            oos_end=oos_end,
            is_total_return=_safe_float(is_result.total_return),
            oos_total_return=_safe_float(oos_result.total_return),
            is_sharpe=is_sharpe,
            oos_sharpe=oos_sharpe,
            is_num_trades=is_result.num_trades,
            oos_num_trades=oos_result.num_trades,
            oos_equity_curve=list(oos_result.equity_curve),
        )
        completed_windows.append(window)

        # Track win counts for aggregate win rate
        wins = round(oos_result.win_rate * oos_result.num_trades)
        oos_win_counts.append(wins)
        oos_trade_counts.append(oos_result.num_trades)

    if not completed_windows:
        return WalkForwardResult(
            windows=[],
            num_windows=0,
            is_months=is_months,
            oos_months=oos_months,
            combined_oos_return=0.0,
            combined_oos_sharpe=0.0,
            combined_oos_win_rate=0.0,
            combined_oos_max_drawdown=0.0,
            wfe=0.0,
            combined_oos_equity=[],
            errors=errors or ["All windows failed to complete"],
        )

    agg = _compute_aggregate(
        completed_windows, oos_win_counts, oos_trade_counts, initial_capital, timeframe_hours
    )

    return WalkForwardResult(
        windows=completed_windows,
        num_windows=len(completed_windows),
        is_months=is_months,
        oos_months=oos_months,
        combined_oos_return=agg["combined_oos_return"],
        combined_oos_sharpe=agg["combined_oos_sharpe"],
        combined_oos_win_rate=agg["combined_oos_win_rate"],
        combined_oos_max_drawdown=agg["combined_oos_max_drawdown"],
        wfe=agg["wfe"],
        combined_oos_equity=agg["combined_oos_equity"],
        errors=errors,
    )
