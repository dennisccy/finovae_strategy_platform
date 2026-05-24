# goal-financial_free-iter-6 — Implementation Summary

**Phase:** goal-financial_free-iter-6
**Date:** 2026-05-24
**Written by:** developer

---

## Features Implemented

- **Learn-from-past-runs ("warm start") for the automated search**: A headless
  automated session can now be told to learn from previous sessions. When you start
  an open-universe run with the new option `history_scope: "global"`, the system reads
  the results of your earlier runs (without changing them), figures out which
  symbol/timeframe combinations performed best historically, and spends its first
  expensive evaluation on that historically-strongest combination — instead of always
  starting in a fixed order.

- **A visible "warm-start" note in the Activity Log**: When warm start is used, the
  session's Activity Log shows one new entry explaining the decision, e.g.
  *"WARM-START — prioritizing ETH/USDT 1h (prior session Run One: robust score +0.50)"*.
  This entry appears in the same place and style as the existing automated-run log
  entries — there is no new screen or button.

- **Opt-out is the default**: If you don't set the option (or set it to
  `history_scope: "this-run"`), the run ignores past sessions entirely and behaves
  exactly as it does today. Warm start is strictly opt-in.

---

## Changed Behavior

- **Starting an automated open-universe run**: Previously every open-universe run
  explored the candidate symbol/timeframe combinations in the same fixed order. Now,
  *only when you opt in with `history_scope: "global"`*, the run reorders that exploration
  so the combination that performed best in your past runs is screened and promoted first.
  Without the opt-in, the order is unchanged.

- **The `POST /api/auto-sessions` request**: now accepts an optional `history_scope`
  field. Sending a value other than `"global"` or `"this-run"` is rejected with a clear
  validation error (HTTP 422). Omitting it keeps today's behavior.

---

## Backend-Only Items

- None that are hidden from users. The one user-visible result of this feature — the
  warm-start Activity-Log entry — renders through the **existing** Activity-Log display
  the UI already polls, so no new UI wiring was required. The `history_scope` option is a
  field on the existing automated-session request (no new screen/button by design).

---

## Incomplete Items

- None from this iteration's spec. All in-scope items (request validation, read-only
  miner, cached planner, warm-start ordering, budget compliance, hermetic tests, and the
  persistence gate) are complete and verified.

- The optional **live** end-to-end run (real AI + Binance, a ≥ 9-month date range) was
  not executed here because no API key is configured in this environment. The feature is
  fully proven by the automated test suite at the data/endpoint layer; the live run can be
  performed manually when a key is available.

---

## Config and Environment Changes

- No new environment variables, no config files, no database/schema changes, no new
  infrastructure. Warm start reads and writes only the existing file-based session store.
- API keys are never written into the Activity Log or any saved session data (verified by
  an automated test).

---

## Known Limitations

- **Warm start prioritizes only within the fixed candidate set.** It never expands the
  search beyond the bounded "seed" list of symbols/timeframes — it only reorders that list
  based on history. If your past runs only explored combinations that are not in the
  current candidate set, warm start makes no change (and adds no log entry).

- **The AI planner is best-effort.** If the AI planner is unavailable or returns something
  unusable, the run automatically falls back to ranking the candidates by their historical
  score — warm start still works, just without the AI's one-line rationale. The run never
  crashes because of a planner problem.

- **Two pre-existing, out-of-scope test issues** remain and are unrelated to this feature:
  one long-standing failing test in the unrelated "directions cache" area, and one
  intermittently-flaky timing test on the (separate) pinned-config path. Both are documented
  and were not introduced by this work.
