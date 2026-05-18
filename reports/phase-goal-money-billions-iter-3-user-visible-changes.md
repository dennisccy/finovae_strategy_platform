# Phase goal-money-billions-iter-3 — User-Visible Changes

**Phase:** goal-money-billions-iter-3
**Date:** 2026-05-18
**Written by:** ui-impact-analyst

---

> **Phase intent:** No new feature. This iteration resolves the
> eager-load anti-goal: opening a session no longer makes the backend parse
> every past run's full results/ratings/trades. The full data for a run is now
> fetched on demand when that run is selected, with explicit loading/error
> feedback. J-04 (AI insights are OOS-aware) is **verification-only — no code
> changed**. So "what users can do" is largely unchanged by design; what
> changed is *how* the session view loads and what feedback it shows.

---

## What Users Can Now Do

<!-- This phase adds no new feature. These are the user-perceptible differences. -->

- Open or reload a session that has many past runs **without waiting on the
  backend to assemble every run's full data** — the history list/tree appears
  from lightweight summaries, so a heavy-history session opens faster.
- See a clear **"Loading run detail…" spinner** in the run-detail pane while a
  selected run's strategy, metrics, and trades are being fetched (previously
  detail was always pre-loaded so there was no wait and no indicator).
- **Recover from a failed detail load**: if a selected run's detail fails to
  fetch, the detail pane shows an explicit error message with a **Retry**
  button instead of going blank, and the history list stays reachable via a
  "Back to history" button.

---

## What Changed in the Visible UI

- The **run-detail pane** (right side of the session view) now has three new
  states it can show on run selection, each with a "Back to history" button:
  - **Loading:** centered spinner with "Loading run detail…" and the sub-text
    "Fetching this run's strategy, metrics, and trades."
  - **Error:** red `AlertCircle` alert "Couldn't load this run's detail" with
    the error message and a **Retry** button.
  - **No detail:** "No detailed results for this run" message for a selected
    errored/in-progress run (it no longer risks a silent blank pane or crash).
- The **run-history cards** (`IterationCard`) still show the metrics row
  (return / max-drawdown / win-rate / Sharpe) for completed runs, now sourced
  from lightweight summary fields — so the metrics appear immediately on
  session open even before that run's full detail is loaded.
- No layout restructure: the two-panel session view (history left / detail
  right) and all existing controls are unchanged.

---

## What Old Behavior Changed

<!-- Regression-relevant: testers must re-verify these. -->

- **Opening / reloading a session:** previously the backend inlined every
  run's complete result/rating/trades into the session-open response. Now it
  returns a lightweight list and each run's full data is fetched the moment
  that run is selected. To the user the history list and detail view look the
  same, with a short loading indicator added on selection. The
  initially-selected run (restored as selected on open) is auto-loaded so the
  detail/results view still renders on open.
- **Automatic AI insights on session open:** previously, opening a session
  could auto-generate AI insights for the most recent completed run if it had
  none. That auto-fire no longer happens on open (the latest run has no
  in-memory result at mount). Insights are now generated only when the user
  requests/regenerates them on a selected run. Requesting/regenerating insights
  itself works exactly as before. (Intended; avoids surprise paid AI calls on
  every open.)
- **"Rerun" and "improve on previous code" from a history card:** these now
  require the source run to be **selected (opened) first**, because a run's
  strategy code is part of the lazily-loaded heavy detail. Re-running or
  building a follow-up prompt on top of an *old, un-opened* run from its
  history card will have empty "previous code" context until that run is
  opened. Running a brand-new strategy and running walk-forward (reached via
  the run-detail view) are unaffected.

---

## Not Visible Yet

- None new. The backend lightweight-session-open change is fully reflected in
  the UI through the new on-demand detail fetch and the loading/error/no-detail
  states. The per-iteration detail endpoint already existed; this phase wires
  the frontend to consume it on selection.
- **J-04 context (no UI delta):** the AI-insights pane is **unchanged code**
  this iteration — J-04 ("suggestions are OOS-aware after a walk-forward run")
  is verification-only. There is no new insights UI; QA must confirm OOS/
  walk-forward/WFE-aware suggestions by running walk-forward then requesting
  insights on the selected run and capturing a **dedicated, distinct
  insights-pane screenshot** (not a duplicate of the J-03 walk-forward panel).
