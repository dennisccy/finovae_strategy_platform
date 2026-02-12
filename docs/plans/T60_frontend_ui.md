# T60: Frontend UI Shell + Chat -> Run -> Results Integration

**Agent:** A5 (Frontend React+TS+Vite)
**Status:** Draft
**Priority:** User-facing (depends on T40 API)

---

## Objective

Build the React + TypeScript frontend with a split-panel layout: a chat/input panel on the left for entering natural language strategies and configuring parameters, and a results panel on the right displaying metrics, equity charts, trade history, and strategy details. Integrate with the backend API via the `useBacktest` hook and support run history navigation.

---

## Current State

- Frontend scaffolded with React 18, TypeScript, Vite, Tailwind CSS, and Recharts.
- `frontend/src/components/` contains existing component files (ChatPanel, ResultsPanel, EquityChart, etc.).
- `frontend/src/hooks/useBacktest.ts` manages API communication.
- `frontend/src/App.tsx` is the main application component.
- Backend API runs at `http://localhost:8000`.

---

## Plan

### 1. Layout Architecture (`App.tsx`)

Split-panel responsive layout:

```
+------------------------------------------+
|            Header / App Title             |
+------------------+-----------------------+
|                  |                       |
|   Chat Panel     |   Results Panel       |
|   (left, 40%)    |   (right, 60%)        |
|                  |                       |
|   - NL Input     |   - Tab Navigation    |
|   - Config       |   - Metrics Summary   |
|   - Submit       |   - Equity Chart      |
|   - Run History  |   - Trades Table      |
|                  |   - Strategy Spec     |
|                  |   - Generated Code    |
|                  |                       |
+------------------+-----------------------+
```

**Responsive behavior:**
- Desktop (>= 1024px): side-by-side panels
- Tablet (768-1023px): stacked panels, results below input
- Mobile (< 768px): full-width stacked, collapsible sections

### 2. Chat Panel (`components/ChatPanel.tsx`)

#### Strategy Input
- Large textarea for natural language strategy description.
- Placeholder text with example: "Buy when 20-day SMA crosses above 50-day SMA, sell when it crosses below."
- Character count display (max 2000 characters).
- Submit button with loading state (spinner + "Compiling strategy...").

#### Configuration Controls
- **Symbol selector**: Dropdown populated from `GET /api/symbols`.
- **Timeframe selector**: Dropdown populated from `GET /api/timeframes`.
- **Date range**: Start date and end date pickers (HTML5 date inputs).
  - Default start: 1 year ago from today.
  - Default end: today.
  - Validation: end must be after start; range <= 5 years.
- **Initial capital**: Number input with default 10,000. Min 100, max 10,000,000.

#### Input Validation (Client-Side)
- Strategy text: required, non-empty after trim, <= 2000 chars.
- Symbol: required, must be from API list.
- Timeframe: required, must be from API list.
- Dates: required, valid range.
- Capital: required, within bounds.
- Display inline validation errors below each field.

#### Run History
- Collapsible section showing past runs.
- Each entry shows: strategy name (truncated), symbol, date, total return (color-coded green/red).
- Clicking a history entry loads that run's results into the Results Panel.
- Data fetched from `GET /api/runs`.

### 3. Results Panel (`components/ResultsPanel.tsx`)

Tab-based navigation with four tabs:

#### Tab 1: Metrics (`components/MetricsSummary.tsx`)

Grid layout displaying key metrics:

```
+------------------+------------------+
| Total Return     | Sharpe Ratio     |
| +15.3%           | 1.82             |
+------------------+------------------+
| Max Drawdown     | Sortino Ratio    |
| -8.2%            | 2.14             |
+------------------+------------------+
| Win Rate         | Profit Factor    |
| 62.5%            | 2.3              |
+------------------+------------------+
| Total Trades     | Avg Trade PnL    |
| 48               | $31.90           |
+------------------+------------------+
```

- Color coding: positive returns green, negative red.
- Tooltips explaining each metric on hover.
- Conditional formatting: Sharpe > 1 green, < 0 red. Max drawdown severity coloring.

#### Tab 2: Equity Chart (`components/EquityChart.tsx`)

Recharts `ComposedChart` with:

- **Primary axis**: Equity curve as `Line` (blue).
- **Secondary area**: Drawdown overlay as `Area` (red, semi-transparent, inverted).
- **X-axis**: Timestamps (formatted by timeframe - daily shows dates, hourly shows date+time).
- **Y-axis left**: Equity value in dollars.
- **Y-axis right**: Drawdown percentage.
- **Tooltip**: Shows date, equity value, drawdown %, and any trade that occurred.
- **Trade markers**: Small dots on the equity line where trades occurred (green for buy, red for sell).
- **Zoom**: Brush component at bottom for selecting date range.
- **Reference line**: Horizontal line at initial capital level.

Performance considerations for large datasets:
- If equity curve has > 2000 points, downsample for rendering (every Nth point).
- Use `isAnimationActive={false}` to skip animation on large datasets.
- Memoize chart data transformation with `useMemo`.

#### Tab 3: Trades Table (`components/TradesTable.tsx`)

Sortable, paginated table:

| Column       | Type     | Sortable | Format                        |
|-------------|----------|----------|-------------------------------|
| #           | int      | Yes      | Trade number                  |
| Entry Date  | datetime | Yes      | YYYY-MM-DD HH:mm             |
| Exit Date   | datetime | Yes      | YYYY-MM-DD HH:mm             |
| Entry Price | float    | Yes      | $XX,XXX.XX                    |
| Exit Price  | float    | Yes      | $XX,XXX.XX                    |
| Quantity    | float    | No       | X.XXXX                        |
| Gross PnL   | float    | Yes      | +$XXX.XX / -$XXX.XX (colored)|
| Net PnL     | float    | Yes      | +$XXX.XX / -$XXX.XX (colored)|
| Return %    | float    | Yes      | +X.XX% / -X.XX% (colored)    |
| Duration    | string   | Yes      | Xd Xh                        |

- Default sort: by entry date descending (most recent first).
- Pagination: 20 trades per page.
- Row click: highlights corresponding trade on equity chart (if tab is visible).
- Summary row at bottom: totals for Gross PnL, Net PnL, and average Return %.

#### Tab 4: Strategy Details (`components/StrategyDetails.tsx`)

Two sub-sections:

**Compiled Strategy Spec:**
- Display StrategySpec as a formatted, readable summary (not raw JSON).
- Show: strategy name, description, indicators used, entry conditions, exit conditions, position sizing.
- Each indicator shown as a badge/chip with its parameters.
- Conditions shown as human-readable expressions.

**Generated Code:**
- Syntax-highlighted Python code display.
- Use a `<pre><code>` block with Tailwind typography classes.
- Copy-to-clipboard button.
- Optional: collapsible section (default collapsed if user prefers summary view).

### 4. useBacktest Hook (`hooks/useBacktest.ts`)

```typescript
interface UseBacktestReturn {
    // State
    isLoading: boolean;
    error: string | null;
    result: BacktestResponse | null;

    // Actions
    runBacktest: (request: BacktestRequest) => Promise<void>;
    clearResults: () => void;

    // Run history
    runs: RunSummary[];
    loadRun: (runId: string) => Promise<void>;
    refreshRuns: () => Promise<void>;
}

function useBacktest(): UseBacktestReturn {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<BacktestResponse | null>(null);
    const [runs, setRuns] = useState<RunSummary[]>([]);

    const runBacktest = async (request: BacktestRequest) => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/run-backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(request),
            });
            const data = await response.json();
            if (data.success) {
                setResult(data);
                refreshRuns();  // Update run history
            } else {
                setError(data.errors?.join('\n') || 'Unknown error');
            }
        } catch (e) {
            setError('Failed to connect to server');
        } finally {
            setIsLoading(false);
        }
    };

    // ... loadRun, refreshRuns, clearResults
}
```

**API base URL configuration:**
- Use Vite environment variable: `VITE_API_URL` defaulting to `http://localhost:8000`.
- Configure proxy in `vite.config.ts` for development:
  ```typescript
  server: {
      proxy: {
          '/api': 'http://localhost:8000'
      }
  }
  ```

### 5. TypeScript Types (`types/index.ts`)

```typescript
interface BacktestRequest {
    natural_language: string;
    symbol: string;
    timeframe: string;
    start_date: string;     // YYYY-MM-DD
    end_date: string;       // YYYY-MM-DD
    initial_capital: number;
}

interface BacktestResponse {
    success: boolean;
    run_id?: string;
    result?: BacktestResult;
    strategy_spec?: StrategySpec;
    generated_code?: string;
    errors?: string[];
}

interface BacktestResult {
    trades: Trade[];
    equity_curve: EquityPoint[];
    metrics: Record<string, number>;
}

interface Trade {
    entry_timestamp: string;
    exit_timestamp: string;
    entry_price: number;
    exit_price: number;
    quantity: number;
    gross_pnl: number;
    net_pnl: number;
    commission: number;
}

interface EquityPoint {
    timestamp: string;
    equity: number;
    drawdown: number;
}

interface StrategySpec {
    name: string;
    description: string;
    indicators: Indicator[];
    entry_conditions: Condition[];
    exit_conditions: Condition[];
    position_sizing: PositionSizing;
}

interface RunSummary {
    run_id: string;
    timestamp: string;
    strategy_name: string;
    symbol: string;
    timeframe: string;
    total_return: number;
    num_trades: number;
    sharpe_ratio: number;
}
```

### 6. Loading and Error States

**Loading state:**
- Full-panel overlay on Results Panel with spinner.
- Progress steps shown: "Compiling strategy..." -> "Fetching data..." -> "Running backtest..." -> "Computing metrics..."
- Disable submit button during loading.

**Error state:**
- Error banner at top of Results Panel (red background, white text).
- Specific error messages from API (compilation errors, data errors, etc.).
- Dismiss button to clear error.
- Suggestion to modify strategy if compilation failed.

**Empty state:**
- Results Panel shows placeholder when no run has been executed.
- Prompt: "Enter a trading strategy in natural language and click Run Backtest to see results."
- Example strategies as clickable chips that populate the input.

### 7. Styling and Theme

- Tailwind CSS utility classes throughout.
- Color palette: dark navy header, white/light gray panels, green/red for PnL.
- Font: system font stack (`font-sans` in Tailwind).
- Consistent spacing: `p-4` for panel padding, `gap-4` for grid gaps.
- Shadows: `shadow-sm` for cards, `shadow-md` for elevated panels.

---

## Files to Modify

| File                                    | Change                                               |
|-----------------------------------------|------------------------------------------------------|
| `frontend/src/App.tsx`                  | Split-panel layout, tab state management            |
| `frontend/src/hooks/useBacktest.ts`     | Add run history, loading states, error handling     |
| `frontend/src/components/ChatPanel.tsx` | Strategy input, config controls, run history        |
| `frontend/src/components/ResultsPanel.tsx` | Tab navigation, conditional rendering           |
| `frontend/src/components/EquityChart.tsx`  | Recharts implementation with drawdown overlay    |

## Files to Create

| File                                          | Purpose                                    |
|-----------------------------------------------|--------------------------------------------|
| `frontend/src/components/MetricsSummary.tsx`  | Metrics grid display                      |
| `frontend/src/components/TradesTable.tsx`     | Sortable, paginated trades table          |
| `frontend/src/components/StrategyDetails.tsx` | Strategy spec + generated code display    |
| `frontend/src/types/index.ts`                 | TypeScript interfaces for API types       |

---

## Test Plan

### Component Rendering Tests

1. **ChatPanel renders**: All form fields present, submit button visible.
2. **ChatPanel validation**: Submit with empty strategy shows error. Submit with invalid dates shows error.
3. **ResultsPanel empty state**: Shows placeholder when no results.
4. **ResultsPanel with data**: All four tabs render correctly with mock data.
5. **MetricsSummary**: All 8 metric cards render with correct formatting and colors.
6. **EquityChart**: Chart renders with mock equity curve data. Handles empty data gracefully.
7. **TradesTable**: Table renders trades. Sorting by each column works. Pagination works.
8. **StrategyDetails**: Spec displayed in readable format. Code block renders with copy button.

### Hook Integration Tests

9. **useBacktest loading state**: `isLoading` is true during API call, false after.
10. **useBacktest success**: Result is set on successful response.
11. **useBacktest error**: Error message set on failed response.
12. **useBacktest run history**: Runs list populated from API.
13. **useBacktest load specific run**: Loads full run data by ID.

### Integration Tests

14. **Full flow**: Enter strategy -> submit -> loading -> results displayed.
15. **Run history click**: Click history entry -> results panel updates.
16. **Responsive layout**: Panels stack correctly at tablet breakpoint.

---

## Risks and Mitigations

| Risk                                              | Likelihood | Impact | Mitigation                                              |
|---------------------------------------------------|-----------|--------|---------------------------------------------------------|
| Large equity curve data causing DOM performance   | High      | Medium | Downsample to max 2000 points for chart; virtualize if needed |
| Responsive layout breaking on edge screen sizes   | Medium    | Low    | Test at standard breakpoints; use Tailwind responsive utilities |
| API response mismatch with TypeScript types       | Medium    | Medium | Runtime type validation or zod schema; match types to backend contracts |
| Recharts rendering performance with many trades   | Medium    | Medium | Disable animation; use `shouldUpdate` optimization     |
| CORS issues in development                        | Low       | Low    | Vite proxy configuration handles dev; CORS middleware on backend |
| Stale run history after new backtest              | Low       | Low    | Auto-refresh after successful run; pull-to-refresh option |

---

## Dependencies

- **Upstream:** T40 (all API endpoints must be available)
- **Libraries:** React 18, TypeScript, Vite, Tailwind CSS, Recharts
- **Dev tools:** ESLint, Vite dev server with HMR

---

## Acceptance Criteria

- [ ] Split-panel layout renders correctly at desktop, tablet, and mobile widths
- [ ] Strategy input form validates all fields before submission
- [ ] Loading state shows progress through pipeline steps
- [ ] Metrics tab displays all key metrics with correct formatting
- [ ] Equity chart renders with drawdown overlay and trade markers
- [ ] Trades table is sortable by all sortable columns and paginated
- [ ] Strategy details show readable spec and syntax-highlighted code
- [ ] Run history loads from API and clicking an entry shows that run's results
- [ ] Error states display descriptive messages from API
- [ ] Empty state guides user with placeholder text and example strategies
- [ ] `npm run build` completes without TypeScript or build errors
- [ ] `npm run lint` passes without errors
