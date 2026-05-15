"""
Strategy Code Generator

Generates executable Python code from StrategySpec.
The generated code is designed to run in the RestrictedPython sandbox.
"""

from textwrap import dedent, indent

from shared.contracts import (
    Condition,
    ConditionOperator,
    IndicatorConfig,
    StrategySpec,
)


class CodeGeneratorError(Exception):
    """Exception raised for code generation errors."""
    pass


class CodeGenerator:
    """
    Generates sandbox-safe Python code from StrategySpec.

    The generated code defines a `signal` function that takes a DataFrame
    and bar index, and returns a trading signal (-1, 0, or 1).
    """

    # Code template for generated strategies
    TEMPLATE = '''"""
Strategy: {name}
{description}

Auto-generated code - DO NOT EDIT
"""

import numpy as np
import pandas as pd

# Indicator computation functions (subset of allowed indicators)
def calc_sma(series, period):
    return series.rolling(window=period).mean()

def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series, period):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_macd(series, fast, slow):
    fast_ema = series.ewm(span=fast, adjust=False).mean()
    slow_ema = series.ewm(span=slow, adjust=False).mean()
    return fast_ema - slow_ema

def calc_macd_signal(series, fast, slow, signal):
    macd = calc_macd(series, fast, slow)
    return macd.ewm(span=signal, adjust=False).mean()

def calc_macd_hist(series, fast, slow, signal):
    macd = calc_macd(series, fast, slow)
    macd_sig = calc_macd_signal(series, fast, slow, signal)
    return macd - macd_sig

def calc_bollinger_upper(series, period, std_dev):
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return middle + (std * std_dev)

def calc_bollinger_middle(series, period):
    return series.rolling(window=period).mean()

def calc_bollinger_lower(series, period, std_dev):
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return middle - (std * std_dev)

def calc_atr(df, period):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calc_stoch_k(df, period):
    lowest_low = df["low"].rolling(window=period).min()
    highest_high = df["high"].rolling(window=period).max()
    return 100 * (df["close"] - lowest_low) / (highest_high - lowest_low)

def calc_stoch_d(df, period, smooth):
    stoch_k = calc_stoch_k(df, period)
    return stoch_k.rolling(window=smooth).mean()

def calc_cci(df, period):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    return (tp - sma) / (0.015 * mad)

def calc_williams_r(df, period):
    highest_high = df["high"].rolling(window=period).max()
    lowest_low = df["low"].rolling(window=period).min()
    return -100 * (highest_high - df["close"]) / (highest_high - lowest_low)

def calc_roc(series, period):
    return 100 * (series - series.shift(period)) / series.shift(period)

def calc_momentum(series, period):
    return series - series.shift(period)

def calc_mfi(df, period):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    mf = tp * df["volume"]
    positive_mf = np.where(tp > tp.shift(), mf, 0.0)
    negative_mf = np.where(tp < tp.shift(), mf, 0.0)
    positive_mf_sum = pd.Series(positive_mf, index=df.index).rolling(window=period).sum()
    negative_mf_sum = pd.Series(negative_mf, index=df.index).rolling(window=period).sum()
    mfr = positive_mf_sum / negative_mf_sum
    return 100 - (100 / (1 + mfr))


def compute_indicators(df):
    """Compute all required indicators."""
    indicators = {{}}
{indicator_code}
    return indicators


def check_cross_above(series1, series2, i):
    """Check if series1 crossed above series2 at index i."""
    if i < 1:
        return False
    prev_diff = series1.iloc[i-1] - series2.iloc[i-1]
    curr_diff = series1.iloc[i] - series2.iloc[i]
    return prev_diff <= 0 and curr_diff > 0


def check_cross_below(series1, series2, i):
    """Check if series1 crossed below series2 at index i."""
    if i < 1:
        return False
    prev_diff = series1.iloc[i-1] - series2.iloc[i-1]
    curr_diff = series1.iloc[i] - series2.iloc[i]
    return prev_diff >= 0 and curr_diff < 0


def check_entry_conditions(df, indicators, i):
    """Check if ALL entry conditions are met."""
    price = df["close"].iloc[i]
{entry_code}


def check_exit_conditions(df, indicators, i):
    """Check if ANY exit condition is met."""
    price = df["close"].iloc[i]
{exit_code}


def signal(df, i):
    """
    Generate trading signal for bar i.

    Args:
        df: DataFrame with OHLCV data up to bar i
        i: Current bar index

    Returns:
        1 for buy signal, -1 for sell signal, 0 for no signal
    """
    if i < 50:  # Need enough data for indicators
        return 0

    try:
        indicators = compute_indicators(df)

        # Check for NaN values at current index
        for name, series in indicators.items():
            if pd.isna(series.iloc[i]):
                return 0

        if check_entry_conditions(df, indicators, i):
            return 1

        if check_exit_conditions(df, indicators, i):
            return -1

        return 0
    except Exception:
        return 0
'''

    def __init__(self):
        """Initialize code generator."""
        pass

    def _generate_indicator_code(self, indicator: IndicatorConfig) -> str:
        """Generate code to compute a single indicator."""
        name = indicator.name
        params = indicator.params
        output_name = indicator.output_name

        # Map indicator names to their computation code
        indicator_code_map = {
            "sma": lambda p: f'indicators["{output_name}"] = calc_sma(df["close"], {p.get("period", 20)})',
            "ema": lambda p: f'indicators["{output_name}"] = calc_ema(df["close"], {p.get("period", 20)})',
            "rsi": lambda p: f'indicators["{output_name}"] = calc_rsi(df["close"], {p.get("period", 14)})',
            "macd": lambda p: f'indicators["{output_name}"] = calc_macd(df["close"], {p.get("fast_period", 12)}, {p.get("slow_period", 26)})',
            "macd_signal": lambda p: f'indicators["{output_name}"] = calc_macd_signal(df["close"], {p.get("fast_period", 12)}, {p.get("slow_period", 26)}, {p.get("signal_period", 9)})',
            "macd_hist": lambda p: f'indicators["{output_name}"] = calc_macd_hist(df["close"], {p.get("fast_period", 12)}, {p.get("slow_period", 26)}, {p.get("signal_period", 9)})',
            "bollinger_upper": lambda p: f'indicators["{output_name}"] = calc_bollinger_upper(df["close"], {p.get("period", 20)}, {p.get("std_dev", 2.0)})',
            "bollinger_middle": lambda p: f'indicators["{output_name}"] = calc_bollinger_middle(df["close"], {p.get("period", 20)})',
            "bollinger_lower": lambda p: f'indicators["{output_name}"] = calc_bollinger_lower(df["close"], {p.get("period", 20)}, {p.get("std_dev", 2.0)})',
            "atr": lambda p: f'indicators["{output_name}"] = calc_atr(df, {p.get("period", 14)})',
            "stoch_k": lambda p: f'indicators["{output_name}"] = calc_stoch_k(df, {p.get("period", 14)})',
            "stoch_d": lambda p: f'indicators["{output_name}"] = calc_stoch_d(df, {p.get("period", 14)}, {p.get("smooth", 3)})',
            "cci": lambda p: f'indicators["{output_name}"] = calc_cci(df, {p.get("period", 20)})',
            "williams_r": lambda p: f'indicators["{output_name}"] = calc_williams_r(df, {p.get("period", 14)})',
            "roc": lambda p: f'indicators["{output_name}"] = calc_roc(df["close"], {p.get("period", 12)})',
            "momentum": lambda p: f'indicators["{output_name}"] = calc_momentum(df["close"], {p.get("period", 10)})',
            "mfi": lambda p: f'indicators["{output_name}"] = calc_mfi(df, {p.get("period", 14)})',
        }

        if name not in indicator_code_map:
            raise CodeGeneratorError(f"Unknown indicator: {name}")

        return "    " + indicator_code_map[name](params)

    def _generate_condition_code(self, condition: Condition, indent_level: int = 1) -> str:
        """Generate code for a single condition."""
        ind = "    " * indent_level

        left = condition.left_operand
        right = condition.right_operand
        op = condition.operator

        # Handle left operand
        if left == "price":
            left_code = "price"
        else:
            left_code = f'indicators["{left}"].iloc[i]'

        # Handle right operand
        if isinstance(right, (int, float)):
            right_code = str(right)
        elif right == "price":
            right_code = "price"
        else:
            right_code = f'indicators["{right}"].iloc[i]'

        # Generate comparison code
        if op == ConditionOperator.GREATER_THAN:
            return f"{ind}({left_code} > {right_code})"
        elif op == ConditionOperator.LESS_THAN:
            return f"{ind}({left_code} < {right_code})"
        elif op == ConditionOperator.GREATER_EQUAL:
            return f"{ind}({left_code} >= {right_code})"
        elif op == ConditionOperator.LESS_EQUAL:
            return f"{ind}({left_code} <= {right_code})"
        elif op == ConditionOperator.EQUAL:
            return f"{ind}({left_code} == {right_code})"
        elif op == ConditionOperator.CROSS_ABOVE:
            if left == "price":
                left_series = 'df["close"]'
            else:
                left_series = f'indicators["{left}"]'
            if isinstance(right, (int, float)):
                right_series = f'pd.Series({right}, index=df.index)'
            elif right == "price":
                right_series = 'df["close"]'
            else:
                right_series = f'indicators["{right}"]'
            return f"{ind}check_cross_above({left_series}, {right_series}, i)"
        elif op == ConditionOperator.CROSS_BELOW:
            if left == "price":
                left_series = 'df["close"]'
            else:
                left_series = f'indicators["{left}"]'
            if isinstance(right, (int, float)):
                right_series = f'pd.Series({right}, index=df.index)'
            elif right == "price":
                right_series = 'df["close"]'
            else:
                right_series = f'indicators["{right}"]'
            return f"{ind}check_cross_below({left_series}, {right_series}, i)"
        else:
            raise CodeGeneratorError(f"Unknown operator: {op}")

    def _generate_entry_code(self, conditions: list[Condition]) -> str:
        """Generate entry condition check code (AND logic)."""
        if not conditions:
            return "    return False"

        condition_codes = [
            self._generate_condition_code(c, indent_level=0)
            for c in conditions
        ]

        # Join with AND
        combined = " and\n        ".join(c.strip() for c in condition_codes)
        return f"    return (\n        {combined}\n    )"

    def _generate_exit_code(self, conditions: list[Condition]) -> str:
        """Generate exit condition check code (OR logic)."""
        if not conditions:
            return "    return False"

        condition_codes = [
            self._generate_condition_code(c, indent_level=0)
            for c in conditions
        ]

        # Join with OR
        combined = " or\n        ".join(c.strip() for c in condition_codes)
        return f"    return (\n        {combined}\n    )"

    def generate(self, spec: StrategySpec) -> str:
        """
        Generate Python code from StrategySpec.

        Args:
            spec: Strategy specification

        Returns:
            Complete Python code string

        Raises:
            CodeGeneratorError: If code generation fails
        """
        # Generate indicator computation code
        indicator_lines = [
            self._generate_indicator_code(ind)
            for ind in spec.indicators
        ]
        indicator_code = "\n".join(indicator_lines) if indicator_lines else "    pass"

        # Generate condition code
        entry_code = self._generate_entry_code(spec.entry_conditions)
        exit_code = self._generate_exit_code(spec.exit_conditions)

        # Fill template
        code = self.TEMPLATE.format(
            name=spec.name,
            description=spec.description,
            indicator_code=indicator_code,
            entry_code=entry_code,
            exit_code=exit_code,
        )

        return code

    def generate_and_validate(self, spec: StrategySpec) -> tuple[str, list[str]]:
        """
        Generate code and validate it compiles.

        Args:
            spec: Strategy specification

        Returns:
            Tuple of (code, errors). Empty errors list if valid.
        """
        try:
            code = self.generate(spec)

            # Try to compile the code
            compile(code, "<strategy>", "exec")

            return code, []

        except SyntaxError as e:
            return "", [f"Generated code has syntax error: {e}"]
        except CodeGeneratorError as e:
            return "", [str(e)]
        except Exception as e:
            return "", [f"Code generation failed: {e}"]
