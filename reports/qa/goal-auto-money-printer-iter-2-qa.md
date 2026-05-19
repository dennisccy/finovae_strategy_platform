# goal-auto-money-printer-iter-2 — QA Validation Report

**Verdict:** PASS

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Mode:** QA Validation (MODE 2) — full pipeline
**Frontend Present:** yes (Chrome MCP browser checks performed)
**Backend:** http://localhost:8691 (health at `/api/health` → 200) · **Frontend:** http://localhost:3691 → 200
**Target journeys:** J-10, J-11 · **Required-still-passing re-verified:** J-01, J-02, J-08

---

## Summary

The Layer-1 Foundation closure is correct and complete. The backend is now the
single source of truth for the automated search: a public stop endpoint +
by-`sessionId` in-process cancel registry + durable worker/restart-safe stop
signal, with `bestIterationId` preserved on stop by the robust objective. The
legacy in-browser `startAutoRun`/`stopAutoRun` iterate loop is deleted (verified
by source diff, not headline); both "Auto Run" entrypoints and the Stop control
now call the backend; `AutoRunBar`/`SessionContainer` ownership is
authoritatively re-derived per-session.

**21/21 functional test cases PASS.** Backend `test_auto_session` 26/26;
full suite 150 passed / 1 failed (the documented pre-existing out-of-scope
`test_directions_cache` failure — independently confirmed pre-existing). Frontend
`tsc && vite build` EXIT 0. All named browser journeys (J-10, J-11) and the
required-still-passing regressions (J-01, J-02, J-08) verified with live
API + browser evidence and screenshots. **UI Evolution: UI-PASS.**

One non-blocking **performance NOTE**: under deliberately extreme concurrent
load (6+ spawned auto-sessions + a browser with 61 live-polling
`SessionContainer`s) one stop call took 10.5 s; in a clean environment stop
returns in ~27 ms (TC-02/TC-05) and the unit suite asserts `< 1 s`. It still
returned without awaiting loop completion and the run reached terminal
`stopped` with best preserved and the UI converged. Flagged for the auditor as
a load-sensitivity note, not a correctness failure (event-loop non-blocking
TC-05 passed; anti-goal "must not block / must not wait for the loop" holds).

---

## Step 1 — Artifact Verification

| Artifact | Status |
|---|---|
| `docs/handoffs/goal-auto-money-printer-iter-2-dev.md` | ✅ present (+ `-frontend.md`); all template sections + retry Fix Notes (Blockers #1–#5) |
| `reports/reviews/goal-auto-money-printer-iter-2-review.md` | ✅ **PASS_WITH_NOTES** (2 NOTE-severity type-honesty items, no runtime bug) |
| `runs/goal-auto-money-printer-iter-2/status.json` | ✅ present (`fix_mode:true`, dev_complete, 5 fixed blockers recorded) |
| 6 UI visibility artifacts | ✅ all present, non-vague, concrete (see TC-15) |

---

## Step 2 — Backend Tests

Command: `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`
Log: `reports/qa/goal-auto-money-printer-iter-2-test.log`

```
26 passed, 4 warnings in 3.88s   (EXIT 0)
```

All 26 incl. the net-new stop coverage:
`test_durable_stop_signal_honored_no_post_stop_iterations`,
`test_restart_safe_stop_with_no_live_token_zero_iterations`,
`test_best_on_stop_uses_robust_objective_not_raw_return`,
`test_cancel_registry_removed_on_every_terminal_path`,
`test_cancel_registry_populated_in_create_auto_session`,
`test_stop_running_session_cancels_token_and_writes_durable_signal`,
`test_stop_is_worker_safe_when_no_live_token_registered`,
`test_stop_unknown_session_raises_clean_404`,
`test_stop_already_terminal_is_idempotent_no_state_regression`,
`test_stop_endpoint_http_unknown_404_and_idempotent_terminal`.

Full suite: `cd apps/backend && .venv/bin/python -m pytest -q`

```
1 failed, 150 passed, 4 warnings in 8.54s
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip
```

**Pre-existing & out-of-scope — independently confirmed:** `test_directions_cache`
is NOT in the iter-2 diff (`git diff HEAD --name-only` shows only
`auto_session.py`, `test_auto_session.py`, `SessionContainer.tsx`,
`useBacktest.ts`, `sessionApi.ts`), and the failure still reproduces on HEAD
with iter-2's backend changes stashed. **Zero new regressions.**

---

## Step 3 — Frontend Tests

No `test` script; the frontend gate is `npm run build` (`tsc && vite build`):

```
✓ 2231 modules transformed.  ✓ built in 4.16s   BUILD_EXIT=0
```

`tsc` clean ⇒ no dangling references to the deleted `startAutoRun`/`stopAutoRun`.
The chunk-size warning is pre-existing and cosmetic.

---

## Step 3.5 — Functional Test Plan Results

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---|---|---|---|---|---|---|
| TC-01 | Start backend auto-session via API | api | 200, sessionId, running/queued, listed | 200 `{sessionId,status:running}`; SID in `GET /api/sessions` with no browser | **PASS** | indistinguishable-from-UI precondition met |
| TC-02 | Stop running session → stopped | api | prompt 2xx <2s; →stopped+reason; no post-stop iters; best preserved | stop 200 in 0.027 s; →`stopped`, `stopReason=stopped`, `stopRequested=true`; 0 post-stop iters | **PASS** | `bestIterationId` null only because stop landed before the 1st LLM iteration completed (correctly preserved = null); non-null best-preserved proven live in TC-17/TC-18 |
| TC-03 | Stop unknown id → 404 | api | clean 404 JSON, no 5xx | 404 `{"detail":"Auto-session does-not-exist-12345 not found."}` | **PASS** | |
| TC-04 | Stop already-terminal idempotent | api | no error, no state regression | 200; `autoRun` byte-identical pre/post; no extra iter | **PASS** | |
| TC-05 | Stop does not block event loop | api | concurrent GET <2s; stop <2s | stop 0.027 s; 5× concurrent `GET /api/sessions` all 200 @ ~0.03 s | **PASS** | clean-env baseline (cf. TC-18 load note) |
| TC-06 | Open-universe POST → 4xx | api | 4xx, no session created | 422 "Missing required pinned config field(s): symbol, timeframe…"; sessions 54→54 | **PASS** | J-12 guard intact |
| TC-07 | `GET /api/sessions/{id}` lazy | api | metadata-only, no inline heavy payloads | 2 iters, keys metadata-only (no `equity_curve`/`trades`/`rating`/`result`); 5168 bytes | **PASS** | anti-goal guard |
| TC-08 | Suite green + extended | artifact | test_auto_session 0-exit; only pre-existing fail | 26/26; full 150 pass / 1 pre-existing | **PASS** | |
| TC-09 | Stop cooperative via durable signal | artifact | test asserts exact values | asserts `status==stopped`, `gen_calls==1` (no post-stop), `bestIterationId==only_id`, `autoRun.stopRequested is True` | **PASS** | exact assertions, not "ran ok" |
| TC-10 | Registry create + removed all paths | artifact | all 4 terminal paths asserted | asserts populate on create + absent for `t-budget`/`t-crit`/`t-stop`/`t-crash` (crash handler incl.) | **PASS** | |
| TC-11 | Worker/restart-safe, no live token | artifact | asserts stopped w/o live token, not skipped | `sid not in _CANCEL_REGISTRY` + `status==stopped` + `gen_calls==0` + `stopRequested is True`; real asserts | **PASS** | not pytest.skip/xfail |
| TC-12 | Best-on-stop robust not raw | artifact | asserts robust winner, not raw | asserts `bestIterationId==id_iter2` and `!=id_iter1` | **PASS** | live-corroborated (TC-17) |
| TC-13 | Legacy in-browser loop deleted | artifact | startAutoRun/stopAutoRun/refs gone | no defs of `startAutoRun`/`stopAutoRun`/`autoRunStopRef`/`autoRunIterationIdsRef`; explicit deletion comment `useBacktest.ts:459`; only backend wiring (`apiStartAutoSession`/`apiStopAutoSession`); `while` @1208/1996 are single-op SSE readers, not iterate loops; J-02 `loadingDetailIdRef` guard intact | **PASS** | source-diff verified per iter-1 lesson |
| TC-14 | Anti-goal source guards | artifact | contracts unchanged, no infra, no secrets | `contracts.py` 0-line diff; no celery/redis/sqlite/etc. added; 0 secret matches across 54 sessions in `.data/backtests`; `BACKTEST_STORE_DIR` defaults to non-`/tmp` `.data/backtests` | **PASS** | |
| TC-15 | Closure artifacts present | artifact | 7 files, non-vague, concrete | dev handoff (all sections) + 6 UI artifacts (67–468 lines, 0 placeholder); what-to-click has concrete click paths | **PASS** | ui-test-results headline cross-checked against own results (not taken at face value) |
| TC-16 | **J-10** server-driven, survives mid-run reload | browser | post-reload progress advances → terminal, best marked | UI per-iteration "Auto Run" → backend session `c7583b75` ("Auto:" prefix, `POST /api/auto-sessions`, `maxIterations=1`, running); **full browser reload mid-run** (fresh navigate, state wiped); run completed **server-side** during reload → `status=complete`/`stopReason=budget-exhausted`, `bestIterationId=39b0ddfa`; reloaded UI shows AutoRunBar "Automated run complete · budget reached · 1/1" + ★ Best, converged via poll (no manual reload) | **PASS** | evidence: `TC-16-after-reload.png` |
| TC-17 | **J-11** UI stop control | browser | →stopped, no post-stop iters, best marked, aria preserved | UI "Stop (3/6)" → `status=stopped`, `stopReason=stopped`, `stopRequested=true`; loop halted at 3/6 (not run to 6); `bestIterationId=fd97e197` preserved = **robust winner (6.45%, robust −999.99)**, NOT the higher-raw-return `88dfd9cd` (12.08%); AutoRunBar "Automated run stopped", `role=status aria-live=polite` preserved | **PASS** | live robust-not-raw confirmation; evidence: `TC-17-stopped.png` |
| TC-18 | **J-11** API stop reflected in UI | browser+api | UI →stopped no reload; best preserved | curl stop → UI AutoRunBar converged to "Automated run stopped" with **no page reload** (DOM read only); backend `status=stopped`, `stopRequested=true`, stopped at 5/8 (not run to budget=8), `bestIterationId=7f1a9316` preserved (27.27% robust winner) | **PASS** | see Performance Note; evidence: `TC-18-api-stop-in-ui.png` |
| TC-19 | **J-02** right panel rebind | browser | right panel (equity+trades+WF) rebinds to selected run | iter#1 detail = "Crossover Mean Reversion" +12.08% / alpha −35.47% / equity+WF; select iter#3 → right panel **rebound** to "Recovery Trend Filter" −3.33% / alpha −50.88% / equity+WF (values changed to match selected run, not just left summary) | **PASS** | iter-0 lesson regression guard green; evidence: `TC-19-right-panel-rebind.png` |
| TC-20 | **J-08** no stale terminal under rapid switch | browser | running session shows running; list+bar agree | with 61 `SessionContainer`s mounted, rapid switch SID20→SID3(terminal)→SID20→Recovery(terminal)→SID20; SID20 AutoRunBar = "Automated run · iteration 5/8" (advanced live 2→5), list row = "running"; **list spinner and AutoRunBar agree**; no stale `stopped`/`complete`; `aria-live=polite` preserved | **PASS** | iter-1 mandatory-lesson fix verified; evidence: `TC-20-no-stale-terminal.png` |
| TC-21 | **J-01** manual backtest e2e | browser | metrics+equity+trades render; new history entry; no errors | NL "Buy when RSI…" → generate → backtest → complete (session "BTC 4H RSI Reversion", +5.06%, 3 trades); right panel renders metrics/Strategy Script/Equity Curve/Walk-Forward/Strategy Rating; new history entry; **0 console errors/JS exceptions** across all 34 captures; bonus: clean inline symbol-format validation error observed (no hang/crash) | **PASS** | manual path not regressed by loop deletion; evidence: `TC-21-manual-backtest.png` |

**21/21 test cases passed.**

Coverage: J-10→TC-16 · J-11→TC-02/TC-17/TC-18/TC-09/TC-12 · J-02→TC-19 ·
J-08→TC-20 · J-01→TC-21 · J-07 baseline→TC-01 · legacy-loop deletion→TC-13 ·
registry→TC-10 · worker/restart-safe→TC-11 · errors→TC-03/TC-04/TC-06 ·
anti-goal guards→TC-05/TC-07/TC-14 · suite+closure→TC-08/TC-15.

---

## Step 4 — Chrome MCP Browser Checks

Performed against http://localhost:3691 (frontend 200). Evidence screenshots in
`reports/qa/goal-auto-money-printer-iter-2-evidence/`:
`TC-16-after-reload.png`, `TC-17-stopped.png`, `TC-18-api-stop-in-ui.png`,
`TC-19-right-panel-rebind.png`, `TC-20-no-stale-terminal.png`,
`TC-21-manual-backtest.png`.

- **J-10 (TC-16):** UI "Auto Run" demonstrably calls `POST /api/auto-sessions`
  (a new `Auto:` backend session appeared; no in-browser loop). A full
  mid-run browser reload did not stop the run — it completed **server-side**
  to a natural terminal and the reloaded UI converged via poll. PASS.
- **J-11 (TC-17 UI control + TC-18 API):** Stop from both the UI button and
  the API drives the run to terminal `stopped` with `stopRequested` persisted
  durably, no iterations appended past the in-flight one, budget not exhausted,
  and the robust-objective `bestIterationId` preserved (NOT re-derived by raw
  return — confirmed live: a 6.45 % robust winner kept over a 12.08 % raw
  candidate). PASS.
- **J-02 (TC-19):** selecting a different prior iteration re-binds the entire
  RIGHT analysis panel (title/return/alpha/equity curve/walk-forward), not just
  the left summary. iter-0 regression guard green. PASS.
- **J-08 (TC-20):** under rapid multi-session switching with 61
  `SessionContainer`s mounted, the freshly-opened still-running session shows
  authoritative "running" (live-advancing), session-list indicator and
  `AutoRunBar` agree — no stale terminal. iter-1 mandatory lesson verified. PASS.
- **J-01 (TC-21):** manual NL→backtest end-to-end unaffected by the loop
  deletion; full analysis renders; zero console errors. PASS.

Skeptical cross-check (iter-1 lesson honored): the `ui-test-results.md`
"PASS" headline was **not** taken at face value — backend 26/26 + full-suite,
the post-fix source diff (TC-13/TC-14), and all 21 functional cases were
independently executed here and corroborate it.

---

## Step 4b — UI Evolution Audit

**Verdict:** UI-PASS

1. **Did the UI evolve to reflect the new capability?** YES — "Auto Run" now
   launches a server-driven backend auto-session (verified UI→`POST
   /api/auto-sessions`); a working Stop control cancels the server run; the
   `AutoRunBar` renders running / stopped / complete states sourced from the
   durable backend poll.
2. **Can the user see/understand/control it?** YES — "Automated run · iteration
   N/M", "Automated run stopped", "complete · budget reached"; functional Stop;
   ★ Best preserved; survives reload; no stale terminal on rapid switching;
   `role=status aria-live=polite` retained.
3. **Still relying on old generic pages?** NO — the in-browser loop is deleted;
   the browser is a viewer/controller of the backend run.
4. **Technically complete but underexposed?** NO — fully exposed and operable
   from the existing UI surface (no new pages, per spec).

---

## Performance Note (non-blocking — for auditor)

`POST /api/auto-sessions/{id}/stop` latency:

| Condition | Stop latency |
|---|---|
| Clean env (TC-02) | 0.027 s |
| Concurrent (TC-05: 5 overlapping GETs) | 0.027 s, GETs ~0.03 s |
| Unit assertion (`test_stop_running_session…`) | asserts `< 1.0 s` (passes) |
| **Extreme load (TC-18: 6+ spawned auto-sessions + 61 live-polling SessionContainers)** | **10.5 s** |

The 10.5 s call still returned 200 (`status:"stopping"`) **without** awaiting
loop completion (an LLM iteration loop would take far longer), the run reached
terminal `stopped` cooperatively with best preserved, and the UI converged with
no reload. TC-05 shows the event loop stays non-blocking under normal
concurrency. This is a latency degradation under an unrealistically heavy QA
load profile, consistent with `status.json` Blocker #3 (stop latency) being
addressed but load-sensitive — recorded as a NOTE, not a blocker. No functional
test failed and no anti-goal is violated.

---

## Blockers

None. (1 pre-existing out-of-scope failure `test_directions_cache` —
independently confirmed pre-existing and not in the iter-2 diff. 1 performance
NOTE on stop latency under extreme load — non-blocking.)

---

## Step 5b — Server Cleanup

No servers were started by QA (backend/frontend are QA-runner managed). All
QA-spawned test auto-sessions were driven to terminal state (no runaway loops
left); post-run check shows zero still-running auto-sessions. Clean state left.

---

**Verdict:** PASS
