# Finovae Strategy Platform

An AI-assisted crypto strategy lab. Describe a trading strategy in plain English; Finovae
compiles it to a structured spec, generates and sandboxes the signal code, backtests it
against real Binance data, and returns an institutional-grade report — with optional
walk-forward validation and AI improvement insights.

It is not a bot runner. It is a strategy lab with a strong, skeptical evaluation loop and
a UI that makes every step of the workflow visible.

## Who it is for

- A solo systematic / retail-quant trader who wants to go from idea to a validated
  backtest fast, without writing backtest-engine code.
- An AI tinkerer who wants a UI over LLM strategy compilation plus an honest critique loop
  (walk-forward, overfit detection, AI insights).

## What you can do

Enter a natural-language strategy and parameters (symbol, timeframe, date range, initial
capital). Finovae:

1. Compiles the description into a structured `StrategySpec` (OpenAI `gpt-5.4-mini` by default; Claude selectable).
2. Generates a `signal(df, i) -> int` function and runs it inside a RestrictedPython
   sandbox.
3. Fetches Binance OHLCV (Parquet-cached) and backtests with a next-bar-open fill model
   (commission + slippage).
4. Returns metrics (Sharpe, Sortino, max drawdown, profit factor, win rate), an equity
   curve, a trade log, and a 5-category rating.
5. On request, runs walk-forward validation (rolling IS/OOS windows, WFE) and generates
   ranked, OOS-aware AI improvement suggestions.

Runs are multi-session and persisted to the filesystem; every run is addressable by
`run_id`. See [`docs/architecture/overview.md`](docs/architecture/overview.md) for the
full component and endpoint list.

## Guiding principles

- **Sandboxed execution, always.** LLM-generated code runs only inside RestrictedPython —
  no file I/O, network, `exec`/`eval`, `__import__`, `open`, or `os`.
- **No lookahead.** A signal at bar `i` fills at bar `i+1` open. The engine enforces it.
- **Deterministic.** Slippage is seeded; identical inputs produce identical outputs.
- **Frozen contracts.** `apps/backend/shared/contracts.py` is a reviewed, stable interface.
- **No database.** Parquet OHLCV cache + file-backed session/run store — reproducible and
  inspectable by design.

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 16+ and npm
- An `OPENAI_API_KEY` (the default model is `gpt-5.4-mini`); `ANTHROPIC_API_KEY` is
  optional — only if you pick a Claude model (backend boots without them; the AI
  endpoints need the key)

### One-time backend setup

```bash
python3 -m venv apps/backend/.venv      # Python 3.11+
apps/backend/.venv/bin/pip install -U pip
apps/backend/.venv/bin/pip install -e apps/backend
apps/backend/.venv/bin/pip install -r apps/backend/requirements.txt
cp apps/backend/.env.example apps/backend/.env   # then set OPENAI_API_KEY (required); ANTHROPIC_API_KEY optional
cd apps/frontend && npm install                  # links the next-vite-shim
```

### Start the platform

```bash
./scripts/dev.sh            # starts backend + frontend together (prints both URLs)
# or individually:
./scripts/start-backend.sh
./scripts/start-frontend.sh
```

`./scripts/dev.sh` computes per-project offset ports and wires the frontend's `/api`
proxy to the backend automatically. Open the frontend URL it prints.

## Using the platform

1. Enter a strategy in natural language and set the symbol, timeframe, date range, and
   initial capital.
2. Submit — read the equity curve, metrics, rating, and trade list.
3. Open a completed iteration's detail view to run **walk-forward validation** (WFE badge
   + per-window table + combined OOS curve).
4. Request **AI insights** for ranked improvement suggestions (OOS-aware when
   walk-forward data exists).
5. Browse prior runs from session history; each is restorable by `run_id`.

## Documentation

| File | Contents |
|---|---|
| [`docs/goal.md`](docs/goal.md) | Vision, target users, success criteria, non-goals, constraints, must-have journeys, anti-goals |
| [`docs/architecture/overview.md`](docs/architecture/overview.md) | Component tables, API endpoints, data model, capability status, decisions |
| [`docs/architecture/backend-internals.md`](docs/architecture/backend-internals.md) | Deep backend internals: pipeline, sandbox security model, data flow |
| `apps/frontend/CLAUDE.md` | Frontend development guidance |
| `apps/backend/CLAUDE.md` | Backend development guidance |

## Project layout

```
apps/
  backend/     FastAPI — NL compile, codegen, sandbox, backtest, metrics, walk-forward (main.py = uvicorn entry)
  frontend/    Vite + React 18 — the platform UI (tools/next-shim bridges the shared scripts)
incredible_auto_dev/   AI multi-agent dev-chain (git subtree; remote auto_dev, --squash)
docs/          goal.md + architecture/ (overview, backend-internals)
CLAUDE.md config scripts templates tests   symlinks → incredible_auto_dev/
```

## Current status

Frontend and backend are functional and merged into a single `apps/` monorepo wired to
the `incredible_auto_dev` automation framework (phase-1 complete). The platform does
**not** do live or paper trading — it is a backtesting and strategy-evaluation lab.
