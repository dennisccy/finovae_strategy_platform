# Iteration Summary — goal-financial_free-iter-0

**Verdict:** CONTINUE
**Iteration type:** goal-lean
**Date:** 2026-05-23
**Iteration:** 0

## In plain words

**What you can do now:** Describe a trading strategy in plain English and run it against real crypto price history, then read back the full result — returns, an account-value chart, and every trade. Browse your past runs and reopen any one to see its strategy and results. Stress-test a strategy across rolling time windows to check it holds up on data it wasn't tuned on. Ask for ranked AI suggestions to improve it. Pick from the available coins and timeframes. And re-run the same test quickly without re-downloading data.

**What changed this time:** Behind-the-scenes work — nothing visibly new this round. This round was a stock-take: we confirmed which abilities already work and mapped out exactly what's left to build.

**What's next:** Next we'll let you start a hands-free, budget-capped strategy search from a single command and watch it work right inside the app.

## Headline

Verify-only baseline: 6 of 16 must-have journeys already pass; the 10 automated-session journeys are unbuilt.

## Direction

**Signal:** improving
**Why:** Baseline iter-0 made zero code changes; it confirmed J-01…J-06 already pass functionally against the live backend (newly recorded green in this session's history — `last_passing_iter` null→iter-0) and identified J-07…J-16 as net-new scope failing-by-absence (`POST /api/auto-sessions` → 404, no auto/optimizer routes in OpenAPI). No regressions and no anti-goal violations were introduced, and the evaluator set a clear Layer-1-first roadmap (CONTINUE, full depth next), so the direction toward the goal is positive even though nothing was built this round.

**Trend (last 1 iter):**
- Newly passing this iter: J-01, J-02, J-03, J-04, J-05, J-06 (status `already_passing` — pre-existing implementation, confirmed at baseline)
- Newly passing in last 1 iter total: J-01, J-02, J-03, J-04, J-05, J-06
- Regressions in last 1 iter: none
- Anti-goal violations in last 1 iter: none (one pre-existing eager-load signal — ~245KB `GET /api/sessions/{id}` open payload embeds `equity_curve` — recorded for a future coherence verdict, not attributed to iter-0)
- Iters with no journey state change: 0 of last 1

**Latest evaluator reasoning:** Clean verify-only baseline (zero code changes — `git diff HEAD` and `--cached` both empty). The six manual journeys J-01…J-06 are already implemented and functionally verified against the live backend (marked `already_passing`); the ten automated-session journeys J-07…J-16 fail-by-absence — `POST /api/auto-sessions` returns 404 and no auto/optimizer routes exist, confirming net-new scope. This is the expected, useful baseline (separates "done" from "to build"); it is not a regression and not goal-achieved.

## What was done

- Made zero code changes — verify-only baseline confirmed (`git diff HEAD` and `--cached` both empty against `cd6cae7`); only pipeline artifacts (dev handoff, status.json) were written.
- Confirmed the backend boots and serves `/docs` (HTTP 200) on this session's stack (backend `:8692`, frontend `:3692`).
- Re-verified the six manual journeys (J-01…J-06) functionally against the live backend endpoints the UI calls: NL→backtest (143 trades, +5.97%, run_id `db758f99`), lazy run-history detail, 8-window walk-forward (wfe=0.4218, yellow), 10 OOS-aware AI suggestions, 26 symbols / 6 timeframes, warm re-run 10.2s vs 43.5s cold.
- Probed the automated-session API first (cost discipline): `POST /api/auto-sessions` and `/{id}/stop` → 404, no `auto`-prefixed routes in OpenAPI → J-07…J-16 confirmed net-new (fail-by-absence).
- Ran the backend unit suite: 124 passed, 1 failed (only the nice-to-have directions cache); anti-goal invariants (`test_lookahead`, `test_determinism`, `test_sandbox`) all pass.
- Spot-checked observable anti-goal signals: non-`/tmp` store default (`<repo>/.data/backtests`), single-Parquet OHLCV cache, no SQLite/DB; recorded one pre-existing eager-load signal (~245KB session-open payload embeds `equity_curve`) for a future coherence verdict.
- Verified 6 of 16 target journeys pass browser QA (6 already-passing; 10 fail-by-absence).

## What's left

- Journey J-07 (Start a headless automated session via the API) — failing; trigger endpoint absent (`POST /api/auto-sessions` → 404), net-new scope.
- Journey J-08 (Track the automated run live in the UI) — failing; no backend run to track.
- Journey J-09 (Automated chain stops on robust target or budget; best is marked) — failing; no controller / stop-reason / best-marking surface.
- Journey J-10 (Backend is the single source of truth; survives reload) — failing; "Auto Run" is in-browser today (`useBacktest.ts`, `IterationCard.tsx`), no backend loop.
- Journey J-11 (Stop a running automated session) — failing; `POST /api/auto-sessions/{id}/stop` → 404.
- Journey J-12 (Open-universe run from only an objective + budget) — failing; strict superset of the absent Layer-1 endpoint.
- Journey J-13 (AI-token/cost budget is hard-enforced) — failing; no budget cost-tracker surface.
- Journey J-14 (Staged screening — full cost only on survivors) — failing; no SCREEN/PROMOTE staging surface.
- Journey J-15 (Learns from global history; opt-out-able) — failing; no planner / history-scope surface.
- Journey J-16 (Robust objective gates overfit) — failing; no leaderboard / robust-selection surface.

## Next step

Begin Layer-1 Foundation (J-07…J-11) — the headless, backend-driven automated session — at full depth. The first feature iteration should establish the core backend auto-session loop and its endpoints, reusing the existing `BacktestPipeline` (no sandbox/engine bypass): `POST /api/auto-sessions` (start, pinned config first) and `POST /api/auto-sessions/{id}/stop` to unblock J-07 and J-11; a backend iterate loop that writes the same session/iteration/activity/suggestion artifacts the UI already renders — no parallel store, no schema fork — to unblock J-08 (live tracking) and J-09 (terminal + stop-reason + best-marking); a durable `autoRun` status persisted to the file store that survives a worker restart and browser reload, with the in-browser Auto Run rewired to the backend loop (J-10); and an immutable hard budget/cost tracker (tokens/USD + max-configs + wall-clock) from the start. Land Layer-1 green before Layer-2 (J-12…J-16). Carry forward (neither blocks the next iteration): a definitive coherence verdict on the ~245KB `GET /api/sessions/{id}` open payload that embeds `equity_curve`, and an opportunistic fix of the red `test_directions_cache` (nice-to-have, outside the Must-have journey set).

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-financial_free-iter-0.md |
| Dev handoff | — | docs/handoffs/goal-financial_free-iter-0-dev.md |
| Review | PASS | reports/reviews/goal-financial_free-iter-0-review.md |
| Browser QA | FAIL | reports/phase-goal-financial_free-iter-0-ui-test-results.md |
| Goal evaluation | CONTINUE | runs/goal-session-financial_free/iter-0/eval.md |
| Journey history | — | runs/goal-session-financial_free/state/journey-history.json |
