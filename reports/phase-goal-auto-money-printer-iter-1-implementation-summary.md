# goal-auto-money-printer-iter-1 — Implementation Summary

**Phase:** goal-auto-money-printer-iter-1
**Date:** 2026-05-19
**Written by:** developer

---

## Features Implemented

- **Start a strategy search with one API call**: `POST /api/auto-sessions`
  with a strategy description, a symbol/timeframe/date-range/capital, a
  model, optional success targets, and a budget. The platform runs the whole
  "write a strategy → backtest it → review it → improve it → repeat" loop on
  the server. No browser is needed to start or drive it.
- **It shows up in the app immediately**: the moment the call returns, the
  new run appears as a session in the existing session list, exactly like a
  manual session — same look, same place.
- **Watch it progress live**: opening that session shows a status strip
  ("Automated run · iteration 2 / 3") that advances on its own, new
  iteration cards appearing as they complete, **without reloading the
  page**. When it finishes the strip shows why it stopped.
- **It always stops on its own**: the run ends as soon as either the
  success targets are met ("robust targets met") or the budget is used up
  ("budget reached"). It can never loop forever or run "one more round" past
  the limit.
- **The best strategy is marked**: a gold "★ Best" badge is placed on the
  strongest iteration, chosen by a quality measure that rewards
  walk-forward-validated, well-traded, low-drawdown strategies — not just
  the one with the biggest headline return.
- **History browsing is now trustworthy (J-02 fix)**: opening any prior run
  from history now reloads its full detail — the trades table, equity
  curve, and walk-forward panel — not just its summary.

---

## Changed Behavior

- **Opening a prior run from history**: Previously the right-hand analysis
  panel stayed stuck on the most recent run when you clicked an older one.
  Now it correctly switches to show the selected run's full trades, equity
  curve, and walk-forward results.
- **Viewing an automated session**: While a server-driven run is active the
  app treats that session as read-only and just displays it (the server is
  the single source of truth for its data). Normal manual sessions are
  completely unaffected.

---

## Backend-Only Items

- None. Every new backend capability is reflected in the existing UI: the
  headless run appears as a session, its live status and stop reason are
  shown in a status strip, and its best iteration is badged.
- (The headless run is *started* via the API by design this iteration — the
  spec defers wiring a UI "start" button to the next iteration.)

---

## Incomplete Items

- **Deliberately deferred per the phase spec (not gaps):** rewiring the
  existing in-browser "Auto Run" button to the backend and removing the old
  in-browser loop; an explicit "Stop" control/endpoint; the open-universe
  search, the AI-token/USD cost meter, staged cheap-then-expensive
  screening, and learning from past sessions. These are later iterations.
- The pre-existing, unrelated "directions cache" test failure was left as-is
  (out of scope).

---

## Config and Environment Changes

- None. No new environment variables, no new services, no database, no
  queue. The automated session reuses the existing durable file store
  (`BACKTEST_STORE_DIR`, unchanged) and the existing backtest engine.

---

## Known Limitations

- The fully automated run uses real AI and market data; on very short date
  ranges walk-forward validation may produce no windows, in which case the
  run still finishes safely on its budget and still marks a best iteration.
- Live in-browser verification of the watch-it-progress, best-badge, and
  history-reload behaviors is performed by the automated browser test step
  with tiny budgets (as the spec directs). The server side was verified
  end-to-end live: a real one-iteration run started via the API, ran on the
  server, finished with a stop reason and a marked best, and was readable in
  the app with full detail and AI suggestions.
- Backend unit/integration tests: 140 passed, 1 failed — the single failure
  is a pre-existing, out-of-scope item unrelated to this work; nothing this
  iteration added regressed the existing platform.

---

## Fixes Applied After QA (2026-05-19)

QA found three problems; all three are fixed:

1. **The app froze while an automated run was working (most serious).**
   While a server-driven run was active, the whole app became
   unresponsive — the session list wouldn't refresh and run details hung
   on "Loading…" until the run finished. Cause: the automated run was doing
   heavy data-saving work on the same thread that answers the app's
   requests. Fix: that saving work is now done on a background worker
   thread (exactly how a normal manual run already does it). The app now
   stays responsive while an automated run is in progress. A new automated
   test guards this so it cannot regress.
2. **A new automated session didn't show up until you reloaded the page.**
   The session list was only loaded once when the app opened. It now
   quietly refreshes every few seconds (and when you return to the tab),
   so a session started by the API appears in the Sessions dropdown on its
   own within a few seconds — no page reload needed. Existing sessions are
   never reordered, renamed, or lost by this.
3. **The "★ Best" badge was missing on the opened (expanded) run.** The
   gold "Best" badge showed in the compact iteration list but not when you
   opened that iteration's full detail. The same badge now also appears
   next to the strategy name in the expanded view.

These were targeted fixes only — no other behavior was changed, and the
manual-backtest, history-reload (J-02), and live-tracking (J-08) behaviors
that already worked were left intact.
