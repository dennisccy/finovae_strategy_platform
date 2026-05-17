# Goal Iteration goal-money-money-iter-0 — UI Test Results

**Phase:** goal-money-money-iter-0
**Date:** 2026-05-18 (journey execution started 2026-05-17 23:40)
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** FAIL

<!-- FAIL: J-05 (a P1 must-have journey) fails its acceptance — reference-data endpoints exist and return data but are not wired into the symbol/timeframe controls. All other target journeys (J-01, J-02, J-03, J-04, J-06) PASS. -->

**Overall:** 5/6 journeys passed (0 skipped, 1 failed)

Mode: GOAL-MODE LEAN baseline. Target journeys: J-01, J-02, J-03, J-04, J-05, J-06. Required-still-passing journeys: None (baseline establishes initial status). Each journey executed end-to-end against the running, unmodified codebase via Chrome MCP. No code changes made.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-J-05 | Reference data loads | journey/happy-path | P1 | `/api/symbols` and `/api/timeframes` populate the symbol and timeframe controls | Both endpoints exist & return valid data (26 symbols, 6 timeframes) but the frontend never calls them on load; Symbol is a free-text input, Timeframe is a static button group — controls are NOT populated from the endpoints | FAIL | `reports/qa/goal-money-money-iter-0-evidence/UT-J-05-controls.png` |
| UT-J-01 | Run a backtest from natural language | journey/happy-path | P1 | Results panel shows non-empty metrics, equity curve, trades table; new run_id in history | -34.98% return, 116 trades, 57% win, -1.18 Sharpe, alpha -202.06%, Strategy Rating, Equity Curve, Trade History (116 trades); new iteration "BTC 1h RSI Mean Reversion" @ 2026-05-17 23:40:54 in history | PASS | `reports/qa/goal-money-money-iter-0-evidence/UT-J-01-result.png` |
| UT-J-02 | Inspect and browse run history | journey/happy-path | P1 | Selected prior run's strategy spec, metrics, and trades reload into the detail view | Switched session via Sessions list; opened prior run "BNB 4h EMA9 Pullback Confirmed" — spec text, params (BNB/USDT, 2020-01-01–2024-01-01, $1,500), metrics (TOTAL TRADES 144, +291.76%, alpha -1893.91%, Strategy Rating), Equity Curve, and Trade History (144 trades) all reloaded; 144 matched the selected run (distinct from active BTC RSI 116) | PASS | `reports/qa/goal-money-money-iter-0-evidence/UT-J-02-detail.png`, `UT-J-02-trades.png` |
| UT-J-03 | Walk-forward validation | journey/happy-path | P1 | WFE badge (green ≥0.5 / yellow 0.3–0.5 / red <0.3), per-window table, combined OOS equity curve | WFE 0.31 badge (yellow tier); per-window table with 2 rolling windows (W1 IS 2023-01-01–2023-07-01 / OOS 2023-07-01–2023-10-01; W2 IS 2023-04-01–2023-10-01 / OOS 2023-10-01–2024-01-01); "Combined OOS Equity Curve (2 windows chained)"; OOS metrics (Return -5.91%, Sharpe -0.35, Win 62.0%, MaxDD -16.12%) | PASS | `reports/qa/goal-money-money-iter-0-evidence/UT-J-03-walkforward.png` |
| UT-J-04 | AI insights | journey/happy-path | P1 | ≥1 ranked suggestion renders; OOS-aware when walk-forward data exists | Substantive AI analysis paragraph rendered + 10 ranked suggestion chips (Fix Entry Direction, Use Symmetric Exit Logic, Add Trend Filter, Tighten Stop Loss, Reduce Take Profit, Tune RSI Periods, Add Volatility Filter, Use Regime Filter, Improve Position Sizing, Add Time-Based Exit). Core acceptance met. OOS-aware sub-clause not explicitly verifiable from chip text (generic labels); deeper "Generating suggestions…" kept streaming | PASS | `reports/qa/goal-money-money-iter-0-evidence/UT-J-04-insights.png` |
| UT-J-06 | Warm-cache re-run works end-to-end | journey/happy-path | P1 | Second run (same strategy/symbol/timeframe/date range) completes with metrics, equity curve, trades, no error, appears in history | Clicked "Re-run" (BTC/USDT 1h 2023-01-01–2024-01-01 $1,500); 2nd run completed with no error: TOTAL TRADES 116, -34.98% return, 57% win (identical to J-01 → deterministic + warm Parquet-cache reuse), Equity Curve + Trade History (116 trades); "Iterations (2)" in history | PASS | `reports/qa/goal-money-money-iter-0-evidence/UT-J-06-rerun.png` |

---

## Passed Tests

### UT-J-01 — Run a backtest from natural language
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-money-iter-0-evidence/UT-J-01-result.png`
- Opened the app, entered the NL strategy "Buy when RSI crosses below 30, sell when it crosses above 70", set Symbol `BTC/USDT`, Timeframe `1h`, date range `2023-01-01 → 2024-01-01` (narrowed from the 2020–2024 default for a faster, reliable baseline run; still a valid date range), Capital `$1,500`, and submitted.
- Pipeline observed: "Generating strategy code…" → validate → compile → fetch market data → run simulation → calculate metrics. A transient **"Operation cancelled"** label appeared in the iteration list mid-SSE-stream but resolved into a fully completed run (no error, not actually cancelled).
- Final result: **-34.98% return, 116 trades, 57% win rate, -1.18 Sharpe**, alpha -202.06%, Annual Return -34.93%, Beta 0.31, Total Commissions $104.94, full Strategy Rating, Monthly Returns, an Equity Curve (Jan 2023→Jan 2024, $0–$1.8K axis), and **Trade History (116 trades)**.
- New iteration "BTC 1h RSI Mean Reversion" timestamped 2026-05-17 23:40:54 appeared in session history ("Iterations (1)").

### UT-J-02 — Inspect and browse run history
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-money-iter-0-evidence/UT-J-02-detail.png`, `UT-J-02-trades.png`
- With completed runs available, opened the Sessions list and switched to an existing session "BNB 4h EMA9 Pullback" (6 prior runs). The "Iterations (6)" history list rendered each prior run with its own name, params, return, vs-BH, trade count, DD, WR, SR, and timestamp.
- Selected the prior run **"BNB 4h EMA9 Pullback Confirmed"** from the history list. Its full detail reloaded into the detail view: strategy spec/modification text + Strategy Script, params (BNB/USDT, 2020-01-01–2024-01-01, $1,500), metrics (**TOTAL TRADES 144**, +291.76% return, alpha -1893.91%, Strategy Rating), Equity Curve, and **Trade History (144 trades)**.
- The 144-trade figure matched the selected run's summary and is distinct from the active BTC-RSI run's 116 trades, confirming the detail view reloaded the correct prior run (not stale data). Cross-session navigation via the Sessions dropdown also works.

### UT-J-03 — Walk-forward validation
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-money-iter-0-evidence/UT-J-03-walkforward.png`
- From the completed J-01 run detail view, IS/OOS window controls were present and set (IS=6, OOS=3). Clicked **"Run Walk-Forward"**.
- Result: a **WFE 0.31** badge (in the yellow tier, 0.3–0.5 per acceptance), a **per-window table** with 2 rolling windows (W1: IS 2023-01-01–2023-07-01 / OOS 2023-07-01–2023-10-01; W2: IS 2023-04-01–2023-10-01 / OOS 2023-10-01–2024-01-01), and a **"Combined OOS Equity Curve (2 windows chained)"**. OOS aggregate metrics also rendered: OOS Return -5.91%, OOS Sharpe -0.35, OOS Win Rate 62.0%, OOS Max DD -16.12%.

### UT-J-04 — AI insights
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-money-iter-0-evidence/UT-J-04-insights.png`
- On the completed run, an AI analysis insight auto-generated: a substantive paragraph diagnosing the strategy ("…losing 34.98% with a 43.27% max drawdown…profit factor of 0.71 shows losers were significantly larger than winners…likely mis-specified for mean reversion…improving exit discipline, trend filtering, and regime selection should have the biggest impact").
- **10 ranked improvement suggestion chips** rendered: Fix Entry Direction, Use Symmetric Exit Logic, Add Trend Filter, Tighten Stop Loss, Reduce Take Profit, Tune RSI Periods, Add Volatility Filter, Use Regime Filter, Improve Position Sizing, Add Time-Based Exit. Acceptance "at least one ranked suggestion renders" is satisfied.
- Caveat (for the evaluator, not a failure): the OOS-aware sub-clause could not be explicitly verified — the chip labels are generic strategy actions with no explicit out-of-sample phrasing, and a deeper "Generating suggestions…" sub-state continued streaming. The platform does expose OOS/walk-forward data on the run, but OOS-specific wording in the suggestions themselves was not observable from the rendered chips.

### UT-J-06 — Warm-cache re-run works end-to-end
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-money-iter-0-evidence/UT-J-06-rerun.png`
- Clicked **"Re-run"** on the completed J-01 run (identical strategy, Symbol BTC/USDT, Timeframe 1h, date range 2023-01-01–2024-01-01, Capital $1,500).
- The second run completed end-to-end **without error**: TOTAL TRADES 116, -34.98% return, 57% win rate — **identical** to the J-01 result, which evidences both deterministic backtests (identical inputs → identical output) and warm single-file Parquet-cache reuse (no Binance re-fetch needed for an already-fetched window). Equity Curve and **Trade History (116 trades)** rendered; a new iteration was added → session history shows **"Iterations (2)"**.
- Observation only (baseline scope): precise cold-vs-warm fetch timing was not separately measured at the UI layer (a backend concern); the UI-observable end-to-end warm re-run path works and the identical deterministic output is consistent with warm-cache reuse.

---

## Failed Tests

### UT-J-05 — Reference data loads
**Verdict:** FAIL
**Failure:** The reference-data endpoints exist and return valid data, but the frontend does not call them and does not populate the symbol/timeframe controls from them — the journey's acceptance ("`/api/symbols` and `/api/timeframes` populate the symbol and timeframe controls") is not met.
**Evidence:** `reports/qa/goal-money-money-iter-0-evidence/UT-J-05-controls.png`

**Steps taken:**
1. Opened the app at http://localhost:3691 and inspected the parameter controls.
2. Verified the endpoints directly via the Vite `/api` proxy: `GET /api/symbols` → 26 symbols (BTC/USDT, ETH/USDT, …); `GET /api/timeframes` → 6 entries (1m…1d). Both return HTTP 200 with valid payloads.
3. Inspected the controls: **Symbol** is a free-text `<input type="text">` (placeholder "e.g. PEPE/USDT", default value "BNB/USDT"), with no `list`/datalist/autocomplete; **Timeframe** is a static button group (1m, 5m, 15m, 1h, 4h, 1D); Exchange is a hardcoded `<select>`.
4. Captured the page's Performance resource entries on a fresh load: the frontend calls many `/api/*` endpoints (`/api/models`, `/api/sessions`, `/api/config`, `/api/directions/cache`, numerous `/api/sessions/<id>`, `/meta`, `/activity`) but **`/api/symbols` and `/api/timeframes` are never requested** (`symbolsCalled=false`, `timeframesCalled=false`).

**Expected:** The symbol and timeframe controls are populated from `/api/symbols` and `/api/timeframes`.
**Actual:** The endpoints work but are not consumed by the UI; the Symbol control is manual free-text entry and the Timeframe control is a static hardcoded button set. The controls are functional for downstream journeys (a user can type a symbol and click a timeframe — which is why J-01/J-02/J-03/J-04/J-06 still pass), but the specific J-05 acceptance is not satisfied. This is a real code-level gap (frontend not wired to the reference-data endpoints), not an environmental or automation issue.

---

## Skipped Tests

None — all 6 target journeys were executed (frontend running, Chrome MCP available).

---

## Notes (baseline observations — observation only, no code changed)

- **Transient "Operation cancelled" label (J-01):** during the SSE-streamed run, the iteration list briefly showed "Operation cancelled" before the run resolved to a complete result set. Not an actual failure here, but flagged for the evaluator as a potentially misleading transient UI state.
- **LLM-dependent journeys ran successfully:** `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are present in `apps/backend/.env`; default model shown is "GPT-5.4 Mini". J-01/J-03/J-04/J-06 completed — no environmental (missing-credential) failures.
- **UI-observable anti-goal posture (for the evaluator; not assessed at code level by this agent):** the session-list/open path requests `/api/sessions/<id>/meta` and `/api/sessions/<id>/activity` (lightweight) and the heavy run detail only loads when a run is selected from history (observed in J-02) — consistent with the lazy-load anti-goal being respected at the UI layer. Parquet single-file vs per-day fan-out and `BACKTEST_STORE_DIR` default location are not browser-observable and were not inspected (left for code-level evaluation).

---

## Environment

- **Frontend URL:** http://localhost:3691
- **Backend:** reachable via the Vite `/api` proxy (direct :8000 not exposed; dev port offset in effect)
- **Browser:** Chrome via `mcp__plugin_superpowers-chrome_chrome__use_browser`
- **Test Date:** 2026-05-17 23:40 → 2026-05-18 00:03
- **Evidence directory:** `reports/qa/goal-money-money-iter-0-evidence/`
- **Code changes:** none (verify-only baseline)
