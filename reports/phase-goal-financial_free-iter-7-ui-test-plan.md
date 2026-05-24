# Phase goal-financial_free-iter-7 — UI Test Plan

**Phase:** goal-financial_free-iter-7 — J-16: robust-objective overfit-gating leaderboard UI
**Date:** 2026-05-24
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3692 (offset stack: http://localhost:3691)

---

## Test Cases

<!-- UT-XX = UI tests, distinct from the functional test plan's TC-XX. -->
<!-- The seeded open-universe session referenced below: 2a829f6e-9762-467e-b32d-d2336724b2df -->

---

### UT-01 — Iterations panel loads with leaderboard card (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (right-hand Iterations panel)

**Preconditions:**
- Frontend running at http://localhost:3692, backend at http://localhost:8692
- An open-universe auto-session with ≥2 evaluated candidates exists (fixture `2a829f6e-9762-467e-b32d-d2336724b2df`)

**Steps:**
1. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Wait for the page to fully load
3. Look at the right-hand Iterations panel

**Expected Result:**
- Page renders with no blank screen or error overlay
- A card with header text "Candidate leaderboard" and "· ranked by robust score" is visible
- A trophy icon sits left of the header; an "N candidates" count (N ≥ 2) shows on the right
- No console errors

---

### UT-02 — Candidate rows are ranked by robust score descending (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iterations panel — `AutoSessionLeaderboard` rows)

**Preconditions:**
- UT-01 passed; the leaderboard shows ≥2 rows

**Steps:**
1. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Read the rank label (`#1`, `#2`, …) at the left of each row
3. Read the right-aligned robust score value on each row's top line, top to bottom

**Expected Result:**
- Row `#1` shows the highest robust score of all rows
- Each subsequent row's score is ≤ the row above it
- Any row whose score displays as "—" appears at the very bottom of the list

---

### UT-03 — Exactly one candidate is marked BEST (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iterations panel — BEST highlight)

**Preconditions:**
- UT-01 passed

**Steps:**
1. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Scan all leaderboard rows for the violet "BEST" badge

**Expected Result:**
- Exactly ONE row has a violet background and a violet "BEST" badge with an award icon
- That same row carries a blue "PROMOTE" stage badge (never "SCREEN")

---

### UT-04 — Rejected candidate shows a gating reason (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (Iterations panel — gating reason)

**Preconditions:**
- The session contains at least one non-best candidate (a row without the BEST badge)

**Steps:**
1. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Find a row that does NOT have the "BEST" badge
3. Read the small text line directly below that row's metrics line

**Expected Result:**
- A plain-language gating reason is shown, e.g. "WFE 0.21 < 0.30", "over-leveraged (margin called)", "0 trades", "screened — not walk-forward validated", or "lower robust score"
- Gated-out (ineligible) reasons render in red; eligible-but-not-best reasons render in muted gray
- The BEST row shows NO gating-reason line

---

### UT-05 — WFE chip color matches threshold (validation)

**Type:** validation
**Priority:** P2
**Surface:** `/` (Iterations panel — WFE chip)

**Preconditions:**
- The session has both PROMOTE rows (with WFE) and at least one SCREEN row

**Steps:**
1. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Read the "WFE x.xx" chip on each row

**Expected Result:**
- A chip with WFE ≥ 0.50 is green (emerald)
- A chip with WFE ≥ 0.30 and < 0.50 is amber
- A chip with WFE < 0.30 is red
- A SCREEN-stage row shows gray "WFE —" with no colored chip

---

### UT-06 — Stage badge and family dedup (validation)

**Type:** validation
**Priority:** P2
**Surface:** `/` (Iterations panel — stage badge)

**Preconditions:**
- UT-01 passed

**Steps:**
1. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Read each row's stage badge and its `SYMBOL TIMEFRAME` family label

**Expected Result:**
- Every row carries either a slate "SCREEN" badge or a blue "PROMOTE" badge
- No two rows share the same `SYMBOL TIMEFRAME` family label (deduped)

---

### UT-07 — Manual session renders no leaderboard (error / empty handling)

**Type:** error
**Priority:** P1
**Surface:** `/` (Iterations panel — empty handling)

**Preconditions:**
- A manual (non-auto) backtest session is available, or a terminal auto-run with zero completed candidates

**Steps:**
1. Navigate to `http://localhost:3692/` and open a manual (non-auto) session
2. Look at the Iterations panel

**Expected Result:**
- No "Candidate leaderboard" card appears at all (no empty card, no header, no error message)
- The rest of the Iterations panel renders normally

---

### UT-08 — Leaderboard position is consistent in empty/waiting state (regression)

**Type:** regression
**Priority:** P2
**Surface:** `/` (Iterations panel — `IterationPanel` wiring)

**Preconditions:**
- An open-universe auto-session that has a leaderboard but no iteration tree yet (or the seeded session)

**Steps:**
1. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Note the leaderboard's vertical position relative to the status strip and the iteration tree
3. Open a session showing "Waiting for the first iteration…" if available

**Expected Result:**
- The leaderboard renders immediately under the auto-session status strip and above the iteration tree in both the populated and the empty/"Waiting…" states

---

### UT-09 — Existing iteration tree and best-badge still work (regression)

**Type:** regression
**Priority:** P1
**Surface:** `/` (Iterations panel — pre-existing UI)

**Preconditions:**
- UT-01 passed

**Steps:**
1. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Confirm the auto-session status strip (with its existing best badge) still renders
3. Confirm the iteration tree below the leaderboard still lists iterations and is clickable
4. Click an iteration node in the tree

**Expected Result:**
- The status strip and its existing best badge render unchanged
- The iteration tree still lists nodes and responds to clicks (selects/shows the iteration as before)
- The new leaderboard does not displace or break either element

---

### UT-10 — Leaderboard is readable on mobile (ux)

**Type:** ux
**Priority:** P2
**Surface:** `/` (mobile "Iterations" tab — responsive)

**Preconditions:**
- UT-01 passed

**Steps:**
1. Resize the browser viewport to ~375 px wide (or use device emulation)
2. Navigate to `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
3. Tap/click the "Iterations" tab
4. Inspect the leaderboard rows

**Expected Result:**
- Rows wrap cleanly; rank, family, badges, score, WFE chip, trades, drawdown, and gating reason all remain readable
- No horizontal scrollbar and no clipped/overlapping text

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | Leaderboard card loads | smoke | P1 | `/` Iterations panel |
| UT-02 | Ranked by robust score desc | happy-path | P1 | `/` rows |
| UT-03 | Exactly one BEST row | happy-path | P1 | `/` BEST highlight |
| UT-04 | Rejected candidate gating reason | happy-path | P1 | `/` gating reason |
| UT-05 | WFE chip color thresholds | validation | P2 | `/` WFE chip |
| UT-06 | Stage badge + family dedup | validation | P2 | `/` stage badge |
| UT-07 | Manual session: no leaderboard | error | P1 | `/` empty handling |
| UT-08 | Consistent position (empty state) | regression | P2 | `/` IterationPanel wiring |
| UT-09 | Status strip + iteration tree intact | regression | P1 | `/` pre-existing UI |
| UT-10 | Readable on mobile | ux | P2 | mobile Iterations tab |

**P1 tests (UT-01, 02, 03, 04, 07, 09) must all pass for the browser QA verdict to be PASS.**

> **Note:** `promote_k` request-contract behavior (200 for 1–3, 422 for 0/4, default-1 on omit) is an API concern covered by the functional test plan (`reports/qa/goal-financial_free-iter-7-test-plan.md`) and the leaderboard-only `_run_inner` exclusion — not repeated here. There is no in-UI control for `promote_k` this iteration.
</parameter>
