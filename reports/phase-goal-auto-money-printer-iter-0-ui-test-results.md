# Goal Iteration 0 — UI Test Results (Baseline Assessment)

**Phase:** goal-auto-money-printer-iter-0
**Date:** 2026-05-19
**Written by:** browser-qa-agent
**Mode:** baseline (no-op iteration — no code changes; this records the starting line)

---

**Browser QA Verdict:** FAIL

<!-- Rationale: 10 of 16 target journeys fail and 1 is partial. The entire headless
auto-optimizing strategy session capability (Key Capability 11; journeys J-07–J-16) is
NOT implemented in the current codebase: POST /api/auto-sessions returns HTTP 404 and the
iterate loop is still an in-browser while-loop. Per browser-qa rules, any failing
happy-path/P1 target journey ⇒ FAIL. This is the expected, valuable outcome of a baseline:
it cleanly separates the 5 already-passing core journeys + 1 partial from the 10 genuine
gaps so subsequent iterations focus only on real work. No code was changed this iteration. -->

**Overall:** 5/16 target journeys PASS, 1 PARTIAL, 10 FAIL (0 skipped)

- **Already implemented (PASS):** J-01, J-03, J-04, J-05, J-06 (core platform)
- **Partial (gap):** J-02 (prior-run reload — spec+metrics reload, trades table does not)
- **Not implemented (FAIL):** J-07, J-08, J-09, J-10, J-11, J-12, J-13, J-14, J-15, J-16
  (the whole Layer 1 + Layer 2 headless auto-optimizing session)

**Backend unit baseline (recorded, not fixed):** `apps/backend/.venv/bin/python -m pytest tests/ -q` ⇒ **124 passed, 1 failed** in 6.78s. The single pre-existing failure is `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (nice-to-have directions cache, Capability 10). No new failures introduced (no code changed).

---

## Environment

- **Frontend URL:** http://localhost:3691 (Vite/React, HTTP 200)
- **Backend URL:** http://localhost:8691 (FastAPI, `/docs` HTTP 200, 27 API paths)
- **Browser:** Chrome via superpowers-chrome MCP
- **Test Date:** 2026-05-19
- **OPENAI_API_KEY:** present in `apps/backend/.env` (live LLM pipeline confirmed — fresh strategy-specific compilation + insights were generated this session). No journeys recorded `blocked-no-key`.
- **Evidence directory:** `reports/qa/goal-auto-money-printer-iter-0-evidence/`
- **Pre-existing session:** one session (`BNB 4h Supertrend EMA Trend`, 1 iteration) existed at start from prior goal sessions; `/api/runs` started empty (0).

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-J-01 | Run a backtest from natural language | happy-path | P1 | Metrics + equity curve + trades table render; new run_id in history | NL "Buy when RSI<30/sell>70" → BTC/USDT 1h 2023-01-01–2023-03-01 $10k ran; rendered +3.28% return / 70.6% win / 0.054 sharpe / PF 1.30, equity curve (1440 pts), Trade History (17 trades), monthly returns, 5-cat rating; new run_id `4f74b3bf`; `/api/runs` 0→1; `GET /api/runs/4f74b3bf`→200 | **PASS** | UT-J-01-result.png |
| UT-J-02 | Inspect and browse run history | happy-path | P1 | Selected prior run's strategy spec, metrics, and trades reload into detail view | Selecting prior BNB run reloads its strategy spec + metrics summary + activity log + AI suggestions into the LEFT detail/conversation panel; but the RIGHT analysis panel (full trades table + equity curve) stays pinned to the latest run (still 17 RSI trades, not BNB's 91). Reproduced across 4 distinct click attempts. Spec ✓ + metrics ✓ reload; trades table ✗ | **PARTIAL** | UT-J-02-result.png, UT-J-02-after-click.png, UT-J-02-state.png |
| UT-J-03 | Walk-forward validation | happy-path | P1 | WFE badge (color-coded) + per-window table + combined OOS equity curve | From RSI run, set IS=1/OOS=1 mo, clicked Run Walk-Forward → "WFE -0.73 ✗" badge (red, <0.3), per-window table (1 window: IS 2023-01-01→02-01 / OOS 2023-02-01→03-01, +11.68%/-8.07%, sharpe 5.52/-4.04, 7/7 trades), "Combined OOS Equity Curve (1 windows chained)" | **PASS** | UT-J-03-result.png |
| UT-J-04 | AI insights | happy-path | P1 | ≥1 ranked suggestion renders; OOS-aware when WF data exists | Each completed run renders ~10 ranked AI improvement suggestions with rationale tooltips + an AI narrative analysis. Fresh RSI-specific suggestions generated this session (live LLM). `POST /api/generate-insights` schema accepts `walk_forward_result` (OOS-aware capability structurally present) | **PASS** | UT-J-04-result.png |
| UT-J-05 | Reference data loads | smoke | P1 | `/api/symbols` + `/api/timeframes` populate the controls | Timeframe `<select>` = all 6 from `/api/timeframes` (1m/5m/15m/1h/4h/1d); symbol input datalist populated from `/api/symbols` (BTC/USDT, ETH/USDT, BNB/USDT, …); model dropdown from `/api/models`. Both APIs return 200 with data | **PASS** | UT-J-05-result.png |
| UT-J-06 | Warm-cache re-run works end-to-end | happy-path | P1 | 2nd identical run completes, renders metrics/equity/trades w/o error, appears in history | Re-ran identical config; 2nd run completed in ~22s (vs ~60s+ cold), rendered metrics/equity(1440)/trades(17), run_id `fb0dff5e`, `/api/runs` 1→2, iterations→3. Output IDENTICAL & deterministic (3.28%/70.6%/17). Single-file Parquet `/tmp/market_data/BTC_USDT/1h.parquet` | **PASS** | UT-J-06-result.png |
| UT-J-07 | Start headless automated session via API | happy-path | P1 | HTTP 200 + sessionId, status running/queued; appears in `GET /api/sessions` | `POST /api/auto-sessions` → **HTTP 404**. Endpoint does not exist (27 API paths; none contain "auto"). No backend auto-session router | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-08 | Track the automated run live in the UI | happy-path | P1 | Live status + iterations appear without manual reload | Cannot start a headless session (depends on J-07; `POST /api/auto-sessions` 404). Only "Auto Run" is the legacy in-browser loop, not a headless backend session | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-09 | Auto chain stops on target/budget; best marked | happy-path | P1 | Terminal status w/ stop reason + best iteration marked | Requires the auto-session backend (`POST /api/auto-sessions` 404). No server-side terminal-state / stop-reason / best-marking | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-10 | Backend is single source of truth (rewired, survives reload) | happy-path | P1 | Run continues server-side after browser reload | Iterate loop is still an **in-browser** `while (attempt < maxAttempts && !autoRunStopRef.current)` loop at `apps/frontend/src/hooks/useBacktest.ts:2065` with browser-memory state (`autoRunStopRef`, `autoRunProgress`, `AbortController`). NOT rewired to backend; would not survive a tab reload; autoRun status lives only in browser memory. Violates the goal/anti-goal "iterate loop MUST exist only in the backend" | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-11 | Stop a running automated session | happy-path | P1 | Run transitions to `stopped`; no further iterations | `POST /api/auto-sessions/{sessionId}/stop` → **HTTP 404**. No server-side stop endpoint | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-12 | Open-universe run from only objective + budget | happy-path | P1 | ≥2 distinct configs as iterations; terminal within budget; best by robust score | Requires `POST /api/auto-sessions` (404). No open-universe optimizer/controller | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-13 | AI-token/cost budget hard-enforced | happy-path | P1 | stop reason `budget-exhausted`; spend ≤ cap; visible in status | Requires the auto-session backend + immutable cost tracker (404). No budget-enforcement path | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-14 | Staged screening — full cost only on survivors | happy-path | P1 | Activity log shows SCREEN (many) → PROMOTE (top-k); WF/strong model only on promoted | Requires the auto-session optimizer (404). No staged SCREEN/PROMOTE evaluation exists | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-15 | Learns from global history (warm start) + opt-out | happy-path | P1 | Run #2 cites prior-session perf; run #3 (`this-run`) does not | Requires the auto-session optimizer + history planner (404). No `history_scope` / cross-run learning | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |
| UT-J-16 | Robust objective gates overfit | happy-path | P1 | Best satisfies WFE+min-trades from WF OOS; raw-return-but-WFE-failing not chosen | Requires the auto-session optimizer's robust-objective selection (404). No automated best-selection logic | **FAIL** | UT-J-07-to-16-no-auto-sessions-api.png |

---

## Passed Tests

### UT-J-01 — Run a backtest from natural language
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-01-result.png`
- Steps executed exactly per goal.md: opened app → typed "Buy when RSI crosses below 30, sell when it crosses above 70" → set symbol `BTC/USDT`, timeframe `1h`, range `2023-01-01`–`2023-03-01`, capital `10000` → submitted.
- LLM compiled & auto-named the strategy **"BTC 1H RSI Reversion"**; pipeline ran validate → compile → fetch → simulate → metrics → suggestions.
- Results panel rendered **non-empty metrics** (+3.28% return, 70.59% win, sharpe 0.054, profit factor 1.30), **equity curve** (1440 points = 2 months of 1h bars), **Trade History (17 trades)** with full columns (# Dir Entry Exit Entry/Exit Price PnL Return), plus Monthly Returns and a 5-category Strategy Rating.
- **New run_id in history:** `4f74b3bf`; `GET /api/runs` total went **0 → 1**; `GET /api/runs/4f74b3bf` → HTTP 200.
- Note: the prominent "-39.57%" is correctly labeled **"VS BENCHMARK (ALPHA)"** (BTC rallied ~42.8% buy-and-hold in the window) — a correctly-labeled metric, not a defect.

### UT-J-03 — Walk-forward validation
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-03-result.png`
- From the completed RSI run's detail view, set IS months = 1, OOS months = 1 (dataset is only 2 months), clicked **Run Walk-Forward**; completed in ~20s.
- **WFE badge** displayed: "WFE **-0.73** ✗" — value < 0.3 ⇒ red/fail indicator (matches the green ≥0.5 / yellow 0.3–0.5 / red <0.3 spec).
- **Per-window table** rendered: 1 window — IS `2023-01-01–2023-02-01` / OOS `2023-02-01–2023-03-01`, IS Return +11.68% / OOS Return -8.07%, IS Sharpe 5.52 / OOS Sharpe -4.04, IS 7 / OOS 7 trades; plus OOS summary (Return -8.07%, Sharpe -4.04, Win 42.9%, MaxDD -10.85%).
- **Combined OOS equity curve** rendered: "Combined OOS Equity Curve (1 windows chained)".
- All three acceptance elements present.

### UT-J-04 — AI insights
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-04-result.png`
- Every completed run renders **~10 ranked AI improvement suggestions** as actionable chips, each with a rationale tooltip (RSI run: "Broaden RSI Entry Band", "Add Midline Exit", "Use Faster RSI Window", "Filter Above Uptrend", "Tighten Stop Placement", "Adapt Targets to Volatility", … ; BNB run: "Require EMA Slope Up", "Tighten Supertrend Multiplier", …) plus a substantive AI narrative analysis (Sharpe/PF/drawdown/win-rate aware).
- Suggestions are clearly LLM-generated and strategy-specific (fresh RSI-specific set produced this session) — confirms the live OpenAI insights pipeline.
- OOS-awareness: `POST /api/generate-insights` request schema includes a `walk_forward_result` field — the OOS-aware capability is structurally present. Caveat (baseline note, not a failure): suggestions auto-generate during the backtest pipeline before walk-forward; end-to-end OOS-aware *regeneration* after a WF run was not separately exercised.

### UT-J-05 — Reference data loads
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-05-result.png`
- Timeframe `<select>` populated with all 6 options matching `/api/timeframes`: 1 Minute=1m, 5 Minutes=5m, 15 Minutes=15m, 1 Hour=1h, 4 Hours=4h, 1 Day=1d.
- Symbol input backed by a datalist autocomplete populated from `/api/symbols` (BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT, ADA/USDT, DOGE/USDT, AVAX/USDT, …).
- Model dropdown populated from `/api/models` (gpt-5.4-mini default + Claude options). Both reference endpoints return HTTP 200 with non-empty data.

### UT-J-06 — Warm-cache re-run works end-to-end
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-06-result.png`
- Cold run (J-01) created single-file Parquet cache `/tmp/market_data/BTC_USDT/1h.parquet` (one file per symbol/timeframe — matches anti-goal; no per-day fan-out).
- Re-ran the **identical** config (BTC/USDT, 1h, 2023-01-01–2023-03-01, $10,000, same RSI prompt). 2nd run **completed in ~22s** (vs the cold run's ~60s+ incl. ~62s Binance fetch), rendered metrics, equity curve (1440 pts) and Trade History (17 trades) **without error**, and appeared in history (`/api/runs` **1 → 2**, run_id `fb0dff5e`; session iterations 2 → 3).
- Output was **byte-identical & deterministic** to the cold run (total_return 0.032762857…, win 70.588…%, 17 trades) — confirms the warm local-cache path works end-to-end.

---

## Failed Tests

### UT-J-02 — Inspect and browse run history (PARTIAL)
**Verdict:** PARTIAL
**Failure:** Selecting a prior run reloads only 2 of the 3 required artifacts into a "detail view".
**Evidence:** `reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-02-result.png`, `UT-J-02-after-click.png`, `UT-J-02-state.png`

**Steps taken:**
1. Completed backtests existed (J-01 RSI + pre-existing BNB Supertrend).
2. Clicked the prior **BNB 4h Supertrend EMA Trend** iteration from the history/iteration list (tried 4 distinct ways: simple text selector, metrics card, chat-header, via the "Iterations" picker).

**Expected:** the selected run's strategy spec, metrics, **and trades** reload into the detail view.
**Actual:** Clicking the prior run reloads its **strategy spec ✓** (full Supertrend description), **metrics ✓** (its result summary "-2.27% return, 91 trades, 33% win rate, -0.07 sharpe" + full activity/metrics log) and AI suggestions into the **LEFT** conversation/detail panel. But the **RIGHT analysis panel** (full Trade History table + equity curve + monthly returns + WF) does **NOT** follow the selection — it stays pinned to the most-recently-run iteration (kept showing RSI's 17-trade table, never BNB's 91-trade table). No "view analysis / open" affordance exists on the card to load a prior run's full trade detail. → spec + metrics reload (2/3); the per-run **trades table does not reload** ⇒ acceptance only partially met.

### UT-J-07 … UT-J-16 — Headless auto-optimizing strategy session (ALL FAIL — not implemented)
**Verdict:** FAIL (10 journeys)
**Failure:** The entire "Headless auto-optimizing strategy session" (Key Capability 11; goal Layer 1 + Layer 2) does not exist in the current codebase.
**Evidence:** `reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png`

**Concrete proof (API):**
- `POST /api/auto-sessions` → **HTTP 404** (also `GET /api/auto-sessions` → 404; `POST /api/auto-sessions/{id}/stop` → 404).
- `GET /openapi.json`: **27** total API paths, **none** contains "auto". Backend routers present: only `directions_routes.py` and `session_routes.py` — no auto-session router. No backend `.py` references `/api/auto`, `AutoSession`, or `auto_session` (tests excluded).

**Concrete proof (J-10 specifically — not rewired):**
- The auto/iterate loop exists **only in the frontend**: `apps/frontend/src/hooks/useBacktest.ts:2065` runs `while (attempt < maxAttempts && !autoRunStopRef.current) { … }` with browser-memory state (`autoRunStopRef`, `autoRunProgress`, `AbortController`, `autoRunIterationIdsRef`). The "Auto Run" button drives this in-browser loop; status is **not** persisted to the durable store and would **not** survive a tab reload. This directly contradicts the goal/anti-goal: "After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST NOT run a second in-browser iterate loop" and "the `autoRun` status MUST be persisted to the durable store … MUST NOT live only in browser memory."

**Consequence per journey:**
- **J-07** (start via API) — FAIL: no `POST /api/auto-sessions` (404).
- **J-08** (track live in UI) — FAIL: nothing headless to track (depends on J-07).
- **J-09** (terminal on target/budget, best marked) — FAIL: no server-side auto session.
- **J-10** (backend single source of truth, survives reload) — FAIL: loop is in-browser, browser-memory state, not rewired.
- **J-11** (stop running session) — FAIL: no `POST /api/auto-sessions/{id}/stop` (404).
- **J-12** (open-universe from objective+budget) — FAIL: no optimizer/controller.
- **J-13** (hard token/USD budget) — FAIL: no auto-session cost tracker.
- **J-14** (staged SCREEN→PROMOTE) — FAIL: no staged evaluation.
- **J-15** (global-history warm start + opt-out) — FAIL: no history planner / `history_scope`.
- **J-16** (robust objective gates overfit) — FAIL: no automated robust best-selection.

These were exercised as far as possible without manufacturing scope: the `POST /api/auto-sessions` start call (the gate for every one of J-07–J-16, including the open-universe/budget/staged variants) returns 404, so the dependent UI/optimizer behaviors cannot be reached. No tiny-budget auto-session could be created; no source-level auto-session implementation exists to drive.

---

## Skipped Tests

None. The frontend (3691) and backend (8691) were both running, Chrome MCP was available, and `OPENAI_API_KEY` was present (live LLM compilation + insights confirmed), so no journey was skipped or recorded `blocked-no-key`.

---

## Baseline Observations (recorded, not fixed — informs later hardening iterations)

1. **Auto-optimizing session entirely absent (primary gap).** The central new goal capability (J-07–J-16) is unimplemented; the legacy in-browser "Auto Run" loop is the only automation and is not backend-driven (J-10). This is the dominant work item for subsequent iterations.
2. **J-02 prior-run detail is partial.** The right-hand analysis panel (trades/equity/WF) does not re-bind when an older run is selected; only the left conversation panel reloads spec+metrics. A "view full analysis for this run" path is missing.
3. **Volatile OHLCV cache path.** `apps/backend/.env` sets `MARKET_DATA_CACHE_DIR=/tmp/market_data` — a volatile `/tmp` location, while `loader.py`'s own comment states the default was moved off `/tmp` to satisfy the single-Parquet storage anti-goal. `BACKTEST_STORE_DIR` itself is correctly durable (`…/.data/backtests`). The OHLCV cache surviving a host restart is at risk; flag for hardening (not a hard anti-goal violation per the literal text, which scopes the `/tmp` prohibition to `BACKTEST_STORE_DIR`).
4. **Warm-cache re-write on hit.** The Parquet cache file's mtime updated on the warm re-run though byte-size was identical and total runtime (~22s) precludes a Binance re-fetch — likely a cache re-write/merge on load. Worth confirming "zero re-fetch when covering cache exists" precisely in a later iteration.
5. **Backend unit baseline:** 124 passed / 1 failed (`test_directions_cache.py::test_write_and_read_full_round_trip`) — pre-existing, in the nice-to-have directions cache; not introduced here and not fixed (no-op iteration).
6. **Input validation (noted, not tested destructively):** `POST /api/auto-sessions` rejecting invalid input could not be assessed because the endpoint does not exist (404). Re-evaluate once the endpoint is built.
