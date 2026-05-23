# Phase goal-financial_free-iter-4 — UI Test Results

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering for the open-universe search (J-14)
**Date:** 2026-05-23
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** SKIPPED

<!-- SKIPPED: Frontend not running. ALL tests skipped. -->

**Overall:** 0/13 tests passed (13 skipped)

**Reason:** Frontend not running. The browser-qa-phase.sh harness reported the frontend
(http://localhost:3692) as NOT available for this run, and the dispatch instructed: "Frontend
is NOT available. Mark all tests as SKIPPED with reason: frontend not running. Do NOT attempt
to run browser tests." No browser automation was attempted; no live UI could be observed.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-00 | Trigger open-universe run (setup) | smoke | P1 | Session view renders; Activity Log + iteration tree + status strip chips visible | Not executed — frontend not running | SKIP | none |
| UT-01 | Session view loads without errors | smoke | P1 | Activity Log (left) + iteration tree (right) visible; no error overlay; no console errors | Not executed — frontend not running | SKIP | none |
| UT-02 | SCREEN stage shown in Activity Log | happy-path | P1 | `SCREEN —` header names `gpt-5.4-mini`, "no walk-forward", candidate count; ≥3 per-candidate rows with score | Not executed — frontend not running | SKIP | none |
| UT-03 | PROMOTE stage top-k of N shown | happy-path | P1 | `PROMOTE —` header "top-1 of 3" names `claude-haiku-4-5` + "walk-forward"; exactly 1 per-candidate row; after SCREEN | Not executed — frontend not running | SKIP | none |
| UT-04 | SCREEN vs PROMOTE distinguishable | ux | P2 | SCREEN and PROMOTE groups both present and clearly separable by text prefix; not interleaved | Not executed — frontend not running | SKIP | none |
| UT-05 | Promoted node nests under screened parent | happy-path | P1 | Promoted card rendered nested as child of its screened parent, not as sibling/top-level | Not executed — frontend not running | SKIP | none |
| UT-06 | Promoted card: stronger model + WF | happy-path | P1 | Card `modelUsed` = `claude-haiku-4-5`; walk-forward (WFE) section present | Not executed — frontend not running | SKIP | none |
| UT-07 | Screened card: cheap model, no WF | validation | P2 | Card `modelUsed` = `gpt-5.4-mini`; no walk-forward section | Not executed — frontend not running | SKIP | none |
| UT-08 | Best badge on promoted WFE node only | validation | P1 | Best badge on a promoted WF-bearing node (`claude-haiku-4-5`); no screened-only node marked best | Not executed — frontend not running | SKIP | none |
| UT-09 | Chips update live without reload (J-08) | regression | P1 | At least one of token/USD/configs chips increases during wait without page reload | Not executed — frontend not running | SKIP | none |
| UT-10 | Run state survives reload (J-10) | regression | P1 | After F5, `autoRun` status, configs-done count, best badge, and SCREEN/PROMOTE log entries persist | Not executed — frontend not running | SKIP | none |
| UT-11 | Distinct configs as cards (J-12) | regression | P1 | ≥2 iteration cards with differing symbol/timeframe; run reached terminal state | Not executed — frontend not running | SKIP | none |
| UT-12 | No secrets in Activity Log | validation | P1 | No API key/token/`sk-`-style secret in any SCREEN/PROMOTE entry | Not executed — frontend not running | SKIP | none |

---

## Passed Tests

None — all tests skipped (frontend not running).

---

## Failed Tests

None — all tests skipped (frontend not running). No test was marked FAIL: per agent rules, a
test is only FAIL when it was executed and the expected result was not met. No test could be
executed here, so none can be FAIL.

---

## Skipped Tests

### UT-00 — Trigger an open-universe run (setup / smoke)
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-01 — Session view loads without errors
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-02 — Activity Log shows the SCREEN stage
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-03 — Activity Log shows the PROMOTE stage with top-k of N
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-04 — SCREEN and PROMOTE stages are visually distinguishable
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-05 — Promoted node nests as a child of its screened parent
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-06 — Promoted card shows stronger model + walk-forward section
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-07 — Screened-only card shows cheap model + no walk-forward section
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-08 — "Best" badge is on a promoted, walk-forward-bearing node only
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-09 — Status-strip token/USD/configs chips update live without reload (J-08)
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-10 — Run state survives a browser reload mid-run (J-10)
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-11 — Distinct configs still appear as iteration cards (J-12)
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-12 — No API key or secret appears in any Activity Log entry
**Verdict:** SKIPPED
**Reason:** frontend not running

---

## Notes

- **Frontend availability:** The dispatch reported `Frontend available: no` and explicitly
  instructed to mark all tests SKIPPED (reason: frontend not running) and to NOT attempt
  browser tests. No Chrome MCP automation was attempted.
- **No frontend code changed this iteration.** Per the UI surface map, zero frontend files
  changed; the 7 affected surfaces are existing components whose *content* changes because the
  backend now emits `SCREEN —` / `PROMOTE —` activity records and screen→promote node lineage.
  The user-visible SCREEN/PROMOTE behavior is therefore best validated by the functional/backend
  test plan and the QA agent's backend-endpoint checks (`GET /api/sessions/<id>` →
  `autoRun` status/bestIterationId/budget counters and the SCREEN/PROMOTE activity entries),
  which do not depend on a rendered frontend.
- **Throttle fallback note:** The plan's throttle fallback (verify via the backend endpoint the
  UI polls if pixels render blank despite a healthy frontend) presupposes a *running* frontend
  with a hidden-tab render throttle. That condition does not apply here — the frontend was not
  available at all — so the fallback path was not exercised by this browser-QA pass. Backend-level
  verification of the same SCREEN/PROMOTE outcomes is owned by the QA agent's functional run.

---

## Environment

- **Frontend URL:** http://localhost:3692 (NOT available this run)
- **Backend health endpoint:** http://localhost:8691/health (managed by browser-qa-phase.sh)
- **Browser:** Chrome via MCP — not invoked (frontend not running)
- **Test Date:** 2026-05-23
- **Evidence directory:** `reports/qa/goal-financial_free-iter-4-evidence/` (no screenshots — no live UI to capture)
