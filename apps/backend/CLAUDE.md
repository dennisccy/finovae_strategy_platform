# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Finovae Strategy API is the backend service for the Finovae crypto backtesting platform. It compiles natural language trading strategy descriptions into executable Python code using Claude API, then backtests them against historical Binance data.

**Tech Stack:**
- Python 3.11+, FastAPI, RestrictedPython, Anthropic SDK
- Data: Binance REST API, pandas, numpy

## Development Commands

### Backend (Python)
```bash
# Install dependencies
pip install -e .
pip install -e ".[dev]"  # Include dev dependencies

# Run API server (from root)
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest                           # All tests
pytest tests/test_lookahead.py   # Specific test file
pytest -v                        # Verbose output
pytest --cov=. --cov-report=html # Coverage report

# Linting and type checking
ruff check .                     # Lint
ruff format .                    # Format
mypy .                           # Type check
```

### Environment Setup
Copy `.env.example` to `.env` and set:
```
ANTHROPIC_API_KEY=your_api_key_here
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
```

## Architecture Overview

### Core Pipeline Flow (backend/pipeline.py)

The `BacktestPipeline` orchestrates the complete workflow:

1. **NL Compilation** (`strategy/compiler.py`): Claude API converts natural language to `StrategySpec` JSON
2. **Code Generation** (`strategy/codegen.py`): StrategySpec → executable Python code with signal function
3. **Sandbox Validation** (`backend/sandbox.py`): RestrictedPython validates code safety
4. **Data Fetching** (`data/loader.py`): Binance API downloads OHLCV data (with file-based caching)
5. **Data Validation** (`data/validation.py`): Checks for gaps, duplicates, monotonicity
6. **Backtest Execution** (`backtest/engine.py`): Runs strategy with next-bar execution model
7. **Metrics Calculation** (`backtest/metrics.py`): Sharpe, Sortino, max drawdown, etc.

### Module Structure

```
shared/
  contracts.py      # FROZEN data contracts (see below) - DO NOT MODIFY
  schemas.py        # Pydantic schemas for API responses

data/
  binance_client.py # Binance REST API client
  loader.py         # OHLCV data fetching with caching
  validation.py     # Data quality checks

strategy/
  compiler.py       # NL → StrategySpec using Claude API
  codegen.py        # StrategySpec → Python code
  indicators.py     # Technical indicator registry

backtest/
  engine.py         # Core backtest loop with position tracking
  fills.py          # Slippage and commission models
  metrics.py        # Performance metric calculations

backend/
  api.py            # FastAPI endpoints (/api/run-backtest, /api/runs, etc.)
  pipeline.py       # Orchestrates full workflow
  sandbox.py        # RestrictedPython executor for strategy code
```

### FROZEN CONTRACTS (shared/contracts.py)

**CRITICAL:** The `shared/contracts.py` file is a frozen interface contract. Changes require architectural review. It contains:
- Data classes: `OHLCV`, `Trade`, `EquityPoint`, `BacktestResult`, `StrategySpec`
- Enums: `ConditionOperator`, `PositionSizingType`, `TradeType`
- Request/Response types for compilation and backtesting

When modifying the system, work within these contracts rather than changing them.

### Sandbox Execution (backend/sandbox.py)

Strategy code runs in a **RestrictedPython sandbox** with strict security:
- **Allowed**: numpy, pandas, basic math operations
- **Blocked**: file I/O, network access, `exec/eval`, `__import__`, `open()`, os module
- **Timeout**: 30 seconds per signal call (Unix only)
- Generated code must define a `signal(df: pd.DataFrame, i: int) -> int` function
  - Returns: 1 (buy), -1 (sell), 0 (hold)
  - Receives DataFrame sliced to current bar to prevent lookahead

### Backtest Engine (backtest/engine.py)

**Next-bar execution model**: Signal generated at bar[i] executes at bar[i+1] open to prevent lookahead bias.

Key features:
- Long-only positions
- Deterministic execution (controlled random seed for slippage)
- Equity curve tracking at each bar
- Commission and slippage modeling

### Data Caching (data/loader.py)

OHLCV data is cached in `.cache/ohlcv/` as Parquet files to avoid redundant Binance API calls. Cache key format: `{symbol}_{timeframe}_{start}_{end}.parquet`

## Testing Philosophy

The test suite focuses on **critical invariants**:

1. **Lookahead Prevention** (`test_lookahead.py`): Ensures signal function never sees future data
2. **Determinism** (`test_determinism.py`): Same inputs → same outputs (for reproducibility)
3. **Sandbox Security** (`test_sandbox.py`): Validates RestrictedPython blocks dangerous operations

When adding features, maintain these guarantees.

## API Endpoints

**Base URL**: `http://localhost:8000`

- `POST /api/run-backtest`: Main endpoint - accepts NL strategy + params, returns backtest results
- `GET /api/runs`: List all backtest run history
- `GET /api/runs/{run_id}`: Get specific run details
- `GET /api/symbols`: Available trading pairs
- `GET /api/timeframes`: Supported candle intervals

### Request/Response Format

**POST /api/run-backtest**
```json
{
  "natural_language": "Buy when RSI crosses below 30, sell when it crosses above 70",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "start_date": "2024-01-01",
  "end_date": "2024-06-01",
  "initial_capital": 10000
}
```

**Response:**
```json
{
  "success": true,
  "run_id": "...",
  "result": { "total_return": ..., "equity_curve": [...], "trades": [...] },
  "strategy_spec": { "name": ..., "indicators": [...], "conditions": [...] },
  "errors": []
}
```

## Common Patterns

### Adding a New Technical Indicator

1. Add indicator function to `strategy/indicators.py` in `INDICATOR_REGISTRY`
2. Update `CompileConstraints.allowed_indicators` in `shared/contracts.py` (requires freeze approval)
3. The code generator will automatically support it in signal functions

### Modifying Strategy Compilation

The compiler uses a **system prompt** (`strategy/compiler.py:SYSTEM_PROMPT`) to guide Claude's JSON output. The prompt defines:
- Output JSON schema (name, description, indicators, conditions, position_size)
- Available indicators from `CompileConstraints.allowed_indicators`
- Entry vs exit condition logic (AND vs OR)
- Operator types (>, <, cross_above, cross_below, etc.)

## CORS Configuration

The API supports configurable CORS origins via the `CORS_ORIGINS` environment variable (comma-separated). Default allowed origins for local development: `http://localhost:5173`, `http://localhost:3000`.

## Cross-Platform Notes

- **Windows**: Timeout mechanism in sandbox uses polling instead of SIGALRM (Unix signals unavailable)
- **Line endings**: Use LF (Unix) for Python files, handled by Git autocrlf
- **Paths**: Use forward slashes in code; os.path handles platform conversion
