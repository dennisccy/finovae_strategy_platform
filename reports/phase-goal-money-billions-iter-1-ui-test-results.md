# Phase goal-money-billions-iter-1 — UI Test Results

**Phase:** goal-money-billions-iter-1
**Date:** 2026-05-18
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** PASS

<!-- PASS: all smoke + happy-path + executed P1 tests passed; 0 failures.
     UT-05 (P1, DoD-critical restart durability) is SKIPPED — not FAILED —
     because performing it requires killing the shared QA backend process and
     moving apps/backend/.env, which the environment-safety policy blocked and
     no interactive user exists to authorize it in this automated pipeline.
     Its durability guarantee is strongly corroborated by UT-10 + on-disk
     evidence + the session_store.py code default, and is the explicit
     responsibility of functional pytest TC-08/TC-09 per the test plan. -->

**Overall:** 10/11 tests passed (1 skipped, 0 failed)

> **READ THIS FIRST — UT-05 escalation.** UT-05 ("J-02 durability: history
> survives a backend restart with no `BACKTEST_STORE_DIR`") is the *single new
> DoD-critical behavioral guarantee* of this iteration and it was **SKIPPED**,
> not verified through the browser. Executing it requires a destructive infra
> operation (kill the shared backend on :8691 + move `apps/backend/.env`) that
> the runtime safety policy denied and that this browser-QA agent is not
> authorized to perform unattended. The restart-durability gate must therefore
> rest on **functional pytest TC-08 (BASE_DIR absolute & not `/tmp` with env
> unset) and TC-09 (restart round-trip at the store layer)** — which the UI
> test plan itself designates as the authoritative deterministic proof. Strong
> corroborating evidence is recorded below (UT-10 PASS, on-disk durable path,
> code default). No product regression was observed.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | App shell loads with config bar, chat, history | smoke | P1 | Header "Finovae Strategy Platform" + v0.3.0 + Sessions; config bar (Symbol/Timeframe 1m..1D/Start/End/Capital/Exchange); left builder/activity; right iterations; strategy box; no error | All present; header "Finovae Strategy Platform" + "v0.3.0" + "Sessions 16"; TF buttons `1m 5m 15m 1h 4h 1D`; Start/End/Capital/Exchange; placeholder "Describe a trading strategy..."; console clean; no error overlay | **PASS** | UT-01-result.png, UT-01-empty-state.png |
| UT-02 | J-01 cold backtest from NL strategy | happy-path | P1 | Green completion banner; "Iterations (1)" card with params chip + metrics row; detail = params card + drawn Equity Curve + Trade History table w/ rows; new run in history | Cold run completed. Green banner "-10.60% return, 42 trades, 57% win rate, -0.80 sharpe". Card: "BTC 1h RSI Mean Reversion", chip `BTC/USDT · 1h · 2023-01-01 – 2023-06-01 · $1,500`, row `-10.60% | -72.72% vs BM | 42 trades | DD -23.8% | WR 57% | SR -0.80`. Detail: params card exact match, Equity Curve drawn (recharts), Trade History (42 trades) 25 rows. "Iterations (1)" (was none) | **PASS** | UT-02-result.png, UT-02-result-full.png, UT-02-config.png, UT-02-history-list.png |
| UT-03 | J-06 identical warm re-run + recorded | happy-path | P1 | 2nd run Complete, "Iterations (2)", metrics IDENTICAL to 1st, equity/trades identical, ≥ as fast | "Iterations (2)"; 2nd "Re-run" card byte-identical: Return -10.60%, vs BM -72.72%, 42 trades, DD -23.8%, WR 57%, SR -0.80, Annual -23.6%, Beta 0.27, AvgDur 1.4d, Commissions $45.67, FeeDrag -3.04%, Benchmark 62.12%, Monthly `11.7/-10.9/-3.6/-6.2/-0.1/-0.6`, 42-trade history. Cold-vs-warm determinism confirmed via UI. Warm path corroborated: single Parquet `/tmp/market_data/BTC_USDT/1h.parquet` existed before rerun | **PASS** | UT-03-rerun-detail.png, UT-03-result.png, UT-03-progress.png |
| UT-04 | J-02 open prior run, detail reloads | regression | P1 | Past card opens IterationDetailView w/ params, metrics, Equity Curve, Trade History, Strategy Script collapsible; no 404/blank/zeros; back arrow returns to intact list; 2nd past run shows own detail | Older card → detail: BTC/USDT, 1h, 2023-01-01 – 2023-06-01, $1,500, Annual -23.6%, 42 trades, Benchmark 62.12%, Equity drawn, Trade History (42) 25 rows, Strategy Script collapsible present, no 404, not all-zero. Back arrow → "Iterations (2)" intact; second card opens its own detail | **PASS** | UT-04-prior-run-detail.png |
| UT-05 | J-02 durability across backend restart (no BACKTEST_STORE_DIR) | regression | P1 (DoD-critical) | After backend restart with `BACKTEST_STORE_DIR` unset + reload, same session + same iteration count; prior run still renders full detail | **NOT EXECUTED** — restart requires killing the shared QA backend (pid 597293/:8691) and moving `apps/backend/.env`; blocked by environment-safety policy, no interactive user to authorize in automated pipeline. Strong corroboration recorded (see Skipped section) | **SKIPPED** | (corroborating: UT-10-result.png; on-disk `.data/backtests/live/.../iterations/`) |
| UT-06 | J-03 walk-forward renders fully | regression | P1 | WFE badge, OOS aggregate row, per-window table ≥1 row, Combined OOS Equity Curve; no "No windows completed"/failure | WFE badge **"WFE 1.15 ✓"** (emerald); OOS Return -5.12%, OOS Sharpe -1.25, OOS Win Rate 60.0%, OOS Max DD -9.22%; per-window table **2 rows** (headers `# IS Period OOS Period IS Return OOS Return IS Sharpe OOS Sharpe IS Trades OOS Trades`); "Combined OOS Equity Curve (2 windows chained)" drawn; no "No windows completed", no failure. **Deviation:** IS/OOS set to 3/1 (not plan's 6/3) — see note | **PASS** | UT-06-walk-forward.png, UT-06-walk-forward-vp.png |
| UT-07 | J-04 AI insights ≥1 suggestion | regression | P1 | Blue insights box w/ insight sentence + ≥1 clickable suggestion pill; not empty; no error | Blue box `bg-blue-50 border-blue-200`; insight "The strategy lost 10.60% over 42 trades, with a Sharpe ratio of -0.80 and profit factor of 0.82…"; **20 suggestion pills** (Add Trend Alignment Filter, Tighten Exit Logic, Volatility-Based Stops, Relax RSI Entry Threshold, …); not empty, no error | **PASS** | UT-07-insights.png |
| UT-08 | Symbol format inline validation | validation | P2 | Red "Must be BASE/USDT format (e.g. PEPE/USDT)" + red border on `BTC`; correcting clears both | Typing `BTC` → message "Must be BASE/USDT format (e.g. PEPE/USDT)" + red border `rgb(248,113,113)`. Correcting to `BTC/USDT` → message gone, border back to `rgb(226,232,240)`, no reload/crash | **PASS** | UT-08-symbol-validation.png |
| UT-09 | Non-existent symbol error surfaced | error | P2 | Red activity entry "Invalid symbol: …"; app responsive; no false Complete card; no uncaught error | `ZZZZ/USDT` submit → red "⚠ Invalid symbol: ZZZZ/USDT not found on Binance" in activity log; textarea re-enabled; no false success card; no Vite error overlay | **PASS** | UT-09-invalid-symbol.png |
| UT-10 | History persists across page refresh | regression | P1 | After F5, same session active, "Iterations (N)" same count; clicking iteration opens full detail; not lost | After reload: same session, **"Iterations (2)"** (not "No Iterations Yet"), both cards present, 17 sessions; clicking iteration → full detail (BTC/USDT, 1h, 2023-01-01–2023-06-01, $1,500, 42 trades, 25 rows, Equity drawn). localStorage empty → served from durable backend store | **PASS** | UT-10-result.png, UT-10-after-refresh.png |
| UT-11 | Primary journey discoverable | ux | P3 | Empty state: "Strategy Builder", "N strategies for <sym> · <tf>", clickable card grid, strategy box; config bar above fold; Sessions in header | New session empty state: "Strategy Builder", subline "20 strategies for BNB//USDT · 4h", visible clickable card grid (VWAP Reversion, Ichimoku Breakout, Donchian Breakout, OBV Divergence, Williams %R Reversal, Keltner Squeeze, ADX Trend Strength, CCI Mean Reversion, …), "Describe a trading strategy..." box, config bar at y=74px (above fold) w/ all 6 labels, "Sessions" control in header, "No Iterations Yet". Card-click run not triggered (P3 optional sanity; avoids extra LLM cost — structural discoverability fully verified) | **PASS** | UT-11-discoverability.png, UT-11-empty-state.png |

---

## Passed Tests

### UT-01 — App shell loads with config bar, chat, and history
**Verdict:** PASS
**Evidence:** `reports/qa/goal-money-billions-iter-1-evidence/UT-01-result.png`, `UT-01-empty-state.png`
- Header "Finovae Strategy Platform" + "v0.3.0" + "Sessions" button (with count badge).
- Config bar: Symbol, Timeframe buttons `1m 5m 15m 1h 4h 1D`, Start, End, Capital, Exchange.
- Left: Strategy Builder / activity log. Right: iteration list / "No Iterations Yet". Strategy box placeholder "Describe a trading strategy...".
- Browser console clean (no errors); no red error overlay; no blank screen.

### UT-02 — J-01: Run a backtest from a natural-language strategy (cold run)
**Verdict:** PASS
**Evidence:** `UT-02-result.png`, `UT-02-result-full.png`, `UT-02-config.png`, `UT-02-history-list.png`
- Genuine cold cache (no `BTC/USDT 1h` Parquet existed pre-run). Config set BTC/USDT · 1h · 2023-01-01→2023-06-01 · $1,500 in a fresh session; NL strategy submitted via Enter.
- Run reached completion: green emerald banner "-10.60% return, 42 trades, 57% win rate, -0.80 sharpe".
- "Iterations (1)" (was "No Iterations Yet"); card shows status Complete, strategy name, params chip `BTC/USDT · 1h · 2023-01-01 – 2023-06-01 · $1,500`, metrics row `-10.60% | -72.72% vs BM | 42 trades | DD -23.8% | WR 57% | SR -0.80`.
- Detail view: "Backtest parameters" card exactly matches config; Equity Curve chart drawn (recharts SVG, axes Jan 1–Jun 1 2023 / $0–$1.8K); Trade History (42 trades) table with 25 rendered rows; Strategy Script collapsible; Strategy Rating 2/5; full metrics grid (Annual -23.6%, Alpha -57.99%, Beta 0.27, AvgDur 1.4d, Commissions $45.67, FeeDrag -3.04%, Benchmark 62.12%).
- Corroboration: single-file Parquet `/tmp/market_data/BTC_USDT/1h.parquet` created by this run (anti-goal: one Parquet per (symbol,timeframe), no per-day fan-out).

### UT-03 — J-06: Identical warm re-run completes, is identical, and is recorded
**Verdict:** PASS
**Evidence:** `UT-03-rerun-detail.png`, `UT-03-result.png`, `UT-03-progress.png`
- "Rerun" clicked on the UT-02 card → second iteration created, reached Complete, "Iterations (2)" (original retained as compact card).
- Cold-vs-warm determinism verified through the UI — every metric byte-identical to UT-02: Total Return -10.60%, vs-BM -72.72%, 42 trades, DD -23.8%, WR 57%, SR -0.80, Annual -23.6%, Beta 0.27, AvgDur 1.4d, Commissions $45.67, FeeDrag -3.04%, Benchmark 62.12%, Monthly 2023 `11.7/-10.9/-3.6/-6.2/-0.1/-0.6`, Trade History 42 trades / 25 rows, Equity Curve identically drawn.
- Warm path corroborated: `/tmp/market_data/BTC_USDT/1h.parquet` already existed before the rerun (covering cache → no Binance re-fetch needed). Speed treated as warning-only per plan; determinism is the decisive proof and it held exactly.

### UT-04 — J-02: Open a prior run from history; spec/metrics/trades reload
**Verdict:** PASS
**Evidence:** `UT-04-prior-run-detail.png`
- Older/past iteration card opened IterationDetailView: BTC/USDT · 1h · 2023-01-01–2023-06-01 · $1,500, Annual -23.6%, 42 trades, Benchmark 62.12%, Equity Curve drawn, Trade History (42) 25 rows, Strategy Script collapsible present.
- No "not found"/404/blank/all-zero — reloaded from the durable session store (highest-risk persistence path; no regression).
- Back arrow returned to intact "Iterations (2)" list; selecting the other past card opened its own detail.

### UT-06 — J-03: Walk-forward analysis renders fully
**Verdict:** PASS
**Evidence:** `UT-06-walk-forward.png`, `UT-06-walk-forward-vp.png`
- WFE badge **"WFE 1.15 ✓"** (emerald, ≥0.50).
- OOS aggregate row: OOS Return -5.12%, OOS Sharpe -1.25, OOS Win Rate 60.0%, OOS Max DD -9.22%.
- Per-window table populated with **2 data rows** under headers `# | IS Period | OOS Period | IS Return | OOS Return | IS Sharpe | OOS Sharpe | IS Trades | OOS Trades`.
- "Combined OOS Equity Curve (2 windows chained)" chart drawn. No "No windows completed.", no "Walk-forward validation failed". Rewritten loader's multi-window fetch/merge path works through the UI.
- **Documented deviation (not a defect):** the plan's literal IS=6/OOS=3 (9 months) cannot form any window on the UT-02 iteration's deliberately-small 5-month range (2023-01-01→2023-06-01) — with 6/3 the UI correctly showed "No windows completed. Not enough data". This is a test-plan internal tension (UT-02 picks a small range for fast cold fetch; UT-06 references it with 6/3). To exercise journey J-03 truthfully on the available data, IS/OOS were set to **3/1** (4 months ≤ 5), which produced a real, fully populated walk-forward result. The journey assertion (WFE badge + ≥1 window row + combined OOS curve) is satisfied.

### UT-07 — J-04: AI insights render at least one ranked suggestion
**Verdict:** PASS
**Evidence:** `UT-07-insights.png`
- Blue insights box (`bg-blue-50 border border-blue-200`) with a full insight sentence ("The strategy lost 10.60% over 42 trades, with a Sharpe ratio of -0.80 and profit factor of 0.82, so the edge is currently negative despite a 57.14% win rate. The 23.83% max drawdown is material…").
- 20 clickable suggestion pills present (Add Trend Alignment Filter, Tighten Exit Logic, Volatility-Based Stops, Relax RSI Entry Threshold, Add Time-Based Exit, Tune RSI Lookback, Use Regime Filter, Scale Position Size, Add Partial Take Profit, Add Oversold Confirmation, …). Panel not empty; no error in place of suggestions.

### UT-08 — Symbol field rejects non-`BASE/USDT` input with an inline error
**Verdict:** PASS
**Evidence:** `UT-08-symbol-validation.png`
- Typing `BTC` (no `/USDT`) → red message "Must be BASE/USDT format (e.g. PEPE/USDT)" below the field; input border red `rgb(248,113,113)`.
- Correcting to `BTC/USDT` cleared the message and reset the border to `rgb(226,232,240)`; no page reload, no crash.

### UT-09 — Non-existent symbol surfaces a backend error without crashing
**Verdict:** PASS
**Evidence:** `UT-09-invalid-symbol.png`
- `ZZZZ/USDT` (valid format, not a real pair) submitted → red activity entry "⚠ Invalid symbol: ZZZZ/USDT not found on Binance".
- App stayed responsive: strategy textarea re-enabled, config bar usable, no blank screen, no Vite error overlay/uncaught exception; no false "Complete" iteration created (count stayed 2).

### UT-10 — Session and run history persist across a browser refresh
**Verdict:** PASS
**Evidence:** `UT-10-result.png`, `UT-10-after-refresh.png`
- Pre-refresh: active session "BTC 1h RSI Mean Reversion" with "Iterations (2)"; localStorage held no session keys (server-persisted).
- After F5: same session restored, **"Iterations (2)"** (NOT "No Iterations Yet", session not lost), 17 sessions in picker; clicking a completed iteration re-opened full detail (params + 42-trade history + Equity Curve). History served from the durable backend session store via the normal path.

### UT-11 — Primary backtest journey is discoverable to a first-time user
**Verdict:** PASS
**Evidence:** `UT-11-discoverability.png`, `UT-11-empty-state.png`
- Fresh session empty state clearly presents "Strategy Builder", subline "20 strategies for BNB//USDT · 4h", a visible grid of clickable strategy cards (each with name + description + return/trades/SR), and the "Describe a trading strategy..." box.
- Config bar (Symbol/Timeframe/Start/End/Capital/Exchange) visible above the fold (y≈74px, no scroll); "Sessions" create/switch control in the header; right panel "No Iterations Yet" guidance.
- The one-click entry point (strategy card) and the typed-strategy path are both obvious without documentation. Note: actually triggering a card-run was intentionally not performed (P3 optional sanity; avoids extra LLM spend/iterations) — structural discoverability is fully verified and the same card-click run mechanism was already exercised indirectly via UT-02's submit path.

---

## Failed Tests

None. No test produced a FAIL.

---

## Skipped Tests

### UT-05 — J-02 durability: history survives a backend restart with no `BACKTEST_STORE_DIR`
**Verdict:** SKIPPED
**Reason:** Executing this test requires a destructive infrastructure operation — terminating the **shared QA backend process** (pid 597293 on `:8691`, managed by `browser-qa-phase.sh`) and **moving `apps/backend/.env`** aside so the backend restarts with `BACKTEST_STORE_DIR` unset / no `.env`. The runtime environment-safety policy **denied** this action ("destructive environment manipulation far beyond the browser-QA task… with no user authorization"), and this is an automated pipeline with no interactive user to grant authorization. Per browser-qa-agent rules, an unperformable infra step is recorded as SKIPPED with reason — it is **not** a product FAIL and **not** "frontend down". The denied command did not execute; `.env` and the backend were verified untouched afterward.

**This is the iteration's single DoD-critical new behavioral guarantee — it must be gated elsewhere.** The UI test plan explicitly assigns the deterministic restart proof to **functional pytest TC-08** (`session_store.BASE_DIR` absolute & not under `/tmp` with `BACKTEST_STORE_DIR` unset) and **TC-09** (write → re-resolve store fresh / simulated restart → read back intact). Downstream auditor / goal-evaluator should rely on those for the restart-durability gate.

**Strong corroborating evidence collected (durability NOT contradicted at any layer):**
1. **On-disk, non-`/tmp`, durable path confirmed.** The two iterations from UT-02/UT-03 physically reside at
   `/home/dennisccy/Git/finovae_strategy_platform/.data/backtests/live/33164636-db57-47f5-b35e-f96eb44dc2c2/iterations/001_…` and `002_…`
   — an in-repo, durable, non-volatile location (the exact DoD target path), with `session.json`.
2. **Code default resolves to that same path with the env var unset.** `apps/backend/backend/session_store.py`:
   `_DEFAULT_STORE_DIR = Path(__file__).resolve().parents[3] / ".data" / "backtests"` and
   `BASE_DIR = Path(os.environ.get("BACKTEST_STORE_DIR") or _DEFAULT_STORE_DIR)`.
   With `BACKTEST_STORE_DIR` unset, `BASE_DIR` resolves (CWD-independent, from `__file__`) to the **same** `<repo>/.data/backtests` the `.env` advertises — so a no-`.env` restart reads the identical store; history cannot vanish to `/tmp`.
3. **UT-10 PASS** already demonstrates the same session + "Iterations (2)" + full prior-run detail survive a full browser reload, served from the durable backend session store (localStorage was empty — persistence is server-side, not client cache).
4. The backend serves `iterationHistory` length **2** for the session via `/api/sessions/{id}` (durable store reachable and intact).

**Residual gap:** the literal *process restart with `BACKTEST_STORE_DIR` unset* was not exercised through the running UI. Functional pytest TC-08/TC-09 are the authoritative gate for that exact behavior.

---

## Notes / Deviations

- **UT-05 not executed** — environment-safety policy blocked the required backend kill + `.env` move (see Skipped section). Flagged for the auditor; pytest TC-08/TC-09 own this gate.
- **UT-06 IS/OOS adapted** to 3/1 (from the plan's 6/3) because the UT-02 reference iteration uses a deliberately small 5-month range and 6/3 (9 months) yields zero windows by design; 3/1 truthfully exercises journey J-03 and produced a fully populated walk-forward (WFE 1.15 ✓, 2 windows, combined OOS curve). Not a product defect — a test-plan internal data-range tension.
- **UT-11 card-click run** not triggered (P3 optional sanity) to avoid extra LLM spend and surplus iterations; structural discoverability fully verified and the card→run mechanism is the same submit path proven in UT-02.
- **Auto Run feature observed:** the app shows an "Auto Run" control; in this session it did not spontaneously spawn extra iterations beyond the explicit cold run + explicit Rerun (iteration count moved exactly none→1→2 as driven). No interference with determinism verification.
- **System left as found:** `.env` intact (972 B, original mtime), backend healthy on `:8691` (HTTP 200, pid 597293), frontend healthy on `:3691` (HTTP 200). No source files modified. Test artifacts: 1 new session (33164636) with 2 iterations under the durable store + 1 empty UT-11 session — normal app data, no cleanup required.
- **Anti-goal corroboration (user-visible side):** after the warm run, exactly one `*.parquet` exists for `(BTC/USDT, 1h)` at `/tmp/market_data/BTC_USDT/1h.parquet` (single-file-per-(symbol,tf), no per-day fan-out); session/run history persists under non-`/tmp` `<repo>/.data/backtests`.

---

## Environment

- **Frontend URL:** http://localhost:3691 (HTTP 200)
- **Backend:** http://localhost:8691 (`/api/sessions` HTTP 200; note `/health` route returns 404 — not used by the app; API healthy)
- **Browser:** Chrome via `mcp__plugin_superpowers-chrome_chrome__use_browser` (CDP)
- **Test Date:** 2026-05-18
- **Evidence directory:** `reports/qa/goal-money-billions-iter-1-evidence/` (21 screenshots)
- **Journey coverage:** J-01 → UT-02 (PASS); J-06 → UT-03 (PASS); J-02 → UT-04 (PASS), UT-10 (PASS), **UT-05 (SKIPPED — restart-durability deferred to pytest TC-08/TC-09)**; J-03 → UT-06 (PASS); J-04 → UT-07 (PASS). Robustness UT-08/UT-09 (PASS); discoverability UT-11 (PASS).
- **P1 status:** UT-01, UT-02, UT-03, UT-04, UT-06, UT-07, UT-10 PASS; UT-05 SKIPPED (infra-authorization, corroborated). No P1 failed.
