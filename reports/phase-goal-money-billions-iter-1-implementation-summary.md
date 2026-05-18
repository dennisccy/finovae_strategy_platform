# Phase goal-money-billions-iter-1 — Implementation Summary

**Phase:** goal-money-billions-iter-1
**Date:** 2026-05-18
**Written by:** developer

---

## Features Implemented

- **Single-file market-data cache**: Historical price data for a trading pair
  and timeframe (e.g. `BTCUSDT` hourly) is now stored as **one cache file per
  pair+timeframe** instead of one tiny file per calendar day. Running the same
  backtest a second time reads entirely from this local file and does **not**
  re-download anything from Binance.
- **Smart partial top-up**: If you previously ran a backtest over one date
  window and then ask for a wider window, only the genuinely missing
  start/end portion is downloaded and merged into the existing cache file —
  not the whole window again.
- **Crash-safe cache writes**: The cache file is written in a way that can
  never be observed half-written, even if two backtests run at once or the
  process is interrupted mid-write.
- **Durable history by default**: Saved sessions and run history are now kept
  in a stable in-project location by default, so they survive a server
  restart or machine reboot even when no configuration file is present.

---

## Changed Behavior

- **Repeat backtests**: Previously a warm re-run still walked a day-by-day
  cache of CSV files. Now a repeat run over an already-fetched
  pair/timeframe/date range loads from a single local file with **zero**
  Binance calls (measured live: ~23× faster than the first run).
- **Default storage locations**: Previously, with no configuration, market
  data and session history defaulted to the system temporary folder
  (`/tmp`), which is wiped on reboot. Now both default to a durable
  in-project location, so nothing is silently lost on restart.
- **"Clear cache" action**: Previously this had silently stopped deleting
  anything (it looked for the old file type). It now correctly removes the
  cache files and reports how many were deleted.

---

## Backend-Only Items

- All changes in this iteration are backend-only and intentionally invisible
  in the UI. There is no new screen, button, or data display. The user-facing
  effect is purely that repeat backtests are fast and history is not lost.

---

## Incomplete Items

- **`GET /api/sessions/{id}` eager-load** (separate anti-goal): confirmed a
  real issue during this iteration but explicitly **out of scope** here — it
  is a session-open contract change with regression risk and is deferred to
  its own dedicated iteration. Not started.
- **Legacy `/tmp/market_data` day-files**: intentionally **not migrated**
  (out of scope — that data is volatile and automatically re-downloadable).
  New code ignores the old files rather than converting them.

---

## Config and Environment Changes

- `MARKET_DATA_CACHE_DIR` — where market-data cache files live. Default
  (when unset) is now the durable in-project `.data/market_data` instead of
  `/tmp/market_data`. `.env.example` updated accordingly.
- `BACKTEST_STORE_DIR` — where session/run history lives. Default (when
  unset) is now the durable in-project `.data/backtests` instead of
  `/tmp/backtests` — the same place the project's runtime config already
  points, so existing saved history is preserved. `.env.example` updated.
- No database, schema, or migration changes (project has no database by
  design).
- Note: a developer's own runtime `.env` is not modified by this work; if it
  explicitly sets these variables, those explicit values still win.

---

## Known Limitations

- The runtime `.env` on a given machine may still point market data at
  `/tmp`; that file is developer-managed and out of scope to change here.
  The anti-goal is satisfied by the cache *structure* (one file per
  pair+timeframe, no re-fetch on a covering cache) regardless of directory.
- One pre-existing, unrelated test failure remains
  (`test_directions_cache.py::test_write_and_read_full_round_trip`). It
  exists in the iter-0 baseline, concerns a module not touched by this
  iteration, and is not a regression introduced here.
- The cache assumes Binance history for liquid pairs is contiguous (no
  interior gaps); a covering date span is treated as fully populated. This
  matches how the platform is used and is documented in the code.
