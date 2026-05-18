# Iteration 1 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** lean

## Summary

The two pinned storage anti-goals are genuinely resolved: OHLCV is now a single
Parquet file per `(symbol, timeframe)` with a deterministic zero-refetch
covering-cache and atomic write, and `session_store.BASE_DIR` defaults to an
absolute, non-`/tmp`, durable in-repo path that lands on the existing live
session store. All five DoD journeys (J-01/J-06 targets; J-02/J-03/J-04
must-pass) were verified passing through the running UI with genuine screenshot
evidence and reproduced pytest counts; determinism/no-lookahead invariants pass
unchanged. Not GOAL_ACHIEVED because J-05 remains failing (explicitly out of
scope this iter) and the eager-load anti-goal is still unresolved (now
code-confirmed, deferred); no journey regressed and no new anti-goal was
introduced.

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run a backtest from NL (target) | already_passing | **passing** | reports/qa/goal-money-billions-iter-1-evidence/TC-15-02-results.png (+12.08% / 20 trades / 70% / 0.91; equity curve; new run_id) |
| J-02 Inspect & browse run history (must-pass) | already_passing | **passing** | TC-17-03-loaded.png + UT-04-prior-run-detail.png + UT-10-result.png (prior session reloaded from durable store; survives browser refresh) |
| J-03 Walk-forward validation (must-pass) | already_passing | **passing** | TC-18-01-walkforward.png (WFE 0.53 ✓ green; OOS row; per-window table; combined OOS curve) |
| J-04 AI insights (must-pass) | already_passing | **passing** | TC-19-01-insights.png + UT-07-insights.png (narrative + 20–28 ranked suggestions). OOS-aware sub-clause still unconfirmed (carried soft gap) |
| J-05 Reference data loads | failing | **failing** (not tested — out of scope) | carried from iter-0; `BacktestConfigBar.tsx` still hardcodes timeframe / free-text symbol |
| J-06 Warm-cache re-run (target) | already_passing | **passing** | TC-16-02-rerun-result.png + UT-03-rerun-detail.png (byte-identical warm re-run; both runs in history) |

## Anti-goal Check

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| Single Parquet per (symbol,tf); no per-day fan-out; no refetch on covering cache | **RESOLVED** | `loader.py` writes `{cache}/{symbol}/{tf}.parquet`; per-day CSV helpers + day loop removed; `clear_cache()` globs `*.parquet`; covering-cache → zero Binance calls; verified by git diff + pytest TC-01..TC-07 + on-disk (`BTC_USDT/1h.parquet`, 0 new `.csv`) |
| `BACKTEST_STORE_DIR` must not default to volatile `/tmp`; history survives restart | **RESOLVED** | `_DEFAULT_STORE_DIR = Path(__file__).resolve().parents[3]/.data/backtests`; absolute, not `/tmp`; auditor independently confirmed via `git rev-parse` it lands on the 18 existing live sessions; pytest TC-08/TC-09 PASS |
| No nondeterministic backtests (seeded slippage; identical inputs→identical output) | OK (held) | `_postprocess` applies dedupe→sort→strict-filter on cold & warm; `test_determinism.py` 6/6, `test_cold_equals_warm_equivalence` PASS; 3 live byte-identical runs |
| No lookahead | OK (held) | `test_lookahead.py` 6/6 unchanged; source byte-identical to HEAD |
| No SQLite/relational DB | OK (held) | Parquet + file store only (code review) |
| `GET /api/sessions/{id}` must not eagerly parse per-iteration result/rating | **UNRESOLVED (deferred, not introduced)** | iter-0 UNCONFIRMED SIGNAL is now CODE-CONFIRMED: `session_routes.py:142-171` `get_session` calls `read_iteration_full` per iteration. Pre-existing, NOT introduced here; explicitly OUT OF SCOPE; severity minor; needs its own full-depth iteration |
| Hard-coded credentials / keys in source | OK | none added; `.env.example` keys commented out with absolute-path guidance (auditor B3 fix) |
| Frozen `shared/contracts.py` not mutated | OK | not touched |

No new anti-goal violation introduced this iteration. Two pre-existing pinned
violations resolved; one (eager-load) confirmed and deferred.

## Next-Step Recommendation

**Next (lean): close J-05** — the only remaining failing Must-have journey and
the critical path to GOAL_ACHIEVED. Wire `apps/frontend/src/components/BacktestConfigBar.tsx`
to fetch `/api/symbols` and `/api/timeframes` and populate the symbol/timeframe
controls from them (replace the hardcoded timeframe literal and free-text symbol
input). Both endpoints are already healthy (confirmed iter-0). Small, isolated,
low-risk frontend change → **lean** depth.

**Subsequent (full): resolve the last anti-goal** — the now-code-confirmed
`GET /api/sessions/{id}` eager-load (`session_routes.py:142-171`). It is a
frontend+backend session-open contract change with J-02 regression risk and
warrants its own dedicated **full**-depth iteration. GOAL_ACHIEVED is blocked
until both J-05 passes and this anti-goal is resolved.

**Soft gap to retire before GOAL_ACHIEVED:** J-04's conditional sub-clause
("suggestions are OOS-aware when walk-forward data exists") is still not
separately asserted; fold an explicit post-walk-forward-insights OOS-awareness
check into the eager-load full iteration's QA.

## Halt Justification (if halting)

Not halting. Progress was real (two pinned anti-goals resolved, all five DoD
journeys re-verified through the migrated storage layer), no regression, and a
clear tractable next step exists (J-05). CONTINUE.
