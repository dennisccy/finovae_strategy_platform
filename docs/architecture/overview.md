# Project Architecture

## Overview

**Project:** Finovae Strategy Platform
**Stack:** FastAPI (Python 3.11+) + Vite 5 / React 18 (TypeScript) + no database (Parquet OHLCV cache + file-based session/run store)
**Description:** AI-assisted crypto strategy lab — NL → `StrategySpec` → generated signal code → RestrictedPython sandbox → Binance backtest → metrics/rating → optional walk-forward → AI insights.

> Deep backend module-by-module internals (pipeline, sandbox security model, data flow):
> see [`backend-internals.md`](./backend-internals.md).

## Components

### Backend

| Component | Path | Purpose |
|-----------|------|---------|
| ASGI entry shim | `apps/backend/main.py` | Re-exports `app` so the shared scripts' `uvicorn main:app` works |
| FastAPI app & REST API | `apps/backend/backend/api.py` | App object (`title="Finovae Strategy Platform API"`), all top-level endpoints |
| Pipeline orchestrator | `apps/backend/backend/pipeline.py` | Drives NL → spec → code → sandbox → data → backtest → metrics |
| RestrictedPython sandbox | `apps/backend/backend/sandbox.py` | Safe execution of generated `signal()` code (30s timeout) |
| Session routes & store | `apps/backend/backend/session_routes.py`, `backend/session_store.py` | `/api/sessions` CRUD, iterations, archive; file-backed persistence |
| Directions cache | `apps/backend/backend/directions_routes.py`, `backend/directions_cache.py` | Cached AI strategy "directions" |
| NL compiler | `apps/backend/strategy/compiler.py` | NL → `StrategySpec` via OpenAI `gpt-5.4-mini` (default) / Claude |
| Code generation | `apps/backend/strategy/codegen.py`, `strategy/script_generator.py` | `StrategySpec` → executable `signal()` code |
| Indicators | `apps/backend/strategy/indicators.py` | Technical-indicator registry |
| Market analysis / insights | `apps/backend/strategy/market_analyzer.py`, `strategy/insights_generator.py` | Regime detection, ranked improvement suggestions |
| Backtest engine | `apps/backend/backtest/engine.py`, `backtest/fills.py` | Next-bar-open fills, commission/slippage, equity tracking |
| Metrics & rating | `apps/backend/backtest/metrics.py`, `backtest/rating.py` | Sharpe/Sortino/drawdown/etc., 5-category rating |
| Walk-forward | `apps/backend/backtest/walk_forward.py` | Rolling IS/OOS windows, WFE |
| Data layer | `apps/backend/data/binance_client.py`, `data/loader.py`, `data/validation.py` | Binance REST, Parquet cache, quality checks |
| Contracts & schemas | `apps/backend/shared/contracts.py`, `shared/schemas.py` | FROZEN dataclasses + Pydantic API schemas |
| Vercel serverless entry | `apps/backend/api/index.py` | Serverless ASGI shim (not deployed by current root `vercel.json`) |

### Frontend

| Component | Path | Purpose |
|-----------|------|---------|
| App shell | `apps/frontend/src/App.tsx`, `src/main.tsx` | Two-panel layout, routing of state |
| Strategy input & config | `apps/frontend/src/components/` (chat / config bar) | NL entry + symbol/timeframe/date/capital controls |
| Results | `apps/frontend/src/components/` (results, equity chart, metrics, trades, rating, walk-forward) | Recharts equity curve, metrics, trade list, WFE badge |
| Sessions & iterations | `apps/frontend/src/components/` (session/iteration containers) | Multi-session tabs, iteration cards, detail views |
| API hooks | `apps/frontend/src/hooks/useBacktest.ts`, `hooks/useDirectionsCache.ts` | Backtest/SSE state, directions cache |
| API clients | `apps/frontend/src/lib/sessionApi.ts`, `lib/directionsApi.ts` | Typed fetch wrappers |
| Dev-script bridge | `apps/frontend/tools/next-shim/` | Maps `next dev|build|start` → Vite so shared Aplhion scripts drive a Vite app |

## API Endpoints

| Method | Path | Purpose | Added in Phase |
|--------|------|---------|----------------|
| GET | `/` | Root liveness | phase-1 |
| GET | `/api/health` | Health check | phase-1 |
| GET | `/api/config` | Worker/concurrency config | phase-1 |
| GET | `/api/models` | Available LLM models | phase-1 |
| GET | `/api/symbols` | Tradable Binance symbols | phase-1 |
| GET | `/api/validate-symbol` | Validate a symbol | phase-1 |
| GET | `/api/timeframes` | Supported candle intervals | phase-1 |
| GET | `/api/runs` | List backtest runs | phase-1 |
| GET | `/api/runs/{run_id}` | Get a run's detail | phase-1 |
| POST | `/api/run-backtest` | Full NL → backtest (deprecated path, still served) | phase-1 |
| POST | `/api/generate-strategy` | NL → `StrategySpec` + code | phase-1 |
| POST | `/api/execute-backtest` | Backtest a generated strategy | phase-1 |
| POST | `/api/execute-walk-forward` | Walk-forward validation (SSE) | phase-1 |
| POST | `/api/generate-insights` | AI improvement suggestions | phase-1 |
| GET/POST | `/api/directions/cache[/{direction_id}]` | Directions cache read/write | phase-1 |
| GET/POST/PUT/DELETE | `/api/sessions/...` | Sessions, iterations, activity, archive (router prefix `/api/sessions`) | phase-1 |
| GET | `/docs`, `/redoc`, `/openapi.json` | FastAPI auto-docs | phase-1 |

## Data Model

No database. Backtest inputs/outputs are FROZEN dataclasses in
`apps/backend/shared/contracts.py`; OHLCV is Parquet-cached; sessions/runs are file-backed.

| Entity | Storage | Key Fields |
|--------|---------|------------|
| `OHLCV` *(frozen)* | Parquet cache (`.cache/ohlcv/`) | timestamp, open, high, low, close, volume |
| `StrategySpec` | session/run JSON | name, description, indicators[], conditions[], position sizing |
| `Condition` / `IndicatorConfig` / `PositionSizing` | embedded in `StrategySpec` | operator, indicator params, sizing type |
| `Trade` *(frozen)* | in `BacktestResult` | entry/exit time & price, qty, pnl, commission, direction, leverage |
| `EquityPoint` *(frozen)* | in `BacktestResult` | timestamp, equity, drawdown |
| `BacktestResult` | run JSON | run_id, total_return, max_drawdown, num_trades, win_rate, sharpe, profit_factor, equity_curve[], trades[] |
| `RunRecord` / `StoredScript` | file session store | run + generated-script persistence |
| `WalkForwardWindow` / `WalkForwardResult` | session JSON | per-window IS/OOS metrics, WFE, combined OOS curve |
| `CategoryRating` / `StrategyRating` | derived | 5-category composite rating |
| Analytics: `DrawdownPeriod`, `TradeExcursion`, `MonthlyReturn`, `RollingMetric`, `HistogramBin`, `SimulatedStopLevel`, `CapacityLevel` | derived in metrics | report sub-structures |

## Key Capabilities

| Capability | Status | Phase |
|-----------|--------|-------|
| NL → `StrategySpec` compilation | complete | phase-1 |
| `StrategySpec` → signal code generation | complete | phase-1 |
| RestrictedPython sandbox execution | complete | phase-1 |
| Binance OHLCV fetch + Parquet cache | complete | phase-1 |
| Backtest engine (next-bar fills, slippage/commission) | complete | phase-1 |
| Metrics + 5-category rating | complete | phase-1 |
| Walk-forward validation (IS/OOS, WFE) | complete | phase-1 |
| AI insights (OOS-aware) | complete | phase-1 |
| Multi-session + run history (file-backed) | complete | phase-1 |
| SSE-streamed execution | complete | phase-1 |

## Architecture Decisions

| Decision | Rationale | Phase |
|----------|-----------|-------|
| No database; Parquet + file session store | Single-user research tool; reproducibility; zero infra | phase-1 |
| `shared/contracts.py` frozen | Stable interface across compiler/engine/API; changes need review | phase-1 |
| RestrictedPython sandbox | Execute LLM-generated code without RCE | phase-1 |
| Next-bar-open fills + seeded slippage | Eliminate lookahead; guarantee determinism | phase-1 |
| One backtest per worker (`Semaphore(1)`, scale via `WEB_CONCURRENCY`) | Bound CPU per process | phase-1 |
| `apps/backend/main.py` re-export shim | Satisfy shared scripts' `uvicorn main:app` contract without touching backend imports | phase-1 |
| `next-vite-shim` | Run a Vite app under the shared Next.js-shaped Aplhion scripts without forking the subtree | phase-1 |
