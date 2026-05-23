# goal-financial_free-iter-4 Execution Plan

**Goal-mode iteration 4 — Layer-2 continued.** Target journey **J-14** (staged SCREEN→PROMOTE
cost-tiering for the open-universe search). Required-still-passing: J-12/J-13 (most at risk — the
open-universe loop is being restructured), J-07–J-11, no-regression J-01–J-06. Depth: **full**
(restructures open-universe control flow + model routing + budget-gating semantics + new hermetic
tests + a user-visible Activity-Log surface).

**Goal alignment / drift check.** The spec maps 1:1 to `docs/goal.md` J-14 and the session
`blueprint.md`, whose IA already reserves J-14's home ("Activity Log stage entries | Left — Activity
Log") and whose Data-Contract open-universe row already carries the additive iter-4 staging Notes.
**No drift, no new surface, no contract churn.** The spec is internally consistent and explicitly
bounds scope (see OUT OF SCOPE). This is a pure-orchestration restructure over the existing
pipeline/scorer/store — nothing here contradicts the goal or the anti-goals.

## What to Build

**Backend (the bulk — `apps/backend/backend/auto_session.py`, orchestration only, no new metric):**

- **Restructure `_run_open_universe` (`auto_session.py:809`) into a two-stage SCREEN→PROMOTE flow.**
  Reuse the existing `_create_iteration` → `BacktestPipeline`, `_build_node`/`result_serialization.py`
  node byte-shape, `_persist_new` → `session_store.write_iteration`, and the one `RobustScorer`. The
  **pinned** path (`_run_inner`) is **untouched** (protects J-07/J-09 + the
  `test_pinned_path_unchanged_runs_improvement_rounds` regression).
  - **SCREEN stage:** enumerate `seed_universe_configs(base, self.budget.max_configs)`. For each,
    evaluate with the **cheapest** model and **`wfv_enabled=False`** via
    `_create_iteration(replace(seed_cfg, model=screen_model), …, wfv_enabled=False, parent_id=None)`.
    Persist each as an iteration node (distinct configs still surface as cards → J-12 preserved).
    `replace(seed_cfg, model=screen_model)` makes the node's `modelUsed` show the cheap model
    (node `modelUsed = gen_result.model_used or config.model`, `auto_session.py:561`).
  - **Rank + select survivors:** rank screened candidates by the **canonical** `RobustScorer.score()`
    (`auto_session.py:236`) and take the top-`k`, `k = min(DEFAULT_PROMOTE_K, n_screened)`; whenever
    `n_screened ≥ 2`, **`k < n_screened` MUST hold**. Add module constant `DEFAULT_PROMOTE_K = 1`.
    Deterministic; ties broken by seed-config order (stable).
  - **PROMOTE stage:** for each survivor, evaluate with the **stronger** model and
    **`wfv_enabled=True`** via `_create_iteration(replace(survivor_cfg, model=promote_model), …,
    wfv_enabled=True, parent_id=<screened node id>)`, persisting it as a child of the screened node it
    was promoted from (screen→promote lineage in the tree). Reuse the same NL prompt it was screened on.
  - **Best selection (anti-goal-critical):** mark `autoRun.bestIterationId` via
    `RobustScorer.select_best()` over the **PROMOTED candidates' metrics ONLY**. ⚠️ `is_eligible`
    (`auto_session.py:249`) only rejects `wfe` when it is **not** None — a screened-only node
    (`wfe=None`) would otherwise pass eligibility and could be wrongly marked best. So the
    `candidates` list fed to `select_best`/best-marking MUST be built from promoted nodes only;
    screened-only nodes are NEVER eligible. `select_best` → `None` (no eligible promoted candidate)
    is the correct gated outcome.

- **Model routing — single source of truth.** Add `cheapest_model() -> str` to
  `apps/backend/shared/model_catalog.py` returning the min-rate model from `MODEL_RATES` (today
  resolves to `gpt-5.4-mini`). SCREEN uses `cheapest_model()`; PROMOTE uses the **request `model`**
  (defaults to `DEFAULT_MODEL`). Tier selection lives in the catalog, not hard-coded in
  `auto_session.py`. Routing is scoped to the open-universe path **only**; pinned keeps `config.model`.

- **Budget semantics across stages (correctness-critical).** `max_configs` is the **SCREEN-breadth**
  cap: `configs_done` counts SCREEN candidates only (`with_config_completed()` once per screen), and
  the full `exceeded()` (`auto_session.py:158-176`) gates **before each SCREEN unit**. **Do NOT reuse
  `exceeded()` to gate PROMOTE** — once SCREEN fills `configs_done` to `max_configs`, `exceeded()` is
  already true (confirmed: line 168) and would skip PROMOTE entirely. Add
  `BudgetTracker.cost_exceeded()` checking **only** `max_tokens`/`max_usd`/`max_wall_clock_sec` (NOT
  configs/iterations); gate each PROMOTE unit on that. Leave `exceeded()` semantics **unchanged**
  (J-13 tests depend on them). Promote generations accrue real USD via the existing `_account_usage`
  (`auto_session.py:522`, stronger model → more USD per `MODEL_RATES`) on the one immutable tracker;
  a token/USD cap hit during SCREEN or PROMOTE still halts `budget-exhausted` and starts no further
  unit. **No new budget counter / status-strip value.**

- **Activity-log visibility of both stages** via the existing `_append_activity` +
  `session_store.append_activity_entries` (canonical records; no new store/schema fork):
  - SCREEN **stage header** — names the cheap model + "no walk-forward" + number of candidates screened;
  - one entry per screened candidate (symbol/timeframe; a score from the canonical `RobustScorer` if a
    number is shown);
  - PROMOTE **stage header** — "top-k of N" (k < N) + the stronger model + "walk-forward"; then one
    entry per promoted candidate.
  - **Recommended (lowest-risk) mechanism:** reuse `type:"auto-run"` entries (already rendered by
    `ActivityLogEntry.tsx:27-34`) with explicit `SCREEN —` / `PROMOTE —` text labels → minimal/zero FE
    change. No secrets/keys ever written.

- **Preserve B1+B2.** All `autoRun` reads/writes stay on `_save_auto_run` / `_stop_requested` under
  the shared per-session `asyncio.Lock`; store I/O off-loop (`_run_off_loop`); backtests
  semaphore-guarded inside `_create_iteration`. A `/stop` mid-SCREEN or mid-PROMOTE → `stopped` at the
  next checkpoint, no further node appended, best-so-far preserved (J-11).

- **Reuse OHLCV Parquet cache + code-hash dedup** across both stages. A SCREEN backtest (`wfv=False`)
  and a PROMOTE backtest (`wfv=True`) have distinct `_backtest_cache_key` (includes the wfv flag) so
  the promote walk-forward correctly runs — added fidelity, not a forbidden re-backtest. Re-generating
  a survivor with the stronger model is deliberate routing, not "re-generating an identical strategy."

**Frontend (display-only — `apps/frontend/src/components/ActivityLogEntry.tsx`):**

- If the backend reuses `type:"auto-run"` (recommended), **confirm** the existing `auto-run` branch
  (lines 27-34) renders the SCREEN/PROMOTE labelled entries legibly → likely **no code change**. If
  dedicated `screen`/`promote` entry types are added instead, add matching render branches consistent
  with the existing icon/typography idiom (Zap icon, violet text — no ad-hoc styling). Promoted cards
  already display their own `modelUsed` + walk-forward section, so the stronger-model/WF-on-promoted
  distinction is visible on cards with no card change.
- **No new page, panel, route, or nav entry. No second data fetch** — the Activity Log already streams
  from the canonical `GET /api/sessions/{id}`.

## Agents Required
- developer: **yes** — backend (SCREEN→PROMOTE restructure, `cost_exceeded()`, `cheapest_model()`,
  `DEFAULT_PROMOTE_K`, staged activity log) + frontend (confirm/extend the `auto-run` render branch).
- backend-data: **yes** (open-universe controller restructure + model routing + budget gating).
- frontend-ux: **yes** (display-only Activity-Log render confirmation; no new surface).

## Frontend Present

Frontend Present: yes

## Files to Create/Modify
- `apps/backend/shared/model_catalog.py` — ADD `cheapest_model() -> str` (min-rate over `MODEL_RATES`;
  → `gpt-5.4-mini` today). Additive; not a frozen contract.
- `apps/backend/backend/auto_session.py` — ADD `DEFAULT_PROMOTE_K = 1`; ADD
  `BudgetTracker.cost_exceeded()` (token/USD/wall-clock only); restructure `_run_open_universe` into
  SCREEN→PROMOTE (cheap/no-WF screen, score-ranked top-k promote with WF + stronger model, best from
  promoted only). `_run_inner`, `exceeded()`, `seed_universe_configs`, `RobustScorer`, `_build_node`
  all reused unchanged.
- `apps/frontend/src/components/ActivityLogEntry.tsx` — confirm `auto-run` renders SCREEN/PROMOTE
  labels (no change if reusing `auto-run`); small additive branch only if dedicated types are chosen.
- `apps/backend/tests/test_auto_session.py` — update existing open-universe tests' call-count
  expectations to the staged flow **without weakening the invariant each protects**; ADD the J-14
  scenarios below.
- `apps/backend/tests/auto_session_helpers.py` — extend `FakePipeline.generate_strategy` to record its
  `model` kwarg (test-helper-only) for a direct SCREEN-cheap / PROMOTE-stronger assertion.
- `apps/backend/tests/test_model_rates.py` (or a small new test) — assert `cheapest_model()` returns
  the min-rate catalog model.
- `docs/handoffs/goal-financial_free-iter-4-dev.md` — dev handoff (required by DoD).
- `runs/goal-session-financial_free/state/blueprint.md` — **no edit needed**: the goal-decomposer
  already added the additive iter-4 staging Notes to the open-universe Data-Contract row (verified in
  the current blueprint). Do **not** add a row, change nav, or set `blueprint.reapproval-requested`.

## UI Evolution (Frontend Present: yes)
- **New user-facing capability:** an open-universe run visibly spends cheap-first — the Activity Log
  shows a cheap SCREEN sweep over several seed configs and a PROMOTE step escalating only the best `k`
  (k < screened) to walk-forward + a stronger model; the marked best comes only from promoted,
  WFE-gated candidates.
- **New information displayed:** SCREEN/PROMOTE stage entries (cheap model + candidate count; "top-k
  of N" + stronger model + walk-forward). The screen→promote lineage shows in the iteration tree
  (promoted node is a child of its screened candidate); promoted cards show the stronger `modelUsed` +
  a walk-forward section, screened cards show the cheap model + none.
- **New user actions:** none (J-14 is observed on the existing API-triggered open-universe run).
- **UI surface changes:** Activity Log gains SCREEN/PROMOTE stage entries. No new pages, panels,
  routes, or nav.
- **Navigation changes:** none (no nav-skeleton change → no blueprint re-approval).

## Visual Requirements (Frontend Present: yes)
- **Component patterns:** reuse the existing `ActivityLogEntry` `auto-run` branch (Zap icon, violet
  `text-violet-600` label) — no new component. If dedicated `screen`/`promote` types are added, mirror
  that icon/typography idiom exactly.
- **Layout:** unchanged — the existing two-panel shell; SCREEN/PROMOTE entries live in the Left
  Activity Log; promoted/screened nodes surface via existing Right-panel cards/tree.
- **Key visual effects:** none new — dense dark analytical workstation idiom; reuse existing styling.
- **States to handle:** SCREEN entries (cheap model, no WF), PROMOTE entries ("top-k of N", stronger
  model, WF), the best-marked entry; active/running during the loop; terminal `budget-exhausted` /
  `stopped`. Screened-only cards render with no WF section (valid existing shape); promoted cards
  render the WF section.

## Key Test Scenarios
**Hermetic (fake pipeline — `tests/auto_session_helpers.py::FakePipeline`):**
- **Stage routing:** SCREEN calls use `wfv_enabled=False` + the cheap model; PROMOTE calls use
  `wfv_enabled=True` + the stronger model — assert via `fake.execute_calls[*].wfv_enabled`, the
  recorded `generate_strategy` `model` kwarg, and the persisted nodes' `modelUsed`.
- **k < N:** with ≥3 seed configs screened, exactly `DEFAULT_PROMOTE_K` (=1) is promoted; count of
  WF-bearing (promoted) nodes < count of screened nodes.
- **Best is WFE-gated from promoted only:** a screened-only candidate with high raw return but no
  walk-forward is NOT marked best; the marked best is a promoted node satisfying the WFE gate
  (extend/port `test_open_universe_best_is_wfe_gated_not_highest_return`).
- **Stop honored mid-stage:** a `/stop` during SCREEN and during PROMOTE → `stopped`, appends no
  further node, preserves best-so-far.
- **Hard budget across stages (J-13 preserved):** a token/USD cap hit during SCREEN or before PROMOTE
  halts `budget-exhausted` with no unit started past the cap (update
  `test_open_universe_stops_at_token_cap_no_config_after` to the staged flow, preserving the "no work
  past cap, spend ≤ cap within one-call tolerance" assertion).
- **J-12 invariants preserved:** ≥2 distinct configs (differing symbol/timeframe) still appear as
  iteration nodes; terminal within budget (update existing open-universe call-count expectations
  **without** weakening each invariant).
- **Model-routing single source:** `cheapest_model()` returns the min-rate catalog model; SCREEN uses it.
- **Error cases:** a single SCREEN or PROMOTE generation/backtest failure is non-fatal (logged, search
  continues); all-screened-fail terminates cleanly (`budget-exhausted`, best `None`); a degenerate
  single-config screen promotes that one config (no crash); exactly-one-of symbol/timeframe still 400
  (unchanged route).
- **Full hermetic suite:** no new failures beyond the known pre-existing red
  `test_directions_cache::test_write_and_read_full_round_trip`; invariants `test_lookahead`,
  `test_determinism`, `test_sandbox` stay green.

**Browser (load-bearing this iteration — clears 3-iteration pixel debt):**
- **J-14:** on a live open-universe run, the Activity Log visibly shows the SCREEN stage (several cheap
  candidates, cheap model, no WF) and the PROMOTE stage ("top-k of N", k<N, stronger model,
  walk-forward); a promoted card shows the stronger `modelUsed` + a WF section while a screened-only
  card shows the cheap model + no WF.
- **Carry-forward J-08 / J-10 pixels:** capture the status-strip token/USD/configs chips live-updating
  without reload (J-08) and the reload-mid-run survival step (J-10).
- **Process requirement (iter-2/iter-3 lesson):** run browser-qa against the **same** live
  backend+frontend the full-QA uses, in the **same** window, on an **uncontended** foreground tab, and
  **health-check the frontend stays serving for the whole window** (re-probe mid-run). A blank-pixel
  result that is *actually* the documented Chrome-MCP hidden-tab throttle is an acceptable fallback
  **only** with the live-service health-check recorded and the backend-endpoint substitute executed
  (`GET /api/sessions/{id}` → `autoRun` + activity entries); "could not run / services down" is NOT
  acceptable this time.
- **Recommended live QA config (cheap, demonstrative):** open-universe `POST /api/auto-sessions` with
  no `symbol`/`timeframe`; `objective:"robust"`; a pinned EMA fast/slow crossover `natural_language`
  (so a promoted candidate is eligible and the best-marking path is exercised, not just gated to None);
  `model:"claude-haiku-4-5"` (the stronger/PROMOTE model — observably different from the cheapest
  `gpt-5.4-mini` SCREEN model, yet inexpensive); a short date range; `budget:{ max_iterations: 2,
  max_configs: 3, max_tokens/max_usd generous enough to complete screen+promote }`. k=1 < 3 makes k<N
  unambiguous; the cheap SCREEN model + short range keep cost tiny.

## Guardrails / Anti-goals to honor (coherence + DoD)
- Coherence: reuse the single `result_serialization.py` (no re-fork — iter-1 lesson); keep the
  list/open path lazy/lightweight (iter-0 lesson, resolved — do not re-litigate); any displayed score
  flows from the one `RobustScorer.score()`, budget values from the one `BudgetTracker` (no second
  computing path — the coherence-auditor's hard-FAIL gate). Controller stays orchestration-only (no new
  metric) → expect COHERENCE-PASS.
- Anti-goals: SCREEN runs neither walk-forward nor the strongest model; best WFE-gated from promoted
  only; existing `BacktestPipeline`/sandbox/deterministic engine reused; bounded seed universe respected
  (no exchange-wide fan-out); same file store, no schema fork; hard budget never exceeded; event loop
  non-blocking; B1+B2 preserved; frozen `contracts.py` untouched; immutable `BudgetTracker` (replace,
  never mutate in place); no secrets in activity entries/artifacts.

## Out of Scope (do not build — per spec)
- J-15 (global-history warm start / LLM planner / cross-session mining + prompt caching); J-16
  (multi-candidate overfit-gating leaderboard UI). SCREEN ordering this iteration is the deterministic
  seed-universe order ranked by the cheap robust score — not history-informed.
- New request fields (`screen_model`/`promote_model`/`promote_k`) — use internal defaults; keep
  `CreateAutoSessionRequest` unchanged.
- Changing the pinned-config path (`_run_inner`) or its single-model behavior.
- Expanding the seed universe beyond `SEED_UNIVERSE_MAX`, or any `shared/contracts.py` change.
- De-flaking `test_post_returns_before_loop_completes_and_get_stays_responsive` or fixing the
  pre-existing red `test_directions_cache` — non-blocking carry-forward (mention in handoff only if
  touched incidentally).
