# goal-auto-money-printer-iter-4 Dev Handoff

**Phase:** goal-auto-money-printer-iter-4
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built

Staged **SCREEN→PROMOTE** cheap-first model/walk-forward routing for the
open-universe automated run (**J-14**), plus the carried iter-3 **B1** fix.
Open-universe only — the pinned path is byte-unchanged behaviourally.

- **Catalog-resolved cheapest model.** New `shared/model_catalog.cheapest_model()`
  returns the lowest combined per-token-cost model from `MODEL_PRICING`
  (resolved from the table at call time, **not a hardcoded literal**; ties
  break on model id for stability). Currently resolves to `gpt-5.4-mini`.

- **Two-stage open-universe controller** (`auto_session._run_staged_open_universe`):
  - **SCREEN stage** — evaluates a deterministic prefix of the bounded seed
    universe (`_SCREEN_SET_SIZE = 4` configs). Each screened config runs
    `generate_strategy` with the **cheapest** model, `execute_backtest` with
    `wfv_enabled=False`, and **no `generate_insights`** call. A distinct
    `SCREEN config N: SYM TF` activity marker + a `SCREEN N done — … in-sample
    Sharpe … (cheap screen — no walk-forward)` completion entry are appended
    per config. A screened iteration node is written (`stage:"screen"`,
    `modelUsed`=cheapest, `walkForwardResult:null`).
  - **Rank + PROMOTE** — survivors are ranked by a cheap **in-sample** proxy
    (in-sample Sharpe, tie-broken by raw return — explicitly **not**
    `robust_score`/WFE, which need the walk-forward SCREEN deliberately
    skipped). Only the small top-k (`_PROMOTE_TOP_K = 2`, with
    `k = min(_PROMOTE_TOP_K, screened-1, max_iter)` so **k < number screened**)
    is promoted. A distinct `PROMOTE config: SYM TF (top-k survivor; …)`
    marker is appended per promoted config.
  - **PROMOTE stage** — reruns the **full** pipeline for each promoted
    config: `wfv_enabled=True`, the **stronger requested `req.model`**, and
    the insights call — **reusing the SCREEN candidate's already-generated
    strategy by code hash** (no second `generate_strategy`) and the warm
    single-file OHLCV Parquet cache (same symbol/timeframe/window → no
    re-fetch). A promoted iteration node is written (`stage:"promote"`,
    `modelUsed`=`req.model`, `walkForwardResult` populated, insights present).
  - **Final best** is chosen by the existing `select_best`/`robust_score`
    over the **promoted (walk-forward-bearing) iterations only** — the cheap
    screen proxy never enters best-selection; screened-only candidates (no
    WF) are structurally not best-eligible (only promoted `RobustInputs` are
    appended to `completed`). J-09/J-16 robust-best invariant preserved;
    `select_best`/`robust_score` reused unchanged.

- **Carried iter-3 B1 fix.** New `_should_skip_insights(tracker)` /
  `_SPEND_CAPS = {"ai-tokens","usd","wall-clock"}`. In the stages that call
  insights (PROMOTE + the pinned path), the post-`generate` insights call is
  skipped **only** when `tracker.would_exceed()` is a true spend cap;
  **never** on the `"max-configs"` sentinel. The iteration node is still
  built/written and activity still recorded when insights is skipped. The
  sentinel distinction (the pinned-path `max_cfg == max_iter` trap from
  `_build_cost_tracker`, which makes the **final pinned iteration**'s
  `would_exceed()` return `"max-configs"`) is documented inline at
  `_SPEND_CAPS`/`_should_skip_insights` and at the gate site.

- **Hard budget under staging (J-13), staged `max_configs` semantics
  (documented inline in `_run_staged_open_universe`'s docstring).** A "config"
  counted against `max_configs` is one **PROMOTE** (expensive, full-pipeline)
  candidate — `tracker.start_config()` is called once per PROMOTE only.
  SCREEN is cheap by construction and bounded by the finite seed universe +
  the AI-token/USD/wall-clock caps, so it is **not** counted against
  `max_configs` (the point of cheap-first staging is to reserve the expensive
  budget for survivors). `tracker.would_exceed()` is checked at the top of
  **every** SCREEN candidate (token/USD/wall-clock gating) and **every**
  PROMOTE candidate (token/USD/wall-clock + max-configs). On any hard cap the
  run reaches the existing `budget-exhausted` terminal with **no further**
  screen/promote config appended (a hard cap during SCREEN also skips PROMOTE
  entirely). SCREEN generates and PROMOTE insights feed the **same**
  `record_usage` real-captured-token path.

- **SCREEN via the subprocess seam.** SCREEN backtests flow through the
  unchanged `_subprocess_backtest_executor` seam exactly like PROMOTE
  (iter-2 lesson: cheap in LLM/engine ≠ cheap in CPU; the GIL-holding
  next-bar engine must never run in-process). Guarded deterministically by
  `child_pid != os.getpid()` in tests — no timing bound.

- **Pinned path byte-unchanged behaviourally** (`_run_pinned`, extracted from
  the prior unified loop): exactly one config every iteration, the full
  pipeline every iteration, the prior-suggestion prompt-refinement chain, the
  same activity strings (`Automated iteration i/max`, `Backtest complete — …`),
  no `stage` key on pinned nodes, no SCREEN/PROMOTE entries. The only added
  behaviour is the B1 gate, a no-op unless a true spend cap is hit between
  generate and insights.

- **Frontend: no code change (verified, not skipped).** The existing activity
  feed renderer renders `auto-run`, `complete`, and `insights` entry
  `content` **verbatim** (`ActivityLogEntry.tsx` — no slice/flatten), and the
  collapsed `ActivityLogGroup` header shows the `complete` summary, which now
  carries the leading `SCREEN`/`PROMOTE` prefix. An operator can therefore
  distinguish the two stages in the existing feed with no new component. Per
  the plan's verify-first conditional, no frontend file was modified. See
  `docs/handoffs/goal-auto-money-printer-iter-4-frontend.md`.

## Files Changed

- `apps/backend/shared/model_catalog.py` — **+`cheapest_model()`** (table-resolved,
  not a literal). No pricing change.
- `apps/backend/backend/auto_session.py` — staged constants
  (`_SCREEN_SET_SIZE`, `_PROMOTE_TOP_K`, `_SPEND_CAPS`), `_should_skip_insights`
  (carried B1, inline sentinel doc), `_build_node` gains an optional additive
  `stage` field (omitted on pinned), shared `_evaluate_one` (generate-or-reuse
  → backtest → B1-gated insights → write node), `_read_stop_requested`,
  `_run_pinned` (extracted; behaviourally byte-unchanged + B1 gate),
  `_run_staged_open_universe` (SCREEN→rank→PROMOTE; staged `max_configs`
  semantics documented inline), `_run_auto_session_impl` reduced to
  setup → branch (open vs pinned) → shared terminal. `shared/contracts.py`,
  `sandbox.py`, `pipeline.py`, `backtest/` untouched.
- `apps/backend/tests/test_model_pricing.py` — +1 test
  (`cheapest_model` derived from `MODEL_PRICING`, not a literal).
- `apps/backend/tests/test_auto_session.py` — `FakePipeline` extended
  additively (`by_cfg` per-config behaviour map; `gen_models`/`insight_models`/
  `bt_wfv`/`bt_cfgs` per-call introspection — legacy positional `steps`
  behaviour byte-unchanged). New: `_stage_markers`/`_nodes_by_stage` helpers;
  `test_screen_stage_cheap_model_no_wf_no_insights` (TC-13),
  `test_screen_stage_failure_is_recorded_loop_continues` (TC-06/13 resilience),
  `test_promote_stage_reuses_screened_strategy_full_pipeline` (TC-14),
  `test_b1_true_spend_cap_between_generate_and_insights_skips_one` (positive
  B1). Consciously updated to staged form (NOT loosened): the augmented
  `test_pinned_path_unchanged_by_open_universe_addition`
  (+`assert pipe.insight_calls == 3` B1 regression guard),
  `test_open_universe_runs_multiple_distinct_configs`,
  `test_open_universe_best_is_robust_not_raw_return`,
  `test_max_configs_cap_stops_open_universe_no_post_cap_config`,
  `test_hard_token_budget_exhausted_real_usage_and_durable_spend`,
  `test_open_universe_multi_config_runs_in_subprocess_distinct_pids`.

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest`
Result: **188 passed, 1 failed**. The single failure is the pre-existing,
out-of-scope, baseline-documented
`test_directions_cache.py::test_write_and_read_full_round_trip` (iter-3
baseline was 183 passed / 1 failed → **+5 new passing, ZERO new
regressions**; the failed count stays exactly 1 and is the same test).

Targeted: `pytest tests/test_auto_session.py -q` → **41 passed**;
`pytest tests/test_model_pricing.py -q` → **6 passed**.

Lint: `.venv/bin/ruff check` on all 4 changed files → **All checks passed**
(no new lint errors).

Anti-goal source guards: `git diff HEAD -- shared/contracts.py
backend/sandbox.py backend/pipeline.py backend/backtest` is **empty**
(byte-unchanged). No new infra import (celery/redis/sqlalchemy/broker/
vector-store/external pricing dep) in the diff. No frontend file touched
(`npm run build` not required). No secrets in any new SCREEN/PROMOTE activity
entry or persisted artifact (covered by the existing
`test_no_secrets_written_into_artifacts` plus the staged content being only
symbol/timeframe/metrics).

Service startup: `import backend.api` boots clean; the full suite drives the
staged + pinned `run_auto_session` paths in-process and via `TestClient`.
No stray uvicorn/next/spawn-child processes left (the autouse fixture shuts
the reusable backtest child down each test).

## Known Issues

- **Live (real-LLM) J-14 verification is browser-qa's job** under the
  tiny-budget mandate (no symbol/timeframe, `objective:"robust"`, short
  window, cheap model, k small, lenient/absent targets → `budget-exhausted`).
  The real-LLM path requires `OPENAI_API_KEY` (pre-existing constraint,
  default model `gpt-5.4-mini`); the backend boots without it but
  generate/insights fail without a key. No new external system was
  introduced (no new dependency, no pricing API), so there is no new live
  integration to validate at the unit level; the SCREEN/PROMOTE split is
  unit-tested deterministically via the extended `FakePipeline`.
- **`modelUsed` on a promoted node is `req.model`** (the stronger model that
  ran the promote-stage insights/refinement). The strategy *code* was
  generated by the cheap SCREEN model and is reused verbatim (no
  re-generation). This is intentional and documented inline so `modelUsed`
  is not mis-read as "the code was regenerated by the stronger model" — it
  reflects the promote stage's representative (expensive) model, matching the
  spec's "the stronger model appears only on promoted".
- **A hard spend cap tripped mid-SCREEN skips PROMOTE entirely** → the run
  ends `budget-exhausted` with `bestIterationId` possibly `null` (no promoted
  WF-bearing candidate ran). This is the correct, spec-mandated "no further
  screen/promote config appended" behaviour for an extreme tiny cap; a normal
  tiny-budget QA run screens then promotes ≥1 before any cap.
- Pre-existing out-of-scope failure
  `test_directions_cache.py::test_write_and_read_full_round_trip` remains
  (untouched; the only tolerated failure per the spec baseline).

## Suggested Next Phase

**J-15** — global-history warm start: a cross-run, prompt-cached history
planner that prioritises historically strong families when ordering the
SCREEN seed set, with `history_scope` opt-out actually honoured (it is
accept-and-persist only today). Builds directly on this iteration's staged
controller (the screen-order enumeration is the natural injection point) and
the iter-3 durable file store (read-only mining, no schema fork). **J-16**
(deep overfit-gating stress demonstration / leaderboard) follows; the
robust-best invariant it relies on is already preserved here.
