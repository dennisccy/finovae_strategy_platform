# Phase goal-financial_free-iter-2 — User-Visible Changes

**Phase:** goal-financial_free-iter-2
**Date:** 2026-05-23
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

- Users can now start a **durable, server-side optimization run** by clicking **"Auto Run"** in the
  config bar (Left panel) or the **⚡ button on any completed iteration card** (Right panel). The run
  now executes on the backend instead of inside the browser tab.
- Users can now **close the laptop, reload the tab, or navigate away** while an Auto Run is in
  progress and **the run keeps going**. Reopening the session shows it still progressing and then
  finishing — the run is no longer tied to the open browser tab.
- Users can now see a **new automated-session status strip** pinned at the top of the Right /
  Iterations panel that shows the live run state, how many improvement rounds have completed against
  the budget, elapsed vs. maximum wall-clock seconds, the reason the run stopped, and which iteration
  is the marked **Best**.
- Users can now **stop a running Auto Run for real**: clicking "Stop" issues a server-side
  cancellation, the run transitions to "Stopped", no further iterations are appended, and the
  best-so-far iteration stays marked.
- Users can now **watch new iteration cards appear live** in the iteration tree as the backend
  produces them — no manual reload is needed.

---

## What Changed in the Visible UI

- The Right / Iterations panel now shows an **Automated-session status strip** at the top with: a
  colored status badge (Queued / Running / Criteria met / Budget exhausted / Interrupted / Stopped /
  Error), a `rounds done / max` counter, an `elapsed s / max s` wall-clock counter, a "Best: <id>"
  badge for the marked-best iteration, and the stop reason on a finished run. A spinner animates while
  the run is active. The strip is **hidden entirely for a manual (non-Auto Run) session**.
- When a session has no iterations yet, the iteration panel shows a **"Waiting for the first
  iteration…"** style empty state while the backend run spins up (the strip still appears above it).
- Clicking **"Auto Run"** now **adds a new session tab and switches to it** in the Session picker
  (the run is a brand-new backend auto-session seeded from the chosen iteration's strategy prompt and
  parameters), rather than iterating in place in the browser.
- The **Auto Run / Stop controls, the Session-picker spinner, and the run progress counter** now
  reflect the backend run state. After a browser reload mid-run, the session still shows as
  "running" with the spinner, and live tracking resumes automatically.

---

## What Old Behavior Changed

- **Auto Run engine:** previously the browser ran its own in-browser optimization loop (a `while`
  loop with a duplicate in-browser scorer). Now Auto Run starts a **server-side** loop and the
  browser only watches it; the in-browser loop and its duplicate scorer have been removed.
- **"Running" indicator:** previously derived from a local in-browser flag (lost on reload). Now
  derived from the backend's `autoRun.status`, so the running state and spinner survive a reload and
  are consistent across tabs.
- **Stop button:** previously aborted only the local in-browser loop. Now sends a real server-side
  cancellation that the backend honors.
- **Auto-sessions are read-only in the browser:** a session created by Auto Run is backend-owned.
  Manually typing a follow-up prompt into a *finished* auto-session is **not persisted** (use a
  manual session to iterate by hand). No iteration is auto-selected when reopening an auto-session —
  the live tree and status strip stay in view by design.

---

## Not Visible Yet

- The **server-side stop-request serialization / off-loop persistence concurrency fix** (the B1+B2
  lock work) is internal robustness with no direct UI element — it is only observable indirectly
  (a "Stop" issued at the exact moment the backend is writing progress is no longer dropped).
- All Layer-2 capabilities (open-universe search, hard token/USD budget enforcement,
  SCREEN→PROMOTE staging, global-history warm start, leaderboard / overfit-gating UI) are **not part
  of this iteration** and have no UI yet.
