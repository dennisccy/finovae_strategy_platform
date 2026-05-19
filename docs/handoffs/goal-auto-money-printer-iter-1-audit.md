# goal-auto-money-printer-iter-1 Audit Report

**Date:** 2026-05-19
**Auditor:** Hard audit pass — skeptical, evidence-based

---

## 1. Executive Verdict

**Verdict:** PASS_WITH_GAPS

The Layer-1 headless auto-session foundation (J-07 start-via-API, J-08
track-live, J-09 terminal+best) plus the lesson-mandated J-02 right-panel
re-bind are genuinely implemented, not just summarized: the controller reuses
the real `BacktestPipeline` (verified against `pipeline.py` signatures/return
shapes), the durable `autoRun` state machine writes to `session.json`, the
budget is provably bounded, and `bestIterationId` is selected by a sound
WFE-gated robust objective. Every enumerated anti-goal holds at the
source-diff and test level (`contracts.py`/`sandbox.py`/`pipeline.py` have
zero diff; `api.py` is a 2-line router mount). The backend suite was
independently re-run by the auditor: **140 passed / 1 pre-existing
out-of-scope failure, zero new regressions**; all 16 new `test_auto_session`
tests pass; `ruff` clean. One IMPORTANT artifact-consistency issue was found
and **fixed during this audit** (the stale `ui-test-results.md` FAIL headline
contradicting the post-fix QA PASS). Remaining gaps are non-blocking and
spec-sanctioned (API-only start = J-10/iter-2; AutoRunBar staleness under
rapid multi-session switching = documented J-10/iter-2 hardening).

---

## 2. Findings

### Backend Findings

**B1 — OBSERVATION (observation): pipeline reuse path differs from the spec's named methods, but is faithful**
The spec/plan named `run()` + `execute_walk_forward()`; the implementation
instead uses `generate_strategy()` → `execute_backtest(wfv_enabled=True)` →
`generate_insights()` (`auto_session.py:316-378`). Verified against
`pipeline.py:277/389/736`: `execute_backtest` returns the exact 5-tuple
`(Optional[BacktestResult], list[str], Optional[StrategyRating], dict,
Optional[WalkForwardResult])` that the controller unpacks at
`auto_session.py:333`, and walk-forward runs *inside* `execute_backtest` via
the pipeline's own WFV — no compile/codegen/sandbox/engine reimplementation,
no bypass. This is a valid (arguably better, for an iterative refine loop)
reuse path; the spec's method list was illustrative ("e.g."). Anti-goal
"reuse BacktestPipeline, no sandbox/engine bypass" holds. No action.

**B2 — OBSERVATION (observation): `_serialize_artifacts` uses raw `jsonable_encoder`, not the manual path's clamping schema**
`auto_session.py:248` projects the result via `jsonable_encoder(result)`;
the manual path routes through `BacktestResultSchema` (clamps `max_drawdown`
to [0,1], `_safe_floats` sharpe/profit). Artifact *shape* is identical
(test `test_iteration_artifacts_match_manual_shape` + QA TC-08 byte-compare
confirm), and best-selection is unaffected (`robust_score` clamps drawdown
internally at `robust_objective.py:84`). A value-level divergence is only
possible in the rare unclamped-drawdown case. Already noted by the reviewer;
optional later-iter parity improvement. No action this iteration.

**B3 — OBSERVATION (observation): `_runner` crash handler conflates a catastrophic crash with cooperative-stop**
`auto_session.py:654` sets `status="stopped", stopReason=None` on an
unexpected background-task exception — the same terminal as a cooperative
cancel. This is defensive only: `run_auto_session` is structured never to
raise out (per-iteration failures are caught and recorded via
`_record_failed`, the loop always reaches a terminal state — proven by
`test_single_iteration_failure_does_not_hang_loop_reaches_terminal`).
Distinguishing a failed/error terminal from a user-stopped one is a
reasonable later refinement. No action.

### Frontend Findings

**F1 — GAP (gap): headless run has no UI start control (API-only)**
Starting a headless run is `POST /api/auto-sessions` only — no button in the
UI. This is **spec-mandated** (GOAL: "A user *or a script* makes one POST
call"; the UI button rewire is explicitly J-10/iter-2, OUT OF SCOPE) and is
correctly documented in `user-visible-changes.md` "Not Visible Yet" and the
ux-regression review. Accepted as a documented, intentional, spec-scoped gap
— not an accidental hidden capability.

**F2 — GAP (gap): `AutoRunBar` can show a stale terminal status under rapid multi-session switching**
Documented by QA (TC-17 non-blocking note) and the dev Known Issues: when
many `SessionContainer`s are mounted and the user switches sessions rapidly,
a freshly-opened still-running session's strip can briefly show a stale
terminal. Mitigated in practice by the session-list running spinner (which
correctly indicates "running"), and all J-08 journey outcomes were
independently reproduced. Deferred to J-10/iter-2 ownership/concurrency
hardening. Acceptable for iter-1.

**F3 — OBSERVATION (observation): J-02 root-cause fix is correct and complete**
Traced end-to-end: the stale hook-lifetime `loadedDetailIdsRef` set (which
went stale when history was polled back to lightweight and permanently
blocked re-fetch) is removed; the lazy-detail effect guard now keys off the
node's own authoritative `result` plus an in-flight `loadingDetailIdRef`
(`useBacktest.ts:1698-1706`); `loadIterationDetail` re-checks both
(`useBacktest.ts:1649-1651`, clears in `finally` 1688); and
`key={selected.id}` on `<IterationDetailView>` (`IterationPanel.tsx:198`)
remounts the detail subtree per selected run. The manual in-memory
history path is not regressed (a node retaining its in-memory `result`
short-circuits the guard — no extra fetch). Confirmed by QA TC-19 and
UT-07/UT-11/UT-12.

### Test Findings

**T1 — OBSERVATION (observation): test quality is strong, assertions tight**
`test_auto_session.py` asserts exact values (`gen_calls == 2`,
`stopReason == "budget-exhausted"`, `currentIteration == 2`,
`maxIterations == HARD_MAX_ITERATIONS`), covers failure/edge paths
(gen_raise, bt_none, cooperative-cancel, clamp, safe-default, no-secrets),
and the robust-objective test directly proves the anti-goal (a
high-raw-return WFE-failing/over-leveraged candidate is NOT selected). The
event-loop guard (`test_headless_loop_does_not_block_event_loop`) is a real
heartbeat sampler with a strict 0.5 s bound (spec bound is 3 s) that fails
pre-fix. Determinism via stubbed LLM/Binance is appropriate (live path
exercised by browser-QA). No accidental-pass setups detected.

**T2 — IMPORTANT (fixed): `ui-test-results.md` carried a stale FAIL verdict contradicting the post-fix QA PASS**
The canonical UI test artifact (a mandatory UI-visibility artifact) still
showed **Browser QA Verdict: FAIL** (UT-03/UT-06), reflecting the *first*
browser-QA run *before* the B1/B2/B3 fixes. The B2 (`App.tsx` discovery
poll) and B3 (`IterationDetailView` BestBadge) fixes are present in source
(diffs verified), B1 (event-loop offload) has a passing guard test, and all
three surfaces were re-validated by the QA MODE-2 browser run
(TC-17/TC-18/TC-06 PASS, with post-fix evidence screenshots present on disk:
`UT-06-expanded-best.png`, `TC-17-*`, `TC-18-J09-terminal-best.png`). The
stale FAIL contradicted the QA PASS and would mislead any reader and trip
the closure consistency gate. **Fixed during this audit**: updated the
headline to `PASS (post-fix)`, added a reconciliation notice, and appended a
fully evidence-grounded "Post-Fix Reconciliation" section (no fabricated
browser steps — cites the QA MODE-2 results and the on-disk post-fix
evidence). The original pre-fix content is preserved verbatim for audit
trail.

---

## 3. Domain Assessment

The core domain logic — the robust objective — is correct and defensible.
`robust_objective.py`: when walk-forward data exists the base reward is the
out-of-sample risk-adjusted return (`oos_sharpe`); without WF the in-sample
Sharpe is heavily discounted (×0.25) because an un-validated strategy is
untrustworthy; drawdown (clamped [0,1], ×2 penalty) and over-leverage
(×0.5 per unit above 1.0) are penalized; failing any hard gate (WF present,
WFE ≥ threshold, min-trades floor) applies a fixed −1000 penalty so a
gate-failing candidate can **never** outrank a gate-passing one regardless of
raw return. `_finite` collapses inf/nan to a very-low finite value (never
emits NaN/Infinity). `targets_met` returns False on empty/None targets (so a
no-targets run can only stop on the hard budget, never `criteria-met` — exactly
the spec semantics), and `min_wfe` additionally requires real WF data.
`select_best` with `require_targets=True` filters to target-satisfying
candidates (guaranteeing J-09's "criteria-met best meets every target"
invariant) with a global-best fallback so a best is always marked. The
bounded-loop control (`_resolve_budget`: absent/≤0 → DEFAULT 3, clamp to
HARD_MAX 50; budget/cancel checked *before* each round) makes an unbounded
loop structurally impossible — verified by
`test_huge_max_iterations_is_clamped_never_unbounded` and
`test_loop_stops_exactly_at_max_iterations` (no "one more round"). Durability
(`_update_autorun` read-update-write of `session.json` every iteration and
transition, all offloaded via `asyncio.to_thread`) is real and survives a
fresh store read (restart proxy `test_autorun_status_persisted_durably`).

Anti-goal scorecard (independently re-verified):

| Anti-goal | Status | Evidence |
|---|---|---|
| Same file store / no schema fork | ✅ | `session_store` writers; QA TC-08 byte-identical to manual |
| Durable persisted `autoRun` | ✅ | `_update_autorun`→`session.json`; `test_autorun_status_persisted_durably` |
| Hard caps → unbounded loop impossible | ✅ | `_resolve_budget`; clamp/default tests; budget checked pre-round |
| `BacktestPipeline` reused, no bypass | ✅ | pipeline/sandbox/contracts zero diff; real 5-tuple unpacked |
| Best by robust objective, not raw return | ✅ | `select_best`/`robust_score`; `test_robust_objective_rejects_*` |
| Event loop not blocked | ✅ | B1 offload; guard test PASS (audit re-ran 16/16); QA TC-06 |
| No secrets in artifacts | ✅ | `test_no_secrets_written_into_artifacts`; QA TC-09 |
| `contracts.py` frozen, no new infra/DB | ✅ | zero diff; local Pydantic DTOs; no celery/redis/sql import |
| Lazy-load `GET /api/sessions/{id}` | ✅ | only `meta.get("autoRun")` added; heavy keys absent (test + TC-03) |
| Legacy in-browser loop untouched | ✅ | `startAutoRun` zero diff (coexistence is spec-expected) |

No anti-goal violation. Definition of Done items 1–5 verified in code; UI
visibility artifacts (items 6–8) all present and now mutually consistent
after the T2 fix.

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| 1 | Important | `reports/phase-goal-auto-money-printer-iter-1-ui-test-results.md` | Reconciled the stale pre-fix `FAIL` headline → `PASS (post-fix)`; added an auditor reconciliation notice and an evidence-grounded "Post-Fix Reconciliation" section (B1/B2/B3 fixes mapped to source diffs + QA MODE-2 TC-17/TC-18/TC-06 + on-disk post-fix screenshots; backend suite re-run 140/1). Original pre-fix content preserved verbatim for audit trail. Resolves the QA-PASS-vs-UI-test-FAIL cross-artifact inconsistency. |

No source-code fixes were required — the implementation is correct and the
backend suite passes independently (140 passed / 1 pre-existing out-of-scope
failure, zero new regressions).

---

## 5. Recommended Next Step

**Proceed to phase closure / next iteration.** The phase goal is genuinely
achieved and the system is materially stronger and verifiable. The closure
gate should now pass — the only artifact inconsistency (stale UI-test FAIL)
was reconciled. iter-2 should carry the spec-deferred items as planned:
**J-10** (rewire the in-browser "Auto Run" button to `POST /api/auto-sessions`,
delete the legacy `startAutoRun` loop, prove backend-source-of-truth via a
mid-run reload, and harden `AutoRunBar` ownership to remove the rapid-switch
staleness gap F2) and **J-11** (the public `POST
/api/auto-sessions/{id}/stop` endpoint + UI stop control — the
`CancellationToken` and the `stopped` terminal state are already plumbed).
Optional later parity item: route `_serialize_artifacts` through
`BacktestResultSchema` for exact value parity with manual runs (B2). The
pre-existing out-of-scope `test_directions_cache` failure remains the single
failing test, as the spec permits.
