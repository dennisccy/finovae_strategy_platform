# goal-auto-money-printer-iter-2 Execution Plan

Closes the Layer-1 Foundation: makes the backend the single source of truth for
the automated search. Rewires the in-UI "Auto Run" button to the existing
`POST /api/auto-sessions`, deletes the legacy in-browser iterate loop, adds a
public stop endpoint + by-`sessionId` cancellation registry + durable stop
signal, and hardens `AutoRunBar`/`SessionContainer` per-session ownership.
Target journeys: **J-10, J-11**. Required-still-passing: **J-01–J-09**
(explicitly re-verify **J-02** right-panel re-bind and **J-08** no-stale
`AutoRunBar`).

Goal alignment: J-10/J-11 are verbatim Layer-1 journeys in `docs/goal.md`;
this activates the anti-goal "after the rewire, the iterate loop MUST exist
only in the backend." No drift, no scope creep — J-12–J-16 (open-universe,
hard token/USD tracker, SCREEN→PROMOTE, warm-start, overfit gating) stay OUT
OF SCOPE; open-universe `POST /api/auto-sessions` must still 4xx.

## What to Build

- **Backend — public stop endpoint** `POST /api/auto-sessions/{session_id}/stop`
  on the existing `auto_session.py` router. Cooperatively requests
  cancellation and returns promptly (must not block the event loop or await
  loop completion). Unknown `session_id` → clean 404; already-terminal session
  → idempotent no-op (no error, no extra iteration, no state regression).
- **Backend — in-process cancellation registry**: a module-level
  `dict[session_id → CancellationToken]` (NO new infra). Populated in
  `create_auto_session` (the token currently created locally at ~641 must be
  registered), removed on **every** terminal path (`criteria-met`,
  `budget-exhausted`, `stopped`, crash). Stop endpoint cancels via this
  registry when the token is in the handling worker.
- **Backend — durable, worker-safe stop signal**: also record the stop request
  in the durable session store via the existing `_update_autorun` /
  `session.json` mechanism. The loop already does a `read_session_meta`-backed
  read-update-write through `_update_autorun_sync` (auto_session.py:209-224)
  on every round (`_update_autorun(... currentIteration=i)` at ~313), so add a
  cooperative per-round check of a persisted stop flag and break — so a stop
  is honored even when the live token is not in the handling worker (multi-
  `WEB_CONCURRENCY`) or after a restart. No parallel store, no schema fork, no
  DB/queue.
- **Backend — terminal correctness on stop**: transition to the existing
  `status="stopped"` with a visible `stopReason`; **no iterations appended
  after the stop**; `bestIterationId` is preserved/finalized from whatever
  completed before the stop via the existing robust `select_best` — never
  re-selected by raw return.
- **Frontend — rewire both "Auto Run" entrypoints** in `SessionContainer.tsx`
  (the `BacktestConfigBar` `onStartAutoRun` at ~238-242 and
  `handleStartAutoRunFromCard` at ~218-220) to call `POST /api/auto-sessions`,
  deriving the pinned config from the chosen completed iteration: its
  natural-language strategy, `symbol`/`timeframe`/`start_date`/`end_date`/
  `initial_capital` from its params, the selected model, and a `budget` whose
  `max_iterations` maps from the existing `autoRunCount` control. The
  resulting session must be indistinguishable in the UI from an API-started one
  (reuse the existing live poll + `AutoRunBar` + `App.tsx` discovery poll).
- **Frontend — delete the legacy in-browser loop**: remove `startAutoRun`
  (`useBacktest.ts:2183-2379`), `stopAutoRun` (2381-2395), and the auto-run-only
  state/refs they solely own (`autoRunStopRef`, `autoRunIterationIdsRef`,
  `isAutoRunning`, `autoRunProgress`, and auto-run-only `abortControllerRef`
  use). Remove only what these deletions make unused; do not touch unrelated
  code (manual run, J-02 path, `runAll`). Post-iteration `grep` for an
  in-browser generate→backtest→insights `while` loop must find nothing.
- **Frontend — wire the UI stop control** to `POST /api/auto-sessions/{id}/stop`
  (replace `onStopAutoRun={stopAutoRun}`), so the existing stop button cancels
  the server-driven run.
- **Frontend — harden `AutoRunBar`/`SessionContainer` ownership (mandatory,
  iter-1 lesson)**: each session's `autoRun` status must be authoritatively
  re-derived from the backend on mount and on session switch, so a
  freshly-opened still-running session never shows a stale terminal status
  under rapid multi-session switching with many `SessionContainer`s mounted.
  The session-list spinner and the in-session `AutoRunBar` must agree.

## Agents Required

- developer: yes — backend stop endpoint + registry + durable cooperative stop
  + terminal/best preservation; frontend button rewire, legacy-loop deletion,
  stop wiring, and `AutoRunBar` ownership hardening. TDD: extend
  `tests/test_auto_session.py` first.
- backend-data: yes (FastAPI endpoint, cancellation registry, durable signal,
  loop terminal logic, pytest).
- frontend-ux: yes (rewire start/stop wiring, delete in-browser loop, per-
  session ownership re-derivation; no new page).

## Frontend Present

Frontend Present: yes

## Files to Create/Modify

- `apps/backend/backend/auto_session.py` — stop endpoint; module-level
  cancellation registry (register in `create_auto_session`, remove on every
  terminal path incl. the `_runner` crash handler ~654); per-round durable
  stop-flag check in `run_auto_session`; preserve `bestIterationId` on stop.
- `apps/backend/tests/test_auto_session.py` — extend: stop→`stopped` + no
  post-stop iterations + `bestIterationId` preserved; registry populated on
  create / removed on all terminal paths; worker-safe/restart-safe stop via
  durable signal with NO live token (assert, do not skip); idempotent
  already-terminal stop; unknown id → 404; regression guards stay green
  (durable autoRun survives restart, budget hard-bounded incl. stop path,
  event-loop non-blocking, no secrets, lazy `GET /api/sessions/{id}`,
  `contracts.py` untouched).
- `apps/frontend/src/hooks/useBacktest.ts` — delete `startAutoRun` /
  `stopAutoRun` + their solely-owned state/refs; add backend
  `startAutoSession(configFromIteration)` → `POST /api/auto-sessions` and
  `stopAutoSession(sessionId)` → `POST /api/auto-sessions/{id}/stop`;
  authoritative per-session `autoRun` re-derivation on mount/switch (do NOT
  regress the J-02 lazy-detail guard / `loadingDetailIdRef` fix or the live
  poll at ~711-800 / hydration ~535).
- `apps/frontend/src/components/SessionContainer.tsx` — point both `onStartAutoRun`
  paths and `handleStartAutoRunFromCard` at the backend start; bind the stop
  button to `stopAutoSession`; ensure `AutoRunBar` (defined ~31, rendered ~248)
  re-derives this session's status on mount/switch.
- (Only if required by the rewire) `apps/frontend/src/components/BacktestConfigBar.tsx`
  / `IterationPanel.tsx` prop plumbing — surgical, no behavior change beyond
  routing start/stop to the backend.

Out of scope (do NOT modify): `shared/contracts.py`, the RestrictedPython
sandbox, the deterministic engine, `BacktestPipeline` internals, the robust
objective / best-selection algorithm, `pipeline.py` `CancellationToken`. No
new datastore/queue/scheduler. The pre-existing out-of-scope
`test_directions_cache.py` failure stays as-is (not "fixed").

## UI Evolution (Frontend Present: yes)

- New user-facing capability: "Auto Run" now launches a fully server-driven
  auto-session that survives closing/reloading the browser; the run is
  stoppable from the UI; the best strategy stays marked.
- New information displayed: a working UI **Stop** affordance on a running
  automated session, and a correct, non-stale per-session running/terminal
  status that survives reload and rapid session switching (`stopped` + stop
  reason already render via the existing `AutoRunBar`).
- New user actions: "Auto Run" → backend `POST /api/auto-sessions` (no longer
  an in-browser loop); Stop control → `POST /api/auto-sessions/{id}/stop`.
- UI surface changes: no new pages — confined to `SessionContainer.tsx`
  (start/stop wiring + `AutoRunBar` ownership) and `useBacktest.ts` (delete
  in-browser loop; backend-sourced start/stop/status).
- Navigation changes: none.

## Visual Requirements (Frontend Present: yes)

- Component patterns: reuse the existing `AutoRunBar` strip, `BacktestConfigBar`
  Auto Run / Stop controls, `Loader2` spinner, and `IterationCard` "★ Best"
  pill — no new components, no `<div>` soup.
- Layout: unchanged two-panel analytical-workstation (left chat/params,
  right equity+metrics+trades); `AutoRunBar` stays the slim strip below the
  config bar.
- Key visual effects: existing slate/primary/emerald/amber tokens and the
  established loading/terminal treatment only — no new effects (cosmetic
  redesign of `AutoRunBar` beyond the correctness/ownership fix is OUT OF SCOPE).
- States to handle: running/queued (spinner + iteration X/N), complete
  (criteria-met | budget-exhausted), **stopped** (red `StopCircle` + stop
  reason), and the no-stale-terminal correctness state under rapid session
  switching; preserve `role="status" aria-live="polite"`.

## Key Test Scenarios

- **J-10 (browser-qa):** from the UI click "Auto Run" on a completed iteration
  with a tiny budget; mid-run reload the tab and reopen the session; progress
  keeps advancing after the reload and the session reaches a terminal state
  (proves server-driven).
- **J-11 (browser-qa + API):** start a still-running run; stop via
  `POST /api/auto-sessions/{id}/stop` AND via the UI stop control; status →
  `stopped`, **no iterations appended after the stop**, best-so-far still
  marked.
- **J-02 (browser-qa, regression):** open a prior run — trades table + equity
  curve + walk-forward re-bind in the RIGHT panel, not just the left summary.
- **J-08 (browser-qa, regression):** open a freshly-started still-running
  session while switching sessions rapidly — status is "running", not a stale
  terminal; session-list spinner and `AutoRunBar` agree.
- **Backend unit/integration (must assert exact values, not skip):**
  stop→`stopped`, zero post-stop iterations, `bestIterationId` preserved (and
  a higher-raw-return WFE-failing/over-leveraged candidate still NOT best);
  registry populated on create and removed on every terminal path; worker-safe/
  restart-safe stop with NO live token honored via the durable signal;
  idempotent already-terminal stop; unknown id → 404; open-universe still 4xx.
- **Regression guards stay green:** durable `autoRun` survives restart/reload;
  budget hard-bounded with no extra round on the stop path; event-loop
  non-blocking; no secrets in artifacts; `GET /api/sessions/{id}` still lazy;
  `contracts.py` unchanged. Backend suite: only the pre-existing out-of-scope
  `test_directions_cache` failure may remain; zero new regressions.

## Notes / Risk Flags

- **Depth = full** (evaluator-mandated): run the full 11-step pipeline incl.
  audit, ux-regression, phase-closure. Frontend-loop deletion + new endpoint +
  registry + durable state + cross-boundary change with J-02/J-08 regression
  exposure.
- **Mandatory lessons (must be applied, not optional):**
  (1) iter-1 — harden `AutoRunBar`/`SessionContainer` ownership (re-derive
  per-session status authoritatively on mount/switch); a stale terminal on a
  still-running session is now a hard correctness failure once the backend is
  the single source of truth. (2) iter-0 — selecting an older run must reload
  its RIGHT analysis panel (trades + equity + WF); do not regress the J-02
  re-bind living in the exact files this iteration edits.
- **Skeptical-evaluation guidance for QA/reviewer/auditor:** do NOT accept a
  reconciled `ui-test-results.md` headline at face value — cross-check the
  post-fix source diff and the QA MODE-2 (full-mode) report (iter-1 lesson;
  the iter-1 UI-test artifact carried a stale FAIL headline reconciled by the
  auditor).
- Deleting `startAutoRun` is mandatory this iteration (anti-goal now active);
  coexistence was spec-expected only through iter-1. Verify by source diff.
- No anti-goal violation may be introduced — verify at source-diff + test
  level, not from a report headline.
