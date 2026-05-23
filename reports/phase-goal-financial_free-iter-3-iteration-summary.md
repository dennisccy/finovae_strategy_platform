# Iteration Summary — goal-financial_free-iter-3

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-23
**Iteration:** 3

## In plain words

**What you can do now:** Describe a trading strategy in plain English and run it against real crypto price history; browse and reopen past runs with their full trades and results; stress-test a strategy across rolling out-of-sample windows; get ranked AI suggestions; choose from the available coins and timeframes; and re-run quickly from a warm cache. You can also kick off a hands-free automated strategy search, watch it work live, stop it from the screen, and reload the page without losing it — it keeps the most robust result and never runs past its budget.

**What changed this time:** You can now start an automated search that picks which coins and timeframes to try on its own — give it just a goal and a budget instead of a fixed setup, and it explores a few different combinations and keeps the best one. Every automated run is now held to a hard spending limit, and the status strip at the top of the results shows the AI usage and the dollar cost climbing live (each against its cap), plus how many setups it has explored so far.

**What's next:** Next, the search will try ideas cheaply first and spend the full, deeper effort only on the most promising ones.

## Headline

Open-universe search from one API call (objective + budget), bounded by a hard token/USD/configs cost budget.

## Direction

**Signal:** improving
**Why:** This iter landed J-12 (open-universe multi-config search via `_run_open_universe`, exploring ≥2 distinct configs from a bounded seed universe `SEED_UNIVERSE_MAX=4`) and J-13 (hard token/USD/`max_configs` budget enforced by `BudgetTracker.exceeded()`), both newly passing on real live-LLM backend runs plus a re-run hermetic suite (194 passed / 1 pre-existing red). Layer-1 (J-07–J-11) stayed green and J-01–J-06 showed no regression; coherence PASS, zero anti-goal violations. J-14/J-15/J-16 remain the failing Layer-2 targets, with J-14 (staged SCREEN→PROMOTE) recommended next — and the recurring J-08/J-10 live-pixel strip-chip debt must finally be cleared in that browser-QA window.

**Trend (last 4 iters):**
- Newly passing this iter: J-12, J-13
- Newly passing in last 4 iters total: J-07, J-08, J-09, J-10, J-11, J-12, J-13
- Regressions in last 4 iters: none
- Anti-goal violations in last 4 iters: none
- Iters with no journey state change: 0 of last 4

**Latest evaluator reasoning:** Layer-2 opens cleanly: J-12 (open-universe multi-config search from objective + budget) and J-13 (hard token/USD/`max_configs` budget) are both newly passing on real live-LLM backend runs plus a hermetic test suite re-run by the evaluator (194 passed / 1 pre-existing red / 1 deselected). The five Layer-1 journeys (J-07–J-11) remain green and J-01–J-06 show no regression; coherence is PASS and no anti-goal was violated (frozen `contracts.py` untouched, zero secrets, no new infra). Not GOAL_ACHIEVED — J-14, J-15, J-16 are still failing (Layer-2 incomplete).

## What was done

- **Open-universe search (J-12):** one API call carrying only `objective` + `budget` (no symbol/timeframe) now launches a server-side search that explores ≥2 distinct configs (e.g. `BTC/USDT 1h`, `ETH/USDT 1h`) from a bounded seed universe, each evaluated through the existing `BacktestPipeline` + `RobustScorer`, marking the single cross-config best (`_run_open_universe`).
- **Hard token/USD/max_configs budget (J-13):** `BudgetTracker.exceeded()` now hard-enforces tokens, USD, configs, and wall-clock, checked *before* each unit of work — never "one more"; the run finishes `budget-exhausted` when any cap is reached.
- **Real spend accounting:** SDK token usage captured via a side channel (script/insights generators → pipeline → `BudgetTracker.with_usage()`), mapped to USD by a new per-model rate table in `shared/model_catalog.py`; frozen `shared/contracts.py` left untouched.
- **Frontend (display-only):** `AutoSessionStatusStrip` gained live token / USD / configs counter chips read straight from `autoRun.budget`; the `AutoRunBudget` TS type was extended to mirror the backend `to_dict()`.
- **Invariants preserved:** the pinned J-07 path is byte-for-byte unchanged, the B1+B2 shared-lock invariant holds for the new loop, and OHLCV cache reuse + code-hash backtest dedup were added.
- **Verification:** functional QA passed 17/17 (J-12, J-13 newly passing on real live-LLM runs; J-07–J-11 + J-01–J-06 regressions green); the dedicated browser-QA SKIPPED (FE/BE down in its window) so interactive strip pixels remain owed — though one clean real-pixel app render was captured (J-05 pixel debt cleared).

## What's left

- Journey J-14 (Staged screening — full cost only on survivors) failing — deferred this iteration; `_create_iteration` was left as one reusable method so SCREEN/PROMOTE stages can wrap it without a rewrite.
- Journey J-15 (Learns from global history / warm start, opt-out-able) failing — deferred.
- Journey J-16 (Robust objective gates overfit — multi-candidate leaderboard) failing — the single WFE-gated best badge exists; the ranked overfit-gating board is deferred.
- Recurring live-pixel debt: the status-strip token/USD/configs chips live-updating and the J-10 reload-mid-run step (J-08/J-10) were not captured at the pixel layer (Chrome-MCP hidden-tab throttle + concurrent QA + browser-QA SKIP) — must be captured in the J-14 browser-QA window on an uncontended foreground tab.
- No UI control to trigger an open-universe run (API-only by design; the in-UI Auto Run stays pinned-config).
- Open-universe runs have no "targets met" early-stop (budget/stop only) and write no per-config insights (`insights:null`) — deferred to J-14.
- Non-blocking: pre-existing red `test_directions_cache`; flaky route timing test `test_post_returns_before_loop_completes_and_get_stays_responsive`; review NOTEs (`_backtest_cache_key` omits `initial_capital`/`commission`; `AutoSessionConfig.symbol/timeframe` typed `str` but `None` in open-universe).

## Next step

Continue Layer-2 at **full** depth with **J-14 (staged SCREEN→PROMOTE cost tiering + model routing)** — wrap the now-reusable `_create_iteration` per-config evaluation in a cheap `SCREEN` stage (no walk-forward, cheapest model) that promotes only the top-k survivors to full evaluation (walk-forward + stronger model), honoring the "SCREEN-skips-WF / strongest-model" anti-goal. The activity log must show the `SCREEN` candidates and the `PROMOTE` subset (k < screened). J-14 is the prerequisite for J-15 (global-history warm start, read-only, opt-out) and J-16 (multi-candidate overfit-gating leaderboard UI), which follow. **Clear the recurring live-pixel debt this time, decisively (J-08/J-10):** J-14 adds genuinely new UI (SCREEN/PROMOTE in the activity log), so browser-QA runs again — it MUST run against the same live services in the same window on an uncontended foreground tab and capture the strip token/USD/configs chips live-updating, config cards streaming without reload, and the reload-mid-run survival step. Non-blocking carry-forward: pre-existing red `test_directions_cache`, the flaky route timing test (de-flake the scaffold), and the two review NOTEs. Do NOT re-litigate the eager-load anti-goal (resolved iter-1) or the in-browser scorer/loop removal (done iter-2).

## Quick verify

From `reports/phase-goal-financial_free-iter-3-what-to-click.md`:

1. In a terminal, launch an open-universe run:
   ```bash
   curl -s -X POST http://localhost:8000/api/auto-sessions \
     -H 'Content-Type: application/json' \
     -d '{"objective":"robust","budget":{"max_configs":2,"max_tokens":50000,"max_usd":0.05,"max_wall_clock_seconds":120}}'
   ```
2. Open `http://localhost:3692` in your browser and select the session you just created.
3. Find the counter group on the right side of the strip (chips separated by `·`).
4. Watch the `tok` chip and the `$` chip for ~5–10 seconds without refreshing.
5. Watch the iteration list below the strip (still no manual refresh).

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-financial_free-iter-3.md |
| Dev handoff | — | docs/handoffs/goal-financial_free-iter-3-dev.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-financial_free-iter-3-review.md |
| Browser QA | SKIPPED | reports/phase-goal-financial_free-iter-3-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-financial_free-iter-3-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-financial_free-iter-3-user-visible-changes.md |
| What to click | — | reports/phase-goal-financial_free-iter-3-what-to-click.md |
| UI surface map | — | reports/phase-goal-financial_free-iter-3-ui-surface-map.md |
| UI test plan | — | reports/phase-goal-financial_free-iter-3-ui-test-plan.md |
| QA | PASS | reports/qa/goal-financial_free-iter-3-qa.md |
| Goal evaluation | CONTINUE | runs/goal-session-financial_free/iter-3/eval.md |
| Journey history | — | runs/goal-session-financial_free/state/journey-history.json |
