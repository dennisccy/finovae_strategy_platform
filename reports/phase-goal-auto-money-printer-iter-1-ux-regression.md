# Phase goal-auto-money-printer-iter-1 — UX Regression Review

**Date:** 2026-05-19

**Verdict:** UX-REGRESSION-WARN

Frontend Present: yes. Full UX regression review performed.

---

## Executive Summary

The new headless auto-session capability is correctly surfaced **once a
session exists** (AutoRunBar status strip, live polling, ★ Best badge, stop
reason) and the lesson-mandated J-02 right-panel re-bind is implemented. No
prior user journey (J-01, J-03, J-04, J-05, J-06) is demonstrably broken — the
browser-QA regression smoke (UT-10–UT-15) passed in the same run.

WARN (not PASS) for three reasons, none individually blocking:

1. **Stale browser-QA evidence.** `ui-test-results.md` is **FAIL** (UT-03,
   UT-06 P1). The developer applied post-QA fixes (B1 event-loop offload,
   B2/UT-03 discovery poll, B3/UT-06 expanded badge). I verified the B2 and B3
   **code fixes are present in source**, but browser QA was **not re-run**, so
   the two P1 fixes and the critical B1 fix are unconfirmed end-to-end.
2. **Start capability is API-only (intentional, documented).** There is no UI
   element to start a headless run; the trigger is `POST /api/auto-sessions`
   only. Spec-deferred to iter-2 (J-10) and documented in
   "Not Visible Yet" — acceptable for this iteration, but a genuine
   discoverability gap for a non-scripting user.
3. **Heavy shared-component churn.** `useBacktest.ts` (+161), `SessionContainer`
   (+52), `IterationPanel`, `IterationCard`, `IterationDetailView`, `App.tsx`
   — all consumed by every prior journey. Risk is mitigated by design (manual
   paths gated on `autoRun == null` / `backendOwnedRef`) and by passing
   regression smoke, with one low-risk watch item (UT-14 heavy WF caveat).

---

## New Capability Discoverability

| Capability | Navigation path | Clicks from home | Assessment |
|---|---|---|---|
| **Start headless session (J-07)** | None — `POST /api/auto-sessions` API only | Not reachable from UI | **Intentional gap.** Spec GOAL is explicitly "A user (or a script) makes one POST /api/auto-sessions call"; UI button is J-10/iter-2. Documented in user-visible-changes "Not Visible Yet". Acceptable for this iteration; flagged as WARN-level, not a hidden-capability FAIL. |
| **Headless session appears in list (J-07/J-08)** | Auto-merged into session picker via 5 s discovery poll (`App.tsx`) | Open picker (1) → select session (2) | Discoverable within 2 clicks — **once the discovery-poll fix works**. The poll fix is in source but browser-QA-unconfirmed (UT-03 was FAIL pre-fix). |
| **Live run status / progress (J-08)** | `AutoRunBar` strip below config bar in the opened session | 2 (open + select) | Discoverable. Reuses existing layout, `Loader2` spinner, slate/primary tokens. |
| **Terminal stop reason (J-09)** | `AutoRunBar` terminal state (green "complete · …" / red "stopped") | 2 | Discoverable; `role="status" aria-live="polite"` (UT-18 pass). |
| **★ Best iteration marker (J-09)** | Amber pill on iteration card (compact tree) **and** expanded `IterationDetailView` header (B3 fix) | 2–3 | Compact-tree badge confirmed (UT-05 pass). Expanded-header badge code fix verified present but browser-QA-unconfirmed (UT-06 was FAIL pre-fix). |
| **J-02 full-detail re-bind** | Select a prior run in history tree | 2 (existing journey) | Discoverable; confirmed working (UT-07/UT-11 pass). |

**Label clarity:** "Automated run · iteration X / N", "robust targets met",
"budget reached", "★ Best" with tooltip "Best iteration — selected by the
robust walk-forward objective" (UT-19 pass) are clear to a non-technical user.
No label confusion.

**Visual consistency:** New `AutoRunBar` and `BestBadge` reuse the existing
slate/primary/emerald/amber token palette, `lucide-react` icons (`Loader2`,
`Star`, `StopCircle`) and the dense analytical-workstation aesthetic. No
arbitrary values, no new effects invented, no new page/route. Consistent with
prior phases.

---

## Regression Risk

This phase changes components shared by **every** prior journey. Risk table:

| Shared component | Prior feature served | Change this phase | Risk | Mitigation status |
|---|---|---|---|---|
| `useBacktest.ts` | J-01/J-02/J-03/J-04/J-06 (the core hook) | J-02 lazy-detail guard rewrite (`loadedDetailIdsRef` → `loadingDetailIdRef` + node-own-`result` key); backend-owned save/beacon suppression; live poll; `isAutoRunning` ∥ `headlessActive` | **High** (central hook) | Mitigated: manual paths gated on `backendOwnedRef.current` (false when `autoRun==null`). Empirically green: UT-07, UT-11, UT-12, UT-13 pass. |
| `App.tsx` | All sessions (tab list) | Additive 5 s discovery poll + window-focus refetch | Medium | Verified strictly additive (lines 152–173: never removes/renames/reorders/persists, no `activeSessionId` change). UT-03 fix — browser-QA-unconfirmed. |
| `SessionContainer.tsx` | J-01–J-06 active-session view | New `AutoRunBar`; `bestIterationId` passthrough | Medium | `AutoRunBar` gated on `autoRun != null` — manual sessions show no strip (UT-02/UT-10 pass). |
| `IterationPanel.tsx` | J-02 history detail | `key={selected.id}` remount; thread `bestIterationId`/`isBest` | Medium | Remount-per-selection is the J-02 fix; UT-07/UT-11 pass. |
| `IterationCard.tsx` / `IterationDetailView.tsx` | J-02 iteration display | `BestBadge` (exported, reused), `isBest` prop | Low | Additive badge only; `isBest` defaults `false`. Compact-tree confirmed; expanded-header fix unconfirmed (UT-06). |
| `session_routes.py` `GET /api/sessions/{id}` | J-02 (open session) | Adds small `autoRun` block to response | Low | Lazy-load anti-goal intact (no `result`/`rating` inlined — UT-05 confirms). Additive field; existing consumers unaffected. |
| `api.py` | All API | 2-line router mount | Low | Additive route registration. |

**Navigation integrity:** Single-page app, no router. Session picker is the
shared navigation for all features; `App.tsx` change is strictly additive and
never reorders/removes existing tabs. All prior session entry points intact.

**Watch item (low risk, not a regression flag):** UT-14 reported the heavy
183-trade / 4-year manual Walk-Forward "still computing at QA end" — browser-QA
classified this as expected dataset slowness, not a confirmed regression. The
B1 fix offloaded auto-session store I/O off the event loop (test-guarded by
`test_headless_loop_does_not_block_event_loop`); the manual WF path was not
modified. Recommend a single confirmatory manual-WF timing check on re-run.

**No prior journey is demonstrably broken.** Regression smoke UT-10 (manual no
AutoRunBar), UT-11 (A→B→A guard), UT-12 (poll preserves open detail), UT-13
(J-01 manual backtest), UT-14 (J-03/J-04 WF+insights), UT-15 (J-05 ref data +
legacy in-browser Auto Run intact) all passed in the browser-QA run.

---

## UI vs Backend Parity

| Backend capability (implementation-summary / dev handoff) | UI exposure | Parity |
|---|---|---|
| `POST /api/auto-sessions` start | **None** (API only) | Intentional gap — J-10/iter-2; documented in "Not Visible Yet". |
| Bounded loop + durable `autoRun` state machine | `AutoRunBar` status/progress, session-picker amber dot | Exposed |
| Terminal stop reason (criteria-met / budget-exhausted) | `AutoRunBar` green/red terminal text | Exposed |
| Robust-objective best selection | ★ Best badge (compact + expanded after B3) | Exposed (expanded path unconfirmed) |
| Headless session in existing store, indistinguishable from manual | Appears in session picker (discovery poll) | Exposed (unconfirmed by re-run) |
| Cooperative cancellation token (plumbed) | **No stop control** | Intentional gap — J-11/iter-2; documented. |
| Token/USD cost accounting | **Not shown** | Out of scope — J-13; documented. |

**Doc inconsistency (minor, non-blocking):** `implementation-summary.md` states
"Backend-Only Items: **None**", but the **start action is backend-only** this
iteration (API-only, no UI trigger). `user-visible-changes.md` correctly
documents this under "Not Visible Yet". The summary slightly overstates UI
parity; the user-visible-changes doc is accurate. Recommend the auditor note
the wording, not block on it — the gap itself is spec-sanctioned.

---

## Flags

### Hidden Capabilities
- None that are accidental. The headless-session **start** has no UI path, but
  this is spec-mandated (GOAL = "a user *or a script* makes one POST" call;
  UI button = J-10/iter-2) and explicitly documented in "Not Visible Yet".
  Classified as an **intentional, documented backend-only entry point**, not an
  accidental hidden capability.

### Undiscoverable Capabilities
- **Headless run discoverability depends on an unverified fix.** UT-03 ("session
  appears without reload") was **FAIL** in browser QA; the `App.tsx` 5 s
  discovery poll fix is present in source but **not re-tested in-browser**. If
  the poll regresses or is slow, the entire J-07/J-08 "watch it live without
  reload" value proposition is undiscoverable without a manual reload. → Re-run
  browser QA to confirm UT-03.

### Potential Regressions
- **`useBacktest.ts` J-02 lazy-detail guard rewrite** (`loadedDetailIdsRef`
  removed) is the highest-risk shared change — it sits on the J-01/J-02 history
  path used by every backtest. Tested green (UT-07/UT-11/UT-12/UT-13) but is
  logic-level, not gated; keep it on the regression watchlist for any future
  history/poll change (matches the iter-0 lesson cited in the spec NOTES).
- **Backend-owned save suppression**: manual sessions are gated out
  (`backendOwnedRef.current` false when `autoRun==null`) — design-correct and
  UT-13 confirms manual save still works. Low residual risk.
- **UT-14 heavy manual Walk-Forward** "still computing at QA end" — low-risk
  watch item, not a confirmed regression (see Regression Risk).

### Visual Consistency
- New `AutoRunBar` and `BestBadge` follow the established slate/primary/
  emerald/amber tokens, existing icon set, and the dense workstation layout.
  No new page, no arbitrary values, no inconsistent effects. **Consistent with
  prior phases.** No visual-inconsistency flag.

---

## Recommendation

**Verdict: UX-REGRESSION-WARN** — UI evolved appropriately with the new
capability and no prior journey is demonstrably broken, but there are
non-blocking gaps the auditor must weigh:

1. **Re-run browser QA** (or have the auditor explicitly accept the source-level
   verification) to confirm the three post-QA fixes that `ui-test-results.md`
   never re-tested: **B1** (event-loop offload — most serious, anti-goal-
   relevant), **UT-03/B2** (discovery poll — the J-07/J-08 discoverability
   mechanism), **UT-06/B3** (expanded ★ Best badge). Code fixes for B2 and B3
   are verified present in source by this review; B1 has a new test guard.
2. **Accept the API-only start as spec-scoped** (J-10/iter-2) — it is correctly
   documented in "Not Visible Yet"; no action needed beyond confirming iter-2
   carries the UI rewire.
3. **Minor doc fix (non-blocking):** reconcile `implementation-summary.md`
   "Backend-Only Items: None" with the reality that the start action is
   backend-only this iteration (already correctly stated in
   `user-visible-changes.md`).
4. Keep the `useBacktest.ts` J-02 guard rewrite on the regression watchlist for
   future history/poll-touching iterations (per the iter-0 lesson).

No critical capability is inaccessible and no prior user journey is broken, so
this is **not** a FAIL. The unconfirmed P1 fixes and the API-only start keep it
from a clean PASS.
