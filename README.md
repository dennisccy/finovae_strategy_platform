# Finovae Strategy Platform

A React + TypeScript application for the Finovae crypto backtesting platform. Provides a chat-based interface for entering natural language trading strategies and displays comprehensive backtest results including equity curves, performance metrics, and trade lists.

## Overview

Finovae enables traders to:
- Write trading strategies in natural language
- Backtest strategies against historical market data
- Analyze performance with key metrics (Sharpe ratio, Sortino ratio, max drawdown, etc.)
- Visualize equity curves and drawdown overlays
- Review detailed trade execution logs
- Compare multiple strategy runs
- Run walk-forward validation to detect overfitting (rolling IS/OOS windows, WFE score, combined OOS equity curve)

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts for equity curves and performance visualization
- **API Communication**: Fetch API with custom hooks

## Quick Start

### Prerequisites
- Node.js (v16 or higher)
- npm or yarn

### Installation & Development

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.example .env

# Start development server
npm run dev
# Opens on http://localhost:5173
```

### Build for Production

```bash
# Build the project
npm run build

# Preview production build locally
npm run preview

# Run linting
npm run lint
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```
VITE_API_URL=http://localhost:8000
```

Leave `VITE_API_URL` empty to use Vite's dev proxy for a local backend.

## Project Structure

```
frontend/src/
├── components/          # React components
│   ├── ChatPanel.tsx    # Natural language strategy input
│   ├── ResultsPanel.tsx # Backtest results display
│   ├── EquityChart.tsx  # Equity curve visualization
│   └── ...
├── hooks/
│   └── useBacktest.ts   # API communication & state management
├── App.tsx              # Main application component
└── index.css            # Global styles
```

## Architecture

### UI Layout

- **Left Panel**: Chat interface for entering natural-language strategy descriptions with parameter controls
  - Trading symbol
  - Timeframe (e.g., 1h, 4h, 1d)
  - Date range selection
  - Initial capital

- **Right Panel**: Results display
  - Equity curve with drawdown overlay
  - Performance metrics summary
  - Trade execution list

### Frontend-Backend Communication

The `useBacktest.ts` hook manages API communication with the backend:

**Request** (POST `/api/run-backtest`):
```json
{
  "natural_language": "Buy when RSI < 30, sell when RSI > 70",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 10000
}
```

**Response**:
```json
{
  "success": true,
  "run_id": "uuid",
  "result": {
    "metrics": { "sharpe": 1.5, "max_drawdown": 0.25, ... },
    "equity_curve": [...],
    "trades": [...]
  },
  "strategy_spec": { ... }
}
```

## Key Features

- ✅ Natural language strategy input
- ✅ Real-time backtest execution with SSE streaming
- ✅ Interactive equity curve visualization
- ✅ Comprehensive performance metrics with 5-category rating system
- ✅ Detailed trade history
- ✅ Multi-session tabs with persistent state
- ✅ Auto-run and parallel worker support
- ✅ Walk-forward validation (overfitting detection)
- ✅ Responsive mobile-friendly design

## Walk-Forward Validation (v0.10)

After running a backtest, open any completed iteration's detail view. The **Walk-Forward Analysis** section appears above the rating panel and is expanded by default. Configure IS and OOS window lengths (default: 6 months IS / 3 months OOS) and click **Run Walk-Forward**.

Results include:
- **Aggregate metrics**: Combined OOS return, OOS Sharpe, OOS win rate, max drawdown
- **WFE badge**: Walk-Forward Efficiency (OOS Sharpe / IS Sharpe) — shown on the iteration card and in the detail header. Green ≥ 0.5, yellow 0.3–0.5, red < 0.3
- **Per-window table**: IS/OOS periods, returns, Sharpe ratios, and trade counts for each window
- **Combined OOS equity curve**: All OOS windows chained and compounded into a single curve

Walk-forward results are persisted with the session (OOS equity curves downsampled for storage efficiency).

### Auto-run WF gate

When Auto Run promotes a candidate that beats the baseline score, it first runs walk-forward validation on that candidate. If the WFE is below 0.3 (likely overfit), the candidate is discarded and the baseline is kept. This prevents Auto Run from locking onto in-sample overfit strategies.

### AI suggestions with OOS context

When walk-forward results are available for an iteration, they are included in the insights generation request. The AI factors in OOS performance when ranking suggestions — strategies with low WFE receive suggestions that prioritise reducing parameter sensitivity and improving robustness.

## Related Repositories

- **Backend API**: `finovae_strategy_platform_api`
  - Handles strategy compilation, backtesting engine, and data management

## Contributing

When working with this codebase, refer to `CLAUDE.md` for detailed development guidelines.