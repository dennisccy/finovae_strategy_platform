# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Finovae Strategy Platform Frontend — a React + TypeScript application for the Finovae crypto backtesting platform. Provides a chat-based interface for entering natural language trading strategies and displays backtest results including equity curves, metrics, and trade lists.

The backend API lives in a separate repository (`finovae_strategy_platform_api`).

**Tech Stack:**
- React 18, TypeScript, Vite, Tailwind CSS, Recharts

## Development Commands

### Frontend (React + Vite)
```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev        # Runs on http://localhost:5173

# Build and preview
npm run build      # TypeScript compile + Vite build
npm run preview    # Preview production build

# Linting
npm run lint       # ESLint
```

### Environment Setup
Copy `.env.example` to `.env` and set:
```
VITE_API_URL=http://localhost:8000
```

Leave `VITE_API_URL` empty when using Vite's dev proxy to a local backend.

## Architecture

### Frontend Structure

```
frontend/src/
  components/       # React components (ChatPanel, ResultsPanel, EquityChart, etc.)
  hooks/            # Custom hooks (useBacktest.ts)
  App.tsx           # Main application component
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
