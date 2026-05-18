# Iteration 0 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

Baseline assessment for goal session `money-billions`, done as designed: verify-only,
zero code changes (dev handoff + empty `git diff` + reviewer PASS confirm). All six
Must-have journey screenshots were independently inspected. 5/6 journeys are
**already passing** on the current codebase (J-01, J-02, J-03, J-04, J-06); **J-05
fails** its literal acceptance (reference-data endpoints are healthy but the UI never
calls them). Pre-existing anti-goal divergences (per-day CSV OHLCV cache, `/tmp`
store code default) were surfaced exactly as the baseline is meant to surface them —
none are critical and none were introduced this iteration, so the loop continues.

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run a backtest from natural language | (none — baseline) | already_passing | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-01-result.png` |
| J-02 Inspect and browse run history | (none — baseline) | already_passing | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-02-result.png` |
| J-03 Walk-forward validation | (none — baseline) | already_passing | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-03-result.png` |
| J-04 AI insights | (none — baseline) | already_passing (primary acceptance; OOS-aware sub-clause untested) | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-04-result.png` |
| J-05 Reference data loads | (none — baseline) | **failing** | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-05-result.png` |
| J-06 Warm-cache re-run works end-to-end | (none — baseline) | already_passing (functional only) | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-06-result.png` |

Screenshot verification (skeptical, not trusting summaries):
- **J-01**: result panel shows "BTC 1H RSI Mean Reversion" −36.07% / 115 trades / 57% win / −1.21 Sharpe, equity curve, Strategy Script, VS BENCHMARK −191.69%, run in history. Confirmed.
- **J-02**: iterations list shows 2 distinct runs; detail view reloaded run 1 with spec + params (BTC/USDT·1h·2023-01-01–2023-12-31·$10,000) + metrics + trades. Confirmed.
- **J-03**: green **WFE 1.26 ✓** badge, per-window table (Window 1 IS 2023-01-01–07-01 / OOS 07-01–10-01), OOS tiles (−7.22% / −1.02 / 62.1% / −16.12%), combined OOS equity curve. Confirmed; badge color logic correct (1.26 ≥ 0.5 → green).
- **J-04**: summary paragraph + 10 ranked actionable suggestion chips. Primary acceptance met. The "OOS-aware when WF data exists" sub-clause was not separately verified (insights generated before the J-03 run) — flagged for a future check, not a baseline failure.
- **J-05**: Symbol = free-text `<input>` ("BNB/USDT"); Timeframe = 6 hardcoded buttons. Endpoints return 26 symbols / 6 timeframes but are orphaned. Literal acceptance ("`/api/symbols` and `/api/timeframes` populate the controls") **not met**.
- **J-06**: 2nd identical run "BTC 1H RSI Cross Mean Reversion" completed without error (−5.31% / 23 trades), both runs in history. Functional warm re-run confirmed (independent of the unmet single-Parquet anti-goal).

## Anti-goal Check

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| No hard-coded credentials/keys in source | OK | Keys in git-ignored `apps/backend/.env`; clean git tree. |
| Sandbox blocks file I/O / net / exec / `__import__` / open / os | OK | `tests/test_sandbox.py` PASS in the 107/1 suite. |
| No lookahead | OK | `tests/test_lookahead.py` PASS. |
| No nondeterministic backtests | OK | `tests/test_determinism.py` PASS. (LLM recompilation variance ≠ backtest determinism — not a violation.) |
| No paid SaaS beyond Anthropic/OpenAI | OK | None added. |
| `shared/contracts.py` frozen dataclasses not mutated | OK | No code changes this iteration. |
| OHLCV = single Parquet per (symbol, timeframe), no per-day fan-out, no re-fetch on covering cache | **VIOLATED (minor, pre-existing)** | `data/loader.py:50-63` writes per-day CSV under `MARKET_DATA_CACHE_DIR`(default `/tmp`); ~29,182 `.csv`, 0 `.parquet` on disk. Not introduced here (verify-only). Top-priority fix for `Mode:next`. |
| `BACKTEST_STORE_DIR` not a volatile `/tmp` default; history survives restart | **VIOLATED (minor, pre-existing)** | `session_store.py:26` default `/tmp/backtests`. Runtime durable only via `apps/backend/.env` override → `.data/backtests`. Code default still contradicts the text. |
| No relational DB / SQLite | OK | No `.db`/`.sqlite*` found. |
| `GET /api/sessions/{id}` must not eagerly parse full per-iteration `result`/`rating` | **UNCONFIRMED SIGNAL (minor)** | browser-QA saw full inline `result`+`rating` in the session payload, but explicitly not a definitive determination. Needs full-mode QA against `session_routes.py`. |

No anti-goal violation is **critical** by the severity taxonomy (no committed secrets, no unapproved paid SaaS, no license violation, no security backdoor) and none was **introduced** this iteration (verify-only). → CONTINUE, not REGRESSION.

## Next-Step Recommendation

Two tractable workstreams for upcoming `Mode:next` iterations:

1. **J-05 (frontend wiring only):** make `apps/frontend/src/components/BacktestConfigBar.tsx`
   fetch `/api/symbols` and `/api/timeframes` and populate the symbol + timeframe controls
   from them (replace the hardcoded timeframe literal at line ~61 and the free-text symbol
   input at lines ~43-54). **Do not modify the backend endpoints — they already work.**

2. **Storage anti-goals (highest value; aligns with the known pending Parquet/durable-store
   migration):** migrate `apps/backend/data/loader.py` from per-day CSV under `/tmp` to a
   single Parquet file per (symbol, timeframe) with a warm-cache read path, and change the
   `BACKTEST_STORE_DIR` default in `apps/backend/backend/session_store.py:26` off volatile
   `/tmp` to a durable in-repo path. This is architecture-level, must preserve the
   determinism / no-lookahead / warm-load-≥10× invariants, and carries regression risk to
   already-passing **J-01** and **J-06** — hence the `full` depth recommendation.

A later full-mode iteration should also (a) confirm or refute the `/api/sessions/{id}`
eager-load signal against `session_routes.py`, and (b) verify the J-04 "OOS-aware when
walk-forward data exists" sub-clause by regenerating insights after a walk-forward run.

## Halt Justification (if halting)

Not halting. Verdict is CONTINUE: this is the expected, healthy baseline outcome. The
goal is not achieved (J-05 failing; storage anti-goals unmet), there is no regression
(no prior journey state existed and no violation was introduced — verify-only), and the
session is not stalled (concrete, tractable next work is identified above).
