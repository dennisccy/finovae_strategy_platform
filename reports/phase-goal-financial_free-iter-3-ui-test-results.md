# Phase goal-financial_free-iter-3 — UI Test Results

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** SKIPPED

<!-- SKIPPED: Frontend not running -->

**Overall:** 0/12 tests passed (12 skipped)

---

## Precondition Check

Per the browser-qa-agent precondition step, service availability was verified before any test execution:

| Service | URL | Result |
|---------|-----|--------|
| Frontend | `http://localhost:3692` | `HTTP 000` — connection failed (not running) |
| Backend | `http://localhost:8691/health` | `HTTP 000` — connection failed (not running) |

The dispatch declared **Frontend available: no** and instructed that all tests be marked SKIPPED. The health checks above confirm both the frontend and backend are unreachable, so no browser automation was attempted. Because every test in this plan requires a live frontend (and most also require a backend-launched open-universe Auto Run as a precondition), none of the 12 cases could be exercised.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | Strip renders, no errors | smoke | P1 | Bordered status strip with status badge + counter chips, no console errors | Not executed — frontend not running | SKIP | none |
| UT-02 | Token chip live + increases | happy-path | P1 | `<spend> / <cap> tok` chip; spend ≥ prior reading, ≤ cap | Not executed — frontend not running | SKIP | none |
| UT-03 | USD chip 4-dp + rises | happy-path | P1 | `$0.0xxx / $0.0xxx` (4 dp); spend ≥ prior, ≤ cap, tracks tokens | Not executed — frontend not running | SKIP | none |
| UT-04 | Configs chip replaces rounds (open-universe) | happy-path | P1 | `<done>/<max> configs` chip, no `rounds` chip, increments | Not executed — frontend not running | SKIP | none |
| UT-05 | Best badge matches API | happy-path | P1 | Violet "Best: <id8>" badge matches `autoRun.bestIterationId` | Not executed — frontend not running | SKIP | none |
| UT-06 | Config cards stream live | happy-path | P1 | ≥2 distinct config cards stream in without reload | Not executed — frontend not running | SKIP | none |
| UT-07 | State survives reload | happy-path | P1 | Strip + counters restored after F5, values ≥ pre-reload | Not executed — frontend not running | SKIP | none |
| UT-08 | Pinned run still shows rounds | regression | P1 | `<done>/<max> rounds` chip, no `configs` chip, tok/$/s present | Not executed — frontend not running | SKIP | none |
| UT-09 | Budget-exhausted amber styling | error | P2 | Amber strip, "Budget exhausted" badge + stop reason, chips legible | Not executed — frontend not running | SKIP | none |
| UT-10 | Caps respected / cap omitted when absent | validation | P2 | Spend ≤ caps; no `/ $cap` portion when `max_usd` omitted | Not executed — frontend not running | SKIP | none |
| UT-11 | No best badge before best exists | ux | P3 | No "Best:" badge / second row while active before a best is set | Not executed — frontend not running | SKIP | none |
| UT-12 | Tooltips name each counter | ux | P3 | Hover tooltips name configs/rounds, tok, $, s chips | Not executed — frontend not running | SKIP | none |

---

## Passed Tests

None — all tests skipped.

---

## Failed Tests

None — all tests skipped. (No test was marked FAIL: skips are due to environment unavailability, not defects observed in the implementation.)

---

## Skipped Tests

All 12 test cases were skipped for the same reason: **frontend not running** (and backend not running). Service health checks returned `HTTP 000` for both `http://localhost:3692` and `http://localhost:8691/health`. Browser automation was therefore not attempted, per the dispatch directive and the browser-qa-agent precondition rule.

### UT-01 — Strip renders, no errors
**Verdict:** SKIPPED
**Reason:** frontend not running (`http://localhost:3692` → HTTP 000)

### UT-02 — Token chip live + increases
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires a backend-launched active open-universe Auto Run (backend `http://localhost:8691/health` → HTTP 000)

### UT-03 — USD chip 4-dp + rises
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires a backend-launched active open-universe Auto Run (backend unreachable)

### UT-04 — Configs chip replaces rounds (open-universe)
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires a backend-launched open-universe Auto Run (backend unreachable)

### UT-05 — Best badge matches API
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires a terminal open-universe run and an API cross-check (backend unreachable)

### UT-06 — Config cards stream live
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires a backend-launched active open-universe Auto Run (backend unreachable)

### UT-07 — State survives reload
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires a backend-launched active open-universe Auto Run (backend unreachable)

### UT-08 — Pinned run still shows rounds
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires starting a pinned Auto Run via the in-UI control (backend unreachable)

### UT-09 — Budget-exhausted amber styling
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires a backend-launched tiny-budget open-universe run (backend unreachable)

### UT-10 — Caps respected / cap omitted when absent
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires two backend-launched runs (with/without `max_usd`) (backend unreachable)

### UT-11 — No best badge before best exists
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires a freshly-launched active open-universe run (backend unreachable)

### UT-12 — Tooltips name each counter
**Verdict:** SKIPPED
**Reason:** frontend not running; also requires an automated session open with the status strip visible (backend unreachable)

---

## Notes

- This is an environment availability skip, **not** a quality signal. No defect in the iter-3 status-strip counters (token-spend, USD-cost, configs-explored chips) or open-universe config-card streaming was observed or implied by these results.
- The dispatch noted that `browser-qa-phase.sh` normally manages the backend (`:8691`) and frontend (`:3692`); at execution time neither was up, so the UI flows could not be driven.
- Per the user-recorded "browser QA headless render throttle" note, when the UI *is* reachable but pixels are blank in a hidden tab, the correct fallback is to cross-check the same values against the backend endpoints the UI calls (`GET /api/sessions/{id}` → `autoRun.budget`). That fallback was **not applicable here** because the backend itself was unreachable — there was nothing to cross-check against. Functional verification of the underlying counters/streaming is covered separately by the functional/QA test plan, not by this browser-QA pass.

---

## Environment

- **Frontend URL:** http://localhost:3692 — not running (HTTP 000)
- **Backend URL:** http://localhost:8691/health — not running (HTTP 000)
- **Browser:** Chrome via MCP — not invoked (no live frontend)
- **Test Date:** 2026-05-23
- **Evidence directory:** `reports/qa/goal-financial_free-iter-3-evidence/` (empty — no screenshots captured, all tests skipped)
