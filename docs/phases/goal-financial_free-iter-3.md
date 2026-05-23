# Goal Iteration 3 — Open-universe search under a hard token/USD budget (Layer-2 start)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** financial_free
- **Iteration:** 3
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes
- **Target journeys:** J-12, J-13
- **Required-still-passing journeys:** J-07, J-08, J-09, J-10, J-11 (and no-regression on J-01, J-02, J-03, J-04, J-05, J-06)
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify.
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - Identical generated strategies (by code hash) MUST NOT be re-generated or re-backtested; the OHLCV Parquet cache MUST be reused across configs (no re-fetch when a covering cache exists).
  - Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are reserved for promoted candidates. *(Staging is J-14 — see OUT OF SCOPE; do not half-build a SCREEN stage this iteration.)*
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - The automated-session `autoRun` status MUST be persisted to the durable store and survive a worker restart and a browser reload; it MUST NOT live only in browser memory or a non-persisted in-process variable.
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.
  - No lookahead; no nondeterministic backtests (slippage seeded); the sandbox MUST block file I/O, network, `exec`/`eval`, `__import__`, `open`, `os`.
  - No relational database or SQLite; OHLCV stays a single Parquet file per (symbol, timeframe); `BACKTEST_STORE_DIR` MUST NOT default to a volatile `/tmp` path; the frozen dataclasses in `shared/contracts.py` MUST NOT be mutated in place.

## GOAL

A single API call carrying only an objective + budget (no `symbol`/`timeframe`) launches a server-side **open-universe** search that explores ≥2 distinct configs from a **bounded seed universe**, runs to a terminal state inside a **hard token/USD/configs/wall-clock budget** enforced by the immutable cost tracker, and marks the best by the robust WFE-gated objective — all streaming live into the existing session UI, with token + USD spend now visible in the status strip.

## BACKGROUND

Layer-1 (J-07…J-11) is complete and re-verified: the backend auto-session loop is the sole Auto Run engine. This iteration starts Layer-2 with its foundation — the open-universe optimizer — at **full** depth (evaluator recommendation; crosses backend loop + pipeline token threading + frontend display). Per the decomposer's tight-iteration rule we take the smallest coherent Layer-2 slice: **J-12 (open-universe multi-config search)** plus **J-13 (hard token/USD budget)**, which are tightly coupled — an open-universe search needs a cost-based budget to bound it. Today the controller only runs a *single pinned config* (improvement rounds on one symbol/timeframe), the route 400-rejects open-universe (`auto_session_routes.py:198-207`), and the `max_tokens`/`max_usd` budget fields are accepted but never enforced (`_build_budget` drops them; `BudgetTracker.exceeded()` checks only iterations + wall-clock). Token usage is available at the SDK level but only logged, not propagated (`compiler.py:303-310`). Staged SCREEN→PROMOTE (J-14), global-history warm start (J-15), and the leaderboard UI (J-16) build on this and stay deferred. **Carry-forward debt (evaluator + iter-2 lesson):** J-08/J-10 live pixels and the J-01/J-05 manual regressions have never been confirmed at the pixel layer (hidden-tab throttle in iter-0, Vite server down mid-window in iter-2). Layer-2 runs browser-QA again — clear that debt this time with a frontend health-checked for the whole window.

## IN SCOPE

### Backend

- [ ] **Accept open-universe on `POST /api/auto-sessions`.** When `symbol`/`timeframe` are omitted (with `objective: "robust"` + a valid `budget`), route to a new open-universe controller path instead of returning 400. Keep the pinned-config path (both present) **unchanged** so J-07 is untouched. `natural_language` becomes optional in open-universe mode (a seed strategy idea is drawn from the seed universe when omitted; if provided, it pins the strategy idea and the universe varies symbol/timeframe).
- [ ] **Define a bounded seed universe** as an explicit, hard-capped constant/config in `auto_session.py` — a small set of liquid symbols × a few timeframes × 1–3 seed strategy ideas. The open-universe search enumerates a budget-bounded subset of it. It MUST NOT enumerate the full `/api/symbols` list or fan out exchange-wide.
- [ ] **Open-universe controller loop.** Explore ≥2 distinct configs (differing symbol and/or timeframe) drawn from the seed universe; evaluate each through the existing `BacktestPipeline` (generate → backtest → walk-forward) and score with the existing `RobustScorer`; mark the single best by robust score across all explored configs (`autoRun.bestIterationId`). Reuse `_build_node` + `result_serialization.py` for node byte-shape (no schema fork) and persist each config via the same `session_store.write_iteration` (lazy detail; lightweight list/open path preserved). A single config's generation/backtest failure is non-fatal (logged, search continues).
- [ ] **Hard budget — `max_configs` + token/USD.** Add `max_configs` (the open-universe analog of `max_iterations`) to `AutoSessionBudget` and `BudgetTracker`, hard-enforced by `BudgetTracker.exceeded()` (checked *before* starting each config — never "one more"). Wire `max_tokens`/`max_usd` from the request through `_build_budget` into `BudgetTracker` and make `exceeded()` enforce them as hard caps. Add `configsDone`/`maxConfigs` (and ensure `tokens`/`usd`/`maxTokens`/`maxUsd`) to `BudgetTracker.to_dict()`.
- [ ] **Real token/USD accounting (J-13).** Capture LLM token usage already present at the SDK response level (OpenAI `response.usage.prompt_tokens/completion_tokens`; Anthropic `usage.input_tokens/output_tokens`) — currently only logged — and thread it out of the pipeline's `generate_strategy`/`generate_insights` into the controller's immutable `BudgetTracker.with_usage()`. Map tokens→USD via a per-model rate (model catalog). Prefer real SDK usage over estimation; the tracker stays frozen (`with_usage` returns a new instance).
- [ ] Both pinned and open-universe runs check **all** hard caps (configs/iterations, tokens, USD, wall-clock) before each unit of work and finish with `status = "budget-exhausted"`, `stopReason = "budget-exhausted"` when any cap is reached; no config/iteration is appended after a cap is hit.
- [ ] **Preserve the B1+B2 invariant.** The new loop uses the existing `_save_auto_run` / `_stop_requested` checkpoints under the shared per-session `asyncio.Lock`; no lock-free `autoRun` read-modify-write; store I/O stays off the event loop (`_run_off_loop`); backtests stay semaphore-guarded.
- [ ] **Reuse the OHLCV Parquet cache across configs** (no re-fetch when a covering cache exists); do not re-backtest an identical generated strategy (by code hash).

### Frontend

- [ ] Surface **token + USD spend** (and configs-explored) in `AutoSessionStatusStrip` budget counters, read-only from the canonical `autoRun.budget` block (`tokens`/`maxTokens`, `usd`/`maxUsd`, `configsDone`/`maxConfigs`), alongside the existing rounds + wall-clock. Display-only formatting (round/label), no recomputation.
- [ ] Extend the `AutoRunStatus.budget` TS type (`sessionApi.ts`) to include the new fields, mirroring the backend `to_dict()` — read from the same canonical block, no second fetch.
- [ ] Open-universe configs render through the **existing** iteration cards (each card already shows its `params` symbol/timeframe) — no new component, no new route.

### New user-facing capability

Trigger an open-universe automated search from one API call (objective + budget only); watch ≥2 distinct configs stream into the session as iteration cards and the run stop at a hard token/USD budget, with live token/USD spend in the status strip.

### New information displayed

Token spend / USD cost (each against its cap) and configs-explored count in the automated-session status strip; iteration cards for distinct open-universe configs (varying symbol/timeframe).

### New user actions

None new at the control level — J-12 is API-triggered ("no browser") and the existing in-UI "Auto Run" control stays pinned-config this iteration. (A UI open-universe trigger is future; the UI still **tracks** the open-universe run live.)

### UI surface changes

Status strip budget counters extended with token/USD/configs. No new pages, panels, or routes.

### Product surface delta

The automated session graduates from "refine one pinned config" to "explore a small open universe under a real cost budget," and the cost is now visible — the workstation shows what the search is spending as it spends it.

### Blueprint conformance

No new home. Open-universe run state + budget counters live under **Right — Iterations → Automated-session status strip**; distinct configs live under **Right — Iterations → iteration history tree** (existing). Open-universe is started via the existing command endpoint `POST /api/auto-sessions` (blueprint already notes "pinned or open-universe"). No nav-skeleton change → no re-approval.

### Data-contract additions

**No new canonical value.** Token spend + USD cost are already registered in the **Budget counters** row (populated best-effort since iter-1); J-13 hard-enforces and *displays* them. `max_configs`/`configsDone` are added to that **same** row (same computing module `auto_session.py:BudgetTracker`, same serving endpoint `GET /api/sessions/{id}` → `autoRun.budget`). The open-universe controller is **orchestration only** — it computes no new metric and reuses the existing `BacktestPipeline` + `RobustScorer`, writing only the already-canonical iteration `params`, `autoRun.bestIterationId`, and `autoRun.budget`. Blueprint edited additively (no nav change → no re-approval): the **Budget-counters** row Notes now reflect token/USD hard-enforced iter-3 + shown in strip + `max_configs`/`configsDone`, and a reserve row **"(Layer-2, iter-3) Open-universe search"** documents the controller path as orchestration-only (no parallel store / no new endpoint / no new score). The run-state enum row already includes `error` (the iter-2 advisory tidy was applied previously — no change needed). No second computing module, no second endpoint, no recomputation in the UI.

## OUT OF SCOPE

- **J-14** staged SCREEN→PROMOTE cost tiering + model routing. iter-3 evaluates each explored config **uniformly** through the existing pipeline (incl. walk-forward, because the robust score is WFE-gated) — this is NOT a "cheap SCREEN" stage, so the SCREEN-skips-WF anti-goal is not triggered. Do **not** half-build staging now. Structure per-config evaluation as one reusable method so J-14 can wrap it in stages later without a rewrite.
- **J-15** global-history warm start / cross-session planner / prompt-cached history context.
- **J-16** multi-candidate leaderboard + overfit-gating visualization (the single best badge already exists; the ranked board is J-16).
- Autonomous strategy-idea invention beyond the small fixed seed-idea set.
- A UI control to trigger open-universe (J-12 is API-triggered; the in-UI Auto Run control stays pinned-config).
- Any edit to `shared/contracts.py` (frozen) or any new datastore/queue/broker.

## DEFINITION OF DONE

- [ ] **J-12** passes via browser-qa-agent / backend evidence: open-universe `POST` (no `symbol`/`timeframe`, `objective: "robust"`, small `budget`) → 200; ≥2 distinct configs (differing symbol and/or timeframe) appear as iterations; the run reaches a terminal state within budget; the best is marked by robust score.
- [ ] **J-13** passes: a tiny token/USD budget yields `stopReason = "budget-exhausted"`; the recorded token/USD spend is ≤ the cap (within one-call tolerance) and is visible in the status block; no iterations are added after the cap is reached.
- [ ] Required-still-passing remain green: J-07 (pinned start → 200 + appears in list), J-08 (live tracking), J-09 (terminal stop-reason + WFE best), J-10 (backend single source / survives reload), J-11 (server-side stop); J-01–J-06 no-regression.
- [ ] No anti-goal violation introduced (see reminders) — verified in code, not just claimed.
- [ ] Unit tests pass; no regressions — including `test_lookahead` / `test_determinism` / `test_sandbox` and the existing auto-session suite. (Pre-existing red `test_directions_cache` remains a non-blocking nice-to-have, untouched.)
- [ ] **Live-pixel debt cleared:** browser-qa captures real pixels for J-08 (status strip live-updating incl. token/USD; cards streaming without reload), J-10 (reload-mid-run survival), and the J-01 / J-05 manual regressions — with the frontend health-checked as serving across the whole browser-qa window.
- [ ] Dev handoff written at `docs/handoffs/goal-financial_free-iter-3-dev.md`.

## TESTING REQUIREMENTS

- **Browser (Frontend Present: yes):** J-08 + J-10 on an open-universe run (live tracking + reload-mid-run survival), plus J-01 and J-05 manual regressions — **clear the accumulated live-pixel debt**. Health-check the Vite frontend is serving at the start AND re-probe mid-window (iter-2 lesson: it was up at QA start then went down). If pixels blank under the documented Chrome-MCP hidden-tab render throttle, fall back to verifying via the exact backend endpoints the UI calls — but the goal is real pixels this time.
- **Unit/integration (hermetic, deterministic fake pipeline — existing `tests/test_auto_session.py` pattern):**
  - Open-universe controller explores ≥2 distinct configs from the bounded seed universe; best selected by `RobustScorer` across configs; terminal at `max_configs`.
  - `BudgetTracker.exceeded()` returns True at the token cap and at the USD cap (each independently), evaluated before the next unit of work; no config/iteration appended after a cap.
  - Token/USD accounting threads real (faked) SDK usage into `with_usage`; tokens→USD mapping asserted to an exact value; tracker remains immutable.
  - `max_configs` hard cap: `max_configs=2` evaluates exactly ≤2 configs.
  - Pinned-config path (J-07) unchanged: `symbol`+`timeframe` present still runs the single-config improvement-rounds loop to its terminal state.
  - Route: open-universe `POST` (no `symbol`/`timeframe`) now returns 200 (not 400); pinned `POST` still 200; pinned with unsupported `timeframe` still 400; `objective != "robust"` still 400.
  - B1+B2 race regression test (`stop` vs `save` under the shared lock) stays green for the open-universe loop.
- **Error cases:** missing `budget` → 422; `max_configs`/`max_tokens`/`max_usd` ≤ 0 → 422; a single config's generation/backtest failure is non-fatal (search continues); a run where every config fails terminates cleanly (`budget-exhausted`) without crashing; no API key/secret ever appears in the activity log or `autoRun` block.
- **Optional live key-gated smoke** (as in iter-1/2): one tiny real open-universe run to a terminal state if `OPENAI_API_KEY` is present.

## NOTES

- **Lessons applied** (from `lessons.md`):
  - *(iter-1)* Reuse the single `result_serialization.py` for node byte-shape — the open-universe path MUST NOT re-fork serialization.
  - *(iter-1)* Preserve the B1+B2 shared-lock co-design — no lock-free `autoRun` read-modify-write in the new loop; the `to_thread` off-loop hop and the `/stop` flag stay serialized by the per-session lock.
  - *(iter-2)* Keep the frontend serving across the **entire** browser-qa window and clear the accumulated J-08/J-10 + J-01/J-05 pixel debt — do not re-defer it.
  - *(iter-0)* Do NOT re-litigate the eager-load anti-goal (resolved iter-1): the open-universe path persists iterations via the lightweight `write_iteration` / lazy-detail path; the list/open path stays lightweight.
- **Token accounting reality:** real usage exists but is only logged at `compiler.py:303-310`; `GenerateStrategyResult` carries `model_used` but no token counts. Threading it through `generate_strategy`/`generate_insights` → controller is the bounded core of J-13.
- **Why this scope:** J-12 is the prerequisite for J-14 (staged screening needs a multi-config search to stage) and J-16 (a leaderboard needs candidates to rank); J-13 is the natural terminator for the search and completes a Data-Contract row that already half-exists. Tight 2-journey slice keeps it scorable; J-14/J-15/J-16 follow.
- **Coherence:** no new canonical value; hard-enforces + displays the already-registered token/USD counters and adds `max_configs` to the same Budget-counters row. Blueprint edits are additive (no nav change → no `blueprint.reapproval-requested`).
