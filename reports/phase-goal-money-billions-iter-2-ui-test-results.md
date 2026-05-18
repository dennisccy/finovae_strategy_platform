# Phase goal-money-billions-iter-2 — UI Test Results

**Phase:** goal-money-billions-iter-2
**Date:** 2026-05-18
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** PASS

<!-- PASS: target journey J-05 passes; all required-still-passing journeys (J-01, J-02, J-03, J-04, J-06) pass with no regression from the symbol/timeframe control change. -->

**Overall:** 6/6 journeys passed (0 skipped)

- Target journey: **J-05** — PASS
- Required-still-passing: **J-01, J-02, J-03, J-04, J-06** — all PASS (no regression)

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-J-05 | Reference data loads (TARGET) | smoke | P1 | `/api/symbols` & `/api/timeframes` populate the symbol & timeframe controls | Symbol = endpoint combobox with 26 `BASE/USDT` opts == live `/api/symbols`; Timeframe `<select>` = 6 `{value,label}` == live `/api/timeframes`; both confirmed fetched via `fetch()`; old hardcoded button row gone | PASS | `UT-J-05-initial.png`, `UT-J-05-result.png` |
| UT-J-01 | Run a backtest from NL | happy-path | P1 | Non-empty metrics + equity curve + trades table + new `run_id` in history | New run `e554838d` appended (4th); persisted `backtestParams`=`BTC/USDT`/`1h`; −7.81% ret, 39 trades, 49% win, equity curve + 39-row trades table rendered | PASS | `UT-J-01-result.png`, `UT-J-01-running.png` |
| UT-J-06 | Warm-cache re-run end-to-end | happy-path | P1 | 2nd run completes, renders metrics/equity/trades, appears in history | New run `a5d18072` (5th, ts matches submit); identical deterministic result (−7.81%/39 trades) on cached data; no error; rendered + in history | PASS | `UT-J-06-result.png` |
| UT-J-02 | Inspect & browse run history | smoke | P1 | Selected prior run's spec/metrics/trades reload into detail view | Opened prior session from Sessions list → detail reloaded: 115-trade table, 2023-01-01–2023-12-31, ALPHA −191.69%, script + equity curve (entirely different from prior view) | PASS | `UT-J-02-result.png`, `UT-J-02-sessions.png` |
| UT-J-03 | Walk-forward validation | smoke | P1 | WFE badge + per-window table + combined OOS equity curve appear | Set IS/OOS (6/3), clicked Re-run → WFE recomputed 0.53→1.26 (green ≥0.5 ✓), OOS Return −11.71%→−7.22%, per-window table + combined OOS curve render | PASS | `UT-J-03-result.png` |
| UT-J-04 | AI insights | smoke | P1 | ≥1 ranked suggestion renders | 7 ranked suggestions rendered on a completed run ("Add Mean Reversion Exit", "Use Higher-Timeframe Trend", "Tighten Adaptive Stops", "Optimize RSI Window", "Add Volatility Floor", "Regime-Based Entry Filter", "Increase Position Size") | PASS | `UT-J-04-result.png` |

---

## Passed Tests

### UT-J-05 — Reference data loads (TARGET JOURNEY)
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-2-evidence/UT-J-05-initial.png`, `UT-J-05-result.png`

Journey steps: *Open the app and inspect the parameter controls.* Acceptance: *`/api/symbols` and `/api/timeframes` populate the symbol and timeframe controls.*

Conclusive verification via DOM + network inspection:

- **Symbol control** is an endpoint-backed native combobox: `<input list="symbol-options">` with a `<datalist id="symbol-options">` containing **exactly 26 options** = `["BTC/USDT","ETH/USDT","BNB/USDT", … ,"WLD/USDT","PEPE/USDT"]`, byte-identical to the live `GET /api/symbols` payload (verified against the live endpoint via the Vite proxy: `{"symbols":["BTC/USDT", … 26 … "PEPE/USDT"]}`). The component initializes `symbolOptions` to `[]` (there is **no 26-element hardcoded fallback** anywhere), so a populated 26-item datalist can **only** have come from the endpoint.
- **Timeframe control** is now a `<select>` (the old hardcoded `['1m','5m','15m','1h','4h','1d']` button row is gone) with **6 options** = `[{1m,"1 Minute"},{5m,"5 Minutes"},{15m,"15 Minutes"},{1h,"1 Hour"},{4h,"4 Hours"},{1d,"1 Day"}]`, exactly matching the live `GET /api/timeframes` payload (server `value` drives selection, server `label` shown).
- **Network proof:** `performance` resource timing shows both `/api/symbols` and `/api/timeframes` requested with `initiatorType:"fetch"` (609 B / 518 B responses), so the timeframe `<select>` is genuinely endpoint-backed and not merely the (coincidentally identical) `FALLBACK_TIMEFRAMES`.
- **Default preserved:** the active session's symbol input shows `BTC/USDT` and timeframe shows `1h`; the app default (`4h`, per `DEFAULT_PARAMS`) is also a selectable option and is preserved — selecting timeframe `4h` then `1h` updated the controlled value correctly, and the persisted `backtestParams` retained the exact slash-form string (no transform).

### UT-J-01 — Run a backtest from natural language
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-2-evidence/UT-J-01-result.png`, `UT-J-01-running.png`

Entered *"Buy when RSI crosses below 30, sell when it crosses above 70"* with the endpoint-backed `BTC/USDT` + `1h` controls (timeframe write-path exercised: select 4h→1h reflected in controlled value) and submitted.

- A fresh backtest executed (SSE-streamed log progressed) and completed.
- **New `run_id` in history:** session `iterationHistory` grew to a new entry `e554838d-caa1-4d6d-91ed-4c97acc386a2` (ts `2026-05-18T03:44:35Z`, matching submit).
- **Controls feed the request correctly (no regression):** persisted `backtestParams` = `symbol:"BTC/USDT"`, `timeframe:"1h"` — the new combobox/`<select>` write the exact string format `/api/run-backtest` already consumes; no transform introduced.
- **Non-empty results rendered:** −7.81% return, 39 trades, 49% win rate, sharpe, ALPHA −55.36%, Strategy Rating panel; equity curve chart; `Trade History (39 trades)` table.

### UT-J-06 — Warm-cache re-run works end-to-end
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-2-evidence/UT-J-06-result.png`

Re-submitted the same strategy with the same `BTC/USDT` / `1h` / `2024-01-01–2024-03-01` (OHLCV cached from J-01).

- Second run completed; `iterationHistory` grew 4→5 with new `run_id` `a5d18072-5060-44f5-8cc9-664bd2553b6c` (ts `2026-05-18T03:51:01Z`, matching submit).
- **Warm path verified:** identical deterministic output to the J-01 run on the same cached data (ret −0.0781, 39 trades) → warm local-cache re-run works end-to-end, no Binance re-fetch, deterministic (anti-goal honored).
- Metrics + equity curve + `Trade History (39 trades)` rendered, **no error banner**, run appears in history.

### UT-J-02 — Inspect and browse run history
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-2-evidence/UT-J-02-sessions.png`, `UT-J-02-result.png`

Opened the Sessions (run-history) list and selected a distinct prior session ("BTC 1H RSI Mean Reversion · 2 iters · −5.3%").

- Detail view **reloaded** the prior run's full detail: `Trade History (115 trades)`, Date Range `2023-01-01 – 2023-12-31`, ALPHA `−191.69%`, Strategy Script, and its own equity curve — entirely different from the pre-click view (39 trades / −55.36% / 2024 range).
- Strategy spec, metrics, and trades all reloaded into the detail view per the acceptance.
- *Note:* the in-conversation chat cards (left panel) are a read-only activity log and are not the run selector; the Sessions list is the run-history list, and it functions correctly. No regression.

### UT-J-03 — Walk-forward validation
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-2-evidence/UT-J-03-result.png`

From a completed run's detail view, IS/OOS window inputs were present and set (IS months = 6, OOS months = 3); clicked the WF **Re-run**.

- Walk-forward executed and recomputed: **WFE badge 0.53 → 1.26** (≥ 0.5 → green, ✓), OOS Return −11.71% → −7.22% (fresh computation confirmed).
- **Per-window table** renders (`# / IS Period / OOS Period / IS Return / OOS Return / IS Sharpe / OOS Sharpe / IS Trades / OOS Trades`, multiple windows with real `2023-…` date ranges).
- **Combined OOS Equity Curve** ("3 windows chained") renders.
- All J-03 acceptance artifacts appear; the WF feature is functional and not regressed by the control change.

### UT-J-04 — AI insights
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-2-evidence/UT-J-04-result.png`

On a completed run, AI improvement insights render: **7 ranked suggestions** — "Add Mean Reversion Exit", "Use Higher-Timeframe Trend", "Tighten Adaptive Stops", "Optimize RSI Window", "Add Volatility Floor", "Regime-Based Entry Filter", "Increase Position Size" — plus the analysis header text. Acceptance "at least one ranked suggestion renders" is satisfied.

*Scope note:* the J-04 sub-assertion "suggestions are OOS-aware when walk-forward data exists" is **explicitly deferred** by the iter-2 spec to a subsequent full-depth iteration's QA and is therefore out of scope here; it is not asserted or gated in this run. Smoke acceptance (≥1 ranked suggestion) passes → no regression.

---

## Failed Tests

None.

---

## Skipped Tests

None. Frontend (`http://localhost:3691`) was up and Chrome MCP was available; all journeys were executed live.

---

## Observations (non-blocking — for the goal-evaluator, not journey failures)

1. **Redundant reference-data fetches (mild efficiency note).** The multi-session UI mounts 18 `BacktestConfigBar` instances; each independently fetches `/api/symbols` + `/api/timeframes` on mount (×2 from React 18 dev StrictMode → 36 + 36 total). Requests all complete within ~330 ms of load and then stop — **no remount/poll loop**. This does not break J-05 or any journey, and a shared cache/hook is explicitly **out of scope** per the iter spec ("Adding a new reference endpoint or caching layer for reference data" is OUT OF SCOPE). Recorded only as a future-efficiency note; not a defect of this iteration.

2. **Deferred eager-load anti-goal still present (pre-existing, out of scope).** `GET /api/sessions/{id}` inlines full per-iteration `result` / `rating` / `insights` / `scriptCode` / `timeframeResults` payloads in `iterationHistory`. This is the known `GET /api/sessions/{id}` eager-load anti-goal — which the iter-2 spec **explicitly defers** to a subsequent full-depth iteration and lists as OUT OF SCOPE. This iteration is frontend-only and did not touch `session_routes.py`, so the condition is **unchanged / pre-existing, not a regression**. The iter spec itself notes GOAL_ACHIEVED remains blocked by this (a goal-evaluator gate, not a browser-QA journey result).

---

## Environment

- **Frontend URL:** http://localhost:3691 (HTTP 200; backend reachable via the Vite `/api` proxy — `/api/symbols` → 26 symbols, `/api/timeframes` → 6 timeframes)
- **Browser:** Chrome via MCP (`mcp__plugin_superpowers-chrome_chrome__use_browser`), viewport 1680×1050
- **Test Date:** 2026-05-18
- **Active session under test:** `e954851a-fd1d-42ab-bf27-b05378ec72d1` ("BTC 1h RSI Reversion"); prior session opened for J-02: "BTC 1H RSI Mean Reversion"
- **Evidence directory:** `reports/qa/goal-money-billions-iter-2-evidence/`
