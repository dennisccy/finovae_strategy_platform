# Phase goal-financial_free-iter-4 — UI Surface Map

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering for the open-universe search (J-14)
**Date:** 2026-05-23
**Written by:** ui-impact-analyst

---

## Affected UI Surfaces

<!-- Zero frontend code changed this iteration; the surfaces below are existing components whose displayed *content* changes because the backend now emits SCREEN/PROMOTE activity records and screen→promote node lineage. -->

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| `/` (session view) | Left **Activity Log** — `ActivityLogEntry` `auto-run` branch | Changed behavior (new content) | Backend now emits `SCREEN —` / `PROMOTE —` `auto-run` records for the staged search | Trigger an open-universe run (`POST /api/auto-sessions`, no symbol/timeframe, `model:"claude-haiku-4-5"`, `budget.max_configs:3`); confirm the Activity Log shows a `SCREEN —` header naming `gpt-5.4-mini` + "no walk-forward" + a candidate count, ≥3 per-candidate `SCREEN —` rows with a score, then a `PROMOTE —` header reading "top-1 of 3 … claude-haiku-4-5 … walk-forward" |
| `/` (session view) | Left **Activity Log** — SCREEN vs PROMOTE visual distinction | Changed behavior | Two stages must be distinguishable in the UI | Confirm `SCREEN —`-prefixed and `PROMOTE —`-prefixed entries are both present and visually separable (Zap icon + violet text), and that no API key/secret string appears in any entry |
| `/` (session view) | Right-panel **iteration tree** | Changed behavior (new lineage) | Promoted node's `parentId` is its screened candidate | Confirm a promoted iteration card renders nested as a **child** of the screened candidate it was promoted from, not as a sibling/top-level node |
| `/` (session view) | **Iteration card** — promoted candidate | Changed behavior (data) | PROMOTE stage uses stronger model + walk-forward | Open a promoted card; confirm `modelUsed` shows the stronger model (`claude-haiku-4-5`) AND a walk-forward section is present with a WFE result |
| `/` (session view) | **Iteration card** — screened-only candidate | Changed behavior (data) | SCREEN stage uses cheap model + no walk-forward | Open a screened-only card; confirm `modelUsed` shows the cheap model (`gpt-5.4-mini`) AND there is **no** walk-forward section |
| `/` (session view) | **"Best" badge** / `bestIterationId` marker | Changed behavior | Best now selected only from promoted WFE-gated candidates | Confirm the marked best is a promoted (walk-forward-bearing) node; a high-return screened-only node is NOT marked best; if no promoted candidate is eligible, no best badge appears (not an error) |
| `/` (session view) | **Status strip** — token / USD / configs chips (carry-forward J-08/J-10) | Changed behavior (re-verify, not new code) | Promote work accrues onto the same single budget tracker; load-bearing pixel debt this iteration | Watch the token/USD/configs chips update live during a run without reloading (J-08); reload the page mid-run and confirm `autoRun` status + chips survive (J-10) |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/shared/model_catalog.py` — new `cheapest_model()` helper (min blended-rate catalog model) — internal model routing; no UI surface. (Indirectly determines the cheap model name shown in SCREEN entries, but adds no surface.)
- `apps/backend/backend/auto_session.py` — `DEFAULT_PROMOTE_K`, `BudgetTracker.cost_exceeded()`, restructured `_run_open_universe` — orchestration/business logic; surfaced only through the activity records and node lineage already mapped above.
- `apps/backend/tests/auto_session_helpers.py`, `test_auto_session.py`, `test_model_rates.py`, `test_auto_session_live.py` — test-only changes; no UI surface.
- `apps/frontend/src/components/ActivityLogEntry.tsx` — **no change** (the existing `auto-run` render branch displays the new SCREEN/PROMOTE content as-is).

---

## Summary

- **Frontend surfaces changed:** 0 code changes; 7 existing surfaces display new content/behavior (Activity Log SCREEN/PROMOTE entries, stage distinction, iteration tree lineage, promoted card, screened card, best badge, status strip)
- **New pages/routes:** 0
- **Modified components:** 0 (zero frontend code changed; content-only behavior changes on existing components)
- **Navigation changes:** no
- **Backend-only changes:** 6 files (1 catalog helper, 1 orchestrator restructure, 4 test files; frontend file unchanged)
