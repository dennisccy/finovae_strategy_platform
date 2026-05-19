# goal-auto-money-printer-iter-1 Dev Handoff

**Phase:** goal-auto-money-printer-iter-1
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built

Layer-1 Foundation of Key Capability #11 — the headless auto-session — plus
the lesson-mandated J-02 right-panel re-bind fix.

- **`POST /api/auto-sessions`** (new router, mounted in `api.py`): one call
  starts a fully server-side generate→backtest→walk-forward→insights→iterate
  loop with a pinned config and a hard budget. Returns
  `200 {"sessionId": "...", "status": "running"}`.
- **`backend/auto_session.py`** — the controller: Pydantic request/response
  DTOs (NOT added to frozen `shared/contracts.py`), the bounded background
  loop (`asyncio.create_task`, same pattern as the manual SSE endpoints),
  the durable `autoRun` state machine, activity emission, and per-iteration
  artifact writing. Reuses the existing `BacktestPipeline`
  (`generate_strategy` → `execute_backtest(wfv_enabled=True)` →
  `generate_insights`) — no compile/codegen/sandbox/engine
  reimplementation, no sandbox/engine bypass. Acquires the existing
  `app.state.backtest_semaphore` around each backtest and plumbs the
  existing `CancellationToken` for cooperative stop.
- **`backend/robust_objective.py`** — the WFE-gated, min-trades-floored,
  drawdown/over-leverage-penalised scalar (`robust_score`, `targets_met`,
  `select_best`). `bestIterationId` is chosen by this, never by raw return.
- **Persisted `autoRun` status** merged into `session.json` via
  `write_session_meta` (read-update-write) after every iteration and every
  state transition: `status` (queued|running|complete|stopped),
  `stopReason` (criteria-met|budget-exhausted|null), `currentIteration`,
  `maxIterations`, `bestIterationId`, `startedAt`, `updatedAt`. Durable file
  store only — survives a worker restart and a browser reload.
- **Hard budget**: `max_iterations` is always defaulted (absent/≤0 → 3) and
  clamped (`HARD_MAX_ITERATIONS = 50`); optional `max_wall_clock_seconds`.
  The loop checks budget/cancel BEFORE each round — it never takes "one more
  round" past the cap.
- **`session_routes.py`**: `GET /api/sessions/{id}` now also returns the
  small `autoRun` status object from `session.json` meta (NOT per-iteration
  result/rating — the lazy-load anti-goal stays intact).
- **Frontend live tracking (J-08)**: `useBacktest.ts` polls the lightweight
  session/open path every 2.5 s while `autoRun.status` is running/queued and
  stops at terminal; merges new iterations without wiping already
  lazy-loaded heavy detail; surfaces a live status bar (running → terminal +
  stop reason) in `SessionContainer` and a "★ Best" badge on the
  robust-best iteration card.
- **Frontend J-02 fix**: the RIGHT analysis panel (trades table + equity
  curve + walk-forward) now re-binds when a prior run is selected.

## Files Changed

- `apps/backend/backend/auto_session.py` — **NEW**: controller, DTOs,
  bounded loop, durable `autoRun` state machine, activity emission,
  endpoint.
- `apps/backend/backend/robust_objective.py` — **NEW**: robust scalar +
  `targets_met` + `select_best`.
- `apps/backend/backend/api.py` — mount the auto-sessions router (2 lines).
- `apps/backend/backend/session_routes.py` — include the `autoRun` block in
  `GET /api/sessions/{id}` (small status object only).
- `apps/backend/tests/test_auto_session.py` — **NEW**: 15 tests covering
  DoD scenarios (a)–(f) + error/robustness cases + robust-objective units.
- `apps/frontend/src/hooks/useBacktest.ts` — `AutoRunStatus` type, `autoRun`
  state, hydration wiring, **backend-owned save suppression**, live polling,
  J-02 guard fix (`loadingDetailIdRef` instead of the stale
  `loadedDetailIdsRef`; dead ref removed), `sessionStatus` headless wiring,
  `autoRun` returned from the hook.
- `apps/frontend/src/components/IterationPanel.tsx` — `key={selected.id}` on
  `IterationDetailView` (J-02 remount); thread `bestIterationId`.
- `apps/frontend/src/components/IterationCard.tsx` — `isBest` prop +
  "★ Best" badge (compact + full views).
- `apps/frontend/src/components/SessionContainer.tsx` — `AutoRunBar` live
  status strip; pass `bestIterationId` to `IterationPanel`.

## Tests Run

Backend: `cd apps/backend && .venv/bin/python -m pytest tests/ -v`
Result: **139 passed, 1 failed**. The single failure is the pre-existing,
out-of-scope `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
(Key Capability #10 nice-to-have, explicitly out of scope). Baseline was
124 passed / 1 failed → +15 new tests, **zero new regressions**.
`ruff check` passes on all new backend files.

Frontend: `cd apps/frontend && npm run build` (tsc + vite build) — **passes
clean** (the >500 kB chunk warning is pre-existing and unrelated). NOTE:
`npm run lint` cannot run — the repo has **no ESLint config file at all**
(pre-existing; affects every file, not this change). `tsc --noEmit` is
clean.

Live smoke (real OPENAI_API_KEY + Binance, throwaway `BACKTEST_STORE_DIR`,
`max_iterations:1`, short range):
- `POST /api/auto-sessions` → `200 {"sessionId","status":"running"}`;
  `GET /api/sessions` listed it immediately; `GET /api/sessions/{id}`
  returned the `autoRun` block — **no browser interaction to start** (J-07).
- The server-side loop ran generate→backtest→walk-forward→insights and
  reached terminal `status:complete`, `stopReason:criteria-met`,
  `bestIterationId` set (J-08 backend + J-09).
- Per-iteration artifact: lightweight list path had **no** heavy keys; the
  per-iteration endpoint returned full `result` (7 trades, 480 equity
  points), `walkForwardResult`, and 10 insights suggestions — identical
  shape to a manual run.
- Secret scan of all written artifacts: **no** API key / Authorization
  strings present.

## Known Issues

- **Frontend live exercise pending browser-qa**: the polling/status-bar/best
  badge and J-02 re-bind were verified by build + code review + the live
  backend smoke; the in-browser J-02/J-08/J-09 user flows are exercised by
  browser-qa (tiny budgets) as the spec designates.
- **Concurrent meta writes**: a browser viewing a backend-owned session no
  longer writes its artifacts back (save effects are suppressed when
  `autoRun` is non-null), so there is no client/loop clobber. The loop's
  `write_session_meta` is the single `autoRun` writer; top-level merge keeps
  `autoRun` intact even if another path writes `backtestParams`. The status
  is re-flushed every iteration so it self-heals — acceptable for iter-1;
  full ownership hardening is J-10/iter-2.
- **Walk-forward on very short ranges** may yield 0 windows; the robust
  objective then gates that candidate down (still finite, still selectable)
  and the run stops `budget-exhausted` rather than `criteria-met` if a
  `min_wfe` target was supplied — both are valid terminal J-09 outcomes.
- **Out of scope (untouched, intentional):** the legacy in-browser
  `startAutoRun` loop (J-10/iter-2 — coexistence is expected, not a
  violation); the public stop endpoint (J-11 — only the token is plumbed);
  J-12–J-16 optimizer; full AI-token/USD cost tracker (J-13). The
  pre-existing directions-cache test failure was not "fixed" (out of scope).
- A throwaway `/tmp/ai_smoke_store` from the live smoke could not be removed
  (sandbox blocked `rm -rf`); it is an ephemeral OS-managed temp dir, not
  committed, not the project store.

## Suggested Next Phase

iter-2 should take **J-10** (rewire the in-browser "Auto Run" button to
`POST /api/auto-sessions` and delete the legacy `startAutoRun` in-browser
loop, proving backend-is-source-of-truth by surviving a mid-run reload) and
**J-11** (the `POST /api/auto-sessions/{id}/stop` endpoint + a UI stop
control — the `CancellationToken` is already plumbed and the `stopped`
terminal state already exists). The Optimizer layer (J-12–J-16:
open-universe search, immutable AI-token/USD cost tracker, staged
SCREEN→PROMOTE, global-history warm-start, deep overfit-gating) follows
after Foundation hardening.

---

## Fix Notes — QA FAIL retry (2026-05-19)

QA report `reports/qa/goal-auto-money-printer-iter-1-qa.md` returned **FAIL**
with three blockers (B1 critical, B2/B3 P1). Each is fixed below; nothing
else was changed.

### B1 (CRITICAL, TC-06 anti-goal): background job blocked the API event loop

**Root cause (verified in code, not the QA's stated hypothesis).** QA's
`reports/qa/...-qa.md` attributed the block to a `to_thread` "GIL convoy"
and recommended a process pool. Reading the code disproved that: the
backtest/rating/walk-forward are *already* offloaded
(`pipeline.py:637/673`, `walk_forward.py:304-361` use
`asyncio.to_thread`), and under CPython 3.11 GIL fairness a single
offloaded CPU worker does not produce 6–15 s hard timeouts. The real,
verified asymmetry: the **manual path persists iterations through
`session_routes.py`, which wraps *every* store call in
`await asyncio.to_thread(...)`**, whereas `auto_session.run_auto_session`
called `session_store.write_iteration` (a `json.dumps` of the ~1.2 MB
result + 6 file writes), `write_session_meta`/`read_session_meta` (via
`_update_autorun`, ~3×/iter), `append_activity_entries`, and
`jsonable_encoder(result)`+`_json_safe(...)` **directly on the
event-loop thread**, every iteration, for the whole multi-iteration run.
That non-offloaded 0.5–4 s/iteration of pure-Python encoding + blocking
disk I/O on the single event-loop thread is what starved `accept()` and
produced the `000` timeouts.

**Evidence.** A deterministic measurement harness (faithful yielding fake
pipeline, large result) showed unfixed loop-starvation scaling with
payload: 0.14 s (5k equity) → 0.54 s (15k) → 1.18 s (30k) → 2.23 s (60k);
the real run's bigger results + heavier real WF + disk latency match QA's
live 6–15 s.

**Fix (surgical, non-regressing — mirrors the manual path).** In
`apps/backend/backend/auto_session.py`, every synchronous CPU/disk store
operation on the controller's event-loop path is now offloaded via
`asyncio.to_thread`:
- `_update_autorun` split into a sync `_update_autorun_sync` (read-update-
  write of `session.json`) + an async wrapper that runs it in a worker
  thread; all 8 call sites `await`ed.
- New sync `_serialize_artifacts(result, rating, wf)` (the
  `jsonable_encoder` + `_json_safe` projection) offloaded via `to_thread`.
- `session_store.write_iteration`, `append_activity_entries`, the
  loop-entry `read_session_meta`, `_record_failed`'s writes, and the
  endpoint's pre-return `write_session_meta` all wrapped in `to_thread`.
- One defensive `await asyncio.sleep(0)` per iteration so back-to-back
  rounds always yield a clean loop turn.

No process pool, no pickling, no change to the shared pipeline, the
sandbox, the engine, or the manual path. Durable-status semantics are
unchanged (still a real `session.json` write, just off the loop thread);
the loop remains the single `autoRun` writer (calls are awaited
sequentially). Not an anti-goal regression.

**New regression guard.** `tests/test_auto_session.py::
test_headless_loop_does_not_block_event_loop` runs the loop with a large
result while sampling the event loop with a heartbeat; asserts max
inter-tick gap `< 0.5 s` (spec bound is 3 s). It fails on the pre-fix code
(`0.98 s` blocked) and passes after the fix.

### B2 (P1, browser-qa UT-03, J-07): headless session not in the list without reload

`apps/frontend/src/App.tsx` fetched the session-tab list on mount only.
Added a strictly-additive discovery effect: every 5 s (and on `window`
`focus`) it calls `fetchSessionTabs()` and merges any **unknown** backend
session IDs into `liveSessions`. It never removes, renames, reorders, or
persists tabs and never changes the active session, so manual / in-browser
sessions and the J-02/J-08 paths are untouched. A new headless session
created via `POST /api/auto-sessions` now appears in the Sessions dropdown
within ~5 s with no manual page reload.

### B3 (P1, browser-qa UT-06, J-09): "★ Best" badge missing in expanded card

`BestBadge` was a private function in `IterationCard.tsx`. Exported it (so
the identical badge + tooltip is reused — keeps UT-19 green), added an
`isBest` prop to `IterationDetailView`, render `<BestBadge />` next to the
strategy name in the expanded header, and threaded
`isBest={selected.id === bestIterationId}` from `IterationPanel`.

### Tests Run (retry)

Backend: `cd apps/backend && .venv/bin/python -m pytest tests/ -v` →
**140 passed, 1 failed**. The single failure is the pre-existing,
out-of-scope `tests/test_directions_cache.py::
test_write_and_read_full_round_trip` (explicitly out of scope; "may remain
failing, nothing else may newly fail"). Baseline was 139 passed → **+1 new
test (the B1 guard), zero new regressions**. `ruff check
backend/auto_session.py tests/test_auto_session.py` → clean.

Frontend: `cd apps/frontend && npm run build` (tsc + vite) → **EXIT 0,
clean** (the pre-existing >500 kB chunk warning is unrelated).

### Files Changed (retry)

- `apps/backend/backend/auto_session.py` — offload all store/encode I/O off
  the event-loop thread (B1).
- `apps/backend/tests/test_auto_session.py` — new event-loop responsiveness
  regression guard (B1).
- `apps/frontend/src/App.tsx` — additive session-list discovery poll (B2).
- `apps/frontend/src/components/IterationCard.tsx` — export `BestBadge`
  (B3).
- `apps/frontend/src/components/IterationDetailView.tsx` — `isBest` prop +
  render badge in expanded header (B3).
- `apps/frontend/src/components/IterationPanel.tsx` — thread `isBest` into
  the detail view (B3).

### Not Regressed (per QA "do not regress" list)

Backend correctness/durability/boundedness/robust-selection/lazy-load/
no-secrets are untouched (all 15 prior `test_auto_session` tests still
pass). The J-02 re-bind, manual-session guard, and regression journeys are
frontend-additive only — no logic in the manual or J-02/J-08 paths was
modified.
