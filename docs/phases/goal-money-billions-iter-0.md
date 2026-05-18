# Goal Iteration 0 — Baseline assessment of all Must-have journeys

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** money-billions
- **Iteration:** 0
- **Mode:** baseline
- **Depth:** lean
- **Frontend Present:** yes
- **Target journeys:** J-01, J-02, J-03, J-04, J-05, J-06
- **Required-still-passing journeys:** None (baseline — no journey is green yet)
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
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

Establish a verified baseline: run every Must-have user journey (J-01 … J-06) against the **current** codebase, with no code changes, and record for each whether it currently passes, fails, or is partial.

## BACKGROUND

This is the baseline assessment for goal session `money-billions` — **not a feature delivery**. Journey history is empty and no journeys have been scored yet. The codebase already contains a substantial implementation (FastAPI backend at `apps/backend/`, Vite/React frontend at `apps/frontend/`, Parquet OHLCV cache, durable session store, walk-forward and AI-insights modules). The purpose of this iteration is to distinguish "already working" from "yet to build" so subsequent iterations target only genuinely failing or partial journeys. The developer step is a deliberate no-op; all value comes from the QA/browser-QA step exercising every journey and recording evidence. No prior lessons learned apply (the ledger is empty).

## IN SCOPE

### Backend
- [ ] None — verify-only. No source files are modified this iteration.

### Frontend (if applicable)
- [ ] None — verify-only. No source files are modified this iteration.

### Verification activities (no code changes)
- [ ] Start the stack with `./scripts/dev.sh` (or `./scripts/start-backend.sh` + `./scripts/start-frontend.sh`); capture the actual offset URLs the scripts print (ports are deterministic offsets, NOT 8000/5173).
- [ ] Confirm the backend boots and serves `/docs`.
- [ ] Run the backend unit suite (`cd apps/backend && .venv/bin/python -m pytest`) and record pass/fail counts — this captures the current state of the anti-goal invariant tests (lookahead, determinism, sandbox security).
- [ ] Exercise each Must-have journey J-01 … J-06 through the UI via browser automation and record pass / fail / partial with evidence (screenshots, response payloads, observed values).
- [ ] Spot-check anti-goal compliance signals observable without code changes (e.g., `BACKTEST_STORE_DIR` default is non-`/tmp`; OHLCV cache produces a single Parquet file per (symbol, timeframe); no SQLite/DB files appear).

### New user-facing capability
None — baseline assessment only. No new capability is delivered this iteration.

### New information displayed
None — no UI changes.

### New user actions
None — no UI changes.

### UI surface changes
None — no UI changes.

### Product surface delta
None — the product experience is unchanged. This iteration only measures and records the current state.

## OUT OF SCOPE

- Any code change, bug fix, refactor, or dependency change (deferred to `Mode: next` iterations once failing/partial journeys are identified).
- Marking journeys as passing/failing — only the goal-evaluator records journey verdicts from the recorded evidence.
- Fixing environment/configuration issues (e.g., a missing `OPENAI_API_KEY`); these are recorded as observations, not repaired here.
- Performance tuning, new tests, or new endpoints.

## DEFINITION OF DONE

- [ ] Every Must-have journey (J-01, J-02, J-03, J-04, J-05, J-06) is exercised against the current codebase and its result (pass / fail / partial) is recorded with concrete evidence.
- [ ] Backend boot + `/docs` availability is recorded.
- [ ] Backend unit-suite result (pass/fail counts) is recorded, including the lookahead / determinism / sandbox invariant tests.
- [ ] Observable anti-goal signals are noted (no `/tmp` store default, single-Parquet OHLCV cache, no SQLite/DB).
- [ ] No code or source files were modified (verify-only confirmed in the dev handoff).
- [ ] No anti-goal violation introduced (trivially satisfied — no code changes).
- [ ] Dev handoff written at `docs/handoffs/goal-money-billions-iter-0-dev.md` explicitly stating "verify-only, no code changes" and summarizing per-journey baseline status.

## TESTING REQUIREMENTS

- **Browser (per Must-have journey, by ID):**
  - **J-01 — Run a backtest from natural language:** open the app; enter "Buy when RSI crosses below 30, sell when it crosses above 70"; set symbol `BTCUSDT`, timeframe `1h`, a date range, initial capital; submit. Expect: results panel shows non-empty metrics, an equity curve, and a trades table, and a new `run_id` appears in history.
  - **J-02 — Inspect and browse run history:** after a completed backtest, open a prior run from the history list. Expect: that run's strategy spec, metrics, and trades reload into the detail view.
  - **J-03 — Walk-forward validation:** from a completed iteration's detail view, set IS/OOS window lengths, click "Run Walk-Forward". Expect: a WFE badge (green ≥ 0.5 / yellow 0.3–0.5 / red < 0.3), a per-window table, and a combined OOS equity curve.
  - **J-04 — AI insights:** on a completed run, request insights. Expect: at least one ranked suggestion renders; suggestions are OOS-aware when walk-forward data exists.
  - **J-05 — Reference data loads:** open the app and inspect parameter controls. Expect: `/api/symbols` and `/api/timeframes` populate the symbol and timeframe controls.
  - **J-06 — Warm-cache re-run works end-to-end:** run a backtest for `BTCUSDT` `1h` over a fixed date range and wait for results; run the same strategy/symbol/timeframe/date range again. Expect: the second run completes and renders metrics, an equity curve, and a trades table without error, and appears in history.
- **Unit/integration:** run the existing backend suite `cd apps/backend && .venv/bin/python -m pytest` and record results (especially `tests/test_lookahead.py`, `tests/test_determinism.py`, `tests/test_sandbox.py`). Do not add or modify tests.
- **Error cases:** none introduced this iteration; record any errors observed while exercising journeys (e.g., missing API key, Binance fetch failure) as baseline observations rather than defects to fix now.

## NOTES

- **Service ports:** `./scripts/dev.sh`, `start-backend.sh`, and `start-frontend.sh` use deterministic per-project offset ports (not 8000/5173) and the backend prints its actual URL on start. Read the printed URL; do not hardcode 8000/5173.
- **API-key dependency (important for evaluator interpretation):** `/api/run-backtest`, `/api/generate-strategy`, and `/api/generate-insights` require `OPENAI_API_KEY` (default model `gpt-5.4-mini`); `ANTHROPIC_API_KEY` only if a Claude model is selected. The backend boots without keys. If no key is configured in the QA environment, J-01, J-03, J-04, and J-06 may fail at the NL-compilation/insights step. Record this as an environment dependency observation — it is NOT a code defect for a `Mode: next` iteration to "fix" in code; the goal-evaluator should classify such failures accordingly when deciding next-iteration scope.
- **Baseline intent:** for this existing project, this iteration is the moment that separates already-implemented journeys from those needing work. The goal-evaluator will mark already-passing journeys as `already_passing` so subsequent `Mode: next` iterations skip them and target only failing/partial ones.
- **Depth rationale:** `lean` per baseline-mode rules — the developer agent is a no-op; the verification value comes entirely from the browser-QA step running every journey.
- **No lessons applied:** the lessons-learned ledger is empty (first iteration); nothing to surface.
