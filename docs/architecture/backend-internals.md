# Finovae Strategy Platform -- Architecture Overview

**Deliverable:** A1 / T02
**Status:** Living document -- update on every module-boundary change.

---

## System Overview

Finovae Strategy Platform is a crypto backtesting platform that compiles natural
language trading strategy descriptions into executable Python code using the
Claude API, then backtests them against historical Binance OHLCV data. The
frontend presents a conversational interface (chat panel) alongside a results
dashboard (equity chart, metrics cards, trades table, run history).

**Tech stack:**

| Layer    | Technology                                        |
|----------|---------------------------------------------------|
| Backend  | Python 3.11+, FastAPI, RestrictedPython, Anthropic SDK |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Data     | Binance REST API, pandas, numpy, Parquet cache    |

---

## Core Pipeline Flow

The `BacktestPipeline` (backend/pipeline.py) orchestrates the following stages
in strict sequential order:

```
Stage  Module                     Input                  Output
-----  -------------------------  ---------------------  --------------------------
  1    Frontend chat panel        User types NL strategy POST /api/run-backtest
  2    strategy/compiler.py       NL text                StrategySpec JSON
  3    strategy/codegen.py        StrategySpec           Python signal function (str)
  4    backend/sandbox.py         Code string            Validated code / rejection
  5    data/loader.py             Symbol, timeframe,     pd.DataFrame (OHLCV)
                                  date range
  6    data/validation.py         DataFrame              Validated DataFrame / errors
  7    backtest/engine.py         Code + DataFrame       Trades, equity curve
  8    backtest/metrics.py        Trades, equity curve   Sharpe, Sortino, drawdown, ...
  9    Frontend results panel     BacktestResult JSON    Charts, cards, tables
```

### Stage Details

1. **User Input** -- The React frontend collects a natural language strategy
   description plus parameters (symbol, timeframe, date range, initial capital)
   and sends a POST to `/api/run-backtest`.

2. **NL Compilation** (`strategy/compiler.py`) -- The Claude API receives a
   system prompt defining the output JSON schema and the allowed indicator
   whitelist. It returns a `StrategySpec` containing name, description,
   indicators, entry/exit conditions, and position sizing.

3. **Code Generation** (`strategy/codegen.py`) -- The `StrategySpec` is
   deterministically translated into a Python source string that defines a
   `signal(df: pd.DataFrame, i: int) -> int` function returning 1 (buy),
   -1 (sell), or 0 (hold).

4. **Sandbox Validation** (`backend/sandbox.py`) -- RestrictedPython compiles
   and validates the generated code. Dangerous operations are blocked at compile
   time. See the Security Model section below.

5. **Data Loading** (`data/loader.py`) -- OHLCV candle data is fetched from the
   Binance REST API (or a local CSV fallback). Results are cached as Parquet
   files under `.cache/ohlcv/` keyed by `{symbol}_{timeframe}_{start}_{end}`.

6. **Data Validation** (`data/validation.py`) -- The DataFrame is checked for
   timestamp gaps, duplicate rows, monotonicity violations, and null values.
   Failures abort the run with a descriptive error.

7. **Backtest Execution** (`backtest/engine.py`) -- The engine iterates over
   each bar, calls the signal function with a DataFrame sliced to prevent
   lookahead (`df[:i+1]`), and executes trades at the **next bar's open**
   (next-bar execution model). Positions are long-only. A deterministic random
   seed controls slippage sampling.

8. **Metrics Calculation** (`backtest/metrics.py`) -- From the trade list and
   equity curve the engine computes: Sharpe ratio, Sortino ratio, max drawdown,
   win rate, profit factor, total return, CAGR, and per-trade statistics.

9. **Results Display** (frontend) -- The React SPA renders an equity chart
   (Recharts), metrics summary cards, a trades table, and a run history sidebar.

---

## Data Flow Diagram (ASCII)

```
 User
  |
  |  NL strategy + params
  v
+-----------------+     POST /api/run-backtest     +------------------+
|                 | -------------------------------->                  |
|    Frontend     |                                 |   FastAPI (api)  |
|  React SPA      |<--------------------------------|                  |
|                 |     BacktestResult JSON         |   backend/       |
+-----------------+                                 |   pipeline.py    |
                                                    +--------+---------+
                                                             |
                          +----------------------------------+----------------------------------+
                          |                                  |                                  |
                          v                                  v                                  v
                 +--------+---------+             +----------+----------+            +----------+----------+
                 |  NL Compilation  |             |   Data Loading      |            |  Sandbox Validation  |
                 |  strategy/       |             |   data/loader.py    |            |  backend/sandbox.py  |
                 |  compiler.py     |             |   data/validation.py|            +----------+----------+
                 +--------+---------+             +----------+----------+                       |
                          |                                  |                                  |
                          | StrategySpec                     | pd.DataFrame (OHLCV)             | Validated code
                          v                                  |                                  |
                 +--------+---------+                        |                                  |
                 |  Code Generation |                        |                                  |
                 |  strategy/       |                        |                                  |
                 |  codegen.py      |                        |                                  |
                 +--------+---------+                        |                                  |
                          |                                  |                                  |
                          | Python signal fn (str)           |                                  |
                          v                                  v                                  v
                 +--------+----------------------------------------------------------+---------+
                 |                       Backtest Engine                                        |
                 |                       backtest/engine.py                                     |
                 |                                                                              |
                 |   for each bar i:                                                            |
                 |     sig = signal(df[:i+1], i)   <-- no lookahead                             |
                 |     execute at bar[i+1] open    <-- next-bar model                           |
                 +-------------------------------------+----------------------------------------+
                                                       |
                                                       | Trades + EquityCurve
                                                       v
                                              +--------+---------+
                                              |  Metrics Calc    |
                                              |  backtest/       |
                                              |  metrics.py      |
                                              +--------+---------+
                                                       |
                                                       | BacktestResult
                                                       v
                                                  Response JSON
```

---

## Module Boundaries

Each top-level directory has a single owner and a clear responsibility boundary.

| Directory    | Owner | Responsibility                                                      | Key constraint                                    |
|--------------|-------|---------------------------------------------------------------------|---------------------------------------------------|
| `shared/`    | A0    | FROZEN data contracts (`contracts.py`, `schemas.py`)                | Changes require lead (A0) approval                |
| `data/`      | --    | CSV/API loader, normalization, validation                           | No business logic; pure data I/O                  |
| `strategy/`  | --    | NL -> StrategySpec -> Code pipeline; owns indicator whitelist       | No execution; produces code strings only           |
| `backtest/`  | --    | Engine, fills/slippage model, metrics                               | Receives code string + data, returns BacktestResult|
| `backend/`   | --    | FastAPI API, sandbox execution, run storage                         | Orchestrates pipeline; owns HTTP surface           |
| `frontend/`  | --    | React SPA: chat UI (left), results (right)                          | Calls `/api/*` endpoints only                      |
| `tests/`     | QA    | All test suites (lookahead, determinism, sandbox, integration)      | QA has veto power on releases                      |

### Rules

- Modules may only import from `shared/` and their own directory.
- `strategy/` MUST NOT import from `backtest/` or `backend/`.
- `backtest/` MUST NOT import from `strategy/` or `backend/`.
- `data/` MUST NOT import from any module except `shared/`.
- `backend/` orchestrates all other modules but does not contain trading logic.

---

## Contract Dependencies

`shared/contracts.py` is the single source of truth for all inter-module data
types. The dependency graph is:

```
shared/contracts.py
  |
  |-- OHLCV                 used by  data/, backtest/engine
  |-- StrategySpec           used by  strategy/compiler, strategy/codegen, backend/api
  |-- Trade                  used by  backtest/engine, backtest/metrics
  |-- EquityPoint            used by  backtest/engine, backtest/metrics
  |-- BacktestResult         used by  backtest/metrics, backend/api, frontend (JSON)
  |-- ConditionOperator      used by  strategy/compiler, strategy/codegen
  |-- PositionSizingType     used by  strategy/compiler, strategy/codegen
  |-- TradeType              used by  backtest/engine
  |-- CompileConstraints     used by  strategy/compiler
  |
  +-- shared/schemas.py      Pydantic wrappers for API serialization
        |
        used by  backend/api
```

**Freeze policy:** Any change to `shared/contracts.py` requires:
1. Written approval from A0 (architecture lead).
2. Impact analysis across all consuming modules.
3. Matching updates to `shared/schemas.py` and frontend TypeScript types.

---

## Security Model

### RestrictedPython Sandbox (`backend/sandbox.py`)

All user-generated strategy code executes inside a RestrictedPython sandbox.

**Allowed:**
- `numpy` (aliased as `np`)
- `pandas` (aliased as `pd`)
- `math` standard library module
- Basic Python builtins: arithmetic, comparisons, list/dict/tuple operations
- The `signal(df, i)` function signature

**Blocked (compile-time rejection):**
- `__import__` -- no dynamic imports
- `open()` -- no file I/O
- `exec`, `eval` -- no dynamic code execution
- `os`, `sys` -- no system access
- Network access (socket, urllib, requests, etc.)
- Attribute access to dunder methods beyond the safe set
- `getattr`, `setattr`, `delattr` with arbitrary targets

**Runtime protections:**
- **Timeout:** 30-second limit per `signal()` invocation (Unix: SIGALRM;
  Windows: polling thread).
- **DataFrame slicing:** The engine passes `df[:i+1]` so the signal function
  physically cannot access future bars.
- **Next-bar execution:** Even if a signal is generated at bar `i`, the trade
  executes at bar `i+1` open, eliminating same-bar lookahead.

### Threat Model Summary

| Threat                        | Mitigation                                |
|-------------------------------|-------------------------------------------|
| Arbitrary code execution      | RestrictedPython compile-time blocks      |
| File system access            | `open()` and `os` blocked                 |
| Network exfiltration          | All network modules blocked               |
| Infinite loop / resource abuse| 30s timeout per signal call               |
| Lookahead bias (data snooping)| DataFrame slice + next-bar execution      |
| Non-deterministic results     | Controlled random seed for slippage       |

---

## Key Invariants

These invariants are enforced by the test suite and MUST hold for every release.
QA has veto power if any invariant is broken.

### 1. Determinism
Same inputs produce identical outputs across runs.
- Controlled random seed in fills model.
- No reliance on wall-clock time, process IDs, or memory addresses.
- Tested by `tests/test_determinism.py`.

### 2. No Lookahead
`signal(df, i)` only ever sees `df[:i+1]` (bars 0 through i inclusive).
- The engine slices the DataFrame before each call.
- No global state leaks future data.
- Tested by `tests/test_lookahead.py`.

### 3. Sandbox Containment
No strategy code can escape the RestrictedPython environment.
- Dangerous builtins and modules are removed at compile time.
- Tested by `tests/test_sandbox.py`.

### 4. Next-Bar Execution
A signal generated at bar `i` always executes at bar `i+1` open.
- Prevents same-bar lookahead even if the signal function is correct.
- Matches real-world order latency semantics.

---

## API Surface

| Method | Endpoint              | Purpose                              |
|--------|-----------------------|--------------------------------------|
| POST   | `/api/run-backtest`   | Submit NL strategy, receive results  |
| GET    | `/api/runs`           | List all historical runs             |
| GET    | `/api/runs/{run_id}`  | Retrieve a specific run's results    |
| GET    | `/api/symbols`        | Available trading pairs              |
| GET    | `/api/timeframes`     | Supported candle intervals           |

### Request (POST /api/run-backtest)
```json
{
  "natural_language": "Buy when RSI crosses below 30, sell when above 70",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 10000
}
```

### Response
```json
{
  "success": true,
  "run_id": "uuid",
  "result": {
    "metrics": { "sharpe": 1.42, "max_drawdown": -0.12, "..." : "..." },
    "equity_curve": [ { "timestamp": "...", "equity": 10234.5 } ],
    "trades": [ { "type": "BUY", "price": 42000, "..." : "..." } ]
  },
  "strategy_spec": { "name": "RSI Mean Reversion", "..." : "..." },
  "errors": []
}
```

---

## Caching

OHLCV data is cached locally to avoid redundant Binance API calls:
- **Location:** `.cache/ohlcv/`
- **Format:** Apache Parquet
- **Key:** `{symbol}_{timeframe}_{start}_{end}.parquet`
- Cache hits skip network entirely; cache misses fetch and persist.

---

*End of architecture document.*
