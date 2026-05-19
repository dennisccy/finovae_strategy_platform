# Phase goal-auto-money-printer-iter-2 — UI Surface Map

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## File Classification

| File | Category | UI Impact | Explanation |
|------|----------|-----------|-------------|
| `apps/frontend/src/components/SessionContainer.tsx` | frontend-direct | direct | Routes both "Auto Run" entrypoints + the Stop control to the backend; passes `isActive` into the hook; renders `AutoRunBar` |
| `apps/frontend/src/hooks/useBacktest.ts` | frontend-direct | direct | Deletes the in-browser iterate loop; adds `startAutoSession`/`stopAutoSession`; re-derives per-session `autoRun` status on mount/switch; feeds `BacktestConfigBar`, `AutoRunBar`, `SessionPicker` |
| `apps/frontend/src/lib/sessionApi.ts` | full-stack | indirect | New `startAutoSession` (`POST /api/auto-sessions`) and `stopAutoSession` (`POST /api/auto-sessions/{id}/stop`) API clients consumed by the hook |
| `apps/backend/backend/auto_session.py` | backend-api | indirect | New `POST /api/auto-sessions/{id}/stop` endpoint (consumed by the UI Stop control) + durable `stopRequested` signal that feeds the polled `autoRun` block the UI renders |
| `apps/backend/tests/test_auto_session.py` | backend-internal | none | Test suite only — no UI surface |
| `runs/.../telemetry.jsonl`, `trace/*` | backend-internal | none | Goal-mode run artifacts — no UI surface |

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| Session view (single-page app, no route change) | `BacktestConfigBar` — violet **"Auto Run (N)"** button | Changed behavior | Now calls `POST /api/auto-sessions` instead of an in-browser loop | On a session with ≥1 completed iteration that has suggestions, click **"Auto Run"**. Confirm an activity-log entry "Started a server-driven Auto Run (up to N iterations)…" appears and that the in-browser loop does NOT run (no iterations get appended to the *current* session). |
| Session view | `SessionPicker` — Sessions dropdown | Changed behavior | New backend auto-session is discovered by App.tsx's 5 s poll | After clicking "Auto Run", open the Sessions dropdown; within ~5 s a new **"Auto: …"** session appears. Select it. |
| Session view | `AutoRunBar` status strip (below config bar, server-driven sessions only) | Changed behavior | Status now authoritatively re-derived from backend on mount/switch | Open the new "Auto: …" session. Confirm `AutoRunBar` shows the spinner + "Automated run · iteration X/N" and that X advances over time. |
| Session view | Browser tab reload during a run (J-10) | Changed behavior | Run is now server-driven and survives a reload | While the "Auto: …" session is mid-run, hard-reload the browser tab, reopen the same "Auto: …" session, and confirm `currentIteration` is **higher** than before the reload and the run eventually reaches a terminal state. |
| Session view | `BacktestConfigBar` — amber **"Stop (x/N)"** button | Changed behavior | Now calls `POST /api/auto-sessions/{id}/stop` (cooperative server stop) | With a still-running "Auto: …" session open, click **"Stop"**. Confirm `AutoRunBar` flips to the red `StopCircle` + "Automated run stopped" within a few seconds, and that NO new iteration cards appear after the stop. |
| Session view | `IterationCard`/`IterationDetailView` — "★ Best" pill | Changed behavior | Best-so-far must be preserved on stop (robust objective, not raw return) | After stopping a run that had ≥1 completed iteration, confirm exactly one iteration still shows the **"★ Best"** pill and it is NOT simply the highest raw-return card if that card failed walk-forward / was over-leveraged. |
| Session view | `IterationPanel` — per-card auto-run action (`handleStartAutoRunFromCard`) | Changed behavior | Per-card "Auto Run" now starts a backend auto-session pinned to that card | Click the auto-run action on a specific completed iteration card; confirm the new "Auto: …" backend session is created (activity-log entry appears) rather than an in-browser loop starting from that card. |
| Session view | `SessionPicker` — `SessionDot` spinner + "running" badge | Changed behavior (iter-1 lesson) | Spinner now derives from the same durable `autoRun.status` as `AutoRunBar` | With every session mounted, rapidly switch between a freshly-opened still-running "Auto: …" session and other sessions. Confirm the still-running session's row keeps the pulsing amber dot + "running" badge AND its `AutoRunBar` shows "running" (no stale terminal; the two must agree). |
| Session view | `ActivityLog` (left panel) | New information | New info/error entries on Auto Run start | Click "Auto Run": confirm the info entry text names the iteration cap and the "continues even if you close/reload this tab" message. Trigger a start failure path (e.g. stop backend) and confirm an "Auto Run failed to start: …" error entry instead. |
| Session view | Stop endpoint error handling (via `stopAutoSession`) | Changed behavior | 404 / already-terminal stop must be a silent no-op in the UI | Click "Stop" on an already-stopped/terminal "Auto: …" session; confirm NO error toast/log entry surfaces and the displayed status does not regress (stays terminal). |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/backend/auto_session.py` — in-process `_CANCEL_REGISTRY`
  (module-level dict, registry lifecycle on every terminal path) — internal
  cancellation plumbing; no UI surface (its effect surfaces only as the
  `stopped` status the `AutoRunBar` already renders).
- `apps/backend/backend/auto_session.py` — durable per-round `stopRequested`
  read in the loop and worker-safe/restart-safe cooperative stop — internal
  durability mechanism; observable only as the eventual `stopped` status.
- `apps/backend/tests/test_auto_session.py` — +11 tests — no UI surface.
- `runs/goal-session-auto-money-printer/telemetry.jsonl`, `trace/*` — goal-mode
  run artifacts — no UI surface.

---

## Summary

- **Frontend surfaces changed:** 10 (Auto Run button, Stop button, per-card
  auto-run action, `AutoRunBar`, `SessionPicker` dropdown, `SessionDot`
  spinner/badge, `ActivityLog`, "★ Best" pill, mid-run reload behavior, stop
  error handling)
- **New pages/routes:** 0 (single-page app; no route or navigation change)
- **Modified components:** `SessionContainer.tsx`, `useBacktest.ts` (hook
  feeding `BacktestConfigBar`, `AutoRunBar`, `SessionPicker`); `sessionApi.ts`
  API client. No new components — all reuse existing
  `AutoRunBar`/`BacktestConfigBar`/`Loader2`/`StopCircle`/"★ Best" patterns.
- **Navigation changes:** no
- **Backend-only changes:** 4 (cancellation registry, durable stop signal,
  test suite, run artifacts)
