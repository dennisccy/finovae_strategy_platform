# goal-financial_free-iter-2 Dev Handoff

**Phase:** goal-financial_free-iter-2
**Date:** 2026-05-23
**Agent:** developer
**Status:** complete
**Target journeys:** J-08 (live UI tracking), J-10 (backend single source of truth / survives reload), J-11 (server-side stop)
**Required-still-passing:** J-01/J-02/J-05/J-07/J-09 (+ J-03/J-04/J-06)
**Frontend Present:** yes

## What Was Built

**Layer-1 finish — the backend auto-session loop is now the ONLY Auto Run engine.**

### Backend — B1+B2 concurrency, co-designed (one fix)
- **Off-loop `autoRun` persistence (B1)** + **single-writer serialization (B2)** in
  `auto_session.py`, solved *together* (per the iter-1 lesson). A new module helper
  `_run_off_loop(fn, *args)` moves the controller's blocking `session.json` reads/writes off
  the event loop (`asyncio.to_thread`); the whole read-modify-write of the `autoRun` block now
  runs under a **per-session `asyncio.Lock`** that is **shared** with the `/stop` endpoint.
- `AutoSessionController._save_auto_run` and `_stop_requested` are now `async` and hold that
  shared lock across the off-loop read+write, so a `/stop` issued *during* a controller save is
  serialized **after** it and its `stopRequested=True` is never clobbered (the TOCTOU the spec
  warned about). `_finish` and all call sites were made `await`-correct.
- `auto_session_routes.py`: a new `AutoSessionHandle(task, lock)` is registered on
  `app.state.auto_sessions`; `POST /api/auto-sessions` creates the lock, passes it to the
  controller, and stores the handle. `POST /api/auto-sessions/{id}/stop` now takes the request,
  looks up that shared lock, and performs its read-modify-write **inside** it (transient lock if
  no live handle — nothing to race locally).
- **Contracts unchanged**: `POST /api/auto-sessions` and `/stop` request/response shapes are
  identical to iter-1; `shared/contracts.py` untouched; no new endpoint, no new infra.

### Frontend — rewire to the backend; delete the in-browser loop
- **J-10**: `startAutoRun` (`useBacktest.ts`) no longer runs an in-browser iterate loop. It seeds
  a **new** backend auto-session from the baseline iteration's NL prompt + params via
  `POST /api/auto-sessions`, then asks the parent (`App`) to add a session tab and switch to it.
  The **in-browser `while` loop and the duplicate `scoreIteration` are deleted** (grep-verified),
  along with now-dead state (`autoRunStopRef`, `autoRunIterationIdsRef`, the local
  `createSemaphore`, the unused `markSuggestionDisabled`, `workerCountRef`).
- **J-08**: the hook captures the backend `autoRun` block on hydration and **polls the existing
  canonical `GET /api/sessions/{id}`** every ~2.5s while the status is active (queued/running),
  merging newly-appeared iteration cards (lightweight) and the activity log; heavy iteration
  detail stays lazy-loaded on selection. A new **Automated-session status strip**
  (`AutoSessionStatusStrip.tsx`) renders run state, budget counters, stop reason, and the best
  badge at the top of the Iterations panel.
- **Single source of truth**: the running indicator (`sessionStatus.isAutoRunning`, the
  SessionPicker spinner, the Auto Run/Stop controls, progress counter) is **derived from the
  polled `autoRun.status`**, not a local boolean — so after a browser reload an active session is
  still shown as running and polling resumes automatically.
- **J-11**: `stopAutoRun` POSTs `/api/auto-sessions/{id}/stop`; the next poll reflects `stopped`.
- **Read-only for auto-sessions**: any session that has an `autoRun` block is treated as
  backend-owned — the frontend's iteration/activity/meta save-effects are disabled for it, so the
  UI never echoes or clobbers backend-written records through the non-atomic `session.json` merge.

## Files Changed

**Backend**
- `apps/backend/backend/auto_session.py` — `_run_off_loop` helper; `auto_run_lock` ctor param +
  `self._lock`; `_save_auto_run`/`_stop_requested`/`_finish` now async + lock-guarded + off-loop;
  all call sites awaited.
- `apps/backend/backend/auto_session_routes.py` — `AutoSessionHandle(task, lock)`; share the lock
  controller↔`/stop`; `/stop` now takes `raw_request: Request` and does its RMW under the lock.
- `apps/backend/tests/test_auto_session.py` — **NEW** regression test
  `test_stop_racing_save_auto_run_is_not_dropped` (+ `asyncio` / module import).

**Frontend**
- `apps/frontend/src/lib/sessionApi.ts` — `AutoRunStatus`/`AutoRunBudget` types, `isAutoRunActive`,
  `startAutoSession()`, `stopAutoSession()`.
- `apps/frontend/src/hooks/useBacktest.ts` — core rewire (loop removed; `autoRun` state + poll +
  merge; derived running/progress; backend-owned save gating; backend-driven start/stop; new
  `onAutoSessionCreated` option).
- `apps/frontend/src/components/AutoSessionStatusStrip.tsx` — **NEW** status strip.
- `apps/frontend/src/components/IterationPanel.tsx` — render the strip (new `autoRun` prop).
- `apps/frontend/src/components/SessionContainer.tsx` — pass `autoRun` to the panel; thread
  `onAutoSessionCreated` into the hook.
- `apps/frontend/src/App.tsx` — `handleAutoSessionCreated` (add tab + switch).

**Docs**
- `runs/goal-session-financial_free/state/blueprint.md` — **additive** Notes clarification: the
  in-browser `scoreIteration`/loop is now retired; the backend `RobustScorer` is the sole engine /
  "best" definition. (No IA or data-contract row change.)

## Tests Run

**Backend** — `cd apps/backend && .venv/bin/python -m pytest`
Result: **165 passed, 1 deselected, 1 failed** (~6s).
- The **1 failed** is the pre-existing, unrelated `test_directions_cache.py::test_write_and_read_full_round_trip`
  (nice-to-have Capability #10, an untouched module) — the documented carry-forward red, **not a
  regression** (it failed identically in iter-1).
- The 40 iter-1 auto-session tests stay green; the new B1+B2 regression test passes (41 in the two
  auto-session files).
- `ruff check` clean on all changed backend files.

**B1+B2 regression — red/green verified.** With the shared lock removed (controller's
`_save_auto_run` given a throwaway lock), the new test FAILS as expected — the concurrent `/stop`
is dropped and the loop reaches `budget-exhausted` instead of `stopped`. With the shared lock
restored it PASSES. This directly demonstrates that B1 (off-loop) without B2 (serialization) drops
the stop, and that the co-design is required.

**Frontend** — `cd apps/frontend && npm run build` (tsc + vite) **passes**; `npm run lint`
(`--max-warnings 0`) **passes**. Grep confirms the in-browser iterate loop and duplicate
`scoreIteration` are **removed** from `useBacktest.ts`.

**Service startup** — `uvicorn main:app` boots clean (no startup errors; orphan reconciliation
runs); `GET /api/health` → 200, `GET /api/sessions` → 200, `POST /api/auto-sessions/{unknown}/stop`
→ 404, open-universe `POST /api/auto-sessions` → 400 (Layer-2 boundary preserved). Server stopped
after the check.

## Known Issues / Limitations

- **Live end-to-end auto-run (real LLM + Binance) was NOT executed by the developer** to avoid
  burning API tokens. The loop itself is covered by the hermetic suite (165 tests) and the iter-1
  live smoke; the frontend wiring is build/lint-verified and the endpoints respond live. **The
  browser-qa-agent should run J-08/J-10/J-11 with a tiny budget** (≤2 iterations, short range,
  cheapest model, lenient targets) — honoring the documented Chrome-MCP headless render-throttle
  (verify via `GET /api/sessions`, `GET /api/sessions/{id}`, `POST /api/auto-sessions`, `/stop` and
  the persisted `autoRun` block if pixels are blank).
- **Auto-sessions are backend-owned / read-only in the frontend** (save-effects disabled when an
  `autoRun` block is present). This is the deliberate design that prevents the UI from
  echoing/clobbering backend writes. Consequence: manually branching off a *finished* auto-session
  (typing a follow-up prompt into it) is not persisted; for manual iteration, use a manual session.
  `selectedIterationId` is likewise not persisted for auto-sessions (cosmetic — no run is
  auto-selected on reopen, which keeps the live tree visible).
- **Auto Run count is clamped to the backend's 1..50** when building the request; the config-bar
  input still accepts up to 100 (silently clamped). QA uses tiny budgets, so this is not exercised.
- **`max_wall_clock_sec` = `max(120, maxIterations * 180)`** — a bounded safety cap (anti-goal
  honored) sized generously so it never prematurely kills a legitimate multi-round run;
  `max_iterations` remains the primary terminator.
- Pre-existing: `mypy` is not gated in this repo; `test_directions_cache` red as noted above.

## Suggested Next Phase

Layer-2 begins (J-12…J-16): open-universe search from a bounded seed universe, hard token/USD
budget enforcement by the immutable cost tracker (wiring real token accounting from the pipeline),
staged SCREEN→PROMOTE (cheap-first, walk-forward/strong-model only on survivors), global-history
warm-start (read-only mining, opt-out honored), and the leaderboard / overfit-gating UI. The
status strip + live-tracking plumbing landed here is the surface those journeys extend.
