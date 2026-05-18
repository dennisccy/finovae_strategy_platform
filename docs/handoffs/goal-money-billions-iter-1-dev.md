# goal-money-billions-iter-1 Dev Handoff

**Phase:** goal-money-billions-iter-1
**Date:** 2026-05-18
**Agent:** developer
**Status:** complete

## What Was Built

Storage-layer invariant hardening (backend-only; no new user-facing capability).
Resolves the two iter-0 pinned storage anti-goal violations:

- **Single-file Parquet OHLCV cache** (`data/loader.py`). Replaced the per-day
  CSV cache (`_get_daily_cache_path`/`_load_from_csv`/`_save_to_csv` + the
  day-by-day loop) with **one Parquet file per (symbol, timeframe)** at
  `{cache_dir}/{safe_symbol}/{timeframe}.parquet`. No `.csv`, no per-day files.
  - **Covering-cache rule:** if the cached `[cache_min, cache_max]` span fully
    covers the requested `[start, end]`, returns the filtered slice with
    **zero Binance calls**. Empty/partial coverage fetches only the missing
    leading and/or trailing sub-range(s), merges, and rewrites the single file.
    (Liquid-pair Binance history assumed contiguous — documented in a code
    comment.)
  - **Determinism invariant preserved exactly:** dedupe-by-timestamp →
    sort-ascending → strict `[start, end]` filter, factored into
    `_postprocess()` and applied identically on the cold and warm paths so the
    returned `list[OHLCV]` is byte-identical cold vs warm.
  - **Atomic write:** merged set written to a `tempfile.mkstemp` temp file in
    the *same directory*, then `os.replace()`d onto the final path (replaces
    the old per-day `OSError`-swallow; last complete writer wins; safe under
    overlapping resolution-TF loads and the `Semaphore(1)` backtest gate).
  - **Corrupt/partial/legacy file → cache miss:** `_read_parquet_cache` wraps
    the read in try/except and returns `[]` (re-fetch) instead of crashing.
  - `clear_cache()` now globs `*.parquet` (was `*.csv`, which had silently
    become a no-op) and returns the correct count.
  - Default cache dir moved off volatile `/tmp` to a durable, CWD-independent
    `<repo>/.data/market_data` resolved from `Path(__file__)`. Transient-error
    retry behaviour preserved (3 attempts, linear backoff) via
    `_fetch_with_retry`. Removed now-dead helpers and unused imports
    (`hashlib`, `json`, `timedelta`).
- **Durable-by-default session store** (`backend/session_store.py`). `BASE_DIR`
  default (when `BACKTEST_STORE_DIR` is unset) is now
  `<repo>/.data/backtests` resolved from `Path(__file__).resolve().parents[3]`
  — absolute, not under `/tmp`, and the **same** path the runtime `.env`
  advertises, so existing on-disk sessions are not orphaned and history
  survives a process restart with no `.env`.
- **`.env.example`** — `MARKET_DATA_CACHE_DIR` and `BACKTEST_STORE_DIR` no
  longer advertise volatile `/tmp`; comments updated (no longer "CSV files").
- **Stale doc fix (secondary)** — corrected the `apps/backend/CLAUDE.md`
  "Data Caching" line that described one-Parquet-per-date-range (contradicted
  the anti-goal) to the implemented single-file-per-(symbol,tf) contract.

## Files Changed

- `apps/backend/data/loader.py` — single-file Parquet cache; covering-cache +
  partial-fetch-merge; atomic write; corrupt→re-fetch; durable default;
  `clear_cache()`→`*.parquet`; dead code/imports removed.
- `apps/backend/backend/session_store.py` — `BASE_DIR` durable default from
  `__file__` (→ `<repo>/.data/backtests`); module docstring updated.
- `apps/backend/.env.example` — durable in-repo defaults; comments updated.
- `apps/backend/CLAUDE.md` — corrected stale "Data Caching" section.
- `apps/backend/tests/test_loader.py` — **new**; 9 tests.
- `apps/backend/tests/test_session_store.py` — **new**; 3 tests.

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest -q` (asyncio_mode=auto)

Full suite: **119 passed, 1 failed** (the 1 failure is the documented
pre-existing iter-0 baseline, see Known Issues).

Per-module (post-change):

| Module | Result |
|---|---|
| `test_determinism.py` (critical invariant — unchanged) | **6 passed** |
| `test_lookahead.py` (critical invariant — unchanged) | **6 passed** |
| `test_sandbox.py` | 27 passed |
| `test_walk_forward.py` | 33 passed |
| `test_sl_tp_path_model.py` | 23 passed |
| `test_directions_cache.py` | 12 passed, **1 failed (pre-existing, out of scope)** |
| `test_loader.py` (new) | **9 passed** |
| `test_session_store.py` (new) | **3 passed** |

Lint: `.venv/bin/ruff check` on all changed source — **All checks passed**.

**Live external integration (real Binance, not mocked):** cold load
`BTCUSDT 1h` 2024-03-01..03 → 49 candles in 0.39s; identical warm re-run in
0.017s (~23× faster, **>10×** goal criterion); exactly one
`BTCUSDT/1h.parquet`, zero `.csv`; `cold == warm`; parquet mtime unchanged on
the warm run (proves zero re-fetch + zero rewrite). **PASS.**

## Known Issues

- **Pre-existing baseline failure (NOT a regression from this iteration):**
  `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  (`len(result["timeframeResults"]) == 1` → got `0`). Both
  `backend/directions_cache.py` and `tests/test_directions_cache.py` are
  **byte-identical to HEAD** (`git diff HEAD --` shows no changes) — this
  module is explicitly OUT OF SCOPE for this iteration and the iter-0 commit
  recorded `failing+1 regressed+0`. It must not be counted as a new regression.
- **Runtime `.env` is out of scope to commit** (gitignored, dev-managed). The
  runtime `.env` still sets `MARKET_DATA_CACHE_DIR=/tmp/market_data`, so at
  runtime OHLCV may live under `/tmp` until a developer updates `.env`. This is
  acceptable per the spec: the pinned OHLCV anti-goal is about *structure*
  (single Parquet, no per-day fan-out, no re-fetch on covering cache), which
  the new code satisfies regardless of directory. Runtime `.env`
  `BACKTEST_STORE_DIR` already points durably at `<repo>/.data/backtests`.
- **Legacy `/tmp/market_data` per-day CSVs are not migrated** (explicitly out
  of scope — volatile and re-fetchable). The new code never reads or converts
  them; a clean cut to the Parquet path is the intended behaviour.
- **No frontend changes.** Browser QA for J-01/J-02/J-03/J-04/J-06 is
  regression-only (see frontend handoff). `Frontend Present: yes` in the plan
  exists solely to make the DoD-mandated browser regression run.

## Suggested Next Phase

The two storage anti-goals targeted here are resolved. The remaining
code-confirmed but deferred anti-goal is the `GET /api/sessions/{id}`
eager-load (`session_routes.py:142-171` calls `read_iteration_full` per
iteration, inlining `result.json`/`rating.json`). It is a frontend+backend
session-open contract change with J-02 regression risk and warrants its own
dedicated `full`-depth iteration. The `directions_cache.py` round-trip
baseline failure could be folded in or fixed separately if directions becomes
in-scope.
