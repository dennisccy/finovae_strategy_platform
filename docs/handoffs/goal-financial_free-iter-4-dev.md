# goal-financial_free-iter-4 Dev Handoff

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering for the open-universe search (J-14)
**Date:** 2026-05-23
**Agent:** developer
**Status:** complete

## What Was Built

Turned the open-universe automated search from a flat "evaluate every seed config uniformly with walk-forward + the chosen model" loop into a **two-stage cost-tiered search** — pure orchestration over the existing pipeline/scorer/store (no new metric, endpoint, page, route, request field, datastore, or `contracts.py` change).

- **SCREEN stage (cheap):** enumerates the budget-bounded seed configs (`seed_universe_configs`) and evaluates each on the **cheapest** catalog model with **`wfv_enabled=False`** (no walk-forward). Each is persisted as an iteration node (distinct configs still surface as cards → J-12 preserved). Screened cards show the cheap model and **no** walk-forward section.
- **Rank + select survivors:** ranks screened candidates by the **canonical** `RobustScorer.score()` and takes the top-`k` where `k = min(DEFAULT_PROMOTE_K, n_screened)` (new module constant `DEFAULT_PROMOTE_K = 1`). Deterministic: ties break by seed-config order. Whenever ≥2 were screened, `k < n_screened` holds.
- **PROMOTE stage (expensive):** re-evaluates only the survivors on the **stronger request model** with **`wfv_enabled=True`** (walk-forward), persisting each as a **child** of the screened node it was promoted from (screen→promote lineage in the iteration tree).
- **Best selection (anti-goal-critical):** `autoRun.bestIterationId` is marked by `RobustScorer.select_best()` over the **PROMOTED candidates only** — screened-only nodes (which carry `wfe=None` and would otherwise pass `is_eligible`) are **never** in the candidate list, so they can never be marked best. `select_best → None` (no eligible promoted candidate) is the correct gated outcome.
- **Model routing — single source of truth:** new `cheapest_model()` in `shared/model_catalog.py` returns the min blended-rate catalog model (today `gpt-5.4-mini`). SCREEN uses `cheapest_model()`; PROMOTE uses the request `model` (defaults to `DEFAULT_MODEL`). Tier selection lives in the catalog, not hard-coded in `auto_session.py`. Scoped to the open-universe path only — the pinned path is untouched.
- **Budget semantics across stages:** new `BudgetTracker.cost_exceeded()` checks **only** the cost caps (tokens / USD / wall-clock), NOT configs/iterations. `max_configs` remains the **SCREEN-breadth** cap (`configs_done` counts SCREEN candidates only; the full `exceeded()` gates each SCREEN unit). PROMOTE — a bounded refinement of already-counted configs — is gated on `cost_exceeded()` so it isn't skipped once SCREEN fills `configs_done` to `max_configs`. `exceeded()` is unchanged (J-13 tests depend on it). Promote generations (stronger model) accrue real USD via the existing `_account_usage` on the one immutable tracker; a token/USD cap reached during SCREEN or PROMOTE halts `budget-exhausted` with no unit started past the cap.
- **Activity-log visibility:** both stages surface as existing `type:"auto-run"` records (no new store, no schema fork) with explicit text labels: a `SCREEN —` stage header (cheap model + "no walk-forward" + count), one `SCREEN —` entry per screened candidate (symbol/timeframe + canonical score), a `PROMOTE —` stage header ("top-k of N" + stronger model + "walk-forward"), and a `PROMOTE —` best entry per new WFE-gated best.
- **Preserved invariants:** B1+B2 (all `autoRun` RMW under the shared per-session lock, store I/O off-loop, backtests semaphore-guarded); a `/stop` mid-SCREEN or mid-PROMOTE transitions to `stopped` at the next checkpoint with no further node appended; OHLCV Parquet cache + code-hash dedup reused (SCREEN `wfv=False` and PROMOTE `wfv=True` have distinct dedup keys, so the promote walk-forward correctly runs — added fidelity, not a forbidden re-backtest); frozen `contracts.py` untouched; no secrets in artifacts.

## Files Changed

- `apps/backend/shared/model_catalog.py` — ADD `cheapest_model() -> str` (min blended input+output rate over `MODEL_RATES`, ties broken by model id → `gpt-5.4-mini` today). Additive; not a frozen contract.
- `apps/backend/backend/auto_session.py` — ADD module constant `DEFAULT_PROMOTE_K = 1`; ADD `BudgetTracker.cost_exceeded()` (token/USD/wall-clock only); import `cheapest_model`; **restructure `_run_open_universe`** into the SCREEN→PROMOTE flow described above. `_run_inner` (pinned path), `exceeded()`, `seed_universe_configs`, `RobustScorer`, `_build_node`, `_create_iteration`, `_persist_new` all reused unchanged.
- `apps/backend/tests/auto_session_helpers.py` — extend `FakePipeline.generate_strategy` to record its `model` kwarg in `generate_calls` (test-helper-only) for a direct SCREEN-cheap / PROMOTE-stronger assertion.
- `apps/backend/tests/test_auto_session.py` — ADD `cost_exceeded()` unit tests + the J-14 staged-flow scenarios (stage routing, k<N, best-WFE-gated-from-promoted-only, stop-mid-SCREEN, stop-mid-PROMOTE, degenerate single-config, promote-failure-non-fatal); UPDATE the existing open-universe tests' expected node counts / best semantics to the staged flow **without weakening the invariant each protects**.
- `apps/backend/tests/test_model_rates.py` — ADD `cheapest_model()` tests (returns the min-rate catalog model; is a real catalog entry).
- `apps/backend/tests/test_auto_session_live.py` — ADD a live, cross-provider staged integration test (`test_live_open_universe_staged_screen_promote`, `@pytest.mark.integration`, gated on both `OPENAI_API_KEY` + `ANTHROPIC_API_KEY`); add the `_HAS_ANTHROPIC_KEY` gate.
- `apps/frontend/src/components/ActivityLogEntry.tsx` — **no change** (see frontend handoff): the recommended `type:"auto-run"` mechanism reuses the existing render branch.

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest -q` (hermetic; integration tests deselected by default)
Result: **207 passed, 1 failed, 2 deselected**

- The single failure is the **known, pre-existing** `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (`timeframeResults` round-trip — unrelated to this journey; `directions_cache.py` and its test are NOT in this diff). Explicitly declared out-of-scope carry-forward by the spec.
- Anti-goal invariants green: `test_lookahead`, `test_determinism`, `test_sandbox` (+ `test_auto_session_routes`) — 59 passed.
- Targeted: `test_model_rates.py` + `test_auto_session.py` — 63 passed.
- `cheapest_model`/`cost_exceeded`/`_run_open_universe` add no new mypy error referencing the J-14 logic (baseline 228 → 229; the +1 is a bare-`dict` type-arg in an annotation, matching the file's pervasive existing convention). Ruff: clean on all changed files.

**Live integration (real OpenAI + Anthropic + Binance):** `test_live_open_universe_staged_screen_promote` — **PASSED in 81s**. Confirmed end-to-end: SCREEN ran ≥2 cheap candidates on `gpt-5.4-mini` (no WF), PROMOTE escalated the top-`k` (k < screened) to `claude-haiku-4-5` **with** walk-forward, the marked best was a promoted WFE-bearing node, and the Activity Log carried both `SCREEN —` and `PROMOTE —` entries — with no secrets in artifacts. This is the spec's recommended live QA recipe, pre-validated at the backend level the UI polls.

**Service startup:** backend boots cleanly (`uvicorn main:app`); `GET /api/models` → 200 (exercises the changed `model_catalog`), `GET /api/symbols` → 200; no errors/tracebacks in the startup log; server processes cleaned up afterward.

## Known Issues

- **Stop mid-SCREEN leaves `bestIterationId = None` (by design, not a regression).** Because the best is WFE-gated and marked only from PROMOTED candidates, a `/stop` before any promote runs leaves best `None` — there is no WFE-gated candidate yet, and a screened-only node must never be marked best (the anti-goal). All screened nodes so far stay persisted/browsable; no work is lost. A stop mid-PROMOTE preserves the already-promoted best (covered by `test_open_universe_stop_during_promote_preserves_best`, which raises promote-k to 2 via monkeypatch to create a between-promotes window).
- **Pre-existing red** `test_directions_cache::test_write_and_read_full_round_trip` left as-is (out of scope; not touched). `test_post_returns_before_loop_completes_and_get_stays_responsive` was not touched (no incidental change).
- **Browser pixel debt (J-08/J-10/J-14):** load-bearing this iteration but is the browser-qa agent's responsibility against the same live FE/BE in its own window. The backend-endpoint substitute (`GET /api/sessions/{id}` → `autoRun` + activity entries) that browser-qa should use as the documented-throttle fallback is exactly what the live integration test above verifies the shape of.
- **One mypy `type-arg` nit** added (228→229) for the `screened: list[tuple[dict, ...]]` annotation — consistent with the file's existing bare-`dict` convention; not a real type error and not gated in this project (228 pre-existing).

## Suggested Next Phase

J-15 (global-history warm start / cached LLM-planner context over prior sessions) is the next journey — it would replace this iteration's deterministic seed-universe SCREEN ordering with a history-informed plan, using prompt caching for the leaderboard/history context. J-16 (multi-candidate overfit-gating leaderboard UI) would visualize the promoted, WFE-gated candidates this iteration now produces.
