# Baseline API & Journey Evidence — goal-financial_free-iter-0
Backend: http://localhost:8692  (frontend 3692 proxies here; GOAL_SESSION_ID=financial_free)
Date: 2026-05-23

## Boot / docs
- GET http://localhost:8692/docs -> HTTP 200 (backend boots, serves Swagger)

## J-07..J-16 GATE — POST /api/auto-sessions (probe-first)
- POST /api/auto-sessions  {}                                 -> HTTP 404 {"detail":"Not Found"}
- POST /api/auto-sessions  {"objective":"robust","budget":{"max_iterations":2}} -> HTTP 404 {"detail":"Not Found"}
- POST /api/auto-sessions/nonexistent/stop                    -> HTTP 404 {"detail":"Not Found"}
- OpenAPI route table contains NO route matching "auto" -> auto-session surface ABSENT.
=> J-07..J-16 fail-by-absence (net-new scope). No AI tokens spent on a non-existent optimizer.

## Backend unit suite (anti-goal invariants)
- `cd apps/backend && .venv/bin/python -m pytest -q` => 124 passed, 1 failed (5.90s)
- Sole failure: tests/test_directions_cache.py::test_write_and_read_full_round_trip (nice-to-have directions cache; goal Capability #10)
- PASSING: test_lookahead.py, test_determinism.py, test_sandbox.py (the lookahead / determinism / sandbox-security anti-goal invariants)

## J-05 — Reference data
- GET /api/symbols    -> 26 symbols [BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT, ...]
- GET /api/timeframes -> 6 [1m,5m,15m,1h,4h,1d]; UI controls show "1 Minute".."1 Day" (DOM-confirmed)
- GET /api/models     -> gpt-5.4-mini (default) + Claude Haiku/Sonnet/Opus (DOM-confirmed in model selector)

## J-01 — Run backtest from NL (real UI path: generate-strategy -> execute-backtest SSE)
- POST /api/generate-strategy {"natural_language":"Buy when RSI crosses below 30, sell when it crosses above 70"} -> HTTP 200, success, compiled StrategySpec + script (4.6s). OPENAI_API_KEY IS configured & working.
- Frontend calls POST /api/execute-backtest (apps/frontend/src/hooks/useBacktest.ts:987), SSE-streamed.
- execute-backtest (EMA 10/30 crossover, BTC/USDT 1h, 2024) -> 103 SSE events, final result:
    num_trades=143, total_return=+5.97%, sharpe=-0.125, max_drawdown=26.3%, win_rate=30.1%, profit_factor=1.15
    equity_curve=8784 pts (10000 -> 10596, NOT flat), trades=143 (full detail), rating present, run_id=db758f99
- run_id db758f99 appears in GET /api/runs. => J-01 PASS via UI path.
- NOTE/observation: POST /api/run-backtest (separate NL convenience endpoint, NOT used by UI) completes 200 with
    a real equity curve + correct benchmark (+121% BTC 2024) but yields 0 trades / flat strategy equity for the
    generated RSI and EMA strategies (errors:[]). Recorded as a baseline observation on the non-UI endpoint.

## J-02 — Browse run history (lazy)
- GET /api/sessions -> {tabs:[...]} 122 lightweight tabs {id,name,lastAccessedAt} — no embedded result/rating arrays.
- GET /api/sessions/{id} -> session w/ iterationHistory (6 lightweight summary nodes). (~245KB; embeds equity_curve — signal recorded, not verdicted per spec.)
- GET /api/sessions/{id}/iterations/{iter_id} -> HTTP 200, FULL detail: result(metrics), trades(21), equity_curve(912),
    scriptCode, rating(5-cat), walkForwardResult, insights. => lazy per-iteration detail works. J-02 PASS.

## J-03 — Walk-forward (POST /api/execute-walk-forward, SSE)
- (EMA 10/30, BTC/USDT 1h, 2024, is_months=3, oos_months=1) -> HTTP 200, final result:
    wfe=0.4218 (=> YELLOW badge, 0.3-0.5), combined_oos_return=+4.66%, combined_oos_sharpe=0.370,
    windows=8 (each is_/oos_ start,end,sharpe,total_return,num_trades + oos_equity_curve), combined OOS equity=720 pts.
  => all three acceptance elements (WFE badge, per-window table, combined OOS curve). J-03 PASS.

## J-04 — AI insights (POST /api/generate-insights)
- backtest_result(143 trades)+walk_forward_result attached -> HTTP 200 (7.2s), success, 10 ranked suggestions
    {title,description,prompt}; OOS-aware = TRUE (suggestions reference walk-forward/OOS). e.g. "Add Trend Regime Filter".
  => J-04 PASS.

## J-06 — Warm-cache re-run end-to-end
- Re-run execute-backtest on already-cached BTC/USDT 1h 2024 -> HTTP 200 in 10.2s (vs 43.5s first), errors:[],
    num_trades=143, equity_curve=8784, run_id=7ba262dd in /api/runs. No Binance re-fetch (data cache warm; benchmark real).
  => J-06 PASS. (Engine determinism covered by passing test_determinism.py.)

## Observable anti-goal signals (recorded, not verdicted — verify-only baseline)
- BACKTEST_STORE_DIR default non-/tmp (dev probe: <repo>/.data/backtests). OHLCV single-Parquet per (symbol,timeframe). No SQLite/DB routes.
- GET /api/sessions/{id} open payload ~245KB embeds equity_curve (eager-load signal worth a coherence look; per-iteration detail endpoint exists for lazy detail).
