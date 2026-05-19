# Phase goal-auto-money-printer-iter-5 — UX Regression Review

**Date:** 2026-05-19

**Verdict:** UX-REGRESSION-PASS

---

## New Capability Discoverability

The single new user-visible capability is the **warm-start planner-decision note** in
the existing session Activity feed. It is *data through an unchanged renderer*, not a
new navigation surface (the spec mandates "no new page, component, route, button,
control, or navigation"; `git diff HEAD -- apps/frontend/` is empty — confirmed).

| New capability | Navigation path | Clicks from home | Label clarity | Visual feedback |
|---|---|---|---|---|
| Warm-start "why" citation (global/default run with prior history) | `/` (home) → open **Sessions** dropdown → select the auto-session row → Activity feed (left panel, default-visible on desktop; "Activity" tab on mobile) | **2 clicks** (open dropdown, select session) — within the ≤2-click bar | Plain operator language: *"Warm start (global history): prioritising ETH/USDT 4h — prior best robust 1.70 across 11 prior sessions"* — clear to a non-technical user | Violet ⚡ row at the **top** of the feed, full text, not truncated; byte-identical DOM to the existing iter-2/iter-4 auto-run markers (UT-08) |
| `history_scope: "this-run"` opt-out | `POST /api/auto-sessions` (API behaviour change — spec-intentional: "No new endpoint, no new control") | Effect observable in UI: **absence** of the citation + fixed seed order (UT-06 PASS) | Opt-out is surfaced by its *effect*, consistent with the iter-0→iter-4 "API-driven optimizer, UI is a viewer" product model | N/A — intentional absence |

UT-02 confirmed the headless session auto-appears in the Sessions dropdown within ~5s
with no reload and is selectable, opening its feed — the discovery path to the citation
is intact. The citation renders ungrouped at the top of the feed (UT-04), readable
without expanding any accordion. **No hidden or undiscoverable user-facing capability.**

## Regression Risk

Shared components touched by this phase and their prior-feature exposure:

| Shared surface | Prior feature (phase) | iter-5 change | Risk | Re-verification |
|---|---|---|---|---|
| Open-universe controller `_run_staged_open_universe` / `_config_plan` seed enumeration | J-12/J-14 SCREEN→PROMOTE staging (iter-4) | **Order-only**: the `configs` list is reordered (stable permutation of the same bounded seed) before the unchanged controller is called; controller body not modified in the diff | **Low** | UT-06 (opt-out → byte-identical fixed seed order `BTC/USDT 4h` first), UT-10 (budget/AutoRunBar terminal), UT-12 (pinned chain unchanged) all PASS |
| Durable file store (read path) | J-02 history browse, J-13 durable spend (iter-3) | **Read-only** mine: only `live_root.iterdir()`, `list_iteration_dirs`, `read_iteration_meta`; current session excluded; no write/rename/delete; `session_store.py` byte-unchanged | **Low** (iter-0 lesson honored) | UT-11 PASS — prior session S-1 detail byte-identical after mining (Sharpe -0.22 / return -3.23% / 21 trades / WFE -0.05,-0.48); dev shipped a before/after content-hash read-only proof test |
| Activity feed renderer `ActivityLog`/`ActivityLogEntry` | All auto-run markers (iter-2/iter-4) | **None** — new entry rides the existing `auto-run` renderer verbatim; zero frontend code change | **Low** | UT-08 PASS — byte-identical DOM (same wrapper/icon/text classes), 0 new buttons/badges |
| Cost tracker / `would_exceed` budget gating | J-13 hard budget (iter-3) | **None** — surrogate-only, no LLM tokens added; gating untouched | **Low** | UT-10 PASS — terminal "budget reached", valid monotonic spend, no NaN |

No navigation/router/auth/layout component changed (frontend diff empty) → navigation
integrity intact for **all** prior journeys; no route or nav link removed.

## UI vs Backend Parity

| Backend capability built | UI exposure | Parity assessment |
|---|---|---|
| Read-only warm-start mine + bounded-seed reorder | Surfaced via the citation note + observable family-screened-first effect | ✅ Surfaced |
| Planner-decision citation (`_warm_start_configs`) | Visible at top of Activity feed (UT-03/04/05/13) | ✅ Surfaced |
| `history_scope` opt-out semantics | Visible as citation absence + fixed seed order (UT-06) | ✅ Surfaced (by effect) |
| Additive `autoRun.effectiveHistoryScope` durable/API key | Returned by `GET /api/sessions/{id}`; **not** a labeled UI element | ✅ Acceptable — spec-intentional ("Not Visible Yet": additive key, no schema fork, the *decision* it encodes is surfaced via the citation). Not a flagged gap. |

The phase goal is delivery of a *visible warm-start through the existing activity feed*
— that is delivered and browser-verified. The only backend-only datum
(`effectiveHistoryScope` raw key) is explicitly and soundly scoped API/record-only by
the spec, with the user-facing decision surfaced indirectly via the citation. This is
an intentional, documented, non-blocking design choice — not a parity violation.

## Flags

### Hidden Capabilities
- None.

### Undiscoverable Capabilities
- None. The citation is reachable in 2 clicks from home and renders at the top of the
  feed without expanding anything.

### Potential Regressions
- None blocking. All four shared surfaces are Low-risk (order-only / read-only / no
  code change) and were live-re-verified PASS by browser QA (UT-06/10/11/12), not
  carried by headline alone (iter-1-lesson cross-check satisfied: read-only proof,
  opt-out absence, citation-present all independently verified).

### Visual Consistency
- The new entry is **byte-identical** to the existing SCREEN/PROMOTE/auto-run feed
  rows (UT-08: same `flex items-center gap-2 mb-1.5 ml-1` wrapper, same
  `lucide-zap text-violet-400` ⚡ icon, same `text-xs text-violet-600 font-medium`
  span). No arbitrary values, no new effects, no DESIGN-SYSTEM deviation — it reuses
  the established dense/dark/data-forward feed styling exactly. Consistent.

### Observations (non-blocking, NOT iter-5 regressions)
- **UT-07 (empty-history, P2) SKIPPED** — justified: the shared durable store holds
  100+ prior promoted sessions, so a genuine empty-history state is not reproducible
  in browser-qa scope without an infra restart. The byte-identical no-history fallback
  is covered by the developer's unit/integration suite (`test_open_universe_*`,
  no-history fallback test). P2 skip does not affect the verdict; all P1 pass.
- **Session-label discovery friction is pre-existing**, not introduced by iter-5: open
  -universe rows display by strategy name rather than `Auto: <nl>` (UT-02 note). The
  frontend diff is empty — iter-5 neither caused nor worsened this. Out of scope for a
  current-phase regression flag; recorded only as context for the evaluator.

## Recommendation

**No action required.** The UI evolved correctly with the new capability: the
user-facing deliverable (the warm-start citation) is discoverable within 2 clicks,
visually consistent with prior-phase feed entries, and browser-verified. No prior user
journey regressed — the only shared surfaces are order-only / read-only / zero-code
changes, all live-re-verified PASS (J-02, J-08, J-12, J-13, J-14, pinned J-07–J-11).
The single backend-only datum is spec-intentional with its decision surfaced via the
citation. Clean pass.

**Verdict:** UX-REGRESSION-PASS
