# Phase goal-money-billions-iter-1 — UI Surface Map

**Phase:** goal-money-billions-iter-1
**Date:** 2026-05-18
**Written by:** ui-impact-analyst

> **No UI surface was added or modified.** Frontend is byte-identical to HEAD.
> The surfaces below are **existing** screens whose *backing data/persistence
> layer changed* (`data/loader.py` single-file Parquet cache; `session_store.py`
> durable default). They are listed because the phase DoD mandates browser
> **regression** of journeys J-01, J-02, J-03, J-04, J-06 — the change is
> behind-the-scenes but these surfaces must be re-verified for no regression
> and for the new warm-cache / durable-persistence behavior.

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| `/` (main app, single-page) | `BacktestConfigBar` (symbol/timeframe/date-range/capital) + NL strategy chat input → **Run** | Changed behavior (backend-only; J-01 regression watch) | `loader.py` now serves OHLCV from a single Parquet file instead of per-day CSV; cold-fetch path rewritten | **J-01:** Enter an NL strategy, set symbol `BTCUSDT`, timeframe `1h`, a fresh date range, and initial capital; click Run. Expect: a results panel renders with **non-empty** metrics, an equity curve, a non-empty trades table, and a **new `run_id`** appearing in the session's run/iteration history. No error toast; run completes. |
| `/` (results region) | `ResultsPanel` → `MetricsCard`, `EquityChart`, `TradesTable` | Changed behavior (backend-only; determinism watch) | Returned `list[OHLCV]` now round-trips through Parquet; must be byte-identical cold vs. warm | **J-06:** Immediately after the J-01 run, click Run again with the **identical** strategy + config. Expect: second run completes **noticeably faster**, and `MetricsCard` values, `EquityChart` shape, and `TradesTable` rows are **identical** to the first run (same numbers, same trade count). A second distinct `run_id` is added to history. |
| `/` (session/run history list) | `IterationPanel` / `IterationCard` list + `SessionPicker` | Changed behavior (backend-only; J-06 history watch) | Run history persisted via durable-by-default `session_store.py`; warm re-run still records a new run | **J-06 (history):** After the two runs above, confirm **both** runs appear as distinct entries in the session's iteration/run history list with their own `run_id`s and timestamps; selecting each shows its own result. |
| `/` (open prior run) | `SessionPicker` → select prior session; `IterationCard` → `IterationDetailView` | Changed behavior (backend-only; **J-02 — highest persistence-regression risk**) | `session_store.BASE_DIR` default moved off `/tmp` to durable `<repo>/.data/backtests`; prior sessions must still resolve | **J-02:** Open a previously-saved session/run via `SessionPicker`; click a prior iteration card. Expect: its strategy spec, metrics, and trades **reload and render fully** (not blank, no 404/“not found”). **Durability check:** restart the backend with **no `BACKTEST_STORE_DIR` set**, reload the page, reopen the same prior run — it must still load (history survived restart, did not vanish with `/tmp`). |
| `/` (walk-forward) | `WalkForwardPanel` | Changed behavior (backend-only; J-03 regression watch) | Walk-forward consumes OHLCV via the rewritten loader (multi-window fetch/merge path) | **J-03:** Trigger a walk-forward analysis. Expect: a WFE (walk-forward efficiency) badge renders, a per-window results table populates with ≥1 window row, and a combined out-of-sample equity curve renders — no error and no empty/zeroed windows. |
| `/` (AI insights) | AI insights / suggestions panel (`RatingPanel` / insights region) | Changed behavior (backend-only; J-04 regression watch) | Insights are generated from a completed backtest whose data now comes from the Parquet cache path | **J-04:** After a completed backtest, open the AI insights/suggestions view. Expect: at least **one ranked suggestion** renders with its text/score visible — the panel is not empty and not errored. |

> Notes for QA: the `What to Test` actions are journey-anchored (J-01…J-06).
> The journey catalog in the spec/plan is authoritative for exact click
> targets if a label differs in the running build. The single **new** assertion
> introduced this iteration is the **warm-path / durability** behavior (J-06
> speed + identical output; J-02 survives a restart with no `.env`); everything
> else is pure no-regression verification.

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/data/loader.py` — Replaces per-day CSV OHLCV cache with one
  Parquet file per `(symbol, timeframe)`; covering-cache rule (zero Binance
  fetch when cached span covers the request), partial leading/trailing
  fetch-and-merge, atomic temp-file + `os.replace()` write, corrupt/legacy file
  → cache-miss re-fetch, `clear_cache()` now globs `*.parquet`, durable
  CWD-independent default cache dir. **No API signature or response shape
  changed** — same `list[OHLCV]` contract; no UI surface directly affected
  (only the *behavior* of journeys that already consume backtest data).
- `apps/backend/backend/session_store.py` — `BASE_DIR` default (when
  `BACKTEST_STORE_DIR` is unset) now resolves from `__file__` to the durable
  `<repo>/.data/backtests` instead of `/tmp/backtests`; module docstring
  updated. **No API or schema change** — same on-disk session/run format and
  same path the runtime `.env` already used, so existing sessions are not
  orphaned.
- `apps/backend/.env.example` — `MARKET_DATA_CACHE_DIR` and
  `BACKTEST_STORE_DIR` example defaults changed off `/tmp` to durable in-repo
  paths; comments updated (no longer "CSV files"). Config/doc only; the
  gitignored runtime `.env` is unchanged.
- `apps/backend/CLAUDE.md` — Corrected a stale "Data Caching" doc line
  (described one-Parquet-per-date-range, which contradicted the anti-goal) to
  the implemented single-file-per-`(symbol,tf)` contract. Documentation only.
- `apps/backend/tests/test_loader.py` (new, 9 tests) and
  `apps/backend/tests/test_session_store.py` (new, 3 tests) — Test code only;
  no runtime/UI impact.
- `runs/goal-session-money-billions/*` (telemetry/trace/.next-step) —
  Framework bookkeeping artifacts, not product code; no UI impact.

---

## Summary

- **Frontend surfaces changed:** 0 (zero frontend code changed; surfaces above
  are existing screens flagged for **regression** due to a backing
  data/persistence-layer change, not UI modification)
- **New pages/routes:** 0
- **Modified components:** 0
- **Navigation changes:** no
- **Backend-only changes:** 6 (`loader.py`, `session_store.py`, `.env.example`,
  `CLAUDE.md`, 2 new test modules) + framework run artifacts
- **Regression-watch journeys (browser QA required):** J-01, J-06 (target —
  cold then identical warm re-run, both render, both in history), and J-02,
  J-03, J-04 (must still pass; J-02 is the key persistence-restart watch)
