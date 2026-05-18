## Iteration 0 — goal-money-billions-iter-0

**Date:** 2026-05-18T00:35:26Z
**Verdict:** CONTINUE
**Depth dispatched:** lean
**Depth recommendation (next):** full
**Journey deltas:**
- Newly passing: none (baseline iteration — no prior state)
- Already passing (baseline): J-01, J-02, J-03, J-04, J-06
- Newly failing: J-05 (failing — baseline)
- Regressed: none (no prior journey state to regress from; journey-history was empty)
- Anti-goal violations: per-day CSV OHLCV cache vs single-Parquet (minor, pre-existing); BACKTEST_STORE_DIR `/tmp` code default (minor, pre-existing, runtime durable via .env); eager-load on `/api/sessions/{id}` (minor, UNCONFIRMED signal — needs full-mode QA)

**Reasoning:** Baseline correctly separated already-working from to-build. All six journey screenshots independently verified: J-01/02/03/04/06 visibly pass (backtest metrics + equity curve + run history; WFE 1.26 green badge + per-window table + combined OOS curve; 10 ranked insight chips; warm re-run with 2 runs in history). J-05 fails its literal acceptance — `/api/symbols` & `/api/timeframes` are healthy but `BacktestConfigBar.tsx` never calls them (hardcoded timeframe literal, free-text symbol input). The anti-goal divergences (per-day CSV cache, `/tmp` store default) are PRE-EXISTING baseline state, NOT introduced (verify-only, zero code changes), and none are critical by the severity taxonomy (no secrets/paid-SaaS/license/backdoor) → not REGRESSION. Clear tractable next work exists → not STALLED. Expected baseline outcome → CONTINUE.

**Next-step recommendation:** Two tractable workstreams. (1) J-05: wire `BacktestConfigBar.tsx` to fetch `/api/symbols` + `/api/timeframes` and populate the symbol/timeframe controls from them (small frontend change). (2) Storage anti-goals (highest-value, aligns with the known pending Parquet migration): migrate `data/loader.py` from per-day CSV under `/tmp` to a single Parquet file per (symbol, timeframe); change `session_store.py:26` `BACKTEST_STORE_DIR` default off volatile `/tmp` to a durable in-repo path. The storage change is architecture-level with regression risk to already-passing J-01/J-06 and multiple anti-goal invariants (determinism, no-lookahead, warm-load ≥10×) → recommend `full` depth for the next iteration. A later full-mode iteration should also (a) confirm/deny the `/api/sessions/{id}` eager-load signal against `session_routes.py`, and (b) verify the J-04 OOS-aware sub-clause via post-walk-forward insights regeneration.
