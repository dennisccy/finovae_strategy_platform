# goal-money-billions-iter-0 Dev Handoff

**Phase:** goal-money-billions-iter-0
**Date:** 2026-05-17
**Agent:** developer
**Mode:** baseline / lean — **VERIFY-ONLY, NO CODE CHANGES**
**Status:** complete

## What Was Built

**Nothing. This is a deliberate no-op developer step.** This is the baseline
assessment for goal session `money-billions`. Per the iter spec IN SCOPE, no
backend or frontend source file is modified. The developer step records
backend-observable baseline signals so subsequent `Mode: next` iterations can
distinguish "already working" from "yet to build". The actual per-journey UI
exercise (J-01…J-06) is performed by the browser-QA step, not here.

## Files Changed

- **None.** No source files modified. `git status --porcelain` shows only
  untracked framework artifacts (`docs/phases/`, `runs/`); no tracked source
  file is added, modified, or deleted. Verify-only confirmed.

## Verify-only confirmation

- `git status --porcelain` before and after all verification: only `?? docs/phases/`
  and `?? runs/` (dev-chain artifact dirs). Zero source-tree changes.
- The only files this step wrote are framework artifacts under
  `runs/goal-money-billions-iter-0/` (logs, `status.json`) and this handoff.

## Verification activities performed (no code changes)

### Backend boot + `/docs`
- Started backend via `bash scripts/start-backend.sh` (offset port, **8691** —
  NOT 8000; deterministic per-project offset). Boot log:
  `runs/goal-money-billions-iter-0/backend-boot.log`.
- Boot is clean: `Application startup complete` / `Uvicorn running on
  http://0.0.0.0:8691`.
- `GET /docs` → **200**. `GET /openapi.json` → **27 paths**.
- Boot log line: `Session store initialized at
  /home/dennisccy/Git/finovae_strategy_platform/.data/backtests` (durable,
  non-`/tmp`).
- Backend process killed after probing; port 8691 confirmed free (no leaked
  server processes).

### Backend unit suite
Command: `cd apps/backend && .venv/bin/python -m pytest`
Result: **107 passed, 1 failed (108 collected) in 11.06s**
Log: `runs/goal-money-billions-iter-0/backend-pytest.log`

- **Anti-goal invariant tests ALL PASS:**
  - `tests/test_lookahead.py` — PASS (no lookahead)
  - `tests/test_determinism.py` — PASS (deterministic backtests)
  - `tests/test_sandbox.py` — PASS (RestrictedPython sandbox blocks file
    I/O / network / `exec`/`eval`/`__import__`/`open`/`os`)
  - `tests/test_walk_forward.py` — PASS
  - `tests/test_sl_tp_path_model.py` — PASS
- **1 FAILED:** `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  — `assert len(result["timeframeResults"]) == 1` got `0`. The directions
  cache is a **nice-to-have** (goal.md Key Capability #10), **not** a Must-have
  journey (J-01…J-06). Recorded as a pre-existing baseline defect; out of scope
  to fix this iteration.

### Observable anti-goal signals (recorded, NOT fixed — verify-only)

1. **OHLCV cache — DIVERGES from anti-goal (code-level).**
   `data/loader.py` caches OHLCV as **one CSV per calendar day**
   (`_get_daily_cache_path` → `<symbol>/<tf>/<YYYY-MM-DD>.csv`; `_save_to_csv`
   → `df.to_csv(...)`; `load()` loops day-by-day; `clear_cache()` globs
   `*.csv`). On disk: `/tmp/market_data` holds **29,182 CSV files, 0 Parquet
   files** — concrete evidence of per-day file fan-out. The anti-goal requires
   "a single Parquet file per (symbol, timeframe) — NOT one CSV or file per
   calendar day". **Current baseline does NOT satisfy this anti-goal.** Cache
   dir resolves to `MARKET_DATA_CACHE_DIR=/tmp/market_data` (volatile `/tmp`);
   code default is also `/tmp`. (Consistent with the known-pending storage-perf
   Parquet migration — this is "yet to build", surfaced exactly as intended.)
2. **`BACKTEST_STORE_DIR` default — code default violates anti-goal, but
   runtime is durable.** Code default is `/tmp/backtests`
   (`backend/session_store.py:26`) — literally a volatile `/tmp` default, which
   the anti-goal forbids. **However** `apps/backend/.env` overrides it to
   `/home/dennisccy/Git/finovae_strategy_platform/.data/backtests`; the boot
   log confirms the session store initialized there, and that directory already
   holds prior `live/` + `archive/` run dirs → in the configured environment
   session/run history is durable and survives restart. Nuance for the
   evaluator: durable behavior is `.env`-provided; the bare code default still
   contradicts the anti-goal text.
3. **Directions cache default** `DIRECTIONS_CACHE_DIR` → `/tmp/initial_directions`
   (`backend/directions_cache.py:23`). Secondary — directions is a nice-to-have;
   the anti-goal pins `BACKTEST_STORE_DIR` specifically.
4. **No relational DB / SQLite — anti-goal SATISFIED.** Repo-wide search for
   `*.db` / `*.sqlite*` (excluding node_modules) returned nothing.
5. **No committed secrets — anti-goal SATISFIED (observable).** API keys live
   in git-ignored `apps/backend/.env`; git tree is clean (no secret in source).
6. **Stale doc divergence (observation only):** `apps/backend/CLAUDE.md` claims
   OHLCV is cached "in `.cache/ohlcv/` as Parquet files" — does not match the
   actual code (per-day CSV under `MARKET_DATA_CACHE_DIR`).

## Per-journey baseline status (backend signals only — UI exercise is browser-QA's job)

> The developer step does NOT mark journeys pass/fail (that is the
> goal-evaluator's job from browser-QA evidence). Below are backend-observable
> readiness signals to inform the browser-QA step and the evaluator.

| Journey | Backend signal | Notes for browser-QA / evaluator |
|---|---|---|
| **J-01** Run backtest from NL | Backend ready: `/api/run-backtest` present (27 OpenAPI paths); `OPENAI_API_KEY` is **SET** in `apps/backend/.env` (default `gpt-5.4-mini`). | Full pass needs UI exercise + live OpenAI + live Binance. **Key validity NOT verified** (no live LLM call made — out of scope here). Record any auth/Binance error as an environment observation, not a code defect. |
| **J-02** Inspect/browse run history | `/api/runs` responds 200 (currently `{"runs":[],"total_count":0}`); `/api/sessions` responds 200; durable store `.data/backtests` already holds prior `live/`+`archive/` run dirs → on-disk persistence works. | A fresh completed run likely needed before a prior run can be reopened in the UI (the `/api/runs` list is empty; history is session-scoped via `/api/sessions`). |
| **J-03** Walk-forward | Backend ready: `test_walk_forward.py` PASS; endpoint present. | Requires a completed run first (depends on J-01). Browser-QA to exercise IS/OOS + WFE badge. |
| **J-04** AI insights | Backend ready: insights endpoint present; `OPENAI_API_KEY` SET. | Depends on a completed run + live OpenAI. Browser-QA to exercise; OOS-aware when WF data exists. |
| **J-05** Reference data loads | **Verified at API level:** `GET /api/symbols` → 26 symbols incl. `BTC/USDT`; `GET /api/timeframes` → 6 incl. `1h`. No API key needed. | Strong baseline-pass signal; browser-QA to confirm the UI controls actually populate from these. |
| **J-06** Warm-cache re-run | Loader has a day-by-day cache-hit path (re-run over the same range reads cache, avoids re-fetch) → functional warm re-run plausible. **BUT** storage is per-day CSV in `/tmp` (anti-goal #1), not single Parquet. | Browser-QA to exercise the full end-to-end UI re-run. Functional success ≠ anti-goal compliance; the single-Parquet anti-goal is currently NOT met. |

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest`
Result: **107 passed, 1 failed in 11.06s** (failure = `test_directions_cache.py`
round-trip, a nice-to-have, not a Must-have journey).

## Known Issues / Baseline observations (NOT fixed — verify-only by design)

- **Anti-goal not met:** OHLCV cache is per-day CSV (29,182 files in
  `/tmp/market_data`), not single Parquet per (symbol, timeframe). Needs a
  `Mode: next` storage iteration (matches the known pending Parquet migration).
- **Anti-goal nuance:** `BACKTEST_STORE_DIR` code default is `/tmp/backtests`;
  durable only because `apps/backend/.env` overrides it. Runtime is durable;
  code default is not.
- **Pre-existing test failure:** `test_directions_cache.py::test_write_and_read_full_round_trip`
  (`timeframeResults` empty). Nice-to-have feature; out of scope this iteration.
- **Unverified:** OpenAI/Anthropic key *validity* and live Binance fetch were
  NOT exercised here (no code-changing live calls in the developer step). The
  browser-QA step will surface whether J-01/J-03/J-04/J-06 fail at the
  LLM/Binance step; per the iter spec NOTES, such failures are environment
  observations for the evaluator to classify, not code defects to "fix".
- **Stale doc:** `apps/backend/CLAUDE.md` OHLCV caching description does not
  match current code.

## Definition of Done — self-check

- [x] Backend boot + `/docs` availability recorded (port 8691, `/docs` → 200).
- [x] Backend unit-suite result recorded (107 passed / 1 failed; lookahead,
      determinism, sandbox invariant tests all PASS).
- [x] Observable anti-goal signals noted (per-day CSV cache violation;
      `BACKTEST_STORE_DIR` default nuance; no SQLite/DB).
- [x] No code/source files modified (verify-only confirmed via `git status`).
- [x] No anti-goal violation *introduced* (trivially — zero code changes).
- [x] Per-journey backend baseline signals summarized for browser-QA/evaluator.
- [ ] Per-journey UI pass/fail — **deferred to browser-QA step** (not the
      developer's responsibility in baseline mode).
