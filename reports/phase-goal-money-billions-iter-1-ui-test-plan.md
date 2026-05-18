# Phase goal-money-billions-iter-1 — UI Test Plan

**Phase:** goal-money-billions-iter-1
**Date:** 2026-05-18
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3691

---

> **Nature of this plan — read first.** Zero frontend code changed this iteration
> (`git diff HEAD -- apps/frontend` is empty). No new screen, route, component,
> button, field, or displayed data. The storage layer beneath the app changed
> (single-file Parquet OHLCV cache + durable-by-default session store). Therefore
> **every test below is a REGRESSION test of an existing journey**, plus two new
> *behavioral* assertions that are observable through the unchanged UI:
> (a) an identical warm re-run completes and is byte-identical (J-06), and
> (b) session/run history survives a backend restart with no `BACKTEST_STORE_DIR`
> set (J-02 durability). No new-feature UX exists to discover.
> Deterministic "zero re-fetch" / "cold==warm list" proofs are pytest
> (functional TC-01/TC-02) and are **not** duplicated here — the browser verifies
> *rendered journeys*, not internal fetch counts.

**App shape:** single-page app at `/`. Header = "Finovae Strategy Platform" +
"Sessions" button (top-right). Left panel = strategy chat ("Activity"). Right
panel = run history ("Iterations"). There is **no button literally labelled
"Run"**: a backtest is submitted by typing into the **"Describe a trading
strategy…"** box and pressing **Enter** (or clicking the paper-plane / send icon
button to its right), or by clicking one of the pre-built strategy cards on the
empty state.

**Symbol field note:** the journey catalog writes the symbol as `BTCUSDT`, but
the Symbol input enforces `BASE/USDT` format. Always type **`BTC/USDT`** (with
the slash) in the UI.

**Default config (if left untouched):** Symbol `BNB/USDT`, Timeframe `4h`,
Start `2020-01-01`, End `2024-01-01`, Capital `1500`, Exchange `binance`. All
tests below explicitly set the config so they do not depend on defaults, and use
a **small** range (`2023-01-01`–`2023-06-01`) so cold fetches finish quickly.

---

## Test Cases

<!-- Test IDs use UT-XX prefix to distinguish from functional test plan TC-XX IDs. -->

---

### UT-01 — App shell loads with config bar, chat, and history (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (App shell — header, `BacktestConfigBar`, `ActivityLog`, `IterationPanel`)

**Preconditions:**
- Backend and frontend running; backend reachable so model list/sessions load
- Browser open, no prior tab state required

**Steps:**
1. Navigate to `http://localhost:3691`
2. Wait for the page to fully load (model `<select>` is populated, the "Sessions" button shows a status dot)

**Expected Result:**
- The header text **"Finovae Strategy Platform"** is visible, with **"v0.3.0"** and a **"Sessions"** button at the top-right
- The config bar shows labels **"Symbol"**, **"Timeframe"** (buttons `1m 5m 15m 1h 4h 1D`), **"Start"**, **"End"**, **"Capital"**, **"Exchange"**
- The left panel shows the heading **"Strategy Builder"** with strategy cards (or, if a session has history, an activity log)
- The right panel shows **"No Iterations Yet"** with text "Your strategy iterations will appear here. Describe a strategy to get started." (or an **"Iterations (N)"** list if the restored session already has runs)
- A multi-line text box with placeholder **"Describe a trading strategy…"** is visible at the bottom-left
- No blank screen, no red error overlay, no uncaught error in the browser console

---

### UT-02 — J-01: Run a backtest from a natural-language strategy (cold run) (happy-path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` — `BacktestConfigBar` + `ActivityLog` chat → `IterationCard` / `IterationDetailView`

**Preconditions:**
- UT-01 passed (app loaded)
- OpenAI key configured on the backend (strategy generation needs it)
- Use a session with **no** prior run of `BTC/USDT 1h 2023-01-01–2023-06-01` so this is a genuine cold cache (or click "Sessions" → "+ New Session" first)

**Steps:**
1. Navigate to `http://localhost:3691`
2. In the **Symbol** field, clear it and type `BTC/USDT`
3. In the **Timeframe** button group, click the **`1h`** button (it becomes highlighted/filled)
4. Click the **Start** date field and set it to `2023-01-01`
5. Click the **End** date field and set it to `2023-06-01`
6. In the **Capital** field, set the value to `1500`
7. Click into the **"Describe a trading strategy…"** box and type exactly: `Buy when RSI crosses below 30, sell when RSI crosses above 70`
8. Press **Enter** (do not hold Shift), or click the **paper-plane (send) icon** button to the right of the box
9. Wait for the run to finish (a new card in the right "Iterations" panel moves through "Generating" → "Executing" → **"Complete"**; typical wait 10–90s on a cold fetch)
10. In the right panel, click the iteration card whose status dot is green / labelled **"Complete"**

**Expected Result:**
- A green completion banner appears in the left activity log (emerald box with a check icon and a summary line)
- The right panel header changes to **"Iterations (1)"** and shows one card with status **"Complete"**, a strategy name, a params chip reading `BTC/USDT · 1h · 2023-01-01–2023-06-01 · $1,500`, and a metrics row of the form `+x.xx%  |  N trades  |  DD -x.x%  |  WR x%  |  SR x.xx` (numbers non-empty)
- After clicking the card, the detail view opens showing a **"Backtest parameters"** card (Symbol `BTC/USDT`, Timeframe `1h`, Date Range `2023-01-01 – 2023-06-01`, Capital `$1,500`), an **"Equity Curve"** chart that is drawn (a line, not an empty box), and a **"Trade History (N trades)"** section whose table has at least one row
- No red "Error" card, no blank screen
- This run constitutes a **new run/iteration in history** (one card now exists where there were none) — satisfies J-01

---

### UT-03 — J-06: Identical warm re-run completes, is identical, and is recorded (happy-path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` — `IterationCard` "Rerun" → `ResultsPanel`/`IterationDetailView`; `IterationPanel` history

**Preconditions:**
- UT-02 just completed in the **same session** for `BTC/USDT 1h 2023-01-01–2023-06-01` (so the Parquet cache for this pair/timeframe is now warm)

**Steps:**
1. In the right "Iterations" panel, locate the completed iteration from UT-02
2. Note its metrics from the card row: total return %, trade count, DD %, WR %, SR (write them down)
3. Hover the latest iteration card and click the **"Rerun"** button (circular-arrow icon / labelled "Rerun") — this re-executes the same strategy code over the same symbol/timeframe/date range
4. Wait for the new child iteration to reach status **"Complete"**
5. Click the new completed iteration card to open its detail view
6. Compare its metrics grid (Total Return, Max Drawdown, Win Rate, Total Trades, Sharpe Ratio, Profit Factor) and trade count to the values noted in step 2

**Expected Result:**
- The second run reaches **"Complete"** with no error state
- The right panel header now reads **"Iterations (2)"** — a **second distinct iteration** is recorded in history (the original is still present, shown as a compact card)
- The second run's **Total Return, Max Drawdown, Win Rate, Total Trades, Sharpe Ratio, Profit Factor** are **identical** to the first run's (same numbers, same trade count) — confirms cold-vs-warm determinism through the UI
- The second run completes **at least as fast as, and typically noticeably faster than, the first** (warm Parquet path makes no Binance fetch). Treat a *much slower* second run as a warning to investigate, not an automatic fail (the deterministic zero-fetch proof is pytest TC-01)
- Equity curve and Trade History render identically populated

---

### UT-04 — J-02: Open a prior run from history; spec/metrics/trades reload (regression)

**Type:** regression
**Priority:** P1
**Surface:** `/` — `IterationPanel` → `IterationCard` (past) → `IterationDetailView`

**Preconditions:**
- A session with **≥2** completed iterations (run UT-02 then UT-03 if needed) so at least one iteration is a **past** (compact) card

**Steps:**
1. Navigate to `http://localhost:3691`
2. In the right "Iterations" panel, click an **older / past** iteration card (a compact card above the latest one)
3. Observe the detail view that opens
4. Click the back-arrow (top-left of the detail view) to return to the list
5. Click a **different** past iteration card

**Expected Result:**
- Clicking a past card opens **`IterationDetailView`** showing that run's **"Backtest parameters"** (Symbol, Timeframe, Date Range, Capital matching what was run), its metrics grid with concrete numbers, an **"Equity Curve"** chart that is drawn, and a **"Trade History (N trades)"** table with rows
- The **"Strategy Script"** collapsible is present (clicking it reveals the strategy code)
- No "not found", no 404, no blank panel, no all-zero metrics — the run reloaded from the durable session store (this is the highest-risk persistence regression for this iteration)
- The back arrow returns to the **"Iterations (N)"** list intact; selecting a second past run shows *its own* distinct spec/metrics/trades

---

### UT-05 — J-02 durability: history survives a backend restart with no BACKTEST_STORE_DIR (regression)

**Type:** regression
**Priority:** P1 (DoD-critical — the single new behavioral guarantee of this iteration)
**Surface:** `/` — `SessionPicker` + `IterationPanel` after backend process restart

**Preconditions:**
- At least one session with ≥1 completed iteration exists (from UT-02/UT-03)
- The operator has access to stop/start the backend process
- This test specifically validates the new durable default: the backend must be
  restarted with the **`BACKTEST_STORE_DIR` environment variable UNSET** (do not
  export it; if a `.env` sets it, temporarily run without that `.env`) so the
  code's new durable default (`<repo>/.data/backtests`, not `/tmp`) is exercised

**Steps:**
1. Confirm the session and its completed iteration(s) are visible at `http://localhost:3691` (note the session name and iteration count, e.g. "Iterations (2)")
2. Stop the backend process
3. Restart the backend process **with `BACKTEST_STORE_DIR` unset** (plain restart, no `.env` override of that variable)
4. Reload the browser tab (`http://localhost:3691`, press F5)
5. Wait for the "Sessions" button to finish loading (status dot stops spinning)
6. If the prior session is not auto-selected, click **"Sessions"** in the header and select the session by name
7. Open a prior iteration (click a past iteration card)

**Expected Result:**
- After the restart + reload, the **same session still appears** in the "Sessions" picker with the **same iteration count** (e.g. still "Iterations (2)") — history did **not** vanish
- Opening a prior iteration still renders its full **`IterationDetailView`** (spec + metrics + Equity Curve + Trade History) — the store resolved to the durable in-repo location and survived the restart
- **"Broken" looks like:** the session is gone, "Iterations (0)" / "No Iterations Yet", or the prior run opens blank / errors — that would indicate the store defaulted to a volatile path (regression / anti-goal violation)

---

### UT-06 — J-03: Walk-forward analysis renders WFE badge + per-window table + OOS curve (regression)

**Type:** regression
**Priority:** P1
**Surface:** `/` — `IterationDetailView` → "Walk-Forward Analysis" → `WalkForwardPanel`

**Preconditions:**
- A completed iteration open in its detail view (run UT-02 first, then click that card)

**Steps:**
1. From a completed iteration's detail view, scroll to the **"Walk-Forward Analysis"** section and click its header to expand it (if collapsed — chevron points down when expanded)
2. In the expanded config row, set **"IS months"** to `6` and **"OOS months"** to `3`
3. Click the **"Run Walk-Forward"** button (top-right of the section). If the button reads **"Re-run"** instead, click that; you may also use the **"Run"** button in the config row
4. Wait while the section shows **"Fetching data…"** then **"Running window X / Y…"** until it finishes

**Expected Result:**
- A **WFE badge** appears next to "Walk-Forward Eff." of the form `WFE x.xx ✓` (emerald, ≥0.50), `WFE x.xx ~` (amber, 0.30–0.50), or `WFE x.xx ✗` (red, <0.30)
- An aggregate metrics row shows **OOS Return**, **OOS Sharpe**, **OOS Win Rate**, **OOS Max DD**
- A **per-window table** is populated with **≥1 data row** under headers `# | IS Period | OOS Period | IS Return | OOS Return | IS Sharpe | OOS Sharpe | IS Trades | OOS Trades`
- A **"Combined OOS Equity Curve (N windows chained)"** chart is drawn below the table
- The section does **not** show "No windows completed." and no red "Walk-forward validation failed" message

---

### UT-07 — J-04: AI insights render at least one ranked suggestion (regression)

**Type:** regression
**Priority:** P1
**Surface:** `/` — left `ActivityLog` insights entry (blue lightbulb box with suggestion pills)

**Preconditions:**
- A completed run exists in the current session (UT-02); OpenAI key configured

**Steps:**
1. Navigate to `http://localhost:3691` with the session that has the UT-02 run
2. In the **left** activity panel, scroll to the latest completed iteration's messages
3. Locate the **blue** info box marked with a lightbulb icon (the AI insights/suggestions entry)

**Expected Result:**
- A blue insights box is present containing a sentence of insight text **and at least one clickable suggestion pill** (rounded blue button labelled with a short suggestion title)
- The panel is **not empty** and shows **no error** in place of suggestions
- (Optional sanity) Clicking one suggestion pill starts a new iteration using that suggestion's prompt (a new card appears in the right panel) — confirms the insights→iterate loop is intact

---

### UT-08 — Symbol field rejects non-`BASE/USDT` input with an inline error (validation)

**Type:** validation
**Priority:** P2
**Surface:** `/` — `BacktestConfigBar` Symbol input

**Preconditions:**
- App loaded (UT-01)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Click the **Symbol** field, clear it, and type `BTC` (no `/USDT`)
3. Click outside the field (blur) or continue — observe the field

**Expected Result:**
- A red validation message **"Must be BASE/USDT format (e.g. PEPE/USDT)"** appears directly below the Symbol field
- The Symbol input border turns red
- Correcting the value to `BTC/USDT` clears the red message and red border (no page reload, no crash)

---

### UT-09 — Non-existent symbol surfaces a backend error without crashing (error)

**Type:** error
**Priority:** P2
**Surface:** `/` — `ActivityLog` error entry path (`validate-symbol` → error log entry)

**Preconditions:**
- App loaded; backend reachable

**Steps:**
1. Navigate to `http://localhost:3691`
2. Set the **Symbol** field to `ZZZZ/USDT` (valid format, but not a real Binance pair)
3. Set Timeframe `1h`, Start `2023-01-01`, End `2023-06-01`, Capital `1500`
4. Type `Buy when RSI crosses below 30, sell when RSI crosses above 70` into the **"Describe a trading strategy…"** box
5. Press **Enter** (or click the send icon)

**Expected Result:**
- A **red error entry** appears in the left activity log with text beginning **"Invalid symbol:"** (e.g. "Invalid symbol: ZZZZ/USDT not found on Binance")
- The app remains responsive: the config bar is still usable, the text box is re-enabled, no blank screen, no uncaught console exception
- No "Complete" iteration is created for this attempt (no false success card)

---

### UT-10 — Session and run history persist across a browser refresh (regression)

**Type:** regression
**Priority:** P1
**Surface:** `/` — `SessionPicker` + `IterationPanel` after page reload (durable store via normal path)

**Preconditions:**
- A session with ≥1 completed iteration (UT-02)

**Steps:**
1. With a session showing **"Iterations (N)"** (N ≥ 1) at `http://localhost:3691`, note N and the active session name
2. Press **F5** (or Cmd+R) to reload the page — do **not** clear browser storage
3. Wait for the "Sessions" button status dot to settle (no spinner)

**Expected Result:**
- After reload, the same session is active (or selectable via the **"Sessions"** dropdown by the same name) and the right panel again shows **"Iterations (N)"** with the same count
- Clicking a completed iteration still opens its full detail (spec + metrics + Equity Curve + Trade History) — history was served from the durable backend session store, not lost
- **"Broken" looks like:** count drops to 0 / "No Iterations Yet" after a plain refresh, or the session disappears from the picker

---

### UT-11 — Primary backtest journey is discoverable to a first-time user (ux)

**Type:** ux
**Priority:** P3
**Surface:** `/` — empty-state `ActivityLog` (Strategy Builder) + header `SessionPicker`

**Preconditions:**
- A fresh session with no iterations (click **"Sessions" → "+ New Session"** if the current one has history)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Click **"Sessions"** in the header, then click **"+ New Session"**
3. Observe the left panel of the new session without prior knowledge of the app
4. Click any one strategy card (e.g. the first card in the grid)

**Expected Result:**
- The empty state clearly presents **"Strategy Builder"**, a sub-line "20 strategies for &lt;symbol&gt; · &lt;timeframe&gt;", a grid of clickable strategy cards, and the "Describe a trading strategy…" box — the way to start a backtest is obvious within **one click** (a strategy card) and the config bar controls (Symbol/Timeframe/dates) are visible above without scrolling
- Clicking a strategy card immediately starts a run (a card appears in the right "Iterations" panel and moves to "Generating") — the core journey is reachable without documentation
- The "Sessions" control for switching/creating sessions is visible in the header (history is discoverable)

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | App shell loads | smoke | P1 | `/` (shell) |
| UT-02 | J-01 cold backtest from NL strategy | happy-path | P1 | `/` config + chat → results/history |
| UT-03 | J-06 identical warm re-run + recorded | happy-path | P1 | `/` Rerun → results, history |
| UT-04 | J-02 open prior run, detail reloads | regression | P1 | `/` IterationPanel → DetailView |
| UT-05 | J-02 durability across backend restart | regression | P1 | `/` SessionPicker + history |
| UT-06 | J-03 walk-forward renders fully | regression | P1 | `/` DetailView → WalkForwardPanel |
| UT-07 | J-04 AI insights ≥1 suggestion | regression | P1 | `/` ActivityLog insights box |
| UT-08 | Symbol format inline validation | validation | P2 | `/` BacktestConfigBar |
| UT-09 | Non-existent symbol error surfaced | error | P2 | `/` ActivityLog error path |
| UT-10 | History persists across page refresh | regression | P1 | `/` SessionPicker + history |
| UT-11 | Primary journey discoverable | ux | P3 | `/` empty-state + header |

**P1 tests must all pass for the browser QA verdict to be PASS:** UT-01, UT-02,
UT-03, UT-04, UT-05, UT-06, UT-07, UT-10.

**Journey coverage:** J-01 → UT-02; J-06 → UT-03; J-02 → UT-04, UT-05, UT-10;
J-03 → UT-06; J-04 → UT-07. UT-08/UT-09 = input/error robustness;
UT-11 = discoverability sanity (no regression in journey entry point).

**Not duplicated here (covered by functional test plan):** deterministic
zero-Binance-fetch on warm re-run (TC-01), byte-identical cold==warm `list[OHLCV]`
(TC-02), on-disk single-Parquet/zero-CSV (TC-03), `BASE_DIR` path resolution
(TC-08), restart round-trip at the store layer (TC-09). The browser plan verifies
these are **not user-visible regressions**, not the internal mechanics.
