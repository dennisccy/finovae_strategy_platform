# Phase goal-auto-money-printer-iter-2 — UI Test Plan

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3691
**Backend URL:** http://localhost:8000 (or `$CHAIN_BACKEND_PORT`)

---

## Conventions & shared preconditions

- Single-page app — there are **no routes**. All surfaces live on `http://localhost:3691`.
- Backend + frontend running; `OPENAI_API_KEY` set (auto-run generates strategies).
- "Tiny budget" = the number input immediately to the right of the **Auto Run**
  button set to **1 or 2**. "Still-running budget" = that input set to **8** (or higher).
- **Baseline state** (needed by most auto-run tests): a session that has **≥1
  iteration card in the right panel whose status is "Complete" AND for which
  suggestion chips have appeared in the left Activity panel**. Only then does the
  violet **"Auto Run (N)"** button appear in the config bar (`canAutoRun`). To
  create it from a blank session, perform UT-15 first (one manual backtest), then
  wait until suggestion chips render in the left Activity log.
- Clicking **Auto Run** does **not** iterate the current session — it creates a
  **new backend `Auto: …` session**. Progress/Stop/AutoRunBar are observed on
  that **new** session, opened from the **Sessions** dropdown (top-right).
- Exact element references:
  - **Auto Run button**: violet button, lightning (`Zap`) icon, text `Auto Run (N)`
    where N = the iteration-count input value (default `1`), pinned to the
    far right of the config bar. Shown only when not running.
  - **Iteration-count input**: small number box immediately right of the Auto Run
    button (min 1, max 100).
  - **Worker badge**: pill right of the input, e.g. `1w` / `2w`.
  - **Stop button**: amber button, square (`Square`) icon, text `Stop (x/N)`,
    same far-right slot, shown only while the open session's auto-run is active.
  - **AutoRunBar**: slim status strip directly **below** the config bar, present
    **only** for server-driven (`Auto: …`) sessions. `role="status"`.
    - running/queued → spinner + `Automated run · iteration X/N` (blue strip);
      `(queued)` appended while queued.
    - stopped → red stop-circle icon + `Automated run stopped` (red strip).
    - complete → green check + `Automated run complete · <reason> · X/N iterations`
      where `<reason>` is `robust targets met` | `budget reached` | `finished`
      (green strip).
  - **"Best" pill**: amber pill with a filled star icon and the text `Best`,
    rendered on the robust-best iteration card in the right Iterations panel
    (tooltip: "Best iteration — selected by the robust walk-forward objective").
  - **Sessions dropdown**: header button labelled **Sessions**; each row has a
    status dot, name, iteration count, best-return %, and a `running` badge.
  - **New auto-session name**: `Auto: <first 40 chars of the strategy text>…`.
  - **Strategy input**: left Activity panel footer — a textarea with placeholder
    `Describe a trading strategy...` and a blue paper-plane (`Send`) submit button.

---

## Test Cases

---

### UT-01 — App loads, two-panel workstation renders (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (single-page app)

**Preconditions:**
- Frontend running at http://localhost:3691; backend running.

**Steps:**
1. Navigate to `http://localhost:3691`
2. Wait for the page to fully load (the **Sessions** button stops showing its spinner)

**Expected Result:**
- Header shows the title "Finovae Strategy Platform", a "Sessions" button, and "v0.3.0"
- The config bar is visible with the labels "Symbol", "Timeframe", "Start", "End", "Capital", "Exchange"
- Two panels render: a left Activity panel ending in a "Describe a trading strategy..." textarea, and a right panel reading "No Iterations Yet" (for a fresh session)
- No blank screen, no red error overlay, no uncaught console errors

---

### UT-02 — "Auto Run" affordance is gated until a completed iteration has suggestions (ux gating / smoke)

**Type:** ux
**Priority:** P1
**Surface:** `BacktestConfigBar` — Auto Run control

**Preconditions:**
- A brand-new session with **zero** iterations is open (use "+ New Session" in the Sessions dropdown if needed).

**Steps:**
1. Navigate to `http://localhost:3691` on a fresh session
2. Inspect the far-right end of the config bar (before running anything)
3. Submit one strategy (see UT-15 steps 2–3) and wait until the right panel shows a "Complete" iteration card **and** suggestion chips appear in the left Activity panel
4. Inspect the far-right end of the config bar again

**Expected Result:**
- Step 2: **no** violet "Auto Run" button is present (nothing to iterate from yet)
- Step 4: a violet **"Auto Run (1)"** button (lightning icon) now appears at the far right, with a number input and a worker badge (e.g. `1w`) beside it
- The button is enabled (not greyed out) when the session is idle

---

### UT-03 — J-10 happy path: config-bar "Auto Run" starts a server-driven session (happy-path)

**Type:** happy-path
**Priority:** P1
**Surface:** `BacktestConfigBar` Auto Run button → `POST /api/auto-sessions`; `ActivityLog`; `SessionPicker`

**Preconditions:**
- Baseline state met (a "Complete" iteration with suggestions; UT-02 step 4 reached).

**Steps:**
1. In the config bar set the iteration-count number input (right of the Auto Run button) to `2`
2. Click the violet **"Auto Run (2)"** button
3. Read the newest entry at the bottom of the left Activity panel
4. Click the **Sessions** button (top-right) and wait up to 6 seconds
5. Click the new **"Auto: …"** row in the dropdown

**Expected Result:**
- Step 3: a new info entry appears reading exactly: *"Started a server-driven Auto Run (up to 2 iterations). It runs on the backend and continues even if you close or reload this tab — a new "Auto: …" session appears in the session list shortly."*
- Step 3: **no** new iteration cards are appended to the *current* session (the loop does NOT run in this browser/session)
- Step 4: within ~5 s a new session named **"Auto: …"** (prefixed `Auto: ` + the start of the strategy text) appears in the "Live Sessions" list with a pulsing amber dot and a `running` badge
- Step 5: that session opens and a slim **AutoRunBar** strip appears directly below the config bar showing a spinner and **"Automated run · iteration X/2"**; X advances over time without any manual reload

---

### UT-04 — J-10: server-driven run survives a mid-run browser reload (happy-path)

**Type:** happy-path
**Priority:** P1
**Surface:** Browser tab reload during a server-driven run

**Preconditions:**
- UT-03 completed; the "Auto: …" session is open and its AutoRunBar shows **"Automated run · iteration X/2"** (still running).

**Steps:**
1. Note the current value of **X** in "Automated run · iteration X/2"
2. Hard-reload the browser tab (Ctrl+Shift+R / Cmd+Shift+R)
3. After reload, click **Sessions** and re-select the same **"Auto: …"** session
4. Observe the AutoRunBar for up to 90 seconds

**Expected Result:**
- After reload the AutoRunBar still renders for the "Auto: …" session and shows **"Automated run · iteration Y/2"** with **Y ≥ X** (progress was not lost / restarted)
- The iteration count visibly advances (or is already terminal) without any in-browser loop
- The run ultimately reaches a terminal state: the strip turns green and reads **"Automated run complete · budget reached · 2/2 iterations"**, and exactly one iteration card in the right panel shows the amber **"Best"** star pill

---

### UT-05 — J-11: Stop a running auto-session from the UI Stop button (happy-path)

**Type:** happy-path
**Priority:** P1
**Surface:** `BacktestConfigBar` Stop button → `POST /api/auto-sessions/{id}/stop`; `AutoRunBar`; "Best" pill

**Preconditions:**
- Baseline state met. Backend running.

**Steps:**
1. Set the iteration-count input to `8`
2. Click **"Auto Run (8)"**
3. Click **Sessions**, wait ~5 s, open the new **"Auto: …"** session
4. Wait until the AutoRunBar shows **"Automated run · iteration X/8"** with X ≥ 1 and at least one "Complete" iteration card is visible in the right panel
5. Note the number of iteration cards in the right panel
6. Click the amber **"Stop (x/8)"** button at the far right of the config bar
7. Observe the AutoRunBar and the right panel for up to 60 seconds

**Expected Result:**
- Within a few seconds the AutoRunBar turns red, shows a stop-circle icon, and reads exactly **"Automated run stopped"**
- The number of iteration cards in the right panel does **not** increase after the click (no iterations appended post-stop)
- Exactly one iteration card retains the amber **"Best"** star pill (best-so-far preserved, not cleared, not re-assigned to the highest raw return)
- The Stop button is replaced (no longer shows "Stop (x/8)") once the run is terminal

---

### UT-06 — J-11: an API-issued stop converges in the UI with no manual reload (happy-path)

**Type:** happy-path
**Priority:** P1
**Surface:** `AutoRunBar` live poll convergence (API stop reflected in UI)

**Preconditions:**
- Backend + frontend running; ability to start a still-running auto-session.

**Steps:**
1. Set the iteration-count input to `8`, click **"Auto Run (8)"**
2. Open the new "Auto: …" session; confirm AutoRunBar shows **"Automated run · iteration X/8"**
3. Obtain that session's id (open the Sessions dropdown — or read it from a `GET http://localhost:8000/api/sessions` response)
4. In a terminal run: `curl -s -X POST "http://localhost:8000/api/auto-sessions/<SID>/stop"`
5. **Without** reloading or clicking anything in the browser, watch the AutoRunBar for up to 60 seconds

**Expected Result:**
- The `curl` returns quickly (sub-second) with a 2xx body
- Within the live-poll interval (a few seconds) the AutoRunBar in the still-open browser flips to the red **"Automated run stopped"** state with **no manual page reload**
- Iteration count is frozen at the stop point; one "Best" star pill remains

---

### UT-07 — Per-iteration card "Auto Run" action starts a backend auto-session (happy-path)

**Type:** happy-path
**Priority:** P1
**Surface:** `IterationPanel` / `IterationCard` per-card Auto Run action → `POST /api/auto-sessions`

**Preconditions:**
- A session with ≥1 "Complete" iteration card in the right Iterations panel.

**Steps:**
1. In the right Iterations panel, hover over a **completed** iteration card
   (compact card: action icons fade in on hover; the latest full card shows a
   labelled row)
2. Click the violet **"Auto Run"** action on that card (lightning icon; labelled
   "Auto Run" on the latest card, icon-only with tooltip "Auto Run" on compact cards)
3. Read the newest entry in the left Activity panel
4. Click **Sessions**, wait ~5 s

**Expected Result:**
- Step 3: the same info entry as UT-03 appears ("Started a server-driven Auto Run (up to N iteration(s))… a new "Auto: …" session appears in the session list shortly.")
- Step 3: **no** in-browser iteration cards are appended to the current session
- Step 4: a new **"Auto: …"** session appears in the Sessions dropdown, pinned to that card's strategy/config; opening it shows the AutoRunBar progressing

---

### UT-08 — Activity log info entry text is accurate and discoverable (ux / content)

**Type:** ux
**Priority:** P2
**Surface:** `ActivityLog` (left panel)

**Preconditions:**
- Baseline state met.

**Steps:**
1. Set the iteration-count input to `1`
2. Click **"Auto Run (1)"**
3. Read the newest entry at the bottom of the left Activity panel

**Expected Result:**
- The entry text reads **verbatim**: *"Started a server-driven Auto Run (up to 1 iteration). It runs on the backend and continues even if you close or reload this tab — a new "Auto: …" session appears in the session list shortly."*
- Note the singular "1 iteration" (not "1 iterations"); with input `2` the text reads "up to 2 iterations"
- The entry is plainly visible at the bottom of the Activity log (not hidden / not requiring scroll-up)

---

### UT-09 — Auto Run start failure surfaces an error entry (error)

**Type:** error
**Priority:** P2
**Surface:** `ActivityLog` error entry on `POST /api/auto-sessions` failure

**Preconditions:**
- Baseline state met. Ability to stop/kill the backend (or block `/api/auto-sessions`).

**Steps:**
1. Stop the backend process (so `POST /api/auto-sessions` fails)
2. Click the **"Auto Run (1)"** button
3. Read the newest entry in the left Activity panel
4. Restart the backend

**Expected Result:**
- A red **error** entry appears in the Activity log reading **"Auto Run failed to start: …"** (followed by the failure reason)
- No "Auto: …" session is created (the Sessions dropdown gains no new row)
- The app does not crash or show a blank screen; the config bar / Auto Run button remain usable after the backend is restored

---

### UT-10 — Stop on an already-terminal auto-session is a silent no-op in the UI (error / edge)

**Type:** error
**Priority:** P2
**Surface:** `stopAutoSession` idempotent/404 handling (no UI error, no state regression)

**Preconditions:**
- An "Auto: …" session that has already reached a terminal state — reuse the
  **stopped** session from UT-05, or a `budget reached` session from a
  max-iterations-1 run (UT-08 then let it finish).

**Steps:**
1. Open the terminal "Auto: …" session; note its AutoRunBar text (e.g. "Automated run stopped" or "Automated run complete · budget reached · 1/1 iterations") and the "Best" pill
2. The Stop button is not shown for a terminal run — instead issue a redundant stop via terminal: `curl -s -X POST "http://localhost:8000/api/auto-sessions/<SID>/stop"`
3. Watch the still-open session's AutoRunBar for ~15 seconds

**Expected Result:**
- No error toast and no red "failed" entry appears in the Activity log
- The AutoRunBar does **not** regress: a `complete` session stays "Automated run complete …" (it is NOT flipped to "Automated run stopped"); a `stopped` session stays "Automated run stopped"
- The "Best" pill and iteration count are unchanged

---

### UT-11 — Iteration-count input clamps to 1–100 and drives the budget (validation)

**Type:** validation
**Priority:** P2
**Surface:** `BacktestConfigBar` iteration-count number input

**Preconditions:**
- Baseline state met.

**Steps:**
1. In the iteration-count input (right of Auto Run) type `0`, then click elsewhere
2. Observe the Auto Run button label
3. Type `250` in the same input, click elsewhere
4. Observe the Auto Run button label
5. Set it to `2`, click **"Auto Run (2)"**, open the new "Auto: …" session

**Expected Result:**
- After step 1: the value is clamped up to `1`; the button reads **"Auto Run (1)"** (never "Auto Run (0)")
- After step 3: the value is clamped down to `100`; the button reads **"Auto Run (100)"** (never higher)
- After step 5: the AutoRunBar of the new session shows the denominator matching the chosen value, i.e. **"Automated run · iteration X/2"**

---

### UT-12 — New "Auto: …" session is discoverable in the Sessions dropdown within ~5 s (ux)

**Type:** ux
**Priority:** P2
**Surface:** `SessionPicker` dropdown + App.tsx discovery poll

**Preconditions:**
- Baseline state met.

**Steps:**
1. Click **"Auto Run (1)"**
2. Immediately open the **Sessions** dropdown and start a stopwatch
3. Keep the dropdown open (or reopen it) and watch the "Live Sessions" list

**Expected Result:**
- Within ~5 seconds (one discovery-poll tick) a new row prefixed **"Auto: "** appears in "Live Sessions" **without a manual page reload**
- That row shows a pulsing amber status dot and an amber **running** badge while the run is active
- The session count badge on the **Sessions** button increments accordingly

---

### UT-13 — Regression J-08: no stale AutoRunBar terminal under rapid session switching (regression)

**Type:** regression
**Priority:** P1
**Surface:** `SessionContainer`/`AutoRunBar` ownership + `SessionPicker` SessionDot

**Preconditions:**
- Backend + frontend running. At least 3 sessions available: a still-running
  "Auto: …" session (start with budget `8`), the originating session, and one
  more (use "+ New Session").

**Steps:**
1. Start an Auto Run with the iteration-count input at `8`; confirm the new "Auto: …" session's AutoRunBar shows **"Automated run · iteration X/8"**
2. Using the **Sessions** dropdown, rapidly switch: Auto session → other session → originating session → back to the Auto session. Repeat this cycle quickly 3–4 times
3. Land on the still-running "Auto: …" session and read its AutoRunBar
4. Open the **Sessions** dropdown and read the status dot/badge on that same "Auto: …" row

**Expected Result:**
- After rapid switching, the still-running "Auto: …" session's AutoRunBar shows the **running** state (spinner + "Automated run · iteration X/8") — **never** a stale "Automated run complete …" or "Automated run stopped"
- In the dropdown, that session's row shows the **pulsing amber dot + "running" badge** — i.e. the list indicator and the in-session AutoRunBar **agree** (no mismatch)
- An explicit FAIL is: the bar shows a terminal state while the run is still progressing, or the list dot/badge disagrees with the bar

---

### UT-14 — Regression J-02: selecting a prior run re-binds the RIGHT analysis panel (regression)

**Type:** regression
**Priority:** P1
**Surface:** `IterationPanel` / `IterationDetailView` right-panel re-bind on history selection

**Preconditions:**
- A session with **≥2 completed iteration cards** with different results
  (e.g. run UT-15 twice with different strategies, or open an "Auto: …" session
  that produced ≥2 iterations).

**Steps:**
1. In the right Iterations panel, click the **most recent** completed iteration card; note its equity curve shape, the first row of its trades table, and its walk-forward section
2. Click **"Back to history"** (top-left of the detail pane)
3. Click a **different / older** completed iteration card in the list
4. Inspect the RIGHT analysis pane (equity chart, trades table, walk-forward)

**Expected Result:**
- After step 3 the RIGHT pane re-binds entirely to the **older** run: its equity curve, its trades table rows, and its walk-forward all change to that run's values
- It does **not** keep showing the previous run's equity curve/trades (explicit FAIL if the right-panel chart/trades stay unchanged while only a summary changed)
- Switching back to the newer card restores the newer run's right-panel data

---

### UT-15 — Regression J-01: manual natural-language backtest still works end-to-end (regression)

**Type:** regression
**Priority:** P1
**Surface:** Manual backtest flow (must not regress after in-browser loop deletion)

**Preconditions:**
- Backend + frontend running; `OPENAI_API_KEY` set. A session open.

**Steps:**
1. Navigate to `http://localhost:3691`
2. In the config bar set: Symbol `BTC/USDT`, Timeframe `1 Hour`, Start `2024-01-01`, End `2024-02-01`, Capital `10000`
3. In the left Activity panel textarea (placeholder "Describe a trading strategy...") type: `Buy when RSI crosses below 30, sell when it crosses above 70`
4. Press Enter (or click the blue paper-plane Send button)
5. Wait for completion (up to ~90 s); open the resulting iteration card

**Expected Result:**
- An iteration card appears in the right panel, transitions through "Generating" / "Executing" to **"Complete"**, then shows metrics (return %, trades, DD, WR, SR)
- Opening the card shows a non-empty equity curve and a trades table in the right pane
- Suggestion chips appear in the left Activity panel after completion
- No console error referencing the removed `startAutoRun` / in-browser auto-run loop; the manual flow is unaffected by the rewire

---

### UT-16 — AutoRunBar terminal "complete" state renders with the correct reason (ux)

**Type:** ux
**Priority:** P3
**Surface:** `AutoRunBar` terminal complete rendering

**Preconditions:**
- An "Auto: …" session that reached `budget reached` (run with budget `1` and let it finish — UT-08 then wait).

**Steps:**
1. Open that terminal "Auto: …" session
2. Read the AutoRunBar strip

**Expected Result:**
- The strip is green, shows a check-circle icon, and reads **"Automated run complete · budget reached · 1/1 iterations"**
- For a criteria-met run the middle phrase would instead be **"robust targets met"**
- The strip preserves `role="status"` and the amber **"Best"** pill is shown on one iteration card

---

### UT-17 — Originating session does not run a second in-browser loop (regression)

**Type:** regression
**Priority:** P2
**Surface:** Originating session after Auto Run (anti-goal: no in-browser iterate loop)

**Preconditions:**
- Baseline state met. Note the originating session's exact iteration-card count.

**Steps:**
1. Record the number of iteration cards in the originating session's right panel (call it C)
2. Click **"Auto Run (2)"**
3. **Stay on the originating session** (do NOT open the "Auto: …" session). Wait 60 seconds
4. Re-count the originating session's iteration cards; check the AutoRunBar area

**Expected Result:**
- The originating session's iteration-card count remains **exactly C** — no new cards are generated locally (the loop is purely server-side)
- The originating session shows **no** AutoRunBar strip and **no** "Stop (x/N)" button (it is not server-driven; only the new "Auto: …" session is)
- The only change in the originating session is the single info entry in the Activity log

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | App loads, two-panel workstation | smoke | P1 | `/` |
| UT-02 | Auto Run gated until completed+suggestions | ux | P1 | ConfigBar Auto Run |
| UT-03 | J-10 start server-driven from config bar | happy-path | P1 | Auto Run → API / ActivityLog / SessionPicker |
| UT-04 | J-10 survives mid-run reload | happy-path | P1 | tab reload |
| UT-05 | J-11 Stop from UI button | happy-path | P1 | Stop button / AutoRunBar / Best pill |
| UT-06 | J-11 API stop converges in UI live | happy-path | P1 | AutoRunBar live poll |
| UT-07 | Per-card Auto Run starts backend session | happy-path | P1 | IterationCard action |
| UT-08 | Activity log info entry text | ux | P2 | ActivityLog |
| UT-09 | Auto Run start failure error entry | error | P2 | ActivityLog error |
| UT-10 | Stop already-terminal is silent no-op | error | P2 | stopAutoSession idempotent |
| UT-11 | Iteration-count clamps 1–100, drives budget | validation | P2 | ConfigBar input |
| UT-12 | New "Auto: …" discoverable ≤5 s | ux | P2 | SessionPicker / poll |
| UT-13 | J-08 no stale terminal under rapid switching | regression | P1 | AutoRunBar ownership / SessionDot |
| UT-14 | J-02 right-panel re-bind on history select | regression | P1 | IterationPanel / DetailView |
| UT-15 | J-01 manual backtest still works | regression | P1 | manual flow |
| UT-16 | AutoRunBar complete state + reason | ux | P3 | AutoRunBar terminal |
| UT-17 | No second in-browser loop in origin session | regression | P2 | originating session |

**P1 tests must all pass for the browser QA verdict to be PASS.**
P1: UT-01, UT-02, UT-03, UT-04, UT-05, UT-06, UT-07, UT-13, UT-14, UT-15.
