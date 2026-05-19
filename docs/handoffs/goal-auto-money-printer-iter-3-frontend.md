# goal-auto-money-printer-iter-3 Frontend Handoff

**Phase:** goal-auto-money-printer-iter-3
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built

A single **additive** change to the existing `AutoRunBar` status strip — no
new page, panel, leaderboard, route, or redesign.

- **Spend readout (J-13).** When the polled durable `autoRun` block carries a
  `spend` object, the bar shows a compact, right-aligned, `tabular-nums`
  readout: `<tokens> tok · $<usd> · <n> cfg` (AI tokens / USD / configs
  explored under the hard budget). Hidden entirely when `spend` is
  absent/null (legacy or just-created sessions) — the bar renders exactly as
  before, never a `NaN`/`undefined`.
- **`budget-exhausted` made visually distinct (J-13).** A budget-reached
  terminal now renders amber with a `CircleDollarSign` icon and
  "Automated run complete · budget reached · X/Y iterations", clearly
  distinct from a `criteria-met` finish (emerald `CheckCircle2`) and a
  `stopped` run (red `StopCircle`).
- The readout updates live while the run is active (the existing 2.5 s
  poll already calls `setAutoRun(nextAuto)` with the whole block) and
  persists after a reload (it reads the durable `autoRun.spend`).

## Files Changed

- `apps/frontend/src/hooks/useBacktest.ts` — added `AutoRunSpend` interface
  and optional `AutoRunStatus.spend?: AutoRunSpend | null`. **Type-only.** No
  change to the live-poll effect, the iter-2 `try/finally` re-arm, or the
  J-02 heavy-detail merge precedence (the existing poll/hydration already
  pass the entire `autoRun` object through `setAutoRun`, so the new field
  flows automatically).
- `apps/frontend/src/components/SessionContainer.tsx` — `AutoRunBar`: new
  `formatSpend()` helper, distinct `budget-exhausted` tone/icon branch, and
  an additive spend `<span>` inside the existing bar `<div>` (no new layout
  region). Imported `CircleDollarSign` from `lucide-react`.

## Tests Run

Command: `cd apps/frontend && npm run build`
Result: **EXIT 0** — `tsc` typecheck + `vite build` succeeded (2231 modules;
the >500 kB chunk-size advisory is pre-existing and not an error).

## Visual / State Coverage

- **running:** spinner + `iteration i/maxIterations` + live-accumulating
  spend readout (partial spend is fine — it only ever increases).
- **complete · criteria-met:** emerald, `CheckCircle2`, final spend shown.
- **complete · budget-exhausted:** amber, `CircleDollarSign`,
  "budget reached", final spend ≤ cap shown — visually distinct.
- **stopped:** red, `StopCircle` (unchanged).
- **legacy / pinned-without-spend / just-created:** `spend` null → readout
  omitted, bar byte-identical to before (graceful, no NaN/undefined).
- Reuses existing Tailwind tokens (text-xs, the bar's tone classes,
  `opacity-75`, `tabular-nums`) — dense, dark, data-forward, consistent with
  the established style; no invented effects.

## Known Issues

None. The change is confined to the `AutoRunBar` strip and its type; no
existing user journey (J-02 prior-run right-panel re-bind, J-08 no-stale-
terminal live poll) is touched.
