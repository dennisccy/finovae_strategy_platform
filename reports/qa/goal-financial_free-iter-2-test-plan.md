# goal-financial_free-iter-2 Functional Test Plan

**Phase:** goal-financial_free-iter-2
**Date:** 2026-05-23
**Frontend Present:** yes

## Phase Goal

Make the backend auto-session loop the **only** Auto Run engine: clicking "Auto Run" starts the server-side loop, the open session tracks `running → terminal` live with no manual reload, the run survives a browser reload, and the UI Stop control truly stops it server-side — while deleting the duplicate in-browser iterate loop and `scoreIteration`.

> Use **tiny budgets** for all live runs (≤ 2 iterations, short date range, cheapest model, lenient targets). Honor the documented Chrome-MCP headless render-throttle: if pixels are blank, verify the journey via the backend endpoints the UI calls and the persisted `autoRun` block.

## Test Cases

### TC-01 — In-browser iterate loop and duplicate scorer removed (J-10 static proof)

**Type:** artifact
**Preconditions:** Frontend rewire complete; `apps/frontend/src/hooks/useBacktest.ts` present.

**Steps:**
1. `grep -n "scoreIteration" apps/frontend/src/hooks/useBacktest.ts`
2. `grep -n "autoRunStopRef\|autoRunIterationIdsRef" apps/frontend/src/hooks/useBacktest.ts`
3. Inspect the `startAutoRun` body (around former line 2047) — confirm no `while` iterate loop remains and it issues a POST to `/api/auto-sessions`.

**Expected outcome:** The duplicate in-browser `scoreIteration` and the iterate `while` loop (former lines 2067–2234) are gone; dead loop-only refs removed. Shared helpers (`generateAndExecute`, `editAndRerun`, `deleteIteration`, manual single-run) remain.
**Pass criteria:** Step 1 and Step 2 return no matches (or only an unrelated comment); `startAutoRun` contains a POST to `/api/auto-sessions` and no client-side iteration loop.

---

### TC-02 — Frontend typechecks, builds, and lints clean

**Type:** artifact
**Preconditions:** Node deps installed in `apps/frontend`.

**Steps:**
1. `cd apps/frontend && npm run build`
2. `cd apps/frontend && npm run lint`

**Expected outcome:** `tsc` typecheck + Vite build succeed; lint passes with max-warnings 0.
**Pass criteria:** Both commands exit 0; no TypeScript errors, no lint warnings.

---

### TC-03 — Backend suite green incl. iter-1 auto-session tests

**Type:** api
**Preconditions:** Backend venv present.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest`

**Expected outcome:** All non-integration tests pass, including the 40 iter-1 auto-session tests.
**Pass criteria:** Exit 0. The only acceptable red is the documented carry-forward `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (untouched module — not a regression). Any other failure = blocker.

---

### TC-04 — B1+B2 concurrency regression: a /stop racing _save_auto_run is honored

**Type:** api
**Preconditions:** New regression test added in `tests/test_auto_session.py` / `test_auto_session_routes.py`.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest -k "stop and (race or concurren or save_auto_run)" -v`
2. Confirm the test simulates a `/stop` issued concurrently with a controller `_save_auto_run` under the off-loop persistence model.

**Expected outcome:** After the race, `session.json` persists the stop signal (`stopRequested=True` or the chosen top-level stop-flag key) and the loop reaches `stopped` — the stop request is NOT dropped (no TOCTOU).
**Pass criteria:** The regression test exists and passes. **Critical gate:** if `to_thread` wraps the controller's `autoRun` writes without serialization against `/stop`, this is a FAIL regardless.

---

### TC-05 — Event loop stays responsive while a run is active

**Type:** api
**Preconditions:** Backend test suite.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest -k "responsive or returns_before_loop" -v`

**Expected outcome:** `POST /api/auto-sessions` returns before the loop completes and a concurrent `GET` stays responsive (one-backtest-per-worker semaphore respected).
**Pass criteria:** The iter-1 `test_post_returns_before_loop_completes_and_get_stays_responsive`-style check passes.

---

### TC-06 — J-07 still green: POST /api/auto-sessions starts a durable session and appears in list

**Type:** api
**Preconditions:** Backend running on its port; reference data available.

**Steps:**
1. `curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/auto-sessions -H 'Content-Type: application/json' -d '{"natural_language":"simple SMA crossover","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-01-07","initial_capital":10000,"leverage":1,"allow_short":false,"model":"<cheapest>","budget":{"max_iterations":2,"max_wall_clock_sec":60}}'`
2. Capture the returned `sessionId`.
3. `curl -s http://localhost:8000/api/sessions` and look for that id.

**Expected outcome:** 200 with a `sessionId`; the new session shows up in `GET /api/sessions`.
**Pass criteria:** Step 1 status 200 and body has a session id; Step 3 list contains that id. (Adjust port if backend differs.)

---

### TC-07 — J-08 live tracking without manual reload (browser)

**Type:** browser
**Preconditions:** Frontend on :3000, backend reachable.

**Steps:**
1. Chrome MCP: navigate to `http://localhost:3000`.
2. Configure a tiny baseline (short date range, cheapest model) and click **Auto Run** with a small budget (≤ 2 iterations).
3. Without reloading, observe the Automated-session status strip in the Right/Iterations panel: status `queued`/`running`, budget counters incrementing.
4. Wait for at least one iteration card to appear with a backtest result + suggestions.
5. Continue observing until status reaches a terminal state (`criteria-met`/`budget-exhausted`/`stopped`).
6. Screenshots to `reports/qa/goal-financial_free-iter-2-evidence/`.

**Expected outcome:** Status strip updates `running → terminal` and ≥1 iteration card appears, all without a manual reload (driven by the ~2–3 s poll of `GET /api/sessions/{id}`).
**Pass criteria:** Strip shows live state transitions and at least one result-bearing iteration with no manual reload. If pixels blank (throttle), verify via `GET /api/sessions/{id}` showing `autoRun.status` advancing to terminal and iterations growing.

---

### TC-08 — J-10 run survives a browser reload (backend-driven proof)

**Type:** browser
**Preconditions:** Frontend + backend running.

**Steps:**
1. Click **Auto Run** on a completed iteration with a small budget large enough to still be mid-run.
2. Mid-run, reload the browser tab (or close/reopen).
3. Reopen the session from the Session picker.
4. Observe whether progress keeps advancing and reaches a terminal state.

**Expected outcome:** Progress continues after reload (no local flag needed — running state derived from polled `autoRun.status`) and the run reaches a terminal state. Proves the loop is backend-driven.
**Pass criteria:** After reload the session still shows running and polling resumes, then reaches terminal. If blank: confirm via `GET /api/sessions/{id}` that `autoRun.status` continued advancing through and past the reload moment.

---

### TC-09 — J-11 Stop truly halts the server loop (browser)

**Type:** browser
**Preconditions:** Frontend + backend running.

**Steps:**
1. Start a run large enough to still be running (e.g. 2 iterations).
2. Issue Stop via the UI Stop control (or `POST http://localhost:8000/api/auto-sessions/{id}/stop`).
3. Observe the next poll: status becomes `stopped`.
4. Confirm no further iterations are appended and the best-so-far is retained.

**Expected outcome:** Session transitions to `stopped`, appends no further iterations, retains best-so-far.
**Pass criteria:** `autoRun.status == "stopped"`, iteration count frozen at issue time, `bestIterationId` retained. Verify via `GET /api/sessions/{id}` if UI blank.

---

### TC-10 — J-09 still green: terminal stop-reason + WFE-gated best

**Type:** api
**Preconditions:** A completed tiny auto-session from TC-06/TC-07.

**Steps:**
1. `curl -s http://localhost:8000/api/sessions/<id>` and inspect the `autoRun` block.

**Expected outcome:** `autoRun` has a terminal `status`, a populated `stopReason`, and a `bestIterationId` set per the WFE-gated `RobustScorer` (sole "best" definition; no browser-side recompute).
**Pass criteria:** `autoRun.status` is terminal, `stopReason` non-empty, `bestIterationId` present and consistent with the backend scorer.

---

### TC-11 — Single-source poll discipline / no eager heavy-payload parse

**Type:** artifact
**Preconditions:** Frontend rewire complete.

**Steps:**
1. Inspect `apps/frontend/src/lib/sessionApi.ts` — the poll reuses the lightweight `apiLoadSession` (`GET /api/sessions/{id}`); confirm `startAutoSession`/`stopAutoSession` client fns hit the existing endpoints only.
2. Grep frontend for any new status endpoint or browser-side "best"/score recomputation.
3. Confirm `GET /api/sessions/{id}` does not eagerly parse full per-iteration `result.json`/`rating.json` (detail lazy-loaded via `fetchIterationDetail`).

**Expected outcome:** Polling reads only the existing canonical `GET /api/sessions/{id}`; no parallel status endpoint; no in-browser score recompute; iteration detail stays lazy.
**Pass criteria:** No new value-serving endpoint; no `scoreIteration`/score recompute in browser; list/open path is lightweight (lazy detail preserved). Coherence-critical.

---

### TC-12 — Error case: stop unknown/non-auto session → 404

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auto-sessions/does-not-exist/stop`

**Expected outcome:** 404.
**Pass criteria:** HTTP status 404.

---

### TC-13 — Error case: stop already-terminal session → idempotent 200

**Type:** api
**Preconditions:** A terminal auto-session id (from TC-09/TC-10).

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auto-sessions/<terminal-id>/stop`

**Expected outcome:** 200 (idempotent); no state change.
**Pass criteria:** HTTP status 200; session remains terminal with same best-so-far.

---

### TC-14 — Error case: Auto Run open-universe (missing symbol/timeframe) → 400

**Type:** api
**Preconditions:** Backend running (Layer-2 boundary preserved).

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auto-sessions -H 'Content-Type: application/json' -d '{"natural_language":"find anything good","initial_capital":10000}'`

**Expected outcome:** 400 — open-universe search rejected (out of scope for Layer-1).
**Pass criteria:** HTTP status 400.

---

### TC-15 — J-01/J-02/J-05 manual paths not regressed (browser)

**Type:** browser
**Preconditions:** Frontend + backend running.

**Steps:**
1. J-01: run a manual NL backtest (single run) and confirm a result renders.
2. J-02: browse run history and confirm prior iterations open.
3. J-05: exercise the reference-data controls and confirm they respond.

**Expected outcome:** All three manual journeys still work after the heavy `useBacktest.ts` edits.
**Pass criteria:** Manual single-run produces a result; run-history browse loads iterations; reference-data controls function. If blank: verify via the backend endpoints these flows call.

---

## Summary

Total test cases: 15
- API tests: 7 (TC-03, TC-04, TC-05, TC-06, TC-10, TC-12, TC-13, TC-14 — note TC-04/TC-05 are pytest-driven)
- Browser tests: 4 (TC-07, TC-08, TC-09, TC-15)
- Artifact checks: 4 (TC-01, TC-02, TC-11) plus build/lint static checks

Counts by primary type: **api = 7, browser = 4, artifact = 4** (15 total).

**Load-bearing this iteration:** TC-04 (B1+B2 concurrency — critical gate), TC-07/TC-08/TC-09 (J-08/J-10/J-11), TC-11 (single-source poll / coherence). A failing TC-04 or a `to_thread`-without-serialization implementation is an automatic FAIL.
</content>
</invoke>
