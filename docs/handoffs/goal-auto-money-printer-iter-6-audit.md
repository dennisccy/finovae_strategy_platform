# goal-auto-money-printer-iter-6 Audit Report

**Date:** 2026-05-20
**Auditor:** Hard audit pass — skeptical, evidence-based

---

## 1. Executive Verdict

**Verdict:** PASS

Iter-6 delivers the J-16 demonstration as specified: every PROMOTE `complete`
activity entry now carries an operator-readable robust-best rationale string,
the WF-validated winner is plainly tagged `"Best — WF-validated …"`, an
overfit-tempting / WFE-failing candidate is plainly tagged `"Not best — WFE
X.XX below 0.30 gate"`, and a terminal `Robust-best: <id> selected over …`
summary appears at the end of any open-universe run with ≥ 2 PROMOTEs. The
implementation is strictly additive (presentation only); `robust_objective.py`,
`shared/contracts.py`, `session_store.py`, `pipeline.py`, `sandbox.py`, and
`backtest/` are byte-empty diffs, and `_run_pinned` is byte-identical (4892
chars HEAD vs working tree). All 16 Must-have journeys are satisfied (J-01–J-15
preserved by structural assertion + the existing `insight_calls == 3` regression
guard; J-16 satisfied by the deterministic primary proof + browser
corroboration with screenshots).

---

## 2. Findings

### Backend Findings

**B1 — OBSERVATION (no action): Snapshot semantics ordering quirk in the J-16 demonstration test**
`apps/backend/tests/test_auto_session.py:2240-2320` — to make the WFE-failing
candidate plainly "Not best" at write time, the deterministic primary test
gives the WF-validated candidate the HIGHER in-sample Sharpe so it is promoted
FIRST and becomes `best_id` before the overfit-tempting candidate is promoted
second. This is documented honestly in `docs/handoffs/goal-auto-money-printer-iter-6-dev.md`
§Snapshot Semantics and explicitly called out in IN-SCOPE spec text ("each
PROMOTE's `detail` is a write-time snapshot"). The behavior is correct (the
round-final `bestIterationId` is the live source of truth for the `Best`
badge), and re-evaluation across rounds is explicitly OUT OF SCOPE. No fix
needed.

**B2 — OBSERVATION (no action): TC-01 browser run produced two PROMOTEs where both gates failed**
`reports/qa/goal-auto-money-printer-iter-6-qa.md:77` — the real tiny-budget
open-universe run during QA produced BTC PROMOTE with `WFE -0.05` (gate fail)
and SOL with `WFE -0.48` (gate fail), so the browser screenshot shows the
sole-survivor branch text `"Best (sole survivor) — gates not met: WFE -0.05
below 0.30 gate"` rather than the canonical `"Best — WF-validated …"` text.
This is the J-16 best-case-vs-tiny-budget tension the spec explicitly
anticipates ("If the natural run does NOT happen to produce a WFE-failing
candidate alongside a passing one in the tiny budget, J-16 still passes as
long as every PROMOTE `complete` entry carries a coherent rationale tag AND
the deterministic unit test proves the rejection branch fires when it
should"). Both conditions are satisfied: every PROMOTE row carries a coherent
rationale, and the deterministic unit test
`test_open_universe_j16_rationale_promotes_robust_winner` is green.

**B3 — OBSERVATION (no action): `_finite_display` non-finite handling uses Unicode `−∞`/`+∞`**
`apps/backend/backend/auto_session.py:1158-1159` — non-finite scores in the
"lower robust score" comparison branch render as the Unicode `−∞` / `+∞`
characters, which are valid JSON string content and render cleanly in modern
browsers. This branch only fires defensively because `_finite` in
`robust_objective.py:54` already collapses non-finite scores upstream, so the
real-pipeline path cannot reach it. Tests
`test_robust_best_rationale_non_finite_score_finite_display` (and the partial
inputs / corrupt RobustInputs test) confirm no `nan`/`inf` literals leak.

### Frontend Findings

**F1 — OBSERVATION (no action): Minimal additive sub-line render is correctly conditional**
`apps/frontend/src/components/ActivityLogEntry.tsx:144-157` — the `complete`
branch wraps the existing `<p>` in `flex-1 min-w-0` and conditionally renders
`<p className="text-xs text-emerald-700/70 mt-1">{entry.detail}</p>` only when
`entry.detail` is truthy. Verified by source read: no new component, no new
icon, no new badge, no new state, no new polling. `IterationCard.tsx`'s `Best`
badge is untouched (still driven by `bestIterationId`). Frontend handoff and
QA TC-15 confirm a clean `tsc && vite build`.

### Test Findings

**T1 — OBSERVATION (no action): Test suite is tight on exact rationale strings**
Tight equality assertions on `detail` values:
- `apps/backend/tests/test_auto_session.py:2135` — `assert out == "Not best — WFE 0.00 below 0.30 gate"`
- `:2145` — `assert out == "Not best — under min-trades floor (2 < 5)"`
- `:2155` — `assert out == "Not best — no walk-forward windows"`
- `:2166` — `assert out == "Not best — over-leveraged (2.5×)"`
- `:2306` — `assert overfit_entry["detail"] == "Not best — WFE 0.00 below 0.30 gate"` (integration)
- `:2356-2357` — under-traded integration assertion
- `:2393` — no-walk-forward integration assertion
These are exact-equality (not substring) checks, so a regression in either the
helper text or the wiring would visibly break. The over-leveraged unit test is
at the helper level (no pipeline scenario), as the spec mandates.

**T2 — OBSERVATION (no action): Pinned-path regression guards intact**
`test_pinned_path_unchanged_by_open_universe_addition` (line 1451) still carries
the iter-4 `insight_calls == 3` assertion (line 1477). The new delta
`test_pinned_path_no_rationale_detail_on_complete` (line 2455) asserts no
`detail` field is set by the iter-6 helper on pinned `complete` rows.
`test_no_terminal_summary_on_pinned_run` (line 2552) asserts the open-universe
terminal summary never emits on pinned. All three green per QA log.

**T3 — OBSERVATION (no action): Once-per-PROMOTE call-count test passes**
`test_rationale_appended_once_per_promote_not_per_round` (line 2489) reads the
activity log back and counts the `detail`-bearing PROMOTE `complete` entries
exactly equal to `_PROMOTE_TOP_K` (2), confirming "exactly once per promoted
iteration, not per round."

---

## 3. Domain Assessment

The robust-best invariant in `backend/robust_objective.py` is structurally
guaranteed (`_GATE_FAIL_PENALTY = 1000.0` subtracted on any hard-gate fail
ensures any gate-passing candidate strictly outranks any gate-failing one).
Iter-6 is pure presentation on top of that invariant. The rationale helper
text mirrors the gate evaluation in `robust_score`:

| Gate (robust_score) | Rationale text |
|--------------------|----------------|
| `num_windows == 0` or `wfe is None` | `"no walk-forward windows"` |
| `wfe < DEFAULT_MIN_WFE` (0.30) | `"WFE X.XX below 0.30 gate"` |
| `num_trades < DEFAULT_MIN_TRADES` (5) | `"under min-trades floor (N < 5)"` |
| `leverage > 1.0` | `"over-leveraged (X.X×)"` |
| gates pass, lower robust | `"lower robust score (X.XX vs best Y.YY)"` |
| gates pass, this is best | `"Best — WF-validated (WFE X.XX, N trades)"` |
| gates fail, this is sole best | `"Best (sole survivor) — gates not met: …"` |

The vocabulary is purely numeric + gate-name + iteration-id — no API jargon,
no secrets, no `null`/`undefined`/`NaN`/`Infinity` literals (verified by QA
TC-14 secret-grep and TC-03 browser DOM extract).

The terminal summary row (open-universe, ≥ 2 PROMOTEs only) text matches the
spec: `"Robust-best: <best-iter-id> selected over <N-1> other promoted
candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage"`. Single
PROMOTE and pinned runs correctly skip the summary.

Anti-goal-by-anti-goal structural check:

| Anti-goal | Status |
|----------|--------|
| Robust selection must rank gate-passing above WFE-failing | byte-unchanged in `robust_objective.py` |
| Cheap SCREEN must not run WFv or strongest model | SCREEN path unmodified; iter-6 wires only on PROMOTE |
| Same store/schema as a manual run | `_activity("complete", …, detail=…)` uses the existing helper; `detail` was already an optional ActivityEntry field (typed in `useBacktest.ts`) |
| Hard budget honored | `tracker.start_config()`/`would_exceed()` byte-unchanged; iter-6 adds zero LLM calls and zero new tokens |
| Bounded seed universe | unchanged |
| OHLCV cache reuse / no re-generation | unchanged |
| Read-only history mining | unchanged |
| Event loop non-blocking | both new appends use `asyncio.to_thread(session_store.append_activity_entries, …)` |
| `GET /api/sessions` does not eagerly parse iteration payloads | unchanged |
| `BACKTEST_STORE_DIR` survives restart | unchanged |
| No sandbox / engine bypass | unchanged |
| Iterate loop only in backend | zero changes to `useBacktest.ts` / `SessionContainer.tsx` / `AutoRunBar.tsx` |
| Frozen dataclasses untouched | `shared/contracts.py` diff is empty |
| No secrets in activity log | rationale vocabulary is numeric + gate name + iter id; QA secret-grep clean |
| No new external infrastructure | only new imports are `DEFAULT_MIN_TRADES` / `DEFAULT_MIN_WFE` from the existing `backend.robust_objective` |
| Prompt-caching / no resend of leaderboard | iter-6 adds zero LLM calls |

All structural anti-goal proofs pass.

---

## 4. Fixes Applied During This Audit

None. The implementation, review, QA validation, UX regression, and phase
closure check are coherent and well-evidenced. No CRITICAL or IMPORTANT issues
found.

| # | Severity | File | Change |
|---|----------|------|--------|
| — | —        | —    | — (no fixes applied) |

---

## 5. Recommended Next Step

**Proceed to goal-evaluator.** With J-16 satisfied (deterministic primary
proof green + browser observable corroboration with screenshots) and J-01–J-15
preserved (`_run_pinned` byte-identical, frozen modules byte-empty, iter-4
`insight_calls == 3` regression guard green, iter-5 write-primitive scan
clean), all 16 Must-have journeys are passing and zero anti-goals are
violated. The goal-evaluator can declare `GOAL_ACHIEVED` per the agent rule
"every journey passing + no critical anti-goal violation."

Outer-loop carryover from iter-4 (two transient `ui-test-design-phase.sh` stub
artifacts at `reports/phase-goal-auto-money-printer-iter-4-ui-test-plan.md`
and `reports/phase-goal-auto-money-printer-iter-4-what-to-click.md`) remains
non-blocking — it is orchestrator/pipeline residue, does not flip any journey
or anti-goal verdict, and is explicitly recorded in NOTES so it is not lost
across iterations. Remediation if desired: a one-command pair (run
`ui-test-design-phase.sh goal-auto-money-printer-iter-4` then
`phase-closure-check.sh goal-auto-money-printer-iter-4`).
