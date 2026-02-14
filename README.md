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
- ✅ Real-time backtest execution
- ✅ Interactive equity curve visualization
- ✅ Comprehensive performance metrics
- ✅ Detailed trade history
- ✅ Run history & comparison
- ✅ Responsive mobile-friendly design

## Related Repositories

- **Backend API**: `finovae_strategy_platform_api`
  - Handles strategy compilation, backtesting engine, and data management

## Contributing

When working with this codebase, refer to `CLAUDE.md` for detailed development guidelines.