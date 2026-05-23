"""Canonical serialization of backtest dataclasses → API/store JSON shapes.

This is the SINGLE source of truth for turning the frozen ``BacktestResult`` /
``StrategyRating`` / ``WalkForwardResult`` dataclasses into the JSON shapes the
UI renders.  It was extracted verbatim from ``backend.api`` so that:

* ``backend.api`` (the manual ``POST /api/execute-backtest`` SSE path) and
* ``backend.auto_session`` (the headless auto-session loop)

produce **byte-shape-identical** ``result`` / ``rating`` / ``walk_forward``
payloads.  A headless run must be indistinguishable in the UI from a manual one
(goal anti-goal: "the automated chain MUST write the same session / iteration /
activity / insights artifacts the UI renders — no parallel store, no schema
fork").  Keeping one serializer is how that guarantee is enforced rather than
re-implemented (and risking drift).

The ``*_schema`` functions return Pydantic schema objects (used by
``backend.api`` response models, unchanged behavior).  The ``*_to_dict``
wrappers return plain JSON-able dicts (used by ``backend.auto_session`` to write
``result.json`` / ``rating.json`` / the iteration node through
``backend.session_store``).
"""

import math
from typing import Optional

from fastapi.encoders import jsonable_encoder

from shared.contracts import BacktestResult, StrategyRating, WalkForwardResult
from shared.schemas import (
    BacktestResultSchema,
    CapacityLevelSchema,
    CategoryRatingSchema,
    DrawdownPeriodSchema,
    EquityPointSchema,
    HistogramBinSchema,
    MonthlyReturnSchema,
    RollingMetricSchema,
    SimulatedStopLevelSchema,
    StrategyRatingSchema,
    TradeExcursionSchema,
    TradeSchema,
    WalkForwardResultSchema,
    WalkForwardWindowSchema,
)


def safe_float(v: float) -> float:
    """Replace inf/nan with JSON-safe sentinel values."""
    if math.isinf(v) or math.isnan(v):
        return 9999.99 if v > 0 else -9999.99
    return v


def equity_point(ep) -> EquityPointSchema:
    """Serialize an equity point, clamping values to schema-valid ranges.

    With leverage/shorts the account can go negative (equity < 0) or drawdown
    can slightly exceed 1.0 due to floating-point arithmetic.  We clamp rather
    than reject so the UI can still render the full curve.
    """
    return EquityPointSchema(
        timestamp=ep.timestamp,
        equity=max(1e-6, float(ep.equity)),    # floor at near-zero; schema requires gt=0
        drawdown=min(1.0, float(ep.drawdown)),  # cap at 100%; schema requires le=1
    )


def serialize_backtest_result(result: BacktestResult) -> BacktestResultSchema:
    """Convert a ``BacktestResult`` dataclass to its Pydantic schema.

    Mirrors the ``POST /api/execute-backtest`` serialization (the canonical
    manual path the headless loop reuses) — including the v0.7/v0.8 additive
    per-trade ``direction`` / ``leverage`` / ``margin`` fields.
    """
    return BacktestResultSchema(
        run_id=result.run_id,
        total_return=result.total_return,
        max_drawdown=min(1.0, float(result.max_drawdown)),
        num_trades=result.num_trades,
        win_rate=result.win_rate,
        sharpe_ratio=safe_float(result.sharpe_ratio),
        profit_factor=safe_float(result.profit_factor),
        equity_curve=[equity_point(ep) for ep in result.equity_curve],
        trades=[
            TradeSchema(
                trade_id=t.trade_id,
                entry_time=t.entry_time,
                exit_time=t.exit_time,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                quantity=t.quantity,
                pnl=t.pnl,
                pnl_percent=t.pnl_percent,
                commission_paid=t.commission_paid,
                direction=t.direction,
                leverage=t.leverage,
                margin=getattr(t, "margin", 0.0),
            )
            for t in result.trades
        ],
        margin_called=getattr(result, "margin_called", False),
        unleveraged_return=getattr(result, "unleveraged_return", None),
    )


def serialize_rating(rating: Optional[StrategyRating]) -> Optional[StrategyRatingSchema]:
    """Convert ``StrategyRating`` dataclass to Pydantic schema."""
    if rating is None:
        return None

    def _safe_metrics(metrics: dict) -> dict:
        return {
            k: (safe_float(v) if isinstance(v, float) else v)
            for k, v in metrics.items()
        }

    def _cat(c):
        return CategoryRatingSchema(
            name=c.name,
            label=c.label,
            stars=c.stars,
            key_metrics=_safe_metrics(c.key_metrics),
            analyses=c.analyses,
        )

    return StrategyRatingSchema(
        profitability=_cat(rating.profitability),
        risk_resistance=_cat(rating.risk_resistance),
        risk_reward=_cat(rating.risk_reward),
        win_rate_ev=_cat(rating.win_rate_ev),
        liquidity=_cat(rating.liquidity),
        benchmark_equity=[equity_point(ep) for ep in rating.benchmark_equity],
        benchmark_total_return=rating.benchmark_total_return,
        monthly_returns=[
            MonthlyReturnSchema(year=m.year, month=m.month, return_pct=m.return_pct)
            for m in rating.monthly_returns
        ],
        trade_excursions=[
            TradeExcursionSchema(
                trade_id=te.trade_id, pnl_percent=te.pnl_percent, mae=te.mae, mfe=te.mfe)
            for te in rating.trade_excursions
        ],
        drawdown_periods=[
            DrawdownPeriodSchema(
                start_time=dp.start_time, end_time=dp.end_time,
                recovery_time=dp.recovery_time, depth=dp.depth,
                duration_days=dp.duration_days, recovery_days=dp.recovery_days,
            )
            for dp in rating.drawdown_periods
        ],
        rolling_sharpe=[
            RollingMetricSchema(timestamp=rm.timestamp, value=rm.value)
            for rm in rating.rolling_sharpe
        ],
        rolling_sharpe_benchmark=[
            RollingMetricSchema(timestamp=rm.timestamp, value=rm.value)
            for rm in rating.rolling_sharpe_benchmark
        ],
        return_distribution=[
            HistogramBinSchema(bin_start=b.bin_start, bin_end=b.bin_end, count=b.count)
            for b in rating.return_distribution
        ],
        simulated_stops=[
            SimulatedStopLevelSchema(
                level_pct=s.level_pct, adjusted_return=s.adjusted_return,
                adjusted_win_rate=s.adjusted_win_rate, trades_affected=s.trades_affected,
            )
            for s in rating.simulated_stops
        ],
        simulated_take_profits=[
            SimulatedStopLevelSchema(
                level_pct=s.level_pct, adjusted_return=s.adjusted_return,
                adjusted_win_rate=s.adjusted_win_rate, trades_affected=s.trades_affected,
            )
            for s in rating.simulated_take_profits
        ],
        capacity_levels=[
            CapacityLevelSchema(
                capital=cl.capital,
                volume_participation_pct=cl.volume_participation_pct,
                estimated_slippage_bps=cl.estimated_slippage_bps,
            )
            for cl in rating.capacity_levels
        ],
        annual_returns=rating.annual_returns,
        benchmark_annual_returns=rating.benchmark_annual_returns,
        annual_long_returns=rating.annual_long_returns,
        annual_short_returns=rating.annual_short_returns,
    )


def serialize_walk_forward(
    result: Optional[WalkForwardResult],
) -> Optional[WalkForwardResultSchema]:
    """Convert ``WalkForwardResult`` dataclass to Pydantic schema."""
    if result is None:
        return None
    return WalkForwardResultSchema(
        windows=[
            WalkForwardWindowSchema(
                window_index=w.window_index,
                is_start=w.is_start,
                is_end=w.is_end,
                oos_start=w.oos_start,
                oos_end=w.oos_end,
                is_total_return=safe_float(w.is_total_return),
                oos_total_return=safe_float(w.oos_total_return),
                is_sharpe=safe_float(w.is_sharpe),
                oos_sharpe=safe_float(w.oos_sharpe),
                is_num_trades=w.is_num_trades,
                oos_num_trades=w.oos_num_trades,
                oos_equity_curve=[equity_point(ep) for ep in w.oos_equity_curve],
            )
            for w in result.windows
        ],
        num_windows=result.num_windows,
        is_months=result.is_months,
        oos_months=result.oos_months,
        combined_oos_return=safe_float(result.combined_oos_return),
        combined_oos_sharpe=safe_float(result.combined_oos_sharpe),
        combined_oos_win_rate=float(result.combined_oos_win_rate),
        combined_oos_max_drawdown=min(1.0, float(result.combined_oos_max_drawdown)),
        wfe=safe_float(result.wfe),
        combined_oos_equity=[equity_point(ep) for ep in result.combined_oos_equity],
        errors=result.errors,
    )


# ---------------------------------------------------------------------------
# Plain-dict wrappers (for the file store / headless loop)
# ---------------------------------------------------------------------------

def result_to_dict(result: Optional[BacktestResult]) -> Optional[dict]:
    """JSON-able dict for a ``BacktestResult`` (identical to the SSE payload)."""
    if result is None:
        return None
    return jsonable_encoder(serialize_backtest_result(result))


def rating_to_dict(rating: Optional[StrategyRating]) -> Optional[dict]:
    """JSON-able dict for a ``StrategyRating`` (identical to the SSE payload)."""
    if rating is None:
        return None
    return jsonable_encoder(serialize_rating(rating))


def walk_forward_to_dict(result: Optional[WalkForwardResult]) -> Optional[dict]:
    """JSON-able dict for a ``WalkForwardResult`` (identical to the SSE payload)."""
    if result is None:
        return None
    return jsonable_encoder(serialize_walk_forward(result))
