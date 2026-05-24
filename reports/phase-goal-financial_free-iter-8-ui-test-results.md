# Phase goal-financial_free-iter-8 — UI Test Results

**Phase:** goal-financial_free-iter-8
**Date:** 2026-05-24
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** SKIPPED

<!-- SKIPPED: Frontend not running — all tests skipped. -->

**Overall:** 0/8 tests passed (8 skipped)

---

## Precondition Check

Per the browser-qa-agent precondition step, service availability was checked before any test execution:

| Service | URL | Result |
|---------|-----|--------|
| Frontend | `http://localhost:3692/` | HTTP `000` — connection refused (not running) |
| Backend  | `http://localhost:8691/health` | HTTP `000` — connection refused (not running) |

The frontend is not reachable, so no browser tests could be executed. No Chrome MCP
navigation was attempted. No screenshots were captured (no live UI to capture).

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | App shell loads (no blank) | smoke | P1 | App shell renders, no `iterationsDone` undefined error in console | Not executed — frontend not running | SKIP | none |
| UT-02 | Legacy session opens, no crash | happy-path | P1 | Legacy (pre-`budget`) session opens; app does not blank; status strip absent | Not executed — frontend not running | SKIP | none |
| UT-03 | Current-schema strip still shows | regression | P1 | `AutoSessionStatusStrip` visible with budget/spend + progress bar | Not executed — frontend not running | SKIP | none |
| UT-04 | Leaderboard ranked rows + BEST | happy-path | P1 | ≥2 ranked rows, exactly one BEST (violet badge/tint), per-row return/trades/drawdown | Not executed — frontend not running | SKIP | none |
| UT-05 | WFE chips color-graded | ux | P2 | WFE chips emerald ≥0.5 / amber 0.3–0.5 / red <0.3; `—` when no WFE | Not executed — frontend not running | SKIP | none |
| UT-06 | Gating reason on non-best row | validation | P2 | Non-best row shows visible gating reason; not highlighted as BEST | Not executed — frontend not running | SKIP | none |
| UT-07 | Empty leaderboard renders clean | regression | P2 | Empty leaderboard renders nothing — no header, no skeleton, no crash | Not executed — frontend not running | SKIP | none |
| UT-08 | Session switch never blanks | regression | P1 | App stays rendered across legacy↔current switches; strip toggles; no console error | Not executed — frontend not running | SKIP | none |

---

## Passed Tests

None — all tests skipped.

---

## Failed Tests

None — all tests skipped.

---

## Skipped Tests

### UT-01 — App shell loads without a blank screen
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692/` returned HTTP `000`, connection refused)

### UT-02 — Legacy auto-session opens without crashing the app
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692/` returned HTTP `000`, connection refused)

### UT-03 — Current-schema running session still shows its status strip
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692/` returned HTTP `000`, connection refused)

### UT-04 — Leaderboard paints ranked candidate rows with a highlighted BEST row
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692/` returned HTTP `000`, connection refused)

### UT-05 — WFE chips are color-graded by score
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692/` returned HTTP `000`, connection refused)

### UT-06 — A non-best candidate shows its gating reason
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692/` returned HTTP `000`, connection refused)

### UT-07 — Empty leaderboard renders cleanly
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692/` returned HTTP `000`, connection refused)

### UT-08 — Switching between legacy and current-schema sessions never blanks the app
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692/` returned HTTP `000`, connection refused)

---

## Notes

- This is a verification / crash-fix iteration (no new control, page, or displayed
  value). The browser test plan exercises the legacy-vs-current-schema crash boundary
  and the existing leaderboard / status-strip rendering. None of it could be exercised
  because the frontend is not running.
- Per browser-qa-agent rules, an unavailable frontend is recorded as SKIPPED (not FAIL).
  The crash-fix and rendering behavior remain unverified at the browser level for this
  iteration and should be re-run once the frontend is available.

---

## Environment

- **Frontend URL:** http://localhost:3692 (not running — HTTP `000`)
- **Backend URL:** http://localhost:8691/health (not running — HTTP `000`)
- **Browser:** Chrome via MCP — not invoked (frontend unavailable)
- **Test Date:** 2026-05-24
- **Evidence directory:** `reports/qa/goal-financial_free-iter-8-evidence/` (no screenshots captured)
