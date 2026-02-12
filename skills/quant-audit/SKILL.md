# Skill: Quant Audit

## Purpose

Audit the backtesting system for correctness, focusing on determinism, lookahead bias prevention, data leakage, and metrics accuracy. This skill is used by **A6 (QA/Audit Agent)** to verify that backtesting results are trustworthy and reproducible.

A backtesting engine that produces unreliable results is worse than no engine at all -- users will make real trading decisions based on these numbers. The quant audit skill exists to catch subtle bugs that can inflate performance (lookahead bias), produce inconsistent results (non-determinism), or miscalculate risk metrics.

## Do

- Run 5 identical backtest runs with the same inputs and compare results trade-by-trade. Every field (`entry_time`, `exit_time`, `entry_price`, `exit_price`, `quantity`, `pnl`, `commission_paid`) must be bit-for-bit identical across all 5 runs.
- Verify that the `signal(df, i)` function receives only data up to and including bar `i`. The DataFrame passed to the signal function must be sliced to `df[:i+1]` or equivalent -- never the full dataset.
- Check that signal execution follows the **next-bar model**: a signal generated at bar[i] must execute at bar[i+1]'s open price, not at bar[i]'s close or any intra-bar price.
- Validate metrics formulas against reference implementations:
  - **Sharpe ratio**: `mean(returns) / std(returns) * sqrt(252)` (or appropriate annualization factor for the timeframe).
  - **Max drawdown**: largest peak-to-trough decline in the equity curve.
  - **Win rate**: `winning_trades / total_trades`.
  - **Profit factor**: `sum(winning_pnl) / abs(sum(losing_pnl))`.
- Test edge cases: empty trade list (no signals triggered), single trade, full drawdown to zero, strategy that is always in a position, strategy that never enters.
- Verify that commission and slippage are applied consistently on both entry and exit.
- Confirm the random seed for slippage simulation is fixed and documented.
- Check that equity curve timestamps align with OHLCV bar timestamps.
- Verify that the backtest engine handles data gaps gracefully (missing bars should not produce phantom trades).

## Don't

- Skip determinism checks. "It works on my machine" is not acceptable -- determinism must be proven by automated tests.
- Accept "close enough" floating-point results. Use `math.isclose()` or `numpy.allclose()` with explicit tolerances (e.g., `rtol=1e-9`) for numeric comparisons, but the tolerance must be justified and documented.
- Ignore edge cases. A backtest with zero trades must return valid metrics (e.g., `total_return=0.0`, `win_rate=0.0`, `profit_factor=0.0`, `sharpe_ratio=0.0`), not crash or return NaN.
- Trust that "the code looks right." Every invariant must have an automated test that fails if the invariant is broken.
- Allow lookahead in any form: future data in signal computation, same-bar execution, or use of close price for entry when signal fires on that bar's close.
- Skip review of the `backtest/engine.py` execution loop. This is where most subtle bugs live.
- Approve a backtest engine change without re-running the full audit.

## SOP (Standard Operating Procedure)

### 1. Run Determinism Tests

```bash
# Run the determinism test suite
pytest tests/test_determinism.py -v

# Expected: 5 identical runs produce identical BacktestResult objects
# Check: trades list, equity_curve, all scalar metrics
```

### 2. Run Lookahead Bias Tests

```bash
# Run the lookahead prevention test suite
pytest tests/test_lookahead.py -v

# Expected:
# - signal(df, i) receives df sliced to [:i+1]
# - Signal at bar[i] executes at bar[i+1] open
# - No future data accessible in signal function
```

### 3. Run Sandbox Security Tests

```bash
# Verify sandbox prevents code-level data leakage
pytest tests/test_sandbox.py -v
```

### 4. Manual Engine Review

Review `backtest/engine.py` line by line, checking:

```bash
cat backtest/engine.py
```

Checklist:
- [ ] Signal function is called with `df.iloc[:i+1]` (or equivalent slicing)
- [ ] Trade entry uses `bar[i+1].open`, not `bar[i].close`
- [ ] Commission is deducted on both entry and exit
- [ ] Slippage is applied with a fixed random seed
- [ ] Equity is updated after each trade, not just at bar close
- [ ] Position tracking prevents double-entry (no buying when already long)
- [ ] Final open position is closed at the last bar's close (or documented if not)

### 5. Metrics Validation

```bash
# Review metrics calculations
cat backtest/metrics.py

# Cross-reference with known test cases:
# - A strategy with 2 winning trades ($100 each) and 1 losing trade (-$50):
#   win_rate = 2/3 = 0.6667
#   profit_factor = 200/50 = 4.0
#   total_return = (10000 + 150) / 10000 - 1 = 0.015
```

### 6. Edge Case Testing

```bash
# Run edge case tests (if they exist, or create them)
pytest tests/ -k "edge or empty or single or zero" -v

# Test manually if needed:
# - Zero trades scenario
# - Single trade scenario
# - Full drawdown scenario
# - All bars produce buy signal
# - All bars produce hold signal
```

### 7. Full Audit Regression

```bash
# Run complete test suite
pytest -v --tb=long

# Generate coverage report to find untested paths
pytest --cov=backtest --cov-report=term-missing
```

## Required Output Format

Every quant-audit task must produce:

### Test Results

```
Determinism Tests:
  [PASS] 5 identical runs -> identical trades (N trades, all fields match)
  [PASS] 5 identical runs -> identical equity curves (M points, all match)
  [PASS] 5 identical runs -> identical scalar metrics (Sharpe, MaxDD, etc.)

Lookahead Tests:
  [PASS] signal(df, i) receives only bars 0..i
  [PASS] entry price = bar[i+1].open (next-bar execution)
  [PASS] no future data accessible via DataFrame index

Sandbox Tests:
  [PASS] all escape attempts blocked (see python-sandboxing skill)
```

### Determinism Diff Report

```
Run 1 vs Run 2: IDENTICAL
Run 1 vs Run 3: IDENTICAL
Run 1 vs Run 4: IDENTICAL
Run 1 vs Run 5: IDENTICAL

Fields compared per trade:
  trade_id, entry_time, exit_time, entry_price, exit_price,
  quantity, pnl, pnl_percent, commission_paid

Scalar metrics compared:
  total_return, max_drawdown, num_trades, win_rate,
  sharpe_ratio, profit_factor

Tolerance: exact match for timestamps and counts; rtol=1e-9 for floats
```

### Lookahead Audit Checklist

```
[PASS/FAIL] Signal function receives sliced DataFrame (bars 0 to i only)
[PASS/FAIL] Trade entry uses next-bar open price (bar[i+1].open)
[PASS/FAIL] No close-price execution on signal bar
[PASS/FAIL] Indicator computation uses only past/current data
[PASS/FAIL] No global state carries future information between signal calls
[PASS/FAIL] DataFrame index does not expose future bar count
```

### Risk Findings

```
Severity: Critical | High | Medium | Low | Info

[Severity] Finding Title
  Description: What was found
  Location: file.py:line_number
  Impact: How this affects backtest results
  Recommendation: How to fix
  Test: Which test covers this (or "needs test")
```
