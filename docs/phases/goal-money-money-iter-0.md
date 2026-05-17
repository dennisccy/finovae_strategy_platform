# Goal Iteration 0 — Baseline journey assessment (verify-only)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** money-money
- **Iteration:** 0
- **Mode:** baseline
- **Depth:** lean
- **Frontend Present:** yes
- **Target journeys:** J-01, J-02, J-03, J-04, J-05, J-06
- **Required-still-passing journeys:** None — this baseline establishes the initial per-journey status; nothing is yet declared passing.
- **Anti-goal reminders:**
  - No hard-coded credentials, API keys, or tokens in source files (keys only via env / git-ignored `.env`).
  - The RestrictedPython sandbox MUST block file I/O, network, `exec`/`eval`, `__import__`, `open`, and `os`.
  - No lookahead: a generated signal must never observe future bars.
  - No nondeterministic backtests (slippage is seeded; identical inputs → identical output).
  - No dependency on a paid SaaS service other than Anthropic/OpenAI (already in Constraints).
  - The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
  - OHLCV market data MUST be cached as a single Parquet file per (symbol, timeframe) — NOT one CSV or file per calendar day — and MUST NOT be re-fetched from Binance when a covering local cache exists.
  - `BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart.
  - No relational database or SQLite is introduced for OHLCV, session, or directions storage (Parquet + durable file store only).
  - `GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint.

## GOAL

Establish a truthful baseline of which Must-have user journeys (J-01..J-06) already pass, partially work, or fail against the current codebase — with zero code changes — so subsequent iterations target only real gaps.

## BACKGROUND

This is iteration 0 of goal session `money-money`: a **baseline assessment, not a feature delivery**. `journey-history.json` is empty and no prior evaluator feedback or lessons exist (fresh session). The Finovae Strategy Platform monorepo already exists (`apps/backend` FastAPI + `apps/frontend` Vite/React with service-start scripts present), so some journeys may already pass. This iteration runs every Must-have journey end-to-end against the current state and records concrete evidence; the goal-evaluator will use these results to seed initial per-journey status (`already_passing` vs. work-needed) so later iterations skip what already works.

## IN SCOPE

### Backend
- None — baseline is verify-only; no source files are modified.

### Frontend
- None — baseline is verify-only; no source files are modified.

### Verification activity (the actual work of this iteration)
- Start dev services and execute each Must-have journey J-01..J-06 against the running, unmodified codebase.
- For each journey, record: pass / partial / fail, the exact step reached, what was observed, and (on failure) where and how it broke.
- Run the existing backend unit/integration suite to capture the current green/red baseline (no new tests authored).
- Observe and record any **pre-existing** anti-goal posture (e.g., per-day cache fan-out, `/tmp` store default, eager session-payload parsing) for the evaluator — observation only, no remediation.

### New user-facing capability
None — baseline assessment only; the product is not changed.

### New information displayed
None.

### New user actions
None.

### UI surface changes
None.

### Product surface delta
None — diff must be empty except this spec and the run/QA artifacts it produces.

## OUT OF SCOPE

- Any code, config, or dependency change (including "obvious" fixes discovered during verification — record them, do not apply them).
- Authoring new unit, integration, or browser tests beyond executing the existing suite and the journey flows.
- Remediating any anti-goal posture or journey failure found — that is for `Mode: next` iterations.
- Marking journeys pass/fail in `journey-history.json` — only the goal-evaluator does that.

## DEFINITION OF DONE

- [ ] Each Must-have journey J-01..J-06 executed against the current codebase via browser-qa-agent
- [ ] Each journey's outcome recorded as pass / partial / fail with concrete evidence (step reached, what was observed, failure location)
- [ ] Existing backend test suite executed and its pass/fail counts recorded
- [ ] No code changes made (working tree diff is empty except this spec and generated run/QA artifacts)
- [ ] No anti-goal violation introduced (none expected — verify-only); any pre-existing anti-goal posture noted for the evaluator
- [ ] Baseline results captured so the evaluator can set initial per-journey status in `journey-history.json`
- [ ] Dev handoff written at `docs/handoffs/goal-money-money-iter-0-dev.md` stating "baseline verify-only — no code changes" plus the per-journey results table

## TESTING REQUIREMENTS

- **Browser (Chrome MCP):** execute each journey end-to-end against running dev services and record the outcome:
  - **J-05 Reference data loads** — open the app; confirm `/api/symbols` and `/api/timeframes` populate the symbol/timeframe controls. (No preconditions — run first.)
  - **J-01 Run a backtest from natural language** — enter "Buy when RSI crosses below 30, sell when it crosses above 70", set `BTCUSDT` / `1h` / a date range / initial capital, submit; expect non-empty metrics, equity curve, trades table, and a new `run_id` in history.
  - **J-02 Inspect and browse run history** — open the prior run from history; expect its spec, metrics, and trades to reload into the detail view. (Requires a completed J-01 run.)
  - **J-03 Walk-forward validation** — from a completed iteration's detail view, set IS/OOS windows, run walk-forward; expect a WFE badge (green ≥0.5 / yellow 0.3–0.5 / red <0.3), per-window table, and combined OOS equity curve. (Requires a completed run.)
  - **J-04 AI insights** — on a completed run, request insights; expect ≥1 ranked suggestion, OOS-aware when walk-forward data exists. (Requires a completed run.)
  - **J-06 Warm-cache re-run** — re-run the same strategy/symbol/timeframe/date range as J-01; expect a second completed run with metrics, equity curve, trades, and a new history entry (warm local-cache path). (Requires a completed J-01 run on the same parameters.)
- **Unit/integration:** run `cd apps/backend && .venv/bin/python -m pytest` and record pass/fail counts as the baseline. Do not author new tests.
- **Error cases:** none authored in baseline; record any errors, stack traces, or HTTP failures encountered while executing the journeys.

## NOTES

- **Verify-only.** Iteration 0 is a baseline snapshot, not feature work. Discovered defects/fixes are recorded for later iterations, never applied here.
- **Service start:** bring up both services with `./scripts/dev.sh` (backend defaults to :8000, frontend :5173; dev offsets ports — use the harness-reported URLs, and the Vite `/api` proxy).
- **LLM-dependent journeys:** J-01, J-03, and J-04 (and J-06, which depends on a J-01 run) require `OPENAI_API_KEY` in `apps/backend/.env` (default model `gpt-5.4-mini`); `ANTHROPIC_API_KEY` only if a Claude model is selected. If the key is absent, record the failure as **environmental (missing credential)**, explicitly distinct from a code defect, so the evaluator does not misclassify a runnable feature as broken.
- **Journey ordering / preconditions:** run J-05 first (no preconditions); then J-01; then J-02, J-03, J-04, and J-06, all of which require a completed run from J-01 (J-06 specifically the same parameters).
- **Anti-goal observation:** baseline should also note any *pre-existing* anti-goal posture (single-file Parquet vs. per-day fan-out, `BACKTEST_STORE_DIR` default location, `GET /api/sessions/{id}` eager-parse behavior) for the evaluator — observation only, no code change.
- **State:** `journey-history.json` is empty and there is no prior evaluator log or lessons file content (fresh session) — nothing to reconcile against.
