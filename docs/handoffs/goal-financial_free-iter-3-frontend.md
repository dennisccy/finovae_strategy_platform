# goal-financial_free-iter-3 Frontend Handoff

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Agent:** developer
**Status:** complete
**Frontend Present:** yes

## What Was Built (UI)

Display-only extension of the existing **Automated-session status strip** — no new pages, panels, or
routes; no new user actions. The strip now surfaces the new canonical budget counters for an
automated (backend Auto Run) session, read straight from `autoRun.budget` (single source of truth)
during the existing ~2.5s poll of `GET /api/sessions/{id}`:

- **Token spend / cap** — `1.2k / 50k tok` style (compact tokens; cap shown only when set).
- **USD cost / cap** — `$0.0123 / $0.0500` style (4-dp USD; cap shown only when set).
- **Configs explored / max** — `1/2 configs` for open-universe runs; pinned sessions keep the
  existing **rounds** counter (`0/2 rounds`). The strip shows configs **or** rounds depending on
  whether `budget.maxConfigs` is present, so each session shows its relevant work counter.

Open-universe configs themselves render through the **existing** iteration cards — each card already
shows its `params` symbol/timeframe, so distinct configs (varying symbol/timeframe) appear as
ordinary cards with no new component.

## Files Changed

- `apps/frontend/src/lib/sessionApi.ts` — extended the `AutoRunBudget` interface with
  `configsDone: number`, `maxConfigs: number | null`, `maxTokens: number | null`,
  `maxUsd: number | null`, mirroring the backend `BudgetTracker.to_dict()`.
- `apps/frontend/src/components/AutoSessionStatusStrip.tsx` — added `fmtTokens`/`fmtUsd`
  display-only formatters and rendered the token / USD / configs counter chips in the existing
  right-aligned counter group (same `text-xs text-slate-500` chips with `·` separators and `title`
  tooltips; no new component, no raw div-soup). The configs↔rounds choice is driven by
  `budget.maxConfigs != null`.

## Design / States

- **Component patterns:** reuses the established status-strip counter row — same typography, spacing,
  and separators; no new visual effects. Follows the existing `STATUS_META` light-theme status
  semantics (running = blue/active spinner; `budget-exhausted` = amber wrap, which the token/USD
  counters inherit when a run finishes at/near its cap).
- **States handled:** active (counters accrue live via the existing poll), terminal `budget-exhausted`
  (amber), and **pinned sessions render cleanly** — the configs chip is omitted when `maxConfigs` is
  null and the rounds chip shows instead; token/USD chips render with spend only when no cap is set.
- **No business logic in the frontend** — every counter is read-only from the canonical
  `autoRun.budget` block; formatting only, never recomputed. No second fetch.

## Tests Run

- `cd apps/frontend && npm run build` (tsc type-check + vite) — **passes**.
- `cd apps/frontend && npm run lint` (`eslint --max-warnings 0`) — **passes**.
- No `AutoRunBudget` object literals are constructed in the frontend (the budget is always read from
  the polled backend response), so the added required fields introduce no type breakage; verified by
  grep + the clean tsc build.

## Known Limitations

- The in-UI "Auto Run" control still starts a **pinned-config** backend session (unchanged from
  iter-2); there is no UI control to trigger an open-universe run this iteration (J-12 is
  API-triggered, per spec). The UI only **tracks** an open-universe run live (status strip + cards).
- Pixel-level confirmation of the live-updating token/USD strip and reload-mid-run survival is for
  the browser-qa-agent (tiny-budget open-universe run), with the Vite frontend health-checked across
  the whole window per the iter-2 lesson. If the documented Chrome-MCP hidden-tab render throttle
  blanks pixels, fall back to the exact backend endpoints the strip reads
  (`GET /api/sessions/{id}` → `autoRun.budget`).
