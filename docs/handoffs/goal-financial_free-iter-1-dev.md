# goal-financial_free-iter-1 Dev Handoff

**Phase:** goal-financial_free-iter-1
**Date:** 2026-05-23
**Agent:** developer
**Status:** complete
**Target journeys:** J-07 (start headless session via API), J-09 (terminal stop-reason + WFE-gated best marking)
**Frontend Present:** no (backend-only)

## What Was Built

A server-side, budget-bounded automated strategy loop that reuses the existing
`BacktestPipeline` and writes the same artifacts the UI renders.

- **`AutoSessionController`** (`backend/auto_session.py`) — runs the headless
  loop as an awaitable background task. Reuses the **injected** pipeline for
  every step (`generate_strategy` → `execute_backtest` → rating → `generate_insights`,
  plus walk-forward on candidates for the WFE gate). The injected-pipeline seam
  makes the loop hermetically testable with no live LLM.
  - Step 0 seeds a baseline iteration (persisted as iteration 1 + activity).
  - Improvement rounds (hard-bounded by budget): take the baseline's untried
    suggestions, generate+backtest+walk-forward each candidate, persist each,
    score, keep/mark the best, regenerate insights on the new baseline.
  - Terminal state machine (priority order, checked each round): targets all
    satisfied → `criteria-met`; hard budget reached → `budget-exhausted`;
    persisted stop request → `stopped`; no remaining suggestions →
    `budget-exhausted`.
- **`BudgetTracker`** — immutable (frozen) value object. `max_iterations` and
  `max_wall_clock_sec` are **hard-enforced** (checked *before* each round; never
  starts "one more round" past a cap). `tokens`/`usd` are best-effort counters
  (hard cap = J-13).
- **`RobustScorer`** — canonical "best" definition. Ported from the in-browser
  `scoreIteration` (`useBacktest.ts:2100`): `(total_return + max(0,sharpe)*0.05)
  * min(1, 0.5 + n/100)`, then a **drawdown penalty** (`- 0.5 * max_drawdown`).
  Eligibility gates: min-trades floor (zero-trade ineligible), `not margin_called`,
  and the **WFE accept gate reusing the 0.3 threshold** verbatim. A higher
  raw-return but WFE-failing/over-leveraged candidate is never marked best.
- **`targets_satisfied`** predicate — best must satisfy *every* supplied target;
  absent targets are explicitly **not** a success condition (→ run to budget).
- **`POST /api/auto-sessions`** (`backend/auto_session_routes.py`) — validates a
  pinned-config Pydantic request, **creates the live session in the store first**
  (so it appears immediately in `GET /api/sessions`), launches the loop as a
  non-blocking `asyncio` task registered on `app.state.auto_sessions`, and returns
  **HTTP 200** `{ sessionId, status, autoRun }`. Each backtest inside the loop
  acquires the existing `app.state.backtest_semaphore` (Semaphore(1)).
- **`POST /api/auto-sessions/{id}/stop`** — flips a persisted `stopRequested`
  flag; the loop honors it at its next checkpoint → `stopped`. Idempotent 200 on
  already-terminal; 404 on unknown/non-auto session. (Cancellation infrastructure;
  the full J-11 UI stop journey is iter-2 — **not claimed here**.)
- **`autoRun` status block** persisted on `session.json` and exposed (additively)
  on `GET /api/sessions/{id}`: `{ status, stopReason, stopRequested,
  bestIterationId, budget:{iterationsDone, maxIterations, wallClockSec,
  maxWallClockSec, tokens, usd}, startedAt, endedAt }`.
- **Startup reconciliation** — any auto-session left `running`/`queued` (orphaned
  by a worker restart) is marked terminal `interrupted` on startup.
- **`backend/result_serialization.py`** — single-source serialization of
  `BacktestResult`/`StrategyRating`/`WalkForwardResult` → the API/store JSON
  shapes, **extracted from `api.py`** so the manual SSE path and the headless
  loop emit byte-shape-identical payloads (see Scope Notes).

## Files Changed

Created:
- `apps/backend/backend/auto_session.py` — controller, `BudgetTracker`,
  `RobustScorer`, `targets_satisfied`, `AutoSessionConfig`, `reconcile_orphaned_sessions`.
- `apps/backend/backend/auto_session_routes.py` — `POST /api/auto-sessions` +
  `/stop`, the pinned-config request schema.
- `apps/backend/backend/result_serialization.py` — canonical result/rating/WFR
  serializers (extracted from `api.py`; adds dict wrappers for the store).
- `apps/backend/tests/test_auto_session.py` — 25 unit + controller tests (hermetic).
- `apps/backend/tests/test_auto_session_routes.py` — 15 route/API tests (hermetic).
- `apps/backend/tests/test_auto_session_live.py` — 1 key-gated live smoke (`@pytest.mark.integration`).
- `apps/backend/tests/auto_session_helpers.py` — shared fakes/factories (not collected).

Modified:
- `apps/backend/backend/api.py` — mounts the auto-session router; startup
  reconciliation + `app.state.auto_sessions` registry; **serialization helpers
  now imported from `result_serialization`** (aliased to their old private names;
  `execute_backtest` uses the shared `serialize_backtest_result`). Also defined
  the module-level `logger` the module already referenced (latent pre-existing bug).
- `apps/backend/backend/session_routes.py` — `get_session` additively returns
  `"autoRun": meta.get("autoRun")` (no change to lazy iteration loading).
- `apps/backend/pyproject.toml` — registered the `integration` pytest marker and
  set `addopts = "-m 'not integration'"` so the default suite stays fast/token-free.

Reused unchanged: `pipeline.py`, `session_store.py`, `backtest/walk_forward.py`,
`backtest/rating.py`, `shared/model_catalog.py`. **`shared/contracts.py` (frozen)
untouched** — all new state lives on the free-form `session.json` meta + new
dataclasses/Pydantic models.

## Tests Run

Command (hermetic, default): `cd apps/backend && .venv/bin/python -m pytest`
Result: **164 passed, 1 deselected, 1 failed** in ~6s.
- The 40 new tests (25 unit/controller + 15 route) all pass.
- The three invariant tests pass: `test_lookahead`, `test_determinism`, `test_sandbox`
  (39 tests across those files).
- The **1 failed** is the pre-existing, unrelated
  `test_directions_cache.py::test_write_and_read_full_round_trip`
  (`timeframeResults` round-trip; nice-to-have Capability #10). It imports only
  `backend.directions_cache` (a module I did not touch) and fails identically on
  the untouched tree — explicitly the only known red per the spec.

Live external-integration smoke (spec-required, key present):
Command: `cd apps/backend && .venv/bin/python -m pytest -m integration tests/test_auto_session_live.py`
Result: **1 passed in 317s (~5.3 min).** The REAL pipeline (OpenAI `gpt-5.4-mini`
strategy generation + insights, real Binance OHLCV fetch, RestrictedPython
sandbox, deterministic engine, real walk-forward) ran end-to-end via the
controller with a tiny budget (`max_iterations: 1`, BTC/USDT 1h, 3-month range)
and reached a **real terminal state with a marked best iteration** that round-trips
through the store. (Excluded from the default suite via `-m "not integration"`.)

Service startup verified: `uvicorn main:app` boots clean (no errors); both new
routes appear in `/openapi.json`; `/api/health` healthy; `GET /api/sessions`
returns 200 (additive `autoRun` field + startup reconciliation cause no
regression). Lint: `ruff check` passes on all new/modified source files.

## Anti-goal compliance (mapped to tests)

- **Same artifacts / no parallel store** — iterations written via `session_store`;
  byte-shape-identical to the manual SSE serializer (one source). Test:
  `test_artifacts_are_byte_shape_compatible_with_manual_run`.
- **Hard budget** — immutable tracker; loop runs exactly `max_iterations` rounds.
  Tests: `test_budget_*`, `test_budget_exhausted_runs_exactly_max_iterations`.
- **Robust best (WFE-gated, min-trades floor, dd-penalized)** — Tests:
  `test_best_is_wfe_gated_not_highest_raw_return`, `test_select_best_*`, `test_*_eligibility`.
- **Persisted status survives restart** — Tests:
  `test_auto_run_status_round_trips_through_session_json`,
  `test_reconcile_orphaned_running_to_interrupted`.
- **Non-blocking event loop** — Test:
  `test_post_returns_before_loop_completes_and_get_stays_responsive` (loop awaits
  the shared backtest semaphore).
- **No secrets in artifacts** — Test: `test_no_secrets_in_artifacts`.
- **Pipeline reuse / no sandbox bypass** — the controller only calls
  `BacktestPipeline` methods; confirmed live by the smoke.
- **Open-universe rejected (J-12 is Layer-2)** — Test: `test_open_universe_rejected_4xx` (400).

## Scope notes for reviewer / auditor

- **Why `api.py` serialization was extracted (beyond the plan's literal list):**
  the same-artifacts anti-goal requires the headless loop's `result`/`rating`
  payloads to be byte-identical to a manual run. Rather than duplicate (drift
  risk), the canonical serializers were moved to `result_serialization.py` and
  imported back into `api.py` under their original private names — a faithful,
  behavior-preserving move. `execute_backtest` now calls the shared
  `serialize_backtest_result` (the manual path J-01 uses). Verified no regression
  (164 hermetic passing incl. all session/walk-forward/run paths).
- **`/stop` is built as infrastructure**, not the J-11 journey. J-11 (UI stop
  control + full reload-survival journey) is iter-2 and is **not** claimed here.
- **In-browser `scoreIteration`/`startAutoRun` left in place** — the transitional
  duplicate for the *manual* Auto Run; the backend `RobustScorer` is the canonical
  "best." J-10 (iter-2) removes the in-browser loop. Treat as scheduled/advisory.
- **Carried-forward eager-load verdict:** this iteration touches
  `session_routes.get_session` (adds the tiny `autoRun` field — status string, ids,
  integer counters). It does **not** worsen the pre-existing ~245KB open-payload
  `equity_curve` embed and does **not** change the route's lazy iteration loading
  (`test_get_session_*` in test_session_routes.py still pass). Fixing that embed
  is out of scope here — verdict deferred to the coherence-auditor.

## Known Issues / Limitations

- **Token/USD are best-effort counters, not hard-capped** this iteration
  (round-count + wall-clock are the hard caps). Hard token/cost enforcement is
  J-13. The `budget.tokens`/`usd` fields currently stay at 0 (no token accounting
  is wired from the pipeline yet) — documented, intended.
- **No new UI** (backend-only by plan). The created session is visible in the
  existing session picker and renders through the existing session-open path;
  live auto-refresh + UI start/stop controls are J-08/J-10/J-11 (iter-2).
- **Walk-forward on a very short date range can yield zero windows**, leaving a
  candidate's WFE at the engine's degenerate value; such a candidate is treated as
  un-validated and cannot win on raw return alone. Use a range long enough for ≥1
  IS+OOS window when the WFE gate should bite.
- **mypy is not gated in this repo** (306 pre-existing errors across 25 files);
  the new `result_serialization.py` helpers intentionally mirror the original
  `api.py` untyped-helper style for a faithful extraction. `ruff` is clean on all
  new/modified source.
- The legacy `api.py` deprecated `POST /api/run-backtest` endpoint keeps its own
  (slightly leaner) inline result shape — intentionally left untouched (deprecated;
  not in any journey).
