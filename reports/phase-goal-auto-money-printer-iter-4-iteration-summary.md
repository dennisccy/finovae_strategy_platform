# Iteration Summary — goal-auto-money-printer-iter-4

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-19
**Iteration:** 4

## Headline

Staged SCREEN→PROMOTE cheap-first screening for headless open-universe runs (J-14) + carried iter-3 B1 spend-cap fix.

## Direction

**Signal:** improving
**Why:** This iter implemented the two-stage SCREEN→PROMOTE controller plus the carried iter-3 B1 spend-cap insights gate in `auto_session.py`/`model_catalog.py`, moving J-14 failing→passing (verified live + browser QA 10/10 + audit source read). All 13 required-still-passing journeys (J-01–J-13) hold — J-02/J-08/J-12/J-13 re-verified live — with zero new regressions (suite 188p/1f; the 1 is the pre-existing out-of-scope `test_directions_cache`). The pipeline's CLOSURE-FAIL is a transient pipeline-tooling stub on two UI-test-design artifacts, not implementation; the goal-evaluator's CONTINUE verdict stands and J-15 is the next target.

**Trend (last 5 iters):**
- Newly passing this iter: J-14
- Newly passing in last 5 iters total: J-01, J-03, J-04, J-05, J-06 (iter-0 baseline); J-02, J-07, J-08, J-09 (iter-1); J-10, J-11 (iter-2); J-12, J-13 (iter-3); J-14 (iter-4)
- Regressions in last 5 iters: none
- Anti-goal violations in last 5 iters: none
- Iters with no journey state change: 0 of 5

**Latest evaluator reasoning:** The indivisible J-14 slice — staged SCREEN→PROMOTE cheap-first model/walk-forward routing for the open-universe run + the carried iter-3 B1 spend-cap insights fix — is genuinely implemented, not just summarized. J-14 moves failing → passing (verified live, in-browser, and by my own source read); all required-still-passing journeys J-01–J-13 hold. Zero anti-goal violations at source-diff + test level. The pipeline's CLOSURE-FAIL is an artifact-completeness gate trip on two stub UI-test-design files from a transient `ui-test-design-phase.sh` CLI exit-1 — not a journey regression, anti-goal violation, or implementation/quality failure; its substance is independently verified.

## What was done

- Cheap-first staged **SCREEN→PROMOTE** routing for headless open-universe runs (J-14): several seed configs are screened with the cheapest catalog model, no walk-forward, no insights; only a small top-k of survivors is promoted to the full expensive pipeline (walk-forward + the stronger requested model + insights), reusing the screened strategy by code hash and the warm Parquet cache.
- Visible SCREEN vs PROMOTE staging in the **existing** session activity feed — a row per screened config and per promoted config; promoted iterations carry walk-forward + the stronger model, screened-only ones do not. No new screen, page, or component.
- "Cheapest model" resolved at run time from the model price table (`shared/model_catalog.cheapest_model()`), not a hardcoded literal — tracks future price changes / new cheaper models.
- Carried iter-3 **B1** budget-accounting fix: a hard *spend* cap (AI tokens/USD/wall-clock) skips that config's insights call (iteration still recorded); the *number-of-configs* limit does NOT skip insights, so the pinned run's final iteration still gets its insights.
- Pinned (single-strategy) path byte-unchanged behaviourally; best-selection invariant preserved (best drawn only from promoted, walk-forward-bearing iterations; `select_best`/`robust_score` reused unchanged).
- Backend suite **188 passed / 1 failed** (only the pre-existing out-of-scope `test_directions_cache::test_write_and_read_full_round_trip`; +5 new, zero new regressions); anti-goal source guards (`contracts.py`/`sandbox.py`/`pipeline.py`/`backtest`) empty diff.
- Verified target journey **J-14** and regression journeys **J-02/J-08/J-12/J-13** pass browser QA (10/10 live-LLM tests PASS, 6 evidence screenshots). Review PASS, QA PASS, audit PASS_WITH_GAPS, UX-regression WARN (non-blocking).

## What's left

- Journey J-15 (Learns from global history (warm start) and is opt-out-able) failing — out of scope iter-4 by design; `history_scope` is accept-and-persist only today.
- Journey J-16 (Robust objective gates overfit) failing — out of scope iter-4 by design; the robust-best invariant it relies on is already preserved here.
- **Closure blocker:** two required UI-visibility artifacts — `reports/phase-goal-auto-money-printer-iter-4-ui-test-plan.md` and `reports/phase-goal-auto-money-printer-iter-4-what-to-click.md` — are stub placeholders ("SKIPPED — agent did not produce this artifact") from a transient `ui-test-design-phase.sh` Claude-CLI exit-1; blocks CLOSURE-PASS. Remediation is a single pipeline-script re-run, no developer/code action (substance independently verified by QA/browser/audit).
- Model-routing split (`modelUsed`) and the additive `stage` field are not rendered as structured UI (spec "Not Visible Yet"; UX-REGRESSION-WARN, non-blocking) — operators infer the split from SCREEN/PROMOTE text + walk-forward presence; tracked as a candidate UI surface for a future J-15/J-16/UI iteration.
- Live real-LLM J-14 validation is browser-QA's job under the tiny-budget mandate (unit tests use a deterministic fake pipeline; no new external system introduced).
- Known limitation: screened (4) / promoted (2) counts are fixed constants, not operator-configurable this iteration.
- Pre-existing out-of-scope failure `test_directions_cache.py::test_write_and_read_full_round_trip` remains (the only tolerated failure per the spec baseline).

## Next step

iter-5 at **full** depth — **J-15** (learns from global history / warm start + `history_scope` opt-out). It activates three load-bearing anti-goals with cross-run state: "global history learning MUST be read-only mining of the existing store (no mutate/delete of prior sessions' artifacts)", "the `history_scope` opt-out MUST be honored" (today accept-and-persist only), and "the LLM-planner / history context MUST use prompt caching; the leaderboard/history MUST NOT be re-sent uncached every round". The natural injection point is this iteration's deterministic SCREEN seed-order enumeration (`_run_staged_open_universe`); reuse the iter-3 durable file store read-only (no schema fork). **J-16** (deep overfit-gating stress demo / leaderboard) follows last — its robust-best invariant is already preserved here.

**Outer-loop action item (NOT a developer/source fix):** the phase is `blocked`/`closure_failed` only because two UI-test-design artifacts (`ui-test-plan.md`, `what-to-click.md`) are transient stubs from a `ui-test-design-phase.sh` Claude-CLI exit-1. The outer loop should run the closure-verdict's exact remediation before iter-4 closes / iter-5 begins: `./scripts/automation/ui-test-design-phase.sh goal-auto-money-printer-iter-4` then `./scripts/automation/phase-closure-check.sh goal-auto-money-printer-iter-4`. No code/test/journey work is implied — implementation, tests, and UI visibility are already fully verified (QA 20/21, browser 10/10, audit PASS_WITH_GAPS).

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-auto-money-printer-iter-4.md |
| Dev handoff | — | docs/handoffs/goal-auto-money-printer-iter-4-dev.md |
| Review | PASS | reports/reviews/goal-auto-money-printer-iter-4-review.md |
| Browser QA | PASS | reports/phase-goal-auto-money-printer-iter-4-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-auto-money-printer-iter-4-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-auto-money-printer-iter-4-user-visible-changes.md |
| What to click | — (stub) | reports/phase-goal-auto-money-printer-iter-4-what-to-click.md |
| UI surface map | — | reports/phase-goal-auto-money-printer-iter-4-ui-surface-map.md |
| UI test plan | — (stub) | reports/phase-goal-auto-money-printer-iter-4-ui-test-plan.md |
| UX regression | UX-REGRESSION-WARN | reports/phase-goal-auto-money-printer-iter-4-ux-regression.md |
| QA | PASS | reports/qa/goal-auto-money-printer-iter-4-qa.md |
| Audit | PASS_WITH_GAPS | docs/handoffs/goal-auto-money-printer-iter-4-audit.md |
| Closure | FAIL | reports/phase-goal-auto-money-printer-iter-4-closure-verdict.md |
| Goal evaluation | CONTINUE | runs/goal-session-auto-money-printer/iter-4/eval.md |
| Journey history | — | runs/goal-session-auto-money-printer/state/journey-history.json |
