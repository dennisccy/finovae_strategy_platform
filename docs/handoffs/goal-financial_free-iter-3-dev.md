# goal-financial_free-iter-3 Dev Handoff

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Agent:** developer
**Status:** complete
**Target journeys:** J-12 (open-universe multi-config search), J-13 (hard token/USD budget)
**Required-still-passing:** J-07/J-08/J-09/J-10/J-11 (+ no-regression J-01–J-06)
**Frontend Present:** yes

## What Was Built

**Layer-2 start — the automated session graduates from "refine one pinned config" to
"explore a small open universe under a real, hard cost budget," with spend now visible.**

### Backend

- **Open-universe on `POST /api/auto-sessions` (J-12).** When BOTH `symbol` and `timeframe` are
  omitted (with `objective: "robust"` + a valid `budget`), the route now returns **200** and launches
  a new **open-universe controller path** instead of the old 400. The pinned-config path (both
  present) is **byte-for-byte unchanged** so J-07 is untouched. Exactly one of symbol/timeframe is
  ambiguous → 400. `natural_language` is now **optional** in open-universe mode (a seed idea is drawn
  when omitted; if provided it pins the idea and only symbol/timeframe vary); a fully-pinned config
  still requires a ≥10-char prompt (422 otherwise).
- **Bounded seed universe** — an explicit, hard-capped constant in `auto_session.py`
  (`SEED_SYMBOLS` × `SEED_TIMEFRAMES` × `SEED_STRATEGY_IDEAS`, ceiling `SEED_UNIVERSE_MAX`). The
  search enumerates a budget-bounded subset; it never enumerates `/api/symbols` or fans out
  exchange-wide. The first two enumerated configs differ in symbol, so a 2-config run yields two
  genuinely distinct configs.
- **Open-universe controller loop** (`_run_open_universe`). Explores ≥2 distinct configs, evaluates
  each **uniformly** through the existing `BacktestPipeline` (generate → backtest → walk-forward),
  scores with the existing `RobustScorer`, and marks the single cross-config best as
  `autoRun.bestIterationId`. Each config persists via the same `session_store.write_iteration` (no
  schema fork; distinct configs render through the existing iteration cards via their own `params`).
  A single config's generation/backtest failure is **non-fatal** (logged, search continues); a run
  where every config fails terminates cleanly as `budget-exhausted`. Per-config evaluation is the
  single reusable method `_create_iteration(config, …)` — J-14 can wrap it in SCREEN/PROMOTE stages
  later with no rewrite.
- **Hard budget — `max_configs` + token/USD (J-13).** `BudgetTracker` gained `max_configs`,
  `configs_done`, `max_tokens`, `max_usd` and `with_config_completed()`. `exceeded()` now
  hard-enforces **all** caps (iterations/configs, wall-clock, tokens, USD), checked **before** each
  unit of work — the loop never starts "one more" past a cap. `to_dict()` exposes
  `configsDone`/`maxConfigs`/`maxTokens`/`maxUsd` (plus the existing tokens/usd) on the canonical
  `autoRun.budget` block.
- **Real token/USD accounting (J-13).** LLM token usage already present at the SDK response level
  (OpenAI `prompt_tokens`/`completion_tokens`; Anthropic `input_tokens`/`output_tokens`) is now
  captured on a **side channel** — `last_usage` on the script/insights generators → surfaced as
  `last_strategy_usage`/`last_insights_usage` on `BacktestPipeline` → threaded into the controller's
  immutable `BudgetTracker.with_usage()`. Tokens→USD is mapped by a **new per-model rate table** in
  `shared/model_catalog.py` (the single source of truth; tests assert exact costs against it). The
  frozen `GenerateStrategyResult` / `shared/contracts.py` are **untouched**.
- **Both pinned and open-universe** now accrue real token/USD and finish `budget-exhausted` when any
  cap is hit; no config/iteration is appended after a cap.
- **B1+B2 preserved** — the open-universe loop reuses `_save_auto_run`/`_stop_requested` under the
  shared per-session `asyncio.Lock`; store I/O stays off-loop via `_run_off_loop`; backtests stay
  semaphore-guarded inside `_create_iteration`.
- **OHLCV cache reuse + code-hash dedup** — the OHLCV Parquet cache is reused across configs
  automatically by the shared pipeline loader (no re-fetch when covered). A per-session backtest
  dedup cache (keyed on code hash + result-affecting params) ensures an identical generated strategy
  on identical params is **never re-backtested**.

### Frontend (display-only)

- `AutoSessionStatusStrip` now shows **token spend / cap**, **USD spend / cap**, and a **configs
  explored / max** counter (for open-universe; pinned sessions keep the **rounds** counter) — all
  read-only from the canonical `autoRun.budget` block, display-formatting only (compact tokens,
  4-dp USD), no recomputation.
- `AutoRunBudget` TS type extended with `configsDone`/`maxConfigs`/`maxTokens`/`maxUsd`, mirroring
  the backend `to_dict()`.

## Files Changed

**Backend**
- `apps/backend/shared/model_catalog.py` — NEW `TokenUsage` + `TokenRate` + `MODEL_RATES` table +
  `cost_usd()` (single source of truth for token→USD). Additive; not a frozen contract.
- `apps/backend/strategy/script_generator.py` — expose captured SDK token usage on `last_usage`
  (both OpenAI + Anthropic branches; reset per call). Existing logging kept.
- `apps/backend/strategy/insights_generator.py` — same `last_usage` side channel (None on cache hit).
- `apps/backend/backend/pipeline.py` — surface `last_strategy_usage`/`last_insights_usage` from the
  generators after each `generate_strategy`/`generate_insights` (no frozen-contract change).
- `apps/backend/backend/auto_session.py` — `BudgetTracker` extended (configs/token/USD hard caps,
  `with_config_completed`, extended `exceeded()`/`to_dict()`); seed-universe constants +
  `seed_universe_configs()`; controller gains `open_universe` + `_account_usage` + a backtest dedup
  cache; pipeline-step methods (`_generate`/`_backtest`/`_build_node`/`_insights`/`_create_iteration`)
  parametrized by an explicit `config`; new `_run_open_universe()`; `run()` dispatches pinned vs
  open-universe. Pinned `_run_inner` preserved.
- `apps/backend/backend/auto_session_routes.py` — `AutoSessionBudget` gains `max_configs` (gt 0);
  `natural_language` now optional with a pinned-requires-NL validator; `_build_config`/`_build_budget`
  handle open-universe (wire `max_tokens`/`max_usd`/`max_configs`, default `max_configs` from
  `max_iterations`); route dispatches open-universe (both omitted) vs pinned, ambiguous one-of → 400;
  pinned timeframe/objective checks preserved.

**Backend tests**
- `apps/backend/tests/test_model_rates.py` — NEW (6 tests): exact token→USD costs, unknown-model
  fallback, every catalog model has a rate.
- `apps/backend/tests/test_auto_session.py` — +18 tests: budget config/token/USD hard caps +
  immutability; open-universe distinct-configs/best, WFE-gated best, terminal-at-max-configs,
  token-cap stop, USD-cap stop, single-config-failure non-fatal, all-fail clean terminal, stop
  request, B1+B2 stop-vs-save race (open-universe), token/USD threading (exact),
  pinned-path-unchanged regression, code-hash dedup. Updated `test_budget_to_dict_shape` for the new
  keys.
- `apps/backend/tests/test_auto_session_routes.py` — open-universe now 200 (replaces the old 400
  test); open-universe-without-NL 200; pinned-without-NL 422; `max_configs`/`max_tokens`/`max_usd`
  ≤ 0 → 422.
- `apps/backend/tests/auto_session_helpers.py` — `FakePipeline` gains `usage` (token side channel),
  `fail_exec_indices` (non-fatal failure tests), `fixed_code` (dedup test).

**Frontend**
- `apps/frontend/src/lib/sessionApi.ts` — `AutoRunBudget` + 4 fields.
- `apps/frontend/src/components/AutoSessionStatusStrip.tsx` — configs/token/USD counters + formatters.

**Docs**
- `runs/goal-session-financial_free/state/blueprint.md` — **no edit needed**: the goal-decomposer had
  already added the additive Budget-counters Notes + the reserve open-universe row for iter-3 (no
  nav-skeleton change → no `blueprint.reapproval-requested`).

## Tests Run

**Backend** — `cd apps/backend && .venv/bin/python -m pytest`
Result: **194 passed, 1 deselected, 1 failed** (~6s).
- The **1 failed** is the pre-existing, unrelated `test_directions_cache.py::test_write_and_read_full_round_trip`
  (nice-to-have Capability #10, untouched) — the documented carry-forward red, **not a regression**
  (identical failure in iter-1/iter-2). The **1 deselected** is the optional live key-gated smoke.
- Invariants green: `test_lookahead`, `test_determinism`, `test_sandbox` all pass.
- `ruff check` clean on all files I authored/changed (auto_session.py, auto_session_routes.py,
  model_catalog.py, and the four test files). Pre-existing lint in `pipeline.py` (15 long-line/import
  findings) and the generators' blank-line whitespace were left untouched (surgical-change policy);
  I added zero new lint findings to those files.

**Frontend** — `cd apps/frontend && npm run build` (tsc + vite) **passes**; `npm run lint`
(`--max-warnings 0`) **passes**.

**Service startup** — `bash scripts/start-backend.sh` boots clean (no startup errors; orphan
reconciliation runs; session store initialized). `GET /api/health` → 200, `GET /api/sessions` → 200,
`GET /api/models` → 200 (model_catalog change intact). New route validation verified **live**
(no tokens burned — these return before any LLM call): ambiguous one-of symbol/timeframe → 400,
open-universe `max_configs=0` → 422, non-robust objective → 400, stop-unknown → 404. Stop→restart on
the deterministic offset port shows **no port conflict**. Backend stopped after the check
(`pkill -f "uvicorn main:app"`; confirmed down).

## Known Issues / Limitations

- **Happy-path live open-universe run (real LLM + Binance) was NOT executed by the developer** to
  avoid burning API tokens (an `OPENAI_API_KEY` is present in `.env`). The loop is covered by the
  hermetic suite (open-universe distinct-configs, budget caps, token/USD threading), and the route is
  verified live for its validation paths. **The browser-qa-agent should run the tiny-budget live
  open-universe smoke** (≤2 configs, short range, cheapest model) plus J-08/J-10 + J-01/J-05 — and,
  per the iter-2 lesson, **health-check the Vite frontend stays serving across the whole browser-qa
  window** (re-probe mid-run) to clear the accumulated live-pixel debt.
- **Open-universe has no `criteria-met` path this iteration** — it terminates on the hard budget
  (configs/tokens/USD/wall-clock) or a `/stop`, marking the best by robust score. Targets-based
  early-stop is the pinned path's behavior (J-09); open-universe is "objective + budget only" per
  the spec.
- **Open-universe does not generate per-config insights** (cheapest path; the spec's per-config
  evaluation is generate→backtest→walk-forward→score). Nodes carry `insights: null`, a valid shape
  the UI already handles. Per-config insights / staged screening is J-14.
- **`max_configs` defaults to `max_iterations`** when an open-universe request omits it, so a minimal
  `{max_iterations: N}` budget explores N configs. The seed universe is hard-capped at
  `SEED_UNIVERSE_MAX` (currently 4) regardless of a larger `max_configs`.
- **No UI control to trigger open-universe** (J-12 is API-triggered; the in-UI "Auto Run" stays
  pinned-config). The UI only *tracks* an open-universe run live (status strip + cards). This is per
  the spec's OUT OF SCOPE.
- Pre-existing: `mypy` is not gated in this repo; `test_directions_cache` red as noted.

## Suggested Next Phase

**J-14** — staged SCREEN→PROMOTE cost tiering + model routing: wrap the now-reusable
`_create_iteration` per-config evaluation in a cheap `SCREEN` stage (no walk-forward, cheapest model)
that promotes only the top-k survivors to full evaluation (walk-forward + stronger model), honoring
the "SCREEN-skips-WF" anti-goal. Then **J-15** (global-history warm start, read-only, opt-out) and
**J-16** (multi-candidate leaderboard + overfit-gating visualization). The open-universe search, the
hard cost budget, and the live token/USD status strip landed here are the foundation those build on.
