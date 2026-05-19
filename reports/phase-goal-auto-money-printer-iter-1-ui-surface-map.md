# Phase goal-auto-money-printer-iter-1 — UI Surface Map

**Phase:** goal-auto-money-printer-iter-1
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

> App is a single-page React app (no URL router). Surfaces are addressed by
> their location in the SPA: the header session-picker, and the active
> session's two-panel workstation (`SessionContainer`). "Route / Page" names
> the logical location, not a URL path.

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| Header session picker | `SessionPicker` dropdown list | Changed behavior | A headless session created via `POST /api/auto-sessions` must appear in the list automatically (J-07) | `POST /api/auto-sessions` with a tiny pinned config + `budget.max_iterations:2`; without reloading, open the header session dropdown and confirm a **new session row** with the returned `sessionId` is listed |
| Header session picker | `SessionPicker` status dot (`StatusDot`, line 27-28) | Changed behavior | Active headless run now drives the amber pulsing activity dot (`isAutoRunning` includes `headlessActive`) | While the headless run is `running`, confirm the new session's row shows the **amber pulsing dot**; after it reaches terminal, confirm the dot **stops pulsing/clears** without a page reload |
| Header session picker | `SessionPicker` best-return label | Changed behavior | Best-return now derived from lightweight completed-iteration return (no longer requires loaded heavy detail) | After ≥1 headless iteration completes, confirm the session row shows a **`+X.X%` / `-X.X%` best-return figure without opening the session** |
| Active session view | `AutoRunBar` (NEW, in `SessionContainer.tsx`, below `BacktestConfigBar`) | New component | Render live headless run status + terminal stop reason (J-08/J-09) | Open the headless session; confirm a status strip reads **"Automated run · iteration X/N" with a spinning loader**; observe X advance **without manually reloading**; at terminal confirm it switches to green **"Automated run complete · robust targets met"** or **"… budget reached · X/N iterations"** |
| Active session view | `AutoRunBar` — stopped state | New component | `stopped` terminal state styling | If a run ends in `stopped`, confirm the strip shows the **red StopCircle icon + "Automated run stopped"** (red tone) |
| Active session view | `AutoRunBar` — absent for manual sessions | New component | Strip is gated on `autoRun != null` | Open a **manual** (non-headless) session; confirm **no AutoRunBar strip** appears below the config bar (regression guard) |
| Active session, right panel | `IterationPanel` → `IterationCard` "★ Best" `BestBadge` (NEW) | New component | Mark the server-selected robust-best iteration (J-09) | After a headless run terminates, confirm exactly **one** iteration card in the right-hand history tree shows an **amber "★ Best" pill**, and it is the iteration whose id equals the session's `autoRun.bestIterationId` (not necessarily the highest raw return) |
| Active session, right panel | `IterationCard` expanded view "★ Best" badge | New component | Best badge must show in both compact tree and expanded card | Click the best iteration card to expand it; confirm the **"★ Best" pill also appears next to the strategy name in the expanded view** |
| Active session, right panel | `IterationPanel` → `IterationDetailView` (`key={selected.id}` remount) | Changed behavior | J-02 — right analysis panel must re-bind to the selected prior run | In a session with ≥2 completed runs, open the latest run's detail (note its trades), go Back, then select an **older** run; confirm the **trades table, equity curve, and walk-forward panel now show the older run's data**, not the latest run's |
| Active session, right panel | `IterationDetailView` re-fetch guard (`useBacktest.ts` lazy-detail effect) | Changed behavior | Stale `loadedDetailIdsRef` removed; re-fetch keyed on node's own `result` | Open run A (loads detail) → open run B → re-select run A; confirm A's full detail (trades/equity/WF) **still displays** and is not blocked/empty (no permanently-stale "no detail" state) |
| Active session (live) | Right-panel history tree + left activity log (live merge, `useBacktest.ts` poll effect) | Changed behavior | J-08 — new iterations + activity stream in via 2.5s poll while active | With the headless run active, **without touching the page**, confirm new **iteration cards appear in the right tree** and new **activity entries appear in the left log** as the server completes rounds; confirm polling **stops** once the run is terminal (no further new cards) |
| Active session (live) | Already-open iteration detail during live poll | Changed behavior | Poll merge must preserve lazy-loaded heavy detail (not downgrade open node) | Open one completed iteration's detail (trades visible) while the run is still active; wait through ≥1 poll cycle; confirm the **open iteration's trades/equity do NOT blank out** or revert to a loading state |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/backend/auto_session.py` — **NEW** controller + DTOs + bounded
  background loop + durable `autoRun` state machine + `POST /api/auto-sessions`
  endpoint. The endpoint has **no UI trigger element** this iteration (called
  by API/script); its *output* is surfaced through the existing session
  list/open paths (covered by the surfaces above). Classify: backend-api,
  indirect — the frontend does not call this endpoint, but consumes the
  sessions it creates.
- `apps/backend/backend/robust_objective.py` — **NEW** WFE-gated,
  min-trades-floored, drawdown-penalized scalar + `select_best`. Internal
  scoring logic; its *result* is visible only as the "★ Best" badge (tested
  above). No direct UI surface.
- `apps/backend/backend/api.py` — 2-line router mount. No UI surface.
- `apps/backend/backend/session_routes.py` — `GET /api/sessions/{id}` now
  also returns the small `autoRun` status block from `session.json`. This is
  the data the frontend consumes for `AutoRunBar` + best badge + live
  polling — its effect is fully exercised by the active-session surfaces
  above; the endpoint itself has no standalone UI.
- `apps/backend/tests/test_auto_session.py` — **NEW** test module. No UI.

---

## Summary

- **Frontend surfaces changed:** 12 (3 in the header session picker; 9 in the
  active-session two-panel view)
- **New pages/routes:** 0 (single-page app; rides the existing two-panel
  workstation — no new route/page)
- **New components:** 2 (`AutoRunBar` live status strip; `BestBadge` on
  `IterationCard`)
- **Modified components:** `SessionContainer`, `IterationPanel`,
  `IterationCard`, `useBacktest` hook (live polling + J-02 re-bind);
  `SessionPicker` is affected via derived `LiveSessionStatus`
- **Navigation changes:** no (no new links/routes; existing session picker
  surfaces the new session automatically)
- **Backend-only changes:** 5 files (auto_session controller/endpoint, robust
  objective, api router mount, session_routes autoRun passthrough, tests) —
  no standalone UI surfaces; effects covered by the surfaces above
