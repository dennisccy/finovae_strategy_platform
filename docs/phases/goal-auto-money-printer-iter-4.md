# Goal Iteration 4 — Staged SCREEN→PROMOTE (cheap-first model/WF routing)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** auto-money-printer
- **Iteration:** 4
- **Mode:** next
- **Depth:** full
- **Target journeys:** J-14
- **Required-still-passing journeys:** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09, J-10, J-11, J-12, J-13
- **Frontend Present:** no (code); the new capability is visible through the **existing** session activity feed — browser-qa MUST verify it renders)
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are reserved for promoted candidates.
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - Identical generated strategies (by code hash) MUST NOT be re-generated or re-backtested; the OHLCV Parquet cache MUST be reused across configs (no re-fetch when a covering cache exists).
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify.
  - After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST NOT run a second in-browser iterate loop.
  - The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.

## GOAL

An open-universe automated run evaluates several seed configs in a cheap **SCREEN** stage (no walk-forward, cheapest model, no insights) and runs the full expensive pipeline (walk-forward + the requested/stronger model + insights) only on the top-k **PROMOTE**d survivors (k < number screened) — visibly staged in the existing session activity feed — while the robust best, the hard budget, and the unchanged pinned path all still hold.

## BACKGROUND

13/16 journeys pass; the only remaining work is the Optimizer's efficiency/learning layer (J-14, J-15, J-16). The iter-3 evaluator and dev handoff both recommend iter-4 = **J-14** (staged SCREEN→PROMOTE) at **full** depth, carrying the tracked **B1** fix. Today every open-universe seed config runs the *full* pipeline — `wfv_enabled=True` (`auto_session.py:810`) and `req.model` for every config — so there is no cheap-first routing; J-14 introduces the SCREEN→PROMOTE split so expensive walk-forward + the stronger model touch only promoted survivors. This is a structural change to the open-universe loop that crosses the cost-tracker, the subprocess seam, the robust selector, and the activity feed, and it carries a fix with a documented regression trap touching J-07–J-11 — hence **full** depth (full 11-step pipeline).

**Carried B1 fix (from iter-3 audit + evaluator recommendation).** Tighten J-13's "within one-call tolerance": after the post-`generate` `_drain_usage` (`auto_session.py:792`), skip the subsequent `insights` call (still record/write the iteration) **only** when `tracker.would_exceed() in {"ai-tokens","usd","wall-clock"}`. **NEVER** skip on the `"max-configs"` sentinel.

**iter-3 lesson (Applies to: any iter touching the `auto_session.py` budget/`would_exceed` loop or the post-`generate`→`insights` sequencing — this is exactly that iter).** `_build_cost_tracker` sets the configs cap **== `max_iter`** on the *pinned* path (`auto_session.py:519`, the `default_cfg = hard_cfg = max_cfg = max_iter` branch). So on the **final pinned iteration** `tracker.start_config()` makes `configs_run == max_configs` and `would_exceed()` returns `"max-configs"`. A naive "skip insights whenever `would_exceed()` is truthy" would silently suppress the **final pinned iteration's insights**, breaking the pinned prompt-refinement chain (`prev_summary` / `prev_suggestion_titles` / `next_prompt`) and J-04 insights rendering — a J-07–J-11 regression that **no current test catches** (`test_pinned_path_unchanged_by_open_universe_addition` asserts `gen_calls` only, not `insight_calls`). The fix MUST gate on the spend-cap set only, and MUST ship with the `insight_calls`-on-final-pinned-iteration regression assertion.

**iter-2 lesson (Applies to: any iter touching the headless loop / asserting event-loop non-blocking — this iter adds a new SCREEN backtest path).** "Cheap" SCREEN is cheap in *LLM tokens* (cheapest model, no insights) and *engine work* (no walk-forward) — it is **NOT** cheap in CPU: the RestrictedPython backtest is GIL-holding CPU work whether `wfv_enabled` is True or False. SCREEN backtests MUST still flow through the existing `multiprocessing` subprocess executor seam; running them in-process "because they're cheap" would re-introduce the iter-2 event-loop-starvation anti-goal. Guard deterministically (`child_pid != os.getpid()`), never a timing bound.

## IN SCOPE

### Backend

- [ ] Introduce a two-stage open-universe controller in `auto_session.py`:
  - **SCREEN stage:** evaluate several seed-universe configs cheaply — `wfv_enabled=False`, generation with the **cheapest** model (lowest `shared/model_catalog.MODEL_PRICING` per-token cost, resolved from the catalog — not a hardcoded literal), and **no insights call**. Append a distinct `SCREEN` activity entry per screened config (symbol/timeframe + cheap screen metric).
  - **Rank + PROMOTE:** rank screened candidates by a cheap in-sample proxy (e.g. in-sample Sharpe / return — explicitly NOT the robust/WFE objective, which requires WF that SCREEN deliberately did not run). Promote only the **top-k** with **k < number screened** and k small. Append a distinct `PROMOTE` activity entry per promoted config.
  - **PROMOTE stage:** for each promoted config run the **full** pipeline — `wfv_enabled=True`, the **requested/stronger** model (`req.model`), and the insights call — **reusing the SCREEN candidate's already-generated strategy (by code hash) and the warm OHLCV Parquet cache** (no re-generation, no re-fetch — dedup anti-goal). The stronger model appears only here (in the promoted insights/refinement call).
- [ ] **Final best** is still chosen by `select_best`/`robust_score` over the **promoted** (walk-forward-bearing) iterations only — the cheap screen proxy MUST NOT leak into best-selection (J-09/J-16 robust-best invariant preserved; screened-only candidates that never got WF are not eligible to be "best").
- [ ] **Carried B1 fix:** in the stage(s) that call insights (PROMOTE + the pinned path), after the post-`generate` `_drain_usage`, skip the insights call (still build/write the iteration node + record activity) only when `tracker.would_exceed() in {"ai-tokens","usd","wall-clock"}`; never on `"max-configs"`. Document the sentinel distinction inline.
- [ ] **Hard budget unchanged across both stages (J-13):** the round-top `tracker.would_exceed()` check gates the start of **every** SCREEN candidate and **every** PROMOTE candidate; on any hard cap the run reaches the existing `budget-exhausted` terminal with **no further** screen/promote config appended. SCREEN and PROMOTE LLM calls feed the same `record_usage` path (real captured tokens). Define and **document inline** the `max_configs` semantics under staging (what counts as a "config" — screened vs promoted vs total) and update the J-12/J-13 tests **deliberately to the new staged semantics, not loosened to pass**; the "no one more config/round past the cap" + `budget-exhausted` + `spend==caps` invariants MUST still hold.
- [ ] SCREEN backtests run through the **same subprocess executor seam** as PROMOTE backtests (iter-2 lesson) — no in-process CPU regression.
- [ ] **Pinned path byte-unchanged behaviourally:** SCREEN/PROMOTE is open-universe-only. A pinned request still runs exactly one config per iteration with the prompt-refinement chain and the full pipeline every iteration (J-07–J-11 unchanged); no SCREEN/PROMOTE activity entries on the pinned path.

### Frontend

- [ ] None expected — the session activity feed already renders arbitrary activity entries (iter-2/iter-3 rendered "Exploring config N"). **If and only if** the existing renderer truncates/flattens entries so an operator cannot distinguish the SCREEN vs PROMOTE staging, a *minimal additive* presentation tweak (preserve the stage prefix; no new component) is in-scope. Do not add frontend not required by this acceptance.

### New user-facing capability

A headless open-universe run now spends cheaply first: the user sees, in the existing session activity feed, several configs screened cheaply and only a small top-k promoted to full walk-forward + the stronger model + insights — the platform spends expensive budget only on survivors.

### New information displayed

`SCREEN` activity entries (several cheap candidates, with the screen metric) and `PROMOTE` activity entries (only the top-k, k < screened) in the existing session activity panel; promoted iterations carry walk-forward data and the stronger model, screened-only ones do not.

### New user actions

None — same `POST /api/auto-sessions` open-universe trigger (no `symbol`/`timeframe`, `objective:"robust"`, small budget) and the same UI session/Auto-Run controls. The staging is automatic.

### UI surface changes

No new surface. The existing session activity feed now shows the SCREEN→PROMOTE staging.

### Product surface delta

Open-universe search becomes cost-efficient and auditable: expensive walk-forward and the strongest model are demonstrably reserved for screened survivors, visible to the operator without new UI.

## OUT OF SCOPE

- **J-15** (global-history warm start, cross-run planner, prompt-cached history, `history_scope` *learning*) — next iteration. `history_scope` stays accept-and-persist only; no cross-run mining/mutation.
- **J-16** (deep overfit-gating stress demonstration / leaderboard) — later iteration. The robust-best invariant is *preserved* here but the J-16 demonstration is not built.
- Any change to `shared/contracts.py`, `sandbox.py`, the backtest engine/fills/metrics, or the next-bar/determinism logic.
- Any new datastore/queue/scheduler/vector-store; any new external dependency or pricing API.
- A cross-config planner/bandit/surrogate for screening order (screening order stays the deterministic bounded seed enumeration — that learning is J-15).
- Multi-objective/Pareto selection (single robust scalar only).
- The legacy in-browser iterate loop must remain deleted (no second frontend loop reintroduced).

## DEFINITION OF DONE

- [ ] **J-14** passes via browser-qa: an open-universe run shows ≥3 `SCREEN` entries and exactly k `PROMOTE` entries with k < number screened in the session activity feed; walk-forward data and the stronger model appear only on promoted iterations; the run reaches a terminal state within the tiny budget.
- [ ] Required-still-passing journeys J-01–J-13 remain green (J-02 & J-08 re-verified **live** per the iter-0/iter-1 lessons; J-07–J-11 pinned path proven unchanged; J-12 open-universe ≥2 distinct configs + J-13 hard-budget invariants re-derived under the new staged semantics).
- [ ] No anti-goal violation introduced (all "Anti-goal reminders" above hold at source-diff + test level; `git diff HEAD -- shared/contracts.py apps/backend/backend/sandbox.py` is empty; no new infra imports).
- [ ] Unit/integration tests pass; the only tolerated pre-existing failure remains `test_directions_cache.py::test_write_and_read_full_round_trip` (baseline-documented, out of scope) — zero new regressions.
- [ ] Dev handoff written at `docs/handoffs/goal-auto-money-printer-iter-4-dev.md`.

## TESTING REQUIREMENTS

- **Browser (browser-qa-agent):**
  - **J-14 (primary):** trigger an open-universe run — `POST /api/auto-sessions` with **no** `symbol`/`timeframe`, `objective:"robust"`, tiny budget (short date window, cheap model, k small, no/lenient targets so it ends `budget-exhausted`). After a terminal state, open the session and inspect the activity feed: assert ≥3 `SCREEN` entries, exactly k `PROMOTE` entries with k < screened, and that promoted iterations have walk-forward results / the stronger model while screened-only ones do not. Capture a screenshot of the staged activity feed.
  - **Regression (re-verify live, not carried):** J-02 (prior run's *trades table* + right analysis panel re-binds, per iter-0 lesson), J-08 (live status, no stale terminal under switching, per iter-1 lesson), J-12 (open-universe still explores ≥2 distinct seed configs and is UI-indistinguishable), J-13 (`budget-exhausted` + visible/durable spend still correct under staging).
- **Unit/integration (`cd apps/backend && .venv/bin/python -m pytest`):**
  - New: SCREEN runs `wfv_enabled=False` + cheapest model + **no** `generate_insights` call for screened-only configs; PROMOTE runs `wfv_enabled=True` + `req.model` + insights and **reuses** the screened strategy (assert no second `generate_strategy` / same code hash, no re-fetch); top-k with **k < screened**; final `bestIterationId` is a **promoted** id chosen by the robust objective (a higher raw-return screened-only or WFE-failing candidate is not best).
  - New: SCREEN backtests flow through the subprocess seam — assert **deterministically** `child_pid != os.getpid()` for a screened config (extend/parallel `test_open_universe_multi_config_runs_in_subprocess_distinct_pids`), never a timing bound (iter-2 lesson).
  - **B1 regression guard (mandatory, per iter-3 lesson):** add an `insight_calls`-on-final-pinned-iteration assertion to `test_pinned_path_unchanged_by_open_universe_addition` (`tests/test_auto_session.py:1288`) — e.g. `assert pipe.insight_calls == 3` for the 3-iteration pinned run — written so it goes **RED** if the B1 skip is naively gated on a truthy `would_exceed()` (which returns `"max-configs"` on the final pinned iteration) and **GREEN** with the correct spend-cap-only gate. Add a positive test that a true spend cap (`ai-tokens`/`usd`/`wall-clock`) hit between generate and insights **does** skip that one insights call while still writing the iteration.
  - Consciously update (do not loosen to pass) the J-12/J-13 tests whose activity-content/“config” assertions change under staging: `test_open_universe_runs_multiple_distinct_configs`, `test_max_configs_cap_stops_open_universe_no_post_cap_config`, `test_open_universe_best_is_robust_not_raw_return`, `test_hard_token_budget_exhausted_real_usage_and_durable_spend` — their invariants (≥2 distinct seed configs, no-config-past-cap, `budget-exhausted`, exact-real-spend, robust-not-raw best) MUST still be asserted in the new staged form.
- **Error cases:** partial pin still `422` (one of symbol/timeframe without the other); bad `objective` still `422`; a SCREEN-stage generate validation failure or backtest failure must not abort the loop (recorded, loop continues to a terminal state); a hard cap tripped mid-SCREEN or mid-PROMOTE yields `budget-exhausted` with no further config appended; no secrets in any new `SCREEN`/`PROMOTE` activity entry or persisted artifact.

## NOTES

- **Tiny-budget reconciliation (pre-empt a false QA/evaluator flag):** `docs/goal.md`'s "≤ 2 screen iterations / short date range / cheapest model / lenient targets" mandate is about keeping the *expensive* path tiny. SCREEN is cheap **by construction** (no walk-forward, cheapest model, no insights, short shared window, warm Parquet cache reused across seed configs), so screening *several* seed configs while promoting only a small top-k is consistent with the fast-and-cheap mandate — that is the entire point of cheap-first staging. Keep the date window short, k small, model cheap, targets lenient/absent so the QA run ends `budget-exhausted` quickly.
- **Robust-best invariant is load-bearing here:** screened-only candidates have no walk-forward, so they are gate-failing under `robust_score`; ensure best-selection draws from promoted (WF-bearing) iterations and reuses `select_best`/`robust_score` unchanged — do not invent a screen-aware best path that could regress J-09/J-16 semantics.
- **Reconciled-UI-test-headline caution (iter-1 lesson, applies to the evaluator):** if `ui-test-results.md` is QA-FAIL→fix→reconciled, do not trust the top headline — cross-check the post-fix source diff and the QA MODE-2 (full-mode) re-verification, especially for the B1 gate and the SCREEN/PROMOTE activity assertions.
- **Source anchors for the developer:** seed universe `auto_session.py:82`; `_config_plan` `:476`; `_build_cost_tracker` pinned `max_cfg==max_iter` branch `:519`; main loop round-top `would_exceed()` `:728`; `tracker.start_config()` `:756`; post-`generate` `_drain_usage` `:792`; `generate_insights` `:833-850`; subprocess-pid guard pattern `test_auto_session.py:1142`; pinned regression test missing the `insight_calls` assertion `test_auto_session.py:1288`.
- Evaluator recommendation drove scope: iter-3 `eval.md` "Next-Step Recommendation" + the iter-3 lessons-learned entry (B1 max-configs sentinel trap) are implemented here.
