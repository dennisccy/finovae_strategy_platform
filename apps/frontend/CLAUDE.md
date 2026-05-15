# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Finovae Strategy Platform Frontend — a React + TypeScript (Vite) application for the Finovae crypto backtesting platform. Provides a chat-based interface for entering natural language trading strategies and displays backtest results including equity curves, metrics, and trade lists.

This is the `apps/frontend/` package of the **finovae_strategy_platform monorepo**. The backend API is in the *same* repo at `apps/backend/` (FastAPI) — it is no longer a separate repository. The `incredible_auto_dev` dev-chain is a git subtree; the repo-root `CLAUDE.md` is a symlink to that framework's constitution, and the authoritative project context for agents is `.claude/project-template.md` + `docs/goal.md` + `docs/architecture/overview.md` at the repo root.

**Tech Stack:**
- React 18, TypeScript, Vite, Tailwind CSS, Recharts

## Development Commands

### Run the whole stack (recommended — from the repo root)
```bash
./scripts/dev.sh          # starts apps/backend (uvicorn) + apps/frontend (Vite) together
./scripts/start-frontend.sh   # frontend only
```
`./scripts/dev.sh` uses deterministic offset ports (not 5173/8000) and exports the
backend URL so the Vite `/api` proxy targets it automatically.

### Frontend only (from this package — `apps/frontend/`)
```bash
cd apps/frontend

npm install            # also links the local `next-vite-shim` (see below)
npm run dev            # Vite dev server on http://localhost:5173 (bare run)
npm run build          # tsc + vite build → dist/
npm run preview        # Preview production build
npm run lint           # ESLint
```

### The `next-vite-shim`
The shared Aplhion scripts invoke `npx next dev|build|start`. This is a Vite app,
so `apps/frontend/tools/next-shim/` provides a local `next` binary (declared as the
`next` devDependency) that translates those commands to Vite. Do **not** install real
Next.js. `vite.config.ts` reads `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_API_PORT` (exported
by the scripts) for its `/api` proxy target, falling back to `http://localhost:8000`.

### Environment Setup
`apps/frontend/.env.example` → `apps/frontend/.env`:
```
VITE_API_URL=
```
Leave `VITE_API_URL` empty for local dev — requests use relative `/api/...` paths
served through the Vite proxy (configured via the scripts' env, or :8000 by default).

## Architecture

### Frontend Structure

```
apps/frontend/
  src/
    components/     # React components (ChatPanel, ResultsPanel, EquityChart, etc.)
    hooks/          # Custom hooks (useBacktest.ts)
    App.tsx         # Main application component
  tools/next-shim/  # local `next` → Vite shim used by ../../scripts/*
  vite.config.ts    # env-driven /api proxy target
```

### Key Components

- **ChatPanel**: Chat interface for entering natural-language strategy descriptions with parameter controls (symbol, timeframe, date range, initial capital)
- **ResultsPanel**: Displays equity chart (Recharts), metrics summary, and trade list
- **EquityChart**: Recharts-based equity curve visualization with drawdown overlay
- **useBacktest hook**: Manages API communication, loading state, error handling, and run history

### Frontend-Backend Communication

The `useBacktest.ts` hook sends requests to the backend API:

```typescript
POST ${VITE_API_URL}/api/run-backtest
{
  natural_language: string,
  symbol: string,
  timeframe: string,
  start_date: date,
  end_date: date,
  initial_capital: number
}
```

Response:
```typescript
{
  success: boolean,
  run_id?: string,
  result?: BacktestResult,      // metrics, equity_curve, trades
  strategy_spec?: StrategySpec,  // parsed strategy structure
  errors?: string[]
}
```

The `VITE_API_URL` environment variable controls the API base URL. When empty, requests use relative paths (suitable for same-origin deployment or Vite proxy).

### UI Layout

- **Left panel**: Chat interface for entering natural-language strategy descriptions
- **Right panel**: Results display — equity chart, metrics summary, trade list
- Each backtest run receives a unique `run_id`
- Run history is accessible and browsable
