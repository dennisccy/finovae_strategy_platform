# Goal Iteration 2 — Rewire "Auto Run" to the backend and add a stop control

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** auto-money-printer
- **Iteration:** 2
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes
- **Target journeys:** J-10, J-11
- **Required-still-passing journeys:** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST NOT run a second in-browser iterate loop.
  - The automated-session `autoRun` status MUST be persisted to the durable store and survive a worker restart and a browser reload; it MUST NOT live only in browser memory or a non-persisted in-process variable.
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.
  - `GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint.
  - The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
  - `BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart.

## GOAL

Make the backend the single source of truth for the automated strategy
search: the existing in-UI "Auto Run" button starts a server-driven
auto-session (no in-browser iterate loop), the run survives a mid-run browser
reload, and the user can stop a running automated session from both the API
and the UI — with the best-so-far iteration still marked.

## BACKGROUND

Layer-1 Foundation (J-07/J-08/J-09) landed in iter-1: `POST /api/auto-sessions`
creates a session synchronously and drives a detached, budget-bounded
server-side loop that writes the standard file-store artifacts and exposes a
durable, polled `autoRun` status block. But the legacy **in-browser** iterate
loop still exists and is still what the UI "Auto Run" button triggers. This
iteration closes the Foundation by rewiring the button to the backend, deleting
the in-browser loop, and adding the missing stop trigger.

The prior evaluator explicitly recommended iter-2 at **full** depth: J-10 is
the structural rewire that *activates the strongest anti-goal in the goal* ("no
second in-browser iterate loop"), it crosses the backend/frontend boundary,
deletes a large stateful frontend code path, adds a new endpoint plus an
in-process cancellation registry, and risks regressing the just-passed J-02 and
J-08 — so the full pipeline (audit + ux-regression + closure) is warranted.

**Lessons that MUST be applied this iteration (from `lessons.md`):**

- **iter-1 lesson (directly targets J-10/J-11):** the in-session `AutoRunBar`
  can show a *stale terminal* status for a freshly-opened *still-running*
  session when many `SessionContainer`s are mounted and the user switches
  sessions rapidly — a real ownership/concurrency bug, not cosmetic. J-10 MUST
  **harden `AutoRunBar`/`SessionContainer` ownership (re-derive per-session
  `autoRun` status authoritatively on mount/switch)**, not merely rewire the
  button. Once the backend is the single source of truth this becomes a hard
  correctness failure if left unfixed. Also: never trust a reconciled
  `ui-test-results.md` headline alone — verify the post-fix source diff plus
  the QA MODE-2 (full-mode) report.
- **iter-0 lesson (protects required-still-passing J-02):** selecting an older
  run must reload its **RIGHT analysis panel (trades table + equity curve +
  WF)**, not just the left summary. J-02 is now passing and is a
  required-still-passing journey; `SessionContainer.tsx` / `useBacktest.ts` —
  the exact files this iteration edits — are where that re-bind lives. Do not
  regress it.

## Current code state (grounding — verified before writing this spec)

- Legacy in-browser loop: `apps/frontend/src/hooks/useBacktest.ts` —
  `startAutoRun` `useCallback` at **lines 2183–2379** and its companion
  `stopAutoRun` at **2381–2395**, plus the in-browser-only state it owns
  (`autoRunStopRef`, `autoRunIterationIdsRef`, `isAutoRunning`,
  `autoRunProgress`, `abortControllerRef` usage for auto-run).
- UI wiring: `apps/frontend/src/components/SessionContainer.tsx` — config-bar
  trigger `onStartAutoRun` (lines ~238–242) and `onStopAutoRun={stopAutoRun}`
  (~243); per-iteration trigger `handleStartAutoRunFromCard` (~218–220) passed
  to `IterationPanel onStartAutoRun` (~284). `AutoRunBar` is defined in
  `SessionContainer.tsx:31` and rendered only when the durable `autoRun` block
  is non-null (~248). The `autoRun` block is hydrated in `useBacktest.ts:535`
  and refreshed by the live poll at `useBacktest.ts:711–800`.
- Backend: `apps/backend/backend/auto_session.py` — `POST /api/auto-sessions`
  (`@router.post("")`, `create_auto_session`, ~line 569) creates the session
  in the existing file store and launches a **detached** `asyncio.create_task`
  runner. `CancellationToken` is created **locally** (~line 641) and passed
  into `run_auto_session`; the loop already checks `cancel_token.is_cancelled`
  (~304/332) and maps a cancelled run to terminal `status="stopped"`
  (~459–460). There is **no** public stop route and **no** registry mapping a
  `sessionId` to its live token, so a stop request currently cannot reach a
  running loop.

## IN SCOPE

### Backend
- [ ] Add a public stop endpoint `POST /api/auto-sessions/{session_id}/stop`
      on the existing `auto_session.py` router. It MUST cooperatively request
      cancellation of the running loop and return promptly (must not block the
      event loop or wait for the loop to finish).
- [ ] Make the running loop's cancellation reachable by `session_id`: maintain
      an **in-process** registry (module-level dict — NO new infra) populated
      in `create_auto_session` and cleaned up when the run reaches any terminal
      state. The stop endpoint cancels via this registry.
- [ ] Make stop **durable and worker-safe**: the stop request must also be
      recorded in the durable session store so the cooperative loop honors it
      even if the live in-process token is not in the handling worker (multi-
      `WEB_CONCURRENCY`) or after a restart. Reuse the existing `_update_autorun`
      / session-store mechanism the loop already polls each round — no parallel
      store, no schema fork, no SQLite/DB.
- [ ] On stop: the run transitions to the existing terminal `status="stopped"`
      with a visible `stopReason`, **no further iterations are appended after
      the stop**, and the best-so-far iteration (selected by the existing
      robust objective) remains marked (`bestIterationId` preserved/finalized
      from whatever completed before the stop — never re-selected by raw return).
- [ ] Stop endpoint error/edge handling: stopping an unknown `session_id`
      returns a clean 404; stopping an already-terminal session is idempotent
      (no error, no extra iterations, no state regression).

### Frontend
- [ ] Rewire **both** UI "Auto Run" entrypoints in `SessionContainer.tsx` (the
      `BacktestConfigBar` trigger and `handleStartAutoRunFromCard`) so clicking
      "Auto Run" on a completed iteration starts a **backend** auto-session via
      `POST /api/auto-sessions`, deriving the pinned config from that iteration
      (its natural-language strategy, `symbol`/`timeframe`/`start_date`/
      `end_date`/`initial_capital` from its params, the selected model, and a
      `budget` whose `max_iterations` maps from the existing `autoRunCount`
      control). The resulting backend-driven session must appear and update in
      the UI indistinguishably from one started directly via the API.
- [ ] **Delete** the legacy in-browser iterate loop `startAutoRun`
      (`useBacktest.ts:2183–2379`) and its now-dead companions (`stopAutoRun`
      at 2381–2395 and the in-browser-only auto-run state/refs it solely owns).
      Remove only code your change makes unused; do not delete unrelated code.
      After this iteration `grep` for an in-browser iterate `while` loop driving
      generate→backtest→insights must find nothing.
- [ ] Wire the UI stop control to the new `POST /api/auto-sessions/{id}/stop`
      endpoint (replace the old in-browser `onStopAutoRun={stopAutoRun}` path),
      so the existing stop button cancels the server-driven run.
- [ ] **Harden `AutoRunBar`/`SessionContainer` ownership (mandatory — iter-1
      lesson):** each session's `autoRun` status must be authoritatively
      re-derived from the backend on mount and on session switch, so a
      freshly-opened *still-running* session never displays a stale terminal
      status under rapid multi-session switching with many `SessionContainer`s
      mounted. The session-list spinner and the in-session `AutoRunBar` must
      agree.

### New user-facing capability
The user can launch a fully server-driven automated strategy search from the
existing "Auto Run" button, close or reload the browser while it keeps running,
reopen the session to see it still progressing toward a terminal state, and
stop it on demand from the UI — with the best strategy still marked.

### New information displayed
A working UI **Stop** affordance on a running automated session, and a
correct, non-stale per-session running/terminal status that survives reload and
rapid session switching. (`stopped` terminal status + stop reason already
render via the existing `AutoRunBar`.)

### New user actions
- "Auto Run" button → starts a backend-driven auto-session (no longer an
  in-browser loop).
- Stop control → `POST /api/auto-sessions/{id}/stop` (cancels the server run).

### UI surface changes
No new pages. Changes are confined to `SessionContainer.tsx` (start/stop
wiring + `AutoRunBar` ownership) and `useBacktest.ts` (delete in-browser loop;
start/stop now call the backend; status sourced from the durable polled block).

### Product surface delta
The automated search becomes genuinely headless and durable end-to-end:
browser is a viewer/controller, not the engine. Closing the tab no longer
kills the run; the run is stoppable and the best result is preserved.

## OUT OF SCOPE

- J-12–J-16 (open-universe search, hard token/USD budget enforcement, staged
  SCREEN→PROMOTE, global-history warm start, robust-objective overfit gating).
  Open-universe is still expected to be rejected with a 4xx by
  `create_auto_session`; do not implement it here.
- Any change to `shared/contracts.py`, the RestrictedPython sandbox, the
  deterministic engine, or the `BacktestPipeline` internals.
- Any new datastore/queue/scheduler/broker; any schema fork of the session
  file store.
- Reworking the robust objective or best-selection algorithm (reuse as-is;
  this iteration only ensures the existing selection is preserved on stop).
- Cosmetic redesign of `AutoRunBar` beyond the correctness/ownership fix.

## DEFINITION OF DONE

- [ ] **J-10** passes via browser-qa: from the UI, click "Auto Run" on a
      completed iteration with a tiny budget; mid-run reload the browser tab and
      reopen the session; progress keeps advancing after the reload and the
      session reaches a terminal state — proving the loop is server-driven.
- [ ] **J-11** passes via browser-qa: start a run with a budget large enough
      that it is still running; stop it via `POST /api/auto-sessions/{id}/stop`
      (and via the UI stop control); the run transitions to `stopped`, no
      further iterations are appended after the stop, and the best-so-far
      iteration remains marked.
- [ ] The legacy in-browser `startAutoRun` iterate loop is **deleted** (no
      second iterate loop in the frontend) — verified by source diff.
- [ ] Required-still-passing journeys J-01, J-02, J-03, J-04, J-05, J-06,
      J-07, J-08, J-09 remain green. Explicitly re-verify **J-02** (RIGHT
      analysis panel re-binds on history selection) and **J-08** (no stale
      `AutoRunBar` terminal status under rapid session switching).
- [ ] No anti-goal violation introduced (see reminders above) — verified at
      source-diff + test level, not just from a report headline.
- [ ] Unit/integration tests pass; the existing `test_auto_session` suite stays
      green and is extended for the stop endpoint; no regressions.
- [ ] Dev handoff written at `docs/handoffs/goal-auto-money-printer-iter-2-dev.md`.
- [ ] All 6 UI visibility artifacts produced; phase-closure gate passes.

## TESTING REQUIREMENTS

- **Browser (named):** J-10 (start-from-UI → mid-run reload → run still
  advances → terminal) and J-11 (start large budget → stop via API and via UI
  control → `stopped`, no post-stop iterations, best still marked). Re-verify
  J-02 (open a prior run; trades table + equity curve + WF re-bind in the right
  panel, not just the left summary) and J-08 (open a freshly-started
  still-running session while switching sessions rapidly; status is "running",
  not a stale terminal — session-list spinner and `AutoRunBar` agree).
- **Unit/integration (must have tests):**
  - `POST /api/auto-sessions/{id}/stop` transitions a running session to
    `stopped`, appends **no** iterations after the stop, preserves
    `bestIterationId`, and is honored cooperatively (loop polls the durable
    stop signal — not only the in-process token).
  - In-process cancellation registry is populated on create and removed on
    every terminal path (`criteria-met`, `budget-exhausted`, `stopped`, crash).
  - Stop is worker-safe / restart-safe: a stop with no live in-process token in
    the handling worker still drives the run to a terminal `stopped` state via
    the durable signal (assert, do not skip).
  - Best-on-stop: stopping after ≥1 completed iteration keeps the
    robust-objective best marked; a higher raw-return but WFE-failing /
    over-leveraged candidate is still NOT marked best.
  - Regression guards stay green: durable `autoRun` survives restart/reload;
    budget still hard-bounded (no extra round past cap on stop path);
    event-loop non-blocking; no secrets in artifacts; `GET /api/sessions/{id}`
    still lazy; `contracts.py` unchanged.
- **Error cases (must be rejected/handled cleanly):** stop on unknown
  `session_id` → 404; stop on an already-terminal session → idempotent no-op
  (no error, no extra iteration, no state regression); open-universe `POST
  /api/auto-sessions` (no symbol/timeframe) still → 4xx (unchanged, J-12 scope).

## NOTES

- **Depth = full** is mandated by the prior evaluator's explicit
  recommendation and the structural risk profile (frontend loop deletion +
  new endpoint + cancellation registry + durable-state + cross-boundary,
  with J-02/J-08 regression exposure). Run the full 11-step pipeline
  including audit, ux-regression, and phase-closure.
- This iteration **activates** the anti-goal "after the rewire, the iterate
  loop MUST exist only in the backend." Deleting `startAutoRun` is mandatory,
  not optional — a coexisting in-browser loop is now a hard violation (it was
  spec-expected only through iter-1).
- The `CancellationToken` and the terminal `stopped` state machine are
  already plumbed in `auto_session.py`; J-11's net-new work is the *reachable
  trigger* (public endpoint + by-`sessionId` registry + durable cooperative
  stop signal) and the UI control — not a new state machine.
- Implementation wiring details (exact config-derivation mapping, how the UI
  stop button binds, registry lifecycle) are the developer's to decide within
  the constraints above; this spec fixes outcomes, anti-goals, and the two
  mandatory lessons, not the micro-implementation.
- Skeptical-evaluation note for QA/reviewer/auditor: do not accept a
  reconciled `ui-test-results.md` headline at face value — cross-check the
  post-fix source diff and the QA MODE-2 report (iter-1 lesson).
