# Skill: DSL Design

## Purpose

Design bounded domain-specific languages for strategy specification within the Finovae Strategy Platform. This skill is used by **A3 (Compiler/Codegen Agent)** in coordination with **A1 (Architecture Lead)** to define and maintain the formal grammar of the `StrategySpec` DSL.

The StrategySpec DSL is the intermediate representation between natural language input and executable Python code. It must be expressive enough to capture meaningful trading strategies but constrained enough to prevent unsafe or nonsensical constructs. The DSL is intentionally **not Turing-complete** -- it is a declarative specification language for condition-based trading rules.

## Do

- Define a formal grammar for `StrategySpec` using BNF (Backus-Naur Form) or an equivalent notation.
- Enumerate **all** valid operators explicitly. Only operators defined in the `ConditionOperator` enum are allowed: `>`, `<`, `>=`, `<=`, `==`, `cross_above`, `cross_below`.
- Enumerate **all** valid indicator names explicitly. Only indicators in `CompileConstraints.allowed_indicators` are valid: `sma`, `ema`, `rsi`, `macd`, `macd_signal`, `macd_hist`, `bollinger_upper`, `bollinger_middle`, `bollinger_lower`, `atr`, `adx`, `stoch_k`, `stoch_d`, `cci`, `williams_r`, `obv`, `vwap`, `mfi`, `roc`, `momentum`.
- Provide at least 10 example strategies covering the full range of DSL constructs.
- Keep the DSL minimal but complete for v0.1. Every construct must have a clear semantic meaning and a direct mapping to generated code.
- Define parameter constraints for each indicator (e.g., `sma.period` must be a positive integer, `rsi.period` must be between 2 and 500).
- Define operand types clearly: an operand is either an indicator output name, the literal `"price"` (mapped to close price), or a numeric constant.
- Document the evaluation semantics: entry conditions use AND logic (all must be true), exit conditions use OR logic (any triggers exit).
- Version the grammar alongside the contracts. Grammar version must be compatible with the `shared/contracts.py` frozen date.

## Don't

- Allow arbitrary expressions. The DSL supports only comparisons between operands, not arithmetic expressions like `sma_20 + atr_14 > price`.
- Support Turing-complete constructs. No loops, no variables, no user-defined functions, no recursion, no state machines.
- Add features without updating the grammar specification. Every new construct must be formally defined before implementation.
- Allow operators not in the `ConditionOperator` enum. If a new operator is needed, it must first be added to the frozen contracts (with A0 approval).
- Allow indicator names not in the `CompileConstraints.allowed_indicators` whitelist. New indicators require contract modification.
- Allow unbounded parameter values. Every indicator parameter must have a defined valid range.
- Mix evaluation semantics. Entry is always AND; exit is always OR. Do not introduce conditional logic or nested grouping in v0.1.
- Create ambiguous grammar rules. Every valid StrategySpec must have exactly one parse interpretation.

## SOP (Standard Operating Procedure)

### 1. Review Current DSL Definition

```bash
# Read the frozen contracts that define DSL types
cat shared/contracts.py

# Read the compiler that produces DSL instances
cat strategy/compiler.py

# Read the codegen that consumes DSL instances
cat strategy/codegen.py

# Read the indicator registry for valid indicator names and parameters
cat strategy/indicators.py
```

### 2. Document the Grammar

Write the grammar in BNF notation (see Required Output Format below). Ensure every production rule maps to a contract dataclass or enum.

### 3. Create Example Strategies

Provide at least 10 examples spanning these categories:

| # | Category | Description |
|---|---|---|
| 1 | Single indicator threshold | RSI > 70 |
| 2 | Single indicator crossover | EMA(20) crosses above EMA(50) |
| 3 | Multi-indicator entry | RSI < 30 AND price > bollinger_lower |
| 4 | Multi-indicator exit | RSI > 70 OR price < sma_200 |
| 5 | Momentum strategy | ROC > 0 AND ADX > 25 |
| 6 | Mean reversion | CCI < -100 entry, CCI > 100 exit |
| 7 | Volatility-based | ATR > threshold AND price cross_above bollinger_middle |
| 8 | Volume-confirmed | MFI < 20 AND OBV cross_above its SMA |
| 9 | Position sizing variant | Same strategy with fixed_percent vs all_in |
| 10 | Minimal strategy | Single entry condition, single exit condition |

### 4. Validate Examples Against Schema

```bash
# Validate each example StrategySpec against the contract
python -c "
from shared.contracts import (
    StrategySpec, IndicatorConfig, Condition, PositionSizing,
    ConditionOperator, PositionSizingType, CompileConstraints
)

constraints = CompileConstraints()

# Example: RSI mean reversion
spec = StrategySpec(
    name='RSI Mean Reversion',
    description='Buy oversold, sell overbought',
    indicators=[
        IndicatorConfig(name='rsi', params={'period': 14}, output_name='rsi_14')
    ],
    entry_conditions=[
        Condition(left_operand='rsi_14', operator=ConditionOperator.CROSS_ABOVE, right_operand=30.0)
    ],
    exit_conditions=[
        Condition(left_operand='rsi_14', operator=ConditionOperator.CROSS_BELOW, right_operand=70.0)
    ],
    position_size=PositionSizing(type=PositionSizingType.ALL_IN, value=100.0)
)

# Validate indicator names
for ind in spec.indicators:
    assert ind.name in constraints.allowed_indicators, f'Invalid indicator: {ind.name}'

# Validate condition count
assert len(spec.entry_conditions) <= constraints.max_conditions
assert len(spec.exit_conditions) <= constraints.max_conditions
assert len(spec.indicators) <= constraints.max_indicators

print('Validation passed')
"
```

### 5. Review with A1 for Contract Alignment

- Confirm grammar matches the current frozen contracts exactly.
- Confirm no grammar construct requires a contract change.
- If a grammar extension is needed, file a contract change request per the `architecture-contracts` skill SOP.

### 6. Regression Test

```bash
# Run all tests that exercise the DSL
pytest tests/ -k "compiler or codegen or strategy" -v

# Type check
mypy strategy/

# Lint
ruff check strategy/
```

## Required Output Format

Every dsl-design task must produce:

### Grammar Specification (BNF)

```bnf
<strategy_spec>    ::= <name> <description> <indicators> <entry_conditions> <exit_conditions> <position_size>

<name>             ::= STRING
<description>      ::= STRING

<indicators>       ::= <indicator_config> | <indicator_config> "," <indicators>
<indicator_config> ::= <indicator_name> "(" <params> ")" "as" <output_name>
<indicator_name>   ::= "sma" | "ema" | "rsi" | "macd" | "macd_signal" | "macd_hist"
                     | "bollinger_upper" | "bollinger_middle" | "bollinger_lower"
                     | "atr" | "adx" | "stoch_k" | "stoch_d" | "cci" | "williams_r"
                     | "obv" | "vwap" | "mfi" | "roc" | "momentum"
<params>           ::= <param_pair> | <param_pair> "," <params>
<param_pair>       ::= PARAM_NAME "=" NUMBER
<output_name>      ::= IDENTIFIER

<entry_conditions> ::= <condition> | <condition> "AND" <entry_conditions>
<exit_conditions>  ::= <condition> | <condition> "OR" <exit_conditions>

<condition>        ::= <operand> <operator> <operand>
<operator>         ::= ">" | "<" | ">=" | "<=" | "==" | "cross_above" | "cross_below"
<operand>          ::= <output_name> | "price" | NUMBER

<position_size>    ::= <sizing_type> "(" <sizing_value> ")"
<sizing_type>      ::= "fixed_amount" | "fixed_percent" | "all_in"
<sizing_value>     ::= NUMBER
```

### Example Strategy Specs

Each example must include:
1. Natural language description
2. StrategySpec JSON
3. Brief explanation of how the NL maps to the spec

```json
{
  "example_number": 1,
  "natural_language": "Buy when RSI(14) crosses above 30, sell when RSI(14) crosses below 70",
  "strategy_spec": {
    "name": "RSI Mean Reversion",
    "description": "Buy oversold, sell overbought using RSI(14)",
    "indicators": [
      {"name": "rsi", "params": {"period": 14}, "output_name": "rsi_14"}
    ],
    "entry_conditions": [
      {"left_operand": "rsi_14", "operator": "cross_above", "right_operand": 30}
    ],
    "exit_conditions": [
      {"left_operand": "rsi_14", "operator": "cross_below", "right_operand": 70}
    ],
    "position_size": {"type": "all_in", "value": 100.0}
  },
  "mapping_notes": "RSI(14) -> indicator rsi with period=14; 'crosses above 30' -> cross_above operator with numeric operand 30; 'crosses below 70' -> cross_below with 70."
}
```

### Validation Results

```
Grammar Validation:
  10/10 example specs conform to BNF grammar
  10/10 example specs pass StrategySpec schema validation
  All indicator names in whitelist: PASS
  All operators in ConditionOperator enum: PASS
  All parameter values within defined ranges: PASS
  Entry conditions use AND semantics: PASS
  Exit conditions use OR semantics: PASS

Contract Alignment:
  Grammar version: 1.0
  Compatible with: shared/contracts.py Frozen Date 2026-02-11
  No contract changes required: PASS
```
