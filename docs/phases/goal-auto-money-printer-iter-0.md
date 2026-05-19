# Goal Iteration 0 — Baseline assessment: verify all Must-have journeys against current state

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** auto-money-printer
- **Iteration:** 0
- **Mode:** baseline
- **Depth:** lean
- **Frontend Present:** yes
- **Target journeys:** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09, J-10, J-11, J-12, J-13, J-14, J-15, J-16
- **Required-still-passing journeys:** (none — baseline establishes the starting line)
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
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - The automated-session `autoRun` status MUST be persisted to the durable store and survive a worker restart and a browser reload; it MUST NOT live only in browser memory or a non-persisted in-process variable.
  - After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST NOT run a second in-browser iterate loop.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify.
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are reserved for promoted candidates.
  - Identical generated strategies (by code hash) MUST NOT be re-generated or re-backtested; the OHLCV Parquet cache MUST be reused across configs (no re-fetch when a covering cache exists).
  - Global history learning MUST be read-only mining of the existing store (it MUST NOT mutate or delete prior sessions' artifacts); the `history_scope` opt-out MUST be honored.
  - The LLM-planner / history context MUST use prompt caching; the leaderboard/history MUST NOT be re-sent uncached every round.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.

## GOAL

Establish the starting line: run every Must-have user journey (J-01 through J-16) against the current codebase and record which already pass, which fail, and which are partial — with zero code changes.

## BACKGROUND

This is iteration 0 — a **baseline assessment, not a feature delivery**. The journey-history is empty and this is a fresh session (`auto-money-printer`) pointed at an existing codebase (`apps/backend` FastAPI + `apps/frontend` React/Vite) that prior goal sessions have already built against. The purpose of this iteration is to distinguish "already implemented" from "yet to build" so subsequent iterations skip already-passing journeys and focus only on real gaps. The developer step is intentionally a no-op; all signal comes from the browser-qa / functional verification step exercising all 16 journeys. No code is written, no journey is marked passing/failing here — the goal-evaluator scores results from the verification evidence.

## IN SCOPE

### Backend
- [ ] (none — baseline iteration, no code changes)

### Frontend (if applicable)
- [ ] (none — baseline iteration, no code changes)

### New user-facing capability
None. This iteration only observes and records the current behavior of existing capabilities.

### New information displayed
None. Output is a baseline verification record (per-journey pass/fail/partial with evidence), not a product change.

### New user actions
None.

### UI surface changes
None.

### Product surface delta
None — the product is unchanged by this iteration. The deliverable is knowledge of the current state.

## OUT OF SCOPE

- Any backend or frontend source code change, refactor, or bug fix (deferred to `Mode: next` iterations once gaps are known).
- Marking journeys as passing/failing (only the goal-evaluator does that, from this iteration's evidence).
- Fixing any journey that is found failing or partial (that is the next iteration's job).
- Manufacturing additional scope beyond the 16 Must-have journeys in `docs/goal.md`.

## DEFINITION OF DONE

- [ ] Every Must-have journey J-01 … J-16 is exercised against the current state and its outcome (pass / fail / partial) is recorded with concrete evidence (HTTP status, screenshot, response snippet, or error).
- [ ] Core platform journeys J-01–J-06 verified via the running backend + frontend (real backtest, history reload, walk-forward, AI insights, reference data, warm-cache re-run).
- [ ] Layer 1 automated-chain journeys J-07–J-11 verified (headless `POST /api/auto-sessions` start, live UI tracking, terminal stop + best marked, backend-is-source-of-truth across reload, stop control).
- [ ] Layer 2 optimizer journeys J-12–J-16 verified (open-universe from objective+budget, hard token/cost budget, staged SCREEN→PROMOTE, global-history warm-start + opt-out, robust objective gates overfit).
- [ ] No anti-goal violation introduced (trivially satisfied — no code changes; but observed anti-goal violations in the current code are noted as evidence).
- [ ] Existing unit tests run and the current pass/fail baseline is recorded; no new test failures are introduced by this iteration (no changes are made).
- [ ] Dev handoff written at `docs/handoffs/goal-auto-money-printer-iter-0-dev.md` stating the iteration was a no-op baseline (no diff) so downstream agents proceed straight to verification.

## TESTING REQUIREMENTS

- **Services:** start the backend with `bash scripts/start-backend.sh` and the frontend with `bash scripts/start-frontend.sh` before verification. Strategy compilation / AI insights / automated-session planning require `OPENAI_API_KEY` (default model `gpt-5.4-mini`); if no key is present, record those journeys as **blocked-no-key** rather than failing — that is itself a baseline finding.
- **Browser (all 16, by ID):** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09, J-10, J-11, J-12, J-13, J-14, J-15, J-16. Use the journey Steps/Acceptance in `docs/goal.md` verbatim as the test scripts. For every automated-session journey (J-07–J-16) use **tiny budgets**: `max_iterations: 2`, a short date range, the cheapest model, lenient `targets` — so verification stays fast and cheap. In `POST /api/auto-sessions` a provided search-space field pins that dimension; omit `symbol`/`timeframe` only for the open-universe journeys (J-12–J-16).
- **Unit/integration:** run the existing backend suite under `apps/backend/tests/` (e.g. `apps/backend/.venv/bin/python -m pytest apps/backend/tests/ -q`, falling back to the project's documented runner if the venv path differs) and record the pass/fail count as the baseline — do not fix failures.
- **Error cases:** while exercising J-07/J-12, note (do not fix) whether `POST /api/auto-sessions` rejects obviously invalid input (e.g. negative budget, unknown symbol) — this informs later hardening iterations.

## NOTES

- Per the goal-decomposer baseline rules: no Backend/Frontend in-scope items, all Must-have journeys targeted, depth `lean` (the lean cycle's verification step is sufficient — the developer step is a deliberate no-op), and Definition of Done is "every journey verified against current state, results recorded."
- Existing prior goal sessions (`goal-session-money-billions`, `goal-session-money-money`) ran against this same codebase, so expect a meaningful fraction of J-01–J-16 to already pass. The value of this iteration is precisely separating those from genuine gaps.
- Lessons-learned ledger is empty (first iteration) — nothing to apply yet.
- Scope-creep guard: every target journey maps directly to a Key Capability in `docs/goal.md` (J-01–J-06 → capabilities 1–9; J-07–J-16 → capability 11, the headless auto-optimizing session). No out-of-goal capability is implied.
