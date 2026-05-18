# Goal Iteration 1 — Storage layer: single-file Parquet OHLCV cache + durable session store default

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** money-billions
- **Iteration:** 1
- **Mode:** next
- **Depth:** full
- **Frontend Present:** no
- **Target journeys:** J-01, J-06
- **Required-still-passing journeys:** J-02, J-03, J-04
- **Anti-goal reminders:**
  - "OHLCV market data MUST be cached as a single Parquet file per (symbol, timeframe) — NOT one CSV or file per calendar day — and MUST NOT be re-fetched from Binance when a covering local cache exists."
  - "`BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart."
  - "No nondeterministic backtests (slippage is seeded; identical inputs → identical output)."
  - "No lookahead: a generated signal must never observe future bars."
  - "No relational database or SQLite is introduced for OHLCV, session, or directions storage (Parquet + durable file store only)."

## GOAL

Repeated backtests on an already-fetched `(symbol, timeframe, date range)` load from a single local Parquet cache file with no Binance re-fetch and no per-day file fan-out, and session/run history persists durably by default (not under volatile `/tmp`) — surviving a process restart even with no `.env` present.

## BACKGROUND

The iter-0 baseline confirmed 5/6 journeys already pass but surfaced two pre-existing storage anti-goal violations that block GOAL_ACHIEVED and are the explicit reason this goal session exists (`docs/goal.md` Vision + Success Criteria): `data/loader.py` caches OHLCV as per-day CSV under `/tmp`, and `session_store.py` defaults `BACKTEST_STORE_DIR` to `/tmp/backtests`. The goal-evaluator ranked this storage workstream as highest-value and recommended `full` depth because it is an architecture-level data/persistence-layer change with regression risk to already-passing J-01 (cold backtest) and J-06 (warm re-run), and must preserve the determinism / no-lookahead invariants.

**Lesson applied (lessons.md iter-0):** the per-day-CSV + `/tmp`-default divergences are PRE-EXISTING baseline state, NOT a regression introduced by this iteration — but this iteration must verify J-01 and J-06 still pass after the Parquet migration. A green J-06 in iter-0 was FUNCTIONAL only and did NOT imply the single-Parquet anti-goal was met; the two are independent and this iteration closes that gap.

## IN SCOPE

### Backend

- [ ] **`apps/backend/data/loader.py` — migrate to a single Parquet file per (symbol, timeframe).**
  - Replace the per-day CSV cache (`_get_daily_cache_path`, `_load_from_csv`, `_save_to_csv`, the day-by-day loop in `load()`) with one Parquet file per pair+timeframe: `{cache_dir}/{safe_symbol}/{timeframe}.parquet` (or equivalent single-file-per-(symbol,tf) layout). No `.csv` and no per-calendar-day files may be written.
  - **Covering-cache rule:** on `load(symbol, tf, start, end)`, read the existing Parquet (if any). If `[start, end]` is fully within the cached timestamp span, return the filtered slice with **zero Binance calls**. If the cache is empty or only partially covers the window, fetch only the missing leading/trailing sub-range(s) from Binance, merge into the cached set, and rewrite the single Parquet. Assume contiguous Binance history for liquid pairs (no interior gaps); document this assumption in a code comment.
  - **Determinism invariant (critical):** for a given `(symbol, tf, start, end)`, the returned `list[OHLCV]` MUST be byte-identical whether served cold or warm. Preserve the existing post-processing exactly: dedupe by timestamp → sort ascending → filter strictly to `[start_date, end_date]`.
  - **Atomic write:** write the merged Parquet to a temp file then `os.replace()` onto the final path so a partial/concurrent write is never observable (replaces the old per-day `OSError`-swallow approach; safe under overlapping resolution-TF loads and `asyncio.Semaphore(1)` backtests).
  - Update `clear_cache()` to remove `*.parquet` (not `*.csv`) so it does not silently become a no-op.
  - Change the default cache dir off volatile `/tmp`: `os.getenv("MARKET_DATA_CACHE_DIR", <durable in-repo path>)` resolved from the module file location (not CWD-relative), consistent with the repo `.data/` convention. Update the docstring (currently says "or /tmp").
  - Remove per-day helper methods/imports that this change makes unused (do not leave dead code).
  - Confirm `pyarrow>=14.0.0` (already in `apps/backend/requirements.txt:23`) is installed in `.venv`; this is the Parquet engine for `pandas.to_parquet`/`read_parquet`.
- [ ] **`apps/backend/backend/session_store.py:26` — durable default.**
  - Change `BASE_DIR = Path(os.environ.get("BACKTEST_STORE_DIR", "/tmp/backtests"))` so the default (when the env var is unset) resolves to a durable in-repo path computed from `__file__` that points to the **same** location the committed env currently advertises (`<repo>/.data/backtests`), so session/run history persists identically with or without `BACKTEST_STORE_DIR` set, and survives a process restart with no `.env`.
- [ ] **`apps/backend/.env.example`** — change `MARKET_DATA_CACHE_DIR=/tmp/market_data` and `BACKTEST_STORE_DIR=/tmp/backtests` to the durable in-repo defaults so the committed example no longer advertises volatile `/tmp` (the gitignored `.env` is developer-managed and out of scope to commit).

### New user-facing capability

None new. This is an invariant-hardening iteration: the same user journeys (run a backtest, warm re-run, browse history) must continue to work, now backed by a single-file Parquet cache and a durable-by-default store.

### New information displayed

None.

### Product surface delta

User-invisible by design: identical UI and journeys; the change is that a warm re-run provably hits the local Parquet cache (no Binance re-fetch) and that run history is not silently lost on a host reboot / `/tmp` clear.

## OUT OF SCOPE

- **J-05 (frontend reference-data wiring)** — separate lean iteration; do NOT modify `/api/symbols`, `/api/timeframes`, or `BacktestConfigBar.tsx` here.
- **`GET /api/sessions/{id}` eager-load anti-goal** — code reading this iteration confirms it is a real violation (`session_routes.py:142-171` `get_session` calls `read_iteration_full` per iteration, inlining `result.json`/`rating.json`), but its fix is a frontend+backend session-open contract change with J-02 regression risk and belongs to a dedicated iteration. Do NOT change `get_session` here.
- Migrating the ~29,182 legacy per-day `.csv` files under `/tmp/market_data` — they are volatile and re-fetchable; a clean cut to the new Parquet path is acceptable. New code must not crash on a stale layout, but must not read or convert old CSVs.
- `directions_cache.py` `/tmp/initial_directions` default — directions is a nice-to-have, not pinned by an anti-goal.
- Any change to `shared/contracts.py` (frozen) or the Binance client wire protocol.

## DEFINITION OF DONE

- [ ] Target journeys **J-01** and **J-06** pass via browser-qa-agent (cold backtest renders metrics/equity/trades + new `run_id`; identical warm re-run completes, renders, and appears in history).
- [ ] Required-still-passing journeys **J-02, J-03, J-04** remain green via browser-qa-agent.
- [ ] No anti-goal violation introduced; the two targeted storage anti-goals are resolved: on disk after a warm run there is exactly one `*.parquet` per `(symbol, timeframe)` and zero per-day `*.csv`/per-day files; `session_store.BASE_DIR` default is not under `/tmp` and is absolute/durable.
- [ ] Determinism preserved: `apps/backend/tests/test_determinism.py` and `tests/test_lookahead.py` pass unchanged.
- [ ] Unit/integration tests pass; no regressions in the existing suite (`test_sandbox.py`, `test_walk_forward.py`, `test_sl_tp_path_model.py`, `test_directions_cache.py`).
- [ ] Dev handoff written at `docs/handoffs/goal-money-billions-iter-1-dev.md`.

## TESTING REQUIREMENTS

- **Browser (regression + target):** verify, by ID, through the running UI — J-01, J-06 (target), and J-02, J-03, J-04 (must-still-pass). J-06 must demonstrate a second identical run completing and appearing in history.
- **Unit/integration (new — none exist today for these modules):**
  - New `tests/test_loader.py`:
    - Warm path makes **zero Binance fetches** when the cached Parquet covers the requested window — assert via a spy/mock that `BinanceClient.fetch_ohlcv` is not called on the second `load()` of the same `(symbol, tf, start, end)` (deterministic; stronger than a flaky wall-clock ratio).
    - Cold-vs-warm equivalence: the `list[OHLCV]` returned cold equals the list returned warm for the same inputs (determinism invariant).
    - On-disk assertion: after a load, exactly one `*.parquet` exists for the pair+timeframe and no per-day `*.csv`/dated files are created.
    - `clear_cache()` deletes the Parquet file(s) and returns the correct count.
  - New `tests/test_session_store.py`:
    - With `BACKTEST_STORE_DIR` unset, `session_store.BASE_DIR` is absolute and not under `/tmp`.
    - Write a session/iteration, re-resolve the store fresh (simulated restart), read it back intact.
  - Existing critical-invariant tests (`test_determinism.py`, `test_lookahead.py`) must pass unchanged — run them explicitly and report counts in the handoff.
- **Error cases:** corrupted/partial Parquet file → treated as a cache miss and re-fetched (not a hard crash); a requested window only partially covered → only the missing sub-range is fetched and merged, not the whole window.

## NOTES

- **Authoritative cache contract = `docs/goal.md`**, not `apps/backend/.claude/CLAUDE.md`. That backend doc's "Data Caching" section is stale/aspirational: it describes `.cache/ohlcv/{symbol}_{timeframe}_{start}_{end}.parquet`, which would be one Parquet **per date range** and contradicts the anti-goal's "**single** Parquet file per (symbol, timeframe)". Follow goal.md (one accumulating file per pair+timeframe). Optionally correct that stale doc line to match reality (secondary; not a DoD blocker).
- Runtime `.env` currently sets `MARKET_DATA_CACHE_DIR=/tmp/market_data` (so OHLCV is volatile even at runtime today) and `BACKTEST_STORE_DIR=<repo>/.data/backtests` (durable). The hard, anti-goal-pinned MUSTs are: single-Parquet-per-(symbol,tf), no per-day fan-out, no re-fetch on covering cache, and a non-`/tmp` durable **default** for the session store. Making the OHLCV cache default durable + fixing `.env.example` aligns with the goal Vision; the single-file Parquet structure itself satisfies the pinned OHLCV anti-goal regardless of directory.
- `session_store.BASE_DIR` is evaluated at module import — derive the durable default from `Path(__file__)` (robust to CWD), and verify the chosen parent index resolves to `<repo>/.data/backtests` so existing on-disk sessions (written there via `.env`) are not orphaned.
- Regression watch (lessons.md iter-0): J-01 and J-06 are the highest-risk journeys for this change; J-02 reads the session store and is the key persistence-layer regression watch. The eager-load violation is now code-confirmed (see OUT OF SCOPE) — the evaluator may treat it as a confirmed-but-deferred anti-goal scheduled for a dedicated iteration, not a new regression introduced here.
- Depth is `full` (architecture-level data + persistence layer, new test modules required, regression risk to two already-passing journeys), consistent with the iter-0 evaluator recommendation.
