# Goal Iteration 0 (financial_free) — Baseline UI/Journey Test Results

**Phase:** goal-financial_free-iter-0 (baseline assessment, lean, verify-only)
**Date:** 2026-05-23
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** FAIL

<!-- Baseline outcome: J-01..J-06 already implemented (PASS); J-07..J-16 fail-by-absence (net-new scope to build). FAIL = not all target journeys pass / goal not yet achieved. This is the expected, useful baseline signal — it separates "already implemented" from "yet to build" for the goal-evaluator. NOT a regression. -->

**Overall:** 6/16 target journeys pass · 10/16 fail-by-absence · 0 skipped

- **Already implemented (PASS):** J-01, J-02, J-03, J-04, J-05, J-06 (matches the prior `money-billions` superset).
- **Fail-by-absence (to build):** J-07 … J-16 — the headless, token-budgeted automated session (Layer 1 + Layer 2). `POST /api/auto-sessions` returns **404**; no auto-session/optimizer routes exist.

> **Verification method note (important for the evaluator).** The frontend bundle is **healthy** and renders the complete, data-populated UI (DOM-captured — see `UT-J-05-rendered-ui-domtext.txt`). However, this **headless Chrome MCP tab runs backgrounded (`document.visibilityState === "hidden"`)**, which throttles the app's async-init commit and the GPU compositor: React mounts the full app for ~100–300 ms then the tree is torn down before paint, so **pixel screenshots came back blank** despite a correct DOM. This is an **automation-environment limitation, not an application defect** (modules serve HTTP 200, import without error, and rendered the full UI once with live API data). Each journey was therefore verified against the **authoritative backend** — the exact endpoints the UI calls (`generate-strategy` → `execute-backtest` SSE, `execute-walk-forward`, `generate-insights`, the lazy `sessions/{id}/iterations/{id}` path) — plus the confirmed UI render. Evidence is HTTP status codes, parsed response payloads, and the captured rendered DOM.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-J-01 | Run a backtest from natural language | happy-path | P1 | NL run → non-empty metrics + equity curve + trades table; new run_id in history | `generate-strategy` 200 (compiled spec+script, 4.6s); UI path `execute-backtest` (SSE, 103 events) → **143 trades**, total_return +5.97%, equity 10000→10596 (8784 pts), rating present, run_id `db758f99` in `/api/runs` | **PASS** | `api-probe-and-journey-evidence.md` §J-01; `UT-J-05-rendered-ui-domtext.txt` |
| UT-J-02 | Inspect & browse run history | happy-path | P1 | Open a prior run → strategy spec, metrics, trades reload into detail (lazy, not eager list-parse) | `/api/sessions` → 122 lightweight tabs (no embedded arrays); `/api/sessions/{id}/iterations/{id}` 200 → full result (metrics), 21 trades, equity 912 pts, scriptCode, 5-cat rating, walkForwardResult, insights | **PASS** | `api-probe-and-journey-evidence.md` §J-02 |
| UT-J-03 | Walk-forward validation | happy-path | P1 | WFE badge (g≥.5/y.3–.5/r<.3) + per-window IS/OOS table + combined OOS equity curve | `execute-walk-forward` (SSE) 200 → **wfe=0.4218 (yellow)**, **8-window** IS/OOS table, combined OOS equity **720 pts**, combined_oos_return +4.66% | **PASS** | `api-probe-and-journey-evidence.md` §J-03 |
| UT-J-04 | AI insights | happy-path | P1 | ≥1 ranked suggestion; OOS-aware when walk-forward data exists | `generate-insights` 200 (7.2s) → **10 ranked suggestions** {title,description,prompt}; **OOS-aware=TRUE** with WF attached (e.g. "Add Trend Regime Filter") | **PASS** | `api-probe-and-journey-evidence.md` §J-04 |
| UT-J-05 | Reference data loads | smoke | P1 | `/api/symbols` + `/api/timeframes` populate symbol & timeframe controls | `/api/symbols`=26 (BTC/USDT…), `/api/timeframes`=6 (1m–1d); rendered UI shows Symbol + Timeframe (1 Minute…1 Day) + model selector (matches `/api/models`) | **PASS** | `UT-J-05-rendered-ui-domtext.txt`; `api-probe-and-journey-evidence.md` §J-05 |
| UT-J-06 | Warm-cache re-run end-to-end | happy-path | P1 | 2nd identical run completes, renders metrics+equity+trades w/o error, in history | Warm `execute-backtest` on cached BTC/USDT 1h 2024 → 200 in **10.2s (vs 43.5s first)**, errors[], 143 trades, equity 8784 pts, run_id `7ba262dd` in `/api/runs`; no Binance re-fetch | **PASS** | `api-probe-and-journey-evidence.md` §J-06 |
| UT-J-07 | Start headless automated session via API (pinned) | happy-path | P1 | 200 + sessionId + running/queued; appears in `/api/sessions` | `POST /api/auto-sessions` (pinned body) → **HTTP 404 Not Found**; route absent from OpenAPI | **FAIL** (by absence) | `api-probe-and-journey-evidence.md` §GATE |
| UT-J-08 | Track automated run live in UI | happy-path | P1 | Running indicator + ≥1 iteration w/ result+suggestions + terminal, no reload | Endpoint to start a headless run is absent (404); nothing to track | **FAIL** (by absence) | §GATE |
| UT-J-09 | Auto chain stops on target/budget; best marked | happy-path | P1 | Terminal status + stop reason (criteria-met/budget-exhausted) + best iteration | Auto-session absent (404); no controller/stop-reason/best-marking surface | **FAIL** (by absence) | §GATE |
| UT-J-10 | Backend single source of truth (survives reload) | happy-path | P1 | Run continues server-side after tab reload | Auto-session backend loop absent (404). Today "Auto Run" is **in-browser** (`useBacktest.ts`, `IterationCard.tsx`) — backend-source-of-truth not yet built | **FAIL** (by absence) | §GATE; dev handoff probe |
| UT-J-11 | Stop a running automated session | happy-path | P1 | `stopped` terminal, no further iterations, best-so-far kept | `POST /api/auto-sessions/{id}/stop` → **HTTP 404**; no run to stop | **FAIL** (by absence) | §GATE |
| UT-J-12 | Open-universe run from objective+budget | happy-path | P1 | ≥2 distinct configs, terminal within budget, best by robust score | Auto-session absent (404); open-universe optimizer is a superset — not built | **FAIL** (by absence) | §GATE |
| UT-J-13 | AI-token/cost budget hard-enforced | happy-path | P1 | stop reason budget-exhausted; spend ≤ cap; no iters after cap | No automated run / no budget cost-tracker surface (404) | **FAIL** (by absence) | §GATE |
| UT-J-14 | Staged screening — full cost only on survivors | happy-path | P1 | SCREEN stage (cheap) + PROMOTE top-k (k<screened); WF/strong model only on promoted | No SCREEN/PROMOTE staging surface (auto-session absent, 404) | **FAIL** (by absence) | §GATE |
| UT-J-15 | Learns from global history; opt-out-able | happy-path | P1 | run #2 cites prior-session warm start; run #3 (this-run) shows none | No automated planner/history-scope surface (auto-session absent, 404) | **FAIL** (by absence) | §GATE |
| UT-J-16 | Robust objective gates overfit | happy-path | P1 | best satisfies WFE≥thr + min-trades, scored from WF OOS; raw-return/over-leveraged not "best" | No automated leaderboard/robust-selection surface (auto-session absent, 404) | **FAIL** (by absence) | §GATE |

---

## Passed Tests

### UT-J-01 — Run a backtest from natural language
**Verdict:** PASS
**Evidence:** `reports/qa/goal-financial_free-iter-0-evidence/api-probe-and-journey-evidence.md` §J-01
- The frontend's real flow is **`generate-strategy` → `execute-backtest`** (SSE) — confirmed at `apps/frontend/src/hooks/useBacktest.ts:987`.
- `generate-strategy` compiled the canonical RSI prompt into a correct `StrategySpec` + Python script in 4.6 s → **`OPENAI_API_KEY` is configured and working** (so J-01/J-03/J-04/J-06 are **not** env-gated here).
- `execute-backtest` (EMA 10/30, BTC/USDT 1h, 2024) streamed 103 events and returned **143 trades**, total_return +5.97 %, an 8784-pt equity curve (10000→10596, not flat), a 5-category rating, and `run_id db758f99`, which then appears in `GET /api/runs`.
- **Observation (non-blocking):** the separate `POST /api/run-backtest` NL convenience endpoint (NOT used by the UI) completes 200 with a real benchmark (+121 % BTC 2024) but returns **0 trades / flat equity** for the generated RSI and EMA strategies (errors `[]`). Recorded for the evaluator; it does not affect the UI journey, which uses `execute-backtest`.

### UT-J-02 — Inspect and browse run history
**Verdict:** PASS
**Evidence:** `…/api-probe-and-journey-evidence.md` §J-02
- `GET /api/sessions` returns **122 lightweight tabs** (`{id,name,lastAccessedAt}`) — no embedded per-iteration result/rating arrays (lazy list path).
- `GET /api/sessions/{id}/iterations/{iteration_id}` returns **HTTP 200 with full detail**: result metrics, 21 trades, 912-pt equity curve, `scriptCode`, 5-category `rating`, `walkForwardResult`, and `insights` — the lazy per-iteration reload the detail view uses.
- Signal recorded (not verdicted, per verify-only spec): the single-session open `GET /api/sessions/{id}` payload is ~245 KB and embeds `equity_curve` — worth a coherence-auditor look at the eager-load anti-goal, independent of this functional pass.

### UT-J-03 — Walk-forward validation
**Verdict:** PASS
**Evidence:** `…/api-probe-and-journey-evidence.md` §J-03
- `execute-walk-forward` (IS=3 mo / OOS=1 mo over 2024) returned **wfe = 0.4218** (→ yellow badge, 0.3–0.5 band), an **8-window IS/OOS table** (each window carries is_/oos_ start, end, sharpe, total_return, num_trades + an `oos_equity_curve`), and a **combined OOS equity curve of 720 points** (combined_oos_return +4.66 %, combined_oos_sharpe 0.370).

### UT-J-04 — AI insights
**Verdict:** PASS
**Evidence:** `…/api-probe-and-journey-evidence.md` §J-04
- `generate-insights` (real backtest_result with 143 trades + attached walk_forward_result) returned **10 ranked suggestions** (`{title, description, prompt}`) in 7.2 s, and the suggestions are **OOS-aware** (explicitly reference walk-forward / out-of-sample), satisfying the "OOS-aware when walk-forward data exists" clause. Example: *"Add Trend Regime Filter — only allow a long entry when price is above the 200-EMA…"*. This is content-distinct from the J-03 walk-forward evidence (prior-session J-04 distinctness lesson honored).

### UT-J-05 — Reference data loads
**Verdict:** PASS
**Evidence:** `reports/qa/goal-financial_free-iter-0-evidence/UT-J-05-rendered-ui-domtext.txt`
- `GET /api/symbols` → 26 symbols (BTC/USDT, ETH/USDT, …); `GET /api/timeframes` → 6 (1m–1d).
- The rendered UI (DOM-captured) shows the Symbol control and the Timeframe control populated with **1 Minute / 5 Minutes / 15 Minutes / 1 Hour / 4 Hours / 1 Day** (exactly the endpoint values), plus an Exchange list and a model selector matching `/api/models` (GPT-5.4 Mini default + Claude Haiku/Sonnet/Opus) — controls are sourced from the endpoints, not hardcoded.

### UT-J-06 — Warm-cache re-run works end-to-end
**Verdict:** PASS
**Evidence:** `…/api-probe-and-journey-evidence.md` §J-06
- A second `execute-backtest` on the already-cached **BTC/USDT 1h 2024** completed in **10.2 s (vs 43.5 s for the first, cold-ish run)** with errors `[]`, **143 trades**, an 8784-pt equity curve, and `run_id 7ba262dd` recorded in `/api/runs`. No Binance re-fetch occurred (the OHLCV Parquet cache is warm; the benchmark computes the real +121 % 2024 BTC return). Engine determinism is covered by the passing `tests/test_determinism.py`.

---

## Failed Tests

> All ten failures share a single root cause: **the headless automated-session API does not exist yet** (expected — net-new scope per the iter spec). The probe was run first to avoid spending AI tokens on a non-existent optimizer.

### UT-J-07 … UT-J-16 — Headless automated session (Layer 1 Foundation + Layer 2 Optimizer)
**Verdict:** FAIL (fail-by-absence — feature not built)
**Failure:** `POST /api/auto-sessions` returns **HTTP 404 `{"detail":"Not Found"}`** for both an empty body and a pinned/objective body; `POST /api/auto-sessions/{id}/stop` also returns **404**. The backend OpenAPI route table contains **no route matching `auto`**, and no optimizer / controller / budget / planner modules exist (static dev probe confirms the same).
**Evidence:** `reports/qa/goal-financial_free-iter-0-evidence/api-probe-and-journey-evidence.md` §GATE

**Steps taken:**
1. `curl -X POST http://localhost:8692/api/auto-sessions -d '{}'` → 404.
2. `curl -X POST http://localhost:8692/api/auto-sessions -d '{"objective":"robust","budget":{"max_iterations":2}}'` → 404.
3. `curl -X POST http://localhost:8692/api/auto-sessions/nonexistent/stop` → 404.
4. Dumped the OpenAPI path list → no `auto`-prefixed routes.

**Expected:** A working headless automated session (start → live track → stop → robust-best selection → budget enforcement → staged screening → global-history warm start → overfit gating).
**Actual:** The trigger endpoint is absent (404). Per-journey specifics:
- **J-10 partial-by-design:** today's "Auto Run" is an **in-browser** loop (`useBacktest.ts`, `IterationCard.tsx`); the backend-as-single-source-of-truth + survive-reload acceptance is not yet met (no backend loop). This is the expected baseline behavior to be subsumed.
- **J-12 … J-16** are a strict superset of the absent Layer-1 endpoint (open-universe search, hard token/USD budget, SCREEN/PROMOTE staging, global-history warm start, robust/WFE overfit gating) — all unbuilt.

---

## Skipped Tests

None. The frontend is running and Chrome MCP is available; no journey was skipped. (Pixel screenshots could not be produced — see the verification-method note above — but all journeys were exercised against the authoritative backend the UI calls.)

---

## Supplementary baseline checks (per iter spec DoD)

| Check | Result | Evidence |
|-------|--------|----------|
| Backend boots & serves `/docs` | **OK** — `GET http://localhost:8692/docs` → HTTP 200 | §boot |
| Backend unit suite | **124 passed, 1 failed** (5.90 s). Sole failure: `test_directions_cache.py::test_write_and_read_full_round_trip` (nice-to-have directions cache, goal Capability #10) | `/tmp/finovae_pytest_iter0.log` |
| Anti-goal invariant tests | **PASS** — `test_lookahead.py`, `test_determinism.py`, `test_sandbox.py` all pass | pytest log |
| `POST /api/auto-sessions` presence | **ABSENT** — 404; no auto-session routes | §GATE |
| Observable anti-goal signals | `BACKTEST_STORE_DIR` default non-`/tmp` (`<repo>/.data/backtests`); OHLCV single-Parquet per (symbol,timeframe); no SQLite/DB routes. Signal to note: session-open payload (~245 KB) embeds `equity_curve` (eager-load worth a coherence look) | dev handoff + §J-02 |

---

## Environment

- **Frontend URL:** http://localhost:3692 (Vite dev; proxies `/api` → backend `:8692`)
- **Backend URL:** http://localhost:8692 (uvicorn; `GOAL_SESSION_ID=financial_free`, this session's stack)
- **Browser:** Chrome via MCP — **tab backgrounded (`visibilityState=hidden`)**, which throttled the app's async-init commit + GPU compositing; DOM rendered correctly, pixel screenshots were blank (environment limitation, not an app defect).
- **OPENAI_API_KEY:** configured & working (proven functionally — `generate-strategy`/`generate-insights` returned real LLM output). J-01/J-03/J-04/J-06 are **not** env-gated in this environment.
- **Test Date:** 2026-05-23
- **Evidence directory:** `reports/qa/goal-financial_free-iter-0-evidence/`
  - `api-probe-and-journey-evidence.md` — decisive probe + per-journey API outputs
  - `UT-J-05-rendered-ui-domtext.txt` — captured rendered-UI DOM text (frontend health / reference-data population)
