# goal-financial_free-iter-1 Execution Plan

Layer-1 Foundation, full depth. Backend-only. Target journeys **J-07** (start headless session via API) and **J-09** (terminal stop-reason + WFE-gated best marking). Builds the server-side auto-session loop core; J-08/J-10/J-11 (UI tracking, in-browser rewire, UI stop control) and J-12–J-16 (open-universe optimizer) are explicitly later iterations.

**Goal alignment:** Direct subset of `docs/goal.md` Key Capability #11 and the iter-0 evaluator's "build Layer-1 Foundation at full depth, start endpoint first" recommendation. No drift. Reuses the existing `BacktestPipeline` + file store (no sandbox/engine bypass, no parallel store). The created session must be byte-shape-indistinguishable in the UI from a manual one.

## What to Build

- **`AutoSessionController`** — runs the headless loop as an awaitable background task; reuses `BacktestPipeline` (`generate_strategy` → `execute_backtest` → rating → `generate_insights`, plus `execute_walk_forward` for the WFE gate) for **every** LLM/backtest step. Accepts an **injected pipeline seam** so tests run hermetically with no live LLM.
- **Headless loop behavior** (port from in-browser `useBacktest.ts:2047` `startAutoRun`/`scoreIteration`; do not reinvent scoring): Step 0 baseline iteration (persist as iteration 1 + activity); then iterate up to `budget.max_iterations` — take untried suggestions, generate+backtest+walk-forward, persist each candidate, score, keep/mark best, regenerate insights on the new baseline. Maintain `autoRun.bestIterationId` (best-so-far) throughout.
- **Immutable BudgetTracker** value object `{ iterationsDone, maxIterations, wallClockSec, maxWallClockSec, tokens, usd }`. **Iterations + wall-clock are hard-enforced**: check `exceeded()` *before* each round; never start "one more round" past a cap. Token/USD are best-effort counters only (hard enforcement = J-13/Layer-2).
- **Robust scorer** (canonical "best" definition, registered in the Data Contract): WFE-gated (reuse existing **0.3** accept threshold), min-trades floor (zero/under-floor ineligible), drawdown-penalized — derived from canonical `WalkForwardResult` + `BacktestResult` (no second metrics/WFE computation).
- **Targets-satisfaction predicate** — given optional robust `targets`, returns whether the current best satisfies **every** supplied target.
- **Terminal state machine** (priority order, checked each round): (a) all `targets` satisfied → `criteria-met`; (b) hard budget reached → `budget-exhausted`; (c) persisted stop request → `stopped`; (d) no remaining suggestions → `budget-exhausted` (documented). On any terminal transition: write final `autoRun` status + `bestIterationId`, stop appending.
- **`POST /api/auto-sessions`** — validate pinned request; **create the live session in the store first** (write `session.json` with name + `backtestParams` + initial `autoRun` block so it appears immediately in `GET /api/sessions`); launch the loop as a non-blocking background task (registry on `app.state`); return **HTTP 200** `{ sessionId, status: "running"|"queued", autoRun: {…} }`. Each backtest inside the loop acquires the existing `app.state.backtest_semaphore` (Semaphore(1)) so the event loop stays responsive.
- **`POST /api/auto-sessions/{id}/stop`** — flip persisted `stopRequested` on the `autoRun` block; loop honors it at next checkpoint → `stopped`; idempotent 200 on already-terminal; 404 on unknown. *(Built as cancellation infrastructure the loop needs; the full J-11 journey is iter-2 — do not over-claim it.)*
- **Pinned-config Pydantic request schema**: `natural_language`, `symbol`, `timeframe`, `start_date`, `end_date`, `initial_capital`, optional `leverage`/`allow_short`, optional `model` (default `DEFAULT_MODEL` from `shared/model_catalog.py`), optional `objective` (default `"robust"`), optional `targets {min_total_return?, min_sharpe?, min_wfe?, max_drawdown?, min_trades?}`, optional `walk_forward {is_months?, oos_months?}`, **required** `budget {max_iterations:int, max_wall_clock_sec?, max_tokens?, max_usd?}`. **Open-universe** (omitted `symbol`/`timeframe`) → **clear 4xx** (it is J-12); missing `budget`/`budget.max_iterations` → 422.
- **Expose status**: add an `autoRun` field to the `GET /api/sessions/{id}` response, read from `session.json` meta. **Additive only** — must not change the route's lightweight/lazy iteration-loading behavior.
- **Startup reconciliation**: in the existing startup hook, mark any auto-session left `running`/`queued` (orphaned by a worker restart) as terminal `interrupted`.
- **`autoRun` block shape** (single source on `session.json`): `{ status, stopReason, stopRequested, bestIterationId, budget:{iterationsDone, maxIterations, wallClockSec, maxWallClockSec, tokens, usd}, startedAt, endedAt }`.

## Agents Required

- developer: **yes** — all backend implementation above + hermetic tests + one key-gated live smoke; writes the dev handoff.
- backend-data: **yes** — new loop module, routes, Pydantic schema, store integration, startup reconciliation.
- frontend-ux: **no** — zero frontend code this iteration (the created session renders through the existing session-open path).

## Frontend Present
no

(Backend-only iteration. The new capability is API-surface only; the created session is visible in the **existing** UI session picker because it appears in `GET /api/sessions` — no new components, screens, or nav. UI tracking/controls are J-08/J-10/J-11, iter-2. Browser QA is substituted by API-grounded verification per the documented Chrome-MCP headless render-throttle — see Key Test Scenarios.)

## Files to Create/Modify

- **CREATE** `apps/backend/backend/auto_session.py` — `AutoSessionController` (injectable-pipeline seam), immutable `BudgetTracker`, robust scorer, targets predicate, terminal state machine, `autoRun` dataclasses/models. New state lives here + on free-form `session.json` meta.
- **CREATE** `apps/backend/backend/auto_session_routes.py` — `POST /api/auto-sessions` + `POST /api/auto-sessions/{id}/stop`; the pinned-config Pydantic request schema (mirrors `session_routes.py`'s router style).
- **CREATE** `apps/backend/tests/test_auto_session.py` (+ `test_auto_session_routes.py` if cleaner) — hermetic loop/route tests with an injected fake pipeline; the full TESTING-REQUIREMENTS scenario set; error cases; one `@pytest.mark.integration` live smoke (tiny real budget, gated on `OPENAI_API_KEY`).
- **MODIFY** `apps/backend/backend/api.py` — `app.include_router(auto_session_router)` (alongside lines 125–126); add startup reconciliation + an `app.state` background-task registry inside the existing `@app.on_event("startup")` (line 1111).
- **MODIFY** `apps/backend/backend/session_routes.py` — add `"autoRun": meta.get("autoRun")` to the `get_session` return dict (lines 175–181); **no other change** to that route (lazy iteration loading preserved).

Reuse without modifying: `pipeline.py` (`generate_strategy`/`execute_backtest`/`generate_insights`/`execute_walk_forward`), `session_store.py` (`write_session_meta`/`write_iteration`/`append_activity_entries`/`read_session_meta`), `backtest/walk_forward.py`, `backtest/rating.py`, `shared/model_catalog.py`. **Do NOT touch** the frozen `shared/contracts.py`.

## UI Evolution / Visual Requirements
N/A — `Frontend Present: no`. Per the blueprint the headless surface adds no IA homes and no nav-skeleton change; the automated session streams into the existing Activity Log / Iterations panels. No `blueprint.reapproval-requested`.

## Key Test Scenarios

Verification is **API-grounded** against the live backend endpoints with concrete values (session id, stop reason, iteration count, best id, target satisfaction). The headless Chrome-MCP tab returns blank pixels (documented background render-throttle) — verifying via the endpoints the UI calls is the sanctioned substitute, **not** a skip.

- **J-07** — `POST /api/auto-sessions` (pinned, `budget.max_iterations: 2`) → 200 + `sessionId` + `status` `running`/`queued`; same `sessionId` appears immediately in `GET /api/sessions`.
- **J-09 (criteria-met)** — lenient `targets` + small budget → terminal `criteria-met`, best marked, and the best iteration's metrics satisfy **every** supplied target.
- **J-09 (budget-exhausted)** — unsatisfiable/absent targets → `budget-exhausted` with `iterationsDone == maxIterations` (or wall-clock hit) and **no** iteration appended after the cap.
- **Same-artifacts anti-goal** — loop-produced iterations readable via `GET /api/sessions/{id}/iterations/{id}` (full result/rating), activity + suggestions present, all written through `session_store` (no parallel store, no schema fork).
- **Persisted-status anti-goal** — `autoRun` round-trips through `session.json` and is returned by `GET /api/sessions/{id}`; a fresh store read (simulated restart) still shows it; an orphaned `running` reconciles to `interrupted` on startup.
- **Robust-best anti-goal** — a higher-raw-return but WFE-below-0.3 (or under min-trades-floor) candidate is **not** marked best.
- **Hard-budget anti-goal** — `BudgetTracker` is immutable; the loop stops before exceeding `max_iterations`/`max_wall_clock_sec` (never starts a round past the cap).
- **Non-blocking anti-goal** — `POST /api/auto-sessions` returns before the loop completes; `GET /api/sessions` responds while a run is active (loop awaits the backtest semaphore).
- **Stop infrastructure** — `POST /api/auto-sessions/{id}/stop` flips the persisted flag → loop transitions to `stopped`, best-so-far retained, no iterations appended after stop.
- **Error cases** — open-universe (missing `symbol`/`timeframe`) → clear 4xx; missing `budget`/`budget.max_iterations` → 422; stop on unknown session → 404; stop on already-terminal session → idempotent 200.
- **Live smoke** — one end-to-end with a tiny real budget when `OPENAI_API_KEY` is present (real terminal state + best marked); if absent, document as skipped in the handoff (do not silently pass).
- **No regression** — J-01…J-06 stay green; the three invariant tests (`test_lookahead`, `test_determinism`, `test_sandbox`) pass; existing suite has no new red (the pre-existing `test_directions_cache::test_write_and_read_full_round_trip` failure is the only known unrelated red).

## Assumptions (documented per token policy — not blocking)

- **Background-task durability:** the asyncio task handle is in-process (no Celery/Redis/broker allowed); durability comes from the persisted `autoRun` status on `session.json`, and orphaned in-flight runs are reconciled to `interrupted` on startup. This satisfies the persisted-status anti-goal (status survives restart; the in-memory handle does not need to).
- **Secret hygiene:** API keys/model secrets are never written to the activity log or `autoRun` block — only NL prompt, config, metrics, ids, and counters are persisted.
- **WFE gate threshold = 0.3**, reused verbatim from the in-browser loop (the canonical value the spec instructs porting).
- **Request schema home:** the pinned-config Pydantic model lives in `auto_session_routes.py`; new `autoRun`/budget/score models live in `auto_session.py`. `shared/contracts.py` (frozen) is untouched.

## Scope Discipline / Flags

- The `/stop` endpoint is built **as infrastructure the loop needs** (cancellation checkpoint) — in scope — but the **J-11 journey is not claimed** this iteration. Reviewer/auditor should not treat building `/stop` as scope creep, nor credit J-11 as done.
- The in-browser `scoreIteration`/`startAutoRun` loop is **intentionally left in place** (transitional duplicate for the manual Auto Run); it is removed at J-10/iter-2. The new backend scorer is the canonical "best." Coherence-auditor: treat the duplicate as scheduled/advisory, not introduced drift.
- **Carry-forward verdict (no fix here):** this iteration touches `get_session`; the coherence-auditor should deliver a definitive verdict on the pre-existing ~245KB `GET /api/sessions/{id}` open-payload `equity_curve` embed. This iteration must **not worsen** it (the `autoRun` block is tiny: strings, ids, integer counters) and must not change the route's lazy iteration loading. Fixing the embed itself is out of scope.
- Out of scope (do not implement): J-08/J-10/J-11 UI work, J-12 open-universe (rejected with 4xx), J-13 hard token/USD enforcement, J-14 SCREEN/PROMOTE, J-15 history warm-start, J-16 leaderboard.
