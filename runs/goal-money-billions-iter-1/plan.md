# goal-money-billions-iter-1 Execution Plan

Storage-layer invariant hardening: single-file Parquet OHLCV cache + durable-by-default
session store. Backend-only; no new user-facing capability. Implements goal.md Vision
(L13–15) / Success Criteria (L41–46) and resolves two iter-0 pinned anti-goal violations
(per-day CSV under `/tmp`; `BACKTEST_STORE_DIR` `/tmp` default).

## Goal Alignment

- **Advances goal:** directly satisfies the OHLCV single-Parquet anti-goal and the
  `BACKTEST_STORE_DIR` durable-default anti-goal (goal.md L159–163). Does not duplicate
  prior work — iter-0 was verify-only (zero code changes).
- **No drift / no contradiction with goal.md.** One internal tension noted below
  (spec metadata `Frontend Present: no` vs. DoD mandating browser regression of 5
  journeys) — resolved as `Frontend Present: yes` so the mandatory browser QA actually
  runs. See "Frontend Present" rationale.
- **Scope discipline:** explicitly excludes J-05 frontend wiring, the
  `GET /api/sessions/{id}` eager-load fix, legacy `/tmp/market_data` CSV migration,
  `directions_cache.py`, and any `shared/contracts.py` change — all correctly deferred
  by the spec. The plan honors these exclusions.

## What to Build

- **`apps/backend/data/loader.py` — single Parquet file per (symbol, timeframe).**
  Replace the per-day CSV cache (`_get_daily_cache_path`, `_load_from_csv`,
  `_save_to_csv`, the day-by-day loop in `load()`) with one file:
  `{cache_dir}/{safe_symbol}/{timeframe}.parquet`. No `.csv`, no per-day files.
  - **Covering-cache rule:** read existing Parquet (if any). If `[start_date, end_date]`
    is fully within the cached timestamp span → return the filtered slice with **zero
    Binance calls**. If empty/partially covering → fetch only the missing leading/trailing
    sub-range(s), merge, rewrite the single Parquet. Assume contiguous Binance history
    for liquid pairs (no interior gaps) — document this in a code comment.
  - **Determinism invariant (critical):** preserve the existing post-processing
    **exactly** — dedupe by timestamp → sort ascending → filter strictly to
    `[start_date, end_date]`. Returned `list[OHLCV]` must be byte-identical cold vs warm.
  - **Atomic write:** write to a temp file *in the same directory* as the target, then
    `os.replace()` onto the final path (atomic on same filesystem). Replaces the old
    per-day `OSError`-swallow approach.
  - **Corrupt/partial Parquet → cache miss:** wrap `read_parquet` in try/except; on
    failure treat as empty cache and re-fetch (never a hard crash).
  - `clear_cache()` must glob `*.parquet` (not `*.csv`) and return the correct count.
  - Default cache dir off `/tmp`: `os.getenv("MARKET_DATA_CACHE_DIR", <durable>)` where
    `<durable>` is resolved from `Path(__file__)` (CWD-independent) →
    `Path(__file__).resolve().parents[3] / ".data" / "market_data"` (i.e. `<repo>/.data/market_data`).
    Update the constructor docstring (currently says "or /tmp").
  - Remove now-dead helpers and unused imports (`hashlib`, `json`, and `timedelta` if it
    becomes unused after the day loop is removed). Keep `_ohlcv_list_to_df` /
    `_df_to_ohlcv_list` (reused for Parquet). Verify `pyarrow` is importable in `.venv`.
- **`apps/backend/backend/session_store.py:26` — durable default.**
  `BASE_DIR = Path(os.environ.get("BACKTEST_STORE_DIR", <durable>))` where `<durable>` =
  `Path(__file__).resolve().parents[3] / ".data" / "backtests"` → must resolve to
  `<repo>/.data/backtests` (the **same** path runtime `.env` advertises, so existing
  on-disk sessions are not orphaned). `BASE_DIR` is import-time — derive the default in a
  way the test can assert (e.g. via `importlib.reload` with `BACKTEST_STORE_DIR` cleared).
  Also update the module docstring line that says "default: /tmp/backtests".
- **`apps/backend/.env.example`** — change `MARKET_DATA_CACHE_DIR=/tmp/market_data` and
  `BACKTEST_STORE_DIR=/tmp/backtests` to the durable in-repo defaults; update the
  `# Directory for caching market data as CSV files` comment (no longer CSV).
- **`tests/test_loader.py`** (new) and **`tests/test_session_store.py`** (new) — see
  Key Test Scenarios.
- Optional (secondary, not a DoD blocker): correct the stale "Data Caching" line in
  `apps/backend/CLAUDE.md` (it describes one-Parquet-per-date-range, which contradicts
  the anti-goal). Authoritative contract = `docs/goal.md`.

## Agents Required

- developer: yes — implement loader Parquet migration, session_store durable default,
  `.env.example`, and the two new test modules (TDD: write the new tests first).
- backend-data: yes — this is a data/persistence-layer change.
- frontend-ux: no — zero frontend code changes, no UI evolution.

## Frontend Present

yes

Frontend Present: yes

> **Rationale (documented decision):** there is **no UI evolution** and **no frontend
> code change** — this is backend-only invariant hardening. However, the spec DoD and
> TESTING REQUIREMENTS *mandate* browser-qa-agent regression of J-01, J-02, J-03, J-04,
> J-06 through the running UI (J-06 must show a 2nd identical run completing and
> appearing in history). `qa-phase.sh` machine-reads this line to decide whether to run
> Chrome MCP checks; marking `no` would skip the DoD-required browser regression and
> make the iteration unverifiable. Therefore `yes`. The spec's goal-mode metadata
> `Frontend Present: no` reflects "no UI *added*"; this plan's `yes` reflects "browser
> verification *required*". Browser QA here is **regression-only**, not new-feature UI.

## Files to Create/Modify

- `apps/backend/data/loader.py` — replace per-day CSV cache with single-file Parquet per
  (symbol, tf); covering-cache + partial-fetch-merge; atomic write; durable default;
  `clear_cache()` → `*.parquet`; prune dead code.
- `apps/backend/backend/session_store.py` — `BASE_DIR` default derived from `__file__` →
  `<repo>/.data/backtests`; fix docstring.
- `apps/backend/.env.example` — durable defaults for `MARKET_DATA_CACHE_DIR` /
  `BACKTEST_STORE_DIR`; fix the "CSV files" comment.
- `apps/backend/tests/test_loader.py` — **new**; warm = zero fetch, cold==warm
  equivalence, on-disk single-Parquet/zero-CSV, `clear_cache()`, partial-coverage merge,
  corrupt-Parquet → re-fetch, durable-default-path assertion.
- `apps/backend/tests/test_session_store.py` — **new**; default not under `/tmp` &
  absolute; write→simulated-restart→read-back round-trip.
- `docs/handoffs/goal-money-billions-iter-1-dev.md` — **new**; required dev handoff
  (report explicit pytest counts for `test_determinism.py`, `test_lookahead.py`,
  `test_loader.py`, `test_session_store.py`).
- `apps/backend/CLAUDE.md` — optional stale-doc fix (secondary; not a DoD blocker).

## UI Evolution

- **None.** No new user-facing capability, no new information displayed, no new user
  actions, no UI surface or navigation changes. User-invisible by design: identical UI
  and journeys; the only behavioral guarantee is that a warm re-run provably hits the
  local Parquet cache (no Binance re-fetch) and run history survives a restart. Browser
  QA is regression verification of existing journeys, not validation of new UI.

## Visual Requirements

- **None** (no frontend changes). Browser QA reuses the existing two-panel UI to
  re-verify existing journeys; no component/layout/effect/state work in this iteration.

## Key Test Scenarios

Unit/integration (new — use `tmp_path` for an isolated cache/store dir; `asyncio_mode`
is `auto`, no decorator needed; mock `BinanceClient.fetch_ohlcv` as an async spy and
support `async with`):

- **Warm = zero fetch:** second `load(symbol, tf, start, end)` over a cached-covering
  window makes **zero** `BinanceClient.fetch_ohlcv` calls (assert call count == 0 on the
  2nd load — deterministic, stronger than a wall-clock ratio).
- **Cold == warm equivalence:** the `list[OHLCV]` returned cold equals the list returned
  warm for identical inputs (determinism invariant; field-wise equality incl. tz-aware
  timestamps surviving the Parquet round-trip).
- **On-disk shape:** after a load, exactly **one** `*.parquet` exists for the pair+tf and
  **zero** per-day `*.csv`/dated files are created (assert within the isolated tmp dir).
- **Partial coverage:** a window only partially covered fetches **only** the missing
  sub-range(s) and merges — not the whole window (assert fetch call args/count).
- **Corrupt Parquet → re-fetch:** a truncated/garbage `.parquet` is treated as a cache
  miss and re-fetched, not a hard crash.
- **`clear_cache()`** deletes the Parquet file(s) and returns the correct count.
- **Durable default path:** with `MARKET_DATA_CACHE_DIR` unset the loader default is
  absolute and not under `/tmp`; with `BACKTEST_STORE_DIR` unset
  `session_store.BASE_DIR` is absolute, not under `/tmp`, and resolves to
  `<repo>/.data/backtests`.
- **Session store restart round-trip:** write a session/iteration, re-resolve the store
  fresh (simulated restart via `importlib.reload`), read it back intact.
- **Invariant regression:** `tests/test_determinism.py` and `tests/test_lookahead.py`
  pass **unchanged**; existing suite (`test_sandbox.py`, `test_walk_forward.py`,
  `test_sl_tp_path_model.py`, `test_directions_cache.py`) shows no new regressions
  (note: `test_directions_cache.py::test_write_and_read_full_round_trip` is a
  **pre-existing** iter-0 baseline failure, out of scope — must not be counted as a new
  regression).

Browser (regression + target — verify by journey ID through the running UI):

- **J-01 (target):** NL strategy + `BTCUSDT`/`1h`/date range/capital → results panel
  shows non-empty metrics, equity curve, trades table, and a new `run_id` in history.
- **J-06 (target):** identical second run completes, renders metrics/equity/trades, and
  appears in history (warm local-Parquet path works end-to-end).
- **J-02, J-03, J-04 (must-still-pass):** open a prior run (spec/metrics/trades reload);
  walk-forward yields WFE badge + per-window table + combined OOS curve; AI insights
  render ≥1 ranked suggestion.

## Risks / Assumptions (documented, not blocking)

- **Highest regression risk:** J-01 and J-06 (loader path) and J-02 (reads the session
  store) — these are the watch items per iter-0 lessons.
- **Path-index correctness is the likely failure point** (spec NOTES flag it): both
  `loader.py` and `session_store.py` sit at depth `apps/backend/<pkg>/file.py`, so
  `Path(__file__).resolve().parents[3]` is `<repo>`. The session-store default **must**
  land on `<repo>/.data/backtests` (existing on-disk sessions live there) — a test
  asserts the resolved path to catch an off-by-one in `parents[N]`.
- **Runtime `.env` is out of scope to commit** (gitignored, dev-managed). Runtime
  `.env` currently sets `MARKET_DATA_CACHE_DIR=/tmp/market_data`, so at runtime OHLCV
  may still live under `/tmp` until a developer updates `.env` manually — **acceptable**:
  the pinned OHLCV anti-goal is about *structure* (single Parquet, no per-day fan-out,
  no re-fetch on covering cache), which the new code satisfies regardless of directory.
  `BACKTEST_STORE_DIR` in runtime `.env` already points durably at `<repo>/.data/backtests`.
- **On-disk "zero CSV" verification scope:** the legacy ~29,182 `/tmp/market_data` CSVs
  are out of scope to migrate; the "exactly one parquet / zero per-day csv" assertion is
  validated in the test's **isolated clean cache dir**, not against the polluted
  `/tmp/market_data`. Browser-QA should verify the Parquet cache path against a clean
  cache dir (or confirm no *new* CSV is written) — a raw `ls /tmp/market_data` will
  still show legacy CSVs and must not be misread as a failure.
- **Concurrency:** distinct (symbol, tf) → distinct files; same-file overlap (resolution
  TF + strategy TF, `Semaphore(1)` backtests) is safe via `os.replace()` (no torn read;
  last complete writer wins) — explicitly sanctioned by the spec.
- **No questions for the user:** spec is detailed, internally consistent, and aligned
  with goal.md; the one judgment call (Frontend Present) is resolved and documented
  above rather than asked (low-value question; DoD is explicit).
