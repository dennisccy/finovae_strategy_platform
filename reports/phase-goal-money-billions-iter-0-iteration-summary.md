# Iteration Summary — goal-money-billions-iter-0

**Verdict:** CONTINUE
**Iteration type:** goal-lean
**Date:** 2026-05-18
**Iteration:** 0

## Headline

Baseline (verify-only, zero code changes): 5/6 Must-have journeys already pass; J-05 fails.

## Direction

**Signal:** holding
**Why:** Baseline iteration established the starting state with zero code changes — 5/6 Must-have journeys (J-01, J-02, J-03, J-04, J-06) already pass browser QA, and J-05 fails only because `BacktestConfigBar.tsx` never calls the working `/api/symbols` / `/api/timeframes` endpoints (hardcoded timeframe literal, free-text symbol input). No regression (no prior journey state existed) and no critical anti-goal violation, so the verdict is CONTINUE. This is the first iteration with no newly-passing delta — direction is set, not yet advancing — with the minor pre-existing storage anti-goals plus the J-05 wiring defining a clear, tractable next path.

**Trend (last 1 iter):**
- Newly passing this iter: none (baseline — no prior journey state)
- Newly passing in last 1 iter total: none
- Regressions in last 1 iter: none
- Anti-goal violations in last 1 iter: 3 minor (per-day CSV OHLCV cache; `/tmp` `BACKTEST_STORE_DIR` code default; unconfirmed `/api/sessions/{id}` eager-load) — all minor, pre-existing, none introduced
- Iters with no journey state change: 1 of 1 (baseline — journey state created, no prior state to change from)

**Latest evaluator reasoning:** Baseline correctly separated already-working from to-build. All six journey screenshots independently verified: J-01/02/03/04/06 visibly pass (backtest metrics + equity curve + run history; WFE 1.26 green badge + per-window table + combined OOS curve; 10 ranked insight chips; warm re-run with 2 runs in history). J-05 fails its literal acceptance — `/api/symbols` & `/api/timeframes` are healthy but `BacktestConfigBar.tsx` never calls them (hardcoded timeframe literal, free-text symbol input).

## What was done

- Ran the baseline assessment for goal session `money-billions` — a deliberate verify-only no-op; zero source files modified (empty `git diff`, reviewer PASS).
- Booted the backend on offset port 8691, confirmed `/docs` → 200; session store initialized at durable `.data/backtests` (via `.env` override).
- Ran the backend unit suite: 107 passed / 1 failed; anti-goal invariant tests (lookahead, determinism, sandbox) all PASS. The single failure is `test_directions_cache.py` round-trip (nice-to-have, not a Must-have journey).
- Exercised all 6 Must-have journeys via browser automation with screenshot evidence.
- Verified 5/6 target journeys pass browser QA (J-01, J-02, J-03, J-04, J-06); J-05 fails.
- Recorded observable anti-goal signals: per-day CSV OHLCV cache (~29,182 `.csv`, 0 `.parquet` in `/tmp`), `BACKTEST_STORE_DIR` `/tmp` code default, no SQLite/DB; flagged a possible `/api/sessions/{id}` eager-load signal for full-mode QA.

## What's left

- Journey J-05 (Reference data loads) failing — `/api/symbols` & `/api/timeframes` work but `BacktestConfigBar.tsx` never calls them (hardcoded timeframe literal line ~61; free-text symbol input lines ~43–54).
- Anti-goal (minor, pre-existing): OHLCV cache is per-day CSV under `/tmp` (`data/loader.py:50–63`) — not a single Parquet file per (symbol, timeframe).
- Anti-goal (minor, pre-existing): `BACKTEST_STORE_DIR` code default is `/tmp/backtests` (`session_store.py:26`) — durable only via the `apps/backend/.env` override.
- Unconfirmed signal: `GET /api/sessions/{id}` may eagerly inline full per-iteration `result`/`rating` — needs full-mode QA against `session_routes.py`.
- J-04 "OOS-aware when walk-forward data exists" sub-clause not separately verified (insights were generated before the J-03 walk-forward run).
- Pre-existing test failure: `test_directions_cache.py::test_write_and_read_full_round_trip` (nice-to-have; out of scope at baseline).

## Next step

Two tractable workstreams for upcoming `Mode: next` iterations: (1) **J-05 (frontend wiring only):** make `apps/frontend/src/components/BacktestConfigBar.tsx` fetch `/api/symbols` and `/api/timeframes` and populate the symbol + timeframe controls from them (replace the hardcoded timeframe literal at line ~61 and the free-text symbol input at lines ~43–54). Do not modify the backend endpoints — they already work. (2) **Storage anti-goals (highest value; aligns with the known pending Parquet/durable-store migration):** migrate `apps/backend/data/loader.py` from per-day CSV under `/tmp` to a single Parquet file per (symbol, timeframe) with a warm-cache read path, and change the `BACKTEST_STORE_DIR` default in `apps/backend/backend/session_store.py:26` off volatile `/tmp` to a durable in-repo path. This is architecture-level, must preserve the determinism / no-lookahead / warm-load-≥10× invariants, and carries regression risk to already-passing J-01 and J-06 — hence the `full` depth recommendation for the next iteration. A later full-mode iteration should also (a) confirm or refute the `/api/sessions/{id}` eager-load signal against `session_routes.py`, and (b) verify the J-04 "OOS-aware when walk-forward data exists" sub-clause by regenerating insights after a walk-forward run.

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-money-billions-iter-0.md |
| Dev handoff | — | docs/handoffs/goal-money-billions-iter-0-dev.md |
| Review | PASS | reports/reviews/goal-money-billions-iter-0-review.md |
| Browser QA | FAIL | reports/phase-goal-money-billions-iter-0-ui-test-results.md |
| Goal evaluation | CONTINUE | runs/goal-session-money-billions/iter-0/eval.md |
| Journey history | — | runs/goal-session-money-billions/state/journey-history.json |
