# goal-auto-money-printer-iter-6 Dev Handoff

**Phase:** goal-auto-money-printer-iter-6
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built

- **`_robust_best_rationale` helper** (and the inner `_robust_best_reason` /
  `_finite_display` helpers) — a pure, dependency-light function in
  `apps/backend/backend/auto_session.py` that takes one PROMOTE candidate's
  `(iter_id, RobustInputs, robust score)` plus the round-current best (id +
  score) and returns a short operator-readable rationale string. Output
  shapes:
  - `iter_id == best_id` and gates pass → `"Best — WF-validated (WFE X.XX, N trades)"`
  - `iter_id == best_id` and gates fail (sole survivor) → `"Best (sole survivor) — gates not met: <reason>"`
  - `iter_id != best_id` and gates fail → `"Not best — <reason>"` (specific
    gate that failed: no walk-forward → WFE → min-trades → over-leverage)
  - `iter_id != best_id` and gates pass → `"Not best — lower robust score (X.XX vs best Y.YY)"`
  - Error fallback: any internal exception returns a finite
    `"… — gate evaluation unavailable"` string (never raises, never empty,
    never leaks `nan`/`inf` into the JSON activity log).
- **Wired the rationale into the existing PROMOTE `complete` activity entry**
  in `_run_staged_open_universe` at the existing append site
  (`auto_session.py:1556-1571` post-edit). `select_best(completed)` is now
  resolved BEFORE the append, so the rationale snapshot reflects the
  round-current best at write time. The append still goes through
  `asyncio.to_thread(session_store.append_activity_entries, …)` (iter-2
  event-loop discipline preserved).
- **Terminal-state robust-best summary emission** at the end of
  `_run_auto_session_impl`: when an open-universe run promoted ≥ 2
  candidates, ONE final `_activity("auto-run", "Robust-best: <iter_id>
  selected over <N-1> other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5
  trades, no over-leverage", best_id)` row is appended just before the
  terminal `_update_autorun`. Single-promote runs (trivially best) and the
  pinned path never emit this row.
- **Frontend `ActivityLogEntry.tsx`** — additive single-line muted sub-line
  beneath the existing `complete` row that renders `entry.detail` when
  present (mirrors iter-5's warm-start citation row). No new component, no
  new state, no new badge. The `Best` badge on `IterationCard.tsx` is
  untouched (already driven by `bestIterationId`).

## Files Changed

- `apps/backend/backend/auto_session.py` -- added rationale helpers and
  terminal-summary emission; modified PROMOTE complete entry to pass the
  rationale as `detail`. `_run_pinned` is byte-unchanged (verified via
  function-range diff).
- `apps/backend/tests/test_auto_session.py` -- added 21 new tests covering
  the J-16 demonstration scenario, min-trades / no-WF / over-leverage /
  lower-robust-score rationales, sole-survivor edge cases (both
  gate-passing and gate-failing), once-per-promote call count, pinned-path
  rationale-absence, SCREEN-path rationale-absence, terminal-summary
  presence/absence, and graceful handling of partial inputs / non-finite
  scores.
- `apps/frontend/src/components/ActivityLogEntry.tsx` -- single additive
  sub-line render of `entry.detail` on the `complete` activity row.

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`
Result: **74 passed** (all auto_session tests green, including the
existing `test_robust_objective_rejects_high_return_wfe_failing_overleveraged`
unit-proof of the invariant the new rationale text describes).

Command: `cd apps/backend && .venv/bin/python -m pytest`
Result: **221 passed, 1 failed** — the only red is the pre-existing,
explicitly-tolerated, out-of-scope
`test_directions_cache::test_write_and_read_full_round_trip` (unchanged,
documented in the spec's DEFINITION OF DONE).

## Structural Anti-Goal Proofs

- `git diff HEAD -- apps/backend/backend/robust_objective.py` → **empty**.
- `git diff HEAD -- apps/backend/shared/contracts.py` → **empty**.
- `git diff HEAD -- apps/backend/backend/session_store.py
  apps/backend/backend/pipeline.py apps/backend/backend/sandbox.py
  apps/backend/backtest/` → **empty**.
- `_run_pinned` (pinned path, J-07–J-11) is byte-unchanged when extracted
  by function-range diff (`async def _run_pinned` … `async def
  _run_staged_open_universe`).
- iter-5 write-primitive scan over the full added diff
  (`grep -E '\.write\(|open\([^)]*[\"'\''](w|a)|json\.dump|\.unlink|\.rename|shutil\.|os\.remove|derive_session_tabs'`)
  returns **zero hits** — all new writes go through the existing
  `session_store.append_activity_entries` helper on the current session.
- No new external infrastructure imports introduced (no Celery / Redis /
  DB / broker / vector-store).
- `_SPEND_CAPS` / `would_exceed` / `max-configs`-vs-spend-cap distinction
  byte-unchanged (no new tokens, no new LLM call, no new budget gate).
- All new `_activity` appends use `asyncio.to_thread` (iter-2 event-loop
  discipline preserved).

## Snapshot Semantics Design Note

The spec explicitly mandates **snapshot semantics** ("Re-evaluate prior
promoted iterations' rationale across rounds is OUT OF SCOPE; each PROMOTE
entry's `detail` reflects the best-known-at-write-time decision").
Consequently, the rationale that appears on a PROMOTE `complete` row
reflects whether, *at the moment that row was written*, the candidate was
the round-current best (using `select_best` over the already-completed
candidates). The round-final `bestIterationId` in the `autoRun` block
remains the single source of truth for the `Best` badge and is what the
UI displays as the chosen winner.

In the open-universe SCREEN→PROMOTE pipeline, candidates are promoted in
descending in-sample-Sharpe order. This means the rationale text a
*specific candidate* receives depends on the order in which it was
promoted. In the deterministic J-16 demonstration test
(`test_open_universe_j16_rationale_promotes_robust_winner`), the
WF-validated candidate is given the higher in-sample Sharpe so it is
promoted first (and receives "Best — WF-validated") and the
overfit-tempting WFE-failing candidate is promoted second (and correctly
receives "Not best — WFE 0.00 below 0.30 gate"). For real headless runs,
the operator sees: at any point, an in-flight winner is plainly tagged
"Best — WF-validated" while a subsequent gate-failing candidate is plainly
tagged "Not best — <reason>"; the terminal summary row durably names the
final chosen best for runs with ≥ 2 promoted candidates.

## Known Issues

- None new. The pre-existing
  `test_directions_cache::test_write_and_read_full_round_trip` failure is
  carried unchanged per the spec; it is unrelated to this iteration's
  scope.
- The deterministic J-16 demonstration is asserted via a `FakePipeline(by_cfg=...)`
  integration test on an isolated `store` fixture (per iter-5's lesson:
  the durable `BACKTEST_STORE_DIR` cannot be emptied for browser QA, and a
  real tiny-budget open-universe browser run cannot deterministically
  guarantee a WFE-failing-and-WF-validated pair co-occurs). The browser
  test is observable corroboration of the *renderer*, not a re-derivation
  of the gate semantics.
- A future architecture that runs multiple SCREEN→PROMOTE rounds would
  see across-round rationale staleness. The spec explicitly defers this
  to a future iteration ("across rounds is OUT OF SCOPE").
