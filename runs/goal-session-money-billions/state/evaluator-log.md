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

## Iteration 1 — goal-money-billions-iter-1

**Date:** 2026-05-18T03:11:15Z
**Verdict:** CONTINUE
**Depth dispatched:** full
**Depth recommendation (next):** lean
**Journey deltas:**
- Newly passing (verified, was already_passing baseline): J-01, J-02, J-03, J-04, J-06
- Newly failing: none
- Regressed: none
- Still failing (out of scope this iter, carried): J-05
- Anti-goal violations: TWO RESOLVED (single-Parquet OHLCV cache; durable BACKTEST_STORE_DIR default). One CODE-CONFIRMED + deferred (GET /api/sessions/{id} eager-load, session_routes.py:142-171, minor, pre-existing, NOT introduced here). Zero new violations introduced.

**Reasoning:** The two pinned storage anti-goals that are the explicit reason this goal session exists are genuinely resolved — verified by reading the git diff (per-day CSV helpers + day loop deleted; single `{symbol}/{tf}.parquet`; covering-cache zero-refetch; atomic os.replace; `_DEFAULT_STORE_DIR` from `__file__`, absolute, not `/tmp`), reproduced pytest counts (TC-01..TC-09), on-disk state (one `BTC_USDT/1h.parquet`, zero new `.csv`), and the auditor's independent `git rev-parse` confirmation the store default lands on the 18 existing live sessions (no orphaning). All five DoD journeys verified passing through the running UI with genuine screenshot evidence (TC-15/16/17/18/19 + UT-02/03/04/06/07/10); cold/warm metrics byte-identical (12.08%/20/0.91 across runs) confirming determinism survived the Parquet round-trip; `test_determinism.py`/`test_lookahead.py` 6/6 each unchanged. The only suite failure is the independently-confirmed pre-existing `test_directions_cache.py` iter-0 baseline (byte-identical to HEAD, out of scope) — not a regression. No journey regressed and no critical/new anti-goal was introduced → not REGRESSION. J-05 (only remaining failing Must-have) was explicitly OUT OF SCOPE this iter and has clear tractable next work → not STALLED. Not all six journeys pass (J-05 failing) and anti-goal #3 (eager-load) is still unresolved → not GOAL_ACHIEVED. Real progress + tractable failing journey remain → CONTINUE.

**Next-step recommendation:** (1) NEXT, lean: close J-05 — wire `apps/frontend/src/components/BacktestConfigBar.tsx` to fetch `/api/symbols` + `/api/timeframes` and populate the symbol/timeframe controls (replace hardcoded timeframe literal + free-text symbol). Small, isolated, low-risk; both endpoints already healthy. This is the critical path to GOAL_ACHIEVED. (2) SUBSEQUENT, full: resolve the last anti-goal — `GET /api/sessions/{id}` eager-load (`session_routes.py:142-171`), a frontend+backend session-open contract change with J-02 regression risk; fold an explicit J-04 OOS-aware-insights post-walk-forward assertion into that iteration's QA. GOAL_ACHIEVED is blocked until both J-05 passes and the eager-load anti-goal is resolved.
