# Phase goal-auto-money-printer-iter-2 — User-Visible Changes

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

- Start a **fully server-driven** automated strategy search by clicking the
  **"Auto Run"** button in the config bar (or the per-iteration-card auto-run
  action) of a session that has at least one completed iteration with
  suggestions. The search now runs on the backend, not in the browser.
- **Close or reload the browser tab while an automated run is in progress** and
  the run keeps going. Reopening the new automated session shows it still
  advancing toward a terminal state.
- **Stop a running automated search on demand** from the config-bar **"Stop"**
  button. The run transitions to a `stopped` state, no further iterations are
  added after the stop, and the best-so-far strategy keeps its "★ Best" mark.
- See a **correct, non-stale running/terminal status** for an automated session
  even when switching between sessions rapidly — a still-running session now
  always shows "running" (it can no longer get stuck showing a finished state),
  and the session-list spinner agrees with the in-session status strip.

---

## What Changed in the Visible UI

- The config-bar **"Auto Run (N)"** button (violet `Zap` button, appears when a
  completed iteration with suggestions exists) now triggers a backend
  `POST /api/auto-sessions` call instead of running a loop inside the browser.
- The config-bar **"Stop (x/N)"** button (amber `Square` button shown while a
  run is active) now calls the backend stop endpoint for the open server-driven
  session instead of aborting an in-browser loop.
- The per-iteration card **auto-run action** in the right-panel
  `IterationPanel` now starts the same backend auto-session, pinned to that
  card's iteration config.
- The **activity log** (left panel) shows a new informational entry when
  "Auto Run" is clicked: *"Started a server-driven Auto Run (up to N
  iterations). It runs on the backend and continues even if you close or reload
  this tab — a new 'Auto: …' session appears in the session list shortly."*
- A new **"Auto: …" session** appears in the **Sessions dropdown**
  (`SessionPicker`) within ~5 seconds of clicking Auto Run (discovered by the
  existing App.tsx background poll).
- The **`AutoRunBar`** status strip (slim bar directly below the config bar,
  shown only for server-driven sessions) now reliably reflects backend truth
  on session open/switch — running (spinner + "iteration X/N"), complete
  (green check + reason), or **stopped** (red `StopCircle` + "Automated run
  stopped").

---

## What Old Behavior Changed

- **"Auto Run" button:** previously ran a generate→backtest→insights iterate
  loop *inside the browser* that died if the tab was closed and operated on the
  current session. Now it creates a **separate backend auto-session** that runs
  independently of the browser; the originating session only logs an info
  entry and the new "Auto: …" session appears in the list.
- **"Stop" button:** previously aborted the in-browser loop and **discarded its
  partial iterations**. Now it cooperatively stops the *server* run and
  **keeps** all completed iterations and the robust "★ Best" marker.
- **Per-session running/terminal status:** previously could display a *stale
  terminal* state for a freshly-opened still-running session under rapid
  multi-session switching. Now each session's status is authoritatively
  re-derived from the backend on mount and on switch, so the session-list
  spinner and the `AutoRunBar` cannot disagree.
- **Auto-run progress counter on the Stop button** (`x/N`) is now sourced from
  the backend durable status (`currentIteration`/`maxIterations`) instead of
  in-browser loop counters.
- **Manual single backtests, history browsing, the J-02 right-panel re-bind
  when selecting an older run, "Run All", and the live poll are unchanged** —
  those code paths were not modified.

---

## Not Visible Yet

- None. Every backend capability added this phase (the
  `POST /api/auto-sessions/{id}/stop` endpoint and the durable stop signal) is
  reachable from the UI via the **Stop** control, and the resulting `stopped`
  state and stop reason render through the existing `AutoRunBar`.
- Out of scope this phase (intentionally not in the UI): open-universe search
  and the hard token/USD/wall-clock cost tracker (future Optimizer layer).
  Open-universe `POST /api/auto-sessions` requests are still correctly
  rejected with a 4xx — there is no UI for them and none is expected yet.
