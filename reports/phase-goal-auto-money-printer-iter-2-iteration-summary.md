# Iteration Summary — goal-auto-money-printer-iter-2

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-19
**Iteration:** 2

## Headline

Auto Run rewired to a server-driven backend session that survives a browser reload and is stoppable from the UI.

## Direction

**Signal:** improving
**Why:** This iter rewired both UI "Auto Run" entrypoints to `POST /api/auto-sessions` and deleted the legacy in-browser iterate loop in `useBacktest.ts`, landing J-10 (survives mid-run reload) and J-11 (stoppable, robust best preserved) as newly-passing with browser + source + unit evidence. No prior-passing journey regressed — the two lesson-protected journeys J-02 (right-panel re-bind) and J-08 (no stale terminal) were explicitly re-verified — and zero anti-goals were violated. The Optimizer layer (J-12–J-16) remains failing by design and is the evaluator's next target; all three iters so far moved journeys forward, so direction is healthy.

**Trend (last 3 iters):**
- Newly passing this iter: J-10, J-11
- Newly passing in last 3 iters total: J-01, J-03, J-04, J-05, J-06 (iter-0 baseline); J-02, J-07, J-08, J-09 (iter-1); J-10, J-11 (iter-2)
- Regressions in last 3 iters: none
- Anti-goal violations in last 3 iters: none (0)
- Iters with no journey state change: 0 of last 3

**Latest evaluator reasoning:** The Layer-1 Foundation is genuinely closed. J-10 (backend single source of truth — both "Auto Run" entrypoints rewired to `POST /api/auto-sessions`, the legacy in-browser iterate loop deleted, run survives a mid-run reload) and J-11 (public stop endpoint + by-`sessionId` cancel registry + durable worker/restart-safe stop signal; `stopped` terminal with reason; robust `bestIterationId` preserved) both newly pass with browser + source + unit evidence. Every required-still-passing journey holds; the two lesson-protected journeys (J-02 right-panel re-bind, J-08 no-stale-terminal) were explicitly re-verified PASS at browser **and** source-diff level.

## What was done

- Rewired both UI "Auto Run" entrypoints (config-bar trigger + per-card action) to start a server-driven backend auto-session via `POST /api/auto-sessions`; the search now keeps running if the browser tab is closed or reloaded (J-10).
- Added `POST /api/auto-sessions/{id}/stop` + a by-`sessionId` in-process cancel registry (cleaned on all 4 terminal paths) + a durable, worker/restart-safe per-round stop signal in the session file store (no new infra, no schema fork); the UI Stop control is wired to it (J-11).
- On stop: terminal `status="stopped"` with a non-null reason, no iterations appended past the stop, and `bestIterationId` stays selected by the existing robust objective (never re-derived by raw return).
- Deleted the legacy in-browser `startAutoRun`/`stopAutoRun` iterate loop and its solely-owned state/refs — no second in-browser generate→backtest→insights loop remains (verified by source diff per the iter-1 lesson).
- Hardened `AutoRunBar`/`SessionContainer` ownership: each session's `autoRun` status is authoritatively re-derived from the backend on mount and on session switch, so the session-list spinner and the status strip cannot disagree (iter-1 mandatory lesson).
- QA-FAIL retry fixes: moved the CPU-bound backtest into a stdlib `multiprocessing` child process (its own GIL — event loop no longer starved; pipeline/engine/sandbox/`contracts.py` unchanged), self-healing live-poll re-arm in `finally`, and a stable Stop-button identity.
- Verified target journeys J-10 and J-11 pass browser QA — 21/21 QA functional cases and 17/17 browser tests PASS; backend `test_auto_session` 26/26, full suite 150 passed / 1 pre-existing out-of-scope fail (zero new regressions), frontend build EXIT 0.

## What's left

- Journey J-12 (Open-universe run from only an objective + budget) failing — out of scope this iter; still correctly 422-rejected.
- Journey J-13 (AI-token/cost budget is hard-enforced) failing.
- Journey J-14 (Staged screening — full cost only on survivors) failing.
- Journey J-15 (Learns from global history / warm start, opt-out-able) failing.
- Journey J-16 (Robust objective gates overfit) failing.
- Non-blocking UX-REGRESSION-WARN: the activity-log message tells operators to look for an "Auto: …" session, but the `Auto:` prefix is transient (~12–15 s) before the backend overwrites it with the strategy name — reword the message or preserve the prefix (deferred; capability not lost: running session reachable via the pulsing amber dot + "running" badge).
- Non-blocking audit GAP: `POST /api/auto-sessions/{id}/stop` latency ~0.027 s clean but ~10.5 s under an unrealistic synthetic load (6+ sessions + 61 live-polling containers) — trim the multi-MB result pickle to a scalar proxy across the child pipe (tracked for iter-3).
- Known limitation (by design): a new "Auto: …" session is discovered via the existing App.tsx ~5 s poll — select it from the Sessions dropdown to watch it.

## Next step

Open the **Optimizer layer at full depth**, starting with the Optimizer Foundation: **J-12** (open-universe config search — currently still correctly 422-rejected by `create_auto_session`, so this is genuine net-new backend work) and **J-13** (the immutable, hard-enforced AI-token/USD + max-configs + wall-clock cost tracker), then **J-14** (staged SCREEN→PROMOTE — cheap screen must NOT run walk-forward or the strong model), **J-15** (read-only global-history warm start with the `history_scope` opt-out + prompt-cached planner context), and **J-16** (robust WFE-gated/drawdown-penalized/min-trades best selection over the open universe). Full pipeline (audit + ux-regression + closure) is warranted: this is the heaviest remaining scope and activates several strong anti-goals (hard budget / no blind fan-out / SCREEN cheapness / prompt caching / robust-best). Carry forward as a tracked, non-blocking item the stop-endpoint pickle trimming (scalar result proxy across the child pipe) to remove the load-sensitive latency tail.

## Quick verify

From `reports/phase-goal-auto-money-printer-iter-2-what-to-click.md`:

1. Open `http://localhost:3691` in your browser.
2. In the config bar set Symbol `BTC/USDT`, Timeframe `1 Hour`, Start `2024-01-01`, End `2024-02-01`, Capital `10000`. In the left box type `Buy when RSI crosses below 30, sell when it crosses above 70` and press **Enter** (or click the blue paper-plane Send button).
3. Set the small number box right of the Auto Run button to `2`, then click the violet **"Auto Run (2)"** button.
4. Click the **Sessions** button (top-right); within ~5 seconds a new **"Auto: …"** row appears with a pulsing amber dot and a `running` badge. Click that row.
5. While it still reads **"Automated run · iteration X/2"**, hard-reload the page (Ctrl+Shift+R). Then click **Sessions** and re-open the same **"Auto: …"** session.

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-auto-money-printer-iter-2.md |
| Dev handoff | — | docs/handoffs/goal-auto-money-printer-iter-2-dev.md |
| Dev handoff (frontend) | — | docs/handoffs/goal-auto-money-printer-iter-2-frontend.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-auto-money-printer-iter-2-review.md |
| Browser QA | PASS | reports/phase-goal-auto-money-printer-iter-2-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-auto-money-printer-iter-2-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-auto-money-printer-iter-2-user-visible-changes.md |
| What to click | — | reports/phase-goal-auto-money-printer-iter-2-what-to-click.md |
| UI surface map | — | reports/phase-goal-auto-money-printer-iter-2-ui-surface-map.md |
| UI test plan | — | reports/phase-goal-auto-money-printer-iter-2-ui-test-plan.md |
| UX regression | UX-REGRESSION-WARN | reports/phase-goal-auto-money-printer-iter-2-ux-regression.md |
| QA | PASS | reports/qa/goal-auto-money-printer-iter-2-qa.md |
| Audit | PASS_WITH_GAPS | docs/handoffs/goal-auto-money-printer-iter-2-audit.md |
| Closure | CLOSURE-PASS | reports/phase-goal-auto-money-printer-iter-2-closure-verdict.md |
| Goal evaluation | CONTINUE | runs/goal-session-auto-money-printer/iter-2/eval.md |
| Journey history | — | runs/goal-session-auto-money-printer/state/journey-history.json |
