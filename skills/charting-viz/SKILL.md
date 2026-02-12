# Skill: Charting & Visualization

## Purpose

Build financial data visualizations using Recharts in React for the Finovae Strategy Platform frontend. This skill is used by **A5 (Frontend/Viz Agent)** to create clear, performant, and accessible charts for equity curves, trade markers, drawdown overlays, and performance summaries.

The frontend lives in `frontend/src/` and uses React 18, TypeScript, Vite, Tailwind CSS, and Recharts. Charts must render backtest results returned from the `/api/run-backtest` endpoint, which include equity curves (`EquityPoint[]`) and trade lists (`Trade[]`).

## Do

- Use **Recharts** (`recharts` npm package) for all chart components. It is the project's standard charting library.
- Show equity curves as a `LineChart` or `AreaChart` with timestamp on the x-axis and equity (USDT) on the y-axis.
- Show drawdown as a secondary overlay (e.g., a red-shaded `Area` below the equity line, or a separate sub-chart).
- Mark trade entries and exits on the equity chart using `ReferenceDot` or custom scatter points. Use distinct colors: green for buy entries, red for sell exits.
- Make all charts **responsive** using Recharts' `ResponsiveContainer` wrapper. Charts must resize correctly from mobile (320px) to desktop (1920px+).
- Use a consistent color scheme across all charts. Define chart colors as Tailwind CSS variables or a shared constants file.
- Label axes clearly: x-axis should show dates in a readable format (e.g., "Jan 15" or "2026-01-15"), y-axis should show currency values with appropriate precision.
- Include tooltips on hover that show: date, equity value, drawdown percentage, and any trade details at that point.
- Handle **loading states** with a skeleton or spinner while backtest results are pending.
- Handle **error states** with a clear message and retry option when the API call fails.
- Handle **empty states** gracefully: show a placeholder message when there are no results to display (e.g., "Run a backtest to see results here").
- Use `React.memo` or `useMemo` to prevent unnecessary re-renders of chart components when parent state changes unrelated to chart data.

## Don't

- Use canvas-based chart libraries (e.g., Chart.js, ECharts) without providing accessibility alternatives. Recharts renders SVG, which is inherently more accessible.
- Load the full dataset into the DOM without downsampling. For equity curves with 10,000+ points, implement downsampling (e.g., LTTB algorithm or simple nth-point sampling) to keep the DOM performant.
- Skip loading or error states. A chart that shows nothing with no explanation is a broken UI.
- Use non-deterministic animations in test environments. Disable or mock animations when running component tests to avoid flaky snapshots.
- Hard-code chart dimensions. Always use `ResponsiveContainer` with percentage-based width and a fixed minimum height.
- Use inline styles for chart colors. Centralize the color palette so it can be updated consistently.
- Render charts outside of error boundaries. A chart rendering error should not crash the entire application.
- Display raw timestamps without formatting. Always convert Unix timestamps or ISO strings to human-readable date/time.
- Ignore timezone handling. Display all times in UTC with a "(UTC)" label, matching the backtest engine's convention.

## SOP (Standard Operating Procedure)

### 1. Review Existing Chart Components

```bash
# List all chart-related components
ls frontend/src/components/*Chart* frontend/src/components/*chart* 2>/dev/null

# Read the main results panel
cat frontend/src/components/ResultsPanel.tsx

# Read existing chart components
cat frontend/src/components/EquityChart.tsx 2>/dev/null

# Check the data hook that feeds chart components
cat frontend/src/hooks/useBacktest.ts
```

### 2. Understand the Data Shape

The API returns `BacktestResult` which includes:

```typescript
interface EquityPoint {
  timestamp: string;  // ISO datetime
  equity: number;     // USDT value
  drawdown: number;   // decimal (0.05 = 5%)
}

interface Trade {
  trade_id: string;
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  pnl_percent: number;
  commission_paid: number;
}
```

### 3. Test with Multiple Data Scenarios

Verify charts render correctly with each scenario:

```bash
cd /home/user/finovae_strategy_platform/frontend

# Run frontend tests
npm test 2>/dev/null || npx vitest run 2>/dev/null

# Build to catch TypeScript errors
npm run build

# Lint
npm run lint
```

Test data scenarios (use mock data in tests):

| Scenario | Data | Expected Behavior |
|---|---|---|
| Empty data | `equity_curve: [], trades: []` | Placeholder message, no crash |
| Single point | `equity_curve: [1 point]` | Single dot or minimal chart |
| Normal data | 500 equity points, 20 trades | Full chart with trade markers |
| Large data | 50,000 equity points | Downsampled, still performant |
| Full drawdown | Equity drops to 0 | Chart handles zero values |
| Negative PnL only | All trades are losers | Red-tinted chart, no errors |

### 4. Check Responsive Behavior

```bash
# Start the dev server
cd /home/user/finovae_strategy_platform/frontend && npm run dev &

# Test at different viewport widths:
# - 320px (mobile)
# - 768px (tablet)
# - 1024px (small desktop)
# - 1920px (full desktop)
```

### 5. Accessibility Check

- Verify charts have appropriate `aria-label` attributes.
- Verify color choices have sufficient contrast (WCAG AA minimum).
- Verify tooltips are keyboard-accessible or have alternative text.
- Verify trade markers are distinguishable without color (use shape + color).

### 6. Full Regression

```bash
cd /home/user/finovae_strategy_platform/frontend
npm run build
npm run lint
npm test 2>/dev/null || npx vitest run 2>/dev/null
```

## Required Output Format

Every charting-viz task must produce:

### Component Code

```typescript
// File: frontend/src/components/EquityChart.tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area } from 'recharts';

interface EquityChartProps {
  equityCurve: EquityPoint[];
  trades: Trade[];
  isLoading: boolean;
  error?: string;
}

export const EquityChart: React.FC<EquityChartProps> = ({ ... }) => {
  // Implementation with loading, error, and empty states
  // ResponsiveContainer wrapper
  // Formatted axes and tooltips
};
```

### Screenshot / Visual Review

Provide a description or screenshot of the rendered chart showing:
- Equity curve line
- Drawdown overlay
- Trade entry/exit markers
- Tooltip on hover
- Responsive layout at mobile and desktop widths

### Accessibility Notes

```
Color Contrast:
  - Equity line (#2563EB blue): contrast ratio X.X:1 against white -> [PASS/FAIL]
  - Drawdown area (#EF4444 red): contrast ratio X.X:1 -> [PASS/FAIL]
  - Trade markers: uses shape + color for colorblind safety -> [PASS/FAIL]

Keyboard Navigation:
  - Tooltip accessible via keyboard -> [PASS/FAIL]
  - Chart has aria-label -> [PASS/FAIL]

Screen Reader:
  - Summary text provided as alt -> [PASS/FAIL]
```
