**Verdict:** PASS

# goal-financial_free-iter-6 QA Report

**Phase:** goal-financial_free-iter-6 (RE-LAND of J-15 — global-history warm start, opt-out-able)
**Date:** 2026-05-24
**Mode:** QA Validation (MODE 2)
**Frontend Present:** no (backend-only; reuses existing `auto-run` Activity-Log render path)
**Reviewer verdict:** PASS_WITH_NOTES

---

## Step 1 — Required Artifact Verification

| Artifact | Status |
|----------|--------|
| `docs/handoffs/goal-financial_free-iter-6-dev.md` | ✅ present, status `complete` |
| `reports/reviews/goal-financial_free-iter-6-review.md` | ✅ present, verdict **PASS_WITH_NOTES** |
| `runs/goal-financial_free-iter-6/status.json` | ✅ present, `changed_files` non-empty, `tests_run: true` |
| `reports/qa/goal-financial_free-iter-6-test-plan.md` | ✅ present (17 test cases) |

All required artifacts present. Review verdict is PASS_WITH_NOTES (acceptable to proceed).

---

## Step 2 — Backend Test Results (exact)

Command: `cd apps/backend && .venv/bin/python -m pytest`
Log: `reports/qa/goal-financial_free-iter-6-test.log`

```
=========== 1 failed, 231 passed, 2 deselected, 4 warnings in 6.78s ============
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip
```

The single failure is **exactly** the documented, pre-existing, out-of-scope red named in
the spec (DoD item: "the full hermetic backend suite is green except the single known
pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip`").
It fails on HEAD too and is untouched by this diff (not in `git diff --name-only HEAD`).
**All 231 other tests pass**, including all 20 new J-15 tests and the J-12/J-13/J-14
no-regression tests (which set no `history_scope`).

Targeted re-run: `tests/test_history_warmstart.py` + `tests/test_auto_session_routes.py`
→ **42 passed**.

---

## Step 3 — Frontend Tests

SKIPPED — Frontend Present: no (zero new FE code; J-15 reuses the existing `auto-run`
Activity-Log render branch).

---

## Step 3.5 — Functional Test Plan Results

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---------|------|------|----------|--------|---------|-------|
| TC-00 | Persistence gate (LOAD-BEARING) | artifact | apps/ diff non-empty w/ 4 req paths; history_planner.py present; grep matches; status.json changed_files+tests_run; handoff matches diff | `git diff --stat HEAD -- apps/backend/` = 7 files (+1123/−9) incl. all four required paths; `history_planner.py` PRESENT; grep `history_scope` returns both backend files; status.json `changed_files` (7) + `tests_run:true`; handoff "Files Changed" == `git diff --name-only` | **PASS** | The single reason iter-5 failed — verified clean against the real tree, not a worktree/cache. |
| TC-01 | Invalid history_scope → 422 | api | 422 citing allowed set | Live POST to `:8691` → HTTP **422**, body: `history_scope must be "global" or "this-run"`. Hermetic `test_history_scope_invalid_value_is_422` passes. | **PASS** | |
| TC-02 | `global` emits cited planner entry & promotes top family | api | ≥1 cross-run citation + first promoted family == prior top family | Hermetic endpoint-layer tests `test_global_warm_start_cites_prior_and_promotes_top_family` + `test_global_endpoint_layer_activity_log_and_iteration_family` pass (assert activityLog citation + first PROMOTEd `(symbol,timeframe)` == mined top family). | **PASS** | Endpoint-layer proof (documented Chrome-MCP-throttle substitute; zero new FE render path). |
| TC-03 | `this-run` / omitted opt-out — no citation | api | Zero cross-run citation; deterministic order | `test_this_run_opt_out_no_cross_run_citation` + `test_omitted_history_scope_behaves_byte_equivalent_to_today` pass. Live route tests accept this-run/omitted → 200. | **PASS** | |
| TC-04 | Read-only mining: prior artifacts byte-identical | artifact | All prior artifacts byte-identical pre/post | `test_read_only_mining_leaves_prior_artifacts_byte_identical` passes. | **PASS** | Anti-goal: read-only mining honored. |
| TC-05 | Meta-only reads (no eager full parse) | artifact | Miner uses read_iteration_meta, not read_iteration_full | Mining path (`auto_session.py:458–497`) uses `derive_session_tabs`/`read_session_meta`/`read_iteration_meta` only; `test_mining_is_meta_only_does_not_parse_full_iteration` passes. (`read_iteration_full` at :980 is baseline-node load, not mining.) | **PASS** | iter-0 lesson honored. |
| TC-06 | Prompt-cache marker + planner ≤ once | artifact | `cache_control:{"type":"ephemeral"}` present; call count 1 (global) / 0 (this-run) | Marker at `history_planner.py:180`; `test_history_planner_system_prompt_carries_ephemeral_cache_control` passes; call-count assertions covered in warm-start tests. | **PASS** | |
| TC-07 | Planner failure non-fatal (deterministic fallback) | artifact | Falls back to deterministic order, reaches terminal state | `test_planner_failure_falls_back_to_deterministic_order` + `test_history_planner_malformed_output_raises_for_deterministic_fallback` pass. | **PASS** | |
| TC-08 | Budget compliance (J-13) | artifact | Planner usage in BudgetTracker; pre-exhausted → budget-exhausted before SCREEN | `test_planner_token_usage_threaded_into_budget` + `test_pre_exhausted_budget_terminates_before_planner_and_screen` pass. | **PASS** | |
| TC-09 | Bounded seed preserved (no fan-out) | artifact | No `(symbol,tf)` outside seed; count ≤ SEED_UNIVERSE_MAX | `test_global_run_never_enumerates_outside_seed_universe` passes. | **PASS** | |
| TC-10 | Coherence: one RobustScorer / one BudgetTracker | artifact | One scorer, one budget; no second scoring path | Exactly one `class RobustScorer` (:242) + one `class BudgetTracker` (:127); miner reuses `scorer.score()` (:497); `test_warm_start_uses_single_robust_scorer_instance` passes. | **PASS** | |
| TC-11 | No secrets in activity log / artifacts | artifact | Zero `api_key`/`sk-` material | `test_no_secrets_in_warm_start_artifacts` passes. | **PASS** | |
| TC-12 | `global` with empty store degrades gracefully | api | No citation, deterministic order, terminal state, no crash | `test_global_empty_store_degrades_gracefully` passes. | **PASS** | |
| TC-13 | `shared/contracts.py` frozen (not in diff) | artifact | contracts.py + frontend absent from diff | `git diff --name-only HEAD` → neither `shared/contracts.py` nor any `apps/frontend/**` present. | **PASS** | |
| TC-14 | Suite health (one known red allowed) | artifact | Full suite green except known pre-existing red | 231 passed, 1 failed = the documented `test_directions_cache` red only. | **PASS** | |
| TC-15 | No-regression J-12/J-13/J-14 pass unchanged | artifact | J-12/J-13/J-14 hermetic tests pass with no edits | `tests/test_auto_session.py` + `tests/test_auto_session_routes.py` pass; J-12/J-13/J-14 set no `history_scope` and pass under new `this-run` default. | **PASS** | |
| TC-16 | Live key-gated run pair (OPTIONAL) | api | Citation+family match (run #2), no citation (run #3), WF ≥1 window | **SKIPPED (not FAIL)** — no LLM/Binance API key configured in this environment. Per test plan, key-gated and explicitly non-blocking; J-15 closed at endpoint layer. | **SKIP** | |

**15/15 gating test cases passed; 1 optional key-gated case skipped (non-blocking).**

---

## Step 4 — Chrome MCP Browser Checks

SKIPPED — backend-only phase (Frontend Present: no). J-15 adds zero new FE render path
(reuses the `auto-run` Activity-Log branch); the display aspect is proven at the endpoint
layer via `GET /api/sessions/{id}.activityLog`, the documented Chrome-MCP-headless-throttle
substitute. The optional pixel capture is explicitly non-blocking per the spec and does NOT
gate J-15.

## Step 4b — UI Evolution Audit

SKIPPED — Frontend Present: no. Spec-justified: the only user-visible surface is a new
warm-start planner-decision Activity-Log entry rendered through the pre-existing `auto-run`
entry type; no new component/page/button/render branch.

---

## Anti-Goal / Coherence Compliance

- ✅ Read-only mining (artifacts byte-identical, TC-04); meta-only reads (TC-05).
- ✅ Prompt-cache marker present; planner ≤ once per run (TC-06).
- ✅ Opt-out honored — `this-run`/omitted produce no citation (TC-03).
- ✅ Bounded seed preserved, no fan-out (TC-09).
- ✅ Exactly one `RobustScorer` + one `BudgetTracker` (TC-10).
- ✅ No secrets in activity log/artifacts (TC-11).
- ✅ `shared/contracts.py` frozen; no frontend touched (TC-13).
- ✅ Budget enforced incl. planner usage; pre-exhausted terminates before SCREEN (TC-08).

---

## Blockers

None.

The only red test (`test_directions_cache.py::test_write_and_read_full_round_trip`) is the
documented pre-existing, out-of-scope failure explicitly permitted by the spec DoD; it is
not in this iteration's diff and fails on HEAD as well. TC-16 (live key-gated run) is skipped
for lack of an API key and is explicitly non-blocking.

---

**Verdict:** PASS
