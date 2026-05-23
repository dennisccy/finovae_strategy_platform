# App Blueprint — financial_free

<!--
Coherence contract for the whole app. Drafted by the goal-decomposer at baseline; approve it once
(edit anything, then `--resume`); the coherence-auditor enforces it every iteration.

REVIEW CHECKLIST before you resume:
  1. Information Architecture — does every Must-have journey have an obvious home reachable in ≤2 clicks?
  2. Data Contract — is every "same-number-everywhere" value listed with exactly ONE computing source and
     ONE serving endpoint? The (planned) automated-session rows reserve canonical homes NOW so Layer 1/2
     work conforms (single source, no parallel store) — adjust them if you disagree with the chosen home.
-->

## Information Architecture

**Layout shell:** Single-page analytical workstation — one persistent two-panel shell, **no multi-route nav**. Header on top; Left = *Activity Log*; Right = *Iterations*. On mobile the two panels collapse to an "Activity" / "Iterations" tab toggle. The headless / API surface (J-07–J-16) adds **no new screens** — an automated session streams the same Activity Log and produces the same iteration / backtest / suggestion records the UI already renders (backend is the single source of truth).

**Navigation skeleton** (the persistent shell — every feature lives under one of these):

```
Finovae Workstation  (single page)
├── Header — brand + Session picker (switch live sessions, manage archive)
├── Left panel — Activity Log
│   ├── NL strategy prompt + Submit
│   ├── Backtest config bar (symbol, timeframe, date range, initial capital, leverage, allow_short)
│   ├── Model selector
│   ├── AI insights & suggestions
│   ├── Cached strategy directions
│   └── Automated-session controls (Auto Run start / stop; budget, objective, history_scope inputs)
└── Right panel — Iterations
    ├── Automated-session status strip (run state, stop reason, budget counters, best badge / leaderboard)
    ├── Iteration history tree (parent→child) + summary cards (strategy name, status, total-return badge)
    └── Iteration Detail (opens from a card — 1 click):
        params · strategy script + diff vs parent · equity curve (Recharts) ·
        Walk-Forward (IS/OOS windows, WFE) · 5-category rating panel · trades table
```

**Command endpoints (headless surface, not value-serving):** `POST /api/auto-sessions` (start; pinned or open-universe), `POST /api/auto-sessions/{id}/stop` (stop). These trigger the backend loop; the created session then appears in the Header Session picker and streams into the panels above — no dedicated screen.

**Feature / journey homes** (each reachable in ≤2 clicks from the persistent shell):

| Feature / journey | Canonical home | Panel / surface |
|---|---|---|
| J-01 Run a backtest from NL | NL prompt + config bar + Submit | Left — Activity Log |
| J-02 Inspect / browse run history | Iteration history tree → card → Iteration Detail | Right — Iterations |
| J-03 Walk-forward validation | Iteration Detail → Walk-Forward section | Right — Iteration Detail |
| J-04 AI insights | AI insights & suggestions | Left — Activity Log |
| J-05 Reference data loads | Backtest config bar controls | Left — Activity Log |
| J-06 Warm-cache re-run | Same Submit path as J-01 | Left — Activity Log |
| J-07 Start headless session (API) | `POST /api/auto-sessions` → Session picker | Header + headless API |
| J-08 Track automated run live | Automated-session status strip + live iteration cards | Right — Iterations |
| J-09 Stops on target/budget; best marked | Status strip (stop reason) + best badge | Right — Iterations |
| J-10 Backend single source of truth | Automated-session controls ("Auto Run") | Left — Activity Log |
| J-11 Stop a running session | Automated-session controls (Stop) + `POST .../stop` | Left — Activity Log + API |
| J-12 Open-universe run | Headless API → live iterations (distinct configs) | Header API + Right — Iterations |
| J-13 Budget hard-enforced | Status strip → budget counters | Right — Iterations |
| J-14 Staged screening (SCREEN/PROMOTE) | Activity Log stage entries | Left — Activity Log |
| J-15 Warm start from global history + opt-out | Activity Log planner-decision entries | Left — Activity Log |
| J-16 Robust objective gates overfit | Best badge / leaderboard | Right — Iterations |

## Data Contract

Every value that must read the same everywhere is registered with **one** computing source and **one** serving endpoint. No page may recompute or re-fetch these elsewhere; the UI may only re-format what the canonical endpoint returns. Automated runs MUST write these to the **same** file store the UI renders — no parallel store, no schema fork.

| Value / entity | Computed by (single module) | Served by (single endpoint) | Notes |
|---|---|---|---|
| Backtest performance metrics — `total_return`, `max_drawdown`, `sharpe_ratio`, `sortino`, `calmar`, `profit_factor`, `win_rate`, `num_trades`, `equity_curve`, `unleveraged_return`, `margin_called` | `apps/backend/backtest/metrics.py:MetricsCalculator.calculate()` → frozen `BacktestResult` (`apps/backend/shared/contracts.py`) | `POST /api/run-backtest`; `GET /api/sessions/{id}/iterations/{iteration_id}` | One read on summary card, detail metrics grid, and rating panel — never recomputed in the UI |
| Walk-forward efficiency — `wfe`, `combined_oos_return`, `combined_oos_sharpe`, `combined_oos_win_rate`, `combined_oos_max_drawdown` | `apps/backend/backtest/walk_forward.py` → `WalkForwardResult` | `POST /api/execute-walk-forward` | WFE badge thresholds: green ≥ 0.5 / yellow 0.3–0.5 / red < 0.3 |
| 5-category rating — `profitability`, `risk_resistance`, `risk_reward`, `win_rate_ev`, `liquidity` | `apps/backend/backtest/rating.py` → `StrategyRating` (`shared/contracts.py`), derived from the same `BacktestResult` | Carried on the iteration / backtest record; `GET /api/sessions/{id}/iterations/{iteration_id}` | Derived from `BacktestResult` — never recomputed independently |
| Shared records — session record, iteration record (`IterationNode`), backtest record (`BacktestResult`), suggestion record (insights/suggestions) | `apps/backend/backend/session_store.py` (file store — the one source) | `GET /api/sessions`, `GET /api/sessions/{id}`, `GET /api/sessions/{id}/iterations/{iteration_id}` | UI read-only. List/open path stays **lightweight** (no eager heavy `result`/`rating` payload); iteration detail lazy-loaded |
| **(Layer-1, iter-1)** Automated-session run state + stop reason — `queued` / `running` / `stopped` / `criteria-met` / `budget-exhausted` / `interrupted` / `error` | `apps/backend/backend/auto_session.py` (`AutoSessionController`) | `GET /api/sessions/{id}` — new `autoRun` block on the session record (no parallel store; started via `POST /api/auto-sessions`) | One canonical status per session, persisted to `session.json`'s `autoRun` block (survives worker restart + browser reload); orphaned `running` reconciled to `interrupted` on startup. UI status strip and API read the same value. **(iter-2)** The UI status strip + live iteration tracking READ this block by polling the same canonical `GET /api/sessions/{id}` (no new status endpoint; lightweight list/open path preserved, no eager heavy-payload parse); the in-browser "Auto Run" control STARTS via `POST /api/auto-sessions` and STOPS via `POST /api/auto-sessions/{id}/stop`. The second in-browser iterate loop + its duplicate `scoreIteration` (`apps/frontend/src/hooks/useBacktest.ts`) are removed, so the backend loop + `RobustScorer` are the sole engine/best definition |
| **(Layer-1 iter-1; configs + token/USD hard-enforced iter-3)** Budget counters — iterations done, **configs explored**, wall-clock seconds; token spend + USD cost | Immutable budget tracker in `apps/backend/backend/auto_session.py` | `GET /api/sessions/{id}` — `autoRun.budget` block | One authoritative counter per automated session. **Iterations + wall-clock hard-enforced (iter-1); `max_configs` AND token/USD become hard caps in iter-3 (J-12/J-13)** — the loop checks every cap *before* each unit of work and never starts one past a cap; token/USD spend is threaded from real LLM SDK usage and shown in the status strip. UI and API read the same tally — never separate counts |
| **(Layer-1, iter-1)** Robust objective score + best marker (`autoRun.bestIterationId`) | Robust scorer in `apps/backend/backend/auto_session.py`, derived from the canonical `WalkForwardResult` (`POST /api/execute-walk-forward`) + `BacktestResult` | `GET /api/sessions/{id}` — `autoRun.bestIterationId` on the session record | WFE-gated, drawdown-penalized, min-trades floor; selects the single "best" iteration — one definition, read identically by the best badge and (Layer-2) the leaderboard. **Legacy duplicate retired (iter-2):** the in-browser `scoreIteration` and the second in-browser iterate loop in `apps/frontend/src/hooks/useBacktest.ts` have been **removed** — **J-10 (iter-2)** rewired Auto Run to start this backend loop (`POST /api/auto-sessions`), so the backend `RobustScorer` is now the **sole** "best" definition and the only iterate engine; the UI only reads `autoRun.bestIterationId` |
| **(Layer-2, iter-3; staged iter-4)** Open-universe search — candidate configs explored (distinct symbol/timeframe drawn from a **bounded seed universe**) | Open-universe controller path in `apps/backend/backend/auto_session.py` (orchestration only — it computes **no** new displayed metric; reuses the existing `BacktestPipeline` + `RobustScorer`; model tier from `shared/model_catalog.py:cheapest_model()`) | `GET /api/sessions/{id}` — writes only the SAME canonical records: candidate configs as iteration `params`, the cross-config winner as `autoRun.bestIterationId` (via the existing `RobustScorer`), counters on `autoRun.budget`, and SCREEN/PROMOTE stage **activity records** | Bounded seed universe only (anti-goal: no exchange-wide fan-out). **(iter-4, J-14) Two-stage cost-tiering:** a cheap **SCREEN** pass evaluates the budget-bounded seed configs on the cheapest catalog model (`cheapest_model()`) with **no walk-forward**; the top-`k` survivors (`k = DEFAULT_PROMOTE_K`, and `k < number screened`) are **PROMOTE**d to full evaluation — walk-forward **and** the stronger request `model` — and the cross-config best is `RobustScorer.select_best()` over the **promoted (WFE-gated) candidates only** (screened-only nodes are never marked best, preserving the WFE-gated-best anti-goal). SCREEN/PROMOTE stages surface as **activity records** in the Left Activity Log (no new value, no new endpoint); any shown score is the one `RobustScorer.score()`. Every unit (each screen + each promote) is bounded by the hard `max_configs` + token/USD + wall-clock budget, checked before the unit. **No parallel store, no new endpoint, no new score.** The overfit-gated leaderboard *visualization* is **J-16**; the cached LLM-planner warm-start over global history is **J-15** |

<!-- Layer-1 iter-1 landed the first three automated-session rows (run state + stop reason, budget counters,
robust best-marker). Layer-2 iter-3 lands open-universe search + the hard token/USD/max_configs budget (J-12 +
J-13): config exploration over a bounded seed universe, uniformly evaluated through the existing pipeline, with
token/USD threaded from real LLM SDK usage and hard-enforced — all writing the SAME canonical records (no
parallel store, no schema fork). iter-4 lands staged SCREEN→PROMOTE cost-tiering (J-14): the open-universe loop
screens the seed configs cheap (cheapest model, no walk-forward) and promotes only top-k survivors (k < screened)
to walk-forward + the stronger model, best WFE-gated among promoted — surfaced as activity records, no new value/
endpoint (additive Notes edit only, no nav change). Still forward-looking: global-history warm start (J-15) and
the overfit-gated leaderboard UI (J-16). -->
