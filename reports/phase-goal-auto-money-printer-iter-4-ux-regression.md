# Phase goal-auto-money-printer-iter-4 — UX Regression Review

**Date:** 2026-05-19

**Verdict:** UX-REGRESSION-WARN

---

## Summary

iter-4 adds staged **SCREEN→PROMOTE** cheap-first routing (J-14) plus the carried
iter-3 **B1** spend-cap insights fix. It is a **backend-only diff**: `git diff
HEAD --stat -- apps/` shows exactly 4 files — `apps/backend/backend/auto_session.py`
(+800/-269), `apps/backend/shared/model_catalog.py` (+16), and the two test files.
**Zero frontend files changed** (verified, not assumed). The new capability rides
the *existing* session Activity panel + Iterations panel + AutoRunBar. The primary
operator-visible J-14 acceptance is met and browser-verified (10/10 PASS, clean
first pass — not a reconciled headline). The WARN is for genuine, **non-blocking,
spec-sanctioned** UI-vs-backend gaps, not for a regression or a hidden primary
capability.

---

## New Capability Discoverability

**Trigger / navigation path — unchanged from iter-3 J-12, no regression.**
The capability is reached by the same path as the existing open-universe run:
`POST /api/auto-sessions` (no symbol/timeframe, `objective:"robust"`, small
budget) or the existing in-UI Auto-Run control → open the session → read the
left **Activity** panel. From home: open/select session (1) → Activity panel is
already in view in the two-panel session layout (≤2 clicks). No new button, page,
menu, or route was required or added — consistent with the spec ("No new
surface", "New user actions: None").

**Is the staging visible? — Yes, verified.** Browser QA (UT-01–UT-06, all PASS)
confirmed the operator sees ≥3 `SCREEN N done — …` accordion groups + exactly
k=2 `PROMOTE done — …` groups (k < screened=4) on 3 independent live runs;
SCREEN groups carry `(cheap screen — no walk-forward)` and **no** insights card;
PROMOTE groups carry `robust …, walk-forward WFE …` and **a** blue insights
card; the robust-best badge sits on a PROMOTE iteration (SOL, robust 0.897), not
the higher-raw-return ETH (+21.11%). The cheap-first behaviour ("expensive work
reserved for survivors") is therefore genuinely discoverable in the existing
feed via the SCREEN/PROMOTE text prefix + the walk-forward presence/absence.

**Label clarity:** `SCREEN`/`PROMOTE` prefixes and the `(cheap screen — no
walk-forward)` disclaimer are plain enough for a non-technical operator to read
the shortlist-then-promote story. No label confusion vs the spec terminology.

## Regression Risk

`auto_session.py` is the single shared backend for J-02, J-07–J-13, and it took
the dominant diff (the unified loop was refactored into `_run_pinned` +
`_run_staged_open_universe` + a shared `_evaluate_one`). High surface area —
but the regression risk is **well-mitigated and was re-verified LIVE, not
carried**:

| Prior journey | Shared surface touched | Mitigation / evidence | Risk |
|---|---|---|---|
| J-02 (prior-run trades table + right analysis re-bind) | `auto_session.py` writes the iteration/trades artifacts; **no frontend file changed** so `useBacktest` merge + `IterationPanel` key-remount are byte-unchanged | UT-10 PASS live: BTC iter → 18 trades, ETH iter → re-bound to 19 trades (not stale, not blank) | Low |
| J-08 (live status, no stale terminal on switch) | same backend status block; live-poll/`AutoRunBar` frontend byte-unchanged | UT-09 PASS live: switch-away/back → bar shows current terminal, `isStaleRunning=false` | Low |
| J-07–J-11 (pinned path: server-driven run, stop, best, insights chain) | `_run_pinned` extracted from the prior unified loop; **carried B1 fix touches the insights gate** | UT-08 PASS live: pinned 3-iter run has no SCREEN/PROMOTE, no `stage` key, and **every** group incl. final 3/3 has 1 insights card; backend cross-check = 3 distinct insights entries | Low (highest-risk item, explicitly guarded — see below) |
| J-09 (robust-best by objective) | best-selection candidate pool narrowed to promoted-only | UT-05 PASS: exactly 1 Best badge, on the robust PROMOTE iter, not the higher-raw-return one; `select_best`/`robust_score` reused unchanged | Low |
| J-12 (open-universe ≥2 distinct seed configs, UI-indistinguishable) | open-universe controller restructured | UT-01 PASS: deterministic 4-config seed prefix screened, ≥2 distinct, UI-indistinguishable | Low |
| J-13 (budget-exhausted + durable/visible spend) | `max_configs` semantics redefined under staging (counts promoted only) | UT-06 PASS: amber `budget reached`, `2 cfg` == #PROMOTE; J-12/J-13 tests consciously updated to staged form (not loosened) | Low |

**Highest-risk item — the carried B1 pinned-path trap (iter-3 audit T2 /
lessons-learned):** a naive "skip insights whenever `would_exceed()` is truthy"
would suppress the **final pinned iteration's** insights (the `max_cfg ==
max_iter` path returns the `"max-configs"` sentinel there), silently breaking
the J-07–J-11 prompt-refinement chain with no test to catch it. iter-4 ships the
mandated guard: `test_pinned_path_unchanged_by_open_universe_addition` now
asserts `insight_calls == 3` (RED on a truthy-gated skip, GREEN on the
spend-cap-only gate) **and** browser QA UT-08 independently confirms the final
pinned group has its insights card. This documented regression trap **does not
reproduce**.

**Navigation/loop integrity:** zero frontend diff ⇒ `App.tsx` (session
discovery poll), router/tabs, auth, `SessionContainer`, `useBacktest`,
`IterationPanel/Card/DetailView`, `ActivityLog*` are all byte-unchanged. All
prior routes/tabs and the iter-2 "no second in-browser iterate loop" guarantee
are structurally intact by construction. Anti-goal source guard re-verified by
me: `git diff HEAD -- shared/contracts.py backend/sandbox.py` is **empty**.

## UI vs Backend Parity

| Backend capability built (iter-4) | UI exposure | Status |
|---|---|---|
| Staged SCREEN→PROMOTE flow | `SCREEN …` / `PROMOTE …` accordion groups in the existing Activity panel | **Surfaced & verified** (UT-01–04) |
| Expensive (walk-forward) reserved for survivors | WF data + WalkForwardPanel only on PROMOTE iterations; "Run Walk-Forward" button on screened | **Surfaced & verified** (UT-05) |
| Robust-best drawn from promoted only | "Best" badge on a PROMOTE iteration; raw-return loser not best | **Surfaced & verified** (UT-05) |
| Hard budget / staged `max_configs` | AutoRunBar amber `budget reached` + `… N cfg` (N = #PROMOTE) | **Surfaced & verified** (UT-06) |
| Insights spent only on survivors | blue insights card present on PROMOTE, absent on SCREEN | **Surfaced & verified** (UT-02/03) |
| **Stronger model only on promoted** (a load-bearing J-14 anti-goal) | `modelUsed` is **never rendered** in the frontend; verifiable only at the API/artifact layer | **NOT browser-visible** (see Flags) |
| `stage:"screen"/"promote"` iteration field | written but **not rendered** as a chip/label; stage inferred from activity text | **NOT a structured UI element** (see Flags) |
| `cheapest_model()` catalog resolution | internal; only its effect (model name on nodes) exists, and that field isn't rendered either | Internal (spec "Not Visible Yet") |

The spec **explicitly and deliberately** scopes the frontend to "None expected"
and lists the model-routing / stage-badge / k-cutoff items under "Not Visible
Yet" as *intentional for this iteration (no new component)*. The
operator-visible J-14 acceptance does **not** depend on those items — it is the
SCREEN/PROMOTE text + walk-forward presence + robust-best badge, all verified.
So the gaps are **acceptable and non-blocking**, but they are real
backend-without-UI gaps, which is precisely what this review must record.

## Flags

### Hidden Capabilities
- None. The primary new capability (cheap-first SCREEN→PROMOTE staging) has a
  clear navigation path (the existing open-universe trigger + Activity panel)
  and is browser-verified discoverable.

### Undiscoverable Capabilities
- **Model-routing proof is not browser-visible (WARN).** "The strongest model
  is reserved for promoted candidates" is a load-bearing J-14 anti-goal, but
  `modelUsed` is rendered nowhere in `apps/frontend/src` (browser QA UT-07
  confirmed this and could only verify the split at the persisted-artifact
  layer). A non-technical operator cannot *see* the cheap-vs-stronger model
  split in the UI; they infer "expensive work was reserved" only indirectly
  from walk-forward presence. Acceptable for this iteration per the spec's
  explicit "Not Visible Yet" scoping; recorded for the evaluator and as a
  candidate surface for a future iteration (e.g. a per-iteration model chip).
- **Stage is inferred from activity text, not a structured UI element (WARN,
  low).** The additive `stage:"screen"/"promote"` field is written but not
  rendered as a badge/color. Operators distinguish stages only by the
  `SCREEN`/`PROMOTE` text prefix and WF presence. Spec-intended (no new
  component this iteration); functional but text-inferred rather than
  first-class UI.

### Potential Regressions
- No confirmed regression. The shared-surface risk (large `auto_session.py`
  diff under J-02/J-07–J-13) was adequately mitigated: every
  required-still-passing journey was re-verified **LIVE** (not carried), the
  carried B1 pinned trap has a dedicated RED/GREEN guard + live UT-08
  confirmation, and backend tests are 188 passed / 1 pre-existing out-of-scope
  failure (`test_directions_cache::test_write_and_read_full_round_trip`) =
  +5 new passing, zero new regressions. Residual risk is low and watched, not
  open.

### Visual Consistency
- No new pages/components/effects introduced (zero frontend diff), so no
  DESIGN-SYSTEM-token deviation is possible. The staged content flows through
  the unchanged dense/dark data-forward Activity feed and reuses the existing
  `BestBadge`, amber `CircleDollarSign` budget-exhausted treatment, and
  WalkForwardPanel — visually consistent with iter-1/2/3 by construction.
- Non-blocking observation (not a defect, not a regression): suggestion
  **chips = 0** inside PROMOTE insights cards. This is data-driven (the live
  LLM returned prose-only insights with empty `detail`); the unchanged
  `ActivityLogEntry` renderer behaves identically to the pinned/manual path.
  The J-14 acceptance is the insights **card** presence/absence (correct), not
  chip count. Recorded so the evaluator does not misread it as a J-14 gap.

## Recommendation

**Ship this iteration — WARN is non-blocking.** The primary user-facing
capability is correctly surfaced, discoverable within ≤2 clicks via the
existing path, and browser-verified; no prior journey regressed (all
re-verified live; the carried B1 trap is guarded and does not reproduce).

Action items (none blocking iter-4; for the evaluator / future iterations):
1. **Track for J-15/J-16 or a UI iteration:** surface the model-routing split
   in the browser (e.g. a per-iteration model chip / a "screened with cheap
   model" vs "promoted with <model>" indicator) so the load-bearing J-14
   anti-goal is operator-visible, not artifact-only.
2. **Optional, low priority:** render the `stage` field as a small SCREEN/
   PROMOTE chip so staging is a first-class UI element rather than text-inferred
   (no functional gap today; purely a discoverability polish).
3. No code change required from this review (read-only per role).
