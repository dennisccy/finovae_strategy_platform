# goal-money-money-iter-0 Dev Handoff

**Phase:** goal-money-money-iter-0
**Date:** 2026-05-17
**Agent:** developer
**Mode:** goal-mode lean iteration 0 — **baseline assessment (verify-only)**
**Status:** complete

> **BASELINE VERIFY-ONLY — NO CODE CHANGES.** Per the iter spec IN SCOPE
> (Backend: None / Frontend: None), this iteration modified zero source files.
> The only working-tree entry is the **pre-existing** ` M .gitignore` (already
> modified in the session-start git snapshot, before iteration 0 began — not
> introduced here) plus the untracked `docs/phases/` (this spec) and `runs/`
> (generated baseline artifacts). `git diff` against source dirs is empty.

## What Was Done (verification activity only)

- Confirmed environment readiness: backend `.venv` (Python 3.12.3), both
  `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` present and non-empty in
  `apps/backend/.env` → **LLM-dependent journeys are NOT environmentally blocked**.
- Ran the existing backend test suite (no new tests authored) and recorded the
  green/red baseline.
- Started the backend (uvicorn :8691) and probed the full `GET` API surface;
  started the frontend (Vite :3691) for a bounded startup smoke. Both servers
  were stopped and their ports released before finishing.
- Inspected source (read-only) for the three pre-existing anti-goal postures
  named in the iter spec; captured concrete runtime evidence.

## Files Changed

- **NONE.** Verify-only baseline — no source, config, or dependency changes.
  (Defects/postures found below are recorded for `Mode: next` iterations, not fixed here.)

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest`
Result: **107 passed, 1 failed** in 6.39s (log: `runs/goal-money-money-iter-0/backend-pytest.log`)

- **FAILED** `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  — `assert len(result["timeframeResults"]) == 1` → `assert 0 == 1`
  (`read_direction_full` returns empty `timeframeResults`). Pre-existing;
  directions cache is a *nice-to-have* (goal.md capability #10), not on the
  J-01..J-06 critical path. **Recorded, not fixed** (verify-only).

## Service Startup Verification

| Service | Result |
|---|---|
| Backend (`uvicorn main:app`, :8691) | **Boots clean in ~2s.** `/api/health` → 200 `{"status":"healthy"}`. Boot log confirms `Session store initialized at /home/dennisccy/Git/finovae_strategy_platform/.data/backtests` (durable path active via `.env` override). |
| Frontend (Vite via `next-vite-shim`, :3691) | **Boots clean.** `VITE v5.4.21 ready in 161 ms`; serves React app HTML at HTTP 200. |

`GET` API surface (all 200 — `runs/goal-money-money-iter-0/api-surface.txt`):
`/api/health`, `/docs`, `/api/models` (gpt-5.4-mini default + Claude selectable),
`/api/symbols` (populated), `/api/timeframes` (populated), `/api/sessions`
(tab list), `/api/runs` (`{"runs":[],"total_count":0}`).

## Per-Journey Baseline (developer vantage)

The **authoritative end-to-end browser pass/fail is the browser-qa-agent's** to
record (DOD: "executed … via browser-qa-agent"). As the developer in a
verify-only baseline I confirmed backend prerequisites / API contracts; rows
below state the developer-vantage status + what the QA step must still drive.

| Journey | Developer-vantage baseline | Evidence / note for evaluator |
|---|---|---|
| **J-05** Reference data loads | **PASS (API-confirmed)** — browser control-population still to be confirmed by QA | `/api/symbols` 200 (BTC/USDT, ETH/USDT, …); `/api/timeframes` 200 (1m…1d). Data path green. |
| **J-01** Backtest from NL | **PENDING browser-qa — prereqs GREEN, NOT env-blocked** | Backend up; `OPENAI_API_KEY` present; `/api/models` serves default `gpt-5.4-mini`. Requires browser + live LLM/Binance; QA must execute. |
| **J-02** Inspect/browse run history | **PENDING browser-qa (depends on a completed J-01 run)** | `/api/sessions` list 200; `/api/runs` 200 (currently 0 runs). Open path `/api/sessions/{id}` returns 200 but **eagerly ~51 MB** (anti-goal posture below — functional, not a failure). |
| **J-03** Walk-forward validation | **PENDING browser-qa (depends on a completed run + LLM)** | Prereqs green; no code reason to expect failure. QA must execute from a run detail view. |
| **J-04** AI insights | **PENDING browser-qa (depends on a completed run + LLM)** | `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` present → not env-blocked. QA must execute. |
| **J-06** Warm-cache re-run | **PENDING browser-qa (depends on a J-01 run, same params)** | Warm path likely functional even though cache layout violates the single-Parquet anti-goal (per-day CSV fan-out — see below); QA must confirm the 2nd run renders. |

> Net: **no journey is environmentally blocked** (both LLM keys present). J-05's
> data path is green at the API. J-01–J-04 and J-06 are runnable and await
> authoritative browser execution by the QA step; the evaluator should seed
> initial per-journey status from the QA results, not from this row set alone.

## Pre-existing Anti-Goal Postures (OBSERVATION ONLY — not remediated)

All three iter-spec-named postures are **present in the current code** and
recorded here for the evaluator. **No remediation performed** (verify-only;
fixes belong to `Mode: next`).

1. **OHLCV cache = per-day CSV fan-out (VIOLATION of single-Parquet anti-goal).**
   `apps/backend/data/loader.py` — `_get_daily_cache_path()` →
   `{cache_dir}/{symbol}/{tf}/{YYYY-MM-DD}.csv`; `load()` loops day-by-day
   writing one **CSV per calendar day** via `_save_to_csv`/`_load_from_csv`;
   `clear_cache()` globs `*.csv`. This is exactly the "one CSV or file per
   calendar day" the anti-goal forbids — and contradicts `apps/backend/CLAUDE.md`
   which *claims* "cached … as Parquet files … `{symbol}_{timeframe}_{start}_{end}.parquet`".
   Cache dir also defaults to `/tmp` (`os.getenv("MARKET_DATA_CACHE_DIR","/tmp")`,
   line 51); `.env` sets `MARKET_DATA_CACHE_DIR=/tmp/market_data` (still volatile,
   acceptable for OHLCV cache per goal.md — only the *store* must be durable).

2. **`BACKTEST_STORE_DIR` code default is volatile `/tmp/backtests`.**
   `apps/backend/backend/session_store.py:26` —
   `BASE_DIR = Path(os.environ.get("BACKTEST_STORE_DIR", "/tmp/backtests"))`.
   The anti-goal says this MUST NOT default to a volatile `/tmp` path. **Durability
   here holds ONLY via the `.env` override** (`BACKTEST_STORE_DIR=/home/dennisccy/Git/finovae_strategy_platform/.data/backtests`,
   confirmed in the boot log). The **code default itself remains an anti-goal posture**.
   Same pattern in `directions_cache.py` (`DIRECTIONS_CACHE_DIR` default `/tmp/initial_directions`).

3. **`GET /api/sessions/{id}` eagerly parses full per-iteration payloads.**
   `apps/backend/backend/session_routes.py:149–156` — `get_session` loops every
   iteration dir calling `read_iteration_full()`, returning all
   `result`/`rating`/`insights`/`timeframeResults`/`scriptCode` in
   `iterationHistory`. Hard evidence
   (`runs/goal-money-money-iter-0/antigoal-sessions-evidence.txt`): one session →
   **`GET /api/sessions/{id}` = HTTP 200, 53,920,916 B (~51 MB), 26 iterations**
   each with full result/rating; the lightweight metas path
   `GET /api/sessions/{id}/iterations` = 1,273,461 B (~42× smaller), and a
   per-iteration detail endpoint already exists. The open path violates the
   lazy-load anti-goal.

## Known Issues

- **`test_directions_cache` failure** (above) is the only red in the suite —
  pre-existing, off the critical journey path. Recorded for a later iteration.
- **Cleanup side effect (self-healed):** the bounded frontend smoke killed stray
  Vite procs on :3691 via `lsof -ti :PORT | kill`. That selector also matched a
  long-running **Chrome network-service utility** (it held a *client* socket to
  the frontend), which received the kill. Chrome **auto-respawned the network
  service** (verified: 17 chrome procs, 5 network-service utilities live
  afterward) — Chrome is healthy and the downstream **browser-qa-agent (Chrome
  MCP) is unaffected**. Lesson for future iterations: filter port-kill selectors
  to `LISTEN` state only (don't `kill` every PID `lsof -ti :PORT` returns).
- **Two foreign `uvicorn` processes** persist on this shared host on non-8691
  ports — other projects' backends (the deterministic offset-port scheme exists
  for exactly this). Not my orphans; intentionally not killed (would disrupt
  other work). My backend (:8691) and frontend (:3691) are both confirmed
  stopped with ports released.
- **`.gitignore` shows ` M`** — this predates iteration 0 (present in the
  session-start git snapshot); **not introduced by this iteration**. Flagged for
  honesty; it is not a source/journey-relevant change.

## Baseline Artifacts (for the goal-evaluator)

Under `runs/goal-money-money-iter-0/`:
- `backend-pytest.log` — full test run (107 passed, 1 failed)
- `api-surface.txt` — every `GET` endpoint + status/size
- `antigoal-sessions-evidence.txt` — eager-parse ~51 MB vs lightweight path proof
- `backend-boot.log` — clean boot + durable store-init line
- `frontend-boot.log` — clean Vite boot

The evaluator should set initial per-journey status in `journey-history.json`
from the **browser-qa-agent** results (J-05 data path already API-green; no
journey is environmentally blocked) and note the three pre-existing anti-goal
postures as targets for `Mode: next` iterations.
