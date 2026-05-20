# Phase goal-auto-money-printer-iter-6 — UI Surface Map

**Phase:** goal-auto-money-printer-iter-6
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|------------|------------|-------------|
| `/` (main session view, Activity Log column) | `ActivityLogEntry.tsx` — `complete` branch (emerald-bordered card, lines 144–158) | Changed layout (additive sub-line) | The existing `<p>` was wrapped in a `flex-1 min-w-0` div and a conditional muted `<p className="text-xs text-emerald-700/70 mt-1">` was added beneath it to render `entry.detail` when present. Required by J-16 so each open-universe PROMOTE `complete` row carries an operator-readable robust-best rationale. | Start an open-universe automated run with budget large enough for ≥ 2 PROMOTE candidates. Wait for ≥ 2 `complete` rows to appear in the Activity Log. Verify each emerald card now shows TWO lines: the existing return/trades/robust/WFE numeric line on top, AND a smaller muted line below reading either `Best — WF-validated (WFE X.XX, N trades)` or `Not best — <named gate>` (e.g., `Not best — WFE 0.00 below 0.30 gate`). Confirm no `null`, `undefined`, `NaN`, `Infinity`, or API-jargon text appears in the muted line. |
| `/` (main session view, Activity Log column) | `ActivityLogEntry.tsx` — `auto-run` branch (violet Zap-icon row, lines 27–34) | Changed behavior (new emission, no component change) | The backend now emits ONE final `_activity("auto-run", "Robust-best: <iter_id> selected over <N-1> other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage", best_id)` row at the end of any open-universe run that promoted ≥ 2 candidates. The renderer is byte-unchanged; only the new emitted entry is new. | After an open-universe run with ≥ 2 promoted candidates completes, scroll to the bottom of the Activity Log. Verify the LAST entry before the terminal stopped-/idle-state markers is a violet row with a Zap icon and the literal text starting `Robust-best:` followed by an iter id, `selected over` an integer, `other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage`. Confirm this row does NOT appear on a single-promote run or on a pinned/SCREEN-only run. |
| `/` (main session view, Activity Log column) | `ActivityLogEntry.tsx` — `complete` branch on PINNED path | Unchanged behavior (anti-regression assertion) | The backend's `_run_pinned` is byte-unchanged; it never sets `detail` on pinned `complete` entries. The renderer's `entry.detail &&` guard means pinned rows render with byte-identical layout to today. | Submit a pinned-path strategy run (manual or J-07 fixture). Wait for the pinned `complete` row to appear in the Activity Log. Verify the emerald card shows EXACTLY ONE line (the existing top-line content) with no muted sub-line beneath — visually byte-identical to pre-iter-6 behavior. |
| `/` (main session view, Iteration list column) | `IterationCard.tsx` — `Best` badge | Unchanged (touchstone for J-16 acceptance) | The `Best` badge is still driven by `autoRun.bestIterationId`; no rendering change was made. The rationale and the badge are independent presentation surfaces but must stay co-locatable in the same view for J-16 to pass. | After an open-universe run, locate the iteration with the `Best` badge in the Iteration list (left/center column). Cross-check that the SAME iteration's row in the Activity Log carries a rationale beginning with `Best —` (not `Not best —`). They must agree: the badge sits on the iteration whose rationale text starts with `Best —`. |
| `/` (main session view, Activity Log column) | `ActivityLogEntry.tsx` — SCREEN entry rows | Unchanged behavior (anti-regression assertion) | SCREEN entries intentionally do NOT receive a rationale `detail` (rationale belongs only on PROMOTE `complete`). The renderer is detail-agnostic, so a SCREEN entry without `detail` renders identically to today. | During an open-universe run, locate any SCREEN-stage activity entries that appear before the PROMOTE stage. Verify NONE of them show a muted rationale sub-line (no `Not best — …` or `Best — …` text under a SCREEN row). |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/backend/auto_session.py` — new `_finite_display`, `_robust_best_reason`, `_robust_best_rationale` helpers — pure functions; consumed only by the PROMOTE branch via the `detail` argument to `_activity`; no UI surface beyond the rendered string itself.
- `apps/backend/backend/auto_session.py` — import-line widening to pull `DEFAULT_MIN_WFE` and `DEFAULT_MIN_TRADES` from `backend.robust_objective` — no new constants, no UI exposure.
- `apps/backend/tests/test_auto_session.py` — 21 new unit/integration tests covering the J-16 demonstration scenario, gate-specific rationale branches, sole-survivor edge cases, call-count, pinned/SCREEN invariance, and partial/non-finite input handling — test-only, no UI surface.

---

## Summary

- **Frontend surfaces changed:** 1 (the `complete`-branch JSX in `ActivityLogEntry.tsx` — +5 net lines)
- **New pages/routes:** 0
- **Modified components:** 1 (`ActivityLogEntry.tsx`)
- **Navigation changes:** no
- **Backend-only changes:** 2 production files (`auto_session.py` rationale helpers + terminal-summary emission; test file with 21 new tests is test-only)
