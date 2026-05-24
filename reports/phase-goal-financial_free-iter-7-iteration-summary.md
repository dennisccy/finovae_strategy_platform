# Iteration Summary — goal-financial_free-iter-7

**Verdict:** CONTINUE
**Iteration type:** goal-full
**Date:** 2026-05-24
**Iteration:** 7

## In plain words

**What you can do now:** Describe a trading strategy in plain English and backtest it on real crypto history; browse and reopen past runs with their trades and results; stress-test a strategy across rolling windows of unseen data; get ranked AI suggestions; pick coins and timeframes; and re-run quickly from a warm cache. You can also start a hands-free automated search that picks its own coins and timeframes from just a goal and a budget — watch it work live (including how much AI usage and money it's spending), stop it from the screen, and reload the page without losing it. The search screens candidates cheaply before spending full effort only on the most promising survivor, stays under a hard spending limit, can be told to learn from your past runs, and crowns only its most robust, fully validated result.

**What changed this time:** After a hands-free automated search, the product now builds a ranked leaderboard of every strategy candidate it tried — with the chosen best highlighted and a short, plain-language reason shown for why each of the others was passed over (for example, a flashier high-return idea that didn't hold up on data it wasn't tuned on). The numbers behind this leaderboard are built and checked, and a real automated run produced a correct ranked list, but the final on-screen confirmation in a real browser window hasn't been captured yet — so this is the one piece not yet fully signed off.

**What's next:** Next we'll confirm the new leaderboard displays correctly in a real browser window — the last check before the automated strategy lab is considered fully delivered.

## Headline

Overfit-gating candidate leaderboard built and data-proven; load-bearing browser pixel render still outstanding.

## Direction

**Signal:** improving
**Why:** J-16 (Robust objective gates overfit — the leaderboard) advanced from `failing` to `partial`: its data, endpoint, persistence, and the new `AutoSessionLeaderboard.tsx` component all landed, persisted (DoD-0 gate held), and were independently proven (12 hermetic tests incl. the binding `test_overfit_gating_higher_return_wfe_fail_not_best`, plus a real live 3-row leaderboard). No journey newly *passed* and J-15…J-01 stayed green with no regression or anti-goal violation, so the only thing between here and GOAL_ACHIEVED is one load-bearing gate: the leaderboard's browser/pixel render, which browser-QA skipped (probed dead `:3692` instead of offset `:3691`) and QA could not capture under the documented hidden-tab throttle.

**Trend (last 5 iters):**
- Newly passing this iter: none (J-16 advanced failing→partial — data layer landed, pixel render pending)
- Newly passing in last 5 iters total: J-12, J-13 (iter-3), J-14 (iter-4), J-15 (iter-6)
- Regressions in last 5 iters: none
- Anti-goal violations in last 5 iters: none
- Iters with no journey state change: 1 of last 5 (iter-5 — work built green but lost before persisting)

**Latest evaluator reasoning:** J-16 (the FINAL journey) half-landed: its data/endpoint/persistence layer is genuinely complete, coherent, and proven, but the LOAD-BEARING browser/pixel render proof was NOT obtained — and the spec is explicit that for this new render path "endpoint-only does NOT close a new render path" and "a 5th endpoint-only substitute is NOT acceptable." Every other journey (J-01–J-15) remains green with no regression, and there are no anti-goal violations and no coherence veto. Because J-16's render layer lacks positive pixel evidence, J-16 is `partial`, not `passing` → GOAL_ACHIEVED is withheld; CONTINUE for one narrow iteration that closes the pixel proof.

## What was done

- Added a per-candidate `leaderboard` to the open-universe auto-run, accumulated at the EXISTING `RobustScorer.score()`/`is_eligible()` call sites (one scorer, zero new scoring, zero new LLM tokens) and persisted via the existing `_save_auto_run` → served on the existing `GET /api/sessions/{id}` (no new endpoint, no eager parse).
- Built new `AutoSessionLeaderboard.tsx` in the Iterations panel: ranked rows (family, SCREEN/PROMOTE badge, robust score, return, color-graded WFE chip, trades, drawdown), a violet "BEST" highlight, and a per-row gating reason; reads `robustScore`/`eligible`/`gatingReason` verbatim and joins display metrics from `iterationHistory` (no FE recompute, best marked solely by `bestIterationId`).
- Added bounded optional `promote_k` (1–3, default 1) on `POST /api/auto-sessions` (422 outside range; omitted ⇒ byte-identical to today), threaded request → `AutoSessionConfig` → `_run_open_universe`; the pinned path ignores it.
- DoD-0 persistence gate satisfied (the iter-5 lost-work failure mode avoided): `apps/` diff = 6 modified + 2 new files, `status.json` `changed_files`=8 + `tests_run:true`, handoff "Files Changed" == diff.
- Verified green: backend 247 passed / 1 pre-existing red (`test_directions_cache`) / 2 deselected, incl. 12 new J-16 leaderboard tests + 4 `promote_k` route tests; FE tsc+vite build + eslint `--max-warnings 0` clean; review PASS_WITH_NOTES; QA PASS_WITH_NOTES.
- Ran a live key-gated open-universe run (`promote_k:2`, 11-month range) that served a real 3-row deduped leaderboard with a correctly WFE-gated best, added 0 tokens, and survived reload.
- Browser QA SKIPPED (0/10 — harness probed dead `:3692` not offset `:3691`) and QA TC-13 BLOCKED by the documented Chrome-MCP hidden-tab render throttle — the leaderboard rows were never pixel-captured (only an empty full-app frame `034-navigate.png`).

## What's left

- Journey J-16 (Robust objective gates overfit) `partial` — its on-screen leaderboard render has no browser/pixel proof; this is the SOLE remaining gate to GOAL_ACHIEVED (spec makes pixel proof load-bearing: an endpoint-only substitute does NOT close a new render path).
- Browser-QA harness root cause still unfixed: `browser-qa-phase.sh` probes `:3000`/wrong offset and missed the deterministic offset port (FE `:3691` / BE `:8691`) — a 7th consecutive pixel miss on the same unfixed bug should be treated as a process stall, not another deferral.
- No in-UI control for `promote_k` (settable only via the API request body, not a form field) — Not Visible Yet.
- Leaderboard is open-universe only; pinned single-strategy runs render no leaderboard (intentional, matches J-16 scope).
- Pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (Capability #10, untouched) — non-blocking carry-forward.
- Flaky pinned-path `test_post_returns_before_loop_completes_and_get_stays_responsive` — de-flake opportunistically, out of scope.
- Out-of-scope `/health` probe still in the tree (release-manager to reconcile handoff/changed_files at commit); `auto_session.py` has grown to ~1.4k lines (future refactor).

## Next step

iter-8 (full depth) = close the SOLE remaining gate — the LOAD-BEARING leaderboard PIXEL render. No new product code is needed; the component is built, type-clean, coherent, and data-proven. (1) Fix the harness ROOT CAUSE first — do NOT retry the broken probe: patch `scripts/automation/browser-qa-phase.sh` to auto-detect the deterministic offset port (`base + sha1(repo)%1000` ⇒ FE `:3691` / BE `:8691`) and health-re-probe across the whole QA window, OR run a genuine foreground, uncontended browser window (the hidden-tab throttle is the documented env limit, not an app bug — keep the tab foreground). (2) Recipe: trigger an open-universe run with `promote_k:2` over a ≥9-month range (iter-4 lesson — else PROMOTE forms 0 WF windows → vacuous) and construct/seek a WFE-failing higher-return candidate so the REJECTION is visible in pixels (the dev's live 2023 run had all candidates pass the gate, so it could not show a rejected one). (3) Capture evidence: ranked rows, highlighted BEST, color-graded WFE chips, and the non-best candidate's gating reason. When that single pixel proof lands, all 16 must-have journeys pass → GOAL_ACHIEVED. Non-blocking carry-forwards (unchanged): pre-existing red `test_directions_cache`; flaky `test_post_returns_before_loop_completes_and_get_stays_responsive`; out-of-scope `/health` probe (release-manager reconciles at commit); `auto_session.py` size.

## Quick verify

From `reports/phase-goal-financial_free-iter-7-what-to-click.md`:

1. Open `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
2. Find the "Candidate leaderboard" card in the Iterations panel (between the status strip and the iteration tree)
3. Read the robust score (right-aligned value on each row's top line) from `#1` downward
4. Locate the violet "BEST" badge
5. Read the small text line under a NON-best row's metrics

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-financial_free-iter-7.md |
| Dev handoff | — | docs/handoffs/goal-financial_free-iter-7-dev.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-financial_free-iter-7-review.md |
| Browser QA | SKIPPED | reports/phase-goal-financial_free-iter-7-ui-test-results.md |
| Implementation summary | — | reports/phase-goal-financial_free-iter-7-implementation-summary.md |
| User-visible changes | — | reports/phase-goal-financial_free-iter-7-user-visible-changes.md |
| What to click | — | reports/phase-goal-financial_free-iter-7-what-to-click.md |
| UI surface map | — | reports/phase-goal-financial_free-iter-7-ui-surface-map.md |
| UI test plan | — | reports/phase-goal-financial_free-iter-7-ui-test-plan.md |
| QA | PASS_WITH_NOTES | reports/qa/goal-financial_free-iter-7-qa.md |
| Goal evaluation | CONTINUE | runs/goal-session-financial_free/iter-7/eval.md |
| Journey history | — | runs/goal-session-financial_free/state/journey-history.json |
