# Iteration Summary — goal-financial_free-iter-2

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-23
**Iteration:** 2

## In plain words

**What you can do now:** Describe a trading strategy in plain English and run it against real crypto price history; browse and reopen past runs with their full results and individual trades; stress-test a strategy across rolling out-of-sample windows; get ranked AI improvement suggestions; pick from the available coins and timeframes; and re-run quickly from a warm cache. On top of that, you can now kick off a hands-free automated strategy search, watch it work live on screen, and stop it whenever you want — and it keeps running even if you reload the page or close the tab.

**What changed this time:** The hands-free Auto Run search now runs entirely on the server instead of inside your browser tab, so you can reload the page or close your laptop and it keeps going. A new status strip at the top of the results panel shows it working live — whether it's running, how many improvement rounds it has done against the budget, how much time has elapsed, why it stopped, and which attempt is the current best — and new strategy attempts appear on their own with no manual refresh. The Stop button now genuinely halts the run on the server and keeps the best result found so far.

**What's next:** Next, the automated search will start picking coins and timeframes on its own from just an objective and a budget, with a hard spending cap and a leaderboard that won't crown an overfit winner.

## Headline

Layer-1 complete: Auto Run rewired to a durable server-side loop with live tracking and a real Stop.

## Direction

**Signal:** improving
**Why:** This iter moved J-08 (track the run live in the UI), J-10 (backend single source of truth, survives reload), and J-11 (server-side stop) from `failing` → `passing`, completing Layer-1 of the automated-search goal. The in-browser iterate loop and the duplicate `scoreIteration` were deleted (grep-verified), Auto Run/Stop were rewired to the existing backend endpoints, and the B1+B2 stop-vs-persist race was closed under a shared per-session `asyncio.Lock` (race regression test green). The only open thread is live-pixel browser QA — deferred because Vite went down mid-window — and Layer-2 (J-12…J-16) is the next target.

**Trend (last 3 iters):**
- Newly passing this iter: J-08, J-10, J-11
- Newly passing in last 3 iters total: J-07, J-08, J-09, J-10, J-11
- Regressions in last 3 iters: none
- Anti-goal violations in last 3 iters: none
- Iters with no journey state change: 0 of last 3

**Latest evaluator reasoning:** Layer-1 is complete: the backend auto-session loop is now the only Auto Run engine. J-08, J-10, and J-11 move from `failing` → `passing` — the in-browser iterate loop and duplicate `scoreIteration` are deleted (grep-verified), "Auto Run"/"Stop" are rewired to the existing backend command endpoints, and the persisted `autoRun` block is surfaced live in the new status strip. The spec-mandated B1+B2 critical gate passes (verified in the actual code, not just claimed). Not GOAL_ACHIEVED — Layer-2 (J-12…J-16) is entirely unbuilt.

## What was done

- Rewired "Auto Run" to start a durable **server-side** optimization session — the backend loop is now the only Auto Run engine, so closing or reloading the tab no longer kills the run; the new run appears as its own entry in the Session picker.
- Deleted the in-browser iterate loop and the duplicate in-browser `scoreIteration` (grep: none found); "best" is now defined solely by the backend WFE-gated, drawdown-penalized `RobustScorer`.
- Added a live **status strip** atop the Iterations panel — run state (Running → Criteria met / Budget exhausted / Stopped), rounds done / max, elapsed / max wall-clock, stop reason, and the marked Best — driven by the polled `autoRun` block with no manual reload; hidden entirely on manual sessions.
- Made the running indicator/spinner derive from the backend `autoRun.status` (reload-safe) instead of a local in-browser flag.
- Wired the Stop button to the existing `POST /api/auto-sessions/{id}/stop`; the run transitions to Stopped, freezes iterations, and retains the best-so-far.
- Closed the B1+B2 stop-vs-persist race: the controller's off-loop `autoRun` read-modify-write is held under a per-session `asyncio.Lock` that `/stop` shares; the new `test_stop_racing_save_auto_run_is_not_dropped` regression test is green.
- Verification posture: QA **PASS**, review **PASS_WITH_NOTES**, coherence **COHERENCE-PASS**. Browser QA was **SKIPPED** (0/15 — Vite dev server went down mid-window); J-08/J-10/J-11 were verified via the spec-sanctioned backend-endpoint + static-code fallback against real tiny-budget live runs (QA TC-06…TC-10).

## What's left

- Journey J-12 (Open-universe run from only an objective + budget) failing — Layer-2, not built (open-universe POST correctly rejected 400 today, boundary preserved).
- Journey J-13 (AI-token/cost budget hard-enforced) failing — `max_iterations` is the current primary terminator; the hard token/USD cap by the immutable cost tracker is not built.
- Journey J-14 (Staged screening — full cost only on survivors) failing — Layer-2, not built.
- Journey J-15 (Learns from global history / warm start, opt-out-able) failing — Layer-2, not built.
- Journey J-16 (Robust objective gates overfit) failing — the WFE-gated scorer exists as the canonical best, but the leaderboard / overfit-gating UI is not built.
- Carry-forward live-pixel UI debt: J-08 (live strip + cards streaming without reload), J-10 (reload-mid-run survival), and the J-01/J-05 manual regressions were verified via backend-endpoint + code fallback only; capture real pixels in the Layer-2 browser-QA window with a reliably-serving frontend.
- Pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (nice-to-have, untouched module) — not a regression; opportunistic fix only.
- Coherence advisory tidies (non-blocking): add `error` to the blueprint run-state enum row; "rounds vs iterations" label is tooltip-clarified and acceptable.

## Next step

Begin **Layer-2 (J-12…J-16) at full depth** — the most complex slice of the goal and the one with a real new UI surface: **J-12** open-universe search from a bounded seed universe (no blind exchange-wide fan-out; ≥2 distinct configs as iterations, best marked by robust score); **J-13** hard token/USD budget enforced by the immutable cost tracker with real pipeline token accounting (`stop reason = budget-exhausted`, spend ≤ cap visible in the status block, no iterations after the cap); **J-14** staged **SCREEN → PROMOTE** (cheap-first; walk-forward + strong model only on promoted top-k, visible in the activity log); **J-15** global-history warm start (read-only mining of the existing store, `history_scope` opt-out honored, planner/history context using prompt caching); **J-16** robust-objective overfit gating surfaced in a leaderboard (WFE ≥ threshold + min-trades floor; a higher-raw-return but WFE-failing/over-leveraged candidate must NOT be marked best). Carry-forward (non-blocking now): clear the live-pixel UI debt for J-08/J-10 and the J-01/J-05 manual regressions in that iteration's browser-QA window; opportunistically fix the pre-existing red `test_directions_cache`; apply the coherence advisory tidies. Do not re-litigate the eager-load anti-goal (resolved iter-1) or the in-browser-scorer removal (done this iter).

## Quick verify

From `reports/phase-goal-financial_free-iter-2-what-to-click.md`:

1. Open `http://localhost:3692` in your browser.
2. In the Left config bar, type a strategy (e.g. `simple SMA crossover`), set the date range to `2024-01-01`→`2024-01-07`, pick the cheapest model, set the Auto Run count input to `2`, then click the violet "Auto Run (2)" button (lightning-bolt icon) at the right of the config bar.
3. Without reloading, watch the status strip counters for ~10 seconds.
4. Keep watching the Iterations panel (do NOT reload).
5. While the run is still active, reload the page (press F5), then re-select the same session tab in the Session picker.

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-financial_free-iter-2.md |
| Dev handoff | — | docs/handoffs/goal-financial_free-iter-2-dev.md |
| Frontend handoff | — | docs/handoffs/goal-financial_free-iter-2-frontend.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-financial_free-iter-2-review.md |
| Browser QA | SKIPPED | reports/phase-goal-financial_free-iter-2-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-financial_free-iter-2-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-financial_free-iter-2-user-visible-changes.md |
| What to click | — | reports/phase-goal-financial_free-iter-2-what-to-click.md |
| UI surface map | — | reports/phase-goal-financial_free-iter-2-ui-surface-map.md |
| UI test plan | — | reports/phase-goal-financial_free-iter-2-ui-test-plan.md |
| QA | PASS | reports/qa/goal-financial_free-iter-2-qa.md |
| Demo results | — | reports/phase-goal-financial_free-iter-2-demo-results.md |
| Coherence | COHERENCE-PASS | runs/goal-session-financial_free/iter-2/coherence.md |
| Goal evaluation | CONTINUE | runs/goal-session-financial_free/iter-2/eval.md |
| Journey history | — | runs/goal-session-financial_free/state/journey-history.json |
