"""
Pydantic Schemas for API Validation

These schemas mirror the contracts but use Pydantic for JSON serialization
and FastAPI integration.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS (Pydantic compatible)
# =============================================================================


class TradeTypeSchema(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ConditionOperatorSchema(str, Enum):
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    CROSS_ABOVE = "cross_above"
    CROSS_BELOW = "cross_below"


class PositionSizingTypeSchema(str, Enum):
    FIXED_AMOUNT = "fixed_amount"
    FIXED_PERCENT = "fixed_percent"
    ALL_IN = "all_in"


# =============================================================================
# DATA SCHEMAS
# =============================================================================


class OHLCVSchema(BaseModel):
    """OHLCV candlestick data schema."""
    timestamp: datetime
    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    timeframe: str = Field(..., pattern=r"^(1m|5m|15m|1h|4h|1d)$")
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    quote_volume: float = Field(..., ge=0)

    @field_validator("high")
    @classmethod
    def high_gte_low(cls, v: float, info) -> float:
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must be >= low")
        return v


# =============================================================================
# STRATEGY SCHEMAS
# =============================================================================


class IndicatorConfigSchema(BaseModel):
    """Indicator configuration schema."""
    name: str
    params: dict[str, int | float]
    output_name: str


class ConditionSchema(BaseModel):
    """Strategy condition schema."""
    left_operand: str
    operator: ConditionOperatorSchema
    right_operand: str | float


class PositionSizingSchema(BaseModel):
    """Position sizing schema."""
    type: PositionSizingTypeSchema
    value: float = Field(..., gt=0)


class StrategySpecSchema(BaseModel):
    """Complete strategy specification schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str
    entry_conditions: list[ConditionSchema] = Field(..., min_length=1)
    exit_conditions: list[ConditionSchema] = Field(..., min_length=1)
    position_size: PositionSizingSchema
    indicators: list[IndicatorConfigSchema]


# =============================================================================
# COMPILATION SCHEMAS
# =============================================================================


class CompileConstraintsSchema(BaseModel):
    """Compilation constraints schema."""
    max_indicators: int = Field(default=10, ge=1, le=20)
    allowed_indicators: list[str] = Field(default_factory=lambda: [
        "sma", "ema", "rsi", "macd", "macd_signal", "macd_hist",
        "bollinger_upper", "bollinger_middle", "bollinger_lower",
        "atr", "adx", "stoch_k", "stoch_d", "cci", "williams_r",
        "obv", "vwap", "mfi", "roc", "momentum"
    ])
    max_conditions: int = Field(default=5, ge=1, le=10)


class StrategyCompileRequestSchema(BaseModel):
    """Strategy compilation request schema."""
    natural_language: str = Field(..., min_length=10, max_length=2000)
    constraints: CompileConstraintsSchema = Field(default_factory=CompileConstraintsSchema)


class StrategyCompileResponseSchema(BaseModel):
    """Strategy compilation response schema."""
    success: bool
    strategy_spec: Optional[StrategySpecSchema] = None
    generated_code: Optional[str] = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# =============================================================================
# BACKTEST SCHEMAS
# =============================================================================


class TradeSchema(BaseModel):
    """Executed trade schema."""
    trade_id: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float = Field(..., gt=0)
    exit_price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    pnl: float
    pnl_percent: float
    commission_paid: float = Field(..., ge=0)


class EquityPointSchema(BaseModel):
    """Equity curve point schema."""
    timestamp: datetime
    equity: float = Field(..., gt=0)
    drawdown: float = Field(..., ge=0, le=1)


class BacktestRequestSchema(BaseModel):
    """Backtest request schema."""
    run_id: str = Field(..., min_length=1)
    strategy_code: str = Field(..., min_length=1)
    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    timeframe: str = Field(..., pattern=r"^(1m|5m|15m|1h|4h|1d)$")
    start_date: date
    end_date: date
    initial_capital: float = Field(default=10000.0, gt=0)
    commission: float = Field(default=0.001, ge=0, le=0.01)
    slippage: float = Field(default=0.0005, ge=0, le=0.01)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class BacktestResultSchema(BaseModel):
    """Backtest result schema."""
    run_id: str
    total_return: float
    max_drawdown: float = Field(..., ge=0, le=1)
    num_trades: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0, le=1)
    sharpe_ratio: float
    profit_factor: float
    equity_curve: list[EquityPointSchema]
    trades: list[TradeSchema]


# =============================================================================
# PERSISTENCE SCHEMAS
# =============================================================================


class RunRecordSchema(BaseModel):
    """Run record schema for persistence."""
    run_id: str
    timestamp: datetime
    request: BacktestRequestSchema
    result: BacktestResultSchema
    strategy_spec: StrategySpecSchema
    natural_language: str


# =============================================================================
# API REQUEST/RESPONSE SCHEMAS
# =============================================================================


class RunBacktestAPIRequest(BaseModel):
    """API request to run a complete backtest from NL."""
    natural_language: str = Field(..., min_length=10, max_length=2000)
    symbol: str = Field(default="BTCUSDT", pattern=r"^[A-Z]+USDT$")
    timeframe: str = Field(default="4h", pattern=r"^(1m|5m|15m|1h|4h|1d)$")
    start_date: date
    end_date: date
    initial_capital: float = Field(default=10000.0, gt=0)


class RunBacktestAPIResponse(BaseModel):
    """API response for backtest run."""
    success: bool
    run_id: Optional[str] = None
    result: Optional[BacktestResultSchema] = None
    strategy_spec: Optional[StrategySpecSchema] = None
    errors: list[str] = Field(default_factory=list)


class RunHistoryResponse(BaseModel):
    """API response for run history."""
    runs: list[RunRecordSchema]
    total_count: int
