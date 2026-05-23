# Phase goal-financial_free-iter-3 — UI Surface Map

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Written by:** ui-impact-analyst

---

## Affected UI Surfaces

<!-- "What to Test" is a specific action with an expected result. -->

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| `/` (Iterations panel) | `AutoSessionStatusStrip` — token-spend chip | Updated layout (new counter) | J-13 surfaces real AI token spend vs cap | Start an open-universe run with a tiny `max_tokens` budget; confirm the strip shows a `… tok` chip whose number **increases** across the ~2.5s polls and reads `<spend> / <cap> tok` (e.g. `1.2k / 5k tok`). |
| `/` (Iterations panel) | `AutoSessionStatusStrip` — USD-cost chip | Updated layout (new counter) | J-13 surfaces real USD cost vs cap | On the same run, confirm a `$…` chip renders 4-dp USD as `$0.0xxx / $0.0xxx` and the spent value rises as tokens accrue; the spend stays ≤ the cap. |
| `/` (Iterations panel) | `AutoSessionStatusStrip` — configs chip | Updated layout (new counter) | J-12 open-universe run tracks configs explored, not rounds | For an open-universe run confirm the strip shows `…/… configs` (e.g. `1/2 configs`) and NOT a `rounds` chip; the configsDone number increments to its `maxConfigs` then the run goes terminal. |
| `/` (Iterations panel) | `AutoSessionStatusStrip` — rounds chip (regression) | Changed behavior (conditional) | configs↔rounds choice now driven by `maxConfigs` | Start a **pinned** Auto Run (symbol+timeframe via the in-UI control); confirm the strip still shows `…/… rounds` (NOT configs) — proving the pinned path display is unregressed (J-07/J-08). |
| `/` (Iterations panel) | `AutoSessionStatusStrip` — terminal state | Changed behavior | budget-exhausted styling now wraps the new counters | Let a tiny-budget open-universe run reach its cap; confirm the strip turns **amber** with a `Budget exhausted` badge + stop-reason label, and the token/USD/configs chips remain readable. |
| `/` (Iterations panel) | `AutoSessionStatusStrip` — Best badge | Changed behavior | best now selected by robust score across ≥2 configs | After the open-universe run goes terminal, confirm a violet **Best: <id8>** badge appears and its id matches `autoRun.bestIterationId` from `GET /api/sessions/{id}`. |
| `/` (Iterations panel) | Iteration history tree — config cards | Changed behavior (existing component, new data) | open-universe configs stream through existing cards | During an open-universe run confirm ≥2 cards appear **without a page reload**, each showing a **distinct** symbol/timeframe in its `params`; reload mid-run and confirm the cards + status strip survive (J-08 live tracking + J-10 reload survival). |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/backend/auto_session.py` — `_run_open_universe` controller loop, seed-universe constants (`SEED_SYMBOLS`/`SEED_TIMEFRAMES`/`SEED_STRATEGY_IDEAS`/`SEED_UNIVERSE_MAX`), `seed_universe_configs()`, `_create_iteration`, backtest dedup cache, `_account_usage` — orchestration only; surfaces no new value to the UI beyond the already-canonical `autoRun.budget` / `bestIterationId` / iteration `params`.
- `apps/backend/backend/auto_session.py` — `BudgetTracker` new fields (`max_configs`/`configs_done`/`max_tokens`/`max_usd`), `with_config_completed`, `with_usage`, extended `exceeded()` — hard budget enforcement; `to_dict()` additions are what the strip reads, but the enforcement logic itself is non-visible.
- `apps/backend/backend/auto_session_routes.py` — open-universe dispatch, optional `natural_language`, `max_configs` field + `_build_budget`/`_build_config` wiring — API contract change; no in-UI trigger this iteration, so visible only via direct API calls.
- `apps/backend/shared/model_catalog.py` — new `TokenUsage`/`TokenRate`/`MODEL_RATES` + `cost_usd()` token→USD price table — feeds the USD figure but has no direct UI surface.
- `apps/backend/strategy/script_generator.py`, `strategy/insights_generator.py`, `backend/pipeline.py` — `last_usage` token side channel threading — backend plumbing for the USD/token counters; no direct UI surface.
- `apps/backend/tests/*` (`test_model_rates.py`, `test_auto_session.py`, `test_auto_session_routes.py`, `auto_session_helpers.py`) — tests; no UI impact.

---

## Summary

- **Frontend surfaces changed:** 1 component (`AutoSessionStatusStrip`) + 1 reused surface (iteration history cards rendering open-universe configs)
- **New pages/routes:** 0
- **Modified components:** 1 (`AutoSessionStatusStrip`); 1 TS type (`AutoRunBudget` in `sessionApi.ts`)
- **Navigation changes:** no
- **Backend-only changes:** 9 files (controller loop, budget tracker, routes, model catalog, generators, pipeline, + 4 test files)
