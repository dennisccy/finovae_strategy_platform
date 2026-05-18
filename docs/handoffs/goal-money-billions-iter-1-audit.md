# goal-money-billions-iter-1 Audit Report

**Date:** 2026-05-18
**Auditor:** Hard audit pass — skeptical, evidence-based

---

## 1. Executive Verdict

**Verdict:** PASS

The phase goal is genuinely achieved, verified by reading the actual code and reproducing
results — not by trusting handoffs. Both pinned storage anti-goals are resolved: OHLCV is
cached as a single Parquet file per `(symbol, timeframe)` with zero per-day fan-out and a
deterministic zero-refetch covering-cache (confirmed in unit tests **and** in the live
runtime cache after real browser backtests), and `session_store.BASE_DIR` now defaults to
an absolute, non-`/tmp`, durable in-repo path that resolves to the *same* location where
18 existing sessions already live (so none are orphaned). Determinism/no-lookahead
invariants pass unchanged, all five DoD browser journeys pass with timestamped evidence,
and the single test failure is an independently-confirmed pre-existing baseline, not a
regression introduced here.

---

## 2. Findings

### Backend Findings

**B1 — OBSERVATION (verified-correct): `loader.py` / `session_store.py` path index**
`Path(__file__).resolve().parents[3]` is the spec's flagged likely failure point.
Independently verified against `git rev-parse --show-toplevel` (NOT the test's own
`parents[3]` expression): `loader._DEFAULT_CACHE_DIR` → `<repo>/.data/market_data`,
`session_store._DEFAULT_STORE_DIR` / `BASE_DIR` → `<repo>/.data/backtests`. The
session-store default lands exactly on the directory holding the 18 existing live
sessions (`.data/backtests/live/`, incl. `9573c955…` used by QA's J-02), confirming
existing on-disk history is not orphaned. No off-by-one. No action needed.

**B2 — OBSERVATION: covering-cache / determinism logic correct (`loader.py:196-240`)**
`_read_parquet_cache` dedupe-sorts so `cached[0]/[-1]` are the true span bounds; the
leading/trailing missing-range computation is correct; `_postprocess` applies
dedupe→sort-asc→strict `[start,end]` filter on both cold and warm paths, satisfying the
critical byte-identical-cold-vs-warm invariant. Atomic write uses
`tempfile.mkstemp(dir=cache_path.parent)` + `os.replace()` (same-fs atomic; temp unlinked
on failure). Corrupt/legacy file → `[]` → re-fetch (no crash). `clear_cache()` globs
`*.parquet` (the old `*.csv` silent no-op is fixed). All confirmed by reading the code.

**B3 — GAP→FIXED: `.env.example` CWD-relative override values**
`MARKET_DATA_CACHE_DIR=.data/market_data` / `BACKTEST_STORE_DIR=.data/backtests` were
relative; copied verbatim and run from `apps/backend/` they resolve to
`apps/backend/.data/...`, splitting session history and contradicting the file's own
"Leave unset to use the durable in-repo default" comment. The pinned anti-goal itself
(no `/tmp` default, durable, survives restart) was already met by the **code** default
(B1), so this was GAP-level, not blocking. **Fixed during this audit** (see §4).

### Frontend Findings

**F1 — OBSERVATION: no frontend change (correct by design)**
`git diff HEAD -- apps/frontend` is empty. `Frontend Present: yes` exists only to force
the DoD-mandated browser regression. Correct for a backend-only invariant-hardening
iteration; UX-regression review returned UX-REGRESSION-PASS.

### Test Findings

**T1 — OBSERVATION: single suite failure is a confirmed pre-existing baseline**
Full suite reproduced: **119 passed, 1 failed**. The failure is
`test_directions_cache.py::test_write_and_read_full_round_trip`. `git diff HEAD --
apps/backend/backend/directions_cache.py apps/backend/tests/test_directions_cache.py`
is **empty** → byte-identical to HEAD → genuine iter-0 baseline (`failing+1`), explicitly
out of scope, NOT a regression. Within TC-11's stated pass criterion.

**T2 — OBSERVATION: default-path tests are self-referential (impl independently proven)**
`test_loader.py:239` / `test_session_store.py:47` derive `repo_root` via the same
`parents[3]` expression as the source, so they cannot catch a `parents[N]` off-by-one.
Reviewer flagged this (NOTE). Mitigated: the auditor independently verified the resolved
paths via `git rev-parse` (B1), so the implementation is proven correct regardless.
Optional future hardening; not blocking.

**T3 — OBSERVATION: redundant in-function `import asyncio` (`loader.py:315`)**
`load_sync` keeps a local `import asyncio` now redundant with the module-level import
(line 7). It is *used* (`asyncio.run` next line), so not dead code; ruff-clean. Cosmetic
only — not fixed per "do not rewrite working implementations / no OBSERVATION fixes".

---

## 3. Domain Assessment

The core domain logic is correct and the determinism contract is genuinely preserved.

- **Anti-goal #1 (single Parquet, no fan-out, no covering-cache refetch):** verified three
  independent ways — unit tests (`test_warm_load_makes_zero_binance_fetches` asserts
  `calls == []` on the warm load; `test_on_disk_single_parquet_zero_csv`;
  `test_partial_*_coverage_fetches_only_missing`), code reading, and the **live runtime
  cache**: after QA's real browser backtests today, `/tmp/market_data` contains exactly
  `BTC_USDT/1h.parquet` + `BTC_USDT/5m.parquet` (resolution TF) and **zero new `.csv`**
  written 2026-05-18. The structural anti-goal is satisfied independent of cache
  directory, exactly as the spec scoped it.
- **Anti-goal #2 (durable session-store default):** `BASE_DIR` default is absolute, not
  `/tmp`, and resolves to the same `<repo>/.data/backtests` the runtime `.env`
  advertises; the 18 existing sessions are not orphaned; round-trip-after-simulated-restart
  test passes. Resolved.
- **Determinism / no-lookahead:** `test_determinism.py` 6/6 + `test_lookahead.py` 6/6 pass;
  both source files byte-identical to HEAD; `test_cold_equals_warm_equivalence` passes
  (tz-aware UTC timestamps + floats survive the Parquet round-trip); QA reports 3 live
  identical runs producing byte-identical metrics. Invariants intact.
- **No SQLite/relational DB introduced:** confirmed by code review (Parquet + file store
  only).

DoD items 1–6 are all met and independently verified (browser journeys J-01/J-06 target
and J-02/J-03/J-04 must-pass: PASS with timestamped evidence screenshots present;
handoff present with concrete pytest counts that I reproduced exactly:
loader 9 / session_store 3 / determinism 6 / lookahead 6).

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| 1 | GAP (review MINOR) | `apps/backend/.env.example` | Commented out `MARKET_DATA_CACHE_DIR` and `BACKTEST_STORE_DIR` (was set to CWD-relative `.data/...`) and added an "If you override, use an ABSOLUTE path" note. Makes the committed example self-consistent with its own "Leave unset to use the durable in-repo default" comment and removes the split-session-history footgun. |

**Why needed:** the relative values, if uncommented and run from `apps/backend/`, would
resolve to `apps/backend/.data/...` rather than `<repo>/.data/...`, fragmenting session
history away from the existing store — directly counter to the spec's durability intent.

**Regression check after the fix (all green):**
- TC-12 still PASS: no `/tmp/(market_data|backtests)` literal; comment still not "CSV files".
- Effective defaults still resolve correctly (keys now unset → code default →
  `<repo>/.data/backtests`, `<repo>/.data/market_data`; the `or` short-circuit also makes
  an empty value safe).
- Full suite re-run: **119 passed, 1 failed** (same pre-existing baseline; zero new
  failures introduced by the edit). No code or test reads `.env.example`.

---

## 5. Recommended Next Step

Proceed. The two targeted storage anti-goals are genuinely resolved, invariants hold,
all DoD journeys pass, and the only open review item has been fixed with zero regression.

The remaining code-confirmed-but-deferred anti-goal is the `GET /api/sessions/{id}`
eager-load (`session_routes.py:142-171` calls `read_iteration_full` per iteration) — a
frontend+backend session-open contract change with J-02 regression risk that warrants
its own dedicated `full`-depth iteration, as the spec OUT OF SCOPE and dev handoff
already note. The pre-existing `test_directions_cache.py` baseline failure remains a
known, out-of-scope iter-0 carryover (not introduced here) and can be folded into a
future directions-focused iteration if directions becomes in-scope.
