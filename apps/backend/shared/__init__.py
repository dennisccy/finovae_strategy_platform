"""Shared module - contains frozen contracts and schemas."""

from shared.contracts import (
    OHLCV,
    BacktestRequest,
    BacktestResult,
    Condition,
    ConditionOperator,
    EquityPoint,
    IndicatorConfig,
    PositionSizing,
    PositionSizingType,
    RunRecord,
    StrategyCompileRequest,
    StrategyCompileResponse,
    StrategySpec,
    Trade,
    TradeType,
    CompileConstraints,
)

__all__ = [
    "OHLCV",
    "BacktestRequest",
    "BacktestResult",
    "Condition",
    "ConditionOperator",
    "EquityPoint",
    "IndicatorConfig",
    "PositionSizing",
    "PositionSizingType",
    "RunRecord",
    "StrategyCompileRequest",
    "StrategyCompileResponse",
    "StrategySpec",
    "Trade",
    "TradeType",
    "CompileConstraints",
]
