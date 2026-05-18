# Phase goal-money-billions-iter-1 — User-Visible Changes

**Phase:** goal-money-billions-iter-1
**Date:** 2026-05-18
**Written by:** ui-impact-analyst

> **Classification:** Backend-only, user-invisible-by-design iteration. Zero
> frontend code changed (`git diff HEAD -- apps/frontend` is empty). No new
> screen, route, component, navigation, button, field, or displayed data.
> `plan.md` sets `Frontend Present: yes` **only** to force the DoD-mandated
> browser **regression** of existing journeys — not because new UI was added.
> The changes (single-file Parquet OHLCV cache + durable-by-default session
> store) sit *beneath* existing journeys and change their backing behavior
> without changing any pixel.

---

## What Users Can Now Do

<!-- No new capability. This is invariant hardening, not a feature. -->

- **None.** No new user action or capability was added. The set of things a
  user can do (enter an NL strategy, configure symbol/timeframe/date
  range/capital, run a backtest, re-run, open a prior run from history, run
  walk-forward, view AI insights) is byte-identically the same as before.

---

## What Changed in the Visible UI

<!-- No visible UI element changed. -->

- **Nothing visually changed.** No page, component, navigation element, form
  field, label, layout, or chart was added, removed, or restyled. A user
  comparing screenshots before and after this iteration would see no
  difference on any screen.

---

## What Old Behavior Changed

These are **behavioral** changes a user can *observe by timing/persistence*,
even though no UI element changed. They are the regression-test focus.

- **Re-running the same backtest is now dramatically faster and does no
  network fetch.** Previously a repeat run over an already-fetched
  pair/timeframe/date range still walked a day-by-day cache. Now it loads
  entirely from one local cache file with **zero** Binance calls (measured
  live: cold `BTCUSDT 1h` ~0.39s → identical warm re-run ~0.017s, ≈23×
  faster). The on-screen result (metrics, equity curve, trades) is
  **identical** to the cold run — only the wait is shorter.
- **A widened date range only downloads the new portion.** If a user runs a
  backtest over one window and then a wider window for the same
  pair/timeframe, only the genuinely missing leading/trailing dates are
  fetched and merged — the previously-fetched middle is reused. Visible effect:
  the second, wider run is faster than a full cold fetch.
- **Saved sessions and run history now survive a server restart / machine
  reboot by default.** Previously, with no configuration file present, history
  defaulted to the system temp folder (`/tmp`), which is wiped on reboot — a
  user could lose prior runs silently. Now it defaults to a durable in-project
  location, so opening a prior run after a restart still works. (On the
  developer's current runtime, history was already durable via an explicit
  `.env`; this change makes durability the *default* even with no `.env`.)
- **Result content is provably stable cold vs. warm.** The same
  `(symbol, timeframe, date range)` produces a byte-identical result list
  whether served from a fresh fetch or the local cache, so a warm re-run shows
  exactly the same metrics/equity/trades as the original run (no off-by-one or
  reordering from the new storage path).

---

## Not Visible Yet

<!-- Backend capability with no UI access point. -->

- **None added.** This iteration introduces no new backend capability that
  lacks a UI. The internal `clear_cache()` correctness fix (it had silently
  become a no-op and now again deletes cache files and reports the count) is an
  internal/maintenance routine with no UI button — it was not user-invokable
  before this iteration either, so it is not a newly-hidden capability.
- **Deferred (not in this iteration, not a new capability):** the
  `GET /api/sessions/{id}` eager-load anti-goal is confirmed but explicitly
  out of scope and scheduled for its own future iteration. Nothing was built
  for it here.
