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
insights. There is no database: OHLCV is cached as a single Parquet file per (symbol,
timeframe), and sessions/runs are persisted to a durable filesystem location (never
volatile `/tmp`).

Strategy development is also available **headless via the API**: a single call starts an
automated, token-budgeted session that *searches an open universe* of symbols /
timeframes / leverage / strategy ideas, learns from prior sessions to spend tokens where
payoff is highest, and maximizes a robust walk-forward profit objective — producing the
same session, iteration, backtest, and suggestion records the UI renders.

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
- Repeated backtests on an already-fetched (symbol, timeframe, date range) load from
  the local Parquet cache with no Binance re-fetch and no per-day file fan-out; a warm
  load is at least 10× faster than the cold fetch.
- Opening a session or run history renders the list without parsing full per-iteration
  `result`/`rating` payloads; heavy iteration detail is fetched lazily on selection.
- Session and run history survive a backend restart (persisted outside volatile `/tmp`).
- One API call (no browser) starts an automated session that explores multiple distinct
  configs, runs to a terminal state (robust targets met or hard budget exhausted)
  server-side within the stated AI-token/cost budget, marks a best strategy by the
  robust objective, and shows all sessions/iterations/suggestions/leaderboard updating
  live in the existing UI.
- A second automated run with global history scope demonstrably warm-starts from prior
  sessions (prioritizes historically strong families) and is opt-out-able.

## Key Capabilities

1. NL → `StrategySpec` compilation — `apps/backend/strategy/compiler.py` (OpenAI `gpt-5.4-mini` default; Claude selectable).
2. `StrategySpec` → executable signal code — `apps/backend/strategy/codegen.py`,
   `strategy/script_generator.py`.
3. RestrictedPython sandbox execution with a 30s per-call timeout —
   `apps/backend/backend/sandbox.py`.
4. Binance OHLCV fetch with single-file Parquet caching per (symbol, timeframe),
   warm-cache reads with no re-fetch — `apps/backend/data/loader.py`,
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
11. Headless auto-optimizing strategy session — API-triggered two-level search: a
    config-search controller (history surrogate/bandit + cached LLM-planner) over an
    open, bounded universe, driving the existing generate→backtest→insights→iterate loop
    under staged cheap-first evaluation, model routing, and a hard AI-token/cost budget;
    selects the best strategy by a robust (walk-forward, WFE-gated, drawdown-penalized)
    objective; runs server-side and writes standard session artifacts that update live
    in the existing UI. Subsumes the previous in-browser "Auto Run" —
    `apps/backend/backend/api.py`, `backend/session_store.py`.

## Non-Goals

- No live or paper trading and no broker/exchange order execution.
- No relational database, SQLite, or migrations — OHLCV uses single-file Parquet;
  sessions/runs/directions use a durable file store by design.
- No authentication, accounts, or multi-tenant isolation.
- No options/derivatives engine beyond the existing long + leverage fields.
- Not a real-time signal/alert or notification service.
- Automated "profit" is backtested / walk-forward only — the chain never executes live
  or paper trades.
- No exhaustive grid over the entire exchange symbol list; automated exploration is
  bounded and budget-driven from a seed universe.
- No new datastore/queue/vector DB/scheduler; automated history learning reuses the
  existing file store; one automated run per API call.
- No multi-objective/Pareto optimization for the automated session (single robust scalar
  objective in v1).

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

## Product Shape
<!--
Seeds the goal-mode coherence blueprint (information architecture + data contract). The
goal-decomposer drafts runs/goal-session-<sid>/state/blueprint.md from this at baseline and the
coherence-auditor enforces it each iteration, so the same metric never differs across views.
-->

### Navigation / information architecture
- Single-page analytical workstation — one persistent two-panel shell, no multi-route nav
  (on mobile the panels collapse to an "Activity" / "Iterations" tab toggle).
- Header: brand + Session picker (switch between live sessions, manage the archive).
- Left — **Activity Log**: natural-language strategy prompt; backtest config bar (symbol, timeframe,
  date range, initial capital, leverage, `allow_short`); model selector; AI-generated insights &
  suggestions; cached strategy directions; automated-session (auto-run) controls.
- Right — **Iterations**: parent→child iteration history tree; per-iteration summary cards
  (strategy name, status, total-return badge).
  - **Iteration Detail** (opens from a card): backtest params; strategy script with diff vs parent;
    equity curve (Recharts); Walk-Forward analysis (IS/OOS windows, WFE); 5-category rating panel;
    trades table.
- Headless / API surface (Layer 1–2 journeys): adds no new screens — an automated session streams
  the same activity log and produces the same iteration/backtest/suggestion records the UI renders
  (backend is the single source of truth).

### Canonical values (single source of truth)
Each value below is computed in exactly one place and read everywhere from that source — a number
(e.g. Sharpe) must read identically on a summary card, the detail metrics grid, and the rating panel.
- **Backtest performance metrics** — computed once by `MetricsCalculator.calculate()`
  (`apps/backend/backtest/metrics.py`), carried on the frozen `BacktestResult` contract
  (`apps/backend/shared/contracts.py`), served by `POST /api/run-backtest` and
  `GET /api/sessions/{id}/iterations/{id}`: `total_return`, `max_drawdown`, `sharpe_ratio`,
  `sortino`, `calmar`, `profit_factor`, `win_rate`, `num_trades`, `equity_curve`,
  `unleveraged_return`, `margin_called`.
- **Walk-forward efficiency** — computed once into `WalkForwardResult`: `wfe`, `combined_oos_return`,
  `combined_oos_sharpe`, `combined_oos_win_rate`, `combined_oos_max_drawdown`.
- **5-category rating** — `StrategyRating` (`profitability`, `risk_resistance`, `risk_reward`,
  `win_rate_ev`, `liquidity`), derived from the same `BacktestResult` — never recomputed independently.
- **Shared records** — the file store (`session_store.py`) is the one source, surfaced read-only in
  the UI: session record, iteration record (`IterationNode`), backtest record (`BacktestResult`),
  suggestion record (insights/suggestions).
- **Budget counters** (headless/optimizer) — one authoritative counter per automated session for
  token spend, USD cost, and wall-clock; UI and API read the same values, never separate tallies.

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

- **J-06: Warm-cache re-run works end-to-end**
  - Steps:
    1. Run a backtest for `BTCUSDT` `1h` over a fixed date range; wait for results
    2. Run the same strategy with the same symbol/timeframe/date range again
  - Acceptance: the second run completes and renders metrics, an equity curve, and a
    trades table without error, and the run appears in history (warm local-cache path
    works end-to-end).

All automated-session journeys (J-07–J-16) MUST use tiny budgets (≤ 2 screen iterations,
a short date range, the cheapest model, lenient targets) so verification stays fast and
cheap. In `POST /api/auto-sessions` every search-space field is optional: a provided
field pins that dimension (cheap deterministic tests); omitting symbol/timeframe means
open-universe. Journeys are layered so the Foundation lands before the Optimizer.

**Layer 1 — Foundation (headless chain + live UI tracking)**

- **J-07: Start a headless automated session via the API (pinned config)**
  - Steps:
    1. `POST /api/auto-sessions` with a pinned config: natural-language strategy,
       `symbol`, `timeframe`, `start_date`, `end_date`, `initial_capital`, `model`,
       robust `targets`, and `budget` with `max_iterations: 2`
    2. Read the JSON response
    3. `GET /api/sessions` (or open the UI session list)
  - Acceptance: the response is HTTP 200 with a `sessionId` and a run state of `running`
    or `queued`; the same `sessionId` appears immediately in `GET /api/sessions` (a new
    session tab in the UI) with no browser interaction required to start it.

- **J-08: Track the automated run live in the UI**
  - Steps:
    1. Trigger a run as in J-07 (tiny budget)
    2. Open the UI and open the created session
    3. Observe the session without manually reloading the page
  - Acceptance: a run-status indicator shows "running"; at least one iteration with a
    backtest result and generated suggestions appears, and the status then reaches a
    terminal state — all without a manual page reload.

- **J-09: Automated chain stops on robust target or budget; best is marked**
  - Steps:
    1. `POST /api/auto-sessions` with lenient robust `targets` and a small `budget`
    2. Wait for the run to reach a terminal state
    3. Open the session in the UI
  - Acceptance: the session shows a terminal status with a visible stop reason
    (`criteria-met` or `budget-exhausted`) and a best iteration marked; when the stop
    reason is `criteria-met`, the best iteration's metrics satisfy every supplied robust
    target.

- **J-10: Backend is the single source of truth (button rewired, survives reload)**
  - Steps:
    1. In the UI, open a completed iteration and click "Auto Run" with a small budget
    2. Mid-run, reload the browser tab and reopen the session
  - Acceptance: the run continues and completes server-side — progress keeps advancing
    after the reload and the session reaches a terminal state — proving the loop is not
    driven by the browser.

- **J-11: Stop a running automated session**
  - Steps:
    1. Start a run with a budget large enough that it is still running
    2. `POST /api/auto-sessions/{sessionId}/stop` (or click the UI stop control)
    3. Reopen / observe the session
  - Acceptance: the run transitions to a `stopped` terminal state, no further iterations
    are appended after the stop, and the best-so-far iteration remains marked.

**Layer 2 — Optimizer (open-universe, token-budgeted search)**

- **J-12: Open-universe run from only an objective + budget**
  - Steps:
    1. `POST /api/auto-sessions` with no `symbol` or `timeframe` — only
       `objective: "robust"` and a small `budget` (optionally `history_scope`)
    2. Wait for a terminal state
    3. Open the session in the UI
  - Acceptance: at least two distinct configs (differing symbol and/or timeframe) appear
    as iterations; the run reaches a terminal state within budget; the best is marked by
    robust score.

- **J-13: AI-token/cost budget is hard-enforced**
  - Steps:
    1. Trigger a run with a tiny token / USD budget
    2. Wait for a terminal state
    3. Read the session status block
  - Acceptance: the stop reason is `budget-exhausted`; the recorded token/cost spend is
    ≤ the cap (within one-call tolerance) and visible in the status block; no iterations
    are added after the cap is reached.

- **J-14: Staged screening — full cost only on survivors**
  - Steps:
    1. Trigger an open-universe run
    2. Inspect the session activity log / status
  - Acceptance: the activity log shows a `SCREEN` stage with several cheap candidates and
    a `PROMOTE` stage applied to only the top-k (k < number screened); walk-forward and
    the stronger model appear only on promoted configs.

- **J-15: Learns from global history (warm start) and is opt-out-able**
  - Steps:
    1. Run #1 open-universe with a tiny budget; let it finish
    2. Run #2 with `history_scope: "global"`
    3. Run #3 with `history_scope: "this-run"`
  - Acceptance: run #2's activity log shows a planner decision citing prior-session
    performance and its first promoted config's family matches a top performer from run
    #1; run #3 shows no such cross-run citation (opt-out honored).

- **J-16: Robust objective gates overfit**
  - Steps:
    1. Trigger an open-universe run
    2. Inspect the leaderboard / best iteration in the UI
  - Acceptance: the marked best satisfies WFE ≥ threshold and the min-trades floor and
    its score derives from walk-forward OOS; a higher raw-return but WFE-failing or
    over-leveraged candidate is not selected as best (visible in the leaderboard /
    activity log).

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
- OHLCV market data MUST be cached as a single Parquet file per (symbol, timeframe) —
  NOT one CSV or file per calendar day — and MUST NOT be re-fetched from Binance when a
  covering local cache exists.
- `BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp`
  path; session and run history MUST survive a process restart.
- No relational database or SQLite is introduced for OHLCV, session, or directions
  storage (Parquet + durable file store only).
- `GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full
  per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded
  via the existing per-iteration endpoint.
- The automated chain MUST write the same session/iteration/activity/insights artifacts
  the UI renders (the existing file store) — no parallel store, no schema fork; a
  headless run MUST be indistinguishable in the UI from a manual one.
- Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND
  wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take
  "one more round" past the cap, even if targets are never met.
- The automated-session `autoRun` status MUST be persisted to the durable store and
  survive a worker restart and a browser reload; it MUST NOT live only in browser memory
  or a non-persisted in-process variable.
- After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST
  NOT run a second in-browser iterate loop.
- The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the
  RestrictedPython sandbox or the deterministic next-bar engine.
- Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly
  fan out across the entire exchange symbol list; expansion only as budget/history
  justify.
- The automated "best" MUST be selected by the robust objective (walk-forward OOS,
  WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing
  or over-leveraged candidate MUST NOT be marked best.
- Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are
  reserved for promoted candidates.
- Identical generated strategies (by code hash) MUST NOT be re-generated or
  re-backtested; the OHLCV Parquet cache MUST be reused across configs (no re-fetch when
  a covering cache exists).
- Global history learning MUST be read-only mining of the existing store (it MUST NOT
  mutate or delete prior sessions' artifacts); the `history_scope` opt-out MUST be
  honored.
- The LLM-planner / history context MUST use prompt caching; the leaderboard/history
  MUST NOT be re-sent uncached every round.
- The automated background job MUST NOT block the API event loop; the UI poll and other
  requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore
  respected).
- No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the
  automated session; optimizer state persists in the existing file store.
- API keys/secrets MUST NOT be written into the activity log or persisted in session
  artifacts.
