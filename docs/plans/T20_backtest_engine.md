# T20: Deterministic Backtest Loop + Basic Metrics

**Agent:** A2 (Data + Backtest Core)
**Status:** Draft
**Priority:** Foundation (blocks T40, T60)

---

## Objective

Ensure the backtest engine produces fully deterministic results given identical inputs, implements a correct next-bar execution model to prevent lookahead bias, and computes a comprehensive set of performance metrics that are JSON-serializable.

---

## Current State

- `backtest/engine.py` implements the core backtest loop with position tracking.
- `backtest/fills.py` models slippage and commission.
- `backtest/metrics.py` calculates performance metrics (Sharpe, Sortino, max drawdown, etc.).
- The engine uses next-bar execution: signal at bar[i] executes at bar[i+1] open.
- A controlled random seed is used for the slippage model.
- The `BacktestResult` dataclass in `shared/contracts.py` defines the output schema.

---

## Plan

### 1. Determinism Guarantees (`backtest/engine.py`)

Audit and harden the engine for strict determinism:

- **Random seed**: Set `numpy.random.seed(42)` (or configurable seed) at the start of each backtest run, before any slippage calculation. The seed must be set within the `run()` method, not at module level, to ensure reruns within the same process are deterministic.
- **Float operations**: Use consistent rounding strategy (`round(value, 8)` for prices, `round(value, 2)` for equity/PnL) to avoid platform-dependent float drift.
- **Iteration order**: Ensure DataFrame iteration uses `iloc` with integer indexing, never rely on dictionary ordering or set iteration.
- **No external state**: The engine must not read environment variables, wall-clock time, or any other non-deterministic input during execution.
- **Timestamp handling**: All timestamp comparisons must use the integer epoch representation, not string comparison.

### 2. Next-Bar Execution Model

Verify and document the execution flow:

```
Bar i:   signal_fn(df[:i+1], i) -> signal  (signal sees data up to and including bar i)
Bar i+1: if signal != 0, execute fill at bar[i+1].open
```

Critical invariants:
- The signal function receives a DataFrame sliced to `df.iloc[:i+1]`, preventing any access to future bars.
- Fill price is always `bar[i+1].open`, never `bar[i].close` or any intra-bar price.
- If `i` is the last bar, the signal is generated but no fill occurs (no bar[i+1] exists).
- Position state changes are recorded with the fill bar's timestamp, not the signal bar's.

### 3. Position Tracking

Long-only, single position model:

```
States: FLAT -> LONG -> FLAT
Transitions:
  FLAT + BUY signal  -> LONG (open position at next bar open)
  LONG + SELL signal -> FLAT (close position at next bar open)
  FLAT + SELL signal -> ignored (no short selling)
  LONG + BUY signal  -> ignored (no pyramiding)
```

Track per position:
- Entry timestamp, entry price (fill price after slippage)
- Exit timestamp, exit price (fill price after slippage)
- Commission paid (entry + exit)
- Gross PnL, net PnL (after commission)
- Holding period (number of bars)

### 4. Equity Curve

Track equity at every bar close:

```python
@dataclass
class EquityPoint:
    timestamp: str    # ISO 8601
    equity: float     # Total portfolio value at bar close
    drawdown: float   # Current drawdown from peak (as fraction, 0.0 to -1.0)
```

- **FLAT**: equity = cash balance (no unrealized PnL)
- **LONG**: equity = cash + position_size * bar.close (mark-to-market)
- Record equity even on bars with no signal or trade.
- Drawdown is calculated as `(equity - peak_equity) / peak_equity`.

### 5. Fill Model (`backtest/fills.py`)

Review and verify the slippage and commission model:

- **Slippage**: Gaussian model with configurable mean (0) and std (default: 0.01% of price).
  - Uses the seeded random number generator for determinism.
  - Applied to fill price: `fill_price = bar_open * (1 + slippage_pct)` for buys, `bar_open * (1 - slippage_pct)` for sells.
- **Commission**: Flat percentage model (default: 0.1% per trade, configurable).
  - Applied to trade notional: `commission = abs(quantity * fill_price) * commission_rate`.
- Both slippage and commission must be recorded on each `Trade` object.

### 6. Performance Metrics (`backtest/metrics.py`)

Compute and return the following metrics, all JSON-serializable:

| Metric              | Type   | Formula / Description                                              |
|---------------------|--------|--------------------------------------------------------------------|
| `total_return`      | float  | `(final_equity - initial_capital) / initial_capital`              |
| `annual_return`     | float  | Annualized total return assuming 365-day year                     |
| `max_drawdown`      | float  | Maximum peak-to-trough decline (negative fraction)                |
| `max_drawdown_duration` | int | Longest drawdown period in bars                                  |
| `sharpe_ratio`      | float  | Annualized Sharpe using daily returns, risk-free rate = 0         |
| `sortino_ratio`     | float  | Like Sharpe but uses downside deviation only                      |
| `profit_factor`     | float  | Gross profit / gross loss (inf if no losing trades)               |
| `win_rate`          | float  | Winning trades / total trades                                     |
| `num_trades`        | int    | Total number of completed round-trip trades                       |
| `avg_trade_pnl`     | float  | Mean net PnL per trade                                            |
| `avg_win`           | float  | Mean PnL of winning trades                                        |
| `avg_loss`          | float  | Mean PnL of losing trades                                         |
| `best_trade`        | float  | Largest single-trade PnL                                          |
| `worst_trade`       | float  | Smallest single-trade PnL (most negative)                         |
| `total_commission`  | float  | Sum of all commissions paid                                       |
| `exposure_pct`      | float  | Fraction of bars spent in a position                              |

JSON serialization requirements:
- All `float` values must be Python `float`, not `numpy.float64`.
- All `int` values must be Python `int`, not `numpy.int64`.
- Timestamps must be ISO 8601 strings, not `datetime` or `Timestamp` objects.
- Use explicit conversion: `float(value)`, `int(value)`, `ts.isoformat()`.

### 7. Output Assembly

The engine's `run()` method returns a `BacktestResult` (from `shared/contracts.py`) containing:
- `trades: list[Trade]` - all completed round-trip trades
- `equity_curve: list[EquityPoint]` - equity at every bar
- `metrics: dict` - all computed metrics
- Ensure no mutation of input DataFrame during backtest execution.

---

## Files to Modify

| File                  | Change                                                           |
|-----------------------|------------------------------------------------------------------|
| `backtest/engine.py`  | Audit determinism, verify next-bar execution, harden float ops  |
| `backtest/fills.py`   | Verify seeded slippage, document commission model               |
| `backtest/metrics.py` | Add missing metrics, ensure JSON-serializable output types      |

## Files to Create

| File                           | Purpose                                       |
|--------------------------------|-----------------------------------------------|
| `tests/test_determinism.py`    | 5-run identical-output determinism test       |
| `tests/test_backtest_engine.py`| Engine logic tests (signals, fills, equity)   |

---

## Test Plan

### Determinism Tests (`tests/test_determinism.py`)

1. **Byte-identical results**: Run the same strategy on the same data 5 times. Serialize each `BacktestResult` to JSON. Assert all 5 JSON strings are identical (not just equivalent - byte-identical).
2. **Seed isolation**: Run two backtests with different seeds, verify results differ. Run two backtests with the same seed, verify results match.
3. **Cross-process determinism**: Run backtest in a subprocess via `subprocess.run`, compare output to in-process result.

### Engine Logic Tests (`tests/test_backtest_engine.py`)

4. **Next-bar execution**: Create a signal function that always returns BUY at bar 0. Verify the fill occurs at bar 1's open price, not bar 0's close.
5. **Signal at last bar**: Signal BUY at the final bar. Verify no trade is opened (no next bar for fill).
6. **Long-only enforcement**: Signal SELL while FLAT. Verify no trade occurs and no error is raised.
7. **No pyramiding**: Signal BUY while already LONG. Verify position size does not change.
8. **Equity curve length**: Verify equity curve has exactly `len(df)` points (one per bar).
9. **Equity curve values**: For a known sequence of trades, manually compute expected equity at each bar and compare.
10. **Commission deduction**: Verify total PnL = sum(trade net PnL) = final_equity - initial_capital.

### Metrics Tests

11. **Zero trades**: Run a strategy that never signals. Verify `num_trades=0`, `total_return=0`, `sharpe_ratio=0`, `win_rate=0`.
12. **All winning trades**: Verify `win_rate=1.0`, `profit_factor=inf`, `avg_loss=0`.
13. **Known values**: For a hand-computed scenario with 3 trades, verify every metric matches expected values.

---

## Risks and Mitigations

| Risk                                      | Likelihood | Impact | Mitigation                                              |
|-------------------------------------------|-----------|--------|---------------------------------------------------------|
| Float precision drift across platforms    | Medium    | High   | Consistent rounding; test on CI (Linux); document precision guarantees |
| Timezone-dependent behavior in timestamps | Low       | High   | All timestamps stored as UTC; no local timezone conversion in engine |
| numpy type leakage in JSON output         | Medium    | Medium | Explicit `float()` / `int()` conversion; add assertion in tests |
| Slippage model producing unrealistic fills| Low       | Low    | Cap slippage at 1% of price; log warning if exceeded |
| Large equity curves consuming memory      | Low       | Medium | Equity points are lightweight dataclasses; only concern for 1M+ bars |

---

## Dependencies

- **Upstream:** T10 (data loader provides the input DataFrame)
- **Downstream:** T40 (pipeline orchestrates engine execution), T60 (frontend displays results)
- **Frozen:** `shared/contracts.py` defines `BacktestResult`, `Trade`, `EquityPoint` schemas

---

## Acceptance Criteria

- [ ] 5 identical runs produce byte-identical JSON output
- [ ] Signal at bar[i] always fills at bar[i+1].open (verified by test)
- [ ] Signal function never receives data beyond bar[i] (verified by lookahead test)
- [ ] All 16 metrics computed and JSON-serializable
- [ ] No `numpy.float64` or `numpy.int64` types in output
- [ ] Zero-trade edge case handled gracefully
- [ ] All tests pass with `pytest tests/test_determinism.py tests/test_backtest_engine.py -v`
