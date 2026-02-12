# T30: StrategySpec + NL Compiler + Validator + Code Generation

**Agent:** A3 (Strategy Compiler)
**Status:** Draft
**Priority:** Core (blocks T40)

---

## Objective

Implement the full strategy compilation pipeline: accept a natural language trading strategy description, compile it to a validated `StrategySpec` JSON via Claude API, validate the spec against the indicator whitelist and schema constraints, and generate executable Python code containing a `signal(df, i) -> int` function that passes RestrictedPython compilation.

---

## Current State

- `strategy/compiler.py` contains the Claude API integration with a system prompt guiding JSON output.
- `strategy/codegen.py` transforms a `StrategySpec` into executable Python code.
- `strategy/indicators.py` maintains the `INDICATOR_REGISTRY` of available technical indicators.
- `shared/contracts.py` defines `StrategySpec`, `CompileConstraints`, `ConditionOperator`, and `PositionSizingType`.
- The system prompt in `compiler.py` defines the output JSON schema and available indicators.

---

## Plan

### 1. Indicator Whitelist (`strategy/indicators.py`)

Review and document the bounded indicator whitelist from `CompileConstraints.allowed_indicators`. Target: 20 indicators across categories.

**Moving Averages:**
- `sma(period)` - Simple Moving Average
- `ema(period)` - Exponential Moving Average
- `wma(period)` - Weighted Moving Average

**Momentum:**
- `rsi(period)` - Relative Strength Index
- `macd(fast, slow, signal)` - MACD line, signal, histogram
- `stochastic(k_period, d_period)` - Stochastic %K and %D
- `cci(period)` - Commodity Channel Index
- `roc(period)` - Rate of Change
- `williams_r(period)` - Williams %R

**Volatility:**
- `bollinger_bands(period, std_dev)` - Upper, middle, lower bands
- `atr(period)` - Average True Range
- `keltner_channels(period, atr_mult)` - Upper, middle, lower channels

**Volume:**
- `obv()` - On-Balance Volume
- `vwap()` - Volume Weighted Average Price
- `volume_sma(period)` - Simple Moving Average of volume

**Trend:**
- `adx(period)` - Average Directional Index
- `supertrend(period, multiplier)` - Supertrend indicator
- `psar()` - Parabolic SAR

**Price:**
- `highest(period)` - Highest high over period
- `lowest(period)` - Lowest low over period

Each indicator function in the registry must:
- Accept a DataFrame and parameters, return a Series or DataFrame (for multi-output indicators like MACD).
- Handle edge cases: insufficient data returns NaN for early bars.
- Use only pandas/numpy operations (no external TA libraries to maintain sandbox compatibility).

### 2. NL Compilation (`strategy/compiler.py`)

The compiler sends the natural language description to Claude API with a structured system prompt.

**System Prompt Structure:**
```
You are a trading strategy compiler. Convert the natural language strategy
description into a StrategySpec JSON object.

Output JSON schema:
{
  "name": string,
  "description": string,
  "indicators": [
    {"name": string, "function": string, "params": {string: number}}
  ],
  "entry_conditions": [
    {"left": string, "operator": string, "right": string}
  ],
  "exit_conditions": [
    {"left": string, "operator": string, "right": string}
  ],
  "position_sizing": {
    "type": "fixed_fraction" | "fixed_amount",
    "value": number
  }
}

Available indicators: [list from CompileConstraints]
Available operators: >, <, >=, <=, ==, cross_above, cross_below
Entry conditions are AND-combined (all must be true).
Exit conditions are OR-combined (any triggers exit).
```

**API Call Configuration:**
- Model: `claude-sonnet-4-20250514` (or latest available, configurable)
- Max tokens: 2048 (StrategySpec is compact)
- Temperature: 0.0 (deterministic output for same input)
- Response format: request JSON via system prompt instruction

**Response Parsing:**
- Extract JSON from Claude's response (handle markdown code blocks if present).
- Parse with `json.loads()` and validate against `StrategySpec` schema.
- Retry once on parse failure with a follow-up message asking for correction.
- Raise `CompilationError` with descriptive message if retry also fails.

### 3. StrategySpec Validation

After parsing, validate the `StrategySpec` against these rules:

| Validation                              | Error Message                                      |
|-----------------------------------------|----------------------------------------------------|
| All indicator functions in whitelist    | `Unknown indicator: {name}. Allowed: [...]`        |
| Indicator params are numeric and positive| `Invalid parameter {key}={value} for {indicator}` |
| Condition operators are valid enums     | `Unknown operator: {op}. Allowed: [...]`           |
| Condition left/right reference valid indicators or price fields | `Unknown reference: {ref}` |
| At least one entry condition exists     | `Strategy must have at least one entry condition`  |
| At least one exit condition exists      | `Strategy must have at least one exit condition`   |
| Position sizing type is valid enum      | `Unknown position sizing type: {type}`             |
| Position sizing value is in range       | `Position size must be between 0 and 1 for fixed_fraction` |
| Name is non-empty                       | `Strategy name is required`                        |

Return a `ValidationResult` with `valid: bool` and `errors: list[str]`.

### 4. Code Generation (`strategy/codegen.py`)

Transform a validated `StrategySpec` into executable Python code.

**Generated Code Template:**
```python
import numpy as np
import pandas as pd

def signal(df: pd.DataFrame, i: int) -> int:
    """
    Generated signal function for: {strategy_name}

    Entry conditions (AND): {entry_description}
    Exit conditions (OR): {exit_description}
    """
    if i < {warmup_period}:
        return 0

    # Compute indicators
    {indicator_computations}

    # Entry conditions (all must be true)
    entry = True
    {entry_condition_checks}

    # Exit conditions (any triggers exit)
    exit_signal = False
    {exit_condition_checks}

    if exit_signal:
        return -1
    if entry:
        return 1
    return 0
```

**Key code generation rules:**

- **Warmup period**: Calculate as the maximum lookback period across all indicators (e.g., SMA(50) needs 50 bars). Return 0 (hold) for bars within warmup.
- **Indicator computation**: Call functions from `INDICATOR_REGISTRY` on the DataFrame slice. Cache indicator values at the current bar index `i`.
- **Cross-above/cross-below operators**: Generate comparison of current and previous bar values:
  ```python
  # cross_above(a, b): a was below b, now a is above b
  cross_above = (a_prev <= b_prev) and (a_curr > b_curr)
  ```
- **Price field references**: Map `close`, `open`, `high`, `low`, `volume` to `df['close'].iloc[i]`.
- **NaN handling**: Wrap indicator values in `pd.notna()` checks; return 0 if any indicator is NaN.

### 5. RestrictedPython Pre-validation

Before returning generated code, verify it compiles under RestrictedPython:

```python
from RestrictedPython import compile_restricted, safe_globals

code = generate_code(strategy_spec)
compiled = compile_restricted(code, filename='<strategy>', mode='exec')
if compiled.errors:
    raise CodeGenError(f"Generated code failed sandbox compilation: {compiled.errors}")
```

This catches syntax errors and RestrictedPython violations before the code reaches the sandbox executor.

---

## Files to Modify

| File                     | Change                                                           |
|--------------------------|------------------------------------------------------------------|
| `strategy/compiler.py`   | Refine system prompt, add retry logic, improve error handling   |
| `strategy/codegen.py`    | Harden code template, add warmup calculation, NaN handling      |
| `strategy/indicators.py` | Verify all 20 indicators, add missing implementations          |

## Files to Create

| File                              | Purpose                                             |
|-----------------------------------|-----------------------------------------------------|
| `tests/test_compiler.py`          | NL -> StrategySpec compilation tests               |
| `tests/test_codegen.py`           | StrategySpec -> Python code generation tests       |
| `tests/test_indicators.py`        | Individual indicator correctness tests             |
| `tests/fixtures/strategy_specs/`  | Sample StrategySpec JSON files for testing          |

---

## Test Plan

### Compiler Tests (`tests/test_compiler.py`)

Test 10+ diverse natural language inputs:

1. **Simple moving average crossover**: "Buy when 20-day SMA crosses above 50-day SMA, sell when it crosses below"
2. **RSI overbought/oversold**: "Buy when RSI(14) drops below 30, sell when RSI(14) rises above 70"
3. **Bollinger Band bounce**: "Buy when price touches the lower Bollinger Band, sell when it hits the upper band"
4. **MACD signal cross**: "Buy on MACD signal line crossover, sell on crossunder"
5. **Multi-indicator**: "Buy when RSI < 40 AND price above 200 SMA AND MACD histogram positive"
6. **Volume confirmation**: "Buy when price breaks above 20-day high with volume above average"
7. **Trend following**: "Buy when ADX > 25 and price above EMA(50), sell when ADX drops below 20"
8. **Mean reversion**: "Buy when CCI drops below -100, sell when CCI rises above 100"
9. **Ambiguous input**: "Buy low sell high" - verify graceful handling
10. **Non-strategy input**: "What's the weather today?" - verify error response

For each test, verify:
- Output is valid JSON
- All indicators are in the whitelist
- All operators are valid
- Entry and exit conditions are present

### Code Generation Tests (`tests/test_codegen.py`)

11. **Compiles under RestrictedPython**: For each of the 10 StrategySpecs above, generate code and verify it compiles.
12. **Signal function signature**: Generated code defines `signal(df, i) -> int` callable.
13. **Return values**: Signal function only returns -1, 0, or 1.
14. **Warmup period**: SMA(50) strategy returns 0 for bars 0-49.
15. **Cross-above logic**: Manually construct a DataFrame where SMA(20) crosses above SMA(50) at a known bar. Verify signal returns 1 at that bar.
16. **NaN safety**: Verify signal returns 0 when indicators produce NaN (early bars).

### Indicator Tests (`tests/test_indicators.py`)

17. **SMA correctness**: Compare against hand-computed values for a known series.
18. **RSI range**: Verify RSI output is always in [0, 100] for valid input.
19. **MACD components**: Verify MACD line = fast EMA - slow EMA.
20. **Bollinger Band ordering**: Verify lower <= middle <= upper for all bars.
21. **ATR non-negative**: Verify ATR >= 0 for all bars.

---

## Risks and Mitigations

| Risk                                        | Likelihood | Impact | Mitigation                                               |
|---------------------------------------------|-----------|--------|----------------------------------------------------------|
| Claude API inconsistency in JSON output     | Medium    | High   | Temperature=0, strict schema in prompt, retry with correction |
| Edge cases in NL interpretation             | High      | Medium | Validate output thoroughly; return clear error for uninterpretable inputs |
| Generated code fails RestrictedPython       | Low       | Medium | Pre-validate before returning; maintain safe code template |
| Indicator computation errors on edge data   | Medium    | Medium | NaN handling in generated code; warmup period buffer     |
| API rate limits or timeouts                 | Low       | Medium | Exponential backoff retry; configurable timeout          |
| Prompt injection via NL input               | Low       | Low    | Claude is instruction-following, not executing; StrategySpec schema constrains output |

---

## Dependencies

- **Upstream:** `shared/contracts.py` (StrategySpec, CompileConstraints) - frozen
- **Downstream:** T40 (pipeline calls compiler, then passes generated code to sandbox)
- **External:** Anthropic Claude API (requires `ANTHROPIC_API_KEY`)

---

## Acceptance Criteria

- [ ] 10+ diverse NL inputs produce valid StrategySpec JSON
- [ ] All generated StrategySpecs pass validation (indicators in whitelist, valid operators)
- [ ] All generated Python code compiles under RestrictedPython
- [ ] Generated `signal()` function returns only -1, 0, or 1
- [ ] Warmup period correctly calculated from indicator parameters
- [ ] Cross-above/cross-below operators correctly implemented in generated code
- [ ] Clear error messages for invalid NL inputs, API failures, and validation failures
- [ ] All tests pass with `pytest tests/test_compiler.py tests/test_codegen.py tests/test_indicators.py -v`
