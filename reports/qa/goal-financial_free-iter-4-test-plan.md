# goal-financial_free-iter-4 Functional Test Plan

**Phase:** goal-financial_free-iter-4
**Date:** 2026-05-23
**Frontend Present:** yes

## Phase Goal

An open-universe automated run spends cheap-first: SCREENs several seed configs on the cheapest model with **no** walk-forward, PROMOTEs only the top-k survivors (k < number screened) to walk-forward + a stronger model, marks the cross-config best strictly from the WFE-gated promoted candidates — and both stages are legible in the session Activity Log.

## Test Cases

### TC-01 — `cheapest_model()` returns the min-rate catalog model
**Type:** api (unit)
**Preconditions:** `apps/backend/shared/model_catalog.py` has `cheapest_model()`; `MODEL_RATES` populated.

**Steps:**
1. Run `cd apps/backend && python -m pytest tests/test_model_rates.py -k cheapest -q` (or the test that asserts `cheapest_model()`).

**Expected outcome:** `cheapest_model()` returns the model with the minimum rate in `MODEL_RATES` (today `gpt-5.4-mini`).
**Pass criteria:** Test asserts the returned model equals `min(MODEL_RATES, key=rate)` and is `gpt-5.4-mini`; passes.

---

### TC-02 — Stage routing: SCREEN cheap+no-WF, PROMOTE stronger+WF
**Type:** api (hermetic, FakePipeline)
**Preconditions:** `FakePipeline.generate_strategy` records its `model` kwarg; `execute_calls[*].wfv_enabled` captured.

**Steps:**
1. Trigger an open-universe run through the fake pipeline (≥3 seed configs, request `model` = a non-cheapest tier).
2. Inspect `fake.execute_calls` and persisted nodes.

**Expected outcome:** All SCREEN units have `wfv_enabled=False` and `generate_strategy` called with `cheapest_model()`; all PROMOTE units have `wfv_enabled=True` and the request `model`. Persisted screened nodes show the cheap `modelUsed`; promoted nodes show the stronger `modelUsed`.
**Pass criteria:** Every SCREEN call: `wfv_enabled is False` and model == cheapest; every PROMOTE call: `wfv_enabled is True` and model == request model. Node `modelUsed` matches per stage.

---

### TC-03 — k < number screened (DEFAULT_PROMOTE_K)
**Type:** api (hermetic)
**Preconditions:** ≥3 seed configs screened; `DEFAULT_PROMOTE_K = 1`.

**Steps:**
1. Run open-universe with ≥3 distinct seed configs.
2. Count screened nodes vs WF-bearing (promoted) nodes.

**Expected outcome:** Exactly `DEFAULT_PROMOTE_K` (=1) promoted; promoted count < screened count.
**Pass criteria:** `count(WF-bearing nodes) == 1` and `count(WF-bearing nodes) < count(screened nodes)`.

---

### TC-04 — Best is WFE-gated from promoted only
**Type:** api (hermetic)
**Preconditions:** A screened-only candidate has high raw return but no walk-forward (`wfe=None`); ≥1 promoted candidate passes the WFE gate.

**Steps:**
1. Run open-universe where the highest raw-return config is screened-only and a lower-return config gets promoted with valid WFE.
2. Read `autoRun.bestIterationId`.

**Expected outcome:** Best is the promoted, WFE-gated node — NOT the high-raw-return screened-only node.
**Pass criteria:** `bestIterationId` references a promoted node satisfying the WFE gate; no screened-only node is ever marked best. (Extend/port `test_open_universe_best_is_wfe_gated_not_highest_return`.)

---

### TC-05 — Stop honored mid-SCREEN and mid-PROMOTE
**Type:** api (hermetic)
**Preconditions:** `/stop` flag toggleable mid-run.

**Steps:**
1. Issue `/stop` during the SCREEN stage; verify status and node count.
2. Repeat issuing `/stop` during the PROMOTE stage.

**Expected outcome:** Run transitions to `stopped` at next checkpoint, appends no further node, preserves best-so-far.
**Pass criteria:** Final `autoRun.status == "stopped"`; node count unchanged after stop; best-so-far preserved in both stop-timing scenarios.

---

### TC-06 — Hard budget across stages (J-13 preserved)
**Type:** api (hermetic)
**Preconditions:** token/USD cap set low enough to trip during SCREEN or before PROMOTE.

**Steps:**
1. Run open-universe with a token/USD cap reached during SCREEN.
2. Verify no unit starts past the cap and spend ≤ cap (within one-call tolerance).

**Expected outcome:** Halts with `budget-exhausted`; no SCREEN/PROMOTE unit started after the cap. `exceeded()` semantics unchanged; PROMOTE gated on `cost_exceeded()` (token/USD/wall-clock only).
**Pass criteria:** Status `budget-exhausted`; no node appended past cap; cumulative spend ≤ cap within one-generate-call tolerance. (Update `test_open_universe_stops_at_token_cap_no_config_after`.)

---

### TC-07 — J-12 invariants preserved (distinct configs, terminal within budget)
**Type:** api (hermetic)
**Preconditions:** ≥2 seed configs with differing symbol/timeframe.

**Steps:**
1. Run open-universe to completion within budget.
2. Inspect persisted iteration nodes.

**Expected outcome:** ≥2 distinct configs appear as iteration nodes; run terminates within budget; best chosen by robust score.
**Pass criteria:** ≥2 nodes with differing symbol/timeframe present; run reaches a terminal state without exceeding budget; existing open-universe tests pass with updated call-counts but unweakened invariants.

---

### TC-08 — `cost_exceeded()` checks cost caps only, not configs/iterations
**Type:** api (unit)
**Preconditions:** `BudgetTracker.cost_exceeded()` added.

**Steps:**
1. Build a tracker with `configs_done >= max_configs` but token/USD/wall-clock under caps.
2. Call `cost_exceeded()` and `exceeded()`.

**Expected outcome:** `exceeded()` is True (configs full) but `cost_exceeded()` is False (cost caps not hit) — so PROMOTE is not skipped by config exhaustion.
**Pass criteria:** `cost_exceeded()` returns False when only the configs cap is hit; returns True when any of token/USD/wall-clock cap is hit; `exceeded()` semantics unchanged.

---

### TC-09 — Error cases: per-config failure non-fatal; all-fail clean; degenerate single config
**Type:** api (hermetic)
**Preconditions:** FakePipeline can raise on a chosen config.

**Steps:**
1. Make one SCREEN config's generation/backtest fail → verify search continues.
2. Make all screened configs fail → verify clean termination.
3. Run with a single seed config → verify it promotes without crash.

**Expected outcome:** Single failure logged and skipped; all-fail terminates `budget-exhausted` with best `None`; single-config screen promotes that one config (no crash).
**Pass criteria:** (1) Run completes, failing config absent, others present. (2) Status `budget-exhausted`, `bestIterationId is None`. (3) No exception; one promoted node produced.

---

### TC-10 — Route validation unchanged (exactly one of symbol/timeframe → 400)
**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auto-sessions -H "Content-Type: application/json" -d '{"symbol":"BTCUSDT","objective":"robust"}'` (timeframe omitted).

**Expected outcome:** Request rejected with 400 (open-universe requires both or neither symbol+timeframe).
**Pass criteria:** HTTP 400 returned; route behavior unchanged from prior iterations.

---

### TC-11 — Anti-goal invariant suite stays green
**Type:** api (hermetic)
**Preconditions:** Full backend test suite runnable.

**Steps:**
1. Run `cd apps/backend && python -m pytest -q` capturing output.

**Expected outcome:** No new failures beyond the known pre-existing red `test_directions_cache::test_write_and_read_full_round_trip`. `test_lookahead`, `test_determinism`, `test_sandbox` pass; `test_pinned_path_unchanged_runs_improvement_rounds` passes (pinned path untouched).
**Pass criteria:** Suite green except the single documented pre-existing red; invariant tests all pass.

---

### TC-12 — Browser: SCREEN/PROMOTE stages legible in Activity Log (J-14)
**Type:** browser
**Preconditions:** Live BE+FE in the **same** window, uncontended foreground tab; live QA config — open-universe `POST /api/auto-sessions`, no symbol/timeframe, `objective:"robust"`, EMA fast/slow crossover NL, `model:"claude-haiku-4-5"`, short date range, `budget:{max_iterations:2, max_configs:3, generous max_tokens/max_usd}`. Health-check FE serving for the whole window (re-probe mid-run).

**Steps:**
1. Trigger the open-universe run; open the session in the UI.
2. Observe the Activity Log: a SCREEN stage header (cheap model `gpt-5.4-mini` + "no walk-forward" + candidate count), one entry per screened candidate.
3. Observe the PROMOTE stage header ("top-k of N", k<N, stronger model `claude-haiku-4-5` + "walk-forward"), one entry per promoted candidate.
4. Inspect a promoted iteration card (stronger `modelUsed` + walk-forward section) vs a screened-only card (cheap model, no WF section).
5. Save screenshots under `reports/qa/goal-financial_free-iter-4-evidence/`.

**Expected outcome:** Both stages visually distinguishable; cheap model + no-WF on SCREEN, stronger model + WF on PROMOTE with k<N; lineage (promoted node child of screened node) visible.
**Pass criteria:** Activity Log shows distinct SCREEN and PROMOTE entries matching the above; promoted card shows WF + stronger model; screened-only card shows cheap model + no WF. If pixels blank due to documented Chrome-MCP throttle, fallback to `GET /api/sessions/{id}` showing `autoRun` + activity entries **with** recorded live-service health-check.

---

### TC-13 — Browser: clear carry-forward J-08 / J-10 pixel debt
**Type:** browser
**Preconditions:** Same live window as TC-12, FE confirmed serving.

**Steps:**
1. During an active run, observe the status-strip token/USD/configs chips updating live **without** reload (J-08).
2. Reload the browser mid-run; confirm the `autoRun` status/best/progress survive the reload (J-10).
3. Save screenshots under `reports/qa/goal-financial_free-iter-4-evidence/`.

**Expected outcome:** Chips increment live without reload; post-reload UI shows the persisted run state (status, configs done, best) — proving durable-store persistence survives a browser reload.
**Pass criteria:** Token/USD/configs chips observed changing without reload; after reload the run state matches pre-reload (status + counters persisted). Throttle fallback: verify via `GET /api/sessions/{id}` snapshots before/after reload **with** health-check evidence; "services down / could not run" is NOT acceptable.

---

### TC-14 — Artifact: dev handoff + blueprint additive update
**Type:** artifact
**Preconditions:** Phase implementation complete.

**Steps:**
1. Check `docs/handoffs/goal-financial_free-iter-4-dev.md` exists.
2. Check `runs/goal-session-financial_free/state/blueprint.md` open-universe Data-Contract row Notes record J-14 staging additively; no new row, no nav change, no `blueprint.reapproval-requested` set.

**Expected outcome:** Handoff present; blueprint updated additively only.
**Pass criteria:** Both files present/updated as specified; no nav-skeleton change; no reapproval flag.

---

## Summary

Total test cases: 14
API tests (incl. hermetic unit/integration): 11 (TC-01–TC-11)
Browser tests: 2 (TC-12, TC-13)
Artifact checks: 1 (TC-14)
