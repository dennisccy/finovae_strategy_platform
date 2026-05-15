# Finovae Strategy API

Backend service for the Finovae crypto backtesting platform. Converts natural language trading strategy descriptions into executable Python code using the Claude API, then backtests them against historical Binance OHLCV data.

## Quick start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run API server
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest -v
pytest --cov=. --cov-report=html   # with coverage
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/generate-strategy` | Generate a strategy script from natural language (Claude API) |
| `POST` | `/api/execute-backtest` | Run the backtest engine on a previously generated script |
| `POST` | `/api/execute-walk-forward` | Run walk-forward validation on a strategy script (SSE stream) |
| `POST` | `/api/generate-insights` | Generate AI improvement suggestions from backtest results |
| `POST` | `/api/run-backtest` | Combined generate + execute in one call _(deprecated)_ |
| `GET` | `/api/runs` | List all backtest run history |
| `GET` | `/api/runs/{run_id}` | Get specific run details |
| `GET` | `/api/symbols` | Available trading pairs |
| `GET` | `/api/timeframes` | Supported candle intervals |

### Generate strategy request

```json
{
  "natural_language": "Buy when EMA 9 crosses above EMA 21, sell on the reverse crossover",
  "symbol": "BTCUSDT",
  "timeframe": "4h",
  "start_date": "2024-01-01",
  "end_date": "2024-06-01",
  "previous_script_code": null,
  "previous_backtest_metrics": null,
  "allow_short": false,
  "leverage": 1.0
}
```

### Execute backtest request

```json
{
  "script_code": "import pandas as pd\n\nclass Strategy:\n    ...",
  "symbol": "BTCUSDT",
  "timeframe": "4h",
  "start_date": "2024-01-01",
  "end_date": "2024-06-01",
  "initial_capital": 10000
}
```

### Response envelope

```json
{
  "success": true,
  "run_id": "...",
  "result": {
    "total_return": 0.23,
    "equity_curve": [...],
    "trades": [...],
    "max_drawdown": 0.08
  },
  "rating": {
    "overall": 3.4,
    "profitability": {...},
    "risk_resistance": {...},
    "risk_reward": {...},
    "win_rate_ev": {...},
    "liquidity": {...}
  },
  "model_used": "claude-haiku-4-5-20251001",
  "errors": []
}
```

## Architecture

```
finovae_strategy_platform_api/
├── shared/
│   ├── contracts.py      # FROZEN v0.1 data contracts — DO NOT MODIFY
│   └── schemas.py        # Pydantic schemas mirroring contracts
├── data/
│   ├── binance_client.py # Binance REST API client
│   ├── loader.py         # OHLCV fetch + file-based Parquet cache (.cache/ohlcv/)
│   └── validation.py     # Gap / duplicate / monotonicity checks
├── strategy/
│   ├── script_generator.py  # NL → Python Strategy class (Claude API, prompt-cached)
│   └── market_analyzer.py   # OHLCV regime detection for prompt context
├── backtest/
│   ├── engine.py         # Next-bar execution loop; SL/TP path model; sub-bar resolution
│   ├── fills.py          # Slippage and commission models
│   ├── metrics.py        # Sharpe, Sortino, max drawdown, win rate, etc.
│   ├── rating.py         # RatingCalculator — 5-category rating vs buy-and-hold benchmark
│   └── walk_forward.py   # Walk-forward validation — rolling IS/OOS windows, WFE, combined OOS equity
├── backend/
│   ├── api.py            # FastAPI endpoints
│   ├── pipeline.py       # Orchestrates the full generate → validate → fetch → backtest flow
│   └── sandbox.py        # RestrictedPython executor for strategy code
└── tests/
```

### Pipeline flow

1. **ScriptGenerator** — Claude API converts NL to a `Strategy` class (single-turn, prompt-cached). Auto-downgrades to Haiku for refinement iterations. Generated scripts include `symbol` and `timeframe` class attributes matching the requested trading pair and timeframe (both required by the trading client).
2. **Sandbox validation** — RestrictedPython ensures scripts cannot perform file I/O, network calls, or any unsafe operation.
3. **Data fetching** — `OHLCVLoader` pulls OHLCV bars from Binance with Parquet file cache. For strategies with SL/TP, a higher-resolution sub-bar dataset is also fetched.
4. **Backtest execution** — `engine.run()` uses next-bar execution (signal at bar N → fill at bar N+1 open). SL/TP exits use an intra-bar path model (bullish: open→low→high→close; bearish: open→high→low→close). When sub-bar resolution data is available, it walks the constituent bars for precise exit detection.
5. **Rating** — `RatingCalculator` computes all 5 categories post-hoc against a buy-and-hold benchmark derived from the same OHLCV data. Liquidity metrics are cached across iterations within a session.
6. **Walk-Forward Validation** _(on-demand or auto-run gate)_ — `run_walk_forward()` splits the full date range into rolling IS+OOS windows (default 6 months IS / 3 months OOS). Data is fetched once; each window compiles fresh IS and OOS strategy instances to prevent state pollution. Per-window Sharpe ratios are used to compute the Walk-Forward Efficiency (WFE = mean OOS Sharpe / mean IS Sharpe). Progress streamed via SSE. Auto-run uses WFE as a gate — candidates with WFE < 0.3 are rejected as likely overfit.
7. **Insights** _(on-demand)_ — `InsightsGenerator.generate()` produces a 5-sentence summary and 10 ranked improvement suggestions via Claude API. When walk-forward results are present, OOS metrics and WFE label are included in the prompt so the AI can factor in out-of-sample performance.

### Walk-forward validation

Walk-forward validation splits the backtest date range into rolling in-sample (IS) + out-of-sample (OOS) windows and tests whether OOS performance tracks IS performance — the standard overfitting check used by professional quants.

**Algorithm** (rolling windows, step = `oos_months`):
```
Window 1: IS [start, start+is_months)   → OOS [start+is_months, start+is_months+oos_months)
Window 2: IS [start+oos_months, ...)    → OOS [...]
... stop when OOS end > full_end
```

**Key design decisions:**
- Full OHLCV dataset fetched **once**, sliced per window via `bisect` (O(log N))
- Strategy sandbox compiled **once**; fresh IS and OOS instances created per window to prevent indicator state from leaking across windows
- `asyncio.to_thread()` wraps synchronous `engine.run()` calls so SSE progress events flush in real time
- WFE = `mean(oos_sharpes) / mean(is_sharpes)` — healthy strategies score > 0.5
- Combined OOS equity curve is compounded across windows (each window scaled to start at the previous window's ending equity); drawdowns are recalculated over the full combined curve

**SSE stream** (`POST /api/execute-walk-forward`):
```
data: {"type":"status","phase":"walk_forward","wf_window":1,"wf_total":10}
data: {"type":"status","phase":"walk_forward","wf_window":2,"wf_total":10}
...
data: {"type":"result","success":true,"result":{"num_windows":10,"wfe":0.74,...}}
```

**Request**:
```json
{
  "script_id": "...",
  "script_code": "...",
  "symbol": "BTC/USDT",
  "timeframe": "4h",
  "start_date": "2020-01-01",
  "end_date": "2024-01-01",
  "initial_capital": 10000,
  "is_months": 6,
  "oos_months": 3,
  "max_windows": null
}
```

**Result fields**:

| Field | Description |
|-------|-------------|
| `windows` | Per-window IS/OOS metrics (return, Sharpe, trade count, OOS equity curve) |
| `num_windows` | Number of completed windows |
| `wfe` | Walk-Forward Efficiency (OOS Sharpe / IS Sharpe); ≥ 0.5 is healthy |
| `combined_oos_return` | Total return across all chained OOS windows |
| `combined_oos_sharpe` | Annualized Sharpe of the combined OOS equity curve |
| `combined_oos_win_rate` | Aggregate OOS win rate across all windows |
| `combined_oos_max_drawdown` | Max drawdown of the combined OOS equity curve |
| `combined_oos_equity` | Full chained OOS equity curve (downsampled to 200 pts in storage) |
| `errors` | Non-fatal window errors (windows with < 2 trades are skipped) |

### Script generator token optimisations

- **Single-turn**: All tool results (market analysis, risk rules, trading plan) are pre-filled into the user message — no multi-turn overhead.
- **Prompt caching**: System prompt uses `cache_control: ephemeral` for Anthropic cache hits.
- **Model routing**: First generation uses Sonnet; refinement iterations auto-downgrade to Haiku.
- **Context-aware rules**: Only the relevant rules section (first-gen vs refinement, long-only vs allow-short) is included per request.

### Frozen contracts (`shared/contracts.py`)

The `shared/contracts.py` data classes are frozen at v0.1. New fields are added additively to avoid breaking the frontend contract. Core types: `OHLCV`, `Trade`, `EquityPoint`, `BacktestResult`, `StrategySpec`.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for strategy generation |
| `HOST` | No | Server bind address (default `0.0.0.0`) |
| `PORT` | No | Server port (default `8000`) |
| `CORS_ORIGINS` | No | Comma-separated allowed frontend origins |
| `DEBUG` | No | Enable debug mode (default `false`) |

## Generated strategy interface

Every generated script follows this interface:

```python
import numpy as np
import pandas as pd

class Strategy:
    name = "Strategy Name"
    description = "One-sentence description"
    symbol = "BTC/USDT"       # must match the requested trading pair

    stop_loss_pct    = 0.03   # 3% stop-loss
    take_profit_pct  = 0.06   # 6% take-profit (>= 2x stop_loss_pct)
    position_size_pct = 0.01  # 1% of account per trade

    timeframe = "4h"          # must match the requested trading timeframe

    def setup(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute and attach indicator columns."""
        return df

    def signal(self, df: pd.DataFrame, i: int) -> int:
        """Return 1 (buy), -1 (sell/exit), 0 (hold), or 2 (flatten)."""
```

The `symbol` and `timeframe` attributes are consumed by the trading client (`finovae_trading_client`). `symbol` removes the need for a `--symbols` CLI flag — the trading pair is embedded in the script itself. `timeframe` configures the data pipeline for the correct bar period, ensuring paper trading executes signals at the same frequency as the backtest.
