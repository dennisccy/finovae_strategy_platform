# Phase goal-financial_free-iter-2 — UI Test Results

**Phase:** goal-financial_free-iter-2
**Date:** 2026-05-23
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** SKIPPED

<!-- SKIPPED: Frontend not running — all tests skipped -->

**Overall:** 0/15 tests passed (15 skipped)

**Precondition check:** Frontend reachability probe `curl http://localhost:3692` returned HTTP `000` (connection refused / not listening). Per the browser-qa-agent precondition policy, when the frontend is not running and cannot be auto-started, all test cases are recorded as SKIPPED with reason "frontend not running". No browser automation was attempted. (Backend probe `http://localhost:8692/health` returned `404`; backend reachability is moot since there is no frontend surface to drive — these UI tests cover the user-visible two-panel shell only.)

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | App shell loads with both panels | smoke | P1 | Two-panel shell renders, no console errors | Not executed — frontend not running | SKIP | none |
| UT-02 | Auto Run starts backend run + mints session tab | happy-path | P1 | New session tab + status strip "Running" | Not executed — frontend not running | SKIP | none |
| UT-03 | Budget counters advance live | happy-path | P1 | rounds + seconds counters increment across polls | Not executed — frontend not running | SKIP | none |
| UT-04 | Iteration cards stream in (no reload) | happy-path | P1 | New cards appear without reload | Not executed — frontend not running | SKIP | none |
| UT-05 | Run reaches terminal state | happy-path | P1 | Badge → terminal, spinner stops, stop-reason shown | Not executed — frontend not running | SKIP | none |
| UT-06 | Best-iteration badge appears | happy-path | P2 | Violet "Best: <id>" pill appears | Not executed — frontend not running | SKIP | none |
| UT-07 | "Waiting for first iteration" empty state | happy-path | P2 | Empty-state message before first card | Not executed — frontend not running | SKIP | none |
| UT-08 | Auto Run ↔ Stop control toggles | validation | P1 | Auto Run swaps to amber Stop while running, back when terminal | Not executed — frontend not running | SKIP | none |
| UT-09 | ⚡ on iteration card seeds new auto-session | happy-path | P1 | New seeded auto-session tab + live tracking | Not executed — frontend not running | SKIP | none |
| UT-10 | Spinner survives reload mid-run | regression | P1 | Spinner + Running re-appear after reload, no user action | Not executed — frontend not running | SKIP | none |
| UT-11 | Stop truly halts backend run | error | P1 | Badge → "Stopped", reason "Stopped by user", no new cards | Not executed — frontend not running | SKIP | none |
| UT-12 | Strip hidden for manual session | regression | P1 | No status strip for manual session | Not executed — frontend not running | SKIP | none |
| UT-13 | Manual single-run still works | regression | P1 | Single result renders, no status strip | Not executed — frontend not running | SKIP | none |
| UT-14 | Run history browse still works | regression | P2 | Prior iteration detail opens | Not executed — frontend not running | SKIP | none |
| UT-15 | Strip labels clear/discoverable | ux | P3 | Badge + counter tooltips make state obvious | Not executed — frontend not running | SKIP | none |

---

## Passed Tests

None — no tests were executed.

---

## Failed Tests

None — no tests were executed. (No test is marked FAIL: a missing frontend is a SKIP condition, not a failure, per browser-qa-agent rules.)

---

## Skipped Tests

All 15 test cases were skipped for the same reason: **frontend not running**. The frontend at `http://localhost:3692` was unreachable (HTTP `000`, connection refused) at QA time and there was no auto-start capability available to this agent.

### UT-01 — App shell loads with both panels
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-02 — Auto Run starts backend run + mints session tab
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-03 — Budget counters advance live during a run
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-04 — New iteration cards stream into the tree without reload
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-05 — Status strip reaches a terminal state when a tiny run finishes
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-06 — Best-iteration badge appears after a result is produced
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-07 — Empty state shows before the first iteration exists
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-08 — Auto Run control toggles to a Stop control while running
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-09 — ⚡ on a completed iteration card seeds a new auto-session
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-10 — Session picker shows a running spinner that survives reload
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-11 — Stop truly halts the backend run
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-12 — Status strip is hidden entirely for a manual session
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-13 — Manual single-run backtest still works
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-14 — Run history browse still opens prior iterations
**Verdict:** SKIPPED
**Reason:** frontend not running

### UT-15 — Strip semantics are clear and discoverable
**Verdict:** SKIPPED
**Reason:** frontend not running

---

## Notes for downstream agents

- **No P1 coverage was obtained from the browser layer.** The 11 P1 UI test cases (UT-01, 02, 03, 04, 05, 08, 09, 10, 11, 12, 13) were not exercised through the browser. This SKIPPED verdict means the user-visible behavior of the AutoSessionStatusStrip, the Auto Run/Stop control toggle, reload-mid-run resilience, and the manual-session regression checks were **not** validated end-to-end via the UI in this run.
- The UI test plan explicitly notes these browser tests do **not** duplicate the API/artifact functional tests in `reports/qa/goal-financial_free-iter-2-test-plan.md`. The backend endpoints behind these flows (`GET /api/sessions`, `GET /api/sessions/{id}`, `POST /api/auto-sessions`, `POST /api/auto-sessions/{id}/stop`) and the persisted `autoRun` block should be confirmed via that functional QA report, since the UI evidence is absent here.
- Re-run `./scripts/automation/browser-qa-phase.sh goal-financial_free-iter-2` once the frontend is serving at `http://localhost:3692` to obtain real user-visible evidence.

---

## Environment

- **Frontend URL:** http://localhost:3692 (probe returned HTTP `000` — not running)
- **Backend URL:** http://localhost:8692 (`/health` returned `404`)
- **Browser:** Chrome via MCP — not invoked (no frontend to drive)
- **Test Date:** 2026-05-23
- **Evidence directory:** `reports/qa/goal-financial_free-iter-2-evidence/` (empty — no screenshots; no tests executed)
