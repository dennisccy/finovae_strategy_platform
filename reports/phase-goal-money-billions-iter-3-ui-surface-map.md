# Phase goal-money-billions-iter-3 — UI Surface Map

**Phase:** goal-money-billions-iter-3
**Date:** 2026-05-18
**Written by:** ui-impact-analyst

> Single-page app (no router): the only "page" is the session view rendered by
> `App → SessionContainer` (one tab per live session). Surfaces below are the
> panels/components within that view.

---

## File Classification

| File | Category | UI Impact | Explanation |
|------|----------|-----------|-------------|
| `apps/backend/backend/session_routes.py` | full-stack (backend-api) | indirect | `GET /api/sessions/{id}` (`get_session`) response shape changed: per-iteration `read_iteration_full` → `read_iteration_meta`. Frontend consumes this on session open — root cause of the visible session-open behavior change. |
| `apps/backend/tests/test_session_routes.py` *(new)* | backend-internal | none | Response-shape / anti-goal proof tests. No UI surface. |
| `apps/frontend/src/lib/sessionApi.ts` | frontend-direct | indirect | New `fetchIterationDetail()` — typed GET of one full iteration node from the existing per-iteration endpoint; the data path behind lazy detail. |
| `apps/frontend/src/hooks/useBacktest.ts` | frontend-direct | direct | Lightweight-node hydration normalization; `loadIterationDetail` + selection/hydration lazy-load effect; write-amplification guard; exposes `detailLoading` / `detailError` / `retryDetailLoad`. Drives the detail-pane states. |
| `apps/frontend/src/components/IterationPanel.tsx` | frontend-direct | direct | New `DetailStatusPane`; renders loading / error (+Retry) / no-detail states for the selected run. User-visible. |
| `apps/frontend/src/components/SessionContainer.tsx` | frontend-direct | indirect | Plumbs `detailLoading` / `detailError` / `retryDetailLoad` from the hook into `IterationPanel`. Enables the visible states. |
| `apps/frontend/src/components/IterationCard.tsx` | frontend-direct | direct | Metrics row no longer gates on `iteration.result` — completed-run cards show return/DD/WR/SR from meta fields on lightweight nodes. |

---

## Affected UI Surfaces

<!-- "What to Test" is a specific action + expected result, not "verify it works". -->

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| Session view | Run-history list/tree (`IterationPanel` / `IterationCard` / `useBacktest` hydration) | Changed behavior | Session-open response is now lightweight (no eager `result`/`rating`) | Open/reload a session that has ≥2 completed runs. **Expect:** the full history list/tree renders (strategy names, params, timestamps, WFE badge) with nothing selected — and no run-detail data is shown until a run is clicked. |
| Session view | Completed-run card metrics row (`IterationCard`) | Changed behavior | Metrics row de-gated from `iteration.result`; now meta-sourced | On session open, look at a completed run's card **before selecting it**. **Expect:** the return / max-drawdown / win-rate / Sharpe row is visible immediately (green/red return value), not hidden until detail loads. |
| Session view | Run-detail pane — loading state (`IterationPanel` → `DetailStatusPane`, `Loader2`) | New component | Heavy detail is now lazy-fetched on selection | Select a prior run from the history list. **Expect:** a centered spinner with "Loading run detail…" appears briefly, then it is replaced by the full detail view (strategy spec, metrics, trades). [J-02 primary regression watch] |
| Session view | Run-detail pane — populated detail after lazy fetch (`IterationDetailView`) | Changed behavior | Detail now arrives via on-demand fetch+merge, not pre-inlined | Select run A (detail loads), click "Back to history", select a *different* run B, then re-select run A. **Expect:** each run's own strategy spec, metrics, and trades load correctly each time (no stale/cross-run bleed, re-selection still works). [J-02] |
| Session view | Run-detail pane — error state + Retry (`DetailStatusPane`, `AlertCircle`) | New component | Lazy fetch can fail; must not blank silently | After the session opens, make the per-iteration fetch fail (stop the backend or block `GET /api/sessions/{id}/iterations/{id}`), then select a run. **Expect:** a red "Couldn't load this run's detail" alert with the error text and a **Retry** button; the history list stays reachable via "Back to history". Restore the backend and click **Retry** → detail loads. |
| Session view | Run-detail pane — no-detail state (`DetailStatusPane`, `GitBranch`) | New component | Selecting an errored/in-progress run with no result must not crash | Select a run that has no stored result (an errored/in-progress run, if present). **Expect:** "No detailed results for this run" message — the app does not crash or blank — and "Back to history" returns to the list. |
| Session view | Run-detail pane on session open (initially-selected run, `useBacktest` hydration effect) | Changed behavior | Initially-resolved run is auto lazy-loaded so detail/results render on open | Open a session whose last-selected run was a *completed* run. **Expect:** after a brief load the run-detail/results view renders automatically (not a blank pane and not stuck on the loading spinner). |
| Session view | AI-insights auto-generate-on-open path (`useBacktest`) | Changed behavior (regression watch) | Latest run has no in-memory `result` at mount → auto-insights no longer fires on open | Open a session whose latest completed run has **no** insights. **Expect:** no automatic AI-insights generation happens just from opening. Then select that run and click request/regenerate insights → insights generate normally (J-04 path: walk-forward then insights still works on the selected, lazy-loaded run). |
| Session view | History-card "Rerun" / "improve on previous code" (`SessionContainer` handlers) | Changed behavior (regression watch) | `scriptCode` is a lazy field — empty on an un-opened old run's card | From the history card of an **old, not-yet-selected** run, trigger "Rerun" / a follow-up prompt that builds on previous code. **Expect:** previous-code context is empty (documented consequence). Then **open that run first**, trigger the same action → previous code is present and used. Confirm a brand-new strategy run (J-01) and walk-forward (J-03, reached via the opened detail view) are unaffected. |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/tests/test_session_routes.py` *(new)* — FastAPI `TestClient`
  tests proving heavy-key absence in `get_session`, the lazy per-iteration
  path still returns the full node, ordering/meta preservation, and 404
  equivalence — no UI surface affected.

> Note: `apps/backend/backend/session_routes.py` (`get_session`) is **not**
> backend-only — its lightweight response is the direct cause of the
> session-open / lazy-detail behavior changes above and is exercised by the
> J-02 browser flow. The lazy detail endpoint
> `GET /api/sessions/{id}/iterations/{id}` is unchanged but is **newly
> consumed** by the frontend (`fetchIterationDetail`).

---

## Summary

- **Frontend surfaces changed:** 1 page (the session view) — 9 distinct
  surface/state behaviors (history list, card metrics row, detail-pane
  loading / populated / error+Retry / no-detail states, on-open auto-load,
  auto-insights path, history-card rerun path).
- **New pages/routes:** 0 (single-page app; no routing).
- **Modified components:** 4 (`IterationPanel`, `SessionContainer`,
  `IterationCard`, `useBacktest` hook) + 1 lib (`sessionApi`).
- **New UI elements:** `DetailStatusPane` (loading / error+Retry / no-detail
  states in the run-detail pane).
- **Navigation changes:** no (a "Back to history" button is added *within* the
  new detail-pane status states; overall navigation/layout unchanged).
- **Backend-only changes:** 1 (`test_session_routes.py`).
- **Regression watch:** J-02 (lazy detail reload — primary), plus the
  auto-insights-on-open and history-card-rerun behavior changes. J-04 is
  verification-only (insights pane code unchanged; needs dedicated screenshot).
