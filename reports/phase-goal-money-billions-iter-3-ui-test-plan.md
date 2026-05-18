# Phase goal-money-billions-iter-3 — UI Test Plan

**Phase:** goal-money-billions-iter-3
**Date:** 2026-05-18
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3691

---

## Context for the operator

- This is a **single-page app — there is no router and no URLs to navigate to
  per feature**. The only page is the session view. "Navigate" below always
  means open `http://localhost:3691` and act inside that one page.
- Layout: a **header** ("Finovae Strategy Platform", a grey **"Sessions"**
  button top-right), a **config bar** (Symbol / Timeframe / Start / End /
  Capital / Exchange + checkboxes), then a two-panel **main** area:
  - **LEFT panel = Activity / Strategy Builder** (strategy textarea, model
    dropdown, blue 💡 AI-insights boxes).
  - **RIGHT panel = Iterations** (run-history list/tree + the run-detail pane).
- This phase changes *how* the session loads, not what features exist: the
  history list now renders from lightweight summaries and each run's full
  detail (strategy script, metrics, trades) is **fetched on demand when that
  run is selected**, with a loading spinner, an error+Retry state, and a
  no-detail state.
- "Open a session" = click the grey **"Sessions"** button in the header, then
  click a session row in the dropdown. "Reload a session" = press **F5** while
  that session is active.
- These UT-XX cases are operator/click-path tests. The API/artifact proofs of
  the anti-goal (`TC-01`/`TC-02` in `reports/qa/goal-money-billions-iter-3-test-plan.md`)
  are **not** duplicated here.

---

## Test Cases

<!-- Test IDs use UT-XX prefix to distinguish from functional test plan TC-XX IDs. -->

---

### UT-01 — Session view loads without errors (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** Session view (whole page)

**Preconditions:**
- Backend + frontend running (start with `./scripts/dev.sh`).
- Frontend reachable at `http://localhost:3691`.

**Steps:**
1. Open `http://localhost:3691` in a fresh browser tab.
2. Wait for the page to finish loading.
3. Open browser DevTools → Console tab and read it.

**Expected Result:**
- The header shows the title text **"Finovae Strategy Platform"** and a grey
  **"Sessions"** button on the right.
- The config bar shows a **"Symbol"** text input (placeholder `e.g. PEPE/USDT`)
  and a **"Timeframe"** dropdown.
- Two panels are visible: a left panel containing **"Strategy Builder"** (or a
  chat/activity list if a session already has runs) and a right panel.
- No full-page blank screen, no red error overlay.
- No uncaught exceptions in the Console (network 4xx/5xx unrelated to a
  deliberately-stopped backend are not present).

---

### UT-02 — Opening a session renders the lightweight history list; detail pane is empty until a run is clicked (happy-path — core changed behavior)

**Type:** happy-path
**Priority:** P1
**Surface:** Right panel — run-history list/tree (`IterationPanel` / `IterationCard`)

**Preconditions:**
- A session that already has **≥2 completed runs** exists. If none exists,
  first run UT-11 twice (two NL backtests) to create them.

**Steps:**
1. Open `http://localhost:3691`.
2. Click the grey **"Sessions"** button in the header.
3. In the dropdown, under **"Live Sessions"**, click the session row that has
   **≥2 iters** (the row shows e.g. `2 iters`).
4. If the right panel is showing a run's detail (a back arrow / "Back to
   history" is visible), click **"Back to history"** (or the top-left back
   arrow) so nothing is selected.
5. Look at the right panel.

**Expected Result:**
- The right panel header reads **"Iterations (N)"** where N ≥ 2.
- Each completed run is listed as a card showing its strategy name, the params
  line (`SYMBOL · timeframe · start–end · $capital`), and a timestamp.
- The newest run is a large card; older completed runs are compact rows.
- No run-detail content (no "Equity Curve", no "Trade History", no strategy
  script) is shown until a card is clicked.
- The page does not error or blank while the list renders from the lightweight
  open response.

---

### UT-03 — Completed-run card shows its metrics row immediately on open, before selection (happy-path — changed behavior)

**Type:** happy-path
**Priority:** P1
**Surface:** Right panel — `IterationCard` metrics row

**Preconditions:**
- The session from UT-02 (≥1 completed run), freshly opened, **no run
  selected** (history list visible).

**Steps:**
1. With the history list visible (UT-02 state), look at any **completed** run's
   card **without clicking it**.

**Expected Result:**
- The card shows a metrics row containing all of:
  - a return value formatted like `+12.34%` (green) or `-5.67%` (red),
  - `N trades`,
  - `DD -X.X%` (red),
  - `WR X%`,
  - `SR X.XX`.
- These values are visible **immediately on session open**, before the run's
  full detail has been fetched (i.e. before any spinner/detail load).
- "Broken" looks like: the metrics row missing, showing `+0.00% · 0 trades ·
  DD -0.0% · WR 0% · SR 0.00` for a run that actually has results, or the row
  only appearing after clicking the card.

---

### UT-04 — Selecting a prior run lazy-loads its detail (loading spinner → populated detail) (happy-path — J-02 primary regression watch)

**Type:** happy-path
**Priority:** P1
**Surface:** Right panel — detail pane loading state (`DetailStatusPane` / `Loader2`) → `IterationDetailView`

**Preconditions:**
- Session from UT-02 open, history list visible, ≥1 completed run.

**Steps:**
1. In the right panel, click a **completed** run card (for an older run, click
   the compact row; for the newest, click the large card).
2. Watch the right panel during and after the click.

**Expected Result:**
- Briefly, the right panel shows a centered spinner with the text
  **"Loading run detail…"** and the sub-text **"Fetching this run's strategy,
  metrics, and trades."**, plus a **"Back to history"** button at the top.
  (On a fast local backend the spinner may flash very briefly — that is
  acceptable; a *stuck* spinner is not.)
- Within ~1–3 s the spinner is replaced by the full detail view:
  - a header with the strategy name, the prompt snippet, a timestamp, and a
    coloured return badge (e.g. `+12.34%`),
  - a parameters card (Symbol / Timeframe / Date Range / Capital),
  - an **"Equity Curve"** chart,
  - a metrics grid (or a rating panel), and
  - a **"Trade History (N trades)"** table with at least one row.
- "Broken" looks like: the pane stays on the spinner forever, goes blank, or
  shows no Equity Curve / empty Trade History for a run that has results.

---

### UT-05 — Switching and re-selecting runs loads each run's own detail (no stale/cross-run bleed) (regression — J-02)

**Type:** regression
**Priority:** P1
**Surface:** Right panel — populated detail after lazy fetch (`IterationDetailView`)

**Preconditions:**
- A session with **≥2 completed runs that have different strategy names**
  (run UT-11 twice with two different prompts if needed).

**Steps:**
1. Open the session (UT-02 steps 1–3).
2. Click **run A** (note its strategy name and return badge in the detail
   header).
3. Click the top-left back arrow (or **"Back to history"**) to return to the
   list.
4. Click a **different run B** (note its strategy name and return badge).
5. Click back to the list again.
6. Click **run A** again.

**Expected Result:**
- After step 2: the detail header shows run A's strategy name and run A's
  return value; the Trade History count matches run A.
- After step 4: the detail header shows run B's *own* (different) strategy
  name / return value / trade count — **not** run A's.
- After step 6: run A's detail loads again correctly (strategy name, metrics,
  trades all match run A's first display).
- At no point does the detail pane show a previous run's data, a blank pane,
  or a permanently spinning loader.

---

### UT-06 — Lazy detail fetch failure shows an explicit error state with a working Retry (error)

**Type:** error
**Priority:** P2
**Surface:** Right panel — detail pane error state (`DetailStatusPane` / `AlertCircle` / Retry)

**Preconditions:**
- A session with ≥1 completed run open in the UI (history list visible).

**Steps:**
1. Open the session and return to the history list (UT-02 state).
2. Open DevTools → Network → enable **request blocking**, add a block rule
   matching `*/api/sessions/*/iterations/*` (URL pattern for the per-iteration
   detail endpoint). *(Alternative if request-blocking is unavailable: stop the
   backend process after the list has loaded.)*
3. In the right panel, click a completed run card.
4. Observe the right panel.
5. Remove the block rule (or restart the backend), then click the **"Retry"**
   button shown in the error pane.

**Expected Result:**
- After step 3: the detail pane shows a red alert icon with the heading
  **"Couldn't load this run's detail"**, an error message line below it, and a
  blue **"Retry"** button. A **"Back to history"** button is present at the
  top.
- The left panel and the right-panel history list are still reachable (clicking
  "Back to history" returns to the run list) — the app did **not** blank or
  crash.
- After step 5 (block removed + Retry): the spinner appears and then the full
  detail view loads correctly (as in UT-04).
- "Broken" looks like: a silent blank pane, a JS crash, or no Retry button.

---

### UT-07 — Selecting a run with no stored results shows a clear no-detail state, no crash (error)

**Type:** error
**Priority:** P2
**Surface:** Right panel — no-detail state (`DetailStatusPane` / `GitBranch`)

**Preconditions:**
- A session containing an **errored or in-progress run** (a run with no stored
  result). To create one: in the strategy textarea type a deliberately broken
  request such as `do something impossible that will not compile as a strategy`
  and submit; wait until that card shows the red **"Error"** status.

**Steps:**
1. In the right panel history list, click the run card whose status is
   **"Error"** (or an in-progress run with no metrics).

**Expected Result:**
- The detail pane shows a grey branch icon with the message **"No detailed
  results for this run"** and the sub-text **"This run has no stored metrics or
  trades to display."**, plus a **"Back to history"** button.
- No JavaScript error, no blank crash; other runs remain clickable after
  pressing **"Back to history"**.

---

### UT-08 — Reopening a session whose last-selected run was completed auto-loads that run's detail (happy-path — changed behavior)

**Type:** happy-path
**Priority:** P1
**Surface:** Right panel — detail pane on session open (initial selection auto lazy-load)

**Preconditions:**
- A session with ≥1 completed run. While that session is open, select a
  **completed** run so its detail is showing (UT-04 end state).

**Steps:**
1. With a completed run's detail visible, press **F5** to reload the page.
2. Wait for the page to finish loading and watch the right panel.

**Expected Result:**
- The session reopens and, after a brief loading state, the right panel
  **automatically renders that previously-selected run's full detail**
  (Equity Curve + Trade History + metrics) — without the operator clicking
  anything.
- "Broken" looks like: after reload the right panel is stuck on the spinner,
  stays blank, or shows the bare history list when a completed run was
  previously selected.

---

### UT-09 — Opening a session does NOT auto-generate AI insights (regression watch — changed behavior)

**Type:** regression
**Priority:** P2
**Surface:** Left panel — AI-insights auto-generate-on-open path

**Preconditions:**
- A session whose **latest completed run has no AI-insights box** yet. (Create
  by running UT-11 once in a brand-new session and, as soon as the run
  completes, do NOT wait for suggestions — proceed; or use a session known to
  have a latest run without a 💡 box.)

**Steps:**
1. Open `http://localhost:3691`, open DevTools → Network, filter for
   `generate-insights`.
2. Click **"Sessions"** → click the target session row.
3. Wait ~15 s on the freshly opened session **without clicking any run**.
4. Inspect the Network panel and the left (Activity) panel.

**Expected Result:**
- **No** `POST /api/generate-insights` request fires merely from opening the
  session.
- **No** new blue 💡 "Suggestions" box appears in the left panel just from
  opening the session.
- This confirms the intended change (no surprise paid AI calls on every open).
  Insights are only produced when the user runs a strategy or uses the
  request/regenerate path (see UT-10).
- "Broken" (regression) looks like: a `generate-insights` call firing
  automatically on open, or a 💡 box appearing without any user action.

---

### UT-10 — J-04: after a walk-forward run, the AI-insights pane shows an OOS/walk-forward-aware suggestion (happy-path — target journey, verification-only)

**Type:** happy-path
**Priority:** P1
**Surface:** Left panel — AI-insights pane (blue 💡 box in the Activity list); Right panel — Walk-Forward Analysis in the detail view

**Preconditions:**
- `OPENAI_API_KEY` is set in the running backend's environment (insights
  regeneration is verification-only; no insights code changed this phase).
- Reference the functional test plan **TC-12** for the exact
  request/regenerate trigger and the binding distinct-screenshot rule — this
  UT-10 is the operator-facing surface check, not a substitute for TC-12.

**Steps:**
1. Open `http://localhost:3691`. In the left panel strategy textarea type:
   `Buy when RSI crosses below 30, sell when it crosses above 70` and press
   the blue **Send** button (paper-plane icon). Use Symbol `BTC/USDT`,
   Timeframe `1h`. Wait for the run to complete (a 💡 "Suggestions" box appears
   in the left panel — these first suggestions are **not** yet OOS-aware).
2. In the right panel, click the completed run card so its detail loads
   (spinner → detail, per UT-04).
3. In the detail view, find the **"Walk-Forward Analysis"** section. Set
   **"IS months"** to `6` and **"OOS months"** to `3`, then click the
   **"Run Walk-Forward"** button (or **"Run"**). Wait until a green
   **`WFE x.xx`** badge, a per-window table, and a combined OOS equity curve
   appear.
4. Trigger an AI-insights **request/regenerate for this same run** as defined
   in functional test plan **TC-12** (the run's detail is lazy-loaded so its
   result is in memory).
5. Look at the **left panel** for the resulting blue 💡 "Suggestions" box and
   read the summary text and the suggestion pill labels.

**Expected Result:**
- A blue box with a 💡 (lightbulb) icon appears in the **left** Activity panel,
  containing a summary line and a row of suggestion pill buttons (rounded blue
  buttons each showing a short title).
- **At least one** suggestion's title or the summary text references
  out-of-sample / walk-forward / WFE / robustness behaviour (e.g. wording like
  "out-of-sample", "walk-forward", "WFE", "overfit", "robustness",
  "generalization").
- The evidence screenshot for J-04 must be of **this left-panel blue 💡 box**
  and must be visually **distinct** from the right-panel Walk-Forward panel
  captured in UT-12 — a duplicate of the walk-forward panel is INVALID for
  J-04.
- "Broken" looks like: no 💡 box ever appears after the regenerate trigger, the
  box has zero suggestions, or no suggestion/summary mentions any
  OOS/walk-forward/WFE/robustness concept.

---

### UT-11 — Regression: a fresh NL backtest still appends a new run to history (regression — J-01)

**Type:** regression
**Priority:** P1
**Surface:** Left panel strategy input → Right panel history list

**Preconditions:**
- `http://localhost:3691` open on any session.

**Steps:**
1. Note the number in the right-panel header **"Iterations (N)"**.
2. In the config bar set **Symbol** = `BTC/USDT`, **Timeframe** = `1h`, and a
   valid **Start**/**End** date range, **Capital** = `10000`.
3. In the left panel textarea type
   `Buy when RSI crosses below 30, sell when it crosses above 70` and click the
   blue **Send** button (paper-plane icon).
4. Wait for the run to complete (status reaches **Complete**).

**Expected Result:**
- The right-panel header increments to **"Iterations (N+1)"**.
- A new run card appears with status **"Complete"** and a populated metrics row
  (UT-03 format).
- Selecting the new run shows a non-empty detail view (Equity Curve + Trade
  History), confirming new runs still create and persist correctly under the
  lazy-load contract.

---

### UT-12 — Regression: walk-forward still renders WFE badge + per-window table + combined OOS curve (regression — J-03)

**Type:** regression
**Priority:** P1
**Surface:** Right panel — `IterationDetailView` → Walk-Forward Analysis (`WalkForwardPanel`)

**Preconditions:**
- A completed run exists; its detail has been opened (lazy-loaded) per UT-04.

**Steps:**
1. With the run's detail open, locate **"Walk-Forward Analysis"** (expand it if
   collapsed by clicking its header).
2. Set **"IS months"** = `6`, **"OOS months"** = `3`.
3. Click **"Run Walk-Forward"** (or **"Run"**).
4. Wait for completion and screenshot the Walk-Forward panel for the J-03/TC-14
   evidence.

**Expected Result:**
- A green (or yellow/red) **`WFE x.xx`** badge appears next to "Walk-Forward
  Analysis".
- A per-window results table renders with one row per window.
- A combined out-of-sample equity curve chart renders.
- This still works when the run's `scriptCode` was lazy-loaded on selection
  (the walk-forward request must have non-empty strategy code) — "broken" looks
  like a Walk-Forward "Error" pill or an HTTP error because the script code was
  empty.

---

### UT-13 — Regression: symbol & timeframe controls still populate (regression — J-05)

**Type:** regression
**Priority:** P2
**Surface:** Config bar — Symbol input + Timeframe dropdown

**Preconditions:**
- `http://localhost:3691` open; backend reachable.

**Steps:**
1. Click into the config bar **"Symbol"** input and view its autocomplete
   suggestions (datalist).
2. Open the **"Timeframe"** dropdown.

**Expected Result:**
- The Symbol input offers a non-empty suggestion list including `BTC/USDT`
  (sourced from `/api/symbols`); the field is editable, not disabled.
- The Timeframe dropdown shows a non-empty list including a `1h` / "1 Hour"
  option.
- Neither control is empty or disabled — confirms the session-open contract
  change did not regress reference-data loading.

---

### UT-14 — Regression: warm-cache re-run is deterministic and appears in history (regression — J-06)

**Type:** regression
**Priority:** P3
**Surface:** Left panel strategy input → Right panel history list / detail metrics

**Preconditions:**
- UT-11 has been completed once for a fixed `BTC/USDT` / `1h` / date range /
  `10000` capital (so the data cache is warm).

**Steps:**
1. Submit the **exact same** strategy text with the **identical** Symbol,
   Timeframe, Start/End dates and Capital as UT-11.
2. Wait for completion.
3. Open the new run's detail and compare its **total return** and **trade
   count** to the UT-11 run's detail.

**Expected Result:**
- The second run completes without error and is added to history (header count
  increments).
- Its key metrics (total return %, number of trades) **exactly match** the
  first run's — confirming the deterministic warm-cache path is intact.

---

### UT-15 — History-card "Rerun" on an un-opened old run has empty previous-code context until the run is opened (regression — documented consequence)

**Type:** regression
**Priority:** P3
**Surface:** Right panel — `IterationCard` Rerun action / `SessionContainer` handlers

**Preconditions:**
- A session with an **old completed run that has NOT been selected/opened**
  this session load (its heavy detail, including `scriptCode`, is not yet
  lazy-loaded).

**Steps:**
1. Open the session and stay on the history list (do **not** click the old
   run).
2. Hover the old compact run card to reveal its icon buttons and click the
   **Rerun** icon (circular-arrow `RotateCw` icon, tooltip **"Rerun"**).
3. Observe the result.
4. Now click the old run card to **open it** (detail lazy-loads per UT-04),
   click **"Back to history"**, then click its **Rerun** icon again.

**Expected Result:**
- Step 2 (run not yet opened): the rerun is a documented no-op / runs with
  **empty previous-code context** (the card's `scriptCode` is a lazy field not
  yet loaded). This is the intended, documented consequence — it must not
  crash the app.
- Step 4 (run opened first): the Rerun now executes with the previous code
  present and produces a child run in history.
- Confirms the documented behaviour change is accurate and non-crashing.
  Brand-new strategy runs (UT-11) and walk-forward (UT-12) remain unaffected.

---

### UT-16 — Lazy-load states are discoverable and clearly labelled (ux)

**Type:** ux
**Priority:** P3
**Surface:** Right panel — `DetailStatusPane` (loading / error / no-detail)

**Preconditions:**
- Session with ≥1 completed run.

**Steps:**
1. Trigger the loading state (UT-04 step 1) and read the on-screen text.
2. Trigger the error state (UT-06) and read the on-screen text.
3. Trigger the no-detail state (UT-07) and read the on-screen text.

**Expected Result:**
- Each state is self-explanatory without developer knowledge:
  - Loading: "Loading run detail…" + "Fetching this run's strategy, metrics,
    and trades."
  - Error: "Couldn't load this run's detail" + a visible error message + a
    clearly-labelled **"Retry"** button.
  - No-detail: "No detailed results for this run" + "This run has no stored
    metrics or trades to display."
- Every state provides a **"Back to history"** affordance so the operator is
  never trapped on a status pane. Labels are plain English, not codes/stack
  traces.

---

### UT-17 — Walk-forward IS/OOS month inputs accept only sane values within the lazily-loaded detail view (validation)

**Type:** validation
**Priority:** P2
**Surface:** Right panel — `IterationDetailView` → Walk-Forward Analysis IS/OOS number inputs

**Preconditions:**
- A completed run's detail opened via the lazy fetch (UT-04). Walk-Forward
  Analysis section visible.

**Steps:**
1. In the **"IS months"** input, clear it and type `0`, then click elsewhere.
2. In the **"IS months"** input, type a non-numeric value (e.g. `abc`).
3. In the **"OOS months"** input, clear it and type `0`.

**Expected Result:**
- "IS months" never holds an invalid run-breaking value: clearing/`0`/`abc`
  resolves to a minimum of `1` (it falls back to `6` for IS / `3` for OOS when
  unpar. i.e. it never submits `0` or `NaN`). The input enforces `min=1`,
  `max=60`.
- Confirms the walk-forward form inside the now-lazily-loaded detail view is
  fully interactive (a proxy that the lazy-fetched detail view mounts a working
  `IterationDetailView`, not a degraded read-only shell).

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | Session view loads | smoke | P1 | Whole page |
| UT-02 | Lightweight history list on open | happy-path | P1 | Right — history list |
| UT-03 | Card metrics row visible pre-selection | happy-path | P1 | Right — `IterationCard` |
| UT-04 | Lazy detail loads on selection (spinner→detail) | happy-path | P1 | Right — detail loading→populated |
| UT-05 | Switch/re-select runs, no stale bleed | regression | P1 | Right — populated detail |
| UT-06 | Detail fetch error + Retry | error | P2 | Right — error state |
| UT-07 | No-detail run does not crash | error | P2 | Right — no-detail state |
| UT-08 | Restored selection auto-loads on reopen | happy-path | P1 | Right — detail on open |
| UT-09 | No auto-insights on session open | regression | P2 | Left — auto-insights path |
| UT-10 | J-04 OOS-aware insights pane | happy-path | P1 | Left — 💡 insights box |
| UT-11 | Fresh NL run appends to history (J-01) | regression | P1 | Left input → Right list |
| UT-12 | Walk-forward WFE/table/curve (J-03) | regression | P1 | Right — Walk-Forward panel |
| UT-13 | Symbol/timeframe controls populate (J-05) | regression | P2 | Config bar |
| UT-14 | Warm-cache re-run deterministic (J-06) | regression | P3 | Left input → Right detail |
| UT-15 | Un-opened card Rerun = empty prev-code | regression | P3 | Right — `IterationCard` Rerun |
| UT-16 | Lazy-load states discoverable/labelled | ux | P3 | Right — `DetailStatusPane` |
| UT-17 | Walk-forward IS/OOS input validation | validation | P2 | Right — Walk-Forward inputs |

**P1 tests must all pass for the browser QA verdict to be PASS.**

- **Primary regression watch:** UT-04 + UT-05 + UT-08 (J-02 lazy detail
  reload). A green J-02 does **not** by itself prove the eager-load anti-goal
  resolved — that proof is `TC-01`/`TC-02` (code + response-shape) in the
  functional test plan.
- **Target verification:** UT-10 (J-04) — the J-04 evidence screenshot must be
  the **left-panel blue 💡 insights box**, provably distinct from the UT-12 /
  TC-14 walk-forward panel.
- **No-regression smoke:** UT-11 (J-01), UT-12 (J-03), UT-13 (J-05),
  UT-14 (J-06).
