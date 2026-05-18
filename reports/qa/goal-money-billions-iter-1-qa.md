# goal-money-billions-iter-1 — QA Validation Report

**Verdict:** PASS

**Phase:** goal-money-billions-iter-1
**Date:** 2026-05-18
**Agent:** qa (MODE 2 — QA Validation)
**Frontend Present:** yes (browser regression of existing journeys — no new UI by design)

---

## Summary

Storage-layer invariant hardening (single-file Parquet OHLCV cache + durable-by-default
session store). Backend-only; no new user-facing capability by design. All 19 functional
test cases pass. Full backend suite **119 passed / 1 failed** — the single failure is the
**documented pre-existing iter-0 baseline** (`test_directions_cache.py::test_write_and_read_full_round_trip`,
explicitly out of scope, not a regression). All five DoD-mandated browser journeys
(J-01, J-02, J-03, J-04, J-06) verified green through the running UI. The two targeted
storage anti-goals are resolved.

---

## Step 1 — Required Artifact Verification

| Artifact | Status |
|---|---|
| `docs/handoffs/goal-money-billions-iter-1-dev.md` | ✅ present (What Built / Files / Tests / Known Issues / Next) |
| `reports/reviews/goal-money-billions-iter-1-review.md` | ✅ **PASS_WITH_NOTES** (3 issues: 1 MINOR + 2 NOTE — all non-blocking, see below) |
| `runs/goal-money-billions-iter-1/status.json` | ✅ present |
| `reports/qa/goal-money-billions-iter-1-test-plan.md` | ✅ present (19 TCs — executed below) |

Review notes (non-blocking, recorded for transparency):
- **MINOR** `.env.example`: `MARKET_DATA_CACHE_DIR/BACKTEST_STORE_DIR=.data/...` are CWD-relative; if copied verbatim and run from `apps/backend/` they resolve to `apps/backend/.data/...` rather than `<repo>/.data/...`. Spec hard requirement (no `/tmp`, durable) is still met; the absolute durable default is enforced in code, not `.env.example`.
- **NOTE** `loader.py:315`: redundant in-function `import asyncio` in `load_sync` (module-level import added at line 7). ruff-clean; the local import is *used* (next line `asyncio.run`), merely redundant — not dead code.
- **NOTE** `test_session_store.py:47`: default-path test derives `repo_root` via the same `parents[3]` expression as the source (can't independently catch a `parents[N]` off-by-one). Implementation independently verified correct by reviewer and by TC-08 here.

None of these are blocking; none affect a DoD item.

---

## Step 2 — Backend Test Results (exact)

Command: `cd apps/backend && .venv/bin/python -m pytest tests/ -v`
Log: `reports/qa/goal-money-billions-iter-1-test.log`

```
======================== 1 failed, 119 passed in 5.58s =========================
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip
        assert 0 == 1  (len(result["timeframeResults"]) == 1 -> got [])
```

Per-module breakdown (from the test log):

| Module | Result | Maps to |
|---|---|---|
| `test_loader.py` (new) | **9 passed / 0 failed** | TC-01..TC-07 |
| `test_session_store.py` (new) | **3 passed / 0 failed** | TC-08, TC-09 |
| `test_determinism.py` (critical invariant) | **6 passed** (unchanged) | TC-10 |
| `test_lookahead.py` (critical invariant) | **6 passed** (unchanged) | TC-10 |
| `test_sandbox.py` | 27 passed | TC-11 |
| `test_walk_forward.py` | 33 passed | TC-11 |
| `test_sl_tp_path_model.py` | 23 passed | TC-11 |
| `test_directions_cache.py` | 12 passed / **1 failed** | TC-11 |

**The single failure is the documented pre-existing iter-0 baseline failure**
(`test_directions_cache.py::test_write_and_read_full_round_trip`). `directions_cache.py`
and its test are byte-identical to HEAD (out of scope this iteration; iter-0 recorded
`failing+1 regressed+0`). It falls **within TC-11's pass criteria** ("only the documented
pre-existing baseline failure may fail; every other test passes"). No structured
failure digest is required — this is a known, non-regression baseline failure, not a
new break introduced by this iteration. **Not a blocker.**

Lint: dev handoff reports `.venv/bin/ruff check` on all changed source — All checks passed.

---

## Step 3 — Frontend Tests

No JS unit-test command defined for this backend-only iteration; frontend validation is
the browser regression below (Step 4).

---

## Step 3.5 — Functional Test Plan Results (19/19 PASS)

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---|---|---|---|---|---|---|
| TC-01 | Warm re-run zero Binance fetches | pytest | 2nd load fetch_count==0 | `test_warm_load_makes_zero_binance_fetches` PASSED (`assert calls == []`) | **PASS** | Deterministic zero-refetch proof |
| TC-02 | Cold==warm byte-identical | pytest | cold_list == warm_list incl. tz | `test_cold_equals_warm_equivalence` PASSED | **PASS** | Determinism invariant survives Parquet round-trip |
| TC-03 | One Parquet, zero per-day CSV | pytest | 1 `*.parquet`, 0 `*.csv` | `test_on_disk_single_parquet_zero_csv` PASSED (`BTCUSDT/1h.parquet`) | **PASS** | OHLCV anti-goal structure |
| TC-04 | Partial coverage fetches only gap | pytest | only missing sub-range fetched | `test_partial_leading...` + `test_partial_trailing...` PASSED | **PASS** | Both leading & trailing gaps |
| TC-05 | Corrupt Parquet → cache miss | pytest | no crash, re-fetch | `test_corrupt_parquet_is_treated_as_cache_miss` PASSED | **PASS** | |
| TC-06 | clear_cache() count | pytest | returns N, removes parquet | `test_clear_cache_deletes_parquet_and_returns_count` PASSED (==2) | **PASS** | Globs `*.parquet` |
| TC-07 | Loader default dir durable | pytest | absolute, not `/tmp`, repo/.data/market_data | `test_default_cache_dir_is_durable_not_tmp` PASSED | **PASS** | CWD-independent |
| TC-08 | session_store.BASE_DIR durable | pytest | absolute, not `/tmp`, == repo/.data/backtests | `test_default_store_dir_is_durable_not_tmp` PASSED | **PASS** | Existing on-disk sessions not orphaned |
| TC-09 | Session store restart round-trip | pytest | write→reload→read back intact | `test_write_then_simulated_restart_round_trip` PASSED | **PASS** | |
| TC-10 | Determinism & lookahead unchanged | pytest | 0 failures, sources unmodified | determinism 6/6 + lookahead 6/6 PASSED | **PASS** | Critical invariants intact |
| TC-11 | No new regressions | pytest | only baseline failure allowed | sandbox 27, walk_forward 33, sl_tp 23, directions 12/1 | **PASS** | Only the documented pre-existing baseline failed |
| TC-12 | `.env.example` no `/tmp`/CSV | artifact | no `/tmp/*`, comment not "CSV" | `MARKET_DATA_CACHE_DIR=.data/market_data`, `BACKTEST_STORE_DIR=.data/backtests`; comment "single Parquet file" | **PASS** | Review MINOR (CWD-relative) noted; criteria met |
| TC-13 | Dead per-day code removed | artifact | no per-day/csv code; os.replace; docstrings | no `_get_daily_cache_path/_load_from_csv/_save_to_csv/.csv/hashlib/json`; `os.replace`+`tempfile.mkstemp`; covering-cache comment; docstrings updated | **PASS** | `hashlib/json/timedelta` removed; review NOTE re redundant local `import asyncio` (non-blocking, used) |
| TC-14 | Dev handoff w/ explicit counts | artifact | 4 concrete pytest count lines | determinism **6**, lookahead **6**, loader **9**, session_store **3** | **PASS** | Concrete numbers present |
| TC-15 | J-01 NL backtest (target) | browser | metrics+equity+trades+new run_id | New run_id `b3fd0cd3…`; +12.08% / 20 trades / 70% win / 0.91 Sharpe; equity curve drawn; 20-row trades table; params BTC/USDT 1h 2024-01-01–2024-03-01 $10k | **PASS** | `POST .../iterations 200`, no 5xx |
| TC-16 | J-06 identical warm re-run (target) | browser | 2nd run renders + history entry | 3 identical runs all completed, **byte-identical** results (+12.08%/20/70%/0.91); distinct run_ids (`b3fd0cd3`→`991efc03`); multiple history iterations; no error | **PASS** | Live boundary fetch delta=2 (sub-range touch, NOT whole-window/per-day) — sanctioned covering-cache behavior; deterministic zero-refetch proven by TC-01 |
| TC-17 | J-02 browse run history | browser | spec+metrics+trades reload | Switched to prior session "BTC 1H RSI Mean Reversion" (sess `9573c955`): params 2023-01-01–2023-12-31, Annual Return/Alpha/Beta/Sharpe, **115-trade** table, equity curve, monthly returns all reloaded from durable store | **PASS** | Directly exercises migrated session_store read path |
| TC-18 | J-03 walk-forward (must-pass) | browser | WFE badge + per-window table + combined OOS curve | Re-ran IS=4/OOS=2 → **WFE 0.53 ✓** (green tier), 4-row per-window table, Combined OOS Equity Curve; fresh values (WFE 1.26→0.53) prove end-to-end recompute | **PASS** | `POST /api/execute-walk-forward 200`, persisted to sess `9573c955`, no errors |
| TC-19 | J-04 AI insights (must-pass) | browser | ≥1 ranked suggestion, no error | Narrative ("…12.08% return over 20 trades, 70% win, PF 1.85, Sharpe 0.91…") + **28 ranked suggestions** (Loosen RSI Entry Band, Add Midline Exit, Use Trend Filter, …) | **PASS** | `POST /api/generate-insights 200` ×3 |

**19/19 test cases passed.** (TC-11 passes under its explicit criterion — only the
documented pre-existing baseline failure occurred.)

---

## Step 4 — Chrome MCP Browser Checks

Frontend reachable at `http://localhost:3691` (HTTP 200). Backend reachable — note the
QA-runner health URL `http://localhost:8691/health` returns 404 (this app exposes no
`/health` route), but `/api/runs`, `/api/symbols`, `/api/timeframes`, `/api/models`,
`/docs`, `/` all return 200, so the backend is up and functional.

All five DoD-mandated journeys executed as **real workflows** (not render-only) via
Chrome MCP. Evidence screenshots in `reports/qa/goal-money-billions-iter-1-evidence/`:

- `TC-15-01-config-set.png`, `TC-15-02-results.png` — J-01 fresh backtest
- `TC-16-01-state.png`, `TC-16-02-rerun-result.png` — J-06 identical warm re-run
- `TC-17-01-sessions-dropdown.png`, `TC-17-03-loaded.png` — J-02 prior session reload
- `TC-18-01-walkforward.png` — J-03 walk-forward re-run
- `TC-19-01-insights.png` — J-04 AI insights

Key real-workflow findings:
- **J-01 / J-06:** A fresh NL backtest (BTC/USDT 1h, fixed range, $10k) ran end-to-end
  through the migrated single-Parquet loader (cold), and identical re-runs completed
  with **byte-identical** results — strong live evidence that cold==warm determinism
  holds and the warm path works through the running UI.
- **J-02:** Switching to a different prior session reloaded its strategy spec, metrics,
  115-trade table, equity curve and monthly returns — directly exercising the migrated
  `session_store.py` read path (highest persistence-layer regression watch). Works.
- **J-03:** Walk-forward re-run recomputed fresh IS/OOS windows through the loader
  (WFE 1.26 → 0.53), confirming the loader change did not regress walk-forward.
- **J-04:** Insights generated and rendered with a substantive narrative tied to the
  run metrics plus many ranked suggestions.
- A `Delete session?` confirmation was accidentally opened while locating the session
  switcher; it was **Cancelled** — no prior session data was deleted.

**No 5xx, no Traceback, no error state observed in any journey.**

---

## Step 4b — UI Evolution Audit

This iteration is **backend-only invariant hardening**; the spec explicitly states
"New user-facing capability: None … User-invisible by design: identical UI and
journeys". `Frontend Present: yes` exists solely to force the DoD-mandated browser
regression of existing journeys.

1. Did the UI evolve to reflect a new capability? — N/A by design (no new capability).
2. Can the user see/understand/control the new capability? — N/A; the change is an
   internal storage/persistence guarantee, intentionally invisible.
3. Is the UI relying on old generic pages for new functionality? — N/A; no new function.
4. Technically complete but product-wise underexposed? — No; correctly invisible, and
   all five pre-existing journeys were regression-verified green through the UI.

**Verdict:** UI-PASS — for a sanctioned backend-only invariant-hardening iteration the
correct outcome is *no UI change with all existing journeys preserved*, which is exactly
what was verified.

---

## Anti-Goal Resolution Evidence

| Targeted anti-goal | Evidence | Status |
|---|---|---|
| OHLCV must be a single Parquet per (symbol,tf); no per-day fan-out; no refetch on covering cache | TC-03 (1 parquet/0 csv), TC-01 (zero-refetch deterministic), TC-04 (only-gap fetch) | ✅ Resolved |
| `BACKTEST_STORE_DIR` default must not be volatile `/tmp`; history survives restart | TC-08 (BASE_DIR == `<repo>/.data/backtests`, absolute, not `/tmp`), TC-09 (restart round-trip), TC-17 (live prior-session reload) | ✅ Resolved |
| No SQLite/relational DB introduced | Parquet + file store only (code review + tests) | ✅ Held |
| Determinism / no-lookahead preserved | TC-02, TC-10 (6+6 passed unchanged); 3 live runs byte-identical | ✅ Held |

Documented, non-blocking out-of-scope item (per spec & dev handoff): runtime `.env`
still sets `MARKET_DATA_CACHE_DIR=/tmp/market_data` (developer-managed, gitignored, not
committed). The pinned OHLCV anti-goal is about **structure** (single Parquet, no
per-day fan-out, no whole-window refetch) which the new code satisfies regardless of
directory; runtime `BACKTEST_STORE_DIR` already points durably at `<repo>/.data/backtests`.

---

## Blockers

**None.**

The only test "failure" is the explicitly documented pre-existing iter-0 baseline
(`test_directions_cache.py::test_write_and_read_full_round_trip`) — out of scope,
not a regression, and within TC-11's pass criteria.

---

## Step 5b — Server Cleanup

No backend/frontend servers were started by QA (the QA runner manages them). No
cleanup required. Chrome MCP browser left in a benign state (prior sessions intact;
the cancelled delete preserved all data).

---

**Final Verdict:** PASS
