# Goal Iteration 4 — Staged SCREEN→PROMOTE cost-tiering for the open-universe search (J-14)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** financial_free
- **Iteration:** 4
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes
- **Target journeys:** J-14
- **Required-still-passing journeys:** J-12, J-13 (most at risk — the open-universe loop is being restructured), J-07, J-08, J-09, J-10, J-11 (and no-regression on J-01, J-02, J-03, J-04, J-05, J-06)
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are reserved for promoted candidates.
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify.
  - Identical generated strategies (by code hash) MUST NOT be re-generated or re-backtested; the OHLCV Parquet cache MUST be reused across configs (no re-fetch when a covering cache exists).
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - The automated-session `autoRun` status MUST be persisted to the durable store and survive a worker restart and a browser reload; it MUST NOT live only in browser memory or a non-persisted in-process variable.
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.
  - The LLM-planner / history context MUST use prompt caching; the leaderboard/history MUST NOT be re-sent uncached every round. *(Cross-session history mining is J-15 — see OUT OF SCOPE; do not start it here.)*
  - No lookahead; no nondeterministic backtests (slippage seeded); the sandbox MUST block file I/O, network, `exec`/`eval`, `__import__`, `open`, `os`. The frozen dataclasses in `shared/contracts.py` MUST NOT be mutated in place. No relational DB/SQLite; OHLCV stays single-Parquet-per-(symbol,timeframe); `BACKTEST_STORE_DIR` MUST NOT default to a volatile `/tmp` path.
  - *(All remaining anti-goals in `docs/goal.md` stay in force even when not restated here.)*

## GOAL

An open-universe automated run now spends cheap first: it **SCREENs** several seed configs on the cheapest model with **no walk-forward**, then **PROMOTEs only the top-k survivors** (k < number screened) to full evaluation — walk-forward **and** a stronger model — and marks the cross-config best strictly from those WFE-gated promoted candidates. Both stages are legible in the session Activity Log.

## BACKGROUND

Layer-1 (J-07–J-11) and the first two Layer-2 journeys (J-12 open-universe search, J-13 hard token/USD/`max_configs` budget) are complete and green. Today the open-universe loop `_run_open_universe` (`apps/backend/backend/auto_session.py:809`) evaluates **every** seed config *uniformly* — each through `_create_iteration(..., wfv_enabled=True)` on the single request `model` — i.e. walk-forward and the chosen model run on *all* configs. J-14 turns that flat loop into a two-stage cost-tiered search: a cheap SCREEN pass (cheapest model, `wfv_enabled=False`) over the budget-bounded seed subset, then a PROMOTE pass that re-evaluates only the top-k screened survivors with walk-forward + a stronger model. iter-3 deliberately left `_create_iteration` as the single reusable per-config unit precisely "so J-14 can wrap it in cheap-SCREEN/PROMOTE stages later without a rewrite" (`auto_session.py:893-895`) — this iteration does exactly that. The evaluator recommended **full** depth: this restructures the open-universe control flow, adds model routing, touches the request→budget mapping, needs new hermetic tests plus updates to the existing open-universe tests, and adds a user-visible activity-log surface.

J-14 is the prerequisite for J-15 (global-history warm start) and J-16 (overfit-gating leaderboard UI), which stay deferred.

**Carry-forward pixel debt (evaluator + iter-2/iter-3 lessons).** The auto-session status-strip chips (J-08 live token/USD/configs updating; J-10 reload-mid-run survival) have **never** been confirmed at the pixel layer — three iterations running the dedicated browser-qa-agent SKIPPED (FE/BE torn down in *its* window) or was blocked by the documented Chrome-MCP hidden-tab throttle compounded by a concurrent QA holding the foreground tab. J-14 adds genuinely new UI (SCREEN/PROMOTE activity-log entries), so browser-qa runs again — this iteration MUST clear that debt decisively (see TESTING REQUIREMENTS).

## IN SCOPE

### Backend

- [ ] **Restructure `_run_open_universe` into a two-stage SCREEN→PROMOTE flow** (`apps/backend/backend/auto_session.py`). Keep it orchestration-only: reuse the existing `_create_iteration` → `BacktestPipeline` (generate → backtest → optional walk-forward), the existing `_build_node` / `result_serialization.py` node byte-shape (no schema fork), `_persist_new` → `session_store.write_iteration` (lazy detail; lightweight list/open path preserved), and the canonical `RobustScorer`. The **pinned** path (`_run_inner`) is **untouched** (protects J-07/J-09 and the `test_pinned_path_unchanged_runs_improvement_rounds` regression test).
  - **SCREEN stage:** enumerate the budget-bounded seed configs via the existing `seed_universe_configs(base, self.budget.max_configs)`. For each, evaluate with the **cheapest** model and **`wfv_enabled=False`** (no walk-forward). Persist each as an iteration node (so distinct configs still surface as cards → J-12 invariant preserved). Use `dataclasses.replace(seed_cfg, model=screen_model)` so the frozen config carries the screen model (`modelUsed` on the node then shows the cheap model).
  - **Rank + select survivors:** rank screened candidates by the **canonical** `RobustScorer.score()` (the one scorer — do **not** introduce a second scoring path) and take the top-`k` where `k = min(DEFAULT_PROMOTE_K, <number screened>)` and, whenever ≥2 configs were screened, `k < number screened` MUST hold. Add a module constant `DEFAULT_PROMOTE_K = 1`. Ranking is deterministic (ties broken by seed-config order).
  - **PROMOTE stage:** for each survivor, evaluate with a **stronger** model and **`wfv_enabled=True`** (walk-forward) via `_create_iteration(replace(survivor_cfg, model=promote_model), ..., wfv_enabled=True)`, persisting it as a new child node whose `parentId` is the screened node it was promoted from (the screen→promote lineage then shows in the iteration tree). Reuse the same NL strategy prompt the config was screened on.
  - **Best selection:** mark `autoRun.bestIterationId` via `RobustScorer.select_best()` over the **PROMOTED** candidates' metrics **only** (they alone carry real WFE) — screened-only nodes are NEVER eligible to be marked best. This keeps the "best is WFE-gated, derives from walk-forward OOS" invariant (J-16) and the J-09 best-marking intact. `select_best` returning `None` (no eligible promoted candidate) is the correct gated outcome.
- [ ] **Model routing — single source of truth.** Add a helper to `apps/backend/shared/model_catalog.py` that returns the cheapest catalog model by `MODEL_RATES` (e.g. `cheapest_model() -> str`; today resolves to `gpt-5.4-mini`). The open-universe SCREEN stage uses `cheapest_model()`; the PROMOTE stage uses the **request `model`** (the user's "full-evaluation" model; defaults to `DEFAULT_MODEL`). Model-tier selection lives in the catalog, not hard-coded in `auto_session.py`. This routing is scoped to the open-universe path **only**; the pinned path keeps using `config.model` as-is.
- [ ] **Budget semantics across the two stages (correctness-critical).** `max_configs` is the **SCREEN-breadth** cap — `configs_done` counts SCREEN candidates explored, and the full `BudgetTracker.exceeded()` (`auto_session.py:158-176`, incl. the `configs_done >= max_configs` and token/USD/wall-clock checks) gates **before each SCREEN unit**. **Do NOT naively reuse `exceeded()` to gate PROMOTE:** once SCREEN fills `configs_done` to `max_configs`, `exceeded()` is already true, which would skip PROMOTE entirely. PROMOTE is a bounded refinement (≤ `k` already-counted configs, not new exploration), so gate **each PROMOTE unit on the cost caps only** (token / USD / wall-clock) — recommended: add a `BudgetTracker.cost_exceeded()` helper that checks `max_tokens`/`max_usd`/`max_wall_clock_sec` (NOT configs/iterations), leaving the existing `exceeded()` semantics (which J-13 tests depend on) unchanged. Real token/USD usage is accounted after every generate call via the existing `_account_usage` (J-13) — promote generations (stronger model) accrue more USD per the rate table, all on the one immutable tracker; a token/USD cap reached during SCREEN or PROMOTE still halts with `budget-exhausted` and starts no further unit. **No new budget counter / status-strip value is introduced** (see Data-contract additions).
- [ ] **Activity-log visibility of both stages** via the existing `_append_activity` + `session_store.append_activity_entries` (already-canonical session records; no new store, no schema fork). The log MUST make clear, in the Activity Log surface:
  - a **SCREEN** stage header naming the cheap model + "no walk-forward" and the number of candidates screened;
  - one entry per screened candidate (its symbol/timeframe; a score from the canonical `RobustScorer` if a number is shown);
  - a **PROMOTE** stage header stating "top-k of N" (k < N) and the stronger model + "walk-forward", followed by an entry per promoted candidate.
  - Recommended mechanism: reuse `type:"auto-run"` entries (already rendered) with explicit `SCREEN`/`PROMOTE` labels, OR add dedicated `screen`/`promote` entry types — either way the two stages MUST be visually distinguishable in the UI and capturable by browser-qa. No secrets/keys ever written to these entries.
- [ ] **Preserve B1+B2.** All `autoRun` reads/writes stay on `_save_auto_run` / `_stop_requested` under the shared per-session `asyncio.Lock`; store I/O stays off the event loop (`_run_off_loop`); backtests stay semaphore-guarded inside `_create_iteration`. A `/stop` mid-SCREEN or mid-PROMOTE transitions to `stopped` at the next checkpoint with no further node appended and the best-so-far preserved (J-11).
- [ ] **Reuse the OHLCV Parquet cache + code-hash backtest dedup** across both stages (no re-fetch when covered; no re-backtest of identical code+params+wfv). Note: a SCREEN backtest (`wfv_enabled=False`) and a PROMOTE backtest (`wfv_enabled=True`) have distinct dedup keys (`_backtest_cache_key` includes the wfv flag) so the promote walk-forward correctly runs — this is added fidelity, not a forbidden re-backtest. Re-generating a survivor with the stronger model is deliberate model routing, not "re-generating an identical strategy."

### Frontend

- [ ] **Render the SCREEN and PROMOTE stage entries** in the Activity Log so a user can see "screened N cheap candidates → promoted top-k (k<N) to full evaluation." If the backend reuses `type:"auto-run"`, confirm the existing `ActivityLogEntry` `auto-run` branch (`apps/frontend/src/components/ActivityLogEntry.tsx:27-34`) renders them legibly; if dedicated `screen`/`promote` types are added, add matching render branches consistent with the existing visual style (DESIGN SYSTEM: dense dark analytical workstation; reuse the existing icon/typography idiom — no raw ad-hoc styling). Promoted iteration cards already display their own `modelUsed` and walk-forward section, so the stronger-model + WF-on-promoted distinction is visible on the cards too (no card change required).
- [ ] No new page, panel, route, or nav entry. No second data fetch — the Activity Log already streams from the canonical `GET /api/sessions/{id}`.

### New user-facing capability

An open-universe run visibly spends cheap-first: the Activity Log shows a cheap SCREEN sweep over several seed configs and a PROMOTE step that escalates only the best k (k < screened) to walk-forward + a stronger model; the marked best comes only from those promoted, WFE-gated candidates.

### New information displayed

SCREEN and PROMOTE stage entries in the Activity Log (cheap model + candidate count for SCREEN; "top-k of N", stronger model, walk-forward for PROMOTE). The screen→promote lineage is visible in the iteration tree (promoted node is a child of its screened candidate); promoted cards show the stronger `modelUsed` + a walk-forward section, screened cards show the cheap model + none.

### New user actions

None. J-14 is observed on an API-triggered open-universe run (same `POST /api/auto-sessions` open-universe trigger from J-12); no new control is added this iteration.

### UI surface changes

Activity Log gains SCREEN/PROMOTE stage entries. No new pages, panels, routes, or nav.

### Product surface delta

The optimizer stops paying full price for every candidate: it triages many configs cheaply and reserves the expensive walk-forward + stronger model for the few that look best — and the user can see that decision happen in the Activity Log.

### Blueprint conformance

No new surface. J-14's home is already reserved in `blueprint.md` Information Architecture — "J-14 Staged screening (SCREEN/PROMOTE) | Activity Log stage entries | Left — Activity Log". The SCREEN/PROMOTE entries live in the existing Left Activity Log; promoted/screened nodes surface through the existing Right-panel iteration cards/tree. **No nav-skeleton change → no re-approval required.**

### Data-contract additions

**None.** No new "same-everywhere" value is introduced:
- SCREEN/PROMOTE stage entries are **activity records** — already covered by the registered "Shared records … suggestion record (insights/suggestions)" / activity row, served read-only by the canonical `GET /api/sessions/{id}`.
- Any score shown in a stage entry MUST be computed by the **one** `RobustScorer` (the registered "Robust objective score + best marker" source) — no second scoring path, no recomputation in the UI.
- `modelUsed` and `walkForwardStatus`/`walkForwardResult` already exist on the iteration node contract; the per-stage model and WF flag reuse them.
- Budget counters (`configsDone`/`tokens`/`usd` …) are unchanged from iter-3 — promote work accrues onto the same single tracker; no new counter.

The `blueprint.md` Data-Contract "(Layer-2, iter-3) Open-universe search" row Notes are updated **additively** to record that staging (J-14) has landed (mechanism + the SCREEN-no-WF/cheap-model, PROMOTE-top-k-WF/stronger-model, best-WFE-gated-among-promoted invariants). No row added, no nav change.

## OUT OF SCOPE

- **J-15 (global-history warm start / cross-session planner context + prompt caching).** Do NOT mine prior sessions or add an LLM planner this iteration. SCREEN ordering this iteration is the deterministic seed-universe order ranked by the cheap robust score — not a history-informed plan.
- **J-16 (multi-candidate overfit-gating leaderboard UI).** The single best badge already exists and stays WFE-gated; a ranked leaderboard visualization is the next journey.
- **New request fields** for `screen_model` / `promote_model` / `promote_k`. Use the internal defaults (cheapest catalog model for SCREEN; request `model` for PROMOTE; `DEFAULT_PROMOTE_K`); keep `CreateAutoSessionRequest` unchanged (no contract churn).
- **Changing the pinned-config path** (`_run_inner`) or its single-model behavior.
- **Expanding the seed universe** beyond the existing `SEED_UNIVERSE_MAX` bound, or any change to `shared/contracts.py`.
- **De-flaking** `test_post_returns_before_loop_completes_and_get_stays_responsive` and **fixing** the pre-existing red `test_directions_cache` — non-blocking carry-forward, not this journey (mention in handoff if touched incidentally; otherwise leave).

## DEFINITION OF DONE

- [ ] **J-14 passes**: an open-universe run's Activity Log shows a SCREEN stage with several cheap candidates and a PROMOTE stage applied to only the top-k (k < number screened); walk-forward and the stronger model appear **only** on promoted configs (verified via the activity log AND the persisted nodes' `walkForwardStatus`/`modelUsed`).
- [ ] **Required-still-passing journeys remain green** — especially J-12 (≥2 distinct configs still appear as iterations; terminal within budget; best by robust score) and J-13 (token/USD/`max_configs` hard caps still enforced, no unit started past a cap). J-07–J-11 and J-01–J-06 show no regression.
- [ ] **No anti-goal violation**: SCREEN runs neither walk-forward nor the strongest model; best is WFE-gated from promoted only; existing `BacktestPipeline`/sandbox/deterministic engine reused; bounded seed universe respected; same file store / no schema fork; hard budget never exceeded; event loop non-blocking; B1+B2 preserved; `contracts.py` untouched; no secrets in artifacts.
- [ ] **Unit/integration tests pass**; the full hermetic backend suite shows no new failures beyond the known pre-existing red `test_directions_cache` (anti-goal invariants `test_lookahead`/`test_determinism`/`test_sandbox` green).
- [ ] **Browser-qa runs against live services in the same window** (see TESTING REQUIREMENTS) and either captures the J-14 SCREEN/PROMOTE pixels + the carry-forward J-08/J-10 strip/reload pixels, or — only if blocked by the documented Chrome-MCP throttle — records the spec-sanctioned backend-endpoint fallback **with** the live-service health-check evidence and an explicit, documented reason.
- [ ] Dev handoff written at `docs/handoffs/goal-financial_free-iter-4-dev.md`.
- [ ] `blueprint.md` open-universe row Notes updated additively (no nav change, no `blueprint.reapproval-requested`).

## TESTING REQUIREMENTS

- **Browser (load-bearing this iteration):**
  - **J-14** — on a live open-universe run, the Activity Log visibly shows the SCREEN stage (several cheap candidates, cheap model, no WF) and the PROMOTE stage ("top-k of N", k<N, stronger model, walk-forward); a promoted iteration card shows the stronger `modelUsed` + a walk-forward section while a screened-only card shows the cheap model + no WF.
  - **Clear the carry-forward pixel debt (J-08, J-10):** capture the status-strip token/USD/configs chips live-updating without reload (J-08), and the reload-mid-run survival step (J-10).
  - **Process requirement (iter-2/iter-3 lesson):** the dedicated browser-qa-agent has SKIPPED the last two iterations because the FE/BE were torn down in *its* window, and the throttle has been compounded by a concurrent QA holding the foreground tab. This iteration MUST run browser-qa against the **same** live backend+frontend the full-QA uses, in the **same** window, on an **uncontended** foreground tab, and **health-check the frontend stays serving for the whole window** (re-probe mid-run). A blank-pixel result that is *actually* the documented hidden-tab throttle is an acceptable fallback **only** with the live-service health-check recorded and the backend-endpoint substitute executed; "could not run / services down" is NOT an acceptable reason this time.
  - Honor the documented headless render-throttle memory: when pixels are blank despite healthy services, verify the journey via the exact backend endpoints the UI polls (`GET /api/sessions/{id}` → `autoRun` + activity entries).
- **Unit/integration (hermetic, fake pipeline — `tests/auto_session_helpers.py::FakePipeline`):**
  - SCREEN calls use `wfv_enabled=False` and the cheap model; PROMOTE calls use `wfv_enabled=True` and the stronger model — assert via `fake.execute_calls[*].wfv_enabled` and the persisted nodes' `modelUsed` (and/or extend `FakePipeline.generate_strategy` to record its `model` kwarg for a direct assertion — a test-helper-only change).
  - **k < number screened**: with ≥3 seed configs screened, exactly `DEFAULT_PROMOTE_K` (=1) are promoted; assert the count of WF-bearing (promoted) nodes < count of screened nodes.
  - **Best is WFE-gated from promoted only**: a screened-only candidate with a high raw return but no walk-forward is NOT marked best; the marked best is a promoted node and satisfies the WFE gate (extend/port `test_open_universe_best_is_wfe_gated_not_highest_return`).
  - **Stop honored mid-stage**: a `/stop` during SCREEN and during PROMOTE transitions to `stopped`, appends no further node, and preserves best-so-far.
  - **Hard budget across stages (J-13 preserved)**: a token/USD cap reached during SCREEN or before PROMOTE halts with `budget-exhausted` and no unit started past the cap (update `test_open_universe_stops_at_token_cap_no_config_after` to the staged flow while preserving the "no work past cap, spend ≤ cap within one-call tolerance" assertion).
  - **J-12 invariants preserved**: ≥2 distinct configs (differing symbol/timeframe) still appear as iteration nodes; terminal within budget (update the existing open-universe tests' call-count expectations to the staged flow **without** weakening the invariant each asserts).
  - **Model-routing single source**: `cheapest_model()` returns the min-rate catalog model; assert SCREEN uses it.
- **Error cases:** a single SCREEN or PROMOTE config's generation/backtest failure is non-fatal (logged, search continues); all-screened-fail terminates cleanly (`budget-exhausted`, best `None`); a degenerate single-config screen promotes that one config (no crash). Invalid/ambiguous requests (exactly one of symbol/timeframe) still 400 (unchanged route behavior).

## NOTES

- **Budget-note vs J-14 reconciliation (decided).** The global journey note says "tiny budgets (≤ 2 screen iterations …)"; J-14 specifically requires "several cheap candidates" and "top-k (k < number screened)". The specific journey acceptance binds: the QA recipe SCREENs **≥3** seed configs and PROMOTEs **1** (k=1 < 3) so k<N is unambiguous, and keeps cost tiny by using the cheapest model for SCREEN, a short date range, and running the expensive walk-forward + stronger model exactly once (on the single promoted survivor). This is comparable in cost to the iter-3 live open-universe QA runs.
- **Recommended live QA config (real-LLM, cheap, demonstrative):** open-universe `POST /api/auto-sessions` with no `symbol`/`timeframe`; `objective:"robust"`; a pinned trading `natural_language` that reliably trades (e.g. an EMA fast/slow crossover) so a promoted candidate is eligible and the best-marking path is exercised (not just correct-gating-to-None); `model:"claude-haiku-4-5"` (the stronger/PROMOTE model — observably different from the cheapest `gpt-5.4-mini` SCREEN model, yet inexpensive); a short date range; `budget:{ max_iterations: 2, max_configs: 3, max_tokens/max_usd generous enough to complete screen+promote }`. Setting `model` to a non-cheapest tier is what makes "stronger model only on promoted" observable — note this in the test plan. (J-13's hard-cap demonstration is already green and need only be *not regressed*, not re-proven, here.)
- **Coherence guardrails (lessons applied):** reuse the single `result_serialization.py` for node byte-shape — do NOT re-fork it (iter-1 lesson); keep the list/open path lazy/lightweight — do NOT eager-parse heavy payloads (iter-0 lesson, resolved iter-1, do not re-litigate); any displayed score flows from the one `RobustScorer` and budget values from the one `BudgetTracker` (no second computing path — this is the coherence-auditor's hard FAIL gate). The open-universe controller stays orchestration-only (no new metric), so the coherence audit should remain COHERENCE-PASS.
- **Restructure risk.** Several existing open-universe tests assert the *uniform-loop* call counts (`test_open_universe_explores_distinct_configs_and_marks_best`, `…_terminal_at_max_configs`, `…_threads_tokens_and_usd`, `…_stops_at_token_cap_no_config_after`, `…_best_is_wfe_gated_not_highest_return`, `…_stop_request_transitions_to_stopped`, `…_stop_racing_save_is_not_dropped`). Expect to update their expected call counts to the staged flow — but preserve the invariant each one protects. Do not delete a regression guard to make a count pass.
- This iteration deliberately introduces **no** new request field, endpoint, page, route, nav entry, datastore, or `contracts.py` change — the staged search is pure orchestration over the existing pipeline/scorer/store, surfaced through the already-reserved Activity Log home.
