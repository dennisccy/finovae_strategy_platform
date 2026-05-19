# Goal Iteration 1 — Headless auto-session Foundation: start via API, runs server-side, tracks live, stops with a best marked

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** auto-money-printer
- **Iteration:** 1
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes
- **Target journeys:** J-07, J-08, J-09, J-02
- **Required-still-passing journeys:** J-01, J-03, J-04, J-05, J-06
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - "The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one."
  - "The automated-session `autoRun` status MUST be persisted to the durable store and survive a worker restart and a browser reload; it MUST NOT live only in browser memory or a non-persisted in-process variable."
  - "Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take \"one more round\" past the cap, even if targets are never met."
  - "The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine."
  - "The automated \"best\" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best."
  - "The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected)."
  - "No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store."
  - "API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts."
  - "`GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint."
  - "`BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart."
  - "No relational database or SQLite is introduced for OHLCV, session, or directions storage (Parquet + durable file store only)."
  - "The frozen dataclasses in `shared/contracts.py` must not be mutated in place."

## GOAL

A user (or a script) makes one `POST /api/auto-sessions` call with a pinned
config and a tiny budget; the platform runs the generate→backtest→insights→iterate
loop entirely server-side, the new session appears immediately in the existing
UI session list and updates live without a manual page reload, and the run
reaches a terminal state with a visible stop reason and a best iteration marked
by a robust objective.

## BACKGROUND

Iter-0 (baseline) confirmed the core platform (J-01/03/04/05/06) already passes
and that the entire Key Capability #11 headless auto-session layer (J-07–J-16)
is unimplemented: `POST /api/auto-sessions` → 404, no backend module, the only
automation being the legacy **in-browser** iterate loop in
`apps/frontend/src/hooks/useBacktest.ts` (`startAutoRun`, ~line 2045). The
evaluator recommended building **Layer-1 Foundation first** at **full** depth.

This iteration delivers the indivisible Foundation vertical slice — J-07 (start
via API), J-08 (track live in UI), J-09 (terminal stop + best marked) — because
none of the three can be meaningfully verified without the other two (a session
that appears but never runs, or runs but never terminates with a best, is not a
capability). J-10 (rewire the in-browser button + prove backend-only by
surviving a mid-run reload) and J-11 (stop endpoint/control) are deliberately
deferred to iter-2: J-10 is a frontend-heavy structural rewire and J-11 is an
isolated endpoint, both separable hardening. The Optimizer (J-12–J-16) is
deferred to later iterations per the goal's layering.

J-02 (partial) is folded in as a small, explicitly-recommended cheap win:
selecting a prior run reloads the LEFT conversation panel but the RIGHT analysis
panel (trades table + equity curve + WF) never re-binds. The developer is
already inside the exact files this bug lives in (`SessionContainer.tsx` /
`IterationPanel.tsx` / `useBacktest.ts`) to build J-08's live tracking, so
fixing it here is efficient and **lesson-mandated** (see NOTES).

## IN SCOPE

### Backend

- [ ] New module `apps/backend/backend/auto_session.py` containing the
      server-side auto-session controller. It MUST reuse the existing
      `BacktestPipeline` from `apps/backend/backend/pipeline.py`
      (`run()`, `generate_insights()`, `execute_walk_forward()`) — no
      reimplementation of compile/codegen/sandbox/fetch/backtest, no sandbox or
      engine bypass.
- [ ] New endpoint `POST /api/auto-sessions` (add to `apps/backend/backend/api.py`
      or a new router mounted in `api.py`). Request body fields, **all
      search-space fields optional** (a provided field pins that dimension; this
      iteration only needs the pinned path — open-universe is J-12, out of
      scope): `natural_language`, `symbol`, `timeframe`, `start_date`,
      `end_date`, `initial_capital`, `model`, robust `targets`
      (e.g. `min_wfe`, `min_trades`, `min_sharpe`/`min_return`), and a `budget`
      object accepting at minimum `max_iterations` and an optional
      `max_wall_clock_seconds`. Response: HTTP 200 with `{ "sessionId": "...",
      "status": "running" | "queued" }`.
- [ ] The endpoint creates the session in the **existing file store** via
      `apps/backend/backend/session_store.py` (`write_session_meta`,
      `write_iteration`, `append_activity_entries`) under `BASE_DIR`
      (`BACKTEST_STORE_DIR` env or the durable default
      `…/.data/backtests` — never `/tmp`). NO parallel store, NO new schema,
      NO new datastore/queue/DB. The created `sessionId` MUST be returned by
      `GET /api/sessions` (router prefix `/api/sessions`, `list_session_tabs`)
      and openable via `GET /api/sessions/{id}` **without** that path eagerly
      parsing per-iteration `result.json`/`rating.json` (anti-goal).
- [ ] Server-side background loop launched with `asyncio.create_task(...)`
      (same pattern as the existing `asyncio.create_task(run())` calls in
      `api.py`). It MUST acquire the existing `app.state.backtest_semaphore`
      (`asyncio.Semaphore(1)`) around each backtest and MUST NOT block the API
      event loop — `GET /api/sessions` and other requests stay responsive while
      a run is active. Reuse the existing `CancellationToken`
      (`apps/backend/backend/pipeline.py:45`) to make the loop cooperatively
      stoppable (the stop *endpoint* itself is J-11/iter-2, but the token plumb
      and a terminal `stopped`-capable state machine land here).
- [ ] Each loop iteration writes a standard iteration record via
      `write_iteration(...)` (the same `meta.json` / `strategy.py` /
      `insights.json` / `timeframes/{tf}/result.json` + `rating.json` layout a
      manual run produces) and appends activity entries via
      `append_activity_entries(...)`, so a headless run is **indistinguishable
      in the UI from a manual one**.
- [ ] Persisted `autoRun` status block merged into `session.json` via
      `write_session_meta(...)` (read-update-write) after every iteration and on
      every state transition: at least `{ status: queued|running|complete|
      stopped, stopReason: criteria-met|budget-exhausted|null, currentIteration,
      maxIterations, bestIterationId, startedAt, updatedAt }`. This status MUST
      live in the durable file store (NOT only in an in-process dict / browser
      memory) so it survives a worker restart and a browser reload.
- [ ] Hard budget enforcement sufficient for J-09: the loop terminates the
      moment EITHER (a) all supplied robust `targets` are satisfied
      (`stopReason = "criteria-met"`) OR (b) `budget.max_iterations` is reached
      or `max_wall_clock_seconds` elapses (`stopReason = "budget-exhausted"`).
      The loop MUST NOT take "one more round" past the cap even if targets are
      never met. (Full immutable AI-token/USD cost-tracker accounting is the
      explicit J-13 target and is OUT OF SCOPE here — but the
      iteration-count + wall-clock caps implemented now MUST already make an
      unbounded loop impossible.)
- [ ] Robust objective module (e.g. `apps/backend/backend/robust_objective.py`
      or a function in `auto_session.py`): a single scalar that gates on
      walk-forward WFE ≥ threshold and a min-trades floor and penalizes
      drawdown / over-leverage. `bestIterationId` MUST be selected by this
      objective, NOT by raw return. (Deep overfit-gating verification is J-16,
      later — but the selector must exist now so J-09's "best marked" /
      "criteria-met" semantics are real.)
- [ ] New DTOs/types go in the new auto-session module — do NOT add to or
      mutate the FROZEN `apps/backend/shared/contracts.py`.
- [ ] API keys / secrets MUST NOT be written into `activity.jsonl` or any
      session artifact.

### Frontend

- [ ] The existing UI session list must surface the headless session and a
      run-status indicator ("running" → terminal) and refresh the open
      auto-session **without a manual page reload** (lightweight polling of
      `GET /api/sessions/{id}` / the iterations list while the session's
      `autoRun.status` is `running`/`queued`; stop polling at terminal). Reuse
      the existing session/iteration fetch paths
      (`apps/frontend/src/lib/sessionApi.ts`, `SessionContainer.tsx`).
- [ ] Render the terminal `stopReason` and the marked best iteration in the
      session view (a badge/marker on the best iteration card is sufficient).
- [ ] **J-02 fix:** selecting a prior run from history must re-bind the RIGHT
      analysis panel — the trades table, equity curve, and walk-forward view
      must reload to the selected run, not stay pinned to the latest run. Fix
      in `SessionContainer.tsx` / `IterationPanel.tsx` / `useBacktest.ts`.

### New user-facing capability

Start a fully automated, server-side strategy-search session with a single API
call (no browser needed to start or drive it) and watch it progress live and
finish with a best strategy in the existing UI. Separately, opening any prior
run from history now correctly reloads its full detail (trades + equity + WF),
not just its summary.

### New information displayed

- A new session tab/entry for the headless run, appearing immediately.
- A live run-status indicator (running → complete) that advances without a
  page reload.
- A terminal stop reason (`criteria-met` / `budget-exhausted`) and a best
  iteration marker.
- For J-02: the selected historical run's full trades table + equity curve +
  walk-forward panel.

### New user actions

- `POST /api/auto-sessions` (headless; primary new action this iteration).
- (UI button rewire and an explicit Stop control are J-10/J-11 — iter-2.)

### UI surface changes

Session list / `SessionContainer` (live-updating status + best marker); the
right-hand analysis panel now correctly re-binds on history selection. No new
page; this rides the existing two-panel workstation layout.

### Product surface delta

The product gains a headless automation entry point: the iterate loop becomes a
real backend capability observable in the existing UI, instead of a
browser-only loop. History browsing becomes trustworthy (full detail reloads).

## OUT OF SCOPE

- **J-10:** rewiring the UI "Auto Run" button to the backend and deleting the
  in-browser loop (`useBacktest.ts` `startAutoRun`). The legacy in-browser loop
  is **left untouched and functional** this iteration; the new backend loop is
  built alongside it. (This intermediate coexistence is NOT an anti-goal
  violation — the "loop only in backend after the rewire" anti-goal is
  conditional on the rewire, which is iter-2. See NOTES.)
- **J-11:** the `POST /api/auto-sessions/{sessionId}/stop` endpoint and UI stop
  control (the cancellation *token* is plumbed now; the public stop path is
  iter-2).
- **J-12–J-16 (Optimizer):** open-universe search, the immutable AI-token/USD
  cost tracker, staged SCREEN→PROMOTE, global-history warm-start +
  `history_scope`, and deep robust-objective overfit-gating verification. Only
  the **pinned-config** path and iteration/wall-clock caps are in scope here.
- Any change to `shared/contracts.py`, the sandbox, the deterministic engine,
  the Parquet cache layer, or `BACKTEST_STORE_DIR` resolution.
- The pre-existing nice-to-have failure
  `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  (Key Capability #10, not a Must-have journey).

## DEFINITION OF DONE

- [ ] Target journeys **J-07, J-08, J-09, J-02** pass via browser-qa-agent
      (J-07 also verifiable via direct API: `POST /api/auto-sessions` → 200 +
      `sessionId`, then `GET /api/sessions` lists it).
- [ ] Required-still-passing journeys **J-01, J-03, J-04, J-05, J-06** remain
      green (manual backtest, walk-forward, AI insights, reference data,
      warm-cache re-run all still work; the legacy in-browser auto-run is not
      broken).
- [ ] No anti-goal violation introduced (see Goal Mode Metadata list; verify
      especially: same file store / no schema fork, persisted durable status,
      hard caps make unbounded loop impossible, `BacktestPipeline` reused,
      best-by-robust-objective, event loop not blocked, no secrets in
      artifacts, `contracts.py` untouched, no new infra/DB).
- [ ] Backend unit/integration tests for the new auto-session module pass; no
      regression in the existing suite (baseline: 124 passed / 1 pre-existing
      unrelated directions-cache failure — that 1 may remain failing, nothing
      else may newly fail).
- [ ] Dev handoff written at
      `docs/handoffs/goal-auto-money-printer-iter-1-dev.md`.

## TESTING REQUIREMENTS

- **Browser (browser-qa-agent), tiny budgets only** (per goal.md: ≤ 2 screen
  iterations, short date range, cheapest model, lenient targets):
  - **J-07:** `POST /api/auto-sessions` with a pinned config —
    `natural_language`, `symbol: "BTCUSDT"`, `timeframe: "1h"`, a short
    `start_date`/`end_date` range, `initial_capital`, cheapest `model`, lenient
    `targets`, `budget: { "max_iterations": 2 }` → assert HTTP 200 +
    `sessionId` + state `running`/`queued`; immediately `GET /api/sessions`
    shows the same `sessionId` (new tab in the UI) with no browser interaction
    needed to start it.
  - **J-08:** trigger as J-07, open the created session in the UI, observe
    (without manual reload) a "running" indicator, ≥ 1 iteration with a
    backtest result + generated suggestions, then a terminal state.
  - **J-09:** trigger with lenient `targets` + small `budget`; wait for
    terminal; assert a terminal status with a visible stop reason
    (`criteria-met` or `budget-exhausted`) and a best iteration marked; if
    `criteria-met`, the best iteration's metrics satisfy every supplied target.
  - **J-02:** complete ≥ 1 backtest, open a prior run from history; assert the
    RIGHT analysis panel (trades table + equity curve + WF) reloads to the
    selected run — not only the left conversation panel.
  - Re-verify **J-01, J-03, J-04, J-05, J-06** (regression smoke).
- **Unit/integration (backend, pytest):** run
  `cd apps/backend && .venv/bin/python -m pytest tests/ -v` (asyncio_mode=auto,
  `testpaths=["tests"]`). New tests required for: (a) `POST /api/auto-sessions`
  returns 200 + `sessionId` and the session is listed by `GET /api/sessions`;
  (b) the loop terminates on `max_iterations` (no extra iteration past the cap)
  with `stopReason = "budget-exhausted"`; (c) terminates with
  `stopReason = "criteria-met"` when lenient targets are satisfied;
  (d) `bestIterationId` is chosen by the robust objective, not raw return
  (a higher-raw-return but WFE-failing / over-leveraged candidate is NOT
  selected); (e) `autoRun` status is persisted into `session.json` and a fresh
  read of the store reflects the last state (restart-survival proxy);
  (f) iteration artifacts written are the same shape `write_iteration`
  produces for a manual run. Mock/stub the LLM + Binance layers in unit tests
  for determinism and cost; the browser-qa run exercises the live path under a
  tiny budget.
- **Error cases that must be rejected/handled:** missing required pinned fields
  → 4xx with a clear message (not a 500); `max_iterations` ≤ 0 or absent →
  rejected or defaulted to a safe small cap (never unbounded); an LLM/backtest
  failure inside one loop iteration is recorded as a failed iteration and the
  loop still reaches a terminal state (does not hang); secrets never appear in
  `activity.jsonl` or session artifacts.

## NOTES

- **Scope discipline / anti-goal nuance — coexisting loops is expected, not a
  violation.** This iteration builds the new backend loop *alongside* the
  legacy in-browser loop in `useBacktest.ts` (`startAutoRun`, ~line 2045). The
  anti-goal *"After the rewire, the iterate loop MUST exist only in the backend;
  the frontend MUST NOT run a second in-browser iterate loop"* is **conditional
  on the rewire**, which is J-10/iter-2. Iter-0's evaluator explicitly
  classified the in-browser loop as "the pre-rewire state J-10 must replace —
  flagged as J-10 failing, not a violation." Developer: do NOT touch / delete
  the in-browser loop this iteration (that is scope creep into J-10).
  Evaluator: do NOT score the coexistence as a regression/anti-goal breach.
- **Lesson applied (lessons.md iter-0, "Applies to: any iter touching
  session/run-history selection or the right-hand analysis panel … also the
  build iters for J-07–J-16, which must not regress this existing
  manual-history path").** J-02 is *partial*, not passing: the LEFT panel
  updates on history selection but the RIGHT panel (trades table) does not
  re-bind — this is easy to misread as "history works." Verification MUST
  confirm the selected prior run's **trades table actually reloads**, not just
  its summary. Because J-08's live tracking touches the same components, the
  developer must both fix J-02 and not regress the existing manual-history
  path.
- **Persistence is foundational, not bolt-on.** The `autoRun` status anti-goal
  applies to the *new* backend session from this iteration: status must be
  flushed to `session.json` via `write_session_meta` after every iteration and
  transition. J-08 ("no manual reload") and J-09 ("open the session in the UI")
  only work because the UI reads the durable store; an in-process-only status
  dict fails both the journey and the anti-goal.
- **Budget layering (avoid a false anti-goal fail).** The hard-budget anti-goal
  enumerates "AI tokens/USD AND max-configs AND wall-clock … immutable cost
  tracker." Full token/USD accounting is the **explicit J-13 journey**
  (deferred). Iter-1 satisfies the *core* of that anti-goal — "MUST NOT loop
  unbounded or take one more round past the cap" — via hard `max_iterations`
  and `max_wall_clock_seconds` caps. The evaluator should treat token/USD
  accounting as not-yet-in-scope (J-13), while still requiring that the loop is
  provably bounded now.
- **Robust objective now vs. J-16.** A WFE-gated, min-trades-floored,
  drawdown-penalized scalar selector must exist this iteration for J-09's
  "best marked" / "criteria-met" semantics to be real; J-16 later stress-tests
  that it actually rejects a high-raw-return overfit candidate. Implement the
  selector now; the deep overfit-gating verification is a later journey.
- **Reuse, don't fork.** `BacktestPipeline.run()` →
  `(BacktestResult, StrategySpec, errors, StrategyRating)`, plus
  `generate_insights()` / `execute_walk_forward()`; `CancellationToken` at
  `pipeline.py:45`; background pattern `asyncio.create_task(run())` and
  `app.state.backtest_semaphore` in `api.py`; store writers in
  `session_store.py` (`write_session_meta`, `write_iteration`,
  `append_activity_entries`). No new infra, no DB/SQLite, no schema fork,
  `contracts.py` frozen.
- Depth is **full** per the iter-0 evaluator recommendation and the
  depth-picking rule (net-new code crossing backend+frontend, writes durable
  artifacts, dense with security/correctness anti-goals): run the full 11-step
  pipeline including audit + ux-regression + closure gate.
