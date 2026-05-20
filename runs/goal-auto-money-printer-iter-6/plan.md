# goal-auto-money-printer-iter-6 Execution Plan

Target journey: **J-16 — Robust objective gates overfit** (open-universe demo).
J-01–J-15 must remain green. GOAL_ACHIEVED gates on this iteration.

## What to Build

- **Robust-best rationale helper** in `apps/backend/backend/auto_session.py` — a new
  pure function (dependency-light; no new module) that takes a completed
  `(iter_id, RobustInputs)`, the round-current `best_id`, and the per-iteration
  robust score and returns a short operator-readable string:
  - `iter_id == best_id` and gates pass: `"Best — WF-validated (WFE {wfe:.2f}, {n} trades)"`.
  - `iter_id == best_id` and gates fail (sole-survivor fallback):
    `"Best (sole survivor) — gates not met: {reason}"`.
  - `iter_id != best_id`: `"Not best — {specific gate that failed}"`. Reason resolution
    order (use existing `DEFAULT_MIN_WFE` / `DEFAULT_MIN_TRADES` from
    `robust_objective.py`, NO new constants): no walk-forward → `"no walk-forward windows"`;
    `wfe < DEFAULT_MIN_WFE` → `"WFE {wfe:.2f} below {DEFAULT_MIN_WFE:.2f} gate"`;
    `num_trades < DEFAULT_MIN_TRADES` →
    `"under min-trades floor ({n} < {min})"`;
    `leverage > 1.0` → `"over-leveraged ({lev:.1f}×)"`;
    else (gate-passing but lower robust) → `"lower robust score ({s:.2f} vs best {b:.2f})"`.
  - Error-case graceful fallback (corrupt / all-None `RobustInputs`, non-finite robust
    score for comparison branch): returns a finite, JSON-safe string
    (`"Not best — gate evaluation unavailable"` and a finite display for ±inf),
    NEVER raises, NEVER emits empty string, NEVER lets `nan`/`inf` leak into the
    activity log (mirrors `_json_safe` discipline at `auto_session.py:452-468`).

- **Wire the rationale into the PROMOTE `complete` activity entry** at the existing
  append site (`auto_session.py:1429-1441`), immediately after `select_best(completed)`
  resolves the round-current best at `auto_session.py:1449`. Pass the resolved string
  as the `detail` kwarg to `_activity("complete", …, iter_id, detail=…)` (the
  `_activity` helper already accepts `detail`, `auto_session.py:478-491`). The
  append stays off the event-loop via the existing
  `asyncio.to_thread(session_store.append_activity_entries, …)` pattern (iter-2 lesson).
  Exactly **once per promoted iteration** (not per round) — assert via call-count
  in unit tests.

- **Optional one-line terminal summary at run end** (open-universe branch only),
  emitted as a single final `_activity("auto-run", "Robust-best: <iter_id> selected
  over <N-1> other promoted candidate(s) — gates: WFE ≥ {min_wfe:.2f}, ≥ {min_trades}
  trades, no over-leverage", iter_id_of_best)` just before the loop returns. Emit
  **only when ≥ 2 PROMOTE candidates completed** (single-promote = trivially best,
  no comparison row).

- **Frontend — render `detail` as a muted sub-line on `complete` activity entries**
  in `apps/frontend/src/components/ActivityLogEntry.tsx`. Today
  `ActivityLogEntry.tsx:144-153` renders only `entry.content` for the `complete` type
  (verified by reading the file — `entry.detail` is NOT rendered on `complete` rows
  today). Add a single inline conditional muted sub-line below the existing `<p>`,
  using the same typography (`text-xs text-emerald-700/70` or the muted scale already
  used elsewhere in this file) — mirrors the iter-5 warm-start citation row.
  **No new component, no new icon, no new badge, no new panel, no new state.** The
  `Best` badge on `IterationCard.tsx` is untouched (already driven by
  `bestIterationId`).

## Out of Scope (do not implement)

- `_run_pinned` and the pinned-path `complete` entry (`auto_session.py:1125-1234`,
  `1192-1204`) — strict git-diff-empty required.
- SCREEN entries / SCREEN done — no `detail` rationale on SCREEN.
- `robust_objective.py` — `robust_score`, `select_best`, `targets_met`,
  `_GATE_FAIL_PENALTY`, `DEFAULT_MIN_*` are byte-unchanged.
- `shared/contracts.py` — frozen dataclasses, git-diff-empty.
- Cross-round re-computation of a prior PROMOTE's `detail` rationale; rationale is a
  write-time snapshot. The round-final `bestIterationId` in `autoRun` is the live
  source-of-truth for the `Best` badge.
- Plumbing a `leverage` API parameter through the engine. `leverage = 1.0` stays
  hard-coded at `_robust_inputs` (`auto_session.py:1072`); the `"over-leveraged"`
  reason text is still defined in the helper for signature completeness but is not
  exercised by a real backtest in this iteration.
- A new leaderboard page, panel, sortable table, or top-N component.
- The iter-4 closure carryover (regenerate two transient `ui-test-design-phase.sh`
  stubs) — orchestrator/outer-loop work per the spec and iter-5 evaluator log; not
  developer/test/journey budget for iter-6.

## Agents Required

- developer: yes — backend rationale helper + wire-in + optional terminal-summary
  emission; frontend single-line sub-line render of `detail` on `complete` entries;
  unit/integration tests per the spec's TESTING REQUIREMENTS.
- backend-data: yes -- author the rationale helper, wire `detail` into the PROMOTE
  `complete` append at `auto_session.py:1429-1441`, add the optional terminal-summary
  emission at run end (open-universe only, ≥ 2 PROMOTE completed), add the unit /
  integration tests below.
- frontend-ux: yes -- render `entry.detail` as a muted sub-line on the `complete`
  activity-log row in `ActivityLogEntry.tsx` (single-line additive change; no new
  component or state).

## Frontend Present

yes

## Files to Create/Modify

- `apps/backend/backend/auto_session.py` — add rationale helper; pass `detail` kwarg
  to the existing `_activity("complete", …)` call at lines 1429-1441 (immediately
  after `select_best(completed)` at line 1449 resolves the round-current `best_id`);
  add the open-universe terminal-summary `_activity("auto-run", …)` emission before
  the loop returns, guarded by `len(completed) >= 2`.
- `apps/backend/tests/test_auto_session.py` — new tests covering the J-16 demonstration
  scenario, min-trades-floor rationale, no-walk-forward rationale, sole-survivor
  edge cases (both gate-passing and gate-failing), once-per-promote call-count,
  pinned-path delta (no `detail` rationale on pinned `complete`), SCREEN-path
  invariance (no `detail` from rationale helper), error-case graceful fallback
  (corrupt `RobustInputs`, non-finite scores → finite JSON-safe strings).
- `apps/frontend/src/components/ActivityLogEntry.tsx` — single additive sub-line in
  the `complete` branch (lines 144-153) to render `entry.detail` as muted text when
  present.

## UI Evolution

- **New user-facing capability:** every promoted candidate in the activity feed now
  carries an operator-readable rationale string explaining the robust-best decision
  (either `"Best — WF-validated …"` or `"Not best — <gate that failed>"`). The
  user can audit the gate decision in plain English without decoding the
  `robust = −999.x` sentinel.
- **New information displayed:** a short muted sub-line beneath the existing
  `complete` row, plus an optional one-line terminal-summary row at run end.
- **New user actions:** none — read-only audit enrichment.
- **UI surface changes:** none structural; rationale is rendered as muted text on
  the existing `complete` entry, exactly the way the iter-5 warm-start citation row
  extended the existing feed. A headless run remains UI-indistinguishable from a
  manual one (manual runs don't traverse PROMOTE, so they never emit the rationale,
  but the renderer is `detail`-agnostic).
- **Navigation changes:** none.

## Visual Requirements

- **Component patterns:** reuse the existing `complete`-row card
  (`bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3` per
  `ActivityLogEntry.tsx:147`); add the rationale as an inline `<p>` sub-line within
  the same card — no new container, no new icon.
- **Layout:** sub-line sits immediately under the existing emerald `<p>` content,
  same indent (`ml-1` parent, no extra nesting).
- **Key visual effects:** muted-text typography only (e.g. `text-xs text-emerald-700/70`
  or the existing muted scale used for sub-lines elsewhere in the file). Conditional:
  only render when `entry.detail` is a non-empty string.
- **States to handle:** present (rationale string) vs absent (`detail` missing /
  empty → render exactly today's single-line `complete` row, byte-identical). No
  loading/error states (the rationale is a static field on the persisted entry).

## Key Test Scenarios

- **J-16 demonstration (deterministic primary proof):** `FakePipeline(by_cfg=…)`
  isolated `store` fixture, two PROMOTE survivors —
  A `{total_return: 0.50, sharpe: 4.0, num_trades: 30, max_drawdown: 0.40, wfe: 0.0,
  oos_sharpe: -0.5, num_windows: 2}` (overfit-tempting),
  B `{total_return: 0.10, sharpe: 1.1, num_trades: 25, max_drawdown: 0.08, wfe: 0.7,
  oos_sharpe: 1.0, num_windows: 3}` (robust). Assert: `autoRun.bestIterationId == B`;
  A's `complete` entry has `detail == "Not best — WFE 0.00 below 0.30 gate"`; B's
  `complete` entry has `detail` starting with `"Best — WF-validated"`. Read both
  through `session_store`.
- **Min-trades-floor rationale:** PROMOTE candidate with `num_trades=2`, `wfe=0.8` →
  `detail == "under min-trades floor (2 < 5)"`.
- **No-walk-forward rationale:** PROMOTE candidate with `num_windows=0` →
  `detail == "no walk-forward windows"`.
- **Sole-survivor edge cases:** single PROMOTE completes — assert `detail` is
  `"Best — WF-validated …"` when its own gates pass, else
  `"Best (sole survivor) — gates not met: …"`. The `Best` badge still appears.
- **Pinned path byte-unchanged:** `test_pinned_path_unchanged_by_open_universe_addition`
  green; add a delta assertion that no PROMOTE-style `detail`-bearing rationale row
  appears on a pinned run.
- **SCREEN entries unchanged:** no SCREEN `complete` / `SCREEN done` entry has a
  `detail` field set by the rationale helper.
- **Robust-best invariant test re-used:**
  `test_robust_objective_rejects_high_return_wfe_failing_overleveraged`
  (`apps/backend/tests/test_auto_session.py:307-318`) stays green unchanged.
- **Once-per-promote / not-per-round:** in a 2-PROMOTE scenario, the rationale row
  appends exactly twice across the run; activity-log read-back / `FakePipeline.bt_calls`
  confirm call-count.
- **Error cases:** corrupt / partial `RobustInputs` → graceful finite string;
  non-finite robust score in the comparison branch → finite display, no `nan`/`inf`
  in the JSON activity log.
- **Browser-QA (J-16, observable corroboration of the renderer):** one tiny-budget
  open-universe run (default `_OPEN_UNIVERSE_*` window) against the real backend.
  At least two PROMOTE `complete` entries appear in the activity feed; each carries
  a coherent rationale tag (`"Best — …"` exactly once across the run,
  `"Not best — …"` on every other PROMOTE). The `Best` badge sits on the entry whose
  rationale begins `"Best — …"`. No secrets, no API jargon, no `null` / `undefined`
  / `NaN` / `Infinity` literals in the rendered text. At least one screenshot
  capturing the rationale text and the `Best` badge co-located in the same view.
  (Per iter-5 lesson, the durable `BACKTEST_STORE_DIR` cannot be emptied and a real
  open-universe run cannot deterministically guarantee a WFE-failing-and-WF-validated
  pair co-occur in a tiny budget; the unit test above is the deterministic primary
  proof, browser is the renderer corroboration — NOT a "fallback".)
- **Regression suite:** full backend suite green except for the pre-existing,
  out-of-scope, explicitly-tolerated
  `test_directions_cache.py::test_write_and_read_full_round_trip` (unchanged).

## Structural Anti-Goal Proofs (developer must self-verify before handoff)

- `git diff HEAD -- apps/backend/backend/auto_session.py` shows ZERO edits inside
  `_run_pinned` (`auto_session.py:1125-1234`).
- `git diff HEAD -- apps/backend/backend/robust_objective.py` is empty.
- `git diff HEAD -- apps/backend/shared/contracts.py` is empty.
- `git diff HEAD -- apps/backend/backend/session_store.py`,
  `apps/backend/backend/pipeline.py`, `apps/backend/backend/sandbox.py`,
  `apps/backend/backtest/**` all empty.
- iter-5 write-primitive scan over the full added iter-6 diff
  (`grep -E '\.write\(|open\([^)]*[\"'"'"']w|json\.dump|\.unlink|\.rename|shutil\.|os\.remove|derive_session_tabs'`)
  finds ONLY additional `append_activity_entries` calls on the *current* session
  (same primitive iter-4 / iter-5 used) — no new write paths, no parallel store, no
  schema fork.
- No new external infrastructure imports (no new top-level imports introduced by
  the diff).
- Rationale string contains no API keys / secrets (it is purely numeric + gate-name
  vocabulary; tests assert this for the deterministic scenarios).
- `would_exceed` / `_SPEND_CAPS` / `max-configs` vs spend-cap distinction
  (`auto_session.py:100-107`, `1381-1385`) byte-unchanged; no new tokens, no new LLM
  call, no budget gate touched.
- All new `_activity` appends use `asyncio.to_thread` (iter-2 event-loop discipline).

## Assumptions

- The existing `ActivityLogEntry.tsx:144-153` `complete` branch does NOT render
  `entry.detail` today — verified by reading the file. A minimal additive sub-line
  is therefore required (not a zero-line diff). If a reviewer disagrees and finds
  generic `detail` rendering elsewhere applies, the preferred outcome is a literal
  zero-line frontend diff — but the dev should not assume that without re-reading.
- `_activity("complete", …, iter_id, detail=…)` is the existing helper signature
  (`auto_session.py:478-491`); no change to `_activity` is required.
- The deterministic J-16 demonstration runs on an isolated `store` fixture (per the
  spec's testing requirements). Browser-QA is observable corroboration of the
  renderer on a real open-universe run, not the deterministic gate-semantics proof.
- The iter-4 closure carryover (two transient ui-test-design stubs) is outer-loop
  work and is explicitly out of scope for the developer; it must not flip any
  journey verdict.
