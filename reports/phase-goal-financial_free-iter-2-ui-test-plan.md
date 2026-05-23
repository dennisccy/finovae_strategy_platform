# Phase goal-financial_free-iter-2 — UI Test Plan

**Phase:** goal-financial_free-iter-2
**Date:** 2026-05-23
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3692

---

> Single-page app (no client-side router). "Surface" refers to the persistent two-panel
> shell and its named panels, not distinct URLs. Use a **tiny budget** for every live run
> (≤ 2 iterations, short date range, cheapest model, lenient targets). Honor the documented
> Chrome-MCP headless render-throttle: if pixels are blank, verify the journey via the backend
> endpoints the UI calls (`GET /api/sessions`, `GET /api/sessions/{id}`,
> `POST /api/auto-sessions`, `POST /api/auto-sessions/{id}/stop`) and the persisted `autoRun`
> block. These UI tests do NOT duplicate the API/artifact tests in
> `reports/qa/goal-financial_free-iter-2-test-plan.md` — they cover the user-visible surfaces only.

---

## Test Cases

<!-- Test IDs use UT-XX prefix to distinguish from functional test plan TC-XX IDs. -->

---

### UT-01 — App shell loads with both panels (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** App shell (`http://localhost:3692`)

**Preconditions:**
- Frontend is running at http://localhost:3692
- Backend is reachable (the two-panel shell fetches `GET /api/sessions` on load)

**Steps:**
1. Navigate to `http://localhost:3692`
2. Wait for the page to fully load

**Expected Result:**
- The page renders without a blank screen or error overlay
- The Left panel (config bar + chat/activity input) is visible
- The Right / Iterations panel is visible
- No uncaught errors appear in the browser console

---

### UT-02 — Clicking "Auto Run" starts a backend run and mints a new session tab (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** Left config bar `Auto Run` control → Session picker → Right / Iterations panel

**Preconditions:**
- App loaded at http://localhost:3692
- A strategy prompt + tiny config is set (short date range e.g. `2024-01-01`→`2024-01-07`, cheapest model, ≤ 2 iterations). The violet **Auto Run** control is visible (i.e. `canAutoRun` is true)

**Steps:**
1. Navigate to `http://localhost:3692`
2. In the Left config bar set the Auto Run count input to `2`
3. Click the violet **"Auto Run (2)"** button (lightning-bolt icon) at the right end of the config bar
4. Observe the Session picker
5. Observe the top of the Right / Iterations panel

**Expected Result:**
- A **new session entry is added to the Session picker and becomes the active/selected tab**
- The **AutoSessionStatusStrip appears pinned at the top of the Iterations panel** with a blue **"Running"** (or briefly "Queued") badge, an animated spinner icon, and the label **"Optimizing server-side"**
- Tracking begins automatically (no manual reload needed)

---

### UT-03 — Status strip budget counters advance live during a run (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `AutoSessionStatusStrip` budget counters (Right / Iterations panel)

**Preconditions:**
- An Auto Run started via UT-02 is currently `queued`/`running`

**Steps:**
1. Keep the auto-session tab selected; do NOT reload
2. Read the right-aligned counters in the status strip: the `<n>/<max> rounds` counter and the `<n>s / <max>s` counter
3. Wait through ~3 successive ~2.5s polls (about 8–10 seconds)
4. Re-read both counters

**Expected Result:**
- The `rounds` counter shows `0/2` (or `1/2`) initially and increments toward `2/2` as iterations complete (it never exceeds `max`)
- The `<n>s / <max>s` elapsed wall-clock counter strictly increases across polls (e.g. `5s / 60s` → `10s / 60s`)
- The spinner keeps animating while status is `running`

---

### UT-04 — New iteration cards stream into the tree without reload (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `IterationPanel` live iteration tree (Right / Iterations panel)

**Preconditions:**
- An Auto Run started via UT-02 is `running`; the page has NOT been reloaded

**Steps:**
1. Keep the auto-session tab selected and do not reload
2. Watch the iteration tree below the status strip for up to ~30 seconds

**Expected Result:**
- At least one **new iteration card appears on its own** in the tree (no manual reload, no button click)
- Each new card shows a completed backtest result (e.g. a metric/return value), not a perpetual spinner
- The card count in the tree matches the strip's `rounds done` counter

---

### UT-05 — Status strip reaches a terminal state when a tiny run finishes (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `AutoSessionStatusStrip` terminal state (Right / Iterations panel)

**Preconditions:**
- A tiny-budget Auto Run (≤ 2 iterations) from UT-02 is in progress

**Steps:**
1. Keep the auto-session tab selected and wait for the run to complete (typically under ~60s for a tiny budget)
2. Observe the status badge, the spinner, and the second row of the strip

**Expected Result:**
- The badge changes from blue "Running" to a terminal state: amber **"Budget exhausted"** or emerald **"Criteria met"**
- The spinner **stops animating**
- The secondary label changes from "Optimizing server-side" to **"Automated session"**
- A stop-reason text appears (e.g. **"Budget exhausted"** or **"Robust targets met"**)

---

### UT-06 — Best-iteration badge appears after a result is produced (happy path)

**Type:** happy-path
**Priority:** P2
**Surface:** `AutoSessionStatusStrip` best badge (second row)

**Preconditions:**
- An Auto Run from UT-02 has produced at least one completed iteration

**Steps:**
1. Keep the auto-session tab selected
2. Look at the second row of the status strip (appears once a best is marked)

**Expected Result:**
- A violet pill badge reading **"Best: <8-char id>"** (award icon) appears in the strip's second row
- The 8-character id matches the backend-marked best iteration (no browser-side recompute)

---

### UT-07 — Empty state shows before the first iteration exists (happy path)

**Type:** happy-path
**Priority:** P2
**Surface:** `IterationPanel` empty state (Right / Iterations panel)

**Preconditions:**
- About to start a fresh Auto Run (so the new session has zero iterations for a brief moment)

**Steps:**
1. From http://localhost:3692, set a tiny config and click **"Auto Run (2)"**
2. Immediately observe the Iterations panel area below the status strip

**Expected Result:**
- While the backend spins up the first iteration, the panel shows a **"Waiting for the first iteration…"** empty-state message
- The status strip is still rendered above this empty state
- Once the first card streams in, the empty state is replaced by the iteration tree

---

### UT-08 — Auto Run control toggles to a Stop control while running (validation/state)

**Type:** validation
**Priority:** P1
**Surface:** `BacktestConfigBar` Auto Run / Stop control (Left config bar)

**Preconditions:**
- App loaded; an Auto Run can be started (violet **"Auto Run (N)"** visible)

**Steps:**
1. Click the violet **"Auto Run (2)"** button
2. Observe the right end of the config bar while status is `queued`/`running`
3. Wait for the run to reach a terminal state and observe the control again

**Expected Result:**
- While running, the violet "Auto Run" button is **replaced by an amber "Stop (current/max)" button** (e.g. "Stop (1/2)") with a square icon
- When the run reaches a terminal status, the amber Stop button is **replaced again by the violet "Auto Run (N)" control**
- The control never shows both Auto Run and Stop at the same time

---

### UT-09 — ⚡ on a completed iteration card seeds a new auto-session (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `IterationCard` ⚡ Auto Run action → Session picker

**Preconditions:**
- A session with at least one **completed** iteration card exists (status "complete")

**Steps:**
1. Navigate to `http://localhost:3692` and select a session containing a completed iteration
2. Hover the completed iteration card to reveal its action buttons
3. Click the **⚡ (lightning-bolt) button** with tooltip **"Auto Run"** on that card
4. Observe the Session picker and the Iterations panel

**Expected Result:**
- A **new session tab is added to the Session picker and becomes the active/selected tab**
- The new tab is a backend auto-session seeded from that iteration's strategy prompt and parameters
- The AutoSessionStatusStrip appears with a "Queued"/"Running" badge and live tracking begins

---

### UT-10 — Session picker shows a running spinner that survives reload (regression/resilience)

**Type:** regression
**Priority:** P1
**Surface:** `SessionPicker` running spinner + reload-mid-run resilience

**Preconditions:**
- An Auto Run is in progress (status `running`) — start one via UT-02 with budget large enough to still be running (2 iterations)

**Steps:**
1. With the auto-session running, observe the Session picker: a spinner shows next to the active auto-session tab
2. Reload the browser tab (press F5 / Cmd+R) **while the run is still in progress**
3. After reload, reopen/select the same auto-session from the Session picker (no other action)
4. Observe the Session picker and the status strip

**Expected Result:**
- After reload the Session picker shows the **spinner again next to the running auto-session, with no user action** to restart it
- The status strip still shows **"Running"** with the elapsed-seconds counter continuing to advance past the reload moment
- The run **reaches a terminal state without a second manual reload**
- (If pixels blank: confirm via `GET /api/sessions/{id}` that `autoRun.status` continued advancing through the reload.)

---

### UT-11 — Stop truly halts the backend run (error/control)

**Type:** error
**Priority:** P1
**Surface:** Server-side Stop action (Left config bar Stop button)

**Preconditions:**
- An Auto Run is in progress with budget large enough to still be running (e.g. 2 iterations)

**Steps:**
1. While the run is `running`, click the amber **"Stop (current/max)"** button in the Left config bar
2. Observe the status strip over the next poll (~2.5s)
3. Watch the iteration tree for ~10s after stopping

**Expected Result:**
- The status badge transitions to slate **"Stopped"** (square icon, no spinner)
- The stop-reason text reads **"Stopped by user"**
- **No further iteration cards are appended** after the stop
- The violet **"Best: <id>"** badge (if one was set) **remains** visible
- (If pixels blank: confirm via `GET /api/sessions/{id}` that `autoRun.status == "stopped"` and iteration count is frozen.)

---

### UT-12 — Status strip is hidden entirely for a manual session (ux/regression)

**Type:** regression
**Priority:** P1
**Surface:** `AutoSessionStatusStrip` (manual session)

**Preconditions:**
- A manual (non-Auto Run) session exists, or can be created by running a single manual backtest

**Steps:**
1. Navigate to `http://localhost:3692`
2. Select (or create via a manual single run) a **manual** session — one that was never started via Auto Run
3. Observe the top of the Right / Iterations panel

**Expected Result:**
- **No status strip is rendered at all** for the manual session (no badge, no counters)
- The iteration tree / results render normally as before this phase

---

### UT-13 — Manual single-run backtest still works (regression)

**Type:** regression
**Priority:** P1
**Surface:** Left chat/activity input → Right results (manual journey J-01)

**Preconditions:**
- App loaded at http://localhost:3692; backend reachable

**Steps:**
1. Navigate to `http://localhost:3692`
2. In the Left activity/chat input type a simple strategy, e.g. `simple SMA crossover`
3. Set a short date range (e.g. `2024-01-01`→`2024-01-07`) and the cheapest model
4. Submit the single backtest (Send / Run)

**Expected Result:**
- A single iteration result renders in the Right panel (metrics / equity curve / trades)
- **No status strip appears** (this is a manual run, not an Auto Run)
- The manual flow behaves as before this phase — the removal of the in-browser loop did not break single runs

---

### UT-14 — Run history browse still opens prior iterations (regression)

**Type:** regression
**Priority:** P2
**Surface:** `IterationPanel` / Session picker (manual journey J-02)

**Preconditions:**
- A session with multiple prior iterations exists

**Steps:**
1. Navigate to `http://localhost:3692` and select a session with prior iterations
2. Click a prior iteration card in the tree

**Expected Result:**
- The selected iteration's detail (result/metrics) opens and renders
- Browsing between iterations works as before this phase

---

### UT-15 — Strip semantics are clear and discoverable (ux)

**Type:** ux
**Priority:** P3
**Surface:** `AutoSessionStatusStrip` labels/tooltips

**Preconditions:**
- An auto-session (running or terminal) is selected

**Steps:**
1. Read the status strip without prior knowledge of the feature
2. Hover the `rounds` counter and the `<n>s / <max>s` counter

**Expected Result:**
- The badge label (Running / Budget exhausted / Criteria met / Stopped / Interrupted / Error) makes the run state obvious at a glance
- Hovering the `rounds` counter shows the tooltip "Improvement rounds done / max"
- Hovering the seconds counter shows the tooltip "Elapsed / max wall-clock (seconds)"
- An operator can tell whether the run is active, what it's optimizing, and which iteration is best within ~5 seconds of looking

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | App shell loads | smoke | P1 | App shell |
| UT-02 | Auto Run starts backend run + mints tab | happy-path | P1 | Config bar / Session picker |
| UT-03 | Budget counters advance live | happy-path | P1 | Status strip counters |
| UT-04 | Iteration cards stream in (no reload) | happy-path | P1 | Iteration tree |
| UT-05 | Run reaches terminal state | happy-path | P1 | Status strip terminal |
| UT-06 | Best badge appears | happy-path | P2 | Status strip best badge |
| UT-07 | "Waiting for first iteration" empty state | happy-path | P2 | Iteration panel empty state |
| UT-08 | Auto Run ↔ Stop control toggles | validation | P1 | Config bar control |
| UT-09 | ⚡ on iteration seeds new auto-session | happy-path | P1 | Iteration card / Session picker |
| UT-10 | Spinner survives reload mid-run | regression | P1 | Session picker / resilience |
| UT-11 | Stop truly halts backend run | error | P1 | Stop action |
| UT-12 | Strip hidden for manual session | regression | P1 | Status strip (manual) |
| UT-13 | Manual single-run still works | regression | P1 | Manual run path |
| UT-14 | Run history browse still works | regression | P2 | Iteration panel |
| UT-15 | Strip labels clear/discoverable | ux | P3 | Status strip labels |

**P1 tests must all pass for browser QA verdict to be PASS.**
P1: UT-01, UT-02, UT-03, UT-04, UT-05, UT-08, UT-09, UT-10, UT-11, UT-12, UT-13.
