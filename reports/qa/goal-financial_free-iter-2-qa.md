**Verdict:** PASS

# QA Validation Report — goal-financial_free-iter-2

**Phase:** goal-financial_free-iter-2
**Date:** 2026-05-23
**Agent:** qa (MODE 2 — validation)
**Frontend Present:** yes
**Backend:** http://localhost:8692 (live, 200 on `/api/sessions`)
**Frontend:** http://localhost:3692 (was 200 at start; Vite dev server went down mid-run — runner-managed, see Browser Checks)

Layer-1 finish: the backend auto-session loop is now the **only** Auto Run engine. This QA exercised the
real backend with tiny live runs (`gpt-4o-mini`, 4-day range, ≤2 iterations) and static/build checks on
the rewired frontend. The two load-bearing gates (TC-04 B1+B2 concurrency, TC-11 single-source poll) pass.

---

## Step 1 — Artifact verification

| Artifact | Status |
|----------|--------|
| `docs/handoffs/goal-financial_free-iter-2-dev.md` | ✅ present (status: complete) |
| `reports/reviews/goal-financial_free-iter-2-review.md` | ✅ present — **PASS_WITH_NOTES** (all NOTE-severity, non-blocking) |
| `runs/goal-financial_free-iter-2/status.json` | ✅ present (`review_passed`) |
| `reports/qa/goal-financial_free-iter-2-test-plan.md` | ✅ present (15 cases) |

---

## Step 2 — Backend test suite (TC-03)

Command: `cd apps/backend && .venv/bin/python -m pytest`

```
1 failed, 165 passed, 1 deselected, 4 warnings in 6.19s
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip
```

The single red is the **documented carry-forward** on the untouched `test_directions_cache` module
(nice-to-have Capability #10) — failed identically in iter-1, explicitly **not a regression** per the spec
NOTES and plan §Assumptions. All 41 auto-session tests (40 iter-1 + the new B1+B2 regression) are green.

**TC-03: PASS.**

---

## Step 3 — Frontend verification (no JS unit runner; build + lint + grep, per plan)

- `npm run build` → exit **0** (tsc typecheck + Vite build; the 500 kB chunk-size note is a pre-existing advisory).
- `npm run lint` (`eslint --max-warnings 0`) → exit **0**.

**TC-02: PASS.**

---

## Step 3.5 — Functional test plan results

> Live runs used tiny budgets. The frontend Vite server was not reachable from Chrome MCP during the
> browser window (down mid-run; no `/tmp/qa-frontend-8692.log`), so the three browser journeys were verified
> via **the exact backend endpoints the UI calls** — the documented fallback for this iteration (spec
> TESTING REQUIREMENTS + plan "Chrome-MCP headless render-throttle"). The frontend rewire is build/lint/grep
> verified and its API client functions (`startAutoSession`/`stopAutoSession`/`apiLoadSession`) hit exactly
> the endpoints exercised below.

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---------|------|------|----------|--------|---------|-------|
| TC-01 | In-browser loop + dup scorer removed (J-10 static) | artifact | No `scoreIteration`, no dead refs, `startAutoRun` POSTs `/api/auto-sessions` | `grep scoreIteration` → NONE; `grep autoRunStopRef\|autoRunIterationIdsRef` → NONE; `startAutoRun` body (l.2136) calls `startAutoSession({...})` POST, no `while` iterate loop (the two remaining `while`s at 1132/1914 are the single-run retry path) | PASS | Shared helpers `generateAndExecute`/`editAndRerun`/`deleteIteration` intact (11 refs) |
| TC-02 | FE typechecks, builds, lints clean | artifact | both exit 0 | build exit 0, lint exit 0 | PASS | chunk-size warning pre-existing advisory |
| TC-03 | Backend suite green incl. iter-1 auto-session | api | exit 0 except documented carry-forward | 165 passed, 1 failed (`test_directions_cache` — documented), 1 deselected | PASS | 41 auto-session tests green |
| TC-04 | **B1+B2 concurrency: /stop racing _save_auto_run honored** | api | regression test passes; `to_thread` writes serialized vs `/stop` | `test_stop_racing_save_auto_run_is_not_dropped` **PASSED**; code: `_save_auto_run`/`_stop_requested` hold per-session `self._lock` with `to_thread` I/O **inside** the lock (auto_session.py:409–429); `/stop` uses the **same shared lock** from `AutoSessionHandle` (auto_session_routes.py:278–291) | PASS | **Critical gate satisfied** — `to_thread` is NOT applied without serialization; reviewer verified red without the shared lock |
| TC-05 | Event loop stays responsive while run active | api | responsiveness test passes | `test_post_returns_before_loop_completes_and_get_stays_responsive` **PASSED** | PASS | |
| TC-06 | J-07: POST /api/auto-sessions starts durable session + appears in list | api | 200 + sessionId; appears in `GET /api/sessions` | POST → **200**, `sessionId=449188b9…`, `status=running`; session present in `GET /api/sessions` under `tabs[]` | PASS | List shape is `{tabs:[{id,…}]}` |
| TC-07 | J-08: live tracking without manual reload | browser→api fallback | strip updates running→terminal; ≥1 result-bearing iteration; no reload | Polling `GET /api/sessions/{id}` every poll: `autoRun.status` advanced `running → budget-exhausted`; iteration nodes grew 1→11 with summary metrics (totalReturn/winRate/sharpe); `bestIterationId` set live | PASS (via backend fallback) | Browser pixels not captured (FE down); poll code = `apiLoadSession` @2500ms, stops at terminal (useBacktest.ts:766–780) |
| TC-08 | J-10: run survives reload (backend-driven) | browser→api/code fallback | progress continues after reload; reaches terminal | Run **completed entirely server-side with no browser attached** (TC-06 run reached `budget-exhausted` on its own) — the strongest proof the loop is backend-driven; running indicator is derived from polled `autoRun.status` (no local flag), so a reload simply resumes polling (code-verified, useBacktest.ts:535/766) | PASS (via backend/code fallback) | In-browser loop deleted (TC-01); live tab-reload pixels not captured (FE down) |
| TC-09 | J-11: Stop truly halts the server loop | browser→api fallback | `stopped`; no further iterations; best retained | Started 2-iter run; issued `POST /stop` mid-run → **200**; next poll `status=stopped`, `stopRequested=True`, `stopReason=stopped`, `best=c7c940a7`, nodes frozen at 1; after +10s still `stopped`, nodes=1, `endedAt` set | PASS | No further iterations appended; best-so-far retained |
| TC-10 | J-09: terminal stop-reason + WFE-gated best | api | terminal status, non-empty stopReason, bestIterationId present | `autoRun`: `status=budget-exhausted`, `stopReason=budget-exhausted`, `bestIterationId=863c1bac` (backend `RobustScorer` is sole "best") | PASS | |
| TC-11 | Single-source poll discipline / no eager parse | artifact | poll reuses lightweight GET; no new endpoint; no browser recompute; lazy detail | `sessionApi.ts`: only `startAutoSession`(POST `/api/auto-sessions`), `stopAutoSession`(POST `/stop`), `loadSession`(GET `/api/sessions/{id}`); no status endpoint; `RobustScorer`/recompute appear only in comments confirming backend is sole scorer; iteration nodes in GET `/api/sessions/{id}` carry summary fields only (no `result`/`trades`/`equity`/`rating` inline); `session_routes.py:152` documents no eager parse | PASS | **Coherence-critical gate satisfied** |
| TC-12 | Stop unknown/non-auto session → 404 | api | 404 | `POST /api/auto-sessions/does-not-exist-xyz/stop` → **404** | PASS | |
| TC-13 | Stop already-terminal → idempotent 200 | api | 200, no state change | `POST /stop` on terminal `449188b9…` → **200**; still `budget-exhausted`, `best=863c1bac` unchanged | PASS | |
| TC-14 | Auto Run open-universe (missing symbol/timeframe) → 400 | api | 400 | With all other required fields present but symbol/timeframe omitted → **400** ("Open-universe runs … not supported yet … J-12 / Layer-2") | PASS | Note: omitting `start_date`/`end_date`/`budget` too returns 422 (Pydantic field validation) before the 400 check; the Layer-2 boundary itself is a clean 400 |
| TC-15 | J-01/J-02/J-05 manual paths not regressed | browser→api/code fallback | manual single-run, history browse, reference-data controls work | `useBacktest.ts` builds/lints clean; manual helpers intact (TC-01); `GET /api/sessions`=200 (J-02 list), iteration lazy detail `GET …/iterations/{id}`=200 (J-02 open prior) | PASS (via backend/code fallback) | Live UI single-run (J-01) + reference-data controls (J-05) pixels not captured (FE down); helpers untouched + build clean |

**15/15 test cases passed** (TC-07/TC-08/TC-15 verified via the documented backend-endpoint fallback because
the frontend dev server was not reachable from Chrome MCP during the browser window).

---

## Step 4 — Chrome MCP browser checks

**SKIPPED — frontend not reachable from Chrome MCP.** The Vite dev server returned 200 at QA start but was
down (`curl 127.0.0.1:3692` → 000; only backend `:8692` listening) by the time browser automation ran, and
no `/tmp/qa-frontend-8692.log` exists. Navigation rendered Chrome's "site can't be reached" page.

Per qa.md ("Do NOT mark FAIL just because browser checks were skipped … Browser SKIPPED + tests passing =
overall PASS is acceptable") and the spec's explicit Chrome-MCP-throttle fallback, the three browser
journeys (J-08/J-10/J-11) were verified through the backend endpoints the UI calls and the persisted
`autoRun` block (TC-07/TC-08/TC-09 above), plus build/lint/grep on the rewired frontend. **A subsequent
browser-qa-agent run with a live frontend should still visually confirm the status strip and reload flow.**

---

## Step 4b — UI Evolution Audit

1. **Did the UI evolve to reflect the new capability?** Yes (code-verified). New `AutoSessionStatusStrip.tsx`
   renders run state / budget counters / stop reason / best badge; `IterationPanel.tsx` mounts it; live
   iteration cards merge from the poll.
2. **Can the user see/understand/control the capability?** Yes — Auto Run starts a durable backend session,
   Stop issues a server-side cancel, and running indicators (`isAutoRunning`, SessionPicker spinner, controls)
   are derived from polled `autoRun.status`, so a reloaded tab still shows an active run and resumes polling.
3. **Still relying on old generic pages?** No — the in-browser loop and duplicate `scoreIteration` are removed;
   the backend is the single source of truth.
4. **Technically complete but under-exposed?** No — the surface is present and wired under the IA homes the
   blueprint reserves; no nav change required.

**Verdict:** UI-PASS — UI meaningfully reflects the new capability (code/build/grep verified; live-pixel
confirmation deferred to browser-qa-agent since the FE server was down during this window).

---

## Critical Gates

- **B1+B2 (TC-04):** PASS — controller `autoRun` RMW and `/stop` share one per-session `asyncio.Lock`, with
  `to_thread` I/O held inside the lock. The FAIL condition (`to_thread` without serialization) is **not**
  triggered. Regression test green; reviewer confirmed it goes red without the shared lock.
- **Single-source poll (TC-11):** PASS — no parallel status endpoint, no browser-side score recompute,
  lightweight list/open path with lazy iteration detail preserved.

## Blockers

None.

## Notes (non-blocking, carried from review/handoff)

- Documented carry-forward red `test_directions_cache::test_write_and_read_full_round_trip` (untouched module).
- UI-started runs omit `targets` → terminate at `budget-exhausted`/`stopped`, never `criteria-met` (matches spec J-10 param list).
- Auto Run count input accepts up to 100 but is silently clamped to the backend max 50.
- Live browser-pixel verification of J-08/J-10/J-11 and J-01/J-05 should still be run by browser-qa-agent against a live frontend.

---

**Verdict:** PASS
