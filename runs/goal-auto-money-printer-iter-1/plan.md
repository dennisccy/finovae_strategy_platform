# goal-auto-money-printer-iter-1 Execution Plan

Layer-1 Foundation of Key Capability #11 (headless auto-session): J-07 (start
via API) + J-08 (track live in UI) + J-09 (terminal stop + best marked), plus
the lesson-mandated J-02 right-panel re-bind fix. Faithful to docs/goal.md; no
goal drift. J-10–J-16 explicitly deferred (out of scope, do not implement).

## What to Build

- **`apps/backend/backend/auto_session.py`** — server-side auto-session
  controller. Reuses `BacktestPipeline` (`pipeline.py`): `run()` →
  `(BacktestResult, StrategySpec, errors, StrategyRating)`, then
  `generate_insights()`, optionally `execute_walk_forward()`. NO
  compile/codegen/sandbox/fetch/engine reimplementation, NO sandbox/engine
  bypass. New DTOs live here — do NOT touch frozen `shared/contracts.py`.
- **`POST /api/auto-sessions`** endpoint (new `APIRouter` mounted in `api.py`
  via `app.include_router`, same pattern as `session_router`). Body: all
  search-space fields optional but this iter only needs the pinned path —
  `natural_language`, `symbol`, `timeframe`, `start_date`, `end_date`,
  `initial_capital`, `model`, robust `targets` (`min_wfe`, `min_trades`,
  `min_sharpe`/`min_return`), `budget` (`max_iterations` required-or-safe-
  defaulted, optional `max_wall_clock_seconds`). Response: HTTP 200
  `{ "sessionId": "...", "status": "running"|"queued" }`. Missing required
  pinned fields → 4xx with a clear message (never a 500); `max_iterations`
  ≤ 0 / absent → rejected or defaulted to a small safe cap (never unbounded).
- **Session creation in the existing file store** via `session_store.py`
  (`write_session_meta` to create `session.json` with `name` +
  `lastAccessedAt` + `autoRun` block synchronously BEFORE returning 200 so the
  sessionId appears immediately in `GET /api/sessions` —
  `derive_session_tabs` keys off `session.json`). No parallel store, no schema
  fork, no new datastore/queue/DB.
- **Background loop** launched with `asyncio.create_task(...)` (same pattern as
  `api.py:647` `task = asyncio.create_task(run())`). Acquire
  `app.state.backtest_semaphore` (`asyncio.Semaphore(1)`, set at
  `api.py:1120`) around each backtest; never block the event loop —
  `GET /api/sessions` stays responsive during a run. Plumb a
  `CancellationToken` (`pipeline.py:45`) through the loop for cooperative
  stop and a `stopped`-capable state machine (the public stop *endpoint* is
  J-11/iter-2 — out of scope).
- **Per-iteration artifacts** written via `write_iteration(session_id, idx,
  node_dict)` in the exact node_dict shape a manual run produces (see
  `api.py:597-615` directions-cache node_dict for the canonical key set:
  `id`, `prompt`, `scriptCode`, `strategyName`, `status`, `result`, `rating`,
  `insights`, `params`, `timestamp`, `parentId`). Serialize results with the
  existing helpers (`BacktestResultSchema`, `_serialize_rating`,
  `_serialize_walk_forward` in `api.py`). Append progress via
  `append_activity_entries(...)`. A headless run MUST be indistinguishable in
  the UI from a manual one.
- **Persisted `autoRun` status** merged into `session.json` via
  `write_session_meta` (read-update-write) after every iteration and every
  state transition: `{ status: queued|running|complete|stopped, stopReason:
  criteria-met|budget-exhausted|null, currentIteration, maxIterations,
  bestIterationId, startedAt, updatedAt }`. Durable file store only — never an
  in-process-only dict / browser memory (survives worker restart + reload).
- **Hard budget**: loop terminates the moment EITHER all supplied `targets`
  are met (`stopReason="criteria-met"`) OR `max_iterations` reached /
  `max_wall_clock_seconds` elapsed (`stopReason="budget-exhausted"`). MUST NOT
  take "one more round" past the cap. (Token/USD cost-tracker = J-13, OUT OF
  SCOPE — but iteration + wall-clock caps now must make an unbounded loop
  impossible.)
- **Robust objective selector** (function in `auto_session.py` or
  `apps/backend/backend/robust_objective.py`): single scalar gating on
  walk-forward WFE ≥ threshold + min-trades floor, drawdown/over-leverage
  penalized. `bestIterationId` selected by this objective, NOT raw return.
- **A loop-iteration LLM/backtest failure** is recorded as a failed iteration;
  the loop still reaches a terminal state (never hangs). API keys/secrets MUST
  NOT be written into `activity.jsonl` or any session artifact.
- **Frontend — `GET /api/sessions/{id}` must surface `autoRun`.** Today
  `get_session` (`session_routes.py:142`) returns only `backtestParams` +
  `selectedIterationId` from meta. Add the small `autoRun` status block to its
  response (it is the tiny status object in `session.json`, NOT per-iteration
  `result.json`/`rating.json` — this stays compliant with the lazy-load
  anti-goal). Surface it in `sessionApi.ts` `loadSession`.
- **Frontend — live tracking (J-08):** lightweight polling of
  `GET /api/sessions/{id}` (+ iterations list) while `autoRun.status` is
  `running`/`queued`; stop polling at terminal. Reuse existing fetch paths
  (`sessionApi.ts`, `SessionContainer.tsx`/`useBacktest.ts`). Surface a
  run-status indicator (running → terminal), the terminal `stopReason`, and a
  best-iteration badge/marker. No manual page reload required.
- **Frontend — J-02 fix:** selecting a prior run must re-bind the RIGHT
  analysis panel (trades table + equity curve + WF), not just the LEFT
  conversation panel. Root cause is in the lazy-detail path: `selectIteration`
  → `selectedIterationId` → `loadIterationDetail` effect
  (`useBacktest.ts:1505-1571`); `IterationPanel.tsx:182-248` renders detail
  only when `selected.result` is present. Verify the prior run's *trades
  table actually reloads* (not just its summary). Do NOT regress the existing
  manual-history path.

## Agents Required

- **developer: yes** — single developer agent does both backend + frontend
  (TDD: write the backend pytest cases first, then implement).
- backend-data: yes — new auto-session controller, endpoint, robust objective,
  durable status, file-store integration.
- frontend-ux: yes — live polling/status indicator, best marker, terminal stop
  reason, J-02 right-panel re-bind fix.

## Frontend Present: yes

## Files to Create/Modify

- `apps/backend/backend/auto_session.py` — **CREATE**: controller, request/
  response DTOs, background loop, budget + state machine, activity emission.
- `apps/backend/backend/robust_objective.py` — **CREATE** (or a function in
  auto_session.py): WFE-gated, min-trades-floored, drawdown-penalized scalar +
  `select_best`.
- `apps/backend/backend/api.py` — **MODIFY**: mount the new auto-sessions
  router (`app.include_router(...)` near `api.py:125`).
- `apps/backend/backend/session_routes.py` — **MODIFY**: include the `autoRun`
  block from `session.json` meta in the `GET /{session_id}` response (small
  status object only — keep the lazy-load anti-goal intact).
- `apps/backend/tests/test_auto_session.py` — **CREATE**: new pytest module
  (mock/stub LLM + Binance for determinism).
- `apps/frontend/src/lib/sessionApi.ts` — **MODIFY**: expose `autoRun` from
  `loadSession`; helper for the iterations-list refetch if needed.
- `apps/frontend/src/hooks/useBacktest.ts` — **MODIFY**: live polling while
  `autoRun` running/queued; surface status/stopReason/bestIterationId;
  J-02 right-panel re-bind fix.
- `apps/frontend/src/components/SessionContainer.tsx` — **MODIFY**: run-status
  indicator wiring; ensure selection re-binds the right panel.
- `apps/frontend/src/components/IterationPanel.tsx` — **MODIFY**: best-
  iteration badge/marker; confirm detail view re-binds on selection.
- `docs/handoffs/goal-auto-money-printer-iter-1-dev.md` — **CREATE**: handoff.

**Guardrails (do NOT touch / do NOT do):** `shared/contracts.py` (frozen);
the legacy in-browser loop `useBacktest.ts` `startAutoRun` ~line 2045 (J-10,
iter-2 — coexistence is expected, not a violation); sandbox, deterministic
engine, Parquet cache layer, `BACKTEST_STORE_DIR` resolution; the public
`POST /api/auto-sessions/{id}/stop` endpoint (J-11, iter-2 — plumb the token
only); J-12–J-16 optimizer (open-universe, cost tracker, SCREEN→PROMOTE,
history warm-start). Do NOT "fix" the pre-existing
`test_directions_cache.py::test_write_and_read_full_round_trip` failure
(nice-to-have, out of scope; it may remain the single failing test).

## UI Evolution

- **New user-facing capability:** start a fully automated, server-side
  strategy-search session with one API call (no browser needed to start/drive
  it) and watch it progress live to a best strategy in the existing UI;
  separately, opening any prior run from history now reloads its full detail.
- **New information displayed:** a session tab for the headless run appearing
  immediately; a live run-status indicator (running → terminal) advancing with
  no page reload; a terminal stop reason (`criteria-met`/`budget-exhausted`)
  and a best-iteration marker; for J-02, the selected historical run's full
  trades table + equity curve + walk-forward panel.
- **New user actions:** `POST /api/auto-sessions` (headless; primary new
  action). No new UI button this iter (rewire = J-10/iter-2).
- **UI surface changes:** session list / `SessionContainer` (live status +
  best marker); right-hand analysis panel correctly re-binds on history
  selection. No new page — rides the existing two-panel workstation layout.
- **Navigation changes:** none.

## Visual Requirements

- **Component patterns:** reuse existing components — session tabs, activity
  log, `IterationPanel`/`IterationCard`/`IterationDetailView`. Best marker =
  a small badge on the iteration card consistent with existing card styling.
- **Layout:** unchanged two-panel workstation (left = activity/chat, right =
  iteration history + detail/analysis).
- **Key visual effects:** match the existing analytical-workstation style
  (dense, light/slate palette already in use — `slate-*`, `primary-*`
  tokens); no new effects invented.
- **States to handle:** running indicator (animated, e.g. existing
  `Loader2` spinner pattern); terminal states (complete/stopped) clearly
  distinct; stop-reason label; detail-pane loading/error/no-detail states
  already exist in `IterationPanel` — reuse them for the re-bind fix.

## Key Test Scenarios

Backend pytest (`cd apps/backend && .venv/bin/python -m pytest tests/ -v`;
mock LLM + Binance). Baseline: 124 passed / 1 pre-existing directions-cache
failure — nothing else may newly fail.

- (a) `POST /api/auto-sessions` (pinned config) → 200 + `sessionId`; the
  session is then listed by `GET /api/sessions`.
- (b) loop terminates exactly on `max_iterations` (NO extra iteration past
  the cap) with `stopReason="budget-exhausted"`.
- (c) loop terminates with `stopReason="criteria-met"` when lenient targets
  are satisfied.
- (d) `bestIterationId` chosen by the robust objective, NOT raw return: a
  higher-raw-return but WFE-failing / over-leveraged candidate is NOT
  selected.
- (e) `autoRun` status persisted into `session.json`; a fresh store read
  reflects the last state (restart-survival proxy).
- (f) iteration artifacts written are the same shape `write_iteration`
  produces for a manual run.
- Error cases: missing required pinned fields → 4xx (not 500);
  `max_iterations` ≤ 0 / absent → rejected or safe-defaulted (never
  unbounded); an LLM/backtest failure inside one iteration → recorded as a
  failed iteration, loop still reaches a terminal state (no hang); secrets
  never appear in `activity.jsonl` / session artifacts; event loop stays
  responsive (semaphore respected).

Browser-QA (tiny budgets only: ≤ 2 screen iterations, short date range,
cheapest model, lenient targets):

- **J-07:** API trigger → 200 + sessionId + running/queued; `GET /api/sessions`
  shows the same sessionId with no browser interaction to start it.
- **J-08:** open the created session in the UI; observe (no manual reload) a
  "running" indicator → ≥ 1 iteration with a backtest result + suggestions →
  terminal state.
- **J-09:** lenient targets + small budget; wait for terminal; visible stop
  reason + best iteration marked; if `criteria-met`, the best iteration's
  metrics satisfy every supplied target.
- **J-02:** complete ≥ 1 backtest, open a prior run from history; assert the
  RIGHT analysis panel (trades table + equity curve + WF) reloads to the
  selected run — not only the left conversation panel.
- **Regression smoke:** J-01, J-03, J-04, J-05, J-06 remain green; the legacy
  in-browser auto-run is not broken.

## Assumptions / Notes

- Coexisting loops (new backend loop + legacy in-browser `startAutoRun`) is
  expected this iter, NOT an anti-goal violation (rewire is J-10/iter-2).
- Token/USD cost accounting is J-13 (deferred); iter-1 satisfies the *core*
  unbounded-loop anti-goal via hard `max_iterations` + `max_wall_clock_seconds`
  caps only.
- The robust selector must *exist and gate* now (WFE/min-trades/drawdown);
  deep overfit-gating stress verification is J-16 (later).
- Depth = full (net-new backend+frontend, durable artifacts, dense
  security/correctness anti-goals): run the full 11-step pipeline incl. audit
  + ux-regression + closure gate.
- The single most non-obvious integration point: `GET /api/sessions/{id}`
  must be extended to return the `autoRun` block (currently it does not) —
  without that, J-08 live tracking and J-09 "open the session in the UI"
  cannot work, and this stays anti-goal-compliant because `autoRun` is a small
  status object in `session.json`, not per-iteration `result/rating` payloads.
</content>
</invoke>
