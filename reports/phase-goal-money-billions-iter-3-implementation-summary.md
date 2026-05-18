# Phase goal-money-billions-iter-3 — Implementation Summary

**Phase:** goal-money-billions-iter-3
**Date:** 2026-05-18
**Written by:** developer

---

## Features Implemented

- **Faster session opening**: Opening or reloading a session no longer makes the
  server read and parse every past run's full results, ratings, equity curve,
  and trade log. It now reads only a small summary per run, so a session with
  many heavy runs opens without the server churning through every run's full
  payload.
- **On-demand run detail**: When you click a run in the history list, the app
  fetches that run's full strategy, metrics, and trades just for that run, and
  shows them in the detail view as before.
- **Clear loading and error feedback**: The run-detail pane now shows a brief
  "Loading run detail…" spinner while a run's full data is being fetched, and a
  clear error message with a Retry button if that fetch fails — instead of a
  blank panel.

---

## Changed Behavior

- **Opening a session**: Previously the server assembled every run's complete
  data when you opened a session. Now it returns a lightweight list and the
  full data for a run is loaded the moment you select that run. To the user the
  history list and detail view look the same, with a short loading indicator on
  selection.
- **Automatic insights on session open**: Previously, opening a session could
  auto-generate AI insights for the most recent run if it had none. Now insights
  are generated when you request them on a selected run (the run's data is
  loaded first). This avoids unexpected paid AI calls just from opening a
  session; requesting/regenerating insights still works exactly as before.
- **"Rerun" / follow-up-from-previous from a history card**: Re-running or
  building a new prompt "on top of" an older run now expects that run to be
  opened (selected) first, because a run's strategy code is loaded on demand.
  Running a brand-new strategy and walk-forward validation (opened from the run
  detail view) are unaffected.

---

## Backend-Only Items

- None. The backend change (lightweight session-open response) is fully
  reflected in the UI via the lazy detail fetch and the new loading/error
  states.

---

## Incomplete Items

- None. All in-scope spec items are implemented. J-04 (AI insights are
  OOS-aware after a walk-forward run) was **verification-only by design** — no
  code change was required or made; it must be confirmed by browser-QA with a
  dedicated, distinct insights-pane screenshot.

---

## Config and Environment Changes

- None. No new environment variables, settings, migrations, or storage layout
  changes. (`BACKTEST_STORE_DIR` and the Parquet/durable-store behavior are
  untouched.)

---

## Known Limitations

- The repository has no ESLint configuration, so `npm run lint` cannot run;
  type checking (`tsc`) and the production build were used to verify the
  frontend instead. This is a pre-existing repo condition, not introduced by
  this work.
- One backend test (`test_directions_cache.py::test_write_and_read_full_round_trip`)
  fails. It is a **pre-existing baseline failure** unrelated to this work
  (confirmed failing on a clean checkout with this iteration's change removed)
  and is out of scope for this iteration.
- There is no automated frontend test harness in the project; the lazy-load-on-
  selection behavior is validated by the browser run-history journey (J-02)
  rather than a unit test.
- Re-running an old run, or starting a new prompt that builds on an old run,
  from a history card now requires opening that run first (its code is loaded
  on demand). This is an intended consequence of not pre-loading every run's
  heavy data on session open.
