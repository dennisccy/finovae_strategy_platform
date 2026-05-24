# Phase goal-financial_free-iter-8 — UI Test Plan

**Phase:** goal-financial_free-iter-8
**Date:** 2026-05-24
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3692

---

## Context for the tester

This is a verification/crash-fix iteration. It added **no new control, page, or
displayed value**. There are exactly three things to confirm:

1. **The crash is gone.** Legacy (pre-`budget`-schema) auto-sessions previously
   blanked the entire single-page app on load. They must now open normally.
2. **The status strip still works for current-schema sessions.** The
   `AutoSessionStatusStrip` (budget / spend / iteration progress bar at the top of
   the right "Iterations" panel) must still appear for sessions that carry a
   `budget` block — and must be absent (not crashing) for legacy sessions.
3. **The leaderboard renders to real pixels.** The right-panel "Iterations"
   leaderboard (ranked candidate rows, highlighted BEST row, color-graded WFE
   chips, gating reason) must paint correctly.

There are no forms, no inputs, and no submit buttons in scope — so there are no
classic validation tests. The "validation/error" coverage here is the crash-fix
boundary (legacy vs. current-schema data).

---

## Test Cases

<!-- Test IDs use UT-XX prefix to distinguish from functional test plan TC-XX IDs. -->

---

### UT-01 — App shell loads without a blank screen (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (app shell / `SessionContainer` via `useBacktest`)

**Preconditions:**
- Frontend is running at http://localhost:3692
- The session store contains at least one auto-session (current or legacy)

**Steps:**
1. Open the browser DevTools console (F12) and clear it.
2. Navigate to `http://localhost:3692/`
3. Wait for the page to fully load (≈3 seconds).

**Expected Result:**
- The page renders the main backtest workspace, NOT a blank white screen.
- The right-hand panel with the "Iterations" tab/section is visible.
- The console shows NO uncaught error containing
  `Cannot read properties of undefined (reading 'iterationsDone')`.
- The console shows NO React `pageerror` / error-boundary crash.

---

### UT-02 — Legacy auto-session opens without crashing the app (happy path — the core fix)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (any pre-`budget`-schema auto-session)

**Preconditions:**
- At least one legacy auto-session (one of the ~70 pre-`budget` records, i.e. NOT
  `j16-leaderboard-proof`) is present in the session list.

**Steps:**
1. Navigate to `http://localhost:3692/`
2. Open the session/run selector and select a **legacy** auto-session (a pre-`budget`
   record — any session other than `j16-leaderboard-proof`).
3. Wait for the session to load.
4. Observe the right "Iterations" panel.

**Expected Result:**
- The app does NOT blank out — the iteration tree, charts, and detail views render.
- The "Iterations" panel opens normally.
- The budget/spend/iteration **status strip is ABSENT** at the top of the panel
  (there is no budget data for a legacy session — its absence is correct, not a bug).
- No uncaught console error.

---

### UT-03 — Current-schema running session still shows its status strip (regression — must not break)

**Type:** regression
**Priority:** P1
**Surface:** `/` → right "Iterations" panel → `AutoSessionStatusStrip`

**Preconditions:**
- A current-schema auto-session carrying a `budget` block exists (e.g.
  `j16-leaderboard-proof` or any session created after the budget-schema landed).

**Steps:**
1. Navigate to `http://localhost:3692/`
2. Open the session/run selector and select a **current-schema** auto-session that
   has a `budget` block (e.g. `j16-leaderboard-proof`).
3. Look at the top of the right "Iterations" panel.

**Expected Result:**
- The `AutoSessionStatusStrip` IS visible at the top of the panel: it shows the
  budget / spend figures and an iteration-progress bar.
- For a still-running session, the iteration progress reflects iterations done vs.
  total (it updates as the session advances).
- Behavior is identical to iter-7 — no visual restyle, no missing fields.

---

### UT-04 — Leaderboard paints ranked candidate rows with a highlighted BEST row (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` → right "Iterations" panel → `AutoSessionLeaderboard`

**Preconditions:**
- An auto-session with **≥2 ranked candidates** is available (e.g.
  `j16-leaderboard-proof`).

**Steps:**
1. Navigate to `http://localhost:3692/`
2. Select the auto-session that has ranked candidates (e.g. `j16-leaderboard-proof`).
3. Scroll to the candidate leaderboard within the "Iterations" panel.

**Expected Result:**
- At least **2 ranked candidate rows** are visible.
- Exactly one row is highlighted as **BEST** — it shows a violet badge and a violet
  tint, and its candidate matches the session's `bestIterationId`.
- Each row shows its per-candidate return, trade count, and drawdown.
- No row overlaps, truncates illegibly, or renders blank.

---

### UT-05 — WFE chips are color-graded by score (ux / happy path)

**Type:** ux
**Priority:** P2
**Surface:** `/` → right "Iterations" panel → `AutoSessionLeaderboard` WFE chips

**Preconditions:**
- The same ranked-candidate session as UT-04 (e.g. `j16-leaderboard-proof`).

**Steps:**
1. Navigate to `http://localhost:3692/` and select the ranked-candidate session.
2. Inspect the WFE (Walk-Forward Efficiency) chip on each leaderboard row.

**Expected Result:**
- WFE chips are color-graded by value:
  - **Emerald/green** chip for WFE ≥ 0.5
  - **Amber/yellow** chip for WFE between 0.3 and 0.5
  - **Red** chip for WFE < 0.3
- A row still at the screen stage (no WFE computed) shows a literal `—` instead of a
  colored chip.

---

### UT-06 — A non-best candidate shows its gating reason (validation / boundary)

**Type:** validation
**Priority:** P2
**Surface:** `/` → right "Iterations" panel → `AutoSessionLeaderboard`

**Preconditions:**
- The ranked-candidate session contains at least one candidate that out-scores the
  BEST row but was rejected (e.g. a WFE-failing candidate) — present in
  `j16-leaderboard-proof`.

**Steps:**
1. Navigate to `http://localhost:3692/` and select the ranked-candidate session.
2. Find the candidate row that is NOT marked BEST yet has a strong raw score.

**Expected Result:**
- That row displays a visible **gating reason** text (e.g. a WFE-failing rejection
  message), explaining why it was not selected as best despite its score.
- The row is clearly NOT highlighted as BEST.

---

### UT-07 — Empty leaderboard renders cleanly (regression / edge)

**Type:** regression
**Priority:** P2
**Surface:** `/` → right "Iterations" panel → `AutoSessionLeaderboard` empty state

**Preconditions:**
- An auto-session with **no leaderboard candidates** is available.

**Steps:**
1. Navigate to `http://localhost:3692/`
2. Select an auto-session that has no ranked candidates.
3. Observe the leaderboard region of the "Iterations" panel.

**Expected Result:**
- The leaderboard area is cleanly empty — the component returns nothing.
- There is NO stray leaderboard header, NO empty table skeleton, and NO crash.
- The rest of the "Iterations" panel still renders normally.

---

### UT-08 — Switching between legacy and current-schema sessions never blanks the app (regression)

**Type:** regression
**Priority:** P1
**Surface:** `/` (session switching via `useBacktest`)

**Preconditions:**
- Both a legacy session and a current-schema session (e.g. `j16-leaderboard-proof`)
  are present.

**Steps:**
1. Navigate to `http://localhost:3692/`
2. Select a current-schema session (e.g. `j16-leaderboard-proof`) — confirm the
   status strip appears.
3. Switch to a legacy session — confirm the app does not blank and the strip
   disappears.
4. Switch back to the current-schema session.

**Expected Result:**
- The app remains rendered through all three switches — never blanks.
- The status strip appears for the current-schema session and is absent for the
  legacy session, toggling correctly each time.
- The console shows no uncaught error across the switches.

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | App shell loads (no blank) | smoke | P1 | `/` |
| UT-02 | Legacy session opens, no crash | happy-path | P1 | `/` |
| UT-03 | Current-schema strip still shows | regression | P1 | Iterations panel |
| UT-04 | Leaderboard ranked rows + BEST | happy-path | P1 | Iterations panel |
| UT-05 | WFE chips color-graded | ux | P2 | Iterations panel |
| UT-06 | Gating reason on non-best row | validation | P2 | Iterations panel |
| UT-07 | Empty leaderboard renders clean | regression | P2 | Iterations panel |
| UT-08 | Session switch never blanks | regression | P1 | `/` |

**P1 tests (UT-01, UT-02, UT-03, UT-04, UT-08) must all pass for browser QA verdict to be PASS.**
