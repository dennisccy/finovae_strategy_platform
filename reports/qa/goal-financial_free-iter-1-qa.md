# goal-financial_free-iter-1 QA Report

**Verdict:** PASS

**Phase:** goal-financial_free-iter-1
**Date:** 2026-05-23
**Agent:** qa (MODE 2 — validation)
**Frontend Present:** no (backend-only — browser checks skipped per agent policy)

## Summary

Backend-only Layer-1 auto-session core (J-07 start + J-09 terminal/best-marking).
The full hermetic backend suite passes (164 passed / 1 deselected live smoke / 1
pre-existing unrelated failure), all 40 new auto-session tests pass, the three
invariant tests pass, and live API-grounded checks against the running backend
(`http://localhost:8692`) confirm the error/validation surface. No regressions
introduced. Verdict: **PASS**.

## Step 1 — Artifact verification

| Artifact | Status |
|----------|--------|
| `docs/handoffs/goal-financial_free-iter-1-dev.md` | ✅ present |
| `reports/reviews/goal-financial_free-iter-1-review.md` | ✅ present — **PASS_WITH_NOTES** |
| `runs/goal-financial_free-iter-1/status.json` | ✅ present (`current_step: browser_qa_complete`) |
| `reports/qa/goal-financial_free-iter-1-test-plan.md` | ✅ present (16 test cases) |
| New source: `auto_session.py`, `auto_session_routes.py`, `result_serialization.py` | ✅ present |
| New tests: `test_auto_session.py`, `test_auto_session_routes.py`, `test_auto_session_live.py` | ✅ present |

Review verdict is PASS_WITH_NOTES (acceptable to proceed). The two review items are
non-blocking: a MINOR note (sync store calls on the loop vs `asyncio.to_thread` —
low impact, backtest/LLM work is correctly awaited + semaphore-guarded) and a NOTE
(transitional in-browser scorer duplicate, slated for J-10 removal — flagged for the
coherence-auditor).

## Step 2 — Backend test suite (exact output)

Command: `cd apps/backend && .venv/bin/python -m pytest` (hermetic default; live smoke deselected via `-m "not integration"`)
Full log: `reports/qa/goal-financial_free-iter-1-test.log`

```
=========== 1 failed, 164 passed, 1 deselected, 4 warnings in 6.03s ============
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip
```

- **164 passed**, 1 deselected (key-gated live smoke), **1 failed**.
- The single failure is `test_directions_cache.py::test_write_and_read_full_round_trip`
  (`timeframeResults` round-trip; `assert 0 == 1`). It is the **pre-existing,
  unrelated** known red explicitly carried forward by the spec (Capability #10
  nice-to-have). `git status` confirms `directions_cache.py` and its test were
  **not touched** this iteration. Not a regression; not a blocker.
- Invariant tests pass — re-ran `test_lookahead.py test_determinism.py test_sandbox.py`: **39 passed**.
- New auto-session tests — re-ran `test_auto_session.py test_auto_session_routes.py`: **40 passed**.

## Step 3 — Frontend tests

SKIPPED — backend-only iteration (Frontend Present: no).

## Step 3.5 — Functional test plan execution

Verification is API-grounded (per the documented Chrome-MCP headless render-throttle).
Hermetic loop test cases are verified by their named tests in the passing suite;
error/validation cases were additionally exercised **live** against the running
backend (`http://localhost:8692`, `/api/health` → 200).

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---------|------|------|----------|--------|---------|-------|
| TC-01 | Start headless session (J-07) | api | 200 + sessionId + status running/queued; session appears in `GET /api/sessions` | `test_create_returns_200_with_session_and_status` + `test_created_session_appears_immediately_in_sessions_list` pass | PASS | Hermetic (injected fake pipeline) — live start needs LLM (covered by TC-15) |
| TC-02 | Terminal: criteria-met (J-09) | api | terminal `criteria-met`, best marked, all targets satisfied | `test_criteria_met_when_baseline_satisfies_targets`, `test_targets_all_supplied_satisfied`, `test_targets_one_unmet_fails` pass | PASS | |
| TC-03 | Terminal: budget-exhausted hard cap (J-09) | api | `budget-exhausted`, iterationsDone == maxIterations, no over-cap iteration | `test_budget_exhausted_runs_exactly_max_iterations` passes | PASS | hard-budget anti-goal |
| TC-04 | Same-artifacts / no parallel store | artifact | iterations full result+rating via standard endpoint; activity+suggestions; via `session_store` | `test_artifacts_are_byte_shape_compatible_with_manual_run` passes | PASS | serializer extracted to one source (`result_serialization.py`) |
| TC-05 | Persisted autoRun + restart + orphan reconcile | api | round-trips via session.json; fresh read shows it; orphan → `interrupted` | `test_auto_run_status_round_trips_through_session_json`, `test_reconcile_orphaned_running_to_interrupted`, `test_get_session_exposes_auto_run_block` pass | PASS | persisted-status anti-goal |
| TC-06 | Robust best WFE-gated + min-trades floor | api | WFE-failing/under-floor not best; robust candidate best | `test_best_is_wfe_gated_not_highest_raw_return`, `test_select_best_excludes_wfe_failing_high_return`, `test_wfe_gate_eligibility`, `test_score_zero_trades_is_negative_infinity`, `test_drawdown_penalty_lowers_score` pass | PASS | robust-best anti-goal |
| TC-07 | Budget tracker immutable & hard | api | immutable; halts before exceeding caps | `test_budget_tracker_is_frozen`, `test_budget_exceeded_on_iterations`, `test_budget_exceeded_on_wall_clock`, `test_with_round_completed_returns_new_instance` pass | PASS | hard-budget anti-goal |
| TC-08 | Stop infrastructure | api | 200; flips stopRequested; → `stopped`; best retained; no over-stop iteration | `test_stop_request_transitions_to_stopped_keeping_best`, `test_stop_running_flips_persisted_flag` pass | PASS | infra for J-11 (not claimed) |
| TC-09 | Non-blocking launch | api | start returns before loop done; `GET /api/sessions` responsive | `test_post_returns_before_loop_completes_and_get_stays_responsive` passes | PASS | non-blocking anti-goal (awaits backtest semaphore) |
| TC-10 | Open-universe rejected (J-12 deferral) | api | clear 4xx | **Live: HTTP 400** — `"Open-universe runs (omitted symbol/timeframe) are not supported yet — pin both 'symbol' and 'timeframe'. (Open-universe is J-12 / Layer-2.)"`; `test_open_universe_rejected_4xx` + `test_missing_symbol_only_rejected_4xx` pass | PASS | clear explanatory message, not silently defaulted |
| TC-11 | Missing required budget | api | 422 for missing budget and missing max_iterations | **Live: HTTP 422** both cases (`missing` body.budget; `missing` body.budget.max_iterations); `test_missing_budget_is_422`, `test_missing_max_iterations_is_422` pass | PASS | |
| TC-12 | Stop unknown / already-terminal | api | unknown → 404; terminal → idempotent 200 | **Live: unknown → HTTP 404** (`"Auto-session does-not-exist-xyz not found"`); `test_stop_unknown_session_404`, `test_stop_already_terminal_is_idempotent_200`, `test_stop_on_manual_session_404` pass | PASS | |
| TC-13 | Backend regression + invariants | api | suite green except known red; invariants pass | 164 passed / 1 pre-existing unrelated red; invariants 39 passed | PASS | only red is untouched `test_directions_cache` |
| TC-14 | Secret hygiene | artifact | no key/secret strings in artifacts | `test_no_secrets_in_artifacts` passes | PASS | |
| TC-15 | Live smoke, tiny real budget (key-gated) | api | real terminal state + best marked, else documented skip | Dev handoff documents the live smoke ran and **passed (1 passed in 317s)** against the real pipeline (gpt-5.4-mini, real Binance OHLCV, sandbox, walk-forward), reaching a real terminal state with a marked best; `test_live_auto_session_reaches_terminal_with_best` exists (`@pytest.mark.integration`). `OPENAI_API_KEY` not exported into the QA env (present in `apps/backend/.env`). QA did not re-execute the ~5-min paid run; dev evidence is documented (not silently passed). | PASS | per spec the requirement is a real run or a documented skip — dev provided a documented real pass |
| TC-16 | get_session payload not worsened | artifact | additive tiny `autoRun`; lazy loading unchanged | `test_get_session_exposes_auto_run_block`, `test_manual_session_has_null_auto_run` pass; review confirms addition is `"autoRun": meta.get("autoRun")` only | PASS | tiny block (strings/ids/int counters); lazy iteration loading unchanged. Carry-forward verdict on the ~245KB `equity_curve` embed deferred to coherence-auditor (fix out of scope, not worsened) |

**16/16 test cases passed.**

## Step 4 — Chrome MCP browser checks

SKIPPED — backend-only phase (Frontend Present: no). Per the documented Chrome-MCP
headless render-throttle, J-07's "appears as a session" is verified via the backend
endpoints the UI calls (`GET /api/sessions` — TC-01), the sanctioned API-grounded
substitute.

## Step 4b — UI Evolution Audit

SKIPPED — backend-only phase (Frontend Present: no). No new UI surface this iteration
by design; the created session renders through the existing session-open path.

## Blockers

None.

## Notes

- The single failing test (`test_directions_cache::test_write_and_read_full_round_trip`)
  is pre-existing, unrelated, and explicitly the only known red carried forward by the
  spec. Files untouched this iteration per `git status`. Not a blocker.
- Review notes (sync store calls vs `asyncio.to_thread`; transitional in-browser scorer
  duplicate) are non-blocking and routed to the coherence-auditor — not QA blockers.
- No servers were started by QA (the runner manages the backend on port 8692); nothing to kill.
