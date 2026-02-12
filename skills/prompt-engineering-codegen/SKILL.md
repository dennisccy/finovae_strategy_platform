# Skill: Prompt Engineering & Code Generation

## Purpose

Design prompts for natural-language-to-StrategySpec compilation and build code generators that output safe, executable Python signal functions. This skill is used by **A3 (Compiler/Codegen Agent)** to maintain the NL compilation pipeline (`strategy/compiler.py`) and the code generation layer (`strategy/codegen.py`).

The compilation pipeline has two stages:
1. **NL -> StrategySpec**: Claude API interprets a user's natural language strategy description and produces a structured `StrategySpec` JSON conforming to the frozen contracts.
2. **StrategySpec -> Python code**: A deterministic code generator transforms the spec into a `signal(df, i) -> int` function that runs inside the RestrictedPython sandbox.

Both stages must produce correct, safe, and deterministic output.

## Do

- Use bounded whitelists for indicators and operators. Only indicators in `CompileConstraints.allowed_indicators` and operators in `ConditionOperator` enum are valid. The compiler prompt must enumerate these explicitly.
- Validate the `StrategySpec` schema before passing it to codegen. Every field must be present, every indicator name must be in the whitelist, every operator must be a valid `ConditionOperator` value.
- Generate `signal(df: pd.DataFrame, i: int) -> int` functions only. The function must return exactly `1` (buy), `-1` (sell), or `0` (hold).
- Include safety guards in generated code: no imports beyond what the sandbox provides, no global state mutation, no file or network access.
- Use few-shot examples in the compiler system prompt to anchor Claude's output format.
- Handle edge cases in the prompt: ambiguous NL input should produce a warning, not a hallucinated strategy.
- Pin the compiler prompt version alongside the contract version so prompt changes are tracked.
- Test the compiler with at least 10 diverse NL inputs spanning simple (single indicator) to complex (multi-indicator, cross conditions) strategies.
- Ensure the codegen output is deterministic: the same `StrategySpec` must always produce the same Python code.

## Don't

- Allow unbounded indicator sets. If the user mentions an indicator not in the whitelist, return a compile error -- never invent a new indicator.
- Generate code with imports beyond `numpy` and `pandas`. The sandbox will reject them, but they should never appear in generated code in the first place.
- Skip schema validation between the compiler and codegen stages. Malformed specs must be caught before code generation.
- Allow `exec()`, `eval()`, `__import__()`, or any dynamic code execution in generated code.
- Use f-strings or string concatenation to build code from user input without sanitization. All user-derived values (indicator names, parameters) must be validated against the whitelist before insertion.
- Hard-code indicator logic in the generated signal function. Generated code must call indicators from the pre-computed DataFrame columns, not re-implement indicator math.
- Allow the compiler to return partial specs. Either the full `StrategySpec` is valid or compilation fails with an error.

## SOP (Standard Operating Procedure)

### 1. Review Current Compiler Prompt

```bash
# Read the current system prompt and compiler logic
cat strategy/compiler.py

# Read the current codegen logic
cat strategy/codegen.py

# Read the indicator registry
cat strategy/indicators.py

# Read the frozen contracts for StrategySpec shape
cat shared/contracts.py
```

### 2. Test Compiler with Diverse NL Inputs

Test with at minimum these categories:

| Category | Example NL Input |
|---|---|
| Simple momentum | "Buy when RSI crosses above 30, sell when RSI crosses below 70" |
| Moving average crossover | "Buy when 20-day EMA crosses above 50-day EMA, sell on reverse" |
| Multi-indicator | "Buy when RSI < 30 AND price > lower Bollinger Band, sell when RSI > 70" |
| Ambiguous | "Buy low sell high" (should produce warning or error) |
| Unsupported indicator | "Buy when Ichimoku cloud turns green" (should fail gracefully) |
| Edge case parameters | "Use a 200-period SMA" (valid but large lookback) |
| Position sizing | "Invest 50% of portfolio each trade" |
| No exit condition | "Buy when MACD histogram is positive" (should infer or warn) |
| Contradictory | "Buy when RSI > 80 and RSI < 20" (should warn) |
| Complex crossover | "Buy when MACD crosses above signal line and ADX > 25" |

```bash
# Run compiler tests
pytest tests/ -k "compiler" -v

# Run codegen tests
pytest tests/ -k "codegen" -v

# Run full pipeline test
pytest tests/ -k "pipeline" -v
```

### 3. Validate Generated Code Against Sandbox

```bash
# For each generated code output, verify it passes sandbox compilation
pytest tests/test_sandbox.py -v

# Verify generated code has no forbidden constructs
grep -n "import \|__import__\|exec(\|eval(\|open(" <generated_code_file>
```

### 4. Schema Validation Check

```bash
# Verify all StrategySpec outputs conform to the contract
python -c "
from shared.contracts import StrategySpec, ConditionOperator, CompileConstraints
# Validate a sample spec
constraints = CompileConstraints()
# Check all indicator names are in whitelist
# Check all operators are valid ConditionOperator values
print('Schema validation passed')
"
```

### 5. Regression Test

```bash
# Run full test suite to ensure no regressions
pytest -v
mypy strategy/
ruff check strategy/
```

## Required Output Format

Every prompt-engineering-codegen task must produce:

### Compiler Prompt Text

```
System Prompt Version: X.Y
Compatible Contract Version: shared/contracts.py Frozen Date YYYY-MM-DD

[Full system prompt text for Claude API call]
```

### StrategySpec JSON Examples

```json
{
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
  "position_size": {"type": "fixed_percent", "value": 100.0}
}
```

### Generated Python Code

```python
def signal(df: pd.DataFrame, i: int) -> int:
    """Generated signal function. Returns 1 (buy), -1 (sell), 0 (hold)."""
    if i < 1:
        return 0
    # Entry conditions (AND logic)
    # Exit conditions (OR logic)
    ...
    return 0
```

### Validation Report

```
Compiler Test Results:
  10/10 NL inputs compiled successfully (or failed gracefully)
  0 schema validation errors
  0 forbidden constructs in generated code
  All generated code passed sandbox compilation
  Codegen is deterministic: 10/10 identical outputs for identical specs
```
