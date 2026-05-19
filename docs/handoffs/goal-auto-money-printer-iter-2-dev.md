# goal-auto-money-printer-iter-2 Dev Handoff

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built

Closes the Layer-1 Foundation: the backend is now the **single source of
truth** for the automated strategy search. J-10 (rewire + survive reload) and
J-11 (stoppable run, best preserved) landed.

- **`POST /api/auto-sessions/{session_id}/stop`** (new public endpoint on the
  existing `auto_session.py` router). Cooperatively requests cancellation and
  **returns promptly** — it never awaits loop completion or blocks the event
  loop. Unknown / non-auto session → clean **404**. Already-terminal session
  → **idempotent 2xx no-op** (writes nothing; no extra iteration; no state
  regression).
- **In-process cancellation registry** — a module-level
  `_CANCEL_REGISTRY: dict[session_id → CancellationToken]` (NO new infra).
  Populated in `create_auto_session` (before the detached task launches);
  removed on **every** terminal path via `run_auto_session`'s `finally`
  (criteria-met / budget-exhausted / stopped / crash) plus a
  defence-in-depth removal in the `_runner` crash handler.
- **Durable, worker-safe stop signal** — the stop endpoint records
  `autoRun.stopRequested` in `session.json` via the existing
  `_update_autorun` mechanism (no parallel store, no schema fork). The loop
  reads it **each round** (off the event-loop thread, like the manual path)
  and breaks, so a stop is honoured even when the live token is not in the
  handling worker (multi-`WEB_CONCURRENCY`) or after a restart.
- **Terminal correctness on stop** — a stopped run transitions to the
  existing `status="stopped"` with a visible, non-null `stopReason="stopped"`,
  appends **no iterations after the stop**, and preserves `bestIterationId`
  from whatever completed before the stop via the existing robust
  `select_best` (never re-selected by raw return).
- **Frontend: both "Auto Run" entrypoints rewired** (`SessionContainer.tsx`
  config-bar trigger and per-card `handleStartAutoRunFromCard`) to start a
  **server-driven** auto-session via `POST /api/auto-sessions`, deriving the
  pinned config (NL strategy, symbol/timeframe/dates/capital, selected model,
  `budget.max_iterations` from the existing `autoRunCount` control) from the
  chosen completed iteration.
- **Frontend: legacy in-browser iterate loop deleted** — `startAutoRun`,
  `stopAutoRun`, the solely-owned state/refs (`isAutoRunning`,
  `autoRunProgress`, `autoRunStopRef`, `autoRunIterationIdsRef`), the
  now-orphaned `createSemaphore`, `workerCountRef` mirror, and
  `markSuggestionDisabled` (all solely consumed by that loop) are removed.
  No second in-browser generate→backtest→insights loop remains.
- **Frontend: UI Stop control wired** to `POST /api/auto-sessions/{id}/stop`
  (`onStopAutoRun={stopAutoSession}`).
- **Frontend: AutoRunBar/SessionContainer ownership hardened (iter-1 lesson)**
  — each session's `autoRun` status is authoritatively re-derived from the
  backend **on mount AND on session switch** (`isActive` now flows into
  `useBacktest`). The session-list spinner and the in-session `AutoRunBar`
  derive from the same durable `autoRun.status`, so they cannot disagree.

## Files Changed

- `apps/backend/backend/auto_session.py` — `_CANCEL_REGISTRY` +
  `_register_cancel`/`_unregister_cancel`; `run_auto_session` split into a
  thin wrapper (registry-cleanup `finally`) + `_run_auto_session_impl`;
  per-round durable `stopRequested` check (offloaded read); stopped terminal
  now sets `stopReason="stopped"`; `create_auto_session` registers the token;
  `_runner` crash handler unregisters + `stopReason="stopped"`; new
  `stop_auto_session` endpoint.
- `apps/backend/tests/test_auto_session.py` — +11 tests: durable stop honored
  (no post-stop iterations, best preserved), restart-safe stop with no live
  token, best-on-stop uses robust objective not raw return, registry removed
  on all four terminal paths, registry populated in `create_auto_session`,
  stop running (token cancel + durable write, returns promptly), worker-safe
  stop with no token, unknown→404 (direct + HTTP), idempotent terminal
  (direct + HTTP); autouse fixture clears the registry per test.
- `apps/frontend/src/lib/sessionApi.ts` — `startAutoSession(config)` →
  `POST /api/auto-sessions`; `stopAutoSession(id)` →
  `POST /api/auto-sessions/{id}/stop` (404/idempotent no-op never throws in
  the UI); `AutoSessionStartConfig` type.
- `apps/frontend/src/hooks/useBacktest.ts` — delete the in-browser loop +
  its solely-owned state/refs/helpers; add `startAutoSession` /
  `stopAutoSession`; authoritative per-session `autoRun` re-derive on
  mount/switch (`isActive` param); derived `headlessRunning` /
  `autoRunProgress`; `sessionStatus.isAutoRunning` now purely backend-sourced.
  The J-02 lazy-detail guard, the live poll (~tick/2.5s), and hydration were
  NOT modified.
- `apps/frontend/src/components/SessionContainer.tsx` — `useBacktest(sessionId,
  isActive)`; both start paths → `startAutoSession`; Stop → `stopAutoSession`.

## Tests Run

Backend: `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`
→ **26 passed**. Full suite `.venv/bin/python -m pytest -q` →
**150 passed, 1 failed**. The single failure is the pre-existing,
out-of-scope `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
(explicitly out of scope; "may remain failing, nothing else may newly fail").
Baseline (iter-1) was 140 passed / 1 failed → **+10 net passing, zero new
regressions**. `ruff check backend/auto_session.py tests/test_auto_session.py`
→ clean.

Frontend: `cd apps/frontend && npm run build` (tsc + vite) → **EXIT 0,
clean** (the pre-existing >500 kB chunk warning is unrelated). `npm run lint`
remains non-functional repo-wide (no ESLint config file exists — pre-existing,
unrelated to this change).

Route registration verified: `POST /api/auto-sessions` and
`POST /api/auto-sessions/{session_id}/stop` are both mounted on the app.

## Known Issues

- **New auto-session discovery is via the existing App.tsx 5 s poll (by
  spec).** Clicking "Auto Run" in a manual session creates a *new* backend
  session; per the spec ("reuse the existing live poll + AutoRunBar +
  App.tsx discovery poll", "changes confined to SessionContainer.tsx and
  useBacktest.ts") App.tsx was intentionally NOT modified. The new
  "Auto: …" session appears in the Sessions dropdown within ~5 s; an
  activity entry is logged in the originating session telling the operator
  this. **Browser-QA note (J-10):** click Auto Run → wait for the new
  "Auto: …" tab → select it → observe the AutoRunBar → reload → reopen the
  same auto-session.
- **Remaining `while` loops in `useBacktest.ts`** (`outer: while (!execData)`
  ~L1174 and `outer: while (!finalData)` ~L1962) are pre-existing
  single-backtest data/exec **retry** loops inside `generateAndExecute` /
  `runWalkForward` — NOT a generate→backtest→insights iterate loop. The
  iterate loop (`while (attempt < maxAttempts && !autoRunStopRef.current)`)
  is deleted. Verify by source diff (the anti-goal is satisfied).
- **Live external (real LLM/Binance) path not re-smoked this iteration.**
  This iteration adds only the stop trigger + the UI rewire; it introduces
  **no new external integration** and reuses the exact pipeline iter-1
  already live-smoked. The full live path (tiny budgets) is exercised by
  browser-qa (J-10/J-11) per the spec, which also designates
  `test_auto_session` to stub the LLM/Binance layers for determinism. The
  in-process FastAPI TestClient suite (26 passing, incl. the create + stop
  endpoint HTTP tests) validates the backend boots and serves the new route
  without leaving server processes alive.
- **`autoRun.stopRequested` is left set on a stopped run.** Harmless: the
  status is terminal so the loop never reads it again and the stop endpoint
  short-circuits any already-terminal session — this is what makes a re-stop
  idempotent.
- **Symbol format is passed through unchanged** from the iteration's own
  `params` (the exact value the manual run already executed successfully),
  so the server-driven run is config-identical to the run it was launched
  from. No new normalization was added (out of scope).
- Pre-existing out-of-scope `test_directions_cache` failure left as-is (not
  "fixed" — explicitly out of scope).

## Suggested Next Phase

Foundation is complete and hardened. iter-3 should open the **Optimizer
layer** starting with **J-12** (open-universe search — currently still
correctly 4xx-rejected by `create_auto_session`) and **J-13** (the immutable
AI-token/USD + wall-clock cost tracker), then J-14–J-16 (staged
SCREEN→PROMOTE, global-history warm start, deeper robust-objective overfit
gating).

---

# Fix Notes — QA FAIL retry (2026-05-19)

**Mode:** FIX MODE (QA verdict FAIL). Fixed ONLY the QA-listed blockers; no
rebuild. Scope held to the 5 in-scope files — `git diff` confirms
`shared/contracts.py`, `backend/pipeline.py`, the engine, the sandbox,
`backend/api.py`, and `robust_objective.py` are **untouched**.

## Blocker #1 (CRITICAL — anti-goal): event-loop / UI-poll starvation

**Root cause (confirmed):** the deterministic engine runs the
RestrictedPython signal bar-by-bar — pure-Python, **GIL-holding** CPU work.
`pipeline.execute_backtest` offloads it via `asyncio.to_thread`, but a
*thread* shares the API worker's GIL. During a *continuous* headless loop
that thread (plus the per-iteration `jsonable_encoder`/`json.dumps` of the
big result) holds the GIL almost the whole run, so every other
`asyncio.to_thread` file-IO task (the `GET /api/sessions` poll, the stop
endpoint's session-store read) is GIL-starved → up to 33.7 s (QA).

**Fix:** run the backtest in a **child process** (`backend/auto_session.py`).
The child has its OWN GIL, so the parent's event loop + every file-IO thread
stay responsive while a run is active.
- A single long-lived `spawn` daemon child (`_BacktestWorker`) is reused
  across iterations; the existing `BacktestPipeline` is built **once**
  child-side and run **verbatim** — no sandbox/engine bypass, `pipeline.py`
  NOT modified (anti-goal: "reuse the existing BacktestPipeline"). The CPU
  artifact-encode is done child-side too, so the parent does ZERO heavy work.
- `multiprocessing` is the Python **stdlib** (same class of in-process
  offload as the ThreadPoolExecutor already used here) — **not** new
  external infra (no Celery/Redis/DB/broker; anti-goal respected).
- The seam is a `backtest_executor` injected by `create_auto_session`.
  Left `None` (every existing unit test's fake pipeline) the backtest runs
  **in-process exactly as before** — so the 25 prior tests are behaviourally
  unchanged (verified: 26/26).
- **Stop is snappy + correct:** cancelling terminates the child immediately
  and raises `PipelineError`, which the *existing* terminal state machine
  maps to `status="stopped"` / `stopReason="stopped"` — no post-stop
  iterations, robust `bestIterationId` preserved (unchanged logic).

This also resolves **Blocker #3** (stop endpoint latency 12–16 s): the stop
endpoint's `read_session_meta`/`_update_autorun` `asyncio.to_thread` calls
are no longer GIL-starved, so it returns in ms.

**Blocker #1 test (the QA "passes by accident" point):**
`test_headless_loop_does_not_block_event_loop` was rewritten. The old stub
used `await asyncio.to_thread(time.sleep, …)` — `time.sleep` *releases* the
GIL, so it could never reproduce the starvation. The new test drives **real
pure-Python CPU-bound (GIL-holding) work through the production subprocess
seam** and asserts **deterministically** that every backtest executed in a
**different OS process** (the child stamps its pid into
`BacktestResult.run_id`; the test asserts `child_pid != os.getpid()`). A
single-thread *timing* bound cannot guard this (the GIL round-robins every
5 ms, so one in-thread CPU backtest only ~halves a concurrent probe — QA's
33 s came from the *continuous* multi-task pool saturation, removed at the
root by process isolation). Verified the guard genuinely **fails** when the
backtest is forced in-process (same pid) and **passes** via the seam.

## Blocker #2 (CRITICAL — J-08 / iter-1 lesson): live poll never converged

**Root cause (frontend, real bug):** in `useBacktest.ts` the live-poll
`tick` did `const raw = await apiLoadSession(); if (cancelled || !raw)
return` **before** re-arming `setTimeout(tick, 2500)`. `apiLoadSession`
swallows network errors → `null`. So a *single* failed/slow poll (exactly
what GIL starvation caused) **permanently killed the poll chain** — the
AutoRunBar froze at the last status ("running 5/8") until a manual reload
(which re-ran hydration + the on-mount re-derive — hence "reload fixes it").

**Fix:** `tick` now wraps the work in `try/catch` and re-arms the next tick
in a **`finally`** while the effect instance is live. The poll self-heals
from any single transient failure and reliably delivers the terminal
transition; when status flips terminal, `setAutoRun` changes the effect dep
→ cleanup clears the timer and polling stops with the bar showing the
terminal state. No reload, no stale terminal — backend and AutoRunBar can no
longer disagree indefinitely (with Blocker #1 fixed the polls also succeed
fast, so convergence is now within one 2.5 s tick).

## Blocker #4 (MEDIUM — UX): first UI Stop click silent no-op

The most likely cause is poll-driven re-render churn swapping the
Stop/Auto-Run button subtree between React commits (a programmatic click then
lands on nothing). Two in-scope mitigations:
1. The Blocker #2 fix stops `autoRun` flickering on transient poll failure,
   so `isAutoRunning` no longer toggles the button between Stop and Auto Run
   while a run is active (the button identity stays stable).
2. `autoRunProgress` is now `useMemo`-stable on `current`/`max` primitives
   (it was a fresh object every 2.5 s tick, recreating the Stop button
   subtree each poll). With both, the Stop button identity is steady so the
   first click reliably fires.

`stopAutoSession` already fires the POST unconditionally on first invoke and
never throws (api client swallows 404/idempotent). Residual: the exact MCP
click-timing behaviour can only be confirmed in-browser — **recommend
browser-qa re-verify TC-17** (root cause — poll/GIL instability — is fixed).

## Blocker #5 (INFO): J-02 right-panel re-bind — re-verify on retry

No code change: the J-02 path (`loadingDetailIdRef` / live poll hydration /
`selectIteration`) is **not** in this fix diff. My poll change only added
`try/catch/finally` re-arm semantics and preserves the existing
heavy-detail-preserving merge precedence unchanged — J-02 is not regressed.
Browser-qa should still exercise TC-19 explicitly per the spec.

## Tests Run (retry)

- Backend targeted: `cd apps/backend && .venv/bin/python -m pytest
  tests/test_auto_session.py -q` → **26 passed** (incl. the rewritten
  CPU-bound subprocess guard; no child process leaks — autouse fixture
  terminates the worker).
- Backend full: `.venv/bin/python -m pytest -q` → **150 passed, 1 failed**.
  The single failure is the pre-existing, out-of-scope
  `test_directions_cache.py::test_write_and_read_full_round_trip`
  (byte-unchanged this iteration). **Zero new regressions** (== baseline).
- `ruff check backend/auto_session.py` → clean.
- Frontend: `cd apps/frontend && npm run build` (tsc + vite) → **EXIT 0**
  (pre-existing >500 kB chunk warning unrelated).

## Known Limitations (retry)

- The child returns both the `BacktestResult`/`WalkForwardResult` objects and
  their JSON projections; for a large real run this pickles a few MB across
  the pipe. It happens in the queue feeder / `asyncio.to_thread(worker.get)`
  thread (off the event loop), so it does not re-introduce starvation;
  trimming to a scalar proxy is a future micro-optimisation, not correctness.
- One idle `spawn` daemon child may remain between runs (reused for
  throughput; daemon → reaped on server exit; killed on cancel; tests'
  autouse fixture terminates it). It is not a server process.
- Blocker #4's exact in-browser click behaviour and Blocker #5 (J-02) need
  browser-qa re-verification; the backend root cause and the certain
  frontend poll bug are fixed and unit/build-verified.
