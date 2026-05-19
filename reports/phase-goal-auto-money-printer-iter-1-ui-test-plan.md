# Phase goal-auto-money-printer-iter-1 — UI Test Plan

**Phase:** goal-auto-money-printer-iter-1
**Date:** 2026-05-19
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3691
**Backend URL:** http://localhost:8691  (deterministic port offset 691; the Vite
proxy path `http://localhost:3691/api/...` is equivalent if 8691 is not directly
reachable)

---

## Conventions & shared fixtures

> The app is a **single-page React app — there is no URL router**. Surfaces are
> reached by location in the SPA: the header **"Sessions"** dropdown
> (`SessionPicker`) and the active session's two-panel workstation
> (`SessionContainer`: left = activity log, right = iteration history + detail).
> "Surface" below names the logical location, not a URL path.

**Tiny-budget headless trigger (used as a precondition by many cases).** The
only way to start a headless run this iteration is the API (no UI button —
deferred to iter-2). Run from a shell:

```
curl -sS -X POST http://localhost:8691/api/auto-sessions \
  -H 'Content-Type: application/json' \
  -d '{"natural_language":"Buy when RSI crosses below 30, sell when it crosses above 70","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-01-15","initial_capital":10000,"model":"gpt-5.4-mini","targets":{"min_wfe":0.0,"min_trades":0,"min_return":-1.0},"budget":{"max_iterations":2}}'
```

Expected response: HTTP 200 body `{"sessionId":"<uuid>","status":"running"}` (or
`"queued"`). **Record the `sessionId`** — several cases match the session row by it.

**Session-discovery fallback (documented, allowed).** The App fetches the
session-tab list only on mount; it does not poll the tab list. If a freshly
created headless session is not yet shown in the "Sessions" dropdown, **reload
the page once** and reopen the dropdown — the backend persists the session to
the durable file store, so it appears after a reload. This fallback is allowed
for every case **except UT-03**, which specifically pins the "appears without a
reload" claim.

**Prerequisites for all live/headless cases:**
- Frontend running at http://localhost:3691, backend at http://localhost:8691.
- Backend env has a working `OPENAI_API_KEY` and outbound network (Binance +
  LLM) — the headless loop performs real generate→backtest→walk-forward→insights.
- No login/auth in this app.

---

## Test Cases

<!-- UT-XX IDs are distinct from the functional plan's TC-XX IDs. -->
<!-- API-only assertions are NOT duplicated here — see reports/qa/...-test-plan.md. -->

---

### UT-01 — App shell loads with the Sessions picker (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** App shell / header

**Preconditions:**
- Frontend running at http://localhost:3691; backend up.

**Steps:**
1. Navigate to `http://localhost:3691`.
2. Wait for the page to fully load.

**Expected Result:**
- The header shows the title text **"Finovae Strategy Platform"** and the
  version label **"v0.3.0"**.
- A **"Sessions"** button (clock icon + the word "Sessions") is visible in the
  top-right of the header.
- The two-panel workstation is visible: a left panel with a chat box whose
  placeholder is **"Describe a trading strategy..."** and a right panel.
- No blank screen, no red error overlay, no uncaught error in the browser
  console.

---

### UT-02 — Manual session workstation renders with NO AutoRunBar (smoke / baseline)

**Type:** smoke
**Priority:** P1
**Surface:** `SessionContainer` (manual session)

**Preconditions:**
- Fresh app load (default session is a manual, non-headless session).

**Steps:**
1. Navigate to `http://localhost:3691`.
2. Observe the area directly **below the backtest-config bar** (the row
   containing the "Symbol", "Timeframe", "Start", "End", "Capital" controls).

**Expected Result:**
- The config bar with **Symbol / Timeframe / Start / End / Capital** controls is
  visible.
- There is **no** status strip reading "Automated run …" anywhere below the
  config bar (the `AutoRunBar` is gated on a headless `autoRun` block and must
  not appear for a manual session).
- The right panel shows the iteration history area (empty or prior runs); no
  console errors.

---

### UT-03 — Headless session appears in the Sessions dropdown without a page reload (J-07 happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** Header session picker → `SessionPicker` dropdown list

**Preconditions:**
- The app is already open at `http://localhost:3691` in the browser **and left
  untouched** (do NOT reload during this case).

**Steps:**
1. With the browser tab already on `http://localhost:3691`, run the tiny-budget
   trigger curl (see "Conventions"); capture the returned `sessionId`.
2. Within ~5s, **without reloading the page**, click the **"Sessions"** button
   in the header to open the dropdown.
3. Read the rows under the **"Live Sessions"** section header.

**Expected Result:**
- A new row appears under **"Live Sessions"** corresponding to the headless
  session (its name will be a session label, e.g. "Session N", not a manual
  one you created).
- That row shows an iteration count (e.g. "0 iters" / "1 iter") and an
  **amber pulsing dot** to its left (run is active).
- The new row is present **without any manual page reload having been
  performed.**
- *What "broken" looks like:* the dropdown shows only the pre-existing
  session(s) and the new row appears **only after** a page reload — record as a
  fail of the "no manual reload" tab-appearance claim (the session itself is
  still openable via the reload fallback for downstream cases).

---

### UT-04 — Open the headless session and watch it progress live, no reload (J-08 happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `AutoRunBar` (running state) + right-panel history tree + left
activity log (2.5 s live merge)

**Preconditions:**
- A tiny-budget headless run was just triggered; its `sessionId` is known.
- The session is visible in the "Sessions" dropdown (reload **once** to
  discover it if needed — allowed per the discovery fallback; after this point
  do **not** reload again for this case).

**Steps:**
1. Click the **"Sessions"** button, then click the headless session's row in
   the dropdown.
2. Look at the strip **directly below the backtest-config bar**.
3. Without touching or reloading the page, watch for ~30–120 s.

**Expected Result:**
- Immediately on open, a **blue/primary-tinted strip** appears below the config
  bar with a **spinning loader** and text **"Automated run · iteration X/2"**
  (X is `1` or `2`; the `/2` is the budget `max_iterations`).
- While watching with **no manual reload**: the iteration number **X advances**
  (e.g. `1/2` → `2/2`), **new iteration cards appear in the right-hand history
  list**, and **new entries appear in the left activity log** (a backtest
  result and generated suggestions for at least one iteration).
- Polling visibly **stops after the run is terminal** (no further new cards
  appear once the strip leaves the running state).
- *What "broken" looks like:* the strip stays on "iteration 1/2" with a
  spinner indefinitely with no new cards unless you manually reload — that is a
  live-tracking (J-08) failure.

---

### UT-05 — Terminal stop reason shown + exactly one "★ Best" iteration marked (J-09 happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `AutoRunBar` (complete state) + `IterationCard` "★ Best" badge
(compact tree view)

**Preconditions:**
- The UT-04 headless session has reached a terminal state (continue watching
  the same open session; no reload).

**Steps:**
1. Keep the headless session open; wait until the strip below the config bar
   leaves the spinner/running state.
2. Read the strip text and tone.
3. Scan every iteration card in the right-hand history list for a badge.

**Expected Result:**
- The strip turns **green** with a check icon and reads exactly one of:
  - **"Automated run complete · robust targets met · X/2 iterations"** (stop
    reason criteria-met), or
  - **"Automated run complete · budget reached · X/2 iterations"** (stop
    reason budget-exhausted).
- **Exactly one** iteration card in the right-hand history list shows a small
  **amber pill containing a filled star and the word "Best"** ("★ Best"). No
  second card shows it.
- The "★ Best" card is not necessarily the highest raw-return card — it is the
  one the server's robust objective chose (`autoRun.bestIterationId`).
- *What "broken" looks like:* no badge at all, or two-plus badges, or the
  strip never leaves the spinner.

---

### UT-06 — "★ Best" badge also shows in the expanded iteration card (J-09)

**Type:** happy-path
**Priority:** P1
**Surface:** `IterationCard` expanded view "★ Best" badge

**Preconditions:**
- UT-05 done; exactly one iteration card shows the "★ Best" pill in the
  compact tree.

**Steps:**
1. Click the iteration card that shows the "★ Best" pill in the right-hand
   history list to open/expand its detail.
2. Look at the strategy-name heading in the expanded detail/card.

**Expected Result:**
- The **"★ Best" amber pill is also shown next to the strategy name** in the
  expanded view (badge appears in both the compact tree item and the expanded
  card — consistent identity for the server-chosen best iteration).

---

### UT-07 — Selecting an older run re-binds the RIGHT analysis panel (J-02 happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `IterationPanel` → `IterationDetailView` (`key={selected.id}`
remount)

**Preconditions:**
- A session with **≥ 2 completed runs/iterations** that have full detail. Use
  the terminal headless session from UT-05 (it has ≥ 2 iterations), or run two
  manual backtests first (see UT-13).

**Steps:**
1. Open the session; open the **most recent** completed iteration's detail in
   the right panel. Note its **Trade History count** (the heading reads
   `Trade History (N trades)`) and the first row's timestamp in the trades
   table, plus the shape of the **Equity Curve**.
2. Click the right panel's **back/up control** to return to the history list
   (or use the history list directly).
3. Click a **different, older** completed iteration in the history list.
4. Inspect the **RIGHT** panel only (not the left activity log).

**Expected Result:**
- The RIGHT panel's **"Trade History (N trades)"** heading shows a **different
  trade count** and/or a **different first-trade timestamp** than the run you
  viewed in step 1, the **Equity Curve redraws**, and the **"Walk-Forward
  Analysis"** section reflects the newly selected run.
- The RIGHT panel is **not pinned** to the previously viewed run's trades/equity.
- *What "broken" looks like:* the trades table and equity curve stay identical
  to the first run after selecting the older run (only the left conversation
  panel changed) — that is the J-02 bug not fixed / regressed.

---

### UT-08 — A failed iteration is still shown and the run still reaches a terminal state (error)

**Type:** error
**Priority:** P2
**Surface:** `AutoRunBar` + right-panel history (failed iteration record)

**Preconditions:**
- A headless run in which at least one iteration's LLM/backtest step fails
  (occurs naturally on flaky generations; otherwise observe across a couple of
  tiny runs). If no failure occurs, mark this case **N/A — could not trigger**
  (do not fail the phase on it).

**Steps:**
1. Trigger a tiny-budget headless run; open the session.
2. Watch the right-hand history list and the strip below the config bar.

**Expected Result:**
- Any iteration whose generation/backtest failed appears as an iteration card
  in a **failed/error state** (not silently dropped, not a blank card).
- The **strip still reaches a terminal state** (green "Automated run
  complete · …" or red "Automated run stopped") — it does **not** hang on the
  spinner forever because one iteration failed.

---

### UT-09 — Run-detail load failure shows a clear error pane with Retry, not a blank/crash (error)

**Type:** error
**Priority:** P2
**Surface:** `IterationPanel` lazy-detail error state

**Preconditions:**
- A session with at least one completed run whose heavy detail is lazy-loaded
  on selection. To force the error path, select a run immediately while the
  backend is briefly unreachable, OR observe naturally if a detail fetch fails.
  If it cannot be triggered, mark **N/A — could not trigger**.

**Steps:**
1. In the right panel's history list, click a run whose detail must be fetched.
2. If the detail fetch fails, observe the right panel.

**Expected Result:**
- The right panel shows **"Couldn't load this run's detail"** with the error
  text and a **"Retry"** button — **not** a blank pane, not a white-screen
  crash, and the history list stays reachable via the back control.
- Clicking **"Retry"** re-attempts the fetch.

---

### UT-10 — Manual (non-headless) session shows NO AutoRunBar (regression guard)

**Type:** regression
**Priority:** P1
**Surface:** `SessionContainer` — `AutoRunBar` absent for manual sessions

**Preconditions:**
- At least one headless session exists (so `AutoRunBar` code is exercised
  somewhere) plus a manual session.

**Steps:**
1. Open the **"Sessions"** dropdown and click **"+ New Session"** (this creates
   a fresh manual session) — or select a pre-existing manual session row.
2. Observe the strip area directly below the backtest-config bar.
3. (Optional cross-check) Switch to the headless session and confirm the strip
   **is** present there, then switch back to the manual session.

**Expected Result:**
- The manual session shows **no "Automated run …" strip** below the config bar.
- The headless session **does** show it — confirming the strip is correctly
  gated on `autoRun != null` and did not regress for manual sessions.

---

### UT-11 — J-02 re-fetch guard: A → B → re-select A still shows A's full detail (regression)

**Type:** regression
**Priority:** P2
**Surface:** `IterationDetailView` re-fetch guard (`useBacktest` lazy-detail)

**Preconditions:**
- A session with **≥ 2** completed runs that have full detail (terminal
  headless session from UT-05 works).

**Steps:**
1. Select run **A** (an older completed run); wait for its detail to load
   (Trade History table + Equity Curve visible). Note A's trade count.
2. Select a different run **B**; wait for B's detail to load.
3. Re-select run **A** again.

**Expected Result:**
- On re-selecting A, A's **full detail re-displays** — its Trade History table
  and Equity Curve are shown again with A's values (the same trade count as
  step 1).
- A does **not** become permanently stuck on a blank / "No detailed results
  for this run" / endless-loading pane (the stale `loadedDetailIdsRef` removal
  must allow re-fetch).

---

### UT-12 — Live poll preserves an already-open iteration's heavy detail (regression)

**Type:** regression
**Priority:** P2
**Surface:** Already-open iteration detail during the 2.5 s live poll

**Preconditions:**
- A headless run that is **still active** (strip shows the running spinner)
  **and** has at least one completed iteration with full detail.

**Steps:**
1. While the run is still active (spinner showing "Automated run · iteration
   X/2"), open one **completed** iteration's detail so its **Trade History
   table and Equity Curve are visible**.
2. Keep that detail open and do nothing for **≥ 3 seconds** (more than one
   2.5 s poll cycle); let at least one poll tick occur.

**Expected Result:**
- The open iteration's **Trade History table and Equity Curve do NOT blank
  out**, do not revert to a "Loading run detail…" spinner, and do not lose
  their rows when the background poll merges new lightweight data.
- *What "broken" looks like:* the open detail flickers to empty/loading on
  each ~2.5 s poll — that is the heavy-detail-preserving merge regressing.

---

### UT-13 — Manual NL backtest still works end-to-end (regression J-01)

**Type:** regression
**Priority:** P1
**Surface:** Activity log chat input → manual backtest flow

**Preconditions:**
- A manual session (use "+ New Session" from the Sessions dropdown).

**Steps:**
1. In the config bar set **Symbol** = `BTC/USDT`, **Timeframe** = `1 Hour`,
   **Start** = `2024-01-01`, **End** = `2024-01-15`, **Capital** = `10000`.
2. In the left panel's chat box (placeholder **"Describe a trading
   strategy..."**) type: `Buy when RSI crosses below 30, sell when it crosses
   above 70`.
3. Press **Enter** (or click the blue send/paper-plane button to the right of
   the text box).
4. Wait for the run to complete.

**Expected Result:**
- The activity log streams progress and completes without an error entry.
- The right panel shows a completed iteration with an **Equity Curve**, a
  metrics summary, and a **"Trade History (N trades)"** table with rows.
- A new iteration/run entry is added to the right-hand history list.

---

### UT-14 — Walk-Forward + AI insights still work on a completed run (regression J-03 / J-04)

**Type:** regression
**Priority:** P2
**Surface:** `IterationDetailView` Walk-Forward Analysis + insights/suggestions

**Preconditions:**
- At least one completed run exists (from UT-13).

**Steps:**
1. Open the completed run's detail in the right panel.
2. In the **"Walk-Forward Analysis"** section, click the **"Run Walk-Forward"**
   button (it reads **"Re-run"** if walk-forward already ran).
3. Wait for it to finish.
4. Trigger AI insights/suggestions for that run (use the suggestion/insights
   affordance in the activity log for that iteration).

**Expected Result:**
- A **WFE badge** appears (e.g. "WFE 0.62"), a per-window breakdown and a
  combined OOS equity curve render in the Walk-Forward Analysis section.
- At least **one ranked improvement suggestion** renders in the activity log
  for the run.
- No error overlay; the run's other detail (trades/equity) stays intact.

---

### UT-15 — Reference-data controls populated + legacy in-browser "Auto Run" not broken (regression J-05 + coexistence)

**Type:** regression
**Priority:** P1
**Surface:** `BacktestConfigBar` symbol/timeframe controls + legacy in-browser
"Auto Run" button

**Preconditions:**
- Fresh app load with at least one completed iteration that has suggestions
  (so the legacy "Auto Run" button is enabled — it appears only when a
  complete iteration with suggestions exists).

**Steps:**
1. Navigate to `http://localhost:3691`.
2. Click the **Timeframe** dropdown in the config bar and inspect its options;
   click into the **Symbol** field and inspect its autocomplete datalist.
3. With a completed iteration present, locate the violet **"Auto Run (N)"**
   button (lightning icon) at the right end of the config bar and click it.
   Then click the amber **"Stop (x/y)"** button to halt it (do not let it run
   to completion).

**Expected Result:**
- The **Timeframe** dropdown is populated (e.g. "1 Hour", "4 Hours", "1 Day"
  …) and the **Symbol** field offers suggestions — reference data loaded
  (J-05 not regressed; fallback list is acceptable if the endpoint is briefly
  down).
- The legacy violet **"Auto Run (N)"** button is **present and starts** its
  in-browser loop when clicked (the config bar switches to an amber
  **"Stop (x/y)"** button); clicking Stop halts it. No console crash.
- This legacy button is **expected to coexist** with the new headless API this
  iteration — its presence is **not** a regression.

---

### UT-16 — Session-picker activity dot pulses amber while headless run is active, clears at terminal (ux)

**Type:** ux
**Priority:** P2
**Surface:** Header session picker → `SessionPicker` status dot + "running"
label

**Preconditions:**
- A tiny-budget headless run is active; its `sessionId` is known and the
  session row is visible in the dropdown (reload once to discover if needed).

**Steps:**
1. Open the **"Sessions"** dropdown while the headless run is still active.
2. Look at the dot to the left of the headless session's row and the small
   text in that row.
3. Keep the dropdown open (or reopen it) and wait until the run reaches a
   terminal state (cross-reference the strip in UT-05). Do not reload.
4. Re-inspect the same row's dot and text.

**Expected Result:**
- While running: the headless row shows an **amber pulsing dot** and an amber
  **"running"** label.
- After the run is terminal: that row's dot is **no longer amber/pulsing** (it
  becomes a steady emerald dot) and the **"running"** label is gone — the
  change is reflected **without a manual page reload**.

---

### UT-17 — Session-picker shows the headless session's best return without opening it (ux)

**Type:** ux
**Priority:** P3
**Surface:** Header session picker → `SessionPicker` best-return label

**Preconditions:**
- A headless session has **≥ 1 completed iteration** (a backtest result
  exists). The session row is visible in the dropdown (reload once to discover
  if needed).

**Steps:**
1. **Without clicking into / opening** the headless session, open the
   **"Sessions"** dropdown.
2. Read the headless session's row.

**Expected Result:**
- The row shows a signed percentage best-return figure, e.g. **"+3.2%"** in
  emerald or **"-1.5%"** in red, **without the session having been opened
  first** (derived from the lightweight completed-iteration return).

---

### UT-18 — AutoRunBar is announced to assistive tech (ux / accessibility)

**Type:** ux
**Priority:** P3
**Surface:** `AutoRunBar` (`role="status"` `aria-live="polite"`)

**Preconditions:**
- A headless session is open and the AutoRunBar strip is visible.

**Steps:**
1. Open the headless session.
2. Inspect the AutoRunBar strip element (browser dev tools / accessibility
   inspector).

**Expected Result:**
- The strip element has `role="status"` and `aria-live="polite"`, so a screen
  reader announces the transition from "Automated run · iteration X/2" to the
  terminal "Automated run complete · …" / "Automated run stopped" text without
  manual focus.

---

### UT-19 — "★ Best" badge is discoverable and self-explanatory (ux)

**Type:** ux
**Priority:** P3
**Surface:** `IterationCard` "★ Best" `BestBadge` tooltip

**Preconditions:**
- A terminal headless session with a marked best iteration (UT-05 done).

**Steps:**
1. Open the headless session; locate the iteration card with the "★ Best"
   amber pill.
2. Hover the pointer over the "★ Best" pill.

**Expected Result:**
- The pill is a clearly visible amber chip with a filled star icon and the
  word **"Best"**.
- Hovering shows the tooltip text **"Best iteration — selected by the robust
  walk-forward objective"** — the marker explains *why* it is best (not just
  raw return), with no developer knowledge required.

---

### UT-20 — AutoRunBar "stopped" terminal styling (ux / error, conditional)

**Type:** ux
**Priority:** P3
**Surface:** `AutoRunBar` — stopped state

**Preconditions:**
- A headless run that ends in the **stopped** terminal state. There is **no UI
  stop control or stop endpoint this iteration** (J-11 deferred), so this state
  is normally only reachable if the loop is internally cancelled / errors into
  `stopped`. If it cannot be produced, mark this case **N/A — stopped state
  not reachable in iter-1** (do not fail the phase on it).

**Steps:**
1. If a headless session reaches the `stopped` terminal state, open it.
2. Read the strip below the config bar.

**Expected Result:**
- The strip is **red-toned** with a **StopCircle icon** and reads **"Automated
  run stopped"** (visually distinct from the green "complete" state and the
  blue "running" state).

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | App shell + Sessions picker loads | smoke | P1 | App shell / header |
| UT-02 | Manual session has no AutoRunBar (baseline) | smoke | P1 | `SessionContainer` |
| UT-03 | Headless session appears in dropdown w/o reload (J-07) | happy-path | P1 | `SessionPicker` list |
| UT-04 | Live progress, no reload (J-08) | happy-path | P1 | `AutoRunBar` + history/activity live merge |
| UT-05 | Terminal stop reason + one "★ Best" (J-09) | happy-path | P1 | `AutoRunBar` complete + `IterationCard` |
| UT-06 | "★ Best" in expanded card (J-09) | happy-path | P1 | `IterationCard` expanded |
| UT-07 | Older run re-binds RIGHT panel (J-02) | happy-path | P1 | `IterationDetailView` remount |
| UT-08 | Failed iteration still terminal | error | P2 | `AutoRunBar` + history |
| UT-09 | Detail-load failure pane + Retry | error | P2 | `IterationPanel` error state |
| UT-10 | Manual session: no AutoRunBar (guard) | regression | P1 | `SessionContainer` |
| UT-11 | J-02 re-fetch guard A→B→A | regression | P2 | lazy-detail re-fetch guard |
| UT-12 | Live poll preserves open detail | regression | P2 | open detail during poll |
| UT-13 | Manual NL backtest works (J-01) | regression | P1 | activity log chat flow |
| UT-14 | Walk-Forward + insights work (J-03/J-04) | regression | P2 | `IterationDetailView` WF/insights |
| UT-15 | Ref data + legacy Auto Run intact (J-05) | regression | P1 | `BacktestConfigBar` |
| UT-16 | Session-picker amber dot pulses/clears | ux | P2 | `SessionPicker` status dot |
| UT-17 | Session-picker best-return w/o opening | ux | P3 | `SessionPicker` best-return |
| UT-18 | AutoRunBar aria-live announced | ux | P3 | `AutoRunBar` a11y |
| UT-19 | "★ Best" tooltip explains selection | ux | P3 | `BestBadge` tooltip |
| UT-20 | AutoRunBar stopped state styling | ux | P3 | `AutoRunBar` stopped (conditional) |

**P1 tests must all pass for the browser-QA verdict to be PASS.** UT-08, UT-09,
and UT-20 may be marked **N/A — could not trigger** without failing the phase
(their trigger conditions are not deterministically reachable in iter-1). API
request/response, persistence, and anti-goal assertions are covered by the
functional test plan (TC-01–TC-16) and are intentionally **not** duplicated here.

**Surface coverage:** all 12 UI-surface-map rows are covered — picker list
(UT-03), picker dot (UT-16), picker best-return (UT-17), AutoRunBar
running/complete (UT-04/05/18), AutoRunBar stopped (UT-20), AutoRunBar absent
for manual (UT-02/10), "★ Best" compact (UT-05/19), "★ Best" expanded (UT-06),
detail remount J-02 (UT-07), re-fetch guard (UT-11/09), live merge J-08
(UT-04), open-detail-preserved-during-poll (UT-12); plus regression J-01/03/04/05
+ legacy auto-run (UT-13/14/15).
