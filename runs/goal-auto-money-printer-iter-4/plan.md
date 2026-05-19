# goal-auto-money-printer-iter-4 Execution Plan

**Optimizer efficiency layer — single slice: J-14 (staged SCREEN→PROMOTE cheap-first
routing) + the carried iter-3 B1 fix.** Depth=full. Builds directly on iter-3's
closed J-12 bounded-seed enumerator + J-13 immutable `CostTracker`; J-15/J-16 remain
OUT. Aligned with `docs/goal.md` Key Capability #11 ("staged cheap-first evaluation,
model routing … under a hard AI-token/cost budget") and J-14. No scope drift.

## What to Build

**Backend (`apps/backend/backend/auto_session.py` — dominant surface)**

- **Two-stage open-universe controller** (open-universe path ONLY; pinned path
  byte-unchanged behaviourally):
  - **SCREEN stage:** evaluate several seed-universe configs cheaply — `wfv_enabled=False`,
    generation with the **cheapest** model resolved from `shared/model_catalog.MODEL_PRICING`
    (lowest per-token cost — *resolved from the catalog, not a hardcoded literal*), and
    **no `generate_insights` call**. Append a distinct `SCREEN` activity entry per screened
    config (symbol/timeframe + the cheap screen metric).
  - **Rank + PROMOTE:** rank screened candidates by a cheap **in-sample** proxy (in-sample
    Sharpe/return — explicitly NOT `robust_score`/WFE, which needs the WF that SCREEN
    deliberately skipped). Promote only the **top-k** with **k < number screened** and k
    small. Append a distinct `PROMOTE` activity entry per promoted config.
  - **PROMOTE stage:** for each promoted config run the **full** pipeline —
    `wfv_enabled=True`, the **requested/stronger** model (`req.model`), and the insights
    call — **reusing the SCREEN candidate's already-generated strategy (same code hash)
    and the warm OHLCV Parquet cache** (no re-generation, no re-fetch). The stronger model
    appears ONLY here.
- **Final best** still chosen by `select_best`/`robust_score` over the **promoted**
  (walk-forward-bearing) iterations only — the cheap screen proxy MUST NOT leak into
  best-selection; screened-only candidates (no WF) are not eligible to be best
  (J-09/J-16 robust-best invariant preserved; reuse `select_best`/`robust_score`
  unchanged — no screen-aware best path).
- **Carried B1 fix:** in the stage(s) that call insights (PROMOTE + the pinned path),
  after the post-`generate` `_drain_usage`, skip the insights call (still build/write
  the iteration node + record activity) **only** when
  `tracker.would_exceed() in {"ai-tokens","usd","wall-clock"}`; **never** on
  `"max-configs"`. Document the sentinel distinction inline (the pinned-path
  `max_cfg==max_iter` trap from `auto_session.py:519`).
- **Hard budget unchanged across both stages (J-13):** the round-top
  `tracker.would_exceed()` check gates the start of **every** SCREEN candidate and
  **every** PROMOTE candidate; on any hard cap → existing `budget-exhausted` terminal
  with **no further** screen/promote config appended. SCREEN and PROMOTE LLM calls feed
  the same `record_usage`/real-captured-token path. Define and **document inline** the
  `max_configs` semantics under staging (what counts as a "config": screened vs promoted
  vs total) and update J-12/J-13 tests **deliberately to the new staged semantics, not
  loosened to pass** — the no-config-past-cap + `budget-exhausted` + `spend==caps`
  invariants MUST still hold.
- **SCREEN backtests run through the same `_subprocess_backtest_executor` seam** as
  PROMOTE (iter-2 lesson: cheap in LLM/engine ≠ cheap in CPU; never in-process).
  Guard deterministically (`child_pid != os.getpid()`), never a timing bound.
- **Pinned path:** still exactly one config/iteration with the prompt-refinement chain
  and the full pipeline every iteration; **no** SCREEN/PROMOTE activity entries.

**Frontend (`apps/frontend`) — conditional, minimal-only**

- None expected: the session activity feed already renders arbitrary activity entries
  (iter-2/3 rendered "Exploring config N"). **Only if** the existing renderer
  truncates/flattens entries so an operator cannot distinguish SCREEN vs PROMOTE
  staging → a *minimal additive* tweak preserving the stage prefix (no new component,
  no redesign). Verify-first; do not add frontend not required by acceptance.

## Agents Required

- developer: **yes** — backend two-stage controller + carried B1 fix + staged
  `max_configs` semantics + staged-form J-12/J-13 test updates + new SCREEN/PROMOTE/B1
  tests; frontend only the conditional minimal stage-prefix tweak if (and only if) the
  existing feed flattens it. Single TDD pass; backend dominant.
- Full 11-step pipeline (UI impact + UI test design + browser-qa + ux-regression +
  audit + closure) — depth=full: structural change crossing the cost-tracker,
  subprocess seam, robust selector, and activity feed, carrying a fix with a documented
  J-07–J-11 regression trap.

## Frontend Present
yes

> **Flagged spec/framework reconciliation (orchestrator must surface, not silently
> resolve):** the spec's machine metadata line reads `Frontend Present: no (code)`,
> but the *same line* states "browser-qa MUST verify it renders", and the spec's
> DEFINITION OF DONE + TESTING REQUIREMENTS **mandate** browser-qa for J-14 (≥3 SCREEN
> / k PROMOTE entries in the activity feed) and **live** regression of
> J-02/J-08/J-12/J-13. The `Frontend Present:` line in this plan is machine-read by
> `qa-phase.sh` to decide whether browser checks run; `no` would **skip the very
> browser QA the spec requires**. Per the orchestrator rule ("if the phase adds any
> user-facing data, Frontend Present MUST be yes") and the iter-1/2/3 precedent (all
> `yes` for the same additive-activity-feed situation), this is **`yes`**. "no (code)"
> means *no new frontend code is expected* — not that browser QA is skipped. The
> developer is NOT required to write frontend code (see conditional clause above);
> browser-qa IS required.

## Files to Create/Modify

- `apps/backend/backend/auto_session.py` — two-stage SCREEN→PROMOTE open-universe
  controller (cheapest-model SCREEN with `wfv_enabled=False`, no insights; in-sample
  rank; top-k<screened PROMOTE reusing the screened strategy by code hash + warm cache,
  `wfv_enabled=True` + `req.model` + insights); carried B1 spend-cap-only insights gate
  with inline sentinel doc; staged `max_configs` semantics documented inline; SCREEN
  via the subprocess seam. Pinned path untouched behaviourally.
- `apps/backend/shared/model_catalog.py` — **read-only reference** to resolve the
  cheapest model from `MODEL_PRICING` (no pricing change unless a helper is genuinely
  absent; do NOT touch `shared/contracts.py`).
- `apps/backend/tests/test_auto_session.py` — **extend, do not duplicate**:
  - New: SCREEN runs `wfv_enabled=False` + cheapest model + **no** `generate_insights`
    for screened-only configs; PROMOTE runs `wfv_enabled=True` + `req.model` + insights
    and **reuses** the screened strategy (assert no 2nd `generate_strategy`, same code
    hash, no re-fetch); top-k with **k < screened**; final `bestIterationId` is a
    **promoted** id by the robust objective (higher-raw-return screened-only / WFE-fail
    is NOT best).
  - New: SCREEN backtest flows through the subprocess seam — deterministic
    `child_pid != os.getpid()` (extend/parallel
    `test_open_universe_multi_config_runs_in_subprocess_distinct_pids`, ref
    `test_auto_session.py:1142`), never a timing bound.
  - **B1 regression guard (mandatory):** add an `insight_calls`-on-final-pinned-
    iteration assertion to `test_pinned_path_unchanged_by_open_universe_addition`
    (`test_auto_session.py:1288`) — e.g. `assert pipe.insight_calls == 3` for a
    3-iteration pinned run — RED if B1 is naively gated on a truthy `would_exceed()`
    (returns `"max-configs"` on the final pinned iteration), GREEN with the
    spend-cap-only gate. Plus a positive test: a true `ai-tokens`/`usd`/`wall-clock`
    cap hit between `generate` and `insights` **does** skip that one insights call
    while still writing the iteration.
  - **Consciously update (NOT loosen):** `test_open_universe_runs_multiple_distinct_configs`,
    `test_max_configs_cap_stops_open_universe_no_post_cap_config`,
    `test_open_universe_best_is_robust_not_raw_return`,
    `test_hard_token_budget_exhausted_real_usage_and_durable_spend` — re-assert their
    invariants (≥2 distinct seed configs, no-config-past-cap, `budget-exhausted`,
    exact-real-spend, robust-not-raw best) in the new staged form.
- `apps/frontend/src/components/SessionContainer.tsx` — **only if** the activity-feed
  renderer flattens the SCREEN/PROMOTE prefix (verify first); minimal additive prefix
  preservation, no new component. iter-2 live-poll `try/finally` re-arm + J-02
  heavy-detail merge precedence MUST stay byte-unchanged.

## UI Evolution
- New user-facing capability: a headless open-universe run now spends cheaply first —
  the operator sees, in the **existing** session activity feed, several configs
  screened cheaply and only a small top-k promoted to full walk-forward + the stronger
  model + insights (expensive budget spent only on survivors).
- New information displayed: `SCREEN` activity entries (several cheap candidates + the
  screen metric) and `PROMOTE` activity entries (only top-k, k < screened) in the
  existing session activity panel; promoted iterations carry walk-forward data + the
  stronger model, screened-only ones do not.
- New user actions: none — same `POST /api/auto-sessions` open-universe trigger and
  the same UI session/Auto-Run controls. Staging is automatic.
- UI surface changes: no new surface — the existing session activity feed now shows
  the SCREEN→PROMOTE staging.
- Navigation changes: none.

## Visual Requirements
- Component patterns: reuse the existing session activity feed list rendering and
  existing `BestBadge`; no new component. If a tweak is needed it preserves the
  `SCREEN`/`PROMOTE` text prefix only.
- Layout: unchanged two-panel session view; no new layout region.
- Key visual effects: match the existing dense/dark/data-forward activity feed; no
  new effects; SCREEN vs PROMOTE distinguishable by entry text.
- States to handle: running (SCREEN entries accumulating, then PROMOTE), terminal
  `budget-exhausted` within the tiny budget; legacy/pinned sessions show NO
  SCREEN/PROMOTE entries (graceful — feed unchanged for old/pinned runs).

## Key Test Scenarios
- **J-14 (browser, primary):** `POST /api/auto-sessions` with **no** symbol/timeframe,
  `objective:"robust"`, tiny budget (short window, cheap model, k small, lenient/absent
  targets so it ends `budget-exhausted` fast). After a terminal state, open the session
  and inspect the activity feed: assert **≥3 `SCREEN` entries**, **exactly k `PROMOTE`
  entries with k < screened**, promoted iterations have walk-forward results / the
  stronger model while screened-only ones do not. Screenshot the staged feed.
- **Regression (browser, re-verify live — NOT carried headline):** J-02 (prior run's
  trades table + right analysis panel re-binds — iter-0 lesson), J-08 (live status, no
  stale terminal under session switching — iter-1 lesson), J-12 (open-universe still
  explores ≥2 distinct seed configs, UI-indistinguishable), J-13 (`budget-exhausted` +
  visible/durable spend correct under staging).
- **Unit/integration (`cd apps/backend && .venv/bin/python -m pytest`; assert exact
  values, no skip/xfail):** all new + updated tests above GREEN. Baseline to preserve:
  the ONLY tolerated failure remains the pre-existing out-of-scope
  `test_directions_cache.py::test_write_and_read_full_round_trip` (iter-3 finished
  **183 passed / 1 failed**) — **zero new regressions**. Frontend `npm run build`
  EXIT 0 (only if a frontend file is touched).
- **Error cases:** partial pin still `422` (one of symbol/timeframe without the other);
  bad `objective` still `422`; a SCREEN-stage generate-validation or backtest failure
  does NOT abort the loop (recorded, loop continues to a terminal state); a hard cap
  tripped mid-SCREEN or mid-PROMOTE → `budget-exhausted`, no further config appended;
  **no secrets** in any new `SCREEN`/`PROMOTE` activity entry or persisted artifact.

## Out of Scope (exclude — flagged to prevent scope creep)
- **J-15** — global-history warm start / cross-run planner / prompt-cached history /
  `history_scope` *learning*. `history_scope` stays accept-and-persist only; no
  cross-run mining/mutation; screening order stays the deterministic bounded seed
  enumeration (no bandit/surrogate/LLM planner for screen order).
- **J-16** — deep overfit-gating *demonstration* / leaderboard. Robust-best invariant
  is *preserved* here; the J-16 demonstration is not built.
- Any change to `shared/contracts.py`, `apps/backend/backend/sandbox.py`, the backtest
  engine/fills/metrics, or the next-bar/determinism logic
  (`git diff HEAD -- shared/contracts.py apps/backend/backend/sandbox.py` MUST be empty).
- Any new datastore/queue/scheduler/broker/vector-store; any new external dependency or
  pricing API; any session-store schema fork (reuse the existing file store).
- Multi-objective/Pareto selection (single robust scalar only). Re-implementing/
  re-tuning `select_best`/`robust_score`.
- Reintroducing any in-browser iterate loop (legacy loop stays deleted).
- Any frontend change beyond the conditional minimal stage-prefix tweak.

## Assumptions (documented per token policy — not blocking)
- "Cheapest model" = lowest per-token cost in `shared/model_catalog.MODEL_PRICING`,
  resolved at runtime from the catalog (developer's exact lookup helper choice).
- k (top-k promoted) is small with k < number screened, and the seed-universe screen
  set is ≥3 configs so J-14's "≥3 SCREEN entries" holds within the tiny budget;
  exact k and screen-set size are the developer's within these constraints.
- The in-sample rank proxy (in-sample Sharpe vs return) is the developer's choice; it
  MUST NOT be `robust_score`/WFE (SCREEN ran no walk-forward).
- `FakePipeline` in `test_auto_session.py` is extended so SCREEN (no-insights,
  cheap-model) vs PROMOTE (insights, `req.model`, WF) is exercised deterministically
  without live LLM calls (tiny-budget mandate); the B1 RED/GREEN behaviour is proven.
- Tiny-budget reconciliation: screening *several* seed configs while promoting only a
  small top-k is consistent with the goal's fast-and-cheap mandate — SCREEN is cheap
  by construction (no WF, cheapest model, no insights, short shared window, warm
  Parquet cache). QA keeps window short / k small / model cheap / targets lenient so
  the run ends `budget-exhausted` quickly.
- Definition of Done also requires: dev handoff at
  `docs/handoffs/goal-auto-money-printer-iter-4-dev.md`; all 6 UI visibility artifacts;
  phase-closure gate passes.
- **Reconciled-UI-test-headline caution (iter-1 lesson, for the evaluator):** if
  `ui-test-results.md` is QA-FAIL→fix→reconciled, do NOT trust the top headline —
  cross-check the post-fix source diff and the QA full-mode re-verification,
  especially the B1 gate and the SCREEN/PROMOTE activity assertions.
