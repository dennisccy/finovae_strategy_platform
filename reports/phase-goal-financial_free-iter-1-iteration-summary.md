# Iteration Summary — goal-financial_free-iter-1

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-23
**Iteration:** 1

## In plain words

**What you can do now:** Describe a trading strategy in plain English and run it against real crypto price history; browse and reopen past runs with their full results and trades; stress-test a strategy across rolling out-of-sample windows; get ranked AI suggestions; pick from the available coins and timeframes; re-run quickly from a warm cache; and — new this round — kick off a fully hands-free automated strategy search that runs to a clean finish and marks its most robust result, all visible in your normal session list.

**What changed this time:** The automated strategy search came online. You can now start a hands-free run with a single command — it seeds a starting strategy, tries AI-suggested improvements one round at a time, and stops cleanly the moment it either meets the targets you set or reaches its budget, never sneaking in an extra round. It picks its winner with a skeptical eye: the result it marks "best" has to survive an out-of-sample validation test, so a flashier-looking result that fails validation can't win. The run shows up like any other session and its status survives a server restart. (For now you start it with a command; on-screen buttons come next.)

**What's next:** On-screen controls to start an automated run, watch it progress live, and stop it — so you can drive it without the command line.

## Headline

Headless automated strategy search lands — start a server-side run with one API call.

## Direction

**Signal:** improving
**Why:** This iter brought the Layer-1 auto-session core online — J-07 (start a headless run via `POST /api/auto-sessions`) and J-09 (terminal stop-reason + WFE-gated best marking) are newly passing, verified by 40 new green tests, route mounting at `api.py:113,116`, and a documented 317s live smoke. J-01…J-06 held with no regression and coherence is PASS. Eight journeys remain failing but all are scheduled (J-08/J-10/J-11 next iteration, J-12…J-16 in Layer-2), so the direction is healthy.

**Trend (last 2 iters):**
- Newly passing this iter: J-07, J-09
- Newly passing in last 2 iters total: J-07, J-09
- Regressions in last 2 iters: none
- Anti-goal violations in last 2 iters: none
- Iters with no journey state change: 0 of last 2

**Latest evaluator reasoning:** The Layer-1 auto-session core landed cleanly: a single `POST /api/auto-sessions` with a pinned config + tiny budget starts a server-side loop that reuses the injected `BacktestPipeline`, writes byte-shape-identical artifacts through `session_store`, runs to a real terminal state (`criteria-met` / `budget-exhausted` / `stopped`), and marks a WFE-gated robust best on a durable `autoRun` block. J-07 and J-09 are newly passing (verified by re-running the suite, confirming route mounting, and the documented 317s live smoke); J-01…J-06 show no regression; no critical anti-goal violation; coherence is PASS.

## What was done

- Added `POST /api/auto-sessions`: a plain-English strategy + pinned config (symbol, timeframe, date range, capital, optional targets) + required budget starts a fully server-side strategy search; the created session appears immediately in `GET /api/sessions` and is browsed like a manual one, launched as a non-blocking background task under the shared one-backtest-per-worker semaphore.
- Implemented the headless loop: seed a baseline, then take untried AI suggestions round by round (generate → backtest → walk-forward), persisting each candidate via `session_store` (no parallel store), running to a real terminal state (`criteria-met` / `budget-exhausted` / `stopped`).
- Built a WFE-gated, drawdown-penalized `RobustScorer` (min-trades floor, 0.3 WFE threshold) that marks a single canonical "best" — a higher-raw-return but WFE-failing candidate is never chosen.
- Added an immutable `BudgetTracker` that hard-enforces `max_iterations` + wall-clock (checked before each round; never starts a round past the cap); token/USD remain best-effort counters (hard cap deferred to J-13).
- Persisted a durable `autoRun` status block on `session.json`, exposed additively on `GET /api/sessions/{id}` (status, stop reason, best-iteration id, budget counters); survives restart/reload, and orphaned `running` sessions reconcile to `interrupted` on startup.
- Added `POST /api/auto-sessions/{id}/stop` graceful-stop plumbing (idempotent 200 / 404 on unknown) as infrastructure for J-11, and extracted `result_serialization.py` so the headless and manual paths emit byte-shape-identical artifacts.
- Verified J-07 + J-09 via 40 new green hermetic tests + the 3 invariant tests, route-mounting checks, and a 317s key-gated live smoke that ran the real pipeline to a terminal state with a marked best (16/16 QA cases; 164 passed / 1 deselected / 1 pre-existing unrelated red). Browser QA skipped (backend-only) — J-07 "appears as a session" confirmed through `GET /api/sessions`.

## What's left

- Journey J-08 (Track the automated run live in the UI) failing — iter-2 target.
- Journey J-10 (Backend is the single source of truth — button rewired, survives reload) failing — iter-2 target.
- Journey J-11 (Stop a running automated session) failing — `/stop` infra exists, the UI stop + reload-survival journey is iter-2.
- Journey J-12 (Open-universe run from only an objective + budget) failing — explicitly rejected with HTTP 400 this iteration by design; Layer-2.
- Journey J-13 (AI-token/cost budget is hard-enforced) failing — token/USD are best-effort counters this iter; hard cap is Layer-2.
- Journey J-14 (Staged screening — full cost only on survivors) failing — Layer-2.
- Journey J-15 (Learns from global history / warm start, opt-out-able) failing — Layer-2.
- Journey J-16 (Robust objective gates overfit) failing — Layer-2 (the robust scorer it will surface was built this iter as the canonical "best" definition).
- Concurrency fix (review MINOR B1 + audit B2) deferred to iter-2 and must be solved together: move the controller's `autoRun` store I/O off the event loop AND serialize it against `/stop` (the `to_thread` fix alone would widen a TOCTOU race on the `stopRequested` flag).
- Pre-existing red `test_directions_cache::test_write_and_read_full_round_trip` (nice-to-have Capability #10, untouched module) — carried forward, not a regression.

## Next step

Build iter-2 (Layer-1 finish): J-08 + J-10 + J-11 at full depth. **J-10** — rewire the in-browser Auto Run (`useBacktest.ts:~2047`) to drive this backend loop, remove the second in-browser iterate loop and delete the now-redundant in-browser `scoreIteration`, and prove server-side progress survives a browser reload. **J-08** — live UI tracking: the open session shows `running` → terminal with at least one iteration + suggestions appearing without a manual reload (poll/SSE off the existing session-open path). **J-11** — wire the UI stop control to the existing `POST /api/auto-sessions/{id}/stop` and verify the full stop journey (transitions to `stopped`, best retained, no further iterations). **Concurrency (audit B1+B2, solved together):** move the controller's `autoRun` reads/writes off the event loop (`await asyncio.to_thread`) AND serialize them against `/stop` (async lock / single-writer) — don't apply `to_thread` alone. Browser QA becomes load-bearing again; honor the documented Chrome-MCP render-throttle (verify via the backend endpoints the UI calls when pixels are blank). Carry forward (non-blocking): the pre-existing red `test_directions_cache`. The eager-load verdict is resolved (conforms) — do not re-litigate.

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-financial_free-iter-1.md |
| Dev handoff | — | docs/handoffs/goal-financial_free-iter-1-dev.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-financial_free-iter-1-review.md |
| Browser QA | SKIPPED | reports/phase-goal-financial_free-iter-1-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-financial_free-iter-1-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-financial_free-iter-1-user-visible-changes.md |
| What to click | — | reports/phase-goal-financial_free-iter-1-what-to-click.md |
| UI surface map | — | reports/phase-goal-financial_free-iter-1-ui-surface-map.md |
| UI test plan | — | reports/phase-goal-financial_free-iter-1-ui-test-plan.md |
| QA | PASS | reports/qa/goal-financial_free-iter-1-qa.md |
| Audit | PASS_WITH_GAPS | docs/handoffs/goal-financial_free-iter-1-audit.md |
| Closure | CLOSURE-PASS | reports/phase-goal-financial_free-iter-1-closure-verdict.md |
| Goal evaluation | CONTINUE | runs/goal-session-financial_free/iter-1/eval.md |
| Journey history | — | runs/goal-session-financial_free/state/journey-history.json |
