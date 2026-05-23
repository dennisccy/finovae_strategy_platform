# Goal Iteration 0 — Baseline assessment of all Must-have journeys (J-01 … J-16)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** financial_free
- **Iteration:** 0
- **Mode:** baseline
- **Depth:** lean
- **Frontend Present:** yes
- **Target journeys:** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09, J-10, J-11, J-12, J-13, J-14, J-15, J-16
- **Required-still-passing journeys:** None (baseline — no journey is green yet in this session)
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

Establish a verified baseline: run every Must-have user journey (J-01 … J-16) against the **current** codebase, with no code changes, and record for each whether it currently passes, fails, or is partial — separating "already implemented" from "yet to build."

## BACKGROUND

This is the baseline assessment for goal session `financial_free` — **not a feature delivery**. Journey history for this session is empty. The codebase already contains a substantial implementation (FastAPI backend at `apps/backend/`, Vite/React frontend at `apps/frontend/`, single-file Parquet OHLCV cache, durable session store, walk-forward and AI-insights modules).

This goal is a **superset** of the prior `money-billions` session, which reached `GOAL_ACHIEVED` with **J-01 … J-06 all passing** (manual NL backtest, run history, walk-forward, AI insights, reference-data loads, warm-cache re-run). Those six journeys are expected to still pass and must be re-verified for no-regression. Journeys **J-07 … J-16 are net-new scope**: a headless, token-budgeted, auto-optimizing automated session (Layer 1 Foundation + Layer 2 Optimizer). A code probe confirms the trigger endpoints (`POST /api/auto-sessions`, `POST /api/auto-sessions/{id}/stop`) and any optimizer/controller/budget/planner modules **do not yet exist** in the backend; an *in-browser* "Auto Run" exists in the frontend (`useBacktest.ts`, `BacktestConfigBar.tsx`, `IterationCard.tsx`) that the goal intends to subsume with a backend loop.

The developer step is a deliberate **no-op**; all value comes from the QA / browser-QA step exercising every journey and recording evidence so the goal-evaluator can mark already-passing journeys `already_passing` and target only genuinely failing/partial ones in subsequent `Mode: next` iterations.

## IN SCOPE

### Backend
- [ ] None — verify-only. No source files are modified this iteration.

### Frontend (if applicable)
- [ ] None — verify-only. No source files are modified this iteration.

### Verification activities (no code changes)
- [ ] Start the stack with the project's dev/start scripts; capture the **actual** offset URLs the scripts print (ports are deterministic per-project offsets, NOT 8000/5173 — read the printed URL).
- [ ] Confirm the backend boots and serves `/docs`.
- [ ] Run the backend unit suite (`cd apps/backend && .venv/bin/python -m pytest`) and record pass/fail counts — this captures the current state of the anti-goal invariant tests (lookahead, determinism, sandbox security).
- [ ] Exercise each Must-have journey J-01 … J-16 and record pass / fail / partial with concrete evidence (screenshots, response payloads, observed values, HTTP status codes).
- [ ] For J-07 … J-16, **probe the API surface first** (see TESTING REQUIREMENTS): a single `POST /api/auto-sessions` returning 404/405 is sufficient evidence the automated session is "not built" — do **not** burn AI tokens or wait on an optimizer that does not exist.
- [ ] Spot-check observable anti-goal compliance signals without code changes (e.g., `BACKTEST_STORE_DIR` default is non-`/tmp`; OHLCV cache produces a single Parquet file per (symbol, timeframe); no SQLite/DB files appear).

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

### Blueprint conformance
No new surfaces. This iteration introduces no pages or values. The session blueprint (`runs/goal-session-financial_free/state/blueprint.md`) is drafted this baseline and awaits human approval; it already reserves the canonical homes for the not-yet-built automated session (run state/stop reason, budget counters, robust score) so future iterations conform.

### Data-contract additions
None — no displayed value is introduced this iteration.

## OUT OF SCOPE

- Any code change, bug fix, refactor, or dependency change (deferred to `Mode: next` iterations once failing/partial journeys are identified).
- Building any part of the headless automated session (J-07 … J-16) — baseline only measures its absence/presence.
- Marking journeys as passing/failing — only the goal-evaluator records journey verdicts from the recorded evidence.
- Fixing environment/configuration issues (e.g., a missing `OPENAI_API_KEY`); these are recorded as observations, not repaired here.
- Performance tuning, new tests, or new endpoints.

## DEFINITION OF DONE

- [ ] Every Must-have journey (J-01 … J-16) is exercised against the current codebase and its result (pass / fail / partial) is recorded with concrete evidence.
- [ ] Backend boot + `/docs` availability is recorded.
- [ ] Backend unit-suite result (pass/fail counts) is recorded, including the lookahead / determinism / sandbox invariant tests.
- [ ] The presence/absence of `POST /api/auto-sessions` (and `POST /api/auto-sessions/{id}/stop`) is recorded with the probe response (status code).
- [ ] Observable anti-goal signals are noted (no `/tmp` store default, single-Parquet OHLCV cache, no SQLite/DB).
- [ ] No code or source files were modified (verify-only confirmed in the dev handoff).
- [ ] No anti-goal violation introduced (trivially satisfied — no code changes).
- [ ] Dev handoff written at `docs/handoffs/goal-financial_free-iter-0-dev.md` explicitly stating "verify-only, no code changes" and summarizing per-journey baseline status.

## TESTING REQUIREMENTS

### Group A — Manual journeys J-01 … J-06 (expected already-passing; re-verify for no-regression)

- **J-01 — Run a backtest from natural language:** open the app; enter "Buy when RSI crosses below 30, sell when it crosses above 70"; set symbol `BTCUSDT`, timeframe `1h`, a date range, initial capital; submit. Expect: results panel shows non-empty metrics, an equity curve, and a trades table, and a new `run_id` appears in history.
- **J-02 — Inspect and browse run history:** after a completed backtest, open a prior run from the history list. Expect: that run's strategy spec, metrics, and trades reload into the detail view (per-iteration lazy fetch, not eager list parse).
- **J-03 — Walk-forward validation:** from a completed iteration's detail view, set IS/OOS window lengths, click "Run Walk-Forward". Expect: a WFE badge (green ≥ 0.5 / yellow 0.3–0.5 / red < 0.3), a per-window IS/OOS table, and a combined OOS equity curve.
- **J-04 — AI insights:** on a completed run, request insights. Expect: at least one ranked suggestion renders; suggestions are OOS-aware when walk-forward data exists. **Capture a distinct, content-legible screenshot of the insights pane** (NOT a duplicate of the J-03 walk-forward capture — see NOTES, prior-session lesson).
- **J-05 — Reference data loads:** open the app and inspect parameter controls. Expect: `/api/symbols` and `/api/timeframes` populate the symbol and timeframe controls (controls sourced from the endpoints, not hardcoded).
- **J-06 — Warm-cache re-run works end-to-end:** run a backtest for `BTCUSDT` `1h` over a fixed date range and wait for results; run the same strategy/symbol/timeframe/date range again. Expect: the second run completes and renders metrics, an equity curve, and a trades table without error, and appears in history.

### Group B — Layer 1 Foundation, headless automated session J-07 … J-11 (API-probe first)

For each, **first** issue `POST /api/auto-sessions` (tiny pinned config; see goal.md J-07). If the endpoint returns 404/405 (route absent), record the journey as failing-by-absence with the probe evidence and stop — do **not** attempt the full flow. Only if the endpoint responds 200 should the journey be exercised end-to-end with a tiny budget (`max_iterations: 2`, short date range, cheapest model, lenient targets).

- **J-07 — Start a headless automated session via the API (pinned config):** Expect HTTP 200 with a `sessionId` and run state `running`/`queued`; the same `sessionId` appears immediately in `GET /api/sessions` with no browser interaction to start it.
- **J-08 — Track the automated run live in the UI:** open the created session; expect a "running" status indicator, ≥1 iteration with a backtest result and generated suggestions, then a terminal state — all without a manual page reload.
- **J-09 — Automated chain stops on robust target or budget; best is marked:** expect a terminal status with a visible stop reason (`criteria-met` or `budget-exhausted`) and a best iteration marked; when `criteria-met`, the best iteration's metrics satisfy every supplied robust target.
- **J-10 — Backend is the single source of truth (button rewired, survives reload):** in the UI, open a completed iteration and click "Auto Run" with a small budget; mid-run reload the tab and reopen the session. Expect the run to keep advancing after reload and reach a terminal state server-side. *Baseline note:* the current "Auto Run" is in-browser, so the backend-source-of-truth acceptance is expected to fail/partial — record the observed behavior precisely.
- **J-11 — Stop a running automated session:** start a run large enough to still be running; `POST /api/auto-sessions/{sessionId}/stop` (or click the UI stop control); reopen the session. Expect a `stopped` terminal state, no further iterations appended, best-so-far still marked.

### Group C — Layer 2 Optimizer, open-universe search J-12 … J-16 (API-probe first)

Same probe-first rule as Group B. If `POST /api/auto-sessions` is absent, record J-12 … J-16 as failing-by-absence with the same probe evidence (the open-universe optimizer is a strict superset of the Layer-1 endpoint).

- **J-12 — Open-universe run from only an objective + budget:** `POST /api/auto-sessions` with no `symbol`/`timeframe`, only `objective: "robust"` + a small `budget`. Expect ≥2 distinct configs (differing symbol and/or timeframe) as iterations; terminal within budget; best marked by robust score.
- **J-13 — AI-token/cost budget is hard-enforced:** trigger with a tiny token/USD budget. Expect stop reason `budget-exhausted`; recorded spend ≤ cap (within one-call tolerance) and visible in the status block; no iterations after the cap.
- **J-14 — Staged screening — full cost only on survivors:** inspect the activity log. Expect a `SCREEN` stage with several cheap candidates and a `PROMOTE` stage on only the top-k (k < #screened); walk-forward + stronger model only on promoted configs.
- **J-15 — Learns from global history (warm start) and is opt-out-able:** run #1 open-universe; run #2 `history_scope: "global"`; run #3 `history_scope: "this-run"`. Expect run #2 to cite prior-session performance and warm-start a top family from run #1; run #3 shows no cross-run citation.
- **J-16 — Robust objective gates overfit:** inspect the leaderboard/best iteration. Expect the marked best satisfies WFE ≥ threshold and the min-trades floor and derives its score from walk-forward OOS; a higher-raw-return but WFE-failing/over-leveraged candidate is NOT selected best.

### Unit/integration
Run the existing backend suite `cd apps/backend && .venv/bin/python -m pytest` and record results (especially `tests/test_lookahead.py`, `tests/test_determinism.py`, `tests/test_sandbox.py`). Do not add or modify tests.

### Error cases
None introduced this iteration; record any errors observed while exercising journeys (e.g., missing API key, Binance fetch failure, 404 on the auto-session endpoint) as baseline observations rather than defects to fix now.

## NOTES

- **Service ports:** the dev/start scripts use deterministic per-project offset ports (not 8000/5173) and the backend prints its actual URL on start. Read the printed URL; do not hardcode 8000/5173.
- **API-key dependency (important for evaluator interpretation):** `/api/run-backtest`, `/api/generate-strategy`, and `/api/generate-insights` require `OPENAI_API_KEY` (default model `gpt-5.4-mini`); `ANTHROPIC_API_KEY` only if a Claude model is selected. The backend boots without keys. If no key is configured in the QA environment, J-01, J-03, J-04, J-06 (and all of J-07 … J-16, which call the LLM) may fail at the NL-compilation/insights step. Record this as an **environment dependency** observation — it is NOT a code defect for a `Mode: next` iteration to "fix" in code; the goal-evaluator should classify such failures accordingly.
- **Cost discipline for J-07 … J-16:** the automated journeys are token-spending. The probe-first rule keeps baseline cheap: confirm the endpoint exists before running anything. Given the code probe shows `/api/auto-sessions` is absent, the most likely baseline outcome is J-07 … J-16 all fail-by-absence (net-new scope) — but the QA step must still produce the probe evidence rather than assume it.
- **Prior-session context (do not treat as a verdict):** the `money-billions` session marked J-01 … J-06 passing at its iter-3 under a lazy-load/lightweight session-open contract. These remain context, not a pass — re-verify functionally this iteration.
- **Prior-session lessons applied to this baseline's QA:**
  - *J-04 distinctness:* a J-04 screenshot that is a byte-duplicate of the J-03 walk-forward capture is invalid evidence; require a content-legible zoom of the **insights pane** showing OOS-referencing suggestions.
  - *Independence rule:* a green functional journey does NOT by itself prove a structural anti-goal resolved (e.g., a passing J-02 does not prove the eager-load anti-goal; a passing J-06 does not prove the single-Parquet anti-goal). Anti-goal compliance needs its own code/test evidence — but this is a verify-only baseline, so record signals only; do not fix.
  - *Restart/persistence proof:* the authoritative proof of "survives restart" is a simulated-restart pytest, not an unattended browser kill (environment-safety policy denies killing the shared QA backend). Relevant later for J-08/J-10 persistence; at baseline just record the current in-browser behavior.
- **Baseline intent:** for this existing project, this iteration separates already-implemented journeys (likely J-01 … J-06) from those needing work (likely all of J-07 … J-16). The goal-evaluator will mark already-passing journeys `already_passing` so subsequent `Mode: next` iterations skip them and target only failing/partial ones. The Layer-1 Foundation (J-07 … J-11) should land before the Layer-2 Optimizer (J-12 … J-16) per goal.md's layering.
- **Depth rationale:** `lean` per baseline-mode rules — the developer agent is a no-op; the verification value comes entirely from the browser-QA / API-probe step running every journey.
