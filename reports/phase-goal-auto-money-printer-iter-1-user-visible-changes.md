# Phase goal-auto-money-printer-iter-1 — User-Visible Changes

**Phase:** goal-auto-money-printer-iter-1
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

- Start a fully automated, server-side strategy search with **one API call**
  (`POST /api/auto-sessions`) — pin a strategy description, symbol, timeframe,
  date range, capital, model, success targets, and a budget. The whole
  "write strategy → backtest → walk-forward → review → improve → repeat" loop
  runs on the server with **no browser open**. (No UI button this iteration —
  the trigger is the API; see "Not Visible Yet".)
- See that automated run **appear by itself** in the existing session list
  (the session-picker dropdown in the header) the moment the API call returns —
  no refresh, no manual "new session" step. It looks and lives exactly like a
  manually created session.
- **Watch an automated run progress live** by opening that session: a status
  strip below the config bar shows "Automated run · iteration X / N" with a
  spinner, new iteration cards stream into the right-hand history tree, and the
  activity log fills in — all **without reloading the page**.
- See **why an automated run stopped**: when it finishes, the status strip
  turns green ("Automated run complete · robust targets met | budget reached ·
  X/N iterations") or red ("Automated run stopped").
- Identify the **best iteration** of an automated run at a glance: an amber
  "★ Best" pill appears on the single iteration the server selected by the
  robust walk-forward objective (not just the biggest headline return).
- **Open any prior run from history and see its full detail** — the trades
  table, equity curve, and walk-forward panel now re-bind to the run you
  click, in both manual and automated sessions (J-02 fix).

---

## What Changed in the Visible UI

- **New live status strip (`AutoRunBar`)** appears directly below the
  backtest-config bar in a session view, but **only for server-driven
  (headless) sessions**. It has three visual states: running (blue, animated
  spinner, "iteration X/N"), complete (green check, stop reason + iteration
  count), stopped (red stop icon). It is `aria-live` so screen readers
  announce transitions. Manual sessions do not show this strip.
- **New "★ Best" badge on iteration cards** (`IterationCard`) — a small amber
  pill with a filled star, shown on both the compact tree-item view and the
  expanded card view, on the iteration whose id matches the auto-session's
  server-chosen best.
- **Right-hand analysis panel now reloads on history selection** — selecting a
  prior run remounts the detail view (`IterationDetailView`, keyed by the
  selected run id) so its trades table, equity curve, walk-forward panel, and
  rating tab show the **selected** run's data instead of the previously
  displayed run's stale data.
- **Session-picker activity dot** (header dropdown) now pulses amber for an
  active headless run as well as for in-browser auto-runs and loading
  sessions; it clears when the headless run reaches a terminal state.
- **Session-picker best-return figure** now shows for a headless session
  without opening it (the list reads the lightweight per-iteration return,
  no longer requiring full detail to be loaded first).

---

## What Old Behavior Changed

- **Browsing run history (J-02 fix):** previously, clicking an older run in
  the history tree updated only the left activity/conversation panel — the
  right analysis panel (trades table + equity curve + walk-forward) stayed
  pinned to the most recently viewed run. Now the right panel correctly
  re-binds to the selected run's full detail. Manual in-memory back-and-forth
  history browsing (run A → run B → Back → A) is unchanged — A keeps its
  in-memory result, so no extra fetch and no flicker. **Re-verify the
  existing manual-history path did not regress.**
- **Viewing a server-driven (headless) session is read-only in the browser:**
  when a session has an `autoRun` block, the client stops writing its
  iteration/activity/meta artifacts back (including the page-unload save
  beacon). This prevents the browser's lightweight polled view from
  overwriting the server's full results. **Manual sessions behave exactly as
  before** — they still save normally from the browser.
- **Session list best-return derivation:** the best-return shown in the
  session picker is now computed from any completed iteration's lightweight
  return value, not only from iterations whose heavy detail is loaded. Manual
  sessions will still show the same number; the change makes headless sessions
  show a best return without being opened first.

---

## Not Visible Yet

- **No UI button to start an automated session.** Starting a headless run is
  `POST /api/auto-sessions` only this iteration. The existing in-browser
  "Auto Run" button still drives the **old browser-side** loop (untouched),
  not the new backend loop — rewiring that button is deferred to iter-2
  (J-10).
- **No UI control to stop a running headless session.** The server loop is
  cooperatively cancellable internally, but there is no stop button or stop
  endpoint exposed yet — deferred to iter-2 (J-11).
- **No token / USD budget display.** The status strip shows iteration progress
  and a budget-reached reason, but the AI-token / dollar cost meter is not
  shown (that accounting is a later iteration, J-13). Only iteration-count and
  wall-clock caps back the "budget reached" stop this iteration.
- **No open-universe / multi-config search UI.** Only the pinned-config path
  is wired; the optimizer's open search, staged screening, and
  learn-from-history are later iterations (J-12–J-16).
