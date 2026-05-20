# Iteration 6 — Implementation Summary

**Phase:** goal-auto-money-printer-iter-6
**Date:** 2026-05-19
**Written by:** developer

---

## Features Implemented

- **Operator-readable robust-best rationale on every promoted candidate
  in the activity feed.** During an open-universe automated search,
  each PROMOTE row in the session activity log now carries a short
  sentence in plain English explaining either why this candidate IS the
  current best (gates passed) or why it is NOT (the specific gate it
  failed). Examples: "Best — WF-validated (WFE 0.70, 25 trades)",
  "Not best — WFE 0.00 below 0.30 gate", "Not best — under min-trades
  floor (2 < 5)", "Not best — no walk-forward windows", "Not best —
  over-leveraged (2.5×)", "Not best — lower robust score (0.50 vs best
  1.50)".

- **Terminal robust-best summary row** at the end of an open-universe
  run that promoted ≥ 2 candidates. One auto-run row reads "Robust-best:
  &lt;iter id&gt; selected over N-1 other promoted candidate(s) — gates:
  WFE ≥ 0.30, ≥ 5 trades, no over-leverage" so the operator has a
  durable record of the chosen winner and the gate set, even if the
  per-row rationale scrolls out of view.

- **Sole-survivor edge case** handled visibly: a run where only one
  PROMOTE candidate completes (others failed or were budget-capped) is
  marked "Best — WF-validated (...)" if its gates pass, or
  "Best (sole survivor) — gates not met: &lt;reason&gt;" if it fails its
  own walk-forward / min-trades / over-leverage gate. A best is always
  marked.

---

## Changed Behavior

- **PROMOTE `complete` activity entries (open-universe path).**
  Previously: showed return, trades, robust score, walk-forward WFE as
  a single line of text. Now: the same line still appears, plus a muted
  sub-line beneath it carrying the rationale. The robust score sentinel
  (`-999.x` when gates fail) was technically visible before but
  cryptic; the new sub-line names the failed gate in operator language.

- **Order of operations inside the open-universe PROMOTE branch.** The
  call to `select_best(completed)` (which resolves the round-current
  best) now happens BEFORE the activity-log append, so the rationale
  embedded in the append reflects the at-write-time best. Functionally
  identical to before from the user's perspective; structurally the
  same set of writes in the same activity feed.

---

## Backend-Only Items

None. Every backend change is reflected in the user-facing activity
feed, which is also wired in the frontend (`ActivityLogEntry.tsx`).

---

## Incomplete Items

None. All in-scope items in the phase spec are complete:

- Rationale helper ✓
- Wire-in to PROMOTE complete entry ✓
- Terminal summary emission ✓
- Pinned path byte-unchanged ✓
- SCREEN path byte-unchanged ✓
- `robust_objective.py` byte-unchanged ✓
- Frontend muted-text sub-line render ✓
- Unit + integration tests for J-16 demonstration, min-trades,
  no-walk-forward, over-leverage, lower-robust-score, sole-survivor,
  once-per-promote, pinned-no-detail, SCREEN-no-detail, terminal
  summary, error cases ✓

---

## Config and Environment Changes

None. No new env vars, no new dependencies, no migration, no new
constants, no new external infrastructure. The rationale text uses
existing constants `DEFAULT_MIN_WFE` and `DEFAULT_MIN_TRADES` from
`backend.robust_objective` (already in use; this iteration only adds
them to the module's `from … import …` line).

---

## Known Limitations

- **Snapshot semantics**: the rationale on a specific PROMOTE row
  reflects the round-current best at *write time*. Within a single
  open-universe run the SCREEN→PROMOTE pipeline promotes candidates in
  descending in-sample-Sharpe order; if a gate-failing candidate happens
  to have the highest in-sample Sharpe and is therefore promoted first,
  its rationale at write time will read "Best (sole survivor) — gates
  not met: ..." rather than "Not best — ..." (because at that instant
  no gate-passing candidate has yet been observed). A subsequent
  gate-passing PROMOTE will displace it in the `bestIterationId` field
  of the `autoRun` block (which the UI uses to render the `Best` badge),
  but the earlier row's textual rationale is a frozen snapshot per the
  phase spec's explicit "out of scope" clause. The terminal summary row
  at run end names the final chosen best, providing a durable
  reconciliation point. A future architecture that runs multiple
  SCREEN→PROMOTE rounds, or that retroactively updates earlier
  rationales, is explicitly deferred.

- **Deterministic primary proof is unit/integration, not browser.**
  Per iter-5's documented lesson, the durable `BACKTEST_STORE_DIR`
  cannot be emptied between QA runs (~113 prior sessions accumulate by
  anti-goal design), and a real tiny-budget open-universe browser run
  cannot guarantee that a WFE-failing-and-WF-validated pair co-occurs.
  The deterministic proof is therefore a
  `FakePipeline(by_cfg=...)` integration test on an isolated `store`
  fixture (`test_open_universe_j16_rationale_promotes_robust_winner`,
  plus the min-trades / no-walk-forward / sole-survivor / pinned /
  SCREEN tests). Browser QA is observable corroboration that the
  *renderer* surface works on a real run — not a re-derivation of the
  gate semantics.

- **The over-leveraged reason text is defined but not exercised by a
  real backtest in this iteration.** The `leverage` parameter is still
  hard-coded to 1.0 in `_robust_inputs` (`auto_session.py:1072`).
  Plumbing a `leverage` request parameter through the API is explicitly
  out of scope per the phase spec.
