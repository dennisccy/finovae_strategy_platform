# Iteration Summary — goal-financial_free-iter-4

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-23
**Iteration:** 4

## In plain words

**What you can do now:** You can describe a trading strategy in plain English and test it against real crypto market history, browse and reopen any past test with its trades and results, check how a strategy holds up across rolling slices of out-of-sample history, get ranked AI improvement suggestions, choose which coins and timeframes to use, and re-run quickly from cached data. You can also kick off a hands-free automated search that picks its own coins and timeframes from just a goal and a budget, stays under a hard spending limit (AI usage, dollar cost, number of setups, and time), shows its progress live with a running token-and-dollar tally, can be stopped from the screen, survives a page reload, and crowns only its most robust result.

**What changed this time:** The automated search now spends cheaply first. It quickly screens several candidate setups on the cheapest AI model without the heavy validation, then takes only the single most promising survivor and gives it the full, expensive treatment — rigorous out-of-sample validation and a more powerful AI model. You can watch this happen as it works (a cheap screening sweep, then the promotion of the winner), and the "best" result badge now only ever lands on a fully validated promoted candidate — never on a cheap, un-validated one that happened to show a flashy return.

**What's next:** Next, the automated search will learn from your past runs to start smarter — with the option to keep any run isolated from that history.

## Headline

Staged SCREEN→PROMOTE: screen candidates cheaply, promote only the top survivor to full walk-forward (J-14).

## Direction

**Signal:** improving
**Why:** This iter turned the open-universe search into a staged SCREEN→PROMOTE cost-tiering flow, moving J-14 from failing to passing (verified hermetically — 209 tests green — plus a live cross-provider gpt-5.4-mini→claude-haiku-4-5 run) with zero regressions and no anti-goal violations. Every iteration since the baseline has moved at least one journey forward (J-07/J-09 → J-08/J-10/J-11 → J-12/J-13 → J-14), so direction is healthy. J-15 (history warm-start) is the evaluator's next target; the only open risk is the 4th-iteration live-pixel capture gap, attributed to the browser-qa harness frontend lifecycle rather than an app defect.

**Trend (last 5 iters):**
- Newly passing this iter: J-14
- Newly passing in last 5 iters total: J-07, J-09 (iter-1); J-08, J-10, J-11 (iter-2); J-12, J-13 (iter-3); J-14 (iter-4) — plus J-01–J-06 confirmed already-passing at the iter-0 baseline
- Regressions in last 5 iters: none
- Anti-goal violations in last 5 iters: none
- Iters with no journey state change: 0 of last 5

**Latest evaluator reasoning:** J-14 (staged SCREEN→PROMOTE cost-tiering for the open-universe search) is newly passing — verified independently, not on trust. The open-universe loop now SCREENs the budget-bounded seed configs cheaply (`cheapest_model()`, `wfv_enabled=False`), ranks them by the one canonical `RobustScorer`, PROMOTEs only the top-k (`DEFAULT_PROMOTE_K=1`, k<N) to a stronger model + walk-forward, and marks best from the PROMOTED candidates only — all as pure orchestration over the existing pipeline/scorer/store with zero `contracts.py`, endpoint, page, route, request-field, or datastore change. Coherence = COHERENCE-PASS, so no structural veto.

## What was done

- Restructured the open-universe automated search into a two-stage SCREEN→PROMOTE flow: cheap screening of seed configs (`cheapest_model()`, `wfv_enabled=False`, no walk-forward), then promote of the top-k=1 survivor on the request model with walk-forward — pure orchestration over the existing pipeline/scorer/store (no `contracts.py`/endpoint/route/request-field/datastore change).
- Added `cheapest_model()` to `shared/model_catalog.py` as the single source for SCREEN model selection (min blended-rate catalog model; `gpt-5.4-mini` today).
- Added `BudgetTracker.cost_exceeded()` (cost caps only — tokens/USD/wall-clock) to gate PROMOTE without consuming config slots; `exceeded()` left byte-unchanged so the J-13 budget invariants hold.
- Marked best via `RobustScorer.select_best()` over PROMOTED candidates only — a cheaply-screened node can never be crowned best (anti-goal-critical), and `select_best → None` before any promote is the correct gated outcome.
- Surfaced both stages in the existing Activity Log (`auto-run` entries): `SCREEN —` header + per-candidate rows, `PROMOTE —` header ("top-k of N") + winner; promoted nodes nest as children of their screened parent. Zero frontend code changed.
- Added 16 hermetic staged-flow tests (stage routing `wfv==[F,F,F,T]`, k<N, best-WFE-gated positive+negative, stop mid-screen/mid-promote, degenerate single-config, promote-fail-non-fatal, `cost_exceeded` units); full suite 209 passed / 1 known pre-existing red / 2 deselected.
- Verified J-14 live (real gpt-5.4-mini SCREEN + claude-haiku-4-5 PROMOTE): 3 SCREEN nodes (cheap model, no WF) + 1 PROMOTE node (stronger model, WF complete) nested under the top-scored screened node, no secrets in artifacts.
- Browser QA: 0 of 13 tests passed — all SKIPPED (frontend not running); target journeys J-08/J-10/J-14 verified instead via the backend endpoint the UI polls (`GET /api/sessions/{id}` → `autoRun` + activity entries) plus zero-frontend-change code confirmation.

## What's left

- Journey J-15 (Learns from global history / warm start, opt-out-able) failing — deferred, the evaluator's next target.
- Journey J-16 (Robust objective gates overfit — multi-candidate leaderboard UI) failing — a single best badge exists, but the ranked overfit-gating leaderboard is not built.
- Live browser-pixel capture of the live status strip (J-08), reload-mid-run survival (J-10), and the new SCREEN/PROMOTE Activity Log entries (J-14) still not captured — 4th-iteration carry-forward; root cause is the harness frontend lifecycle (the FE on :3692 does not stay serving through the browser-qa/QA window), not an app defect.
- No UI to tune promote-k or the per-stage models — internal defaults (`DEFAULT_PROMOTE_K=1`, cheapest SCREEN model, request PROMOTE model); deliberately out of scope.
- Stopping during the cheap SCREEN phase leaves no "best" yet (by design — best is WFE-gated from promoted candidates only); screened nodes remain saved and browsable.
- Pre-existing red test `test_directions_cache` (unrelated nice-to-have, untouched module).
- Flaky test `test_post_returns_before_loop_completes_and_get_stays_responsive` to de-flake (test-scaffolding timing race; green in the evaluator re-run).
- Scope/doc reconciliation: an out-of-scope `GET /health` probe was added to `api.py` (absent from the handoff/`changed_files`), and the `incredible_auto_dev/.../demo*.sh` working-tree changes are unrelated framework tooling — release-manager should reconcile/note or exclude these in the commit.

## Next step

Proceed to **J-15 (learns from global history / warm start, opt-out-able) at full depth** — replace this iteration's deterministic seed-universe SCREEN ordering with a history-informed plan: read-only mining of prior sessions in the existing file store, a cached LLM-planner that cites prior-session performance, with `history_scope: "global"|"this-run"` honored as the opt-out. Enforce the binding anti-goals: history mining MUST be read-only (never mutate/delete prior artifacts), the planner/leaderboard context MUST use prompt caching (not re-sent uncached each round), and the `history_scope` opt-out MUST be honored. Then J-16 (multi-candidate overfit-gating leaderboard UI) visualizes the promoted, WFE-gated candidates this iteration now produces. **Decisively address the now-4×-recurring live-pixel gap by fixing the ROOT CAUSE, not the instruction** — either fix `browser-qa-phase.sh` so the frontend is started and stays serving for the entire window (health-re-probed, uncontended tab) before any pixel claim, or formally accept the endpoint-layer + zero-FE-change proof as sufficient for these display-only journeys and stop carrying it as debt. Any walk-forward-dependent live QA MUST use a date range ≥ IS_months + OOS_months (≥9mo at defaults) so best-marking is not silently vacuous. Non-blocking carry-forward (do not re-litigate resolved items): pre-existing red `test_directions_cache`; de-flake `test_post_returns_before_loop_completes_and_get_stays_responsive`; reconcile the `/health` addition and the framework `demo*.sh` changes into the handoff/commit.

## Quick verify

From `reports/phase-goal-financial_free-iter-4-what-to-click.md`:

1. Start one open-universe run by running this `curl -s -X POST http://localhost:8000/api/auto-sessions` command (objective `robust`, model `claude-haiku-4-5`, `max_configs:3`) in a terminal; copy the returned session id.
2. Open `http://localhost:3692/?session=<id>` in your browser (paste the id).
3. While the run is active, watch the status-strip chips (token / USD / configs) near the top for ~15 seconds without reloading.
4. In the Left Activity Log, find the entry beginning with `SCREEN —`.
5. Below the SCREEN entries, find the entry beginning with `PROMOTE —`.

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-financial_free-iter-4.md |
| Dev handoff | — | docs/handoffs/goal-financial_free-iter-4-dev.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-financial_free-iter-4-review.md |
| Browser QA | SKIPPED | reports/phase-goal-financial_free-iter-4-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-financial_free-iter-4-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-financial_free-iter-4-user-visible-changes.md |
| What to click | — | reports/phase-goal-financial_free-iter-4-what-to-click.md |
| UI surface map | — | reports/phase-goal-financial_free-iter-4-ui-surface-map.md |
| UI test plan | — | reports/phase-goal-financial_free-iter-4-ui-test-plan.md |
| QA | PASS | reports/qa/goal-financial_free-iter-4-qa.md |
| Goal evaluation | CONTINUE | runs/goal-session-financial_free/iter-4/eval.md |
| Journey history | — | runs/goal-session-financial_free/state/journey-history.json |
