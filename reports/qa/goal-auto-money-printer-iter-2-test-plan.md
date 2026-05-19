# goal-auto-money-printer-iter-2 Functional Test Plan

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Frontend Present:** yes

## Phase Goal

Make the backend the single source of truth for the automated strategy search: the in-UI "Auto Run" button starts a server-driven auto-session (no in-browser loop), the run survives a mid-run browser reload, the user can stop it from the API and the UI, the legacy in-browser `startAutoRun` loop is deleted, and the best-so-far iteration stays marked — with no regression to J-01–J-09 (especially J-02 and J-08).

Conventions: backend `BASE=http://localhost:${CHAIN_BACKEND_PORT:-8000}`, frontend `http://localhost:${CHAIN_FRONTEND_PORT:-3000}`. Backend tests: `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`. All auto-session tests use tiny budgets (≤2 iterations, short date range, cheapest model, lenient targets).

## Test Cases

### TC-01 — Start a backend auto-session via API (J-07 baseline; "indistinguishable from UI" precondition)

**Type:** api
**Preconditions:** Backend running; `OPENAI_API_KEY` set.

**Steps:**
1. `curl -s -o /tmp/tc01.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"Buy when RSI crosses below 30, sell when it crosses above 70","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-02-01","initial_capital":10000,"model":"gpt-5.4-mini","budget":{"max_iterations":2}}'`
2. `curl -s "$BASE/api/sessions"` and look for the returned `sessionId`.

**Expected outcome:** HTTP 200, body has `sessionId` and `status` of `running` or `queued`; the `sessionId` immediately appears in `GET /api/sessions`.
**Pass criteria:** `http_code == 200`, `.sessionId` is a non-empty string, `.status ∈ {running, queued}`, and the same id is present in `GET /api/sessions` with no browser interaction.

---

### TC-02 — Stop a running auto-session via API → `stopped` (J-11 core API path)

**Type:** api
**Preconditions:** A session started with a budget large enough to still be running (e.g. `max_iterations: 8`, longer date range) from TC-01-style call; capture its `SID`.

**Steps:**
1. Confirm running: `curl -s "$BASE/api/sessions/$SID"` shows `autoRun.status == "running"`.
2. `curl -s -o /tmp/tc02.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions/$SID/stop"` and record the HTTP code + return latency.
3. Poll `curl -s "$BASE/api/sessions/$SID"` every 2s for up to 60s; record `autoRun.status`, `autoRun.stopReason`, and the iteration count before vs. after the stop.

**Expected outcome:** Stop returns promptly (2xx, sub-second, does not await loop completion); the run transitions to terminal `status == "stopped"` with a visible `stopReason`; no iterations are appended after the stop request; `bestIterationId` from before the stop is preserved.
**Pass criteria:** stop call `http_code ∈ {200,202,204}` and returns in < 2s; within 60s `autoRun.status == "stopped"` with non-empty `stopReason`; post-stop iteration count == count observed at stop time (no new iterations); `bestIterationId` non-null and unchanged from its pre-stop value (never re-derived by raw return).

---

### TC-03 — Stop an unknown session_id → clean 404

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `curl -s -o /tmp/tc03.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions/does-not-exist-12345/stop"`

**Expected outcome:** A clean 404 with a JSON error body; no traceback/500.
**Pass criteria:** `http_code == 404`; body is well-formed JSON with an error/detail message; no server 5xx.

---

### TC-04 — Stop an already-terminal session is idempotent

**Type:** api
**Preconditions:** A session that has already reached a terminal state (reuse TC-02's stopped session, or a `budget-exhausted` session from a `max_iterations:1` run).

**Steps:**
1. Record `autoRun` block (`status`, `stopReason`, iteration count, `bestIterationId`).
2. `curl -s -o /tmp/tc04.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions/$SID/stop"`.
3. Re-read `curl -s "$BASE/api/sessions/$SID"`.

**Expected outcome:** Idempotent no-op — no error, no extra iteration, no state regression (a `criteria-met`/`budget-exhausted` session is not flipped to `stopped`).
**Pass criteria:** `http_code` is a clean 2xx (or 409, not 5xx); post-call `status`, `stopReason`, iteration count, and `bestIterationId` are byte-identical to the pre-call values.

---

### TC-05 — Stop does not block the API event loop

**Type:** api
**Preconditions:** A still-running session `SID` (as in TC-02).

**Steps:**
1. Issue the stop: `curl -s -X POST "$BASE/api/auto-sessions/$SID/stop"` in the background.
2. Immediately (overlapping) issue 5× `curl -s -o /dev/null -w "%{http_code} %{time_total}\n" "$BASE/api/sessions"`.

**Expected outcome:** The concurrent `GET /api/sessions` calls stay responsive while the stop is processed and while the loop is winding down.
**Pass criteria:** All concurrent `GET` calls return `200` with `time_total < 2s` each; the stop call itself returns < 2s; no request hangs until loop completion.

---

### TC-06 — Open-universe POST still rejected with 4xx (J-12 out-of-scope guard, unchanged)

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `curl -s -o /tmp/tc06.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","budget":{"max_iterations":1}}'` (no `symbol`/`timeframe`).

**Expected outcome:** Rejected with a clear 4xx (open-universe is J-12 scope, not implemented here).
**Pass criteria:** `http_code` is 4xx (400/422); body explains the missing pinned dimension; no session is created (`GET /api/sessions` count unchanged).

---

### TC-07 — `GET /api/sessions/{id}` stays lazy (anti-goal regression guard)

**Type:** api
**Preconditions:** A session with ≥1 completed iteration exists (`SID`).

**Steps:**
1. `curl -s "$BASE/api/sessions/$SID"` and inspect the payload.

**Expected outcome:** The list/open path returns session/iteration metadata without inlining full per-iteration `result.json` / `rating.json` payloads (those load lazily via the per-iteration endpoint).
**Pass criteria:** Response does NOT contain full `equity_curve`/`trades`/full rating arrays inline for each iteration; iteration entries are metadata-only (id/status/summary). Detail is only present from the dedicated per-iteration endpoint.

---

### TC-08 — Backend `test_auto_session` suite green + extended for stop

**Type:** artifact
**Preconditions:** Dev complete; backend deps installed.

**Steps:**
1. Run `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v 2>&1 | tee reports/qa/goal-auto-money-printer-iter-2-test.log`.
2. Run the full backend suite `cd apps/backend && .venv/bin/python -m pytest -q` and record counts.

**Expected outcome:** `test_auto_session.py` passes including new stop-endpoint cases; the full suite has zero new regressions (only the pre-existing out-of-scope `test_directions_cache` failure, if present, may remain).
**Pass criteria:** `test_auto_session.py` exit code 0, all tests pass; full-suite failures, if any, are exactly the documented pre-existing `test_directions_cache` failure and nothing else (exact counts recorded verbatim).

---

### TC-09 — Stop is cooperative via the durable signal (no post-stop iterations, best preserved)

**Type:** artifact
**Preconditions:** New/extended pytest cases in `tests/test_auto_session.py`.

**Steps:**
1. Inspect the test that drives a multi-iteration run, requests stop mid-run, and asserts the loop honors a *persisted* stop flag (read each round via `read_session_meta`/`_update_autorun`), not only the in-process `CancellationToken`.

**Expected outcome:** A test asserts: final `status == "stopped"`, iterations appended after the stop request == 0, `bestIterationId` equals the robust-objective best of iterations completed before the stop.
**Pass criteria:** Such a test exists, asserts exact values (not "ran without error"), and passes; it asserts the durable per-round stop check (not skipped/mocked away).

---

### TC-10 — Cancellation registry populated on create, removed on every terminal path

**Type:** artifact
**Preconditions:** Extended pytest cases.

**Steps:**
1. Inspect tests covering the module-level `session_id → CancellationToken` registry.

**Expected outcome:** Tests assert the registry entry is added in `create_auto_session` and removed on each terminal path: `criteria-met`, `budget-exhausted`, `stopped`, and the runner crash/exception handler.

**Pass criteria:** A test asserts registry membership after create and asserts absence after EACH of the four terminal paths (including the crash handler) — all four explicitly covered and passing; no module-level leak across runs.

---

### TC-11 — Worker-safe / restart-safe stop with NO live in-process token

**Type:** artifact
**Preconditions:** Extended pytest cases.

**Steps:**
1. Inspect the test that simulates a stop request when the live in-process token is absent in the handling worker (registry empty / token cleared / simulated restart), relying solely on the durable persisted stop signal.

**Expected outcome:** The run still drives to terminal `status == "stopped"` purely via the durable signal the loop polls each round.
**Pass criteria:** The test is present and **asserts** the stopped outcome with no live token (it must NOT be `pytest.skip`-ed or xfail); it passes.

---

### TC-12 — Best-on-stop uses the robust objective, not raw return

**Type:** artifact
**Preconditions:** Extended pytest cases.

**Steps:**
1. Inspect the test where, before stop, one iteration has a higher raw return but fails WFE / is over-leveraged and another satisfies the robust objective.

**Expected outcome:** After stop, `bestIterationId` points to the robust-objective winner; the higher-raw-return WFE-failing/over-leveraged candidate is NOT marked best; selection reuses the existing `select_best` (not re-implemented).
**Pass criteria:** Test asserts the exact expected `bestIterationId` (the robust winner) and explicitly asserts the raw-return candidate is NOT best; passes.

---

### TC-13 — Legacy in-browser `startAutoRun` iterate loop is deleted (source diff)

**Type:** artifact
**Preconditions:** Dev complete.

**Steps:**
1. `grep -n "startAutoRun\|stopAutoRun\|autoRunStopRef\|autoRunIterationIdsRef\|isAutoRunning\|autoRunProgress" apps/frontend/src/hooks/useBacktest.ts apps/frontend/src/components/SessionContainer.tsx`.
2. `grep -rn "while" apps/frontend/src/hooks/useBacktest.ts` and inspect for any generate→backtest→insights iterate loop.
3. `git diff --stat` / `git diff` on `useBacktest.ts` to confirm the ~2183–2395 block and solely-owned refs are removed.

**Expected outcome:** The legacy in-browser `startAutoRun` (`useBacktest.ts:2183–2379`), `stopAutoRun` (2381–2395), and the auto-run-only state/refs they solely owned are gone; no in-browser `while` loop drives generate→backtest→insights; unrelated code (manual run, `runAll`, J-02 lazy-detail guard, live poll ~711–800, hydration ~535) is untouched.
**Pass criteria:** No remaining definition of an in-browser iterate loop; `startAutoRun`/`stopAutoRun` definitions absent; only routing-to-backend wiring remains; manual-run/J-02/live-poll code unchanged in the diff.

---

### TC-14 — Anti-goal source guards (contracts, secrets, no new infra)

**Type:** artifact
**Preconditions:** Dev complete; at least one auto-session run produced artifacts under the file store.

**Steps:**
1. `git diff --name-only` — confirm `apps/backend/shared/contracts.py` is not modified; `git diff shared/contracts.py` empty.
2. Search produced session artifacts/activity log for secret leakage: `grep -rni "sk-\|api[_-]\?key\|OPENAI_API_KEY\|ANTHROPIC_API_KEY\|Bearer " <session-store-dir>` over the run's `session.json`/activity/insights files.
3. Inspect the diff for any new datastore/queue/scheduler/broker import or schema fork of the session store.

**Expected outcome:** `contracts.py` unchanged; no API keys/secrets in any persisted artifact or activity log; no new external infra; no parallel store / schema fork (reuses existing `_update_autorun`/`session.json`).
**Pass criteria:** Zero diff in `contracts.py`; secret grep returns no matches in artifacts; no Celery/Redis/DB/broker/vector-store added; durable stop reuses the existing session-store mechanism only.

---

### TC-15 — Required closure artifacts present

**Type:** artifact
**Preconditions:** Pipeline run for this phase.

**Steps:**
1. Verify `docs/handoffs/goal-auto-money-printer-iter-2-dev.md` exists and follows the handoff template (What Was Built / Files Changed / Tests Run / Known Issues / Suggested Next).
2. Verify the 6 UI visibility artifacts exist for this phase: implementation-summary, user-visible-changes, ui-surface-map, ui-test-plan, ui-test-results, what-to-click.

**Expected outcome:** Dev handoff and all 6 UI artifacts exist and are non-vague (exact click paths in what-to-click / ui-test-plan).
**Pass criteria:** All 7 files present and populated; no placeholder/empty sections; manual steps are concrete and ordered.

---

### TC-16 — J-10: backend is single source of truth, survives mid-run reload (browser)

**Type:** browser
**Preconditions:** Backend + frontend running; ≥1 completed iteration available to "Auto Run" from.

**Steps:**
1. Open `http://localhost:${CHAIN_FRONTEND_PORT:-3000}`, open a session with a completed iteration.
2. Click "Auto Run" on that completed iteration with a tiny budget (≤2 iterations).
3. While the `AutoRunBar` shows "running" with iteration progress, reload the browser tab (full page reload).
4. Reopen the same session; observe progress for up to 90s. Screenshot to `reports/qa/goal-auto-money-printer-iter-2-evidence/TC-16-after-reload.png`.

**Expected outcome:** After the reload the run is still progressing (iteration count advances past the pre-reload value) and ultimately reaches a terminal state — proving the loop is server-driven, not browser-driven.
**Pass criteria:** Post-reload `AutoRunBar`/iteration count is ≥ the pre-reload count and visibly advances without any in-browser loop; the session reaches a terminal status (`criteria-met`/`budget-exhausted`) with a best iteration marked; no manual page reload was needed for updates.

---

### TC-17 — J-11: stop a running auto-session from the UI control (browser)

**Type:** browser
**Preconditions:** Backend + frontend running.

**Steps:**
1. From the UI, "Auto Run" with a budget large enough to stay running (e.g. ≥8 iterations / longer range).
2. While running, click the UI **Stop** control on the running automated session.
3. Observe the session for up to 60s. Screenshot to `reports/qa/goal-auto-money-printer-iter-2-evidence/TC-17-stopped.png`.

**Expected outcome:** The run transitions to `stopped` (red `StopCircle` + stop reason in `AutoRunBar`), no further iterations appear after the stop, and the best-so-far iteration keeps its "★ Best" pill.
**Pass criteria:** `AutoRunBar` shows the `stopped` terminal state with a visible stop reason; iteration count after stop == count at the moment of clicking Stop (no post-stop iterations); a best iteration remains marked; `role="status" aria-live="polite"` preserved.

---

### TC-18 — J-11: API stop is reflected live in the UI (browser + api)

**Type:** browser
**Preconditions:** Backend + frontend running.

**Steps:**
1. From the UI, "Auto Run" (still-running budget); note the `sessionId` (from session list / network).
2. From a terminal: `curl -s -X POST "$BASE/api/auto-sessions/$SID/stop"`.
3. Without manually reloading the page, watch the session in the UI for up to 60s. Screenshot to `reports/qa/goal-auto-money-printer-iter-2-evidence/TC-18-api-stop-in-ui.png`.

**Expected outcome:** The UI converges to the `stopped` state from the API-issued stop with no manual reload (live poll picks up the durable status); best stays marked.
**Pass criteria:** `AutoRunBar` shows `stopped` + stop reason within the poll interval without a page reload; iteration count frozen at stop; best preserved.

---

### TC-19 — J-02 regression: prior run reloads the RIGHT analysis panel (browser)

**Type:** browser
**Preconditions:** ≥2 completed runs/iterations in history.

**Steps:**
1. With one run open, select a *different* prior run from the history list.
2. Inspect the RIGHT analysis panel. Screenshot to `reports/qa/goal-auto-money-printer-iter-2-evidence/TC-19-right-panel-rebind.png`.

**Expected outcome:** Selecting the older run re-binds the RIGHT panel — trades table, equity curve, and walk-forward — to the selected run, not just the left summary.
**Pass criteria:** Right-panel equity curve + trades table + WF reflect the newly selected run's data (values change to match it); the left summary alone changing is NOT sufficient — explicit FAIL if the right panel keeps the previous run's data.

---

### TC-20 — J-08 regression: no stale `AutoRunBar` terminal under rapid session switching (browser)

**Type:** browser
**Preconditions:** Backend + frontend running; ability to start a fresh still-running auto-session.

**Steps:**
1. Start a fresh auto-session (still-running budget) so it is in "running" state.
2. With multiple session tabs/containers present, rapidly switch between several sessions and back to the freshly-started one (repeat several times quickly).
3. Observe the just-started session's status and the session-list spinner. Screenshot to `reports/qa/goal-auto-money-printer-iter-2-evidence/TC-20-no-stale-terminal.png`.

**Expected outcome:** The freshly-opened still-running session authoritatively shows "running" (status re-derived per-session on mount/switch), never a stale terminal status; the session-list spinner and the in-session `AutoRunBar` agree.
**Pass criteria:** After rapid switching, the running session's `AutoRunBar` shows "running" (not a stale `complete`/`stopped`); the list spinner for that session is active and consistent with the bar; no mismatch between list indicator and `AutoRunBar`.

---

### TC-21 — J-01 regression smoke: backtest from natural language end-to-end (browser)

**Type:** browser
**Preconditions:** Backend + frontend running; `OPENAI_API_KEY` set.

**Steps:**
1. Open the app; enter "Buy when RSI crosses below 30, sell when it crosses above 70"; set `BTCUSDT`, `1h`, a short date range, initial capital `10000`; submit.
2. Wait for results. Screenshot to `reports/qa/goal-auto-money-printer-iter-2-evidence/TC-21-manual-backtest.png`.

**Expected outcome:** Non-empty metrics, an equity curve, and a trades table render; a new `run_id` appears in history (manual path not regressed by the loop deletion).
**Pass criteria:** Results panel shows non-empty metrics + equity curve + trades table; a new history entry appears; no console errors tied to the removed `startAutoRun`.

---

## Summary

Total test cases: 21

- API tests: 7 (TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07)
- Browser tests: 6 (TC-16, TC-17, TC-18, TC-19, TC-20, TC-21)
- Artifact checks: 8 (TC-08, TC-09, TC-10, TC-11, TC-12, TC-13, TC-14, TC-15)

Coverage map: J-10 → TC-16; J-11 → TC-02, TC-17, TC-18, TC-09, TC-12; J-02 regression → TC-19; J-08 regression → TC-20; J-01 regression → TC-21; J-07 baseline → TC-01; legacy-loop deletion → TC-13; cancellation registry → TC-10; worker/restart-safe stop → TC-11; error cases → TC-03, TC-04, TC-06; anti-goal guards (lazy GET, contracts, secrets, no-new-infra, event-loop) → TC-07, TC-05, TC-14; suite green + closure artifacts → TC-08, TC-15.
