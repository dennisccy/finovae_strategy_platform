"""
FROZEN CONTRACTS - v0.1

This file contains the interface contracts for the Finovae Strategy Platform.
DO NOT MODIFY without A0 (Orchestrator) approval.

Frozen Date: 2026-02-11
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


# =============================================================================
# ENUMS
# =============================================================================


class TradeType(str, Enum):
    """Type of trade execution."""
    BUY = "BUY"
    SELL = "SELL"


class ConditionOperator(str, Enum):
    """Operators for strategy conditions."""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    CROSS_ABOVE = "cross_above"
    CROSS_BELOW = "cross_below"


class PositionSizingType(str, Enum):
    """Position sizing method."""
    FIXED_AMOUNT = "fixed_amount"       # Fixed USDT amount per trade
    FIXED_PERCENT = "fixed_percent"     # Percentage of equity
    ALL_IN = "all_in"                   # Use all available capital


# =============================================================================
# DATA CONTRACTS
# =============================================================================


@dataclass(frozen=True)
class OHLCV:
    """
    Single candlestick data point from Binance spot market.

    Attributes:
        timestamp: Candle open time (UTC)
        symbol: Trading pair (e.g., "BTCUSDT")
        timeframe: Candle interval (e.g., "1h", "4h", "1d")
        open: Opening price in quote currency (USDT)
        high: Highest price during the period
        low: Lowest price during the period
        close: Closing price
        volume: Volume in base currency
        quote_volume: Volume in quote currency (USDT)
    """
    timestamp: datetime
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float


# =============================================================================
# STRATEGY CONTRACTS
# =============================================================================


@dataclass
class IndicatorConfig:
    """
    Configuration for a technical indicator.

    Attributes:
        name: Indicator name (must be in whitelist)
        params: Indicator parameters (e.g., {"period": 14})
        output_name: Name to reference this indicator's output
    """
    name: str
    params: dict[str, int | float]
    output_name: str


@dataclass
class Condition:
    """
    A single condition for entry/exit logic.

    Attributes:
        left_operand: Left side of comparison (indicator name or "price")
        operator: Comparison operator
        right_operand: Right side (indicator name, "price", or numeric value)
    """
    left_operand: str
    operator: ConditionOperator
    right_operand: str | float


@dataclass
class PositionSizing:
    """
    Position sizing configuration.

    Attributes:
        type: Sizing method
        value: Amount or percentage based on type
    """
    type: PositionSizingType
    value: float


@dataclass
class StrategySpec:
    """
    Complete strategy specification compiled from natural language.

    Attributes:
        name: Strategy name
        description: Human-readable description
        entry_conditions: List of conditions that must ALL be true to enter
        exit_conditions: List of conditions where ANY being true triggers exit
        position_size: How to size positions
        indicators: Required indicator configurations
    """
    name: str
    description: str
    entry_conditions: list[Condition]
    exit_conditions: list[Condition]
    position_size: PositionSizing
    indicators: list[IndicatorConfig]


# =============================================================================
# COMPILATION CONTRACTS
# =============================================================================


@dataclass
class CompileConstraints:
    """
    Constraints for strategy compilation.

    Attributes:
        max_indicators: Maximum number of indicators allowed
        allowed_indicators: Whitelist of indicator names
        max_conditions: Maximum conditions per entry/exit
    """
    max_indicators: int = 10
    allowed_indicators: list[str] = field(default_factory=lambda: [
        "sma", "ema", "rsi", "macd", "macd_signal", "macd_hist",
        "bollinger_upper", "bollinger_middle", "bollinger_lower",
        "atr", "adx", "stoch_k", "stoch_d", "cci", "williams_r",
        "obv", "vwap", "mfi", "roc", "momentum"
    ])
    max_conditions: int = 5


@dataclass
class StrategyCompileRequest:
    """
    Request to compile natural language into a strategy.

    Attributes:
        natural_language: User's strategy description in plain English
        constraints: Compilation constraints
    """
    natural_language: str
    constraints: CompileConstraints = field(default_factory=CompileConstraints)


@dataclass
class StrategyCompileResponse:
    """
    Response from strategy compilation.

    Attributes:
        success: Whether compilation succeeded
        strategy_spec: Compiled strategy specification (if success)
        generated_code: Python code for the strategy (if success)
        errors: List of error messages (if failure)
        warnings: Non-fatal warnings about the strategy
    """
    success: bool
    strategy_spec: Optional[StrategySpec] = None
    generated_code: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# BACKTEST CONTRACTS
# =============================================================================


@dataclass(frozen=True)
class Trade:
    """
    A single executed trade.

    Attributes:
        trade_id: Unique trade identifier
        entry_time: Entry timestamp
        exit_time: Exit timestamp
        entry_price: Entry price in USDT
        exit_price: Exit price in USDT
        quantity: Position size in base currency
        pnl: Profit/loss in USDT
        pnl_percent: Profit/loss as percentage
        commission_paid: Total commission for entry + exit
        direction: Trade direction ("long" or "short") — v0.7 additive
        leverage: Leverage multiplier applied — v0.7 additive
    """
    trade_id: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    commission_paid: float
    direction: str = "long"   # "long" | "short"
    leverage: float = 1.0
    margin: float = 0.0   # cash collateral posted (= notional / leverage); v0.8 additive


@dataclass(frozen=True)
class EquityPoint:
    """
    Single point on the equity curve.

    Attributes:
        timestamp: Time of this equity snapshot
        equity: Total equity value in USDT
        drawdown: Current drawdown from peak (as decimal, e.g., 0.05 = 5%)
    """
    timestamp: datetime
    equity: float
    drawdown: float


@dataclass
class BacktestRequest:
    """
    Request to run a backtest.

    Attributes:
        run_id: Unique identifier for this run
        strategy_code: Python code to execute (sandboxed)
        symbol: Trading pair (e.g., "BTCUSDT")
        timeframe: Candle interval (e.g., "1h", "4h")
        start_date: Backtest start date
        end_date: Backtest end date
        initial_capital: Starting capital in USDT
        commission: Commission rate (default 0.00075 = 0.075%, Binance BNB taker discount)
        slippage: Slippage rate (default 0.0005 = 0.05%)
        allow_short: Allow short positions — v0.7 additive
        leverage: Leverage multiplier (1x–10x); strategy attr overrides if set — v0.7 additive
    """
    run_id: str
    strategy_code: str
    symbol: str
    timeframe: str
    start_date: date
    end_date: date
    initial_capital: float = 10000.0
    commission: float = 0.00075
    slippage: float = 0.0005
    allow_short: bool = False
    leverage: float = 1.0
    max_order_size_pct: Optional[float] = None   # v0.9 additive — fraction of cash per trade
    max_daily_loss_pct: Optional[float] = None   # v0.9 additive — fraction of initial_capital as daily loss limit


@dataclass
class BacktestResult:
    """
    Result from a backtest run.

    Attributes:
        run_id: Unique run identifier
        total_return: Total return as decimal (e.g., 0.15 = 15%)
        max_drawdown: Maximum drawdown as decimal
        num_trades: Total number of completed trades
        win_rate: Winning trades / total trades
        sharpe_ratio: Risk-adjusted return metric
        profit_factor: Gross profit / gross loss
        equity_curve: Time series of equity values
        trades: List of all executed trades
    """
    run_id: str
    total_return: float
    max_drawdown: float
    num_trades: int
    win_rate: float
    sharpe_ratio: float
    profit_factor: float
    equity_curve: list[EquityPoint]
    trades: list[Trade]
    margin_called: bool = False                    # v0.8 additive
    unleveraged_return: Optional[float] = None     # v0.8 additive; None when leverage == 1


# =============================================================================
# PERSISTENCE CONTRACTS
# =============================================================================


@dataclass
class RunRecord:
    """
    Complete record of a backtest run for persistence.

    Attributes:
        run_id: Unique run identifier
        timestamp: When the run was executed
        request: Original backtest request
        result: Backtest results
        strategy_spec: Strategy specification used (None for script-based runs)
        natural_language: Original NL input from user
    """
    run_id: str
    timestamp: datetime
    request: BacktestRequest
    result: BacktestResult
    strategy_spec: Optional[StrategySpec]
    natural_language: str


# =============================================================================
# AI SCRIPT PROXY CONTRACTS (v0.2 additive)
# =============================================================================


@dataclass
class GenerateStrategyResult:
    """
    Result from AI script generation.

    Attributes:
        script_id: Unique identifier for the generated script
        script_code: Python source code of the Strategy class
        strategy_name: Name extracted from the Strategy class
        strategy_description: Description extracted from the Strategy class
        validation_errors: Sandbox validation errors (empty if valid)
    """
    script_id: str
    script_code: str
    strategy_name: str
    strategy_description: str
    validation_errors: list[str] = field(default_factory=list)
    model_used: str = ""  # v0.5 additive: actual model used for generation


@dataclass
class StoredScript:
    """
    In-memory stored script with metadata.

    Attributes:
        script_id: Unique identifier
        script_code: Python source code
        strategy_name: Strategy name
        strategy_description: Strategy description
        natural_language: Original NL input
        created_at: When the script was generated
        model: Claude model used for generation
    """
    script_id: str
    script_code: str
    strategy_name: str
    strategy_description: str
    natural_language: str
    created_at: datetime
    model: str


# =============================================================================
# STRATEGY RATING CONTRACTS (v0.3 additive)
# =============================================================================


@dataclass
class DrawdownPeriod:
    """A single drawdown period with recovery info."""
    start_time: datetime
    end_time: datetime
    recovery_time: Optional[datetime]  # None if not recovered
    depth: float  # max drawdown depth as decimal (e.g. 0.15 = 15%)
    duration_days: float  # days from start to trough
    recovery_days: Optional[float]  # days from trough to recovery (None if not recovered)


@dataclass
class TradeExcursion:
    """MAE/MFE excursion data for a single trade."""
    trade_id: str
    pnl_percent: float
    mae: float  # max adverse excursion as positive decimal
    mfe: float  # max favorable excursion as positive decimal


@dataclass
class MonthlyReturn:
    """Monthly return data for heatmap."""
    year: int
    month: int
    return_pct: float  # as decimal (0.05 = 5%)


@dataclass
class RollingMetric:
    """A single point in a rolling metric time series."""
    timestamp: datetime
    value: float


@dataclass
class HistogramBin:
    """A single bin in a return distribution histogram."""
    bin_start: float
    bin_end: float
    count: int


@dataclass
class SimulatedStopLevel:
    """Impact of a simulated stop-loss or take-profit level."""
    level_pct: float  # stop/TP level as percentage
    adjusted_return: float  # total return with this stop/TP
    adjusted_win_rate: float
    trades_affected: int


@dataclass
class CapacityLevel:
    """Estimated performance at a given capital level."""
    capital: float
    volume_participation_pct: float
    estimated_slippage_bps: float  # basis points


@dataclass
class CategoryRating:
    """Rating for a single category (1-5 stars)."""
    name: str  # e.g. "profitability"
    label: str  # e.g. "Profitability"
    stars: int  # 1-5
    key_metrics: dict[str, float | str]  # metric_name -> value
    analyses: dict  # category-specific analysis data


@dataclass
class StrategyRating:
    """Complete 5-category strategy rating."""
    profitability: CategoryRating
    risk_resistance: CategoryRating
    risk_reward: CategoryRating
    win_rate_ev: CategoryRating
    liquidity: CategoryRating
    # Shared analysis data
    benchmark_equity: list[EquityPoint]
    benchmark_total_return: float
    monthly_returns: list[MonthlyReturn]
    trade_excursions: list[TradeExcursion]
    drawdown_periods: list[DrawdownPeriod]
    rolling_sharpe: list[RollingMetric]
    rolling_sharpe_benchmark: list[RollingMetric]
    return_distribution: list[HistogramBin]
    simulated_stops: list[SimulatedStopLevel]
    simulated_take_profits: list[SimulatedStopLevel]
    capacity_levels: list[CapacityLevel]
    annual_returns: dict[int, float]
    benchmark_annual_returns: dict[int, float]
    annual_long_returns: dict[int, float]
    annual_short_returns: dict[int, float]


# =============================================================================
# WALK-FORWARD VALIDATION CONTRACTS (v0.10 additive)
# =============================================================================


@dataclass
class WalkForwardWindow:
    """A single IS+OOS window in a walk-forward validation run."""
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
    oos_equity_curve: list[EquityPoint]


@dataclass
class WalkForwardResult:
    """Results of a walk-forward validation run."""
    windows: list[WalkForwardWindow]
    num_windows: int
    is_months: int
    oos_months: int
    combined_oos_return: float
    combined_oos_sharpe: float
    combined_oos_win_rate: float
    combined_oos_max_drawdown: float
    wfe: float  # Walk-Forward Efficiency: mean(OOS Sharpe) / mean(IS Sharpe); healthy > 0.5
    combined_oos_equity: list[EquityPoint]  # compounded across all OOS windows
    errors: list[str]
