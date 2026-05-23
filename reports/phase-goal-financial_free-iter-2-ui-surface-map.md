# Phase goal-financial_free-iter-2 — UI Surface Map

**Phase:** goal-financial_free-iter-2
**Date:** 2026-05-23
**Written by:** ui-impact-analyst

> Single-page app (no client-side router). "Route / Page" below refers to the persistent two-panel
> shell and its named panels rather than distinct URLs. Use a **tiny budget** for any live test
> (≤ 2 iterations, short date range, cheapest model, lenient targets). Honor the documented
> Chrome-MCP headless render-throttle: if pixels are blank, verify via the backend endpoints the UI
> calls (`GET /api/sessions`, `GET /api/sessions/{id}`, `POST /api/auto-sessions`,
> `POST /api/auto-sessions/{id}/stop`) and the persisted `autoRun` block.

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| App shell (Right / Iterations panel) | `AutoSessionStatusStrip` (NEW) | New component | Surfaces the live backend `autoRun` block (status, budget, stop reason, best) | Start an Auto Run; confirm the strip appears at the top of the Iterations panel showing a **blue "Running"** badge with an animated spinner and a "Optimizing server-side" label. |
| App shell (Right / Iterations panel) | `AutoSessionStatusStrip` budget counters | New component | Shows live progress against budget | While a run is active, confirm the `rounds done / max` counter increments (e.g. `1/2 rounds`) and the `elapsed s / max s` wall-clock counter increases over successive ~2.5s polls. |
| App shell (Right / Iterations panel) | `AutoSessionStatusStrip` terminal state | New component | Shows the run outcome and reason | Let a tiny-budget run finish; confirm the badge changes to **"Budget exhausted"** (amber) or **"Criteria met"** (emerald), the spinner stops, and the stop-reason text (e.g. "Budget exhausted") appears. |
| App shell (Right / Iterations panel) | `AutoSessionStatusStrip` best badge | New component | Marks the backend-chosen best iteration | After at least one iteration produces a result, confirm a violet **"Best: <8-char id>"** badge appears in the strip's second row. |
| App shell (Right / Iterations panel) | `AutoSessionStatusStrip` (manual session) | New component | Strip must not show for manual sessions | Open or create a **manual** (non-Auto Run) session; confirm the status strip is **not rendered** at all. |
| App shell (Right / Iterations panel) | `IterationPanel` live iteration tree | Changed behavior | New iteration cards now stream in from backend polling | Start an Auto Run and **do not reload**; confirm at least one new iteration card appears in the tree on its own within a few seconds, each with a backtest result. |
| App shell (Right / Iterations panel) | `IterationPanel` empty state | Changed behavior | Run spins up before first iteration exists | Immediately after starting an Auto Run, confirm a "Waiting for the first iteration…" style empty state shows beneath the status strip. |
| App shell (Left / config bar) | `BacktestConfigBar` Auto Run / Stop control | Changed behavior | Control state now derives from backend `autoRun.status` | Click "Auto Run"; confirm the Auto Run control becomes **disabled** and a **Stop** control becomes visible while the backend status is queued/running, then re-enables at terminal status. |
| App shell (iteration card) | `IterationCard` ⚡ Auto Run action | Changed behavior | ⚡ now seeds a backend auto-session | Click the ⚡ on a **completed** iteration card; confirm a **new session tab is added and selected** in the Session picker and tracking of the new auto-session begins. |
| App shell (Session picker) | `SessionPicker` running spinner | Changed behavior | Spinner now derives from backend status | With an auto-session running, confirm the Session picker shows a spinner next to it; reload the page mid-run and confirm the spinner **reappears** without any user action. |
| App shell (Session picker) | New auto-session tab | New behavior | Auto Run mints a new backend session | After clicking Auto Run, confirm a new session entry appears in the picker and is the active tab. |
| App shell (whole app) | Stop action (server-side) | Changed behavior | Stop now cancels the backend loop | Start a run with budget large enough to still be running, click **Stop**; confirm the badge transitions to **"Stopped"** (slate), no further iteration cards appear, and the Best badge remains. |
| App shell (whole app) | Reload-mid-run resilience | New behavior | Running state survives reload (no local flag) | Start an Auto Run, reload the browser tab mid-run, reopen the same session; confirm it still shows **Running** with live counters advancing and reaches a terminal state without a second manual reload. |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/backend/auto_session.py` — `_run_off_loop` helper, per-session `asyncio.Lock`, async
  lock-guarded `_save_auto_run` / `_stop_requested` / `_finish` (B1+B2 concurrency co-design) — robustness
  only; no UI surface. Observable indirectly: a "Stop" raced against a backend progress write is no
  longer dropped.
- `apps/backend/backend/auto_session_routes.py` — `AutoSessionHandle(task, lock)`, shared lock between
  the controller and `/stop`, `/stop` performing its read-modify-write under the lock. Request/response
  contracts unchanged from iter-1; no new endpoint.
- `apps/backend/tests/test_auto_session.py` — NEW regression test
  `test_stop_racing_save_auto_run_is_not_dropped` — test code, no UI surface.
- `runs/goal-session-financial_free/state/blueprint.md` — additive Notes clarification (in-browser
  scorer/loop retired; backend `RobustScorer` is the sole engine) — documentation, no UI surface.

---

## Summary

- **Frontend surfaces changed:** 12 (1 new component with 5 distinct states + 6 changed-behavior surfaces)
- **New pages/routes:** 0 (single-page app; new surface is the `AutoSessionStatusStrip` component)
- **Modified components:** `IterationPanel`, `SessionContainer`, `App`, `useBacktest` hook, `sessionApi`
  (controls in `BacktestConfigBar` / `IterationCard` / `SessionPicker` are visually unchanged but now
  derive state from backend `autoRun.status`)
- **Navigation changes:** no (no new route or nav section; Auto Run adds a session tab via the existing
  Session picker)
- **Backend-only changes:** 4
