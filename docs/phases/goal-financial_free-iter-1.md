# Goal Iteration 1 — Headless auto-session loop: start endpoint + terminal/best-marking (Layer-1 core)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** financial_free
- **Iteration:** 1
- **Mode:** normal
- **Depth:** full
- **Frontend Present:** no
- **Target journeys:** J-07, J-09
- **Required-still-passing journeys:** J-01, J-02, J-03, J-04, J-05, J-06
- **Anti-goal reminders** (verbatim from `docs/goal.md`; full list there — these are the set this iteration must actively respect):
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - The automated-session `autoRun` status MUST be persisted to the durable store and survive a worker restart and a browser reload; it MUST NOT live only in browser memory or a non-persisted in-process variable.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.
  - After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST NOT run a second in-browser iterate loop. *(The rewire is J-10/iter-2; iter-1 intentionally leaves the in-browser Auto Run in place as a transitional duplicate — see NOTES.)*
  - Always-on invariants that must not regress: No lookahead; no nondeterministic backtests (seeded slippage); the sandbox blocks file I/O, network, `exec`/`eval`, `__import__`, `open`, `os`; the frozen dataclasses in `shared/contracts.py` must not be mutated in place; OHLCV cached as a single Parquet file per (symbol, timeframe) with no re-fetch when a covering cache exists; `BACKTEST_STORE_DIR` MUST NOT default to a volatile `/tmp` path; no relational DB/SQLite; no hard-coded credentials/keys in source.

## GOAL

A single API call — `POST /api/auto-sessions` with a pinned config and a tiny budget — starts a server-side automated strategy session that reuses the existing `BacktestPipeline`, writes standard session/iteration/activity/suggestion artifacts to the existing file store, runs to a terminal state (robust targets met → `criteria-met`, else hard budget exhausted → `budget-exhausted`), marks a best iteration by a WFE-gated robust objective, and exposes a durable `autoRun` status block on the existing session record — all with no browser involvement.

## BACKGROUND

Baseline (iter-0) confirmed the six manual journeys J-01…J-06 already pass and the entire automated surface (J-07…J-16) fails-by-absence — `POST /api/auto-sessions` returns 404 and no auto/optimizer routes exist. The evaluator recommended building **Layer-1 Foundation** at full depth, starting with the backend auto-session loop and its start endpoint, reusing `BacktestPipeline` (no sandbox/engine bypass) and writing the same artifacts the UI renders. Per the goal-decomposer's "1–3 journeys per iteration" rule and to keep verification fully API-grounded (the headless Chrome-MCP tab is render-throttled — see NOTES), this iteration delivers the **backend loop core (J-07 start + J-09 terminal/best-marking)**. The frontend-coupled Layer-1 journeys (J-08 live tracking, J-10 in-browser rewire + reload survival, J-11 UI stop control) are deferred to iter-2; the open-universe optimizer (J-12…J-16) follows.

Architecture facts established by codebase inspection (use them; do not re-discover):
- `BacktestPipeline` (`apps/backend/backend/pipeline.py`) already exposes `generate_strategy`, `execute_backtest`, `generate_insights`, and `execute_walk_forward` — the loop composes these. It owns the sandbox + deterministic engine.
- The manual backtest path does **not** persist to the store server-side — the browser writes iterations/activity via the `session_routes.py` endpoints. The headless loop therefore MUST persist server-side by calling `session_store.py` directly (`write_session_meta`, `write_iteration`, `append_activity_entries`) so a headless run produces the identical on-disk shape a manual run does.
- `session_store.write_session_meta` merges arbitrary keys into `live/{sessionId}/session.json` — the durable home for the `autoRun` block (no schema fork, no new store).
- The in-browser loop in `apps/frontend/src/hooks/useBacktest.ts` (`startAutoRun`/`stopAutoRun`, ~lines 2047–2259) is the reference behavior to **port** to the backend (seed baseline → score untried suggestions → keep best → regenerate insights → repeat under a cap), including its WFE accept-gate and min-trades floor. Port it; do not reinvent the scoring.

## IN SCOPE

### Backend
- [ ] New module `apps/backend/backend/auto_session.py` housing:
  - [ ] An `AutoSessionController` (or equivalent) that runs the headless loop as an awaitable background task and **reuses `BacktestPipeline`** for every LLM/backtest/walk-forward step (no direct sandbox/engine calls, no bypass).
  - [ ] An **immutable budget tracker** value object holding `{ iterationsDone, maxIterations, wallClockSec, maxWallClockSec, tokens, usd }`. `iterations` and `wall-clock` are **hard-enforced**: the loop checks `tracker.exceeded()` *before* starting each round and stops immediately if any enforced cap is reached — it never starts "one more round" past the cap. Token/USD counters are populated best-effort (their hard cap is J-13/Layer-2).
  - [ ] A **robust scorer** that selects the single best iteration: WFE-gated (reject candidates with WFE below the accept threshold — reuse the existing 0.3 threshold from the in-browser loop), min-trades floor (zero/under-floor trades are ineligible), drawdown-penalized. This is the canonical "best" definition (registered in the blueprint Data Contract).
  - [ ] A `targets`-satisfaction predicate: given the supplied robust `targets` (all fields optional), return whether the current best iteration satisfies **every** supplied target.
- [ ] The headless loop behavior:
  - [ ] Step 0 — create the **baseline iteration**: `generate_strategy` from the NL prompt → `execute_backtest` → rating → `generate_insights`. Persist it as iteration 1 via `session_store.write_iteration` and append activity entries.
  - [ ] Iterate up to `budget.max_iterations` rounds: take untried suggestions from the current baseline, generate+backtest (and run walk-forward to obtain WFE for the gate), persist each candidate iteration, score, keep/mark the best, regenerate insights on the new baseline. Mirror the in-browser accept logic.
  - [ ] Terminal conditions (checked each round, in priority order): (a) supplied `targets` all satisfied by best → `criteria-met`; (b) hard budget (`max_iterations` or `max_wall_clock_sec`) reached → `budget-exhausted`; (c) a persisted stop request → `stopped`; (d) no remaining suggestions → `budget-exhausted` (documented). On any terminal transition, write the final `autoRun` status + `bestIterationId` and stop appending iterations.
  - [ ] Maintain `autoRun.bestIterationId` throughout (best-so-far always marked).
- [ ] New route module `apps/backend/backend/auto_session_routes.py` (mounted in `api.py` via `include_router`, mirroring `session_routes.py`):
  - [ ] `POST /api/auto-sessions` — validate the pinned request; **create the live session in the store first** (write `session.json` with name + `backtestParams` + initial `autoRun` block so it appears immediately in `GET /api/sessions`), then launch the loop as a non-blocking background task (`asyncio.create_task` or equivalent registry), then return **HTTP 200** with `{ sessionId, status: "running" | "queued", autoRun: {…} }`. Each backtest inside the loop MUST acquire the existing `app.state.backtest_semaphore` (Semaphore(1)) so the one-backtest-per-worker rule holds and the event loop stays responsive.
  - [ ] `POST /api/auto-sessions/{sessionId}/stop` — flip a persisted `stopRequested` flag on the `autoRun` block; the loop honors it at its next checkpoint and transitions to `stopped`. Returns 200. *(Built as cancellation infrastructure the loop needs anyway; the full J-11 journey — UI stop control + reload survival — is claimed in iter-2.)*
- [ ] Pinned-config request schema (Pydantic): `natural_language`, `symbol`, `timeframe`, `start_date`, `end_date`, `initial_capital`, optional `leverage`/`allow_short`, optional `model` (default `DEFAULT_MODEL` from `shared/model_catalog.py`), optional `objective` (default `"robust"`), optional `targets` `{ min_total_return?, min_sharpe?, min_wfe?, max_drawdown?, min_trades? }`, optional `walk_forward` `{ is_months?, oos_months? }`, and **required** `budget` `{ max_iterations (int), max_wall_clock_sec?, max_tokens?, max_usd? }`. **Open-universe** (omitted `symbol`/`timeframe`) is **rejected with a clear 4xx** in iter-1 — it is J-12/Layer-2; do not silently default it.
- [ ] Expose the status: add an `autoRun` field to the `GET /api/sessions/{id}` response (`session_routes.py:get_session`), read from `session.json` meta. Additive only — do **not** change the lazy iteration-loading behavior of that route (it must stay lightweight; see the carried-forward eager-load note in NOTES).
- [ ] Startup reconciliation: in the existing startup path, mark any auto-session left in `running`/`queued` (orphaned by a worker restart) as terminal `interrupted`, so no session is stuck "running" forever.
- [ ] `autoRun` block shape persisted on `session.json` (single source, served by `GET /api/sessions/{id}`): `{ status, stopReason, stopRequested, bestIterationId, budget: { iterationsDone, maxIterations, wallClockSec, maxWallClockSec, tokens, usd }, startedAt, endedAt }`.

### Frontend (if applicable)
- None. This iteration is backend-only. The created session is visible in the **existing** UI session picker because it appears in `GET /api/sessions` and renders through the existing session-open path — no new frontend code. (Live auto-refresh, the in-browser rewire, and the UI stop control are iter-2: J-08/J-10/J-11.)

### New user-facing capability
A user (or script) can start a fully automated, budget-bounded strategy search with one HTTP call and watch it appear as a normal session in the existing UI — no manual backtest, no clicking, no browser loop. The session runs to a terminal state server-side and marks its best strategy.

### New information displayed
On the existing session record (`GET /api/sessions/{id}`): the `autoRun` status block — run state, stop reason, best-iteration id, and budget counters (iterations done / max, wall-clock, token/USD best-effort). The created session and its loop-produced iterations/activity/suggestions render through the existing session UI.

### New user actions
API only: `POST /api/auto-sessions` (start), `POST /api/auto-sessions/{id}/stop` (stop). No new UI controls this iteration.

### UI surface changes
None (no new screens/components). Per the blueprint, the headless surface adds no new screens — the automated session streams into the existing Activity Log / Iterations panels.

### Product surface delta
The platform gains a headless, server-driven optimization entry point. From the user's perspective the product now "runs itself" from a single API call and the result is an ordinary, browsable session — the foundation the open-universe optimizer (Layer-2) builds on.

### Blueprint conformance
No new Information-Architecture homes and **no nav-skeleton change** — `POST /api/auto-sessions` + `POST /api/auto-sessions/{id}/stop` (command endpoints) and the automated-session status strip already exist in `blueprint.md`. The created session lives in the existing Header → Session picker; its `autoRun` status reads on the Right-panel status strip; its iterations render in the existing Iterations panel. No `blueprint.reapproval-requested` is raised.

### Data-contract additions
No NEW value is introduced — this iteration **implements** three values already reserved in the Data Contract, concretizing their canonical computing module to `apps/backend/backend/auto_session.py` and their serving endpoint to `GET /api/sessions/{id}` (the `autoRun` block). The blueprint rows were updated (additive) accordingly:
- Automated-session run state + stop reason → `AutoSessionController`, served on `autoRun.status`/`autoRun.stopReason`.
- Budget counters (iterations + wall-clock hard-enforced; token/USD best-effort) → immutable budget tracker, served on `autoRun.budget`.
- Robust objective score + best marker → robust scorer (derived from the canonical `WalkForwardResult` + `BacktestResult`), served on `autoRun.bestIterationId`.
Reuse the registered canonical sources for everything else: backtest metrics from `MetricsCalculator`/`BacktestResult`, WFE from `walk_forward.py`/`POST /api/execute-walk-forward`, rating from `rating.py`. **Do not** add a second computation or endpoint for any of these.

## OUT OF SCOPE

- **J-08 (live UI tracking without reload)**, **J-10 (rewire in-browser Auto Run to the backend + browser-reload survival + remove the second in-browser loop)**, **J-11 (UI stop control + full stop-journey verification)** — iter-2. The `/stop` endpoint is built now as infrastructure but J-11 is not claimed this iteration.
- **J-12 open-universe** (omitted symbol/timeframe, planner over a seed universe) — rejected with a 4xx this iteration.
- **J-13 hard token/USD budget enforcement** — only `max_iterations` + wall-clock are hard caps in iter-1; token/USD are best-effort counters.
- **J-14 staged SCREEN/PROMOTE**, **J-15 global-history warm start + opt-out + prompt-cached planner**, **J-16 leaderboard / full overfit gating UI** — Layer-2.
- The in-browser `scoreIteration`/`startAutoRun` loop is **not removed** this iteration (removed at J-10). It remains the manual Auto Run path transitionally.
- Carry-forwards that do **not** block this iteration: the pre-existing `tests/test_directions_cache.py::test_write_and_read_full_round_trip` failure (nice-to-have Capability #10); fixing the ~245KB `GET /api/sessions/{id}` open-payload `equity_curve` embed (see NOTES — deliver a verdict, do not refactor here).

## DEFINITION OF DONE

- [ ] Target journeys verified against the live backend endpoints:
  - [ ] **J-07** — `POST /api/auto-sessions` with a pinned config + `budget.max_iterations: 2` returns HTTP 200 with a `sessionId` and `status` `running`/`queued`; the same `sessionId` appears immediately in `GET /api/sessions`.
  - [ ] **J-09** — a run with lenient `targets` + small budget reaches a terminal status with a visible `stopReason` (`criteria-met` or `budget-exhausted`) and a marked `bestIterationId`; when `criteria-met`, the best iteration's metrics satisfy every supplied target; when `budget-exhausted`, `iterationsDone == maxIterations` (or wall-clock hit) and no further iterations are appended.
- [ ] Required-still-passing journeys J-01…J-06 remain green (the loop reuses the same pipeline + store; manual flows and the existing in-browser Auto Run are unaffected).
- [ ] No anti-goal violation introduced (see TESTING; particularly: same artifacts/no parallel store, hard budget, persisted status, pipeline reuse, robust-best, non-blocking event loop, no secrets in artifacts).
- [ ] Backend unit/integration tests pass; the three invariant tests (`test_lookahead`, `test_determinism`, `test_sandbox`) still pass; no new regressions in the existing suite (the pre-existing `test_directions_cache` failure is the only known red and is unrelated).
- [ ] Dev handoff written at `docs/handoffs/goal-financial_free-iter-1-dev.md`.

## TESTING REQUIREMENTS

- **Unit/integration (hermetic — no live LLM):** Inject/stub the LLM-dependent `BacktestPipeline` steps (compiler/script generation/insights) with a deterministic fake so the loop is testable cheaply and repeatably. The controller MUST accept an injected pipeline (or equivalent seam) to enable this. Cover:
  - [ ] `POST /api/auto-sessions` (pinned, `max_iterations: 2`) → 200 + `sessionId` + `status` running/queued; session present in `GET /api/sessions` immediately. **(J-07)**
  - [ ] Run to terminal with **lenient targets** → `criteria-met`, best marked, best satisfies all supplied targets. **(J-09)**
  - [ ] Run to terminal with **unsatisfiable/absent targets** → `budget-exhausted`, `iterationsDone == maxIterations`, no iteration appended after the cap. **(J-09 + hard-budget anti-goal)**
  - [ ] Loop-produced artifacts are byte-shape-compatible with a manual run: iterations readable via `GET /api/sessions/{id}/iterations/{id}` (full result/rating), activity entries present, suggestions present — and written through `session_store` (no parallel store, no schema fork). **(same-artifacts anti-goal)**
  - [ ] `autoRun` status round-trips through `session.json` and is returned by `GET /api/sessions/{id}`; a fresh store read (simulated restart) still shows the persisted status; an orphaned `running` is reconciled to `interrupted` on startup. **(persisted-status anti-goal)**
  - [ ] Robust best-marking is WFE-gated + min-trades-floored: a candidate with higher raw return but WFE below threshold (or below the min-trades floor) is **not** marked best. **(robust-best anti-goal)**
  - [ ] Budget tracker is immutable and hard: constructing/incrementing never yields a state exceeding the enforced caps; the loop stops before exceeding `max_iterations`/`max_wall_clock_sec`. **(hard-budget anti-goal)**
  - [ ] `POST /api/auto-sessions/{id}/stop` flips the persisted flag and the loop transitions to `stopped` with the best-so-far retained; no iterations appended after stop. *(infrastructure for J-11)*
  - [ ] Non-blocking launch: `POST /api/auto-sessions` returns before the loop completes, and `GET /api/sessions` responds while a run is active (loop awaits the backtest semaphore). **(non-blocking anti-goal)**
- **Error cases:** open-universe request (missing `symbol`/`timeframe`) → 4xx with a clear message; missing required `budget`/`budget.max_iterations` → 422; `stop` on an unknown session → 404; `stop` on an already-terminal session → no-op 200 (idempotent).
- **External integration:** at least one end-to-end smoke with a **tiny real budget** (`max_iterations: 1–2`, short date range, cheapest default model) when `OPENAI_API_KEY` is present, asserting a real terminal state + best marked; if the key is absent, document it as skipped in the dev handoff (do not silently pass). All automated-session tests MUST use tiny budgets per `docs/goal.md`.
- **Browser:** J-07's "appears as a new session tab" — confirm the headless-started `sessionId` is present in the session list the UI renders (`GET /api/sessions`) and the session opens. If the Chrome-MCP tab returns blank pixels (documented headless-tab render throttle), verify via the backend endpoints the UI calls — that is the sanctioned substitute, not a failure.

## NOTES

- **Verification method (render throttle):** iter-0 documented that the headless Chrome-MCP tab runs backgrounded and returns blank pixels — a known automation-environment limitation, not an app defect. Both target journeys are API-first; verify them against the authoritative backend endpoints (HTTP status + parsed `autoRun`/iteration payloads) with concrete values (session id, stop reason, iteration count, best id, target satisfaction). Do not block on pixel screenshots.
- **Transitional duplicate (coherence):** the in-browser `scoreIteration`/`startAutoRun` loop in `useBacktest.ts` still exists after this iteration and computes "best" for the *manual* Auto Run. The new backend robust scorer is the **canonical** definition (now registered in the Data Contract); the in-browser one is pre-existing legacy that **J-10 (iter-2)** deletes when it rewires Auto Run to this backend loop. This is a scheduled consolidation, not silent drift — the canonical home is unambiguous and the duplicate is slated for removal next iteration. Coherence-auditor: please treat as advisory/transitional, not an introduced recompute.
- **Carried-forward eager-load verdict (lessons iter-0):** this iteration touches `session_routes.py:get_session` (adds the `autoRun` field). Per the iter-0 lesson, the coherence-auditor should deliver a definitive verdict on whether the pre-existing ~245KB `GET /api/sessions/{id}` open payload embedding `equity_curve` violates the "no eager full-payload parse" anti-goal. This iteration must **not worsen** that payload (the `autoRun` block is tiny: status string, ids, integer counters) and must **not** change the route's lazy iteration-loading behavior. Fixing the embed itself is out of scope here.
- **Frozen contracts:** `autoRun` status, budget counters, and the robust score are NEW state — they live on the free-form `session.json` meta and new dataclasses/Pydantic models in `auto_session.py`. Do **not** mutate the frozen dataclasses in `shared/contracts.py` to carry them.
- **Why full depth:** new cross-cutting backend surface (new routes + a background-task loop + durable status + concurrency against the event-loop semaphore) with anti-goals that become live the moment this code lands — it warrants the full 11-step pipeline, not a lean cycle.
- **Reference:** evaluator recommendation in `runs/goal-session-financial_free/iter-0/eval.md` (§Next-Step Recommendation); in-browser loop to port at `apps/frontend/src/hooks/useBacktest.ts:2047`.
