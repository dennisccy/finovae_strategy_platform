# Finovae Strategy Platform — Frontend

React + TypeScript UI for the Finovae crypto backtesting platform. Describes trading strategies in plain English, iterates on them through a chat-like interface, and visualises backtest results (equity curve, metrics, trade list, rating breakdown).

## Quick start

```bash
cd frontend

# Install dependencies
npm install

# Development server (http://localhost:5173)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

## Environment

Copy `.env.example` to `.env`:

```dotenv
VITE_API_URL=http://localhost:8000
```

Leave `VITE_API_URL` empty to use Vite's dev proxy or same-origin deployment.

## Architecture

```
frontend/src/
├── App.tsx                        # Root: session tab management
├── main.tsx
├── components/
│   ├── SessionPicker.tsx          # Dropdown: live sessions + archive
│   ├── SessionContainer.tsx       # Per-session wrapper (hidden via display:none when inactive)
│   ├── BacktestConfigBar.tsx      # Symbol / timeframe / date range / capital controls
│   ├── ActivityLog.tsx            # Per-session event feed
│   ├── ActivityLogEntry.tsx
│   ├── IterationPanel.tsx         # Sidebar: iteration history cards
│   ├── IterationCard.tsx
│   ├── IterationDetailView.tsx    # Expanded view: script source (Diff / Full toggle)
│   ├── ChartContainer.tsx
│   ├── EquityChart.tsx            # Recharts equity curve + drawdown overlay
│   ├── ResultsPanel.tsx           # Metrics + trades + rating tabs
│   ├── MetricsCard.tsx
│   ├── TradesTable.tsx
│   ├── StrategyDisplay.tsx
│   ├── ScriptEditorModal.tsx      # Manual script editing
│   ├── RatingPanel.tsx            # Top-level rating container
│   └── rating/
│       ├── ProfitabilityTab.tsx
│       ├── RiskResistanceTab.tsx
│       ├── RiskRewardTab.tsx
│       ├── WinRateEvTab.tsx
│       ├── LiquidityTab.tsx
│       ├── StarRating.tsx
│       ├── BarComparison.tsx
│       ├── MonthlyHeatmap.tsx
│       ├── ScatterPlot.tsx
│       └── CategoryHeader.tsx
├── hooks/
│   └── useBacktest.ts             # All API state, session persistence, abort control
├── utils/
│   └── scriptDiff.ts              # LCS-based line diff for iteration comparison
└── data/
    └── strategyPrompts.ts         # Suggested prompt examples
```

## Key concepts

### Multi-session workspace

Multiple independent backtest sessions run simultaneously. Each session is identified by a UUID and persisted in `localStorage` under the key `finovae_session_<uuid>`. The tab list is stored in `finovae_session_tabs`. Completed sessions can be archived and revisited via the session picker.

`SessionContainer` mounts once per live session and remains mounted (hidden via `display: none`) even when another session is active — keeping any in-progress backtest running in the background.

### `useBacktest(sessionId)` hook

Central state machine for a single session. Manages:
- Generating and executing backtest iterations via the API
- Aborting in-flight requests when a new generation starts
- Persisting session state to `localStorage` (equity curve downsampled to 300 pts, trades capped at 200)
- Exposing `LiveSessionStatus` for the session picker status dot

### Iteration panel and script diff

Each backtest run is an `IterationNode` stored in the session. The iteration panel shows a card per run with `maxDrawdown` and `changeSummary`. Selecting an iteration opens `IterationDetailView`, which shows the full strategy script with a **Diff / Full** toggle — the diff is computed against the previous completed iteration using `scriptDiff.ts` (LCS-based line differ).

### Rating panel

Displays a five-category strategy rating (Profitability, Risk Resistance, Risk/Reward, Win Rate EV, Liquidity) computed by the API against a buy-and-hold benchmark. Each category has a dedicated tab with charts and star scores.

## API contract

The hook communicates with the backend via two endpoints:

```
POST /api/generate-strategy   → generates Claude script + validates
POST /api/execute-backtest    → runs backtest engine on generated script
```

Both are called in sequence per iteration. `useBacktest` aborts the previous in-flight request when a new generation is triggered.

## Tech stack

| Package | Role |
|---------|------|
| React 18 | UI framework |
| TypeScript 5 | Type safety |
| Vite 5 | Dev server + build |
| Tailwind CSS 3 | Styling |
| Recharts 2 | Equity curve and charts |
| Prism.js | Syntax highlighting in script editor |
| lucide-react | Icons |
