# T40: Sandbox Runner + /api/run-backtest + Run Persistence

**Agent:** A4 (Backend + Sandbox + Runs)
**Status:** Draft
**Priority:** Integration (blocks T60)

---

## Objective

Implement the secure sandbox execution environment for strategy code, the main `/api/run-backtest` API endpoint that orchestrates the full pipeline, and a run persistence layer that stores and retrieves backtest results.

---

## Current State

- `backend/sandbox.py` implements RestrictedPython-based code execution with security restrictions.
- `backend/api.py` defines FastAPI endpoints for backtesting and run management.
- `backend/pipeline.py` orchestrates the full workflow from NL input to backtest results.
- Run persistence uses JSON file storage.
- The sandbox allows numpy and pandas but blocks file I/O, network, imports, and eval/exec.

---

## Plan

### 1. Sandbox Execution (`backend/sandbox.py`)

#### Restricted Globals Setup

Build a safe execution environment:

```python
from RestrictedPython import compile_restricted, safe_globals, limited_builtins
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import guarded_unpack_sequence, safer_getattr

def build_restricted_globals():
    _globals = safe_globals.copy()

    # Allowed builtins (whitelist approach)
    _globals['__builtins__'] = {
        'True': True,
        'False': False,
        'None': None,
        'abs': abs,
        'bool': bool,
        'float': float,
        'int': int,
        'len': len,
        'list': list,
        'max': max,
        'min': min,
        'range': range,
        'round': round,
        'sum': sum,
        'tuple': tuple,
        'zip': zip,
        'enumerate': enumerate,
        'isinstance': isinstance,
        'dict': dict,
    }

    # Inject safe libraries
    _globals['np'] = numpy
    _globals['pd'] = pandas
    _globals['math'] = math  # only safe math functions

    # Required RestrictedPython guards
    _globals['_getiter_'] = default_guarded_getiter
    _globals['_getattr_'] = safer_getattr
    _globals['_unpack_sequence_'] = guarded_unpack_sequence
    _globals['_getitem_'] = default_guarded_getitem

    return _globals
```

#### Explicitly Blocked Operations

| Operation          | Mechanism                                     |
|--------------------|-----------------------------------------------|
| `__import__`       | Not in builtins whitelist                     |
| `open()`           | Not in builtins whitelist                     |
| `exec()` / `eval()`| Not in builtins whitelist                    |
| `os` module        | Not injected into globals                     |
| `sys` module       | Not injected into globals                     |
| `subprocess`       | Not injected into globals                     |
| `__builtins__` access | RestrictedPython guards attribute access   |
| Network access     | `socket` not available; `urllib` not imported |
| File system access | `open`, `pathlib`, `os` all unavailable       |

#### Timeout Mechanism

**Unix (SIGALRM):**
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Strategy execution exceeded 30 second limit")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)
try:
    exec(compiled_code, restricted_globals)
    result = restricted_globals['signal'](df_slice, i)
finally:
    signal.alarm(0)  # Cancel alarm
```

**Windows (threading fallback):**
```python
import threading

def run_with_timeout(fn, args, timeout=30):
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = fn(*args)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        raise TimeoutError("Strategy execution exceeded 30 second limit")
    if exception[0]:
        raise exception[0]
    return result[0]
```

#### Sandbox Runner Interface

```python
class SandboxRunner:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._globals = build_restricted_globals()

    def validate(self, code: str) -> list[str]:
        """Compile code under RestrictedPython, return list of errors."""

    def execute_signal(self, code: str, df: pd.DataFrame, bar_index: int) -> int:
        """Execute signal function for a single bar, return -1/0/1."""

    def execute_all_signals(self, code: str, df: pd.DataFrame) -> list[int]:
        """Execute signal for all bars, return list of signals."""
```

### 2. Pipeline Orchestration (`backend/pipeline.py`)

The `BacktestPipeline` orchestrates the complete flow:

```python
class BacktestPipeline:
    async def run(self, request: BacktestRequest) -> BacktestResponse:
        # Step 1: Compile NL to StrategySpec
        strategy_spec = await self.compiler.compile(request.natural_language)

        # Step 2: Generate executable code
        code = self.codegen.generate(strategy_spec)

        # Step 3: Validate code in sandbox
        errors = self.sandbox.validate(code)
        if errors:
            return BacktestResponse(success=False, errors=errors)

        # Step 4: Fetch market data
        df = await self.loader.load(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date
        )

        # Step 5: Validate data
        validation_report = self.validator.validate(df, request.timeframe)
        if not validation_report.valid:
            return BacktestResponse(success=False, errors=[...])

        # Step 6: Execute backtest
        signals = self.sandbox.execute_all_signals(code, df)
        result = self.engine.run(df, signals, request.initial_capital)

        # Step 7: Compute metrics
        metrics = self.metrics.compute(result)

        # Step 8: Persist run
        run_id = self.run_store.save(request, strategy_spec, code, result, metrics)

        return BacktestResponse(
            success=True,
            run_id=run_id,
            result=result,
            strategy_spec=strategy_spec,
            generated_code=code
        )
```

**Error Handling Strategy:**
- Each step wrapped in try/except with specific error types.
- `CompilationError` -> return with compilation error message.
- `CodeGenError` -> return with code generation error.
- `SandboxError` -> return with security violation message (do NOT expose code details).
- `DataError` -> return with data fetching/validation error.
- `TimeoutError` -> return "Strategy execution timed out".
- Generic `Exception` -> log full traceback, return sanitized "Internal error" message.

### 3. API Endpoints (`backend/api.py`)

#### POST /api/run-backtest

```python
@app.post("/api/run-backtest")
async def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """Main endpoint: NL strategy + params -> backtest results."""
    pipeline = BacktestPipeline(...)
    return await pipeline.run(request)
```

Request schema:
```json
{
    "natural_language": "Buy when RSI(14) < 30, sell when RSI(14) > 70",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 10000.0
}
```

Response schema:
```json
{
    "success": true,
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "result": {
        "trades": [...],
        "equity_curve": [...],
        "metrics": {...}
    },
    "strategy_spec": {...},
    "generated_code": "def signal(df, i): ...",
    "errors": null
}
```

#### GET /api/runs

```python
@app.get("/api/runs")
async def list_runs(limit: int = 50, offset: int = 0) -> list[RunSummary]:
    """List all backtest runs, most recent first."""
```

Returns abbreviated run records (no full equity curve):
```json
[
    {
        "run_id": "...",
        "timestamp": "2024-01-15T10:30:00Z",
        "strategy_name": "RSI Reversal",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "total_return": 0.15,
        "num_trades": 42,
        "sharpe_ratio": 1.8
    }
]
```

#### GET /api/runs/{run_id}

```python
@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> RunRecord:
    """Get full details of a specific run."""
```

Returns the complete `RunRecord` including equity curve, all trades, generated code, and strategy spec.

#### GET /api/symbols

```python
@app.get("/api/symbols")
async def get_symbols() -> list[str]:
    """Available trading pairs."""
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", ...]
```

#### GET /api/timeframes

```python
@app.get("/api/timeframes")
async def get_timeframes() -> list[str]:
    """Supported candle intervals."""
    return ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
```

### 4. Run Persistence

#### Storage Format

JSON file-based storage in `.runs/` directory:

```
.runs/
  {run_id}.json          # Full RunRecord
  index.json             # Lightweight index for list queries
```

#### RunRecord Schema

```python
@dataclass
class RunRecord:
    run_id: str                    # UUID4
    timestamp: str                 # ISO 8601 creation time
    request: BacktestRequest       # Original request parameters
    strategy_spec: StrategySpec    # Compiled strategy
    generated_code: str            # Python code that was executed
    result: BacktestResult         # Full backtest results
    metrics: dict                  # Computed metrics
    duration_ms: int               # Pipeline execution time
    errors: list[str] | None      # Any errors/warnings
```

#### RunStore Implementation

```python
class RunStore:
    def __init__(self, base_dir: str = ".runs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def save(self, record: RunRecord) -> str:
        """Save run record, update index, return run_id."""

    def get(self, run_id: str) -> RunRecord | None:
        """Load full run record by ID."""

    def list(self, limit: int = 50, offset: int = 0) -> list[RunSummary]:
        """List runs from index, sorted by timestamp desc."""

    def _update_index(self, record: RunRecord):
        """Append summary to index.json for fast listing."""
```

**Concurrency**: Use file locking (`fcntl` on Unix, `msvcrt` on Windows) for index.json updates to handle concurrent API requests.

### 5. CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Files to Modify

| File                  | Change                                                            |
|-----------------------|-------------------------------------------------------------------|
| `backend/sandbox.py`  | Harden restricted globals, verify blocked operations, add timeout |
| `backend/api.py`      | Verify all endpoints, error handling, CORS, validation           |
| `backend/pipeline.py` | Verify orchestration flow, error handling at each step           |

## Files to Create

| File                              | Purpose                                          |
|-----------------------------------|--------------------------------------------------|
| `tests/test_sandbox.py`           | Sandbox escape attempt tests                    |
| `tests/test_api.py`               | API endpoint integration tests                  |
| `tests/test_pipeline.py`          | Pipeline orchestration tests                    |

---

## Test Plan

### Sandbox Security Tests (`tests/test_sandbox.py`)

1. **Import blocked**: Code containing `import os` raises `SandboxError`.
2. **Open blocked**: Code containing `open('/etc/passwd')` raises `SandboxError`.
3. **Exec blocked**: Code containing `exec('print(1)')` raises `SandboxError`.
4. **Eval blocked**: Code containing `eval('1+1')` raises `SandboxError`.
5. **`__import__` blocked**: Code containing `__import__('os')` raises `SandboxError`.
6. **Network blocked**: Code attempting `socket.connect()` raises error.
7. **Dunder access blocked**: Code accessing `__builtins__.__dict__` raises error.
8. **Timeout enforced**: Code with `while True: pass` raises `TimeoutError` within ~30s.
9. **Valid code succeeds**: A correct signal function executes and returns -1/0/1.
10. **numpy/pandas available**: Code using `np.mean()` and `pd.Series()` executes successfully.
11. **Return value constrained**: Signal returning 5 is caught as invalid (only -1/0/1 allowed).

### API Integration Tests (`tests/test_api.py`)

12. **Valid request**: POST to `/api/run-backtest` with valid NL returns 200 with `success=true`.
13. **Missing fields**: POST with missing `natural_language` returns 422 validation error.
14. **Invalid symbol**: POST with unknown symbol returns error.
15. **Date range validation**: End date before start date returns error.
16. **List runs**: GET `/api/runs` returns array of run summaries.
17. **Get specific run**: GET `/api/runs/{id}` returns full run record.
18. **Run not found**: GET `/api/runs/nonexistent` returns 404.
19. **Symbols endpoint**: GET `/api/symbols` returns non-empty list.
20. **Timeframes endpoint**: GET `/api/timeframes` returns expected intervals.

### Pipeline Tests (`tests/test_pipeline.py`)

21. **Full pipeline success**: End-to-end test with a simple strategy.
22. **Compilation failure**: Invalid NL input returns descriptive error.
23. **Sandbox failure**: Strategy code that violates sandbox returns security error.
24. **Data fetch failure**: Invalid date range or symbol returns data error.
25. **Run is persisted**: After successful backtest, run can be retrieved by ID.

---

## Risks and Mitigations

| Risk                                        | Likelihood | Impact | Mitigation                                                |
|---------------------------------------------|-----------|--------|-----------------------------------------------------------|
| RestrictedPython bypass (sandbox escape)    | Low       | Critical| Defense-in-depth: whitelist builtins, no imports, timeout; follow RestrictedPython security advisories |
| Resource exhaustion (memory/CPU)            | Medium    | High   | Timeout enforcement; consider memory limits via `resource` module (Unix) |
| Concurrent run conflicts in persistence     | Medium    | Medium | File locking on index.json; UUID collision is negligible  |
| Large response payloads (long equity curves)| Medium    | Low    | Consider pagination or summary mode for equity curves     |
| API key exposure in error messages          | Low       | High   | Sanitize all error messages before returning to client    |

---

## Dependencies

- **Upstream:** T10 (data loader), T20 (backtest engine), T30 (strategy compiler + codegen)
- **Downstream:** T60 (frontend consumes API endpoints)
- **External:** Anthropic Claude API (for compilation step), Binance API (for data fetching)

---

## Acceptance Criteria

- [ ] All 11 sandbox security tests pass (no escape vectors)
- [ ] Timeout kills runaway code within 30-35 seconds
- [ ] `/api/run-backtest` completes end-to-end for a valid strategy
- [ ] Error responses are descriptive but do not leak internal details
- [ ] Runs are persisted and retrievable by ID
- [ ] Run listing returns correct summaries sorted by recency
- [ ] CORS allows frontend dev server origin
- [ ] All tests pass with `pytest tests/test_sandbox.py tests/test_api.py tests/test_pipeline.py -v`
