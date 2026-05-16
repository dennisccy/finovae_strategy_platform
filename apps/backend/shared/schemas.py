"""
Pydantic Schemas for API Validation

These schemas mirror the contracts but use Pydantic for JSON serialization
and FastAPI integration.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from shared.model_catalog import DEFAULT_MODEL, HAIKU_MODEL, SONNET_MODEL


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
    symbol: str = Field(..., pattern=r"^[A-Z]+/USDT$")
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
    direction: str = "long"   # "long" | "short" — v0.7 additive
    leverage: float = 1.0     # leverage multiplier — v0.7 additive
    margin: float = 0.0       # cash collateral posted — v0.8 additive


class EquityPointSchema(BaseModel):
    """Equity curve point schema."""
    timestamp: datetime
    equity: float = Field(..., ge=0)  # ge=0 to allow margin-called equity of 0
    drawdown: float = Field(..., ge=0, le=1)


class BacktestRequestSchema(BaseModel):
    """Backtest request schema."""
    run_id: str = Field(..., min_length=1)
    strategy_code: str = Field(..., min_length=1)
    symbol: str = Field(..., pattern=r"^[A-Z]+/USDT$")
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
    margin_called: bool = False                    # v0.8 additive
    unleveraged_return: Optional[float] = None     # v0.8 additive; None when leverage == 1


# =============================================================================
# PERSISTENCE SCHEMAS
# =============================================================================


class RunRecordSchema(BaseModel):
    """Run record schema for persistence."""
    run_id: str
    timestamp: datetime
    request: BacktestRequestSchema
    result: BacktestResultSchema
    strategy_spec: Optional[StrategySpecSchema] = None
    natural_language: str


# =============================================================================
# API REQUEST/RESPONSE SCHEMAS
# =============================================================================


class RunBacktestAPIRequest(BaseModel):
    """API request to run a complete backtest from NL."""
    natural_language: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural language strategy description",
        examples=["Buy when RSI crosses below 30, sell when it crosses above 70"],
    )
    symbol: str = Field(
        default="BTC/USDT",
        pattern=r"^[A-Z]+/USDT$",
        description="Trading symbol (USDT pairs)",
        examples=["BTC/USDT", "ETH/USDT"],
    )
    timeframe: str = Field(
        default="4h",
        pattern=r"^(1m|5m|15m|1h|4h|1d)$",
        description="Candle timeframe interval",
        examples=["1h", "4h", "1d"],
    )
    start_date: date = Field(
        ...,
        description="Backtest start date",
        examples=["2024-01-01"],
    )
    end_date: date = Field(
        ...,
        description="Backtest end date",
        examples=["2024-06-01"],
    )
    initial_capital: float = Field(
        default=10000.0,
        gt=0,
        description="Starting capital in USDT",
        examples=[10000.0],
    )
    model: str = Field(
        default=DEFAULT_MODEL,
        pattern=r"^(claude-|gpt-)",
        description="Claude or OpenAI model to use for strategy compilation",
        examples=[DEFAULT_MODEL, SONNET_MODEL, HAIKU_MODEL],
    )


class RunBacktestAPIResponse(BaseModel):
    """API response for backtest run."""
    success: bool
    run_id: Optional[str] = None
    result: Optional[BacktestResultSchema] = None
    rating: Optional["StrategyRatingSchema"] = None
    strategy_spec: Optional[StrategySpecSchema] = None
    errors: list[str] = Field(default_factory=list)


class RunHistoryResponse(BaseModel):
    """API response for run history."""
    runs: list[RunRecordSchema]
    total_count: int


# =============================================================================
# AI SCRIPT PROXY SCHEMAS
# =============================================================================


class GenerateStrategyRequest(BaseModel):
    """API request to generate a strategy script from NL."""
    natural_language: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Natural language strategy description",
    )
    model: str = Field(
        default=DEFAULT_MODEL,
        pattern=r"^(claude-|gpt-)",
        description="Claude or OpenAI model to use for script generation",
    )
    previous_script_code: Optional[str] = Field(
        default=None,
        description="Previous script code for iterative refinement",
    )
    symbol: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Z]+/USDT$",
        description="Trading symbol for market context (e.g. PEPE/USDT)",
    )
    timeframe: Optional[str] = Field(
        default=None,
        description="Candle timeframe for calibrating indicator periods",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Backtest start date (YYYY-MM-DD)",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Backtest end date (YYYY-MM-DD)",
    )
    previous_backtest_metrics: Optional[dict] = Field(
        default=None,
        description="Metrics from previous backtest for iterative improvement",
    )
    allow_short: bool = Field(default=False, description="Allow short positions — v0.7.1")
    leverage: float = Field(default=1.0, ge=1.0, le=10.0, description="Leverage — v0.7.1")


class GenerateStrategyResponse(BaseModel):
    """API response for strategy script generation."""
    success: bool
    script_id: Optional[str] = None
    script_code: Optional[str] = None
    strategy_name: Optional[str] = None
    strategy_description: Optional[str] = None
    model_used: Optional[str] = None
    validation_errors: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExecuteBacktestRequest(BaseModel):
    """API request to execute a backtest from a generated/edited script."""
    script_id: str = Field(
        ...,
        min_length=1,
        description="ID of the previously generated script",
    )
    script_code: Optional[str] = Field(
        default=None,
        description="Edited script code (if user modified it). If None, uses stored script.",
    )
    strategy_name: Optional[str] = Field(
        default=None,
        description="Override strategy name if restoring an edited/cached script",
    )
    strategy_description: Optional[str] = Field(
        default=None,
        description="Override strategy description if restoring an edited/cached script",
    )
    job_id: Optional[str] = Field(
        default=None,
        description="Client-generated job ID for real-time status polling",
    )
    symbol: str = Field(
        default="BTC/USDT",
        pattern=r"^[A-Z]+/USDT$",
    )
    timeframe: str = Field(
        default="4h",
        pattern=r"^(1m|5m|15m|1h|4h|1d)$",
    )
    start_date: date = Field(
        ...,
        description="Backtest start date",
    )
    end_date: date = Field(
        ...,
        description="Backtest end date",
    )
    initial_capital: float = Field(
        default=10000.0,
        gt=0,
    )
    commission: float = Field(
        default=0.001,
        ge=0,
        le=0.01,
        description="Commission rate per trade (0.001 = 0.1%). Reflects exchange fee.",
    )
    allow_short: bool = Field(
        default=False,
        description="Allow short positions — v0.7 additive",
    )
    leverage: float = Field(
        default=1.0,
        ge=1.0,
        le=10.0,
        description="Leverage multiplier (1x–10x); strategy attr overrides if set — v0.7 additive",
    )
    exchange: Optional[str] = Field(
        default=None,
        description="Exchange identifier — used to build directions cache key when direction_id is set",
    )
    direction_id: Optional[str] = Field(
        default=None,
        description="Direction card ID (e.g. 'strategy-0'). When set, result is saved to directions cache.",
    )
    direction_index: Optional[int] = Field(
        default=None,
        description="Direction card index (0-based) for cache directory naming.",
    )
    direction_prompt: Optional[str] = Field(
        default=None,
        description="Original prompt text for this direction — saved to cache.",
    )
    max_order_size_pct: Optional[float] = Field(
        default=None,
        ge=0.01,
        le=1.0,
        description="Max order size as fraction of current cash per trade — v0.9 additive",
    )
    max_daily_loss_pct: Optional[float] = Field(
        default=None,
        ge=0.001,
        le=1.0,
        description="Daily loss circuit breaker as fraction of initial_capital — v0.9 additive",
    )
    wfv_enabled: bool = Field(default=False, description="Run walk-forward validation as phase 5")
    wfv_is_months: int = Field(default=6, ge=1, le=60, description="In-sample window months")
    wfv_oos_months: int = Field(default=3, ge=1, le=60, description="Out-of-sample window months")
    wfv_max_windows: Optional[int] = Field(default=None, ge=1, le=100, description="Max WFV windows")

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class PhaseTimings(BaseModel):
    """Backend phase timing measurements in milliseconds."""
    validate_ms: float = 0
    fetch_ms: float = 0
    simulate_ms: float = 0
    calculate_ms: float = 0
    calculate_steps: Optional[dict[str, float]] = None
    walk_forward_ms: Optional[float] = None
    total_ms: float = 0


class JobStatusResponse(BaseModel):
    """Real-time job status for polling endpoint."""
    job_id: str
    phase: str
    validate_step: Optional[str] = None
    calculate_step: Optional[str] = None
    calculate_step_index: int = 0
    sim_bar: int = 0
    sim_total_bars: int = 0
    error_message: Optional[str] = None


class ExecuteBacktestResponse(BaseModel):
    """API response for backtest execution."""
    success: bool
    run_id: Optional[str] = None
    result: Optional[BacktestResultSchema] = None
    rating: Optional["StrategyRatingSchema"] = None
    timings: Optional[PhaseTimings] = None
    script_code: Optional[str] = None
    strategy_name: Optional[str] = None
    strategy_description: Optional[str] = None
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# STRATEGY RATING SCHEMAS (v0.3 additive)
# =============================================================================


class DrawdownPeriodSchema(BaseModel):
    start_time: datetime
    end_time: datetime
    recovery_time: Optional[datetime] = None
    depth: float
    duration_days: float
    recovery_days: Optional[float] = None


class TradeExcursionSchema(BaseModel):
    trade_id: str
    pnl_percent: float
    mae: float
    mfe: float


class MonthlyReturnSchema(BaseModel):
    year: int
    month: int
    return_pct: float


class RollingMetricSchema(BaseModel):
    timestamp: datetime
    value: float


class HistogramBinSchema(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class SimulatedStopLevelSchema(BaseModel):
    level_pct: float
    adjusted_return: float
    adjusted_win_rate: float
    trades_affected: int


class CapacityLevelSchema(BaseModel):
    capital: float
    volume_participation_pct: float
    estimated_slippage_bps: float


class CategoryRatingSchema(BaseModel):
    name: str
    label: str
    stars: int = Field(..., ge=1, le=5)
    key_metrics: dict[str, float | str]
    analyses: dict


class StrategyRatingSchema(BaseModel):
    profitability: CategoryRatingSchema
    risk_resistance: CategoryRatingSchema
    risk_reward: CategoryRatingSchema
    win_rate_ev: CategoryRatingSchema
    liquidity: CategoryRatingSchema
    benchmark_equity: list[EquityPointSchema]
    benchmark_total_return: float
    monthly_returns: list[MonthlyReturnSchema]
    trade_excursions: list[TradeExcursionSchema]
    drawdown_periods: list[DrawdownPeriodSchema]
    rolling_sharpe: list[RollingMetricSchema]
    rolling_sharpe_benchmark: list[RollingMetricSchema]
    return_distribution: list[HistogramBinSchema]
    simulated_stops: list[SimulatedStopLevelSchema]
    simulated_take_profits: list[SimulatedStopLevelSchema]
    capacity_levels: list[CapacityLevelSchema]
    annual_returns: dict[int, float]
    benchmark_annual_returns: dict[int, float]
    annual_long_returns: dict[int, float]
    annual_short_returns: dict[int, float]


# =============================================================================
# STRATEGY INSIGHTS SCHEMAS (v0.4 additive)
# =============================================================================


class InsightsSuggestion(BaseModel):
    """A single AI-generated improvement suggestion."""
    title: str
    description: str
    prompt: str


class GenerateInsightsRequest(BaseModel):
    """API request to generate strategy insights from backtest results."""
    backtest_result: BacktestResultSchema
    strategy_name: str = ""
    strategy_description: str = ""
    script_code: str = ""
    natural_language_prompt: str = ""
    model: str = Field(
        default=DEFAULT_MODEL,
        pattern=r"^(claude-|gpt-)",
        description="Claude or OpenAI model to use for insights generation",
    )
    symbol: Optional[str] = Field(
        default=None,
        description="Trading symbol for market context (e.g. PEPE/USDT)",
    )
    timeframe: Optional[str] = Field(
        default=None,
        description="Candle timeframe for context",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Backtest start date (YYYY-MM-DD)",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Backtest end date (YYYY-MM-DD)",
    )
    allow_short: bool = Field(default=False, description="Allow short positions — v0.7.1")
    leverage: float = Field(default=1.0, ge=1.0, le=10.0, description="Leverage — v0.7.1")
    initial_capital: Optional[float] = Field(default=None, description="Initial capital in USDT")
    previous_summary: Optional[str] = Field(default=None, description="Summary from previous iteration for context")
    previous_suggestions: Optional[List[str]] = Field(
        default=None,
        description="Titles of previously tried suggestions to avoid repeating"
    )
    walk_forward_result: Optional[dict] = Field(
        default=None,
        description="Walk-forward validation summary for OOS context (v0.10)",
    )


class GenerateInsightsResponse(BaseModel):
    """API response for strategy insights generation."""
    success: bool
    summary: Optional[str] = None
    suggestions: list[InsightsSuggestion] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# WALK-FORWARD VALIDATION SCHEMAS (v0.10 additive)
# =============================================================================


class WalkForwardWindowSchema(BaseModel):
    window_index: int
    is_start: date
    is_end: date
    oos_start: date
    oos_end: date
    is_total_return: float
    oos_total_return: float
    is_sharpe: float
    oos_sharpe: float
    is_num_trades: int
    oos_num_trades: int
    oos_equity_curve: list[EquityPointSchema]


class WalkForwardResultSchema(BaseModel):
    windows: list[WalkForwardWindowSchema]
    num_windows: int
    is_months: int
    oos_months: int
    combined_oos_return: float
    combined_oos_sharpe: float
    combined_oos_win_rate: float
    combined_oos_max_drawdown: float = Field(..., ge=0)
    wfe: float
    combined_oos_equity: list[EquityPointSchema]
    errors: list[str] = Field(default_factory=list)


class ExecuteWalkForwardRequest(BaseModel):
    script_id: str = Field(..., min_length=1)
    script_code: Optional[str] = Field(default=None)
    strategy_name: Optional[str] = Field(default=None)
    strategy_description: Optional[str] = Field(default=None)
    symbol: str = Field(default="BTC/USDT", pattern=r"^[A-Z]+/USDT$")
    timeframe: str = Field(default="4h", pattern=r"^(1m|5m|15m|1h|4h|1d)$")
    start_date: date = Field(...)
    end_date: date = Field(...)
    initial_capital: float = Field(default=10000.0, gt=0)
    commission: float = Field(default=0.001, ge=0, le=0.01)
    allow_short: bool = Field(default=False)
    leverage: float = Field(default=1.0, ge=1.0, le=10.0)
    is_months: int = Field(default=6, ge=1, le=60)
    oos_months: int = Field(default=3, ge=1, le=60)
    max_windows: Optional[int] = Field(default=None, ge=1, le=100)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class ExecuteWalkForwardResponse(BaseModel):
    success: bool
    result: Optional[WalkForwardResultSchema] = None
    errors: list[str] = Field(default_factory=list)


# Rebuild models that use forward references
RunBacktestAPIResponse.model_rebuild()
ExecuteBacktestResponse.model_rebuild()
