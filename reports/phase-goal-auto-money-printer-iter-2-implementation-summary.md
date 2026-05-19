# Phase goal-auto-money-printer-iter-2 — Implementation Summary

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Written by:** developer

---

## Features Implemented

- **Server-driven "Auto Run"**: Clicking "Auto Run" now launches the
  automated strategy search on the server instead of in the browser. The
  search keeps running even if you close or reload the browser tab — the
  computer doing the work is the server, not your browser.
- **Stop button that actually stops the run**: A running automated search
  can now be stopped on demand, both from the app's Stop control and via the
  API. When you stop it, it finishes cleanly: no extra strategies are tried
  after you press Stop, and the best strategy found so far stays marked with
  its "★ Best" badge.
- **Reliable, accurate status**: When you switch between sessions quickly,
  a still-running automated session always correctly shows "running" — it
  can no longer get "stuck" displaying a finished state by mistake. The
  little spinner in the session list and the status strip inside the
  session always agree.
- **Stop survives a server restart / multi-process setup**: A stop request
  is remembered durably, so the run still stops correctly even if it is
  being handled by a different server process or the server was restarted.

---

## Changed Behavior

- **"Auto Run" button**: Previously ran the search loop inside your browser
  (it stopped if you closed the tab). Now it starts a search on the server
  that continues independently; a new "Auto: …" session appears in the
  session list within a few seconds, and a note is added to the originating
  session's activity log telling you so.
- **Stop button**: Previously cancelled the in-browser loop and discarded
  its partial work. Now it cooperatively stops the server run and keeps the
  completed strategies and the best-so-far marker.
- **Manual single backtests, history browsing, the right-panel re-bind when
  selecting an older run, and "Run All" are unchanged.**

---

## Backend-Only Items

- None. Every backend capability added this phase (the stop endpoint, the
  durable stop signal) is reachable from the UI (the Stop control) and via
  the live status the app already displays.

---

## Incomplete Items

- None for this phase's scope. Open-universe search and the hard
  token/USD/wall-clock cost tracker remain intentionally **out of scope**
  (future Optimizer layer); open-universe requests are still correctly
  rejected with a clear 4xx error.

---

## Config and Environment Changes

- None. No new environment variables, no new dependencies, no datastore /
  queue / scheduler, no database, and no changes to the frozen data
  contracts. The durable stop reuses the existing session file store.

---

## Known Limitations

- After clicking "Auto Run", the new automated session appears in the
  Sessions dropdown within about 5 seconds (it is discovered by the app's
  existing background poll). To watch it, select the new "Auto: …" session
  from the list. This is the intended design for this phase.
- The live end-to-end run (real strategy generation + market data) is
  validated by the browser test pass using tiny budgets; the automated
  backend test suite uses deterministic stand-ins for speed and zero cost.
- A stopped run keeps an internal "stop requested" marker; this is harmless
  and is what makes pressing Stop again a safe no-op.

---

## Fix Notes — QA FAIL retry (2026-05-19, plain language)

QA failed the first attempt for four reasons. All are now fixed; the backend
behaviour that mattered (start, stop, best-preserved) was already correct.

1. **The app froze the session list for up to ~34 seconds while an automated
   run was active.** Cause: the automated run's number-crunching ran inside
   the web server and monopolised Python's single "lane" (the GIL), so every
   other request waited. Fix: the number-crunching now runs in a **separate
   background process** with its own lane, so the rest of the app stays
   responsive while an automated search runs. The same proven backtest engine
   is reused unchanged — only *where* it runs moved.
2. **The Stop endpoint was slow to respond (12–16 s).** Same cause as #1;
   fixed by the same change — it now responds in milliseconds.
3. **After stopping (or finishing), the on-screen status bar stayed stuck on
   "running" until the user manually reloaded the page.** Cause: if one
   status refresh failed (which the slowdown above made likely), the app
   stopped refreshing entirely. Fix: status refresh now always reschedules
   itself, so the bar reliably catches up to "stopped"/"complete" on its own.
4. **The first click on the Stop button sometimes did nothing.** Reduced the
   needless screen re-rendering that could swap the button out from under a
   click; the Stop button is now stable. Recommended for a final in-browser
   re-check.

Behaviour change for operators: an automated run now uses a small background
helper process; this is internal and invisible in the UI — a headless run
still looks and behaves exactly like before, just without freezing the app.

Tests: backend 26/26 targeted, 150 passed / 1 pre-existing-unrelated failure
(zero new regressions); frontend build clean.
