# Iteration Summary — goal-auto-money-printer-iter-3

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-19
**Iteration:** 3

## Headline

Headless open-universe strategy search (objective + budget only) plus a hard, immutable AI-token/USD cost budget.

## Direction

**Signal:** improving
**Why:** This iter landed the indivisible Optimizer-Foundation slice: J-12 (open-universe bounded-seed search from only an objective + budget) and J-13 (immutable AI-token/USD/max-configs/wall-clock cost tracker fed by real captured SDK usage) both moved failing → passing on browser + independently re-run unit suite + source-diff evidence. No prior journey (J-01–J-11) regressed and all ~14 activated anti-goals hold at source-diff level; the only open item is the tracked non-blocking B1 (bounded one-config LLM overshoot) carried forward to J-14. Each of the last four iters has moved journeys forward (now 13/16 passing), so direction is healthy.

**Trend (last 4 iters):**
- Newly passing this iter: J-12, J-13
- Newly passing in last 4 iters total: J-01, J-02, J-03, J-04, J-05, J-06 (iter-0 baseline), J-07, J-08, J-09 (iter-1), J-02 partial→passing (iter-1), J-10, J-11 (iter-2), J-12, J-13 (iter-3)
- Regressions in last 4 iters: none
- Anti-goal violations in last 4 iters: none (0)
- Iters with no journey state change: 0 of last 4

**Latest evaluator reasoning:** The indivisible Optimizer-Foundation slice landed and is genuinely implemented, not just summarized. J-12 (open-universe search from only an objective + budget) and J-13 (immutable hard AI-token/USD/max-configs/wall-clock cost tracker fed by real captured SDK usage, budget-exhausted terminal, durable + visible spend) both move failing → passing on multi-level evidence (live browser screenshots + independently re-run unit suite + source-diff). No prior passing journey regressed; all ~14 activated anti-goals hold at source-diff level. J-14/J-15/J-16 remain failing by design (explicitly OUT OF SCOPE this iteration).

## What was done

- Shipped headless open-universe strategy search — `POST /api/auto-sessions` with only an objective + budget (no symbol/timeframe) runs a deterministic bounded enumerator over a fixed 6-entry seed universe (BTC/ETH/SOL/BNB × 4h/1h), exploring ≥2 distinct configs rendered live in the existing iteration tree with the robust `BestBadge` (J-12).
- Added an immutable hard cost tracker (`backend/cost_tracker.py`) — frozen `CostCaps` fixed at run start, monotonic/append-only spend, independently enforcing AI-tokens / USD / max-configs / wall-clock plus the existing `max_iterations` clamp; hits a `budget-exhausted` terminal with no extra round/config past the cap (J-13).
- Captured real SDK token usage (`shared/llm_usage.py`) through the compiler / insights / script generators into the tracker, priced via a static per-model USD table in `shared/model_catalog.py` — actual tokens, never an estimate or constant; `shared/contracts.py`/sandbox/engine byte-unchanged.
- Surfaced spend in the existing `AutoRunBar` (`SessionContainer.tsx`): right-aligned `<tok> tok · $<usd> · <n> cfg` readout plus a distinct amber `budget-exhausted` state; durable across a hard browser reload. `useBacktest.ts` change is type-only.
- Post-QA round-1 fix (TC-07): persisted accepted `objective`/`history_scope` into the durable `autoRun` block so they survive restart/reload and appear in `GET /api/sessions/{id}`.
- Backend suite: 183 passed / 1 pre-existing out-of-scope fail (+33 net-new, zero new regressions); iter-3 targeted suites 59 passed; frontend build EXIT 0.
- Verified 2 target journeys (J-12, J-13) pass browser QA — 11/11 UI tests PASS, 0 skipped.

## What's left

- Journey J-14 (Staged screening — full cost only on survivors) failing — no SCREEN→PROMOTE stage; every explored config runs the full pipeline (out of scope this iter, by design; total cost still hard-bounded by J-13).
- Journey J-15 (Learns from global history / warm start, opt-out-able) failing — `history_scope` is persisted only; the controller is a deterministic enumerator with no cross-run learning or prompt-cached planner.
- Journey J-16 (Robust objective gates overfit — leaderboard demonstration) failing — the robust selector is reused as-is; no dedicated overfit-gating leaderboard UI.
- Tracked non-blocking B1: no spend-cap recheck between `generate` and `insights`, so a terminal config can complete one extra in-flight LLM call (bounded one-config overshoot; the load-bearing "no extra round/config past the cap" guarantee holds) — carry into J-14.
- Budget-cap headroom and wall-clock spend are captured/typed but not rendered in `AutoRunBar` (spec-scoped-out; documented "Not Visible Yet").
- Open-universe has no UI trigger control — API-only by explicit spec design (results are fully visible; not a gap).
- Pre-existing out-of-scope failure `test_directions_cache.py::test_write_and_read_full_round_trip` remains (the sole tolerated baseline failure).

## Next step

iter-4 at **full** depth — **J-14** (staged SCREEN→PROMOTE: a cheap SCREEN stage that does NOT run walk-forward or the strongest model; full pipeline only on the top-k promoted survivors), carrying the tracked **B1** fix: after the post-`generate` `_drain_usage`, skip the `insights` call (still record the iteration) only when `would_exceed() in {"ai-tokens","usd","wall-clock"}` — **never** on `"max-configs"` (which on the pinned path equals `max_iter`, so a naive skip would silently suppress the final pinned iteration's insights — a J-07–J-11 regression no current test guards). Add an `insight_calls`-on-final-pinned-iteration assertion to `test_pinned_path_unchanged_by_open_universe_addition` alongside that fix. J-15 (global-history warm start + prompt-cached planner + `history_scope` learning) and J-16 (deep overfit-gating leaderboard demonstration) follow.

## Quick verify

From `reports/phase-goal-auto-money-printer-iter-3-what-to-click.md`:

1. In a terminal, start **two** headless runs back-to-back (Run A: `objective:"robust"` + `max_iterations:2,max_configs:2`; Run B: tiny token/USD budget `max_ai_tokens:1,max_usd:0.0001`) via `POST http://localhost:8691/api/auto-sessions`.
2. Open `http://localhost:3691`, click the **"Sessions"** button (clock icon, top of page), then under **"Live Sessions"** click the row **`Auto: momentum breakout`**.
3. Watch the left iteration list fill in for up to ~2 minutes (do **not** reload — it auto-updates); read each iteration card's config line (`<symbol> · <timeframe> · <dates> · $<capital>`).
4. Look at the far-right end of the blue/colored strip while it runs, then wait ~6 seconds and look again.
5. Wait until the strip stops spinning (terminal), then scan the iteration cards.

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-auto-money-printer-iter-3.md |
| Dev handoff | — | docs/handoffs/goal-auto-money-printer-iter-3-dev.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-auto-money-printer-iter-3-review.md |
| Browser QA | PASS | reports/phase-goal-auto-money-printer-iter-3-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-auto-money-printer-iter-3-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-auto-money-printer-iter-3-user-visible-changes.md |
| What to click | — | reports/phase-goal-auto-money-printer-iter-3-what-to-click.md |
| UI surface map | — | reports/phase-goal-auto-money-printer-iter-3-ui-surface-map.md |
| UI test plan | — | reports/phase-goal-auto-money-printer-iter-3-ui-test-plan.md |
| UX regression | UX-REGRESSION-PASS | reports/phase-goal-auto-money-printer-iter-3-ux-regression.md |
| QA | PASS | reports/qa/goal-auto-money-printer-iter-3-qa.md |
| Audit | PASS_WITH_GAPS | docs/handoffs/goal-auto-money-printer-iter-3-audit.md |
| Closure | CLOSURE-PASS | reports/phase-goal-auto-money-printer-iter-3-closure-verdict.md |
| Goal evaluation | CONTINUE | runs/goal-session-auto-money-printer/iter-3/eval.md |
| Journey history | — | runs/goal-session-auto-money-printer/state/journey-history.json |
