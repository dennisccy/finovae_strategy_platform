# Phase goal-financial_free-iter-3 — UI Test Plan

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3692

---

## Scope & Setup Notes

This iteration adds **three new counter chips** (token spend, USD cost, configs-explored) to the `AutoSessionStatusStrip` at the top of the Iterations panel, and renders **open-universe configuration cards** streaming through the existing iteration history.

**Critical setup constraint (from user-visible-changes):** there is **no in-UI control** to start an open-universe run this iteration. The in-UI "Auto Run" control starts only a **pinned-config** session. To exercise the token/USD/configs chips and streaming config cards, an open-universe run must be launched via the API first, then **tracked** in the UI:

```bash
# Launch an open-universe run (used by several test cases below as a precondition).
# Tiny token cap to force fast budget-exhaustion for terminal-state tests.
curl -s -X POST http://localhost:8000/api/auto-sessions \
  -H 'Content-Type: application/json' \
  -d '{"objective":"robust","budget":{"max_configs":2,"max_tokens":5000,"max_usd":0.05,"max_wall_clock_seconds":120}}'
# -> returns 200 with the created session id; open that session in the UI.
```

The UI reads every counter **read-only** from `GET /api/sessions/{id}` → `autoRun.budget`. Browser pixels may be throttled in a hidden/background tab (known render throttle) — keep the tab foregrounded; if pixels are blank, cross-check the same values against the `autoRun.budget` payload from the endpoint and say so.

---

## Test Cases

<!-- Test IDs use UT-XX prefix to distinguish from functional test plan TC-XX IDs. -->

---

### UT-01 — Iterations panel + status strip render without errors (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (Iterations panel → `AutoSessionStatusStrip`)

**Preconditions:**
- Frontend running at http://localhost:3692, backend at http://localhost:8000
- At least one automated (Auto Run) session exists — launch the open-universe run from the Setup Notes above, OR start a pinned Auto Run via the in-UI control

**Steps:**
1. Navigate to `http://localhost:3692`
2. Open the automated session created above (select it from the session list / workstation)
3. Look at the top of the **Iterations** panel
4. Open the browser devtools Console tab (F12)

**Expected Result:**
- A bordered status strip is pinned at the top of the Iterations panel
- The strip shows a status badge (e.g. "Running" with a spinning icon, or a terminal label such as "Budget exhausted")
- A right-aligned counter group is visible containing chips separated by `·`
- No red console errors; page is not blank

---

### UT-02 — Token-spend chip shows live `spend / cap tok` and increases (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iterations panel → token-spend chip)

**Preconditions:**
- An **open-universe** run is **active** (status "Running"). Launch with a slightly larger token cap so it stays active long enough to observe growth, e.g. `"max_tokens":50000`, `"max_configs":2`

**Steps:**
1. Navigate to `http://localhost:3692` and open the active open-universe session
2. In the status strip counter group, locate the chip ending in `tok` (hover shows tooltip "AI tokens spent / cap")
3. Read its value (e.g. `1.2k / 50k tok`)
4. Wait ~5 seconds (≈2 poll cycles at 2.5s) and read the chip again

**Expected Result:**
- The chip renders as `<spend> / <cap> tok` with the spend value formatted compactly (e.g. `1.2k`, integers under 1000 shown as-is)
- The spend (left) number is **≥** its earlier reading and never exceeds the cap (right number, e.g. `50k`)
- The cap portion (` / 50k`) is present because `max_tokens` was supplied

---

### UT-03 — USD-cost chip shows 4-dp `$spend / $cap` and rises with tokens (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iterations panel → USD-cost chip)

**Preconditions:**
- Same active open-universe run as UT-02

**Steps:**
1. On the open session, locate the chip beginning with `$` (hover tooltip "AI cost (USD) spent / cap")
2. Read its value (e.g. `$0.0123 / $0.0500`)
3. Wait ~5 seconds and read it again

**Expected Result:**
- The chip renders as `$0.0xxx / $0.0xxx` — both spent and cap shown to **exactly 4 decimal places**
- The spent value is **≥** its earlier reading and stays **≤** the cap
- The spent USD moves in step with the token chip (rises as tokens accrue)

---

### UT-04 — Configs chip replaces rounds chip for open-universe runs (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iterations panel → configs chip)

**Preconditions:**
- An open-universe run (budget carries `max_configs`, e.g. `max_configs:2`), active or terminal

**Steps:**
1. Open the open-universe session at `http://localhost:3692`
2. Inspect the first chip in the counter group (leftmost, hover tooltip "Configs explored / max (open-universe search)")
3. Confirm no `rounds` chip is present in the strip

**Expected Result:**
- The leftmost chip reads `<configsDone>/<maxConfigs> configs` (e.g. `1/2 configs`)
- There is **NO** `… rounds` chip anywhere in the strip
- As the run progresses, `configsDone` increments toward `maxConfigs` (e.g. `1/2` → `2/2`)

---

### UT-05 — Best badge appears on terminal open-universe run, matches API (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iterations panel → Best badge)

**Preconditions:**
- An open-universe run that has reached a **terminal** state (≥2 configs evaluated)

**Steps:**
1. Open the terminal open-universe session at `http://localhost:3692`
2. Look at the strip's second row (below the counter row)
3. Note the violet badge text "Best: <id8>" (first 8 chars of the iteration id)
4. In a terminal, run `curl -s http://localhost:8000/api/sessions/<id> | grep -o '"bestIterationId":"[^"]*"'`

**Expected Result:**
- A violet badge with a trophy icon reading "Best: " + an 8-character id is visible
- Those 8 characters match the first 8 characters of `autoRun.bestIterationId` from the API response

---

### UT-06 — Open-universe config cards stream in live without reload (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iteration history tree → config cards)

**Preconditions:**
- An **active** open-universe run with `max_configs:2` (so at least 2 distinct cards will appear)

**Steps:**
1. Open the active open-universe session at `http://localhost:3692`
2. Watch the iteration history list below the status strip **without** manually refreshing
3. As cards appear, read the symbol/timeframe shown in each card's params

**Expected Result:**
- At least 2 iteration cards appear over time **without a manual page reload**
- Each card displays a **distinct** symbol/timeframe combination in its params (configs differ from one another)
- Cards carry no AI-suggestion section (insights are null this iteration) but do show strategy, params, metrics, equity curve, and walk-forward result

---

### UT-07 — Run state and counters survive a mid-run page reload (happy path / persistence)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iterations panel — full strip)

**Preconditions:**
- An **active** open-universe run (use a larger budget, e.g. `max_tokens:50000`, `max_wall_clock_seconds:120`, so it is still running during the reload)

**Steps:**
1. Open the active open-universe session at `http://localhost:3692`
2. Note the current status badge, configs chip value, and token chip value
3. Press F5 (or Cmd+R) to reload the page
4. Re-open the same session if needed and re-read the strip

**Expected Result:**
- After reload, the status strip reappears with the same run still tracked (status, configs, token, USD, wall-clock chips all present)
- The counter values are equal to or greater than the pre-reload readings (state restored from the server's durable store, not lost) — confirms values come from `GET /api/sessions/{id}`, not browser memory

---

### UT-08 — Pinned Auto Run still shows `rounds`, not `configs` (regression)

**Type:** regression
**Priority:** P1
**Surface:** `/` (Iterations panel — rounds chip)

**Preconditions:**
- No `max_configs` in the budget — start a **pinned** Auto Run via the in-UI "Auto Run" control (pick a symbol + timeframe in the UI)

**Steps:**
1. Navigate to `http://localhost:3692`
2. Start a pinned Auto Run using the in-UI control (select a symbol and timeframe, launch)
3. Open the resulting session and inspect the status-strip counter group

**Expected Result:**
- The leftmost chip reads `<iterationsDone>/<maxIterations> rounds` (e.g. `0/5 rounds`)
- There is **NO** `… configs` chip
- The token (`tok`), USD (`$`), and wall-clock (`s`) chips still render alongside the rounds chip — pinned display is otherwise unchanged from before this iteration

---

### UT-09 — Terminal budget-exhausted styling wraps the new counters (error / terminal state)

**Type:** error
**Priority:** P2
**Surface:** `/` (Iterations panel — terminal state)

**Preconditions:**
- A **tiny-budget** open-universe run that trips its cap quickly — launch with `"max_tokens":1`, `"max_configs":2`, `"max_usd":0.05`, `"max_wall_clock_seconds":120`

**Steps:**
1. Launch the tiny-budget open-universe run via the API (Setup Notes pattern, with `max_tokens:1`)
2. Open that session at `http://localhost:3692` and wait for it to go terminal (~a few poll cycles)
3. Inspect the strip's background, badge, and counter chips

**Expected Result:**
- The whole strip wraps **amber** (amber background + border)
- The status badge reads "Budget exhausted" with a warning (triangle) icon
- The second row shows the stop-reason label "Budget exhausted"
- The token / USD / configs chips are still present and readable (legible against the amber background)

---

### UT-10 — Counter values never exceed caps; missing cap omits the ` / cap` (validation)

**Type:** validation
**Priority:** P2
**Surface:** `/` (Iterations panel — counter chips)

**Preconditions:**
- One terminal open-universe run **with** a `max_usd` cap, and one automated run started **without** a `max_usd` (omit `max_usd` from the budget) for the contrast check

**Steps:**
1. Open the capped run; read the token and USD chips
2. Open the run started without `max_usd`; read the USD chip

**Expected Result:**
- For the capped run, both spend values are **≤** their caps (token left ≤ token right; `$` left ≤ `$` right)
- For the run without `max_usd`, the USD chip shows only the spent value (e.g. `$0.0042`) with **no** ` / $…` cap portion — the strip renders cleanly without a dangling separator

---

### UT-11 — Best badge / second row absent while run is active with no best yet (ux)

**Type:** ux
**Priority:** P3
**Surface:** `/` (Iterations panel — second row)

**Preconditions:**
- An open-universe run **early** in its life (active, before any best iteration is marked)

**Steps:**
1. Open a freshly-launched active open-universe session at `http://localhost:3692`
2. Before any config completes, inspect whether a second row / "Best:" badge is shown

**Expected Result:**
- While active and before `bestIterationId` is set, no "Best:" badge is shown (the second row is hidden until a best exists or the run goes terminal with a stop reason)
- The counter row alone is shown cleanly with no empty/blank second row

---

### UT-12 — Counter group labels are discoverable via tooltips (ux)

**Type:** ux
**Priority:** P3
**Surface:** `/` (Iterations panel — counter chips)

**Preconditions:**
- Any automated session open with the status strip visible

**Steps:**
1. Open an automated session at `http://localhost:3692`
2. Hover the mouse over each chip in the counter group in turn (configs/rounds, tok, $, s)

**Expected Result:**
- Hovering the configs chip shows tooltip "Configs explored / max (open-universe search)" (or "Improvement rounds done / max" for the rounds chip)
- Hovering the `tok` chip shows "AI tokens spent / cap"
- Hovering the `$` chip shows "AI cost (USD) spent / cap"
- Hovering the `s` chip shows "Elapsed / max wall-clock (seconds)"

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | Strip renders, no errors | smoke | P1 | `/` strip |
| UT-02 | Token chip live + increases | happy-path | P1 | token chip |
| UT-03 | USD chip 4-dp + rises | happy-path | P1 | USD chip |
| UT-04 | Configs chip replaces rounds (open-universe) | happy-path | P1 | configs chip |
| UT-05 | Best badge matches API | happy-path | P1 | Best badge |
| UT-06 | Config cards stream live | happy-path | P1 | history cards |
| UT-07 | State survives reload | happy-path | P1 | strip |
| UT-08 | Pinned run still shows rounds | regression | P1 | rounds chip |
| UT-09 | Budget-exhausted amber styling | error | P2 | terminal state |
| UT-10 | Caps respected / cap omitted when absent | validation | P2 | counter chips |
| UT-11 | No best badge before best exists | ux | P3 | second row |
| UT-12 | Tooltips name each counter | ux | P3 | counter chips |

**P1 tests (UT-01 through UT-08) must all pass for the browser QA verdict to be PASS.**
