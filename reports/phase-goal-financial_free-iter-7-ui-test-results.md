# Phase goal-financial_free-iter-7 — UI Test Results

**Phase:** goal-financial_free-iter-7 — J-16: robust-objective overfit-gating leaderboard UI
**Date:** 2026-05-24
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** SKIPPED

<!-- PASS: All P1 tests pass -->
<!-- FAIL: Any P1 test fails -->
<!-- SKIPPED: Frontend not running or Chrome MCP unavailable -->

**Overall:** 0/10 tests passed (10 skipped)

**Reason:** Frontend not running. The browser-qa-phase.sh harness reported the frontend at http://localhost:3692 as not available for this run, so no browser tests were executed. Per the browser-qa-agent precondition check, all test cases are recorded as SKIPPED. No source files were changed and no test results were invented.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | Leaderboard card loads | smoke | P1 | "Candidate leaderboard · ranked by robust score" card visible with trophy icon and N≥2 count | Not executed — frontend not running | SKIP | none |
| UT-02 | Ranked by robust score desc | happy-path | P1 | Row #1 has highest robust score; each row ≤ the one above; "—" rows at bottom | Not executed — frontend not running | SKIP | none |
| UT-03 | Exactly one BEST row | happy-path | P1 | Exactly one violet "BEST" row carrying a blue "PROMOTE" badge | Not executed — frontend not running | SKIP | none |
| UT-04 | Rejected candidate gating reason | happy-path | P1 | Non-best rows show a plain-language gating reason (red if gated-out, gray if eligible); BEST row shows none | Not executed — frontend not running | SKIP | none |
| UT-05 | WFE chip color thresholds | validation | P2 | WFE chip emerald ≥0.50, amber ≥0.30, red <0.30; SCREEN rows gray "WFE —" | Not executed — frontend not running | SKIP | none |
| UT-06 | Stage badge + family dedup | validation | P2 | Every row has slate SCREEN or blue PROMOTE badge; no duplicate SYMBOL TIMEFRAME families | Not executed — frontend not running | SKIP | none |
| UT-07 | Manual session: no leaderboard | error | P1 | No leaderboard card at all for a manual session; rest of panel renders normally | Not executed — frontend not running | SKIP | none |
| UT-08 | Consistent position (empty state) | regression | P2 | Leaderboard sits under status strip, above iteration tree, in both populated and "Waiting…" states | Not executed — frontend not running | SKIP | none |
| UT-09 | Status strip + iteration tree intact | regression | P1 | Status strip + best badge unchanged; iteration tree still lists and responds to clicks | Not executed — frontend not running | SKIP | none |
| UT-10 | Readable on mobile | ux | P2 | Rows wrap cleanly at ~375px; no horizontal scrollbar or clipped text | Not executed — frontend not running | SKIP | none |

---

## Passed Tests

None — all tests skipped (frontend not running).

---

## Failed Tests

None — all tests skipped (frontend not running).

---

## Skipped Tests

### UT-01 — Iterations panel loads with leaderboard card
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-02 — Candidate rows ranked by robust score descending
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-03 — Exactly one candidate marked BEST
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-04 — Rejected candidate shows a gating reason
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-05 — WFE chip color matches threshold
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-06 — Stage badge and family dedup
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-07 — Manual session renders no leaderboard
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-08 — Leaderboard position consistent in empty/waiting state
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-09 — Existing iteration tree and best-badge still work
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

### UT-10 — Leaderboard readable on mobile
**Verdict:** SKIPPED
**Reason:** Frontend not running — http://localhost:3692 unavailable; no browser session could be started.

---

## Notes

- The 6 P1 tests (UT-01, UT-02, UT-03, UT-04, UT-07, UT-09) that gate the PASS verdict were all skipped, so a PASS verdict cannot be asserted from browser evidence.
- `promote_k` request-contract behavior (200 for 1–3, 422 for 0/4, default-1 on omit) and the leaderboard-only `_run_inner` exclusion are API concerns covered by the functional test plan (`reports/qa/goal-financial_free-iter-7-test-plan.md`), not by browser QA.
- No screenshots were captured because no browser session was started; the evidence directory was therefore not created.

---

## Environment

- **Frontend URL:** http://localhost:3692 (not running)
- **Backend URL:** http://localhost:8692 (health: http://localhost:8691/health per harness)
- **Browser:** Chrome via MCP — not invoked (frontend unavailable)
- **Test Date:** 2026-05-24
- **Evidence directory:** `reports/qa/goal-financial_free-iter-7-evidence/` (not created — no screenshots)
