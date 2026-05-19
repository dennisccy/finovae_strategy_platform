# Goal Session auto-money-printer — Lessons Learned

Append-only ledger of takeaways from prior iterations. The goal-evaluator
appends one entry per iteration; the goal-decomposer reads this file before
planning each iteration to avoid repeating known pitfalls.

Each entry should be 1-3 sentences capturing a non-obvious lesson — surprising
failures, regression triggers, or decisions that worked well. Avoid
restating the verdict (the evaluator-log.md already does that).

## iter-0 — 2026-05-19T01:45:00Z

**Verdict:** CONTINUE
**Lesson:** J-02 ("browse run history") is *partial*, not passing, in the
core platform a prior session marked GOAL_ACHIEVED: selecting an older run
reloads its spec+metrics into the LEFT conversation panel but the RIGHT
analysis panel (trades table + equity curve + WF) stays pinned to the latest
run and never re-binds. This is easy to misread as "history works" because
the left panel does update — any iter must verify the prior run's *trades
table* actually reloads, not just its summary.
**Applies to:** any iter touching session/run-history selection or the
right-hand analysis panel (`apps/frontend` `SessionContainer.tsx` /
`IterationPanel.tsx` / `useBacktest.ts`); also the build iters for J-07–J-16,
which must not regress this existing manual-history path.

## iter-1 — 2026-05-19T07:20:00Z

**Verdict:** CONTINUE
**Lesson:** J-08's "live tracking" passes the happy path but the in-session
`AutoRunBar` can show a *stale terminal* status for a freshly-opened
still-running session when many `SessionContainer`s are mounted and the user
switches sessions rapidly (only masked because the session-list running
spinner is independently correct). This is a real ownership/concurrency bug
(per-session status not authoritatively re-derived on mount/switch), not
cosmetic polish — it will become a hard correctness failure once J-10 makes
the backend the single source of truth and deletes the in-browser loop.
Separately: the canonical `ui-test-results.md` headline was a *stale pre-fix
FAIL* reconciled to PASS by the auditor — never trust that headline alone;
verify the post-fix source diff + the QA MODE-2 (full-mode) report.
**Applies to:** iter-2 J-10/J-11 and any iter touching
`apps/frontend/src/components/SessionContainer.tsx` /
`AutoRunBar` / `apps/frontend/src/hooks/useBacktest.ts` autoRun status wiring —
J-10 MUST harden AutoRunBar ownership (re-derive per-session status on
mount/switch), not just rewire the button. Also: any evaluator reading a
reconciled UI-test artifact must cross-check source diffs + QA MODE-2, not the
top headline.
