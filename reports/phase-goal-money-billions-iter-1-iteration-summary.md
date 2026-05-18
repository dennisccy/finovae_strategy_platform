# Iteration Summary — goal-money-billions-iter-1

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-18
**Iteration:** 1

## Headline

Single-file Parquet OHLCV cache + durable-by-default session store; both pinned storage anti-goals resolved.

## Direction

**Signal:** improving
**Why:** This iter resolved 2 of the 3 pinned storage anti-goals — single-Parquet-per-(symbol,tf) OHLCV cache and a durable, non-`/tmp` `BACKTEST_STORE_DIR` default — which are the explicit reason this goal session exists, and re-verified all five in-scope DoD journeys (J-01/J-02/J-03/J-04/J-06) green through the migrated storage layer with determinism preserved and zero regression. No journey flipped status because the in-scope journeys were already passing at baseline and J-05 (the only failing Must-have) was deliberately out of scope and deferred to a lean next iter. Direction is clearly toward GOAL_ACHIEVED; remaining blockers are J-05 and the still-open minor `GET /api/sessions/{id}` eager-load anti-goal.

**Trend (last 2 iters):**
- Newly passing this iter: none (J-01/J-02/J-03/J-04/J-06 re-verified passing through the migrated storage layer — already passing at baseline; no failing→passing flip)
- Newly passing in last 2 iters total: none (J-01/J-02/J-03/J-04/J-06 baseline-passing since iter-0; J-05 has never passed)
- Regressions in last 2 iters: none
- Anti-goal violations in last 2 iters: 3 total, all minor — 2 pre-existing pinned (single-Parquet OHLCV; durable `BACKTEST_STORE_DIR`) RESOLVED in iter-1; 1 (`GET /api/sessions/{id}` eager-load) code-confirmed iter-1, deferred, NOT introduced here
- Iters with no journey state change: 2 of 2 (no journey status flipped; iter-1's progress was resolving 2 pinned anti-goals, not a journey change)

**Latest evaluator reasoning:** The two pinned storage anti-goals are genuinely resolved: OHLCV is now a single Parquet file per `(symbol, timeframe)` with a deterministic zero-refetch covering-cache and atomic write, and `session_store.BASE_DIR` defaults to an absolute, non-`/tmp`, durable in-repo path that lands on the existing live session store. All five DoD journeys (J-01/J-06 targets; J-02/J-03/J-04 must-pass) were verified passing through the running UI with genuine screenshot evidence and reproduced pytest counts; determinism/no-lookahead invariants pass unchanged. Not GOAL_ACHIEVED because J-05 remains failing (explicitly out of scope this iter) and the eager-load anti-goal is still unresolved (now code-confirmed, deferred); no journey regressed and no new anti-goal was introduced.

## What was done

- Replaced the per-day CSV OHLCV cache with a single Parquet file per `(symbol, timeframe)`; a repeat backtest now reads entirely from that local file with zero Binance re-fetch (~23× faster, measured live) (`apps/backend/data/loader.py`).
- Added smart partial top-up: widening a date range fetches only the genuinely missing leading/trailing portion and merges it into the existing file (no whole-window refetch).
- Made cache writes crash-safe — `tempfile.mkstemp` + `os.replace()` atomic write, never observable half-written, safe under concurrent runs and the `Semaphore(1)` backtest gate; corrupt/legacy file → cache miss (re-fetch, no crash).
- Defaulted session/run history off volatile `/tmp` to a durable in-project path resolved from `__file__`, so history survives a server restart even with no `.env` (lands on the same path as the 18 existing live sessions — none orphaned) (`apps/backend/backend/session_store.py`).
- Fixed `clear_cache()` (had silently become a `*.csv` no-op; now removes `*.parquet` and reports the count), removed dead per-day helpers/imports, and corrected the stale `apps/backend/CLAUDE.md` data-caching doc.
- Added `tests/test_loader.py` (9 tests) and `tests/test_session_store.py` (3 tests); determinism 6/6 + lookahead 6/6 unchanged; full suite 119 passed / 1 pre-existing baseline failure; `.env.example` moved off `/tmp` (audit commented the override keys out).
- Verified all 5 in-scope DoD journeys (J-01, J-02, J-03, J-04, J-06) pass browser QA — 10/11 UI tests PASS, 1 SKIPPED for environment-safety, 0 FAIL; both targeted storage anti-goals resolved.

## What's left

- Journey J-05 (Reference data loads) failing — `apps/frontend/src/components/BacktestConfigBar.tsx` still hardcodes the timeframe list and uses a free-text symbol input; it never calls the healthy `/api/symbols` & `/api/timeframes`. Only remaining failing Must-have; explicitly out of scope this iter; the critical path to GOAL_ACHIEVED.
- Anti-goal still open (blocks GOAL_ACHIEVED): `GET /api/sessions/{id}` eager-load (`session_routes.py:142-171` calls `read_iteration_full` per iteration) — now code-confirmed, minor, pre-existing (NOT introduced here), deferred to its own dedicated full-depth iteration.
- Soft gap carried (must retire before GOAL_ACHIEVED): J-04's conditional sub-clause "suggestions are OOS-aware when walk-forward data exists" is still not separately asserted; fold an explicit post-walk-forward OOS-awareness check into the eager-load iteration's QA.
- Verification-method gap (non-blocking): UT-05 (literal backend restart with `BACKTEST_STORE_DIR` unset, through the UI) was SKIPPED for environment-safety; the exact behavior is gated by passing pytest TC-08/TC-09 plus auditor `git rev-parse` confirmation and UT-10 corroboration. A future CI/UI harness that can exercise the literal process restart would close this.
- Pre-existing baseline test failure carried (not a regression): `test_directions_cache.py::test_write_and_read_full_round_trip` (byte-identical to HEAD, iter-0 baseline, out of scope). Track for a future directions-focused iteration.
- Runtime `.env` on a given machine may still point `MARKET_DATA_CACHE_DIR` at `/tmp` (developer-managed, gitignored, out of scope to commit); the pinned OHLCV anti-goal is satisfied by cache *structure* regardless of directory. Legacy `/tmp` per-day CSVs are intentionally not migrated.

## Next step

**Next (lean): close J-05** — the only remaining failing Must-have journey and the critical path to GOAL_ACHIEVED. Wire `apps/frontend/src/components/BacktestConfigBar.tsx` to fetch `/api/symbols` and `/api/timeframes` and populate the symbol/timeframe controls from them (replace the hardcoded timeframe literal and free-text symbol input). Both endpoints are already healthy (confirmed iter-0). Small, isolated, low-risk frontend change → **lean** depth.

**Subsequent (full): resolve the last anti-goal** — the now-code-confirmed `GET /api/sessions/{id}` eager-load (`session_routes.py:142-171`). It is a frontend+backend session-open contract change with J-02 regression risk and warrants its own dedicated **full**-depth iteration. GOAL_ACHIEVED is blocked until both J-05 passes and this anti-goal is resolved.

**Soft gap to retire before GOAL_ACHIEVED:** J-04's conditional sub-clause ("suggestions are OOS-aware when walk-forward data exists") is still not separately asserted; fold an explicit post-walk-forward-insights OOS-awareness check into the eager-load full iteration's QA.

## Quick verify

From `reports/phase-goal-money-billions-iter-1-what-to-click.md`:

1. Open `http://localhost:3691` in your browser
2. In the config bar set: **Symbol** = `BTC/USDT`, **Timeframe** = click `1h`, **Start** = `2023-01-01`, **End** = `2023-06-01`, **Capital** = `1500`
3. Click the **"Describe a trading strategy…"** box, type `Buy when RSI crosses below 30, sell when RSI crosses above 70`, then press **Enter** (or click the paper-plane send icon to the right of the box)
4. Click the completed iteration card in the right panel
5. Click the back arrow (top-left), then on the latest iteration card click **"Rerun"** (circular-arrow icon / "Rerun")

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-money-billions-iter-1.md |
| Dev handoff | — | docs/handoffs/goal-money-billions-iter-1-dev.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-money-billions-iter-1-review.md |
| Browser QA | PASS (10/11, 1 SKIPPED, 0 FAIL) | reports/phase-goal-money-billions-iter-1-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-money-billions-iter-1-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-money-billions-iter-1-user-visible-changes.md |
| What to click | — | reports/phase-goal-money-billions-iter-1-what-to-click.md |
| UI surface map | — | reports/phase-goal-money-billions-iter-1-ui-surface-map.md |
| UI test plan | — | reports/phase-goal-money-billions-iter-1-ui-test-plan.md |
| UX regression | UX-REGRESSION-PASS | reports/phase-goal-money-billions-iter-1-ux-regression.md |
| QA | PASS | reports/qa/goal-money-billions-iter-1-qa.md |
| Audit | PASS | docs/handoffs/goal-money-billions-iter-1-audit.md |
| Closure | CLOSURE-PASS | reports/phase-goal-money-billions-iter-1-closure-verdict.md |
| Goal evaluation | CONTINUE | runs/goal-session-money-billions/iter-1/eval.md |
| Journey history | — | runs/goal-session-money-billions/state/journey-history.json |
