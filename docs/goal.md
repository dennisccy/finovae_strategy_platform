# Project Goal

## Vision

Finovae Strategy Platform is an AI-assisted crypto strategy lab. A user describes a
trading strategy in plain English; an LLM (OpenAI `gpt-5.4-mini` by default; Claude selectable) compiles it into a
structured `StrategySpec`, a code generator emits a `signal(df, i) -> int` function, that
function executes inside a RestrictedPython sandbox, and it is backtested against real
Binance OHLCV data with a next-bar-open fill model (commission + slippage). The platform
returns an institutional-grade report — Sharpe, Sortino, max drawdown, profit factor, win
rate, equity curve, trade log, and a 5-category rating — with optional walk-forward
validation (rolling in-sample/out-of-sample windows, WFE) and AI-generated improvement
insights. There is no database: OHLCV is cached as Parquet and sessions/runs are persisted
to the filesystem.

## Target Users

- A solo systematic / retail-quant trader who wants to go from idea to validated backtest
  fast, without writing backtest-engine code.
- An AI tinkerer who wants a UI over LLM strategy compilation plus a skeptical critique
  loop (walk-forward, overfit detection, AI insights).
- The repository owner driving phased, agent-assisted development of the platform itself.

## Success Criteria

- A user submits a natural-language strategy plus parameters (symbol, timeframe, date
  range, initial capital) and receives a complete backtest: metrics, equity curve, trades.
- LLM-generated strategy code always runs inside the RestrictedPython sandbox — no file
  I/O, network, `exec`/`eval`, `__import__`, `open`, or `os` access.
- Backtests are deterministic and lookahead-free: a signal at bar `i` fills at bar `i+1`
  open; identical inputs yield identical outputs.
- Walk-forward validation runs on demand and yields a WFE score, a per-window table, and a
  combined OOS equity curve.
- The AI insights endpoint returns ranked improvement suggestions, OOS-aware when
  walk-forward data exists.
- Multi-session UI with file-backed persistent history; every run is addressable by
  `run_id`.
- The backend boots and serves `/docs`; all key `GET /api/*` endpoints respond in a
  running dev environment.

## Key Capabilities

1. NL → `StrategySpec` compilation — `apps/backend/strategy/compiler.py` (OpenAI `gpt-5.4-mini` default; Claude selectable).
2. `StrategySpec` → executable signal code — `apps/backend/strategy/codegen.py`,
   `strategy/script_generator.py`.
3. RestrictedPython sandbox execution with a 30s per-call timeout —
   `apps/backend/backend/sandbox.py`.
4. Binance OHLCV fetch with Parquet caching — `apps/backend/data/loader.py`,
   `data/binance_client.py`, `data/validation.py`.
5. Backtest engine: next-bar fills, commission/slippage, equity tracking —
   `apps/backend/backtest/engine.py`, `backtest/fills.py`.
6. Metrics + 5-category rating — `apps/backend/backtest/metrics.py`, `backtest/rating.py`.
7. Walk-forward validation (rolling IS/OOS, WFE) — `apps/backend/backtest/walk_forward.py`.
8. AI insights generation — `apps/backend/strategy/insights_generator.py`,
   `strategy/market_analyzer.py`.
9. SSE-streamed execution, multi-session + run history — `apps/backend/backend/api.py`,
   `backend/session_routes.py`, `backend/session_store.py`.
10. (nice-to-have) Directions cache — `apps/backend/backend/directions_routes.py`,
    `backend/directions_cache.py`.

## Non-Goals

- No live or paper trading and no broker/exchange order execution.
- No relational database or migrations (Parquet + file-based session/run store by design).
- No authentication, accounts, or multi-tenant isolation.
- No options/derivatives engine beyond the existing long + leverage fields.
- Not a real-time signal/alert or notification service.

## Constraints

- Backend: Python 3.11+, FastAPI, RestrictedPython, Anthropic/OpenAI SDKs.
- Frontend: Node.js 16+, Vite 5, React 18, TypeScript, Tailwind, Recharts.
- Strategy compilation and AI insights require `OPENAI_API_KEY` (default model
  `gpt-5.4-mini`); `ANTHROPIC_API_KEY` is only needed if a Claude model is
  selected. The backend boots without keys but those endpoints will fail.
- Depends on the public Binance REST API for market data.
- `apps/backend/shared/contracts.py` is a FROZEN interface contract — changes require
  architectural review.
- Deploy target: Vercel static build for the frontend (`vercel.json`); the backend's
  serverless entry exists (`apps/backend/api/index.py`) but is not deployed by the current
  monorepo Vercel config.
- One backtest per worker (`asyncio.Semaphore(1)`); scale with `WEB_CONCURRENCY`.

## Design Direction

- Visual style: a modern analytical workstation — dense, dark, data-forward dashboards;
  not a consumer trading-app aesthetic.
- Mood: professional, skeptical, evidence-driven.
- Layout: two panels — left = natural-language strategy chat + parameter controls;
  right = equity chart (Recharts) + metrics summary + trade list.
- Reference: the existing `apps/frontend` UI.

## Must-have user journeys

- **J-01: Run a backtest from natural language**
  - Steps:
    1. Open the app
    2. Enter "Buy when RSI crosses below 30, sell when it crosses above 70"
    3. Set symbol `BTCUSDT`, timeframe `1h`, a date range, and initial capital
    4. Submit
  - Acceptance: the results panel shows non-empty metrics, an equity curve, and a trades
    table, and a new `run_id` appears in history.

- **J-02: Inspect and browse run history**
  - Steps:
    1. Complete at least one backtest
    2. Open a prior run from the history list
  - Acceptance: the selected run's strategy spec, metrics, and trades reload into the
    detail view.

- **J-03: Walk-forward validation**
  - Steps:
    1. From a completed iteration, open its detail view
    2. Set IS/OOS window lengths
    3. Click "Run Walk-Forward"
  - Acceptance: a WFE badge (green ≥ 0.5 / yellow 0.3–0.5 / red < 0.3), a per-window
    table, and a combined OOS equity curve appear.

- **J-04: AI insights**
  - Steps:
    1. On a completed run, request insights
  - Acceptance: at least one ranked suggestion renders; suggestions are OOS-aware when
    walk-forward data exists.

- **J-05: Reference data loads**
  - Steps:
    1. Open the app and inspect the parameter controls
  - Acceptance: `/api/symbols` and `/api/timeframes` populate the symbol and timeframe
    controls.

## Anti-goals

- No hard-coded credentials, API keys, or tokens in source files (keys only via env /
  git-ignored `.env`).
- The RestrictedPython sandbox MUST block file I/O, network, `exec`/`eval`, `__import__`,
  `open`, and `os`.
- No lookahead: a generated signal must never observe future bars.
- No nondeterministic backtests (slippage is seeded; identical inputs → identical output).
- No dependency on a paid SaaS service other than Anthropic/OpenAI (already in
  Constraints).
- The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
