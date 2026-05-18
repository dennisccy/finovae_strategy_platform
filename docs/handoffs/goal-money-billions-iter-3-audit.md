# goal-money-billions-iter-3 Audit Report

**Date:** 2026-05-18
**Auditor:** Hard audit pass — skeptical, evidence-based

---

## 1. Executive Verdict

**Verdict:** PASS_WITH_GAPS

The phase goal is genuinely achieved. The last tracked anti-goal (eager session-open
load) is resolved and proven **independently of J-02** by code inspection
(`session_routes.py:164` now calls `read_iteration_meta`, no `read_iteration_full` in
`get_session`) plus a non-vacuous backend response-shape test that seeds a node *with*
heavy payloads and asserts their exact absence (re-run independently this audit: **5/5
pass**). J-04 finally has dedicated, distinct OOS-aware evidence — the two screenshots
were independently verified byte-distinct **and** visually/structurally distinct
(insights pane with OOS/WFE prose + ranked chips vs the J-03 walk-forward panel),
closing the long-open lessons.md iter-2 duplicate-screenshot failure mode. No must-have
journey regresses. Remaining items are documented, non-blocking known limitations (one
MINOR interstitial UX nit, two intended/spec-anticipated behavior deltas, one
spec-pre-authorized pre-existing test failure) — none CRITICAL or IMPORTANT.

---

## 2. Findings

### Backend Findings

**B1 — OBSERVATION (verified): anti-goal resolved at the source, not inferred.**
`apps/backend/backend/session_routes.py:155-181` `get_session._load()` builds
`iterations` via `read_iteration_meta(session_id, parts[1])` (line 164).
`read_iteration_meta` (`session_store.py:295-302`) reads only `meta.json`, which
`write_iteration` (`session_store.py:262-266`) writes excluding
`_BULK_KEYS = {prompt, scriptCode, insights, result, rating, timeframeResults}`.
`read_iteration_full` remains imported (line 26) and used **only** by the unchanged
lazy `get_iteration` endpoint (line 242). The 404 condition (line 172
`if not meta and not activity and not iterations`) and the response envelope
(lines 175-181) are behaviorally unchanged. Independence rule (lessons.md iter-0)
satisfied: resolution rests on code + response-shape test, not on J-02.

**B2 — OBSERVATION (verified): pre-existing failure is genuinely out of scope.**
Full suite re-run this audit: `124 passed, 1 failed`. The lone failure
`tests/test_directions_cache.py::test_write_and_read_full_round_trip` is unrelated:
`git log` shows `test_directions_cache.py` and the directions-cache module were last
touched in the monorepo-restructure commit `7c23531`, not by this iteration; the only
iter-3 backend source change is `session_routes.py` (zero coupling). The iter-3 spec
DoD explicitly pre-authorizes this as documented pre-existing. Documented in the dev
handoff and `reports/qa/goal-money-billions-iter-3-failure-digest.md`.

### Frontend Findings

**F1 — OBSERVATION (verified): write-amplification guard is correctly wired.**
This was the highest correctness risk. The version key is byte-identical at all three
sites — hydration seed `useBacktest.ts:569`, save-effect compute `:607`, lazy-merge
pre-set `:1546-1548` — all `` `${status}:${insights?.suggestions?.length ?? 0}` ``.
The pre-set runs synchronously (`:1546`) before `setIterationHistory` (`:1552`), so when
the save effect (`:602-623`) fires on the merged state it recomputes the *same* key,
`savedIterationVersionRef.current.get(id) === versionKey` holds, and `upsertIteration`
is **not** called. `savedActivityCountRef` is untouched and `loadIterationDetail`
does not mutate `activityLog`, so no activity-log write-amplification. Correct.

**F2 — OBSERVATION (verified): `migrateSession` is robust to lightweight nodes.**
The plan flagged a risk that `migrateSession` (`useBacktest.ts:50-84`) runs on raw
lightweight nodes *before* `normalizeLightweight`. Verified safe: it only
`delete`s absent keys (no-op) and uses optional chaining + default
(`node.result?.max_drawdown ?? 0`); `maxDrawdown` is a meta field present on
lightweight nodes so that branch is skipped anyway. No unguarded heavy-field
dereference. Corroborated by QA TC-10/TC-13 (session open + history render + selection
worked in the browser).

**F3 — OBSERVATION (verified): detail-pane state machine is crash-safe.**
`IterationPanel.tsx` precedence is `selected.result` → `detailLoading` (spinner) →
`detailError` (message + Retry) → benign "No detailed results". A selected node with
no result never silently blanks and never crashes the detail view. `fetchIterationDetail`
throws on failure; `loadIterationDetail` catches → `detailError`. QA TC-17 (forced 500
→ error pane + Retry recovery) and TC-18 (no-result node, no crash) empirically confirm.

**F4 — GAP (reviewer MINOR, confirmed, non-blocking): global single-slot detail
loading state.** `useBacktest.ts` uses one `detailLoading`/`loadingDetailIdRef` slot.
Under a rapid overlapping selection (select A, then B before A resolves), fetch A's
`finally` clears `detailLoading` while B is still in flight, briefly rendering the
benign "No detailed results" pane for B instead of the spinner. The merge stays correct
(keyed by id) and the per-iteration fetch is a fast local read; QA TC-10 observed no
blank/stale on multi-select + re-select in practice. Interstitial-only UX nit, data
correct — documented, not fixed (OBSERVATION-class; matches reviewer's lone MINOR).

**F5 — GAP (intended, documented): two behavior deltas from the lightweight contract.**
Per dev handoff Known Issues #2/#3: (a) insights no longer auto-generate on session
open (latest node has no in-memory `result` at mount) — arguably preferable (no
surprise paid OpenAI calls); does not affect J-04 (user-initiated on a lazy-loaded
selected run). (b) Card-level "Rerun"/"improve-on-previous-code" context now requires
selecting the source run first (`scriptCode` is a lazy heavy field). QA smoke
(TC-13/14/15/16) confirms none of J-01/J-03/J-05/J-06 regress. Prefetching is
explicitly OUT OF SCOPE for iter-3. Acceptable and honestly disclosed.

### Test Findings

**T1 — OBSERVATION (verified): the binding backend tests are tight and non-vacuous.**
`test_session_routes.py` independently re-run: **5 passed**.
`test_get_session_iteration_list_is_lightweight_no_heavy_payloads` seeds a node
*containing* `result/rating/insights/prompt/scriptCode` then asserts each of
`result, rating, insights, prompt, scriptCode, timeframeResults, equity_curve, trades`
is `not in entry` (exact absence, not present-but-null) AND that lightweight fields
(`id, status, timestamp, strategyName, parentId, params, totalReturn`) are present with
exact expected values — it cannot pass by accident.
`test_get_session_does_not_call_read_iteration_full` uses `inspect.getsource` on the
real function (the code-inspection independence proof).
`test_per_iteration_endpoint_still_returns_full_node` asserts exact values
(`total_return == 0.37`, `len(equity_curve) == 1`, `len(trades) == 1`). Order/meta and
404 covered. Assertions are tight.

**T2 — OBSERVATION (verified): J-04 evidence is genuinely distinct.** Independent
sha256: `TC-12-j04-insights.png` = `ada68f7d…` ≠ `TC-14-j03-walkforward.png` =
`1df318ef…` (matches QA's claim). Direct image inspection confirms structural
distinctness: TC-12 is the **insights pane** — prose explicitly citing "healthy 1.256
WFE … OOS results remain negative at -7.22%" plus ranked suggestion chips; TC-14 is the
**walk-forward panel** — WFE -6.00 badge, IS/OOS per-window table, combined OOS curve,
strategy-rating stars. Not a duplicate. lessons.md iter-2 rule satisfied; corroborated
by the QA API-level proof (5/10 suggestions OOS/WFE/robustness-aware).

---

## 3. Domain Assessment

The core change is a one-line, semantically correct swap (`read_iteration_full` →
`read_iteration_meta`) backed by a pre-existing on-disk file split (`_BULK_KEYS`), so
the lightweight contract is structurally guaranteed rather than hand-filtered — a robust
design. The frontend lazy-load is the genuinely hard part, and its two correctness
hazards (save-effect write-amplification under lazy-merged insights; `migrateSession`
on lightweight nodes) were both specifically anticipated and correctly handled, verified
by reading the actual code (not the handoff). Error/loading/no-detail states are
explicit and crash-safe. J-04 is genuinely verification-only — every spec-forbidden file
(`insights_generator.py`, `backend/api.py`, `loader.py`, `session_store.py`,
`contracts.py`, `BacktestConfigBar.tsx`) was independently confirmed untouched. Scope is
exactly the 7 planned files. Both binding gates hold under independent re-verification.

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| — | — | — | None. No CRITICAL or IMPORTANT issues found; both binding gates pass under independent verification. |

---

## 5. Recommended Next Step

Proceed. The last tracked anti-goal (#10, `GET /api/sessions/{id}` eager-load) is
code-and-test proven resolved independently of J-02, J-04 OOS-awareness finally has
dedicated distinct evidence, and no must-have journey regresses (backend 124 pass + new
5 pass; QA 18/18). The remaining gaps (F4 interstitial UX nit; F5 intended behavior
deltas; B2 spec-pre-authorized pre-existing `test_directions_cache` failure) are
documented and non-blocking. The goal-evaluator now has the evidence to declare
**GOAL_ACHIEVED**; any follow-up should be release/finalization only, not new capability.
The F4 single-slot `detailLoading` nit is a reasonable cleanup candidate for a future
polish pass but must not block this iteration.
