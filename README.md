# Finovae Strategy Platform

A React + TypeScript application for the Finovae crypto backtesting platform. Provides a chat-based interface for entering natural language trading strategies and displays comprehensive backtest results including equity curves, performance metrics, trade lists, and strategy ratings.

## Overview

Finovae enables traders to:
- Write trading strategies in plain English and generate executable code automatically
- Backtest strategies against historical Binance OHLCV data
- Analyse performance with a 5-category rating system (profitability, risk resistance, risk/reward, win-rate EV, liquidity)
- Visualise equity curves, drawdown overlays, and trade execution logs
- Run multiple sessions in parallel and compare iterations side-by-side
- Extract strategies from YouTube trading videos
- Validate strategies with institutional-grade robustness tools (v0.9)

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts for equity curves and performance visualisation
- **API Communication**: Custom hooks (`useBacktest`, `useVideoStrategy`)

## Quick Start

### Prerequisites
- Node.js v16 or higher
- npm or yarn

### Installation & Development

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000 (or leave empty for Vite proxy)

# Start development server
npm run dev
# Opens on http://localhost:5173
```

### Build for Production

```bash
cd frontend
npm run build      # TypeScript compile + Vite build
npm run preview    # Preview production build locally
npm run lint       # ESLint
```

## Environment Configuration

```
VITE_API_URL=http://localhost:8000
```

Leave `VITE_API_URL` empty to use Vite's dev proxy for a local backend.

---

## v0.9 Robustness Features — What You See in the UI

The backend now runs seven analytical phases automatically. Here is what each phase adds to the UI experience.

### Phase 1 — Data Integrity

**Impact on results**: Before any backtest runs, the backend scans the generated strategy code for lookahead bias. If the code references future bars (e.g. `df.shift(-1)`), the backtest is **blocked** and an error is shown instead of results.

**In the UI**: A data integrity panel appears in the backtest response. It shows:
- Overall quality score (0–1)
- List of lookahead warnings with the exact line number and pattern
- Survivorship bias warnings (volume gaps, zombie asset detection)
- Whether the data passed or failed the quality gate

A quality score below 0.7 is a signal to review the data or strategy. A blocked backtest means the result would have been meaningless.

---

### Phase 2 — Enhanced Transaction Costs

**Impact on results**: When `cost_config` is provided in the backtest request, the fill model switches from a flat slippage rate to a realistic model that accounts for volatility-scaled spread, market impact, and tiered commissions. Returns will generally be **lower** than with the default model, especially for:
- High-frequency strategies (more fills = more impact per trade)
- Large position sizes relative to bar volume (liquidity cap kicks in)
- Volatile periods (spread widens proportionally to ATR)

**In the UI**: No separate panel — the change is reflected in all standard metrics (total return, Sharpe, equity curve). You can compare a baseline run (default costs) against an enhanced-cost run to see the realistic performance drag.

---

### Phase 3 — Complexity Controls

**Impact on results**: Every backtest now includes a `complexity` object. Complex strategies (many indicators, deep nesting, many conditions) receive a Sharpe penalty of up to 30%, producing a **complexity-adjusted Sharpe** that penalises over-engineering.

**In the UI**: A complexity panel shows:
- Indicator count, parameter count, condition count, max nesting depth
- Raw complexity score
- Penalty factor (0%–30%)
- Complexity-adjusted Sharpe alongside the raw Sharpe

A strategy with a raw Sharpe of 2.0 but 30% penalty has an adjusted Sharpe of 1.4 — you can compare this adjusted figure across iterations to see if simplification actually improves robustness.

---

### Phase 4 — Train/Test Split (`POST /api/train-test`)

**Impact on results**: Runs the exact same strategy on two non-overlapping data segments. The degradation ratio tells you how much performance dropped out-of-sample.

**In the UI** (requires explicit API call): A split results panel shows:
- In-sample metrics (train period) vs out-of-sample metrics (test period) side-by-side
- Sharpe comparison: IS Sharpe vs OOS Sharpe
- Degradation ratio (e.g. 0.85 = OOS return is 85% of IS return — good; 0.2 = likely curve-fitted)
- Two separate equity curves on the same axis

A degradation ratio below 0.5 is a red flag for curve-fitting. A ratio above 0.8 suggests genuine signal.

---

### Phase 5 — Walk-Forward Framework (`POST /api/walk-forward`)

**Impact on results**: Instead of one train/test split, the strategy is tested across many rolling folds. The combined OOS equity curve simulates what a live deployment would have looked like.

**In the UI** (requires explicit API call): A walk-forward panel shows:
- Per-fold IS vs OOS Sharpe table
- Combined OOS equity curve (the "real" performance you'd have experienced)
- IS Sharpe vs OOS Sharpe comparison across all folds
- Return degradation ratio
- Number of folds and window sizes

A strategy with consistently positive OOS Sharpe across all folds has genuine edge. Wide IS vs OOS gaps on individual folds indicate regime sensitivity.

---

### Phase 6 — Parameter Robustness (`POST /api/param-search`)

**Impact on results**: Tests many parameter combinations and identifies whether a strategy's performance is narrowly tuned or broadly robust.

**In the UI** (requires explicit API call): A parameter search panel shows:
- Heatmap of Sharpe ratio across 2D parameter grid (e.g. `sma_period` vs `rsi_period`)
- Best parameter combination and its PSR (Probabilistic Sharpe Ratio, 0–1)
- Plateau detected / not detected — a plateau means ≥30% of the parameter space achieves Sharpe within 80% of the best
- Full list of tested combinations with Sharpe, return, drawdown, and PSR per point

PSR < 0.95 means the strategy may not beat random noise. A narrow Sharpe spike with no plateau = over-fitting. A broad plateau = the parameters genuinely matter less, which is desirable.

---

### Phase 7 — AI Diagnostic Improvement Loop

**Impact on results and suggestions**: Diagnostics are automatically computed after every backtest and passed to the AI insight generator, producing more targeted suggestions.

**In the UI**: A diagnostics panel in the backtest results shows:
- **Market regime breakdown**: What fraction of the backtest was trending up/down/ranging, and the strategy's cumulative return in each regime
- **Win/loss streaks**: Max win streak, max loss streak, current streak — useful for identifying overconfidence in a win run
- **Trade timing heatmap**: Average return by hour of day and by day of week — highlights if the strategy has a time-of-day edge or avoids certain days
- **Drawdown clusters**: Groups of consecutive drawdown events — helps distinguish isolated bad luck from systematic regime losses
- **Avg trade duration**: Average hours the strategy is in a position

**In AI suggestions**: Instead of generic advice, the suggestions become specific — e.g.:
- "Strategy only profits in trending markets (67% of trending returns vs −3% ranging). Add a regime filter."
- "Max loss streak is 8. Consider reducing position size after 3 consecutive losses."
- "Monday trades average −1.2% return. Add a weekday filter to skip Monday entries."

**Experiment tracker** (via `GET /api/experiments/{session_id}` and `POST /api/experiments/compare`):
- Logs each iteration's before/after Sharpe, improvement percentage, and the hypothesis that motivated the change
- A/B comparison endpoint: pick two experiment IDs to get a winner determination with Sharpe delta and explanation
- Iteration chains link parent experiments to children, making it easy to trace the evolution of a strategy across many refinement cycles

---

## Project Structure

```
frontend/src/
├── components/
│   ├── rating/              # 5-category rating tab components
│   │   └── RatingPanel.tsx  # Top-level rating container
│   ├── ChatPanel.tsx        # Natural language strategy input
│   ├── ResultsPanel.tsx     # Backtest results display
│   ├── EquityChart.tsx      # Equity curve + drawdown overlay
│   ├── IterationPanel.tsx   # Per-iteration history with script diff view
│   ├── SessionContainer.tsx # Per-session wrapper (hidden when inactive)
│   └── SessionPicker.tsx    # Multi-session dropdown with status dots
├── hooks/
│   ├── useBacktest.ts       # API communication, state, session persistence
│   └── useVideoStrategy.ts  # Video URL processing hook
├── utils/
│   └── scriptDiff.ts        # LCS-based line diff for code comparison
├── App.tsx                  # Session management, tab switching
└── index.css                # Global styles
```

## Key Architecture Notes

- **Multi-session**: `useBacktest(sessionId)` supports multiple concurrent sessions; each persists to localStorage under `finovae_session_${sessionId}`.
- **Session persistence**: Equity curve downsampled to 300 points, trades capped at 200, activity log at 150 to stay within localStorage quota.
- **Script diff**: Each iteration shows a line-level diff against the previous iteration's script.
- **Rating system**: 5 categories computed against a buy-and-hold benchmark. Liquidity cached per session after first computation.
- **Video strategy**: `VideoStrategyContainer` mirrors `SessionContainer`; video sessions stored separately under `finovae_video_session_tabs`.

## Related Repository

**Backend API**: `finovae_strategy_platform_api` — handles strategy compilation, backtesting engine, data management, and all v0.9 robustness features.
