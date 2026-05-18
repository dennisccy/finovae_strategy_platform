# goal-money-billions-iter-1 Functional Test Plan

**Phase:** goal-money-billions-iter-1
**Date:** 2026-05-18
**Frontend Present:** yes (browser regression of existing journeys — no new UI)

## Phase Goal

Migrate the OHLCV cache to a single Parquet file per `(symbol, timeframe)` (no per-day CSV fan-out, no Binance re-fetch on a covering cache) and make `session_store.BASE_DIR` durable by default (off volatile `/tmp`), while preserving determinism/no-lookahead and all existing user journeys.

## Conventions

- **Pytest tests** run from `apps/backend/`: `.venv/bin/python -m pytest tests/<file> -v` (`asyncio_mode=auto`, no decorator needed). New tests use `tmp_path` for an isolated cache/store dir and mock `BinanceClient` so `fetch_ohlcv` is an async spy and the object supports `async with` (`__aenter__`/`__aexit__`). `pyarrow` must be importable in `.venv`.
- `<repo>` = `/home/dennisccy/Git/finovae_strategy_platform`. Durable target paths: `<repo>/.data/market_data`, `<repo>/.data/backtests`.
- Browser tests require backend + frontend running and the app reachable in a browser; they verify rendered journeys, not internal fetch counts (the deterministic "zero re-fetch" proof is TC-01, not the browser).
- **Known pre-existing baseline failure (NOT a regression):** `test_directions_cache.py::test_write_and_read_full_round_trip` (iter-0 baseline, out of scope) — must not be counted as a new regression.

## Test Cases

### TC-01 — Warm re-run makes zero Binance fetches

**Type:** api (pytest — `tests/test_loader.py`, new)
**Preconditions:** `OHLCVLoader` with `cache_dir=tmp_path`, `BinanceClient.fetch_ohlcv` patched as an async spy returning a fixed synthetic OHLCV list.

**Steps:**
1. `await loader.load("BTCUSDT","1h",start,end)` (cold) — populates the Parquet cache.
2. Reset/inspect the spy; `await loader.load("BTCUSDT","1h",start,end)` again with the identical window.

**Expected outcome:** First load invokes `fetch_ohlcv` ≥1×; the second load invokes it 0×.
**Pass criteria:** `fetch_ohlcv.call_count == 0` for the second `load()` over a fully-covered window (deterministic assertion, not a wall-clock ratio).

---

### TC-02 — Cold vs warm OHLCV list is byte-identical (determinism invariant)

**Type:** api (pytest — `tests/test_loader.py`)
**Preconditions:** Same as TC-01; a *fresh* `OHLCVLoader` instance pointed at the same `tmp_path` for the warm read.

**Steps:**
1. Cold `load(...)` → capture `cold_list`.
2. New loader instance, same inputs → warm `load(...)` → capture `warm_list`.

**Expected outcome:** Lists are equal field-by-field, including tz-aware UTC timestamps surviving the Parquet round-trip, dedupe→sort-ascending→strict `[start,end]` filter preserved.
**Pass criteria:** `cold_list == warm_list` (length, order, every OHLCV field, timestamp tzinfo == UTC).

---

### TC-03 — On-disk: exactly one Parquet per (symbol,tf), zero per-day CSV/dated files

**Type:** api (pytest — `tests/test_loader.py`)
**Preconditions:** Isolated `cache_dir=tmp_path`; one or more `load()` calls completed.

**Steps:**
1. Run `load("BTCUSDT","1h",start,end)`.
2. Walk `tmp_path` recursively and enumerate files.

**Expected outcome:** Exactly one `*.parquet` for `BTCUSDT`/`1h` (e.g. `BTCUSDT/1h.parquet`); no `*.csv` and no per-calendar-day/dated files anywhere under `tmp_path`.
**Pass criteria:** `len(rglob("*.parquet")) == 1` for the pair+tf **and** `rglob("*.csv") == []` **and** no `YYYY-MM-DD`-named files. (Validated only in the isolated tmp dir — legacy `/tmp/market_data` CSVs are out of scope and must not be inspected.)

---

### TC-04 — Partial coverage fetches only the missing sub-range(s) and merges

**Type:** api (pytest — `tests/test_loader.py`)
**Preconditions:** Parquet pre-seeded to cover an interior window `[d2, d4]`; request the wider `[d1, d5]`.

**Steps:**
1. Seed cache for `[d2,d4]` (one prior `load`).
2. Reset the fetch spy; `await loader.load(symbol,tf,d1,d5)`.
3. Inspect spy call args.

**Expected outcome:** Only the missing leading `[d1,d2)` and trailing `(d4,d5]` sub-range(s) are fetched and merged into the single Parquet — never the whole `[d1,d5]`.
**Pass criteria:** Fetch call args cover only the gap sub-range(s) (no call spanning the full window); returned list covers `[d1,d5]`, deduped and sorted; still one Parquet file.

---

### TC-05 — Corrupt/partial Parquet → cache miss + re-fetch, no crash

**Type:** api (pytest — `tests/test_loader.py`)
**Preconditions:** A valid cache Parquet path overwritten with truncated/garbage bytes.

**Steps:**
1. Run a normal `load()` to create the Parquet.
2. Overwrite the Parquet file with non-Parquet bytes.
3. `await loader.load(...)` again with the spy active.

**Expected outcome:** `load()` does not raise; the corrupt file is treated as a cache miss, data is re-fetched, and the Parquet is rewritten valid; a subsequent warm load reads cleanly.
**Pass criteria:** No exception; `fetch_ohlcv` called on the corrupt-cache load; following load returns the correct list with `fetch_ohlcv.call_count == 0`.

---

### TC-06 — `clear_cache()` deletes Parquet file(s) and returns the correct count

**Type:** api (pytest — `tests/test_loader.py`)
**Preconditions:** Cache populated with N Parquet files (≥2 distinct (symbol,tf) pairs).

**Steps:**
1. Populate cache via N loads across distinct pairs/timeframes.
2. Call `loader.clear_cache()`.

**Expected outcome:** All `*.parquet` removed; `clear_cache()` globs `*.parquet` (not `*.csv`, so it is not a silent no-op).
**Pass criteria:** Return value `== N`; `rglob("*.parquet") == []` afterward.

---

### TC-07 — Loader default cache dir is absolute, not under `/tmp`, CWD-independent

**Type:** api (pytest — `tests/test_loader.py`)
**Preconditions:** `MARKET_DATA_CACHE_DIR` unset (`monkeypatch.delenv`); process CWD changed to an unrelated tmp dir.

**Steps:**
1. `monkeypatch.delenv("MARKET_DATA_CACHE_DIR", raising=False)`; `monkeypatch.chdir(tmp_path)`.
2. Instantiate `OHLCVLoader()` (no `cache_dir` arg).
3. Inspect `loader.cache_dir`.

**Expected outcome:** Default is an absolute durable in-repo path derived from `Path(__file__)`, not CWD-relative, not under `/tmp`.
**Pass criteria:** `loader.cache_dir.is_absolute()` is True; `"tmp"` not in `cache_dir.parts`; path resolves to `<repo>/.data/market_data` regardless of CWD.

---

### TC-08 — `session_store.BASE_DIR` default is absolute, not `/tmp`, resolves to `<repo>/.data/backtests`

**Type:** api (pytest — `tests/test_session_store.py`, new)
**Preconditions:** `BACKTEST_STORE_DIR` unset; module reloaded so the import-time default is recomputed.

**Steps:**
1. `monkeypatch.delenv("BACKTEST_STORE_DIR", raising=False)`.
2. `importlib.reload(backend.session_store)`.
3. Inspect `session_store.BASE_DIR`.

**Expected outcome:** Default derived from `Path(__file__)` (not CWD); not volatile.
**Pass criteria:** `BASE_DIR.is_absolute()` is True; `"tmp"` not in `str(BASE_DIR)`; `BASE_DIR` resolves exactly to `<repo>/.data/backtests` (same location runtime `.env` advertises — existing on-disk sessions not orphaned).

---

### TC-09 — Session store survives a simulated restart (write → reload → read-back)

**Type:** api (pytest — `tests/test_session_store.py`)
**Preconditions:** `BACKTEST_STORE_DIR` set to `tmp_path`; module reloaded.

**Steps:**
1. Point store at `tmp_path`, reload; `write_session_meta(...)` and `write_iteration(...)` with known content.
2. Simulate a restart: `importlib.reload(session_store)` (still resolving the same `tmp_path`).
3. `read_session_meta(...)` and `read_iteration_full(...)`.

**Expected outcome:** Written session/iteration data is read back intact after the simulated process restart.
**Pass criteria:** Round-tripped meta + iteration (prompt, strategy, result/rating) equal what was written.

---

### TC-10 — Determinism & lookahead invariants pass unchanged

**Type:** api (pytest)
**Preconditions:** Implementation complete.

**Steps:**
1. `.venv/bin/python -m pytest tests/test_determinism.py tests/test_lookahead.py -v`.

**Expected outcome:** Both invariant suites pass with no source modification to the test files.
**Pass criteria:** Exit code 0; 0 failures; pass counts recorded verbatim in the dev handoff.

---

### TC-11 — No new regressions in the existing backend suite

**Type:** api (pytest)
**Preconditions:** Implementation complete.

**Steps:**
1. `.venv/bin/python -m pytest tests/test_sandbox.py tests/test_walk_forward.py tests/test_sl_tp_path_model.py tests/test_directions_cache.py -v`.

**Expected outcome:** No new failures introduced by this iteration.
**Pass criteria:** Only the documented pre-existing baseline failure `test_directions_cache.py::test_write_and_read_full_round_trip` may fail; every other test passes; no new failure attributable to the Parquet/session-store change.

---

### TC-12 — `.env.example` no longer advertises volatile `/tmp` or "CSV files"

**Type:** artifact
**Preconditions:** None.

**Steps:**
1. Read `apps/backend/.env.example`.

**Expected outcome:** `MARKET_DATA_CACHE_DIR` and `BACKTEST_STORE_DIR` point to durable in-repo defaults (not `/tmp/market_data` / `/tmp/backtests`); the `# Directory for caching market data as CSV files` comment is corrected (no longer "CSV").
**Pass criteria:** No `/tmp/market_data` or `/tmp/backtests` literal in the file; comment text no longer says "CSV files".

---

### TC-13 — Dead per-day code removed; cache contract correct in source

**Type:** artifact
**Preconditions:** None.

**Steps:**
1. Read `apps/backend/data/loader.py` and `apps/backend/backend/session_store.py`.

**Expected outcome:** Per-day helpers (`_get_daily_cache_path`, `_load_from_csv`, `_save_to_csv`, the day-by-day loop) and now-unused imports (`hashlib`, `json`, `timedelta` if unused) are removed; `clear_cache()` globs `*.parquet`; atomic write uses temp-file-in-same-dir + `os.replace()`; covering-cache assumption documented in a comment; loader constructor docstring and `session_store` module docstring no longer say `/tmp`.
**Pass criteria:** No `.csv` write path or per-day path code remains; no leftover unused imports from this change; `os.replace` used for the Parquet write; docstrings updated.

---

### TC-14 — Dev handoff exists with explicit pytest counts

**Type:** artifact
**Preconditions:** Implementation complete.

**Steps:**
1. Check `docs/handoffs/goal-money-billions-iter-1-dev.md` exists.

**Expected outcome:** Handoff present with What Was Built / Files Changed / Tests Run / Known Issues / Suggested Next Phase, including explicit pass/fail counts for `test_determinism.py`, `test_lookahead.py`, `test_loader.py`, `test_session_store.py`.
**Pass criteria:** File exists; the four pytest count lines are present and concrete (numbers, not "passes").

---

### TC-15 — J-01: Run a backtest from natural language (target)

**Type:** browser
**Preconditions:** Backend + frontend running; app open in browser; OpenAI key configured.

**Steps:**
1. Enter "Buy when RSI crosses below 30, sell when it crosses above 70".
2. Set symbol `BTCUSDT`, timeframe `1h`, a fixed date range, initial capital.
3. Submit and wait for completion.

**Expected outcome:** Results panel renders non-empty metrics, an equity curve, and a trades table; a new `run_id` appears in history.
**Pass criteria:** Metrics non-empty, equity chart drawn, trades table populated, and a new history entry/`run_id` is visible.

---

### TC-16 — J-06: Warm-cache re-run works end-to-end (target)

**Type:** browser
**Preconditions:** TC-15 completed for the same `BTCUSDT`/`1h`/date range.

**Steps:**
1. Re-run the identical strategy with the same symbol/timeframe/date range/capital.
2. Wait for results.

**Expected outcome:** The second run completes without error, renders metrics + equity curve + trades, and appears in history (warm local-Parquet path works end-to-end).
**Pass criteria:** Second run renders fully and a second history entry appears; no error state. (Deterministic no-re-fetch proof is TC-01.)

---

### TC-17 — J-02: Inspect and browse run history (must-still-pass)

**Type:** browser
**Preconditions:** ≥1 completed backtest in history.

**Steps:**
1. Open a prior run from the history list.

**Expected outcome:** The selected run's strategy spec, metrics, and trades reload into the detail view (session store reads correctly post-migration).
**Pass criteria:** Spec + metrics + trades for the selected run render correctly.

---

### TC-18 — J-03: Walk-forward validation (must-still-pass)

**Type:** browser
**Preconditions:** A completed iteration open in its detail view.

**Steps:**
1. Set IS/OOS window lengths.
2. Click "Run Walk-Forward".

**Expected outcome:** A WFE badge (green ≥0.5 / yellow 0.3–0.5 / red <0.3), a per-window table, and a combined OOS equity curve appear.
**Pass criteria:** All three elements render with consistent values.

---

### TC-19 — J-04: AI insights (must-still-pass)

**Type:** browser
**Preconditions:** A completed run; OpenAI key configured.

**Steps:**
1. Request insights on a completed run.

**Expected outcome:** ≥1 ranked improvement suggestion renders; OOS-aware when walk-forward data exists.
**Pass criteria:** At least one ranked suggestion is displayed without error.

---

## Summary

Total test cases: **19**

| Type | Count | IDs |
|------|-------|-----|
| api (pytest) | 11 | TC-01 … TC-11 |
| artifact | 3 | TC-12, TC-13, TC-14 |
| browser | 5 | TC-15 … TC-19 |

**Spec coverage:** DoD #1 → TC-15/16; DoD #2 → TC-17/18/19; DoD #3 (anti-goals) → TC-03/07/08/12; DoD #4 (determinism) → TC-02/10; DoD #5 (no regression) → TC-11; DoD #6 (handoff) → TC-14. TESTING REQUIREMENTS error cases → TC-04 (partial coverage), TC-05 (corrupt Parquet). New test modules → TC-01–09. Dead-code/surgical-change rule → TC-13.
