# T50 — QA Gates: Determinism, Lookahead, Sandbox Tests

**Agent:** A6 (Quant QA/Audit)
**Owns:** `/tests/**`
**Phase:** 2 (QA Gates)
**Status:** PLAN — awaiting A0 approval
**Depends on:** T20 (backtest engine), T30 (strategy compiler), T40 (sandbox runner)

---

## Objective

Build the QA gate test suite that must pass before any release. Three categories of tests form an absolute veto gate: if any fail, the release is blocked.

---

## Test Categories

### 1. Determinism Tests (`tests/test_determinism.py`)

**Goal:** Prove that identical inputs produce byte-identical outputs across 5 consecutive runs.

**Test Cases:**
| # | Test | Method |
|---|------|--------|
| D1 | Same NL strategy → identical StrategySpec | Run compiler 5x, compare JSON |
| D2 | Same StrategySpec → identical generated code | Run codegen 5x, compare string |
| D3 | Same code + data → identical trades list | Run engine 5x, compare trade-by-trade |
| D4 | Same code + data → identical equity curve | Run engine 5x, compare point-by-point |
| D5 | Same code + data → identical metrics | Run engine 5x, compare all metric values |
| D6 | Seeded slippage produces identical fills | Verify RNG seed controls fill prices |

**Comparison Method:**
- Serialize all outputs to JSON with `sort_keys=True`
- SHA-256 hash each run's output
- Assert all 5 hashes are identical
- On failure: print first diff location for debugging

**Edge Cases:**
- Float comparison: use exact equality (not approximate) since determinism is the goal
- Timestamp format: ensure consistent ISO 8601 serialization
- Empty strategy (zero trades): must still produce identical empty results

### 2. Lookahead/Leakage Tests (`tests/test_lookahead.py`)

**Goal:** Prove that the signal function cannot access future data and that execution uses next-bar model.

**Test Cases:**
| # | Test | Method |
|---|------|--------|
| L1 | DataFrame slicing prevents future access | Signal at bar i receives df[:i+1] only |
| L2 | Signal cannot modify the DataFrame | Pass df, verify no mutations after signal call |
| L3 | Next-bar execution timing | Signal at bar[i] → fill at bar[i+1] open price |
| L4 | No future price in trade entry | entry_price == bar[i+1].open, not bar[i].close |
| L5 | No future price in trade exit | exit_price == bar[j+1].open where j is exit signal bar |
| L6 | Indicator warmup doesn't leak | First N bars (warmup period) produce hold signals |

**Method:**
- Create a synthetic dataset where future bars have distinctive values (e.g., prices 10x higher)
- Write a "cheating" strategy that tries to access future data
- Verify the cheating strategy cannot outperform random (proving it can't see future)
- Instrument engine.py to log exactly which slice is passed to signal()

**Synthetic Data Design:**
```
Bars 0-49: prices in range [100, 110]
Bars 50-99: prices in range [1000, 1100]  (10x jump)
```
A strategy signaling at bar 49 should NOT know about the jump at bar 50.

### 3. Sandbox Escape Tests (`tests/test_sandbox.py`)

**Goal:** Prove that RestrictedPython blocks all dangerous operations.

**Test Cases:**
| # | Test | Attack Vector | Expected |
|---|------|--------------|----------|
| S1 | `import os` | Direct import | SecurityError / blocked |
| S2 | `__import__('os')` | Builtin import | SecurityError / blocked |
| S3 | `open('/etc/passwd')` | File read | SecurityError / blocked |
| S4 | `open('/tmp/x', 'w')` | File write | SecurityError / blocked |
| S5 | `exec('import os')` | Dynamic exec | SecurityError / blocked |
| S6 | `eval('__import__("os")')` | Dynamic eval | SecurityError / blocked |
| S7 | `import subprocess` | Subprocess | SecurityError / blocked |
| S8 | `import socket` | Network | SecurityError / blocked |
| S9 | `while True: pass` | Infinite loop | Timeout (30s) |
| S10 | `[0] * (10**9)` | Memory bomb | MemoryError or killed |
| S11 | `getattr(obj, '__class__')` | Dunder access | Blocked |
| S12 | `().__class__.__bases__[0].__subclasses__()` | Class traversal | Blocked |
| S13 | Legitimate numpy/pandas code | Normal strategy | Succeeds |
| S14 | `signal(df, i) -> int` returns valid values | Correct interface | Succeeds |

**Method:**
- Each test wraps a malicious code string in the sandbox executor
- Assert that execution raises the expected exception type
- S13-S14 verify that legitimate code still works (no false positives)

---

## Test Infrastructure

### Fixtures
- `sample_ohlcv_df`: 100-bar synthetic OHLCV DataFrame with known values
- `sample_strategy_code`: Simple MA crossover signal function (known correct)
- `synthetic_future_data`: Dataset with distinctive future values for lookahead tests
- `sample_backtest_request`: Complete BacktestRequest with all fields filled

### Markers
```python
@pytest.mark.determinism   # Determinism tests
@pytest.mark.lookahead     # Lookahead/leakage tests
@pytest.mark.sandbox       # Sandbox security tests
@pytest.mark.gate          # All gate tests (must pass for release)
```

### Running
```bash
# All gate tests
pytest tests/ -m gate -v

# Individual categories
pytest tests/test_determinism.py -v
pytest tests/test_lookahead.py -v
pytest tests/test_sandbox.py -v

# With coverage
pytest tests/ -m gate --cov=. --cov-report=html
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `tests/test_determinism.py` | Enhance | Add D1-D6 tests, SHA-256 comparison |
| `tests/test_lookahead.py` | Enhance | Add L1-L6 tests, synthetic data |
| `tests/test_sandbox.py` | Enhance | Add S1-S14 tests |
| `tests/conftest.py` | Create | Shared fixtures, markers |
| `tests/fixtures/` | Create | Sample data files |

---

## Acceptance Criteria

- [ ] All D1-D6 determinism tests pass (5 runs each, identical hashes)
- [ ] All L1-L6 lookahead tests pass (no future data accessible)
- [ ] All S1-S14 sandbox tests pass (all attacks blocked, legitimate code works)
- [ ] Zero false positives (legitimate strategy code must execute successfully)
- [ ] Test coverage for backtest/engine.py >= 90%
- [ ] Test coverage for backend/sandbox.py >= 90%
- [ ] All tests run in < 60 seconds total
- [ ] Gate marker `pytest -m gate` runs all critical tests

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| RestrictedPython bypass via new Python version | High | Pin Python version; test on CI with exact version |
| Float non-determinism across platforms | Medium | Test on target platform; document platform requirements |
| Timeout test is slow (30s per test) | Low | Use shorter timeout for tests (2s); test timeout mechanism separately |
| Class traversal attack evolves | Medium | Regularly update escape test suite; follow RestrictedPython advisories |

---

## Veto Power

A6 has **veto power** over releases. If any gate test fails:
1. Release is blocked
2. Failing agent (A2/A3/A4) is notified with specific failure details
3. Fix must be verified by re-running full gate suite
4. A6 signs off on the fix before release proceeds
