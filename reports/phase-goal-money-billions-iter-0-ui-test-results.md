# Goal money-billions — Iteration 0 — UI Test Results (Baseline)

**Phase:** goal-money-billions-iter-0 (baseline assessment, verify-only)
**Date:** 2026-05-18
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** FAIL

<!-- FAIL: J-05 (a Must-have / P1 journey) fails its literal acceptance.
     5/6 Must-have journeys PASS (J-01, J-02, J-03, J-04, J-06).
     This is the expected baseline outcome: it separates "already working"
     (J-01/02/03/04/06) from "needs work" (J-05) for subsequent iterations.
     Journey verdicts are recorded here as evidence; the goal-evaluator
     makes the authoritative journey/scope determination. -->

**Overall:** 5/6 journeys passed, 1 failed (0 skipped)

| Journey | Verdict |
|---------|---------|
| J-01 Run a backtest from natural language | **PASS** |
| J-02 Inspect and browse run history | **PASS** |
| J-03 Walk-forward validation | **PASS** |
| J-04 AI insights | **PASS** (primary acceptance; OOS-aware sub-clause not separately re-verified — see note) |
| J-05 Reference data loads | **FAIL** (endpoints work but UI controls are not populated by them) |
| J-06 Warm-cache re-run works end-to-end | **PASS** |

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-J-01 | Run a backtest from natural language | happy-path | P1 | Results panel shows non-empty metrics, equity curve, trades table; new run_id in history | NL "Buy when RSI crosses below 30, sell when it crosses above 70" + BTC/USDT·1h·2023-01-01→2023-12-31·$10,000 compiled via gpt-5.4-mini → run_id `c5bb46b5`, status `complete`: total_return −36.07%, sharpe −1.21, maxDD 43.21%, win_rate 56.52%, profit_factor 0.70, 115 trades, 8759-pt equity curve, 5-category rating; iteration appears in history | PASS | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-01-result.png` |
| UT-J-02 | Inspect and browse run history | happy-path | P1 | Selected prior run's strategy spec, metrics, trades reload into detail view | From iterations list, clicked prior run (run 1) → detail view switched to "BTC 1H RSI Mean Reversion" (ts 01:04:13, −36.07%, 115 trades, params BTC/USDT·1h·2023-01-01–2023-12-31·$10,000, Strategy Script + benchmark + 26-row trades table), distinct from run 2 (Cross, 23 trades, 01:12:27) | PASS | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-02-result.png` |
| UT-J-03 | Walk-forward validation | happy-path | P1 | WFE badge (color-coded), per-window table, combined OOS equity curve | On run 1 detail set IS=6/OOS=3 months, clicked "Run Walk-Forward" → **WFE 1.26** badge rendered GREEN (`bg-emerald-100 text-emerald`, correct: 1.26 ≥ 0.5); per-window table (Window 1: IS 2023-01-01–07-01 / OOS 2023-07-01–10-01, IS ret −12.38% / OOS ret −7.22%, IS sharpe −0.81 / OOS sharpe −1.02, IS 45 / OOS 29 trades); "Combined OOS Equity Curve (1 windows chained)" chart + OOS summary (OOS Return −7.22%, OOS Sharpe −1.02, OOS Win Rate 62.1%, OOS MaxDD −16.12%) | PASS | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-03-result.png` |
| UT-J-04 | AI insights | happy-path | P1 | ≥1 ranked suggestion renders; OOS-aware when WF data exists | On run 1, insights auto-generated: summary paragraph ("The BTC/USDT 1H RSI mean-reversion strategy performed poorly in 2023, losing 36.07%…") + **10 ranked suggestions** rendered as actionable chips; backend `insights = {summary, suggestions[10]}` persisted. Primary acceptance met. OOS-aware sub-clause: insights were generated *before* walk-forward; not separately re-verified post-WF | PASS | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-04-result.png` |
| UT-J-05 | Reference data loads | happy-path | P1 | `/api/symbols` and `/api/timeframes` populate the symbol and timeframe controls | Endpoints WORK (curl: `/api/symbols` → 26 symbols, `/api/timeframes` → 6 timeframes) but the frontend **never calls them**: `BacktestConfigBar.tsx` timeframe control is a hardcoded constant `['1m','5m','15m','1h','4h','1d']` (line 61); symbol control is a free-text `<input>` w/ regex validation (lines 43–54), no datalist/dropdown. Observed network calls on load: `/api/models`, `/api/sessions`, `/api/config`, `/api/directions/cache` — never `/api/symbols`/`/api/timeframes`. Controls are functional but NOT populated by the reference-data endpoints | FAIL | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-05-result.png` |
| UT-J-06 | Warm-cache re-run works end-to-end | happy-path | P1 | 2nd run completes, renders metrics/equity/trades without error, appears in history | Re-submitted identical NL + identical BTC/USDT·1h·2023-01-01→2023-12-31·$10,000 → 2nd run status `complete`, new run_id `b953df49`; renders summary (−5.31% return, 23 trades, 35% win rate, −2.30 sharpe), equity curve (Recharts), 24-row trades table, NO errors; iterationHistory count = 2, both runs in history list. Warm local OHLCV cache served the re-run end-to-end | PASS | `reports/qa/goal-money-billions-iter-0-evidence/UT-J-06-result.png` |

---

## Passed Tests

### UT-J-01 — Run a backtest from natural language
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-0-evidence/UT-J-01-result.png` (also `UT-J-01-config.png`, `UT-J-01-running.png`)
- Steps executed exactly: opened app → entered NL "Buy when RSI crosses below 30, sell when it crosses above 70" → set Symbol BTC/USDT (UI requires `BASE/USDT`; "BTCUSDT" maps to "BTC/USDT"), Timeframe 1h, range 2023-01-01→2023-12-31, Capital $10,000 → submitted.
- NL→StrategySpec compiled via OpenAI `gpt-5.4-mini` (OPENAI_API_KEY is configured in this environment — inferred from successful compilation, not from reading credentials).
- Backend confirms (`/api/sessions/9573c955-dc15-41a4-b476-01f7158ef6a6`): iteration `9c8e19cf`, **run_id `c5bb46b5`**, status `complete`, result keys = run_id/total_return/max_drawdown/num_trades/win_rate/sharpe_ratio/profit_factor/equity_curve/trades; 115 trades; 8759 equity-curve points; 5-category rating + benchmark present.
- UI rendered non-empty metrics, equity-curve chart, trades table; iteration appears in history list.

### UT-J-02 — Inspect and browse run history
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-0-evidence/UT-J-02-result.png`
- With 2 completed runs, navigated detail→list (back arrow) then clicked the prior run's compact card in the "Iterations (2)" list.
- Detail view reloaded run 1: title "BTC 1H RSI Mean Reversion", timestamp 01:04:13, −36.07%, params bar (BTC/USDT·1h·2023-01-01–2023-12-31·$10,000), Strategy Script section, VS BENCHMARK −191.69%, and a 26-row trades table — verifiably distinct from run 2 (Cross, 23 trades, −5.31%, ts 01:12:27). Strategy spec + metrics + trades all reloaded.

### UT-J-03 — Walk-forward validation
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-0-evidence/UT-J-03-result.png`
- From run 1's detail view, "Walk-Forward Analysis" panel present with IS months / OOS months inputs; set IS=6, OOS=3; clicked "Run Walk-Forward".
- **WFE badge:** "WFE 1.26 ✓" rendered in a GREEN pill (`rounded-full bg-emerald-100 text-emerald`) — color logic correct (1.26 ≥ 0.5 → green).
- **Per-window table:** header `# | IS Period | OOS Period | IS Return | OOS Return | IS Sharpe | OOS Sharpe | IS Trades | OOS Trades`; Window 1 = IS 2023-01-01–2023-07-01 / OOS 2023-07-01–2023-10-01, −12.38% / −7.22%, −0.81 / −1.02, 45 / 29 trades (1 full window fits a 12-month range with 6/3 config).
- **Combined OOS equity curve:** "Combined OOS Equity Curve (1 windows chained)" Recharts chart rendered; OOS summary tiles (OOS Return −7.22%, OOS Sharpe −1.02, OOS Win Rate 62.1%, OOS MaxDD −16.12%).

### UT-J-04 — AI insights
**Verdict:** PASS (primary acceptance)
**Evidence:** `reports/qa/goal-money-billions-iter-0-evidence/UT-J-04-result.png`
- On the completed run, AI insights auto-generated and rendered: a summary analysis paragraph plus **10 ranked, actionable suggestion chips** (Add Higher-Timeframe Trend Filter, Tighten Oversold Entry, Exit On RSI Reversion, Improve Stop Placement, Increase Reward Multiple, Optimize RSI Period, Filter Low-Volatility Hours, Add Regime Filter, Use Volatility-Sized Positions, Require Confirmation Candle).
- Backend persists `insights = {summary: str, suggestions: list[10]}` on the iteration (ordered list = ranked).
- **Note (baseline nuance):** the acceptance sub-clause "suggestions are OOS-aware when walk-forward data exists" was NOT separately verified — insights were generated *before* the J-03 walk-forward run, so OOS-awareness of regenerated insights is untested. Primary acceptance ("≥1 ranked suggestion renders") is unambiguously met. Recommend the goal-evaluator decide whether a dedicated post-WF insights-regeneration check is needed in a `Mode: next` iteration.

### UT-J-06 — Warm-cache re-run works end-to-end
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-0-evidence/UT-J-06-result.png`
- Re-submitted the identical NL strategy with identical symbol/timeframe/date-range/capital. 2nd run completed (status `complete`), new run_id `b953df49`, rendered metrics/equity-curve/24-row trades table with NO errors, and appears in history (iterationHistory count = 2; both runs in the list).
- Warm local OHLCV cache served the re-run end-to-end (no Binance fetch failure; run completed). Acceptance met.
- **Observation (not a failure):** the 2nd compilation of the same NL prompt produced a *different* strategy variant — "BTC 1H RSI Cross Mean Reversion" (23 trades, −5.31%) vs run 1's "BTC 1H RSI Mean Reversion" (115 trades, −36.07%). This is LLM recompilation variance at the NL→code step; it is orthogonal to the OHLCV warm cache and is NOT a violation of the backtest-determinism anti-goal (which concerns identical strategy code + data → identical output, not LLM determinism).

---

## Failed Tests

### UT-J-05 — Reference data loads
**Verdict:** FAIL
**Failure:** The journey's literal acceptance ("`/api/symbols` and `/api/timeframes` populate the symbol and timeframe controls") is not met. The reference-data endpoints are healthy, but the frontend does not consume them — the parameter controls are driven by a hardcoded frontend constant (timeframe) and a free-text input (symbol).
**Evidence:** `reports/qa/goal-money-billions-iter-0-evidence/UT-J-05-result.png`

**Steps taken:**
1. Opened the app, inspected the parameter controls (Symbol, Timeframe).
2. `curl http://localhost:8691/api/symbols` → 26 symbols (BTC/USDT, ETH/USDT, …); `curl .../api/timeframes` → 6 timeframes (1m,5m,15m,1h,4h,1d). Endpoints work.
3. Inspected the symbol control: a free-text `<input type=text>` (value "BNB/USDT"), no `<datalist>`, no dropdown; focus/click shows no API-sourced option list.
4. Inspected the timeframe control: 6 buttons exactly `1m 5m 15m 1h 4h 1D`.
5. Source confirmation (read-only): `apps/frontend/src/components/BacktestConfigBar.tsx` — timeframe is a hardcoded literal `['1m','5m','15m','1h','4h','1d']` (line 61); symbol is a free-text input with regex validation `^[A-Z]+\/USDT$` (lines 43–54). Neither calls `/api/symbols` or `/api/timeframes`.
6. Network/resource-timing on load showed `/api/models`, `/api/sessions`, `/api/config`, `/api/directions/cache` — **never** `/api/symbols` or `/api/timeframes`.

**Expected:** Symbol and timeframe controls populated from `/api/symbols` and `/api/timeframes`.
**Actual:** Controls are present and functional, but populated by a hardcoded constant (timeframe) and free-text entry (symbol). The reference-data endpoints exist and return correct data but are orphaned/unused by the UI. This is a genuine baseline gap — the failure is "UI does not consume working endpoints," not "endpoints broken."

---

## Skipped Tests

None — frontend (`:3691`) and backend (`:8691`) were running and Chrome MCP was available; all 6 Must-have journeys were executed.

---

## Baseline Observations (anti-goal signals — verify-only, recorded for goal-evaluator)

The iteration spec asks browser-QA to spot-check observable anti-goal compliance signals. These were observed via read-only inspection while exercising the journeys; **no code was modified**. They do not change journey verdicts — they are recorded for the goal-evaluator/QA to weigh.

1. **OHLCV cache is per-day CSV under volatile `/tmp` (contradicts the single-Parquet anti-goal).**
   - `apps/backend/data/loader.py:50–63`: `cache_dir = os.getenv("MARKET_DATA_CACHE_DIR", "/tmp")`; cache path = `{cache_dir}/{safe_symbol}/{timeframe}/{date_str}.csv`.
   - Observed live: `/tmp/market_data/BTC_USDT/1h/` contains **366 per-day `.csv` files** for 2023 (one per calendar day). **Zero `.parquet` files exist anywhere in the repo.**
   - Directly contradicts: "OHLCV market data MUST be cached as a single Parquet file per (symbol, timeframe) — NOT one CSV or file per calendar day" and the durable-store intent.

2. **`BACKTEST_STORE_DIR` defaults to a volatile `/tmp` path (contradicts the durable-store anti-goal).**
   - `apps/backend/backend/session_store.py:26`: `BASE_DIR = Path(os.environ.get("BACKTEST_STORE_DIR", "/tmp/backtests"))`.
   - Code-level default is `/tmp/backtests`. (Sessions did persist during this run; whether the running process overrides the default via env was not inspected — process-env credential read was out of scope and denied. The recorded signal is the code default.)

3. **No SQLite / relational DB files anywhere** — consistent with the "no SQLite/relational DB" anti-goal. ✓ (no `.sqlite*` / `.db` files found outside venv/pytest caches).

4. **Possible eager-load on the open path — needs deeper QA verification.**
   - `GET /api/sessions/9573c955-…` returned the session with `iterationHistory[]` containing full per-iteration `result` (incl. an 8759-point `equity_curve` and 115 `trades`) and `rating` inline.
   - The anti-goal states `GET /api/sessions/{id}` (list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` (detail should be lazy-loaded via the per-iteration endpoint). The observed payload shape suggests possible eager inclusion. **Recorded as a signal for the QA agent to verify against the actual `session_routes.py` open vs. per-iteration endpoints** — not a definitive determination from browser-QA.

---

## Environment

- **Frontend URL:** http://localhost:3691 (HTTP 200; deterministic per-project offset port, not 5173)
- **Backend URL:** http://localhost:8691 (`/` 200, **`/docs` 200**; deterministic offset port, not 8000)
- **Reference endpoints:** `/api/symbols` → 26 symbols; `/api/timeframes` → 6 timeframes (both healthy)
- **Browser:** Chrome via `mcp__plugin_superpowers-chrome_chrome__use_browser`
- **Test Date:** 2026-05-18
- **Model used for compilation:** `gpt-5.4-mini` (default; OPENAI_API_KEY is configured in this environment — inferred from successful NL compilation, J-01/J-03/J-04/J-06 all proceeded past the compile step)
- **Active session:** `9573c955-dc15-41a4-b476-01f7158ef6a6` (2 iterations created: `c5bb46b5`, `b953df49`)
- **Evidence directory:** `reports/qa/goal-money-billions-iter-0-evidence/` (10 screenshots: UT-J-01-config/running/result, UT-J-02-before/attempt/result, UT-J-03-result, UT-J-04-result, UT-J-05-result, UT-J-06-result)
- **Code modified:** none (verify-only baseline iteration confirmed)
