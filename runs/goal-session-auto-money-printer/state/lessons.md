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
