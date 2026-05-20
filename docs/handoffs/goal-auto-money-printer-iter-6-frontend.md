# goal-auto-money-printer-iter-6 Frontend Handoff

**Phase:** goal-auto-money-printer-iter-6
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built

- **Additive muted sub-line on the `complete` activity-log row**
  (`apps/frontend/src/components/ActivityLogEntry.tsx`): when an activity
  entry of type `complete` carries a non-empty `detail` field, it is
  rendered as a single muted-text `<p>` immediately below the existing
  `entry.content` paragraph, using the same emerald-card container the
  row already uses. Typography: `text-xs text-emerald-700/70 mt-1`
  (smaller, slightly transparent, one-row margin). Mirrors iter-5's
  warm-start citation row pattern.

## What is NOT changed

- `IterationCard.tsx` — the `Best` badge is untouched (already driven by
  `bestIterationId` from `autoRun`; no rendering changes required).
- `useBacktest.ts` — the `ActivityEntry` type already accepts an optional
  `detail` field (the existing iter-4 SCREEN/PROMOTE auto-run rows and
  iter-5 warm-start row already passed `detail`); no contract change.
- `SessionContainer.tsx`, `AutoRunBar.tsx`, polling/auto-run state — no
  changes (anti-goal: "the iterate loop MUST exist only in the backend;
  the frontend MUST NOT run a second in-browser iterate loop").

## Files Changed

- `apps/frontend/src/components/ActivityLogEntry.tsx` — wrapped the
  existing `<p>` for the `complete` branch in a `<div className="flex-1
  min-w-0">` and added a conditional muted sub-line `<p>` for
  `entry.detail`. Net: +5 lines.

## User-Visible Change

Operators reading the session activity feed now see, beneath each
PROMOTE `complete` row in an open-universe run, a small muted line that
either reads:

- `Best — WF-validated (WFE 0.70, 25 trades)` — this candidate passed the
  walk-forward, min-trades, and over-leverage gates; it is the
  round-current winner.
- `Not best — WFE 0.00 below 0.30 gate` (or `under min-trades floor (2 < 5)`,
  `no walk-forward windows`, `over-leveraged (2.5×)`, `lower robust score
  (0.50 vs best 1.50)`) — this candidate is NOT selected as best and the
  specific gate it failed (or that it lost on robust score) is named.
- `Best (sole survivor) — gates not met: <reason>` — only one PROMOTE
  candidate survived and its own gates fail.

For pinned runs and SCREEN-only rows, no sub-line is rendered (no
`detail` is emitted by the backend on those entries).

In addition, on an open-universe run that promoted ≥ 2 candidates, a
single terminal auto-run row at the end of the feed reads:

> Robust-best: <iter_id> selected over <N-1> other promoted candidate(s)
> — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage

This row uses the existing `auto-run` entry style (zap icon, violet
text) — no new component or icon.

## TypeScript / Lint

- `npx tsc --noEmit -p tsconfig.json` → no errors.
- The `ActivityEntry.detail` field was already declared as
  `detail?: string` in `useBacktest.ts`; no type changes needed.

## Visual Consistency

- Existing emerald-card complete row dimensions and rounded corners
  preserved (`bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3`).
- Sub-line uses the established `text-xs text-emerald-700/70 mt-1` muted
  typography scale already used elsewhere in the file.
- The conditional render means rows without `detail` look byte-identical
  to today; only rows that explicitly carry the rationale show the new
  sub-line.

## Known Limitations

- The rationale text uses a Unicode em-dash (`—`) and the Unicode
  multiplication sign (`×`) — both are valid JSON string characters and
  render correctly across modern browsers; no encoding workaround needed.
- The non-finite `±∞` displays (Unicode minus-infinity / plus-infinity)
  appear only in the defensive error fallback for the
  "lower robust score" branch when a score is non-finite — the
  real-pipeline path never triggers this because
  `backend.robust_objective._finite` collapses non-finite scores to a
  finite sentinel before they reach the rationale helper.
