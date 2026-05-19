# goal-auto-money-printer-iter-4 Audit Report

**Date:** 2026-05-19
**Auditor:** Hard audit pass — skeptical, evidence-based

---

## 1. Executive Verdict

**Verdict:** PASS_WITH_GAPS

The phase goal — staged **SCREEN→PROMOTE** cheap-first model/walk-forward routing
for the open-universe run (**J-14**) plus the carried iter-3 **B1** spend-cap
insights fix — is fully and correctly achieved. The implementation was verified by
reading the actual source (not handoff summaries): the two-stage controller, the
catalog-resolved cheapest model, the in-sample rank, the code-hash strategy reuse,
the promoted-only robust-best invariant, the spend-caps-only B1 gate, the staged
`max_configs` semantics, and the byte-unchanged pinned path are all present and
correct. The test suite was re-run independently: **188 passed / 1 failed**, the
single failure being the pre-existing, out-of-scope, baseline-documented
`test_directions_cache.py::test_write_and_read_full_round_trip` (+5 new, **zero new
regressions**). The sole gap is non-implementation: two UI-test-design artifacts
(`ui-test-plan`, `what-to-click`) are auto-generated stubs from a transient
`ui-test-design-phase.sh` CLI exit-1; their substance is independently verified
in-browser and they are owned by the downstream phase-closure-auditor gate.

---

## 2. Findings

### Backend Findings

**B1 — OBSERVATION (verified-correct): Two-stage SCREEN→PROMOTE controller is spec-faithful**
`_run_staged_open_universe` (`apps/backend/backend/auto_session.py:1044-1270`):
- SCREEN evaluates `configs[:_SCREEN_SET_SIZE]` (`:1089`, =4) with
  `gen_model=cheap_model` / `wfv_enabled=False` / `want_insights=False` /
  `stage="screen"` (`:1118-1126`); distinct `SCREEN config N` + `SCREEN N done …
  (cheap screen — no walk-forward)` activity entries (`:1112-1146`).
- `tracker.start_config()` is **not** called during SCREEN; it is called once per
  PROMOTE (`:1191`) — the staged `max_configs`=PROMOTE semantics, documented inline
  in the docstring (`:1069-1081`).
- Rank is `sorted(screened, key=lambda s: (s.proxy, s.total_return), reverse=True)`
  where `proxy = float(res.result.sharpe_ratio)` from the no-WF backtest (`:1132`,
  `:1168-1169`) — in-sample Sharpe, **not** `robust_score`/WFE. Correct.
- `k = max(0, min(_PROMOTE_TOP_K, len(ranked) - 1, max_iter))` (`:1172`) — the
  `len(ranked) - 1` term structurally guarantees **k < number screened**.
- PROMOTE reuses `cand.gen` via `reuse_gen=cand.gen` (`:1217`) →
  `_evaluate_one` takes the `gen = reuse_gen` branch with **no second
  `generate_strategy`** (`:769-774`); same `(symbol,timeframe,window)` ⇒ warm
  single-file Parquet cache, no re-fetch. Dedup anti-goal honoured structurally.
- A hard cap / stop during SCREEN returns before any PROMOTE
  (`:1162-1163`) — "no config past the cap" holds across the stage boundary.

**B2 — OBSERVATION (verified-correct): Robust-best invariant preserved structurally**
Only PROMOTE appends to `completed` (`auto_session.py:1225`); SCREEN never does.
`best_id = select_best(completed)` (`:1248`) and the terminal
`select_best(completed, …)` (`:1344-1347`) therefore draw exclusively from
walk-forward-bearing promoted iterations. `select_best`/`robust_score` are reused
unchanged (no screen-aware best path). The cheap screen proxy cannot leak into
best-selection. J-09/J-16 invariant intact.

**B3 — OBSERVATION (verified-correct): Carried B1 fix gates on spend-caps only**
`_SPEND_CAPS = frozenset({"ai-tokens", "usd", "wall-clock"})`
(`auto_session.py:100`); `_should_skip_insights` returns
`tracker.would_exceed() in _SPEND_CAPS` (`:103-107`), explicitly excluding the
`"max-configs"` sentinel. The pinned-path `max_cfg == max_iter` trap is documented
inline at `:87-99` and at the gate site `:834-841`. On the final pinned iteration
`would_exceed()=="max-configs"` does **not** skip insights. Verified by reading the
gate in `_evaluate_one` (`:833-868`) — insights still runs, the iteration node is
still built/written (`:886-906`) when a true spend cap *does* skip.

**B4 — OBSERVATION (verified-correct): SCREEN flows through the subprocess seam**
SCREEN and PROMOTE share `_evaluate_one`, whose backtest goes through
`_perform_backtest(... backtest_executor=backtest_executor ...)` inside the
semaphore (`auto_session.py:812-820`). No in-process branch for "cheap" SCREEN.
iter-2 CPU anti-goal not reintroduced.

**B5 — OBSERVATION (verified-correct): Pinned path behaviourally byte-unchanged**
`_run_pinned` (`auto_session.py:924-1041`): one config/iteration, full pipeline
(`wfv_enabled=True, want_insights=True, stage=None`, `:981`), prompt-refinement
chain (`prev_script_code`/`prev_summary`/`prev_suggestion_titles`/`next_prompt`,
`:1018-1024`), unchanged activity strings, no `stage` key (`_build_node` omits it
when `stage is None`, `:1417-1418`), no SCREEN/PROMOTE entries. Only added
behaviour is the B1 gate (a no-op unless a true spend cap hits between generate
and insights).

**B6 — OBSERVATION (verified-correct): `cheapest_model()` catalog-resolved, not a literal**
`shared/model_catalog.py:87-100`:
`min(MODEL_PRICING, key=lambda m: (MODEL_PRICING[m][0]+MODEL_PRICING[m][1], m))`
— combined per-token price, deterministic id tie-break, resolved at call time. No
pricing change to the table. Anti-goal "resolved from the catalog, not a hardcoded
literal" satisfied.

**B7 — OBSERVATION (documented limitation, not a defect): `modelUsed` on a promoted node is `req.model`**
`_evaluate_one` sets `model_used = req.model` for `stage=="promote"`
(`auto_session.py:876-882`) even though the strategy *code* was generated by the
cheap SCREEN model and reused verbatim. This is intentional and documented inline
(`:877-881`): it reflects the promote stage's representative (expensive) model.
Not misleading given the inline rationale; recorded as a known interpretation note.

### Frontend Findings

**F1 — OBSERVATION (verified-correct): No frontend code change, correctly justified**
`git diff HEAD -- apps/frontend` is empty (verified). The frontend handoff's
verify-first claim was spot-checked against the spec's conditional clause: the
staged controller emits standard `auto-run`/`complete`/`insights` entries with the
`SCREEN`/`PROMOTE` text prefix, which the existing renderer shows verbatim. The
additive `stage` field on open-universe nodes is inert extra JSON the typed
frontend never reads — no schema fork, no runtime type error. Spec-compliant
("Frontend: None expected").

**F2 — GAP (documented, non-blocking, spec-sanctioned): model-routing split not browser-visible**
Per the ux-regression review, `modelUsed` and the `stage` field are not rendered
as structured UI elements; an operator infers "expensive work reserved for
survivors" from the SCREEN/PROMOTE text + walk-forward presence/absence, not from a
model chip. The spec explicitly scopes this under "Not Visible Yet" / "no new
component", and the primary J-14 acceptance does not depend on it. Acceptable for
this iteration; a candidate surface for a future (J-15/J-16/UI) iteration. Not a
phase-goal compromise.

### Test Findings

**T1 — OBSERVATION (verified-correct): B1 regression guard is genuinely RED-under-naive-gate**
`test_pinned_path_unchanged_by_open_universe_addition`
(`tests/test_auto_session.py:1430-1459`) asserts `pipe.insight_calls == 3` for a
3-iteration pinned run. Traced by hand: pinned `max_configs == max_iter == 3`; on
iteration 3 `start_config()` makes `configs_run == 3` so `would_exceed()` returns
`"max-configs"`. A naive `if would_exceed():` gate would skip iteration 3's
insights (→ `insight_calls == 2`, RED); the shipped `would_exceed() in _SPEND_CAPS`
gate runs it (→ 3, GREEN). The mandated mutation guard is real, not cosmetic.

**T2 — OBSERVATION (verified-correct): positive B1 test proves skip-one-while-writing**
`test_b1_true_spend_cap_between_generate_and_insights_skips_one`
(`tests/test_auto_session.py:1462-1494`): a `max_ai_tokens=90` cap crossed by
generate's 100 drained tokens skips exactly that iteration's insights
(`insight_calls == 0`) while the iteration node is still written
(`status=="complete"`, `total_return==0.2`) and activity recorded; spend is the
exact generate-only `80+20`. Tight, exact-value.

**T3 — OBSERVATION (verified-correct): SCREEN/PROMOTE/staged-J-12/J-13 tests are tight, not loosened**
`test_screen_stage_cheap_model_no_wf_no_insights` (`:1497`),
`test_promote_stage_reuses_screened_strategy_full_pipeline` (`:1585`),
`test_open_universe_best_is_robust_not_raw_return` (`:1115`),
`test_max_configs_cap_stops_open_universe_no_post_cap_config` (`:1174`),
`test_hard_token_budget_exhausted_real_usage_and_durable_spend` (`:1209`),
`test_open_universe_multi_config_runs_in_subprocess_distinct_pids` (`:1273`) all
assert exact values (`gen_models == [cheap]*n`, `bt_wfv` slicing, exact
`aiTokens`/`usd`, `scriptId`/`scriptCode` reuse equality, deterministic
`int(pid) != os.getpid()`, best id pinned to a specific promoted node). No
`pytest.mark.skip`/`xfail` added (grep clean). J-12/J-13 invariants re-asserted in
staged form, strengthened (+79/−14 per QA), not relaxed to pass.

**T4 — GAP (non-implementation, downstream-owned): two UI-test-design artifacts are stubs**
`reports/phase-goal-auto-money-printer-iter-4-ui-test-plan.md` (15 lines) and
`…-what-to-click.md` (15 lines) are auto-generated stubs ("SKIPPED — agent did not
produce this artifact"; `ui-test-design-phase.sh` Claude CLI exited code 1). This
is a pipeline-tooling transient, **not** an implementation defect — the developer
did not author them. The substantive UI visibility they would document is
independently verified: QA browser TC-07–TC-12 (+6 screenshots), `ui-test-results.md`
(157 lines), `user-visible-changes.md` (118 lines), `ui-surface-map.md` (70 lines),
and the ux-regression review (UT-01–UT-10 PASS, evidence screenshots present).
Owned by the dedicated phase-closure-auditor (CLAUDE.md DoD #9), with the concrete
recovery already flagged in the QA report. Not fixed here: re-running a pipeline
orchestration script is the closure gate's explicit responsibility, not a surgical
source fix; fabricating the artifact content in the auditor would defeat the
framework's separation of concerns.

---

## 3. Domain Assessment

The core domain logic is correct. Cheap-first routing is real, not cosmetic:
SCREEN demonstrably runs the catalog-cheapest model with `wfv_enabled=False` and no
insights, while the expensive walk-forward + stronger `req.model` + insights are
reserved for the small top-k promoted survivors that reuse the screened strategy by
code hash with a warm Parquet cache. The robust-best invariant is preserved by
construction (best-selection draws only from promoted, walk-forward-bearing
iterations; `select_best`/`robust_score` untouched), so a higher-raw-return
screened-only or WFE-failing promoted candidate cannot become best — proven by
`test_open_universe_best_is_robust_not_raw_return`. The carried B1 fix correctly
distinguishes the `"max-configs"` sentinel (must NOT skip insights — the pinned
final-iteration trap) from true spend caps (skip the one in-flight insights call,
still write the iteration), with both a RED-under-naive-gate regression guard and a
positive cap-skip test. The hard budget holds across both stages with a
deliberately redefined-and-documented staged `max_configs` semantics, re-asserted
(not loosened) in the J-12/J-13 tests. Anti-goal source guards verified empty
(`shared/contracts.py`, `sandbox.py`, `pipeline.py`, `backtest/`), no new infra
imports, no frontend diff, no schema fork. The architecture remains local-first and
minimal; failure handling is explicit (failed screen/promote recorded, loop
continues to a terminal state); ambiguous data is surfaced honestly (the
`modelUsed` interpretation is documented inline, not hidden). Phase deliverables
match the spec's exact scope with no drift (J-15/J-16 untouched).

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| — | — | — | None. The implementation is correct as shipped; the only gap (T4) is a non-implementation, downstream-owned pipeline-tooling transient with a documented recovery path — outside the auditor's surgical-fix scope. |

---

## 5. Recommended Next Step

**Proceed.** The phase goal (J-14 staged SCREEN→PROMOTE + carried B1 fix) is
genuinely achieved with strong source-, unit-, live-API-, and browser-level
evidence; the system is materially stronger than before this iteration with zero
new regressions.

One non-blocking action item for the **phase-closure-auditor** (not the
developer): re-run
`./scripts/automation/ui-test-design-phase.sh goal-auto-money-printer-iter-4`
to regenerate the two stub artifacts (`ui-test-plan`, `what-to-click`) before
CLOSURE-PASS. This is the documented owner of UI-artifact completeness
(CLAUDE.md DoD #9); the implementation and its UI visibility are already fully
verified and require no further development work.

Suggested next iteration: **J-15** (global-history warm start / cross-run
prompt-cached history planner over the now-existing staged SCREEN seed-order
injection point), then **J-16** (deep overfit-gating demonstration / leaderboard —
its robust-best invariant is already preserved here).
