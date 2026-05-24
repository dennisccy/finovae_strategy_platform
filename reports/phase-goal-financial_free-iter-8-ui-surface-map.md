# Phase goal-financial_free-iter-8 — UI Surface Map

**Phase:** goal-financial_free-iter-8
**Date:** 2026-05-24
**Written by:** ui-impact-analyst

---

## File Classification

| File | Category | UI Impact | Explanation |
|------|----------|-----------|-------------|
| `apps/frontend/src/hooks/useBacktest.ts` | frontend-direct | direct | Null-guard on render-derived `autoRunProgress` (`autoRun?.budget ? … : null`). Crash fix — prevented whole-app blank on legacy sessions. Not poll/visibility logic. |
| `apps/frontend/src/components/IterationPanel.tsx` | frontend-direct | direct | Gates `AutoSessionStatusStrip` on `autoRun?.budget` at 2 call sites (empty-state + main view). Leaderboard mount unchanged. |
| `incredible_auto_dev/scripts/automation/browser-qa-phase.sh` | backend-internal | none | Verification-harness shell script: port reconciliation + cold-start FE re-probe. No product surface. |
| `reports/qa/goal-financial_free-iter-8-evidence/*` | n/a (artifacts) | none | Pixel-proof screenshots + reproduction scripts. Not shipped code. |

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| `/` (single-page app, any auto-session selected) | `AutoSessionStatusStrip` (top of Right "Iterations" panel) | Changed behavior | Now gated on `autoRun?.budget` to avoid dereferencing a missing `budget` on legacy records | Select a **current-schema** running auto-session → confirm the status strip (budget/spend/iteration progress) still appears and updates. Select a **legacy** auto-session (e.g. `j16-leaderboard-proof` is current-schema; pick one of the ~70 pre-`budget` ones) → confirm the panel opens with NO status strip and the app does NOT blank. |
| `/` (any session, including legacy) | App shell / `SessionContainer` (`useBacktest`) | Changed behavior (crash fix) | `autoRunProgress` previously read `autoRun.budget.iterationsDone` unguarded, crashing the whole app via an always-mounted hook | Load the app with at least one legacy auto-session present in the store → confirm no blank screen, no uncaught `pageerror` in the console, and the iteration tree/charts render. |
| `/` Right panel — "Iterations" | `AutoSessionLeaderboard` | Render proof (no code change) | iter-7's surface; this iteration captures the pixel proof it paints | Open an auto-session with ≥2 ranked candidates → confirm ≥2 ranked rows, the BEST row highlighted (violet badge/tint) and equal to `bestIterationId`, color-graded WFE chips (emerald ≥0.5 / amber 0.3–0.5 / red <0.3), and a non-best candidate showing its `gatingReason` text (e.g. WFE-failing rejection). |
| `/` Right panel — "Iterations" (empty) | `AutoSessionLeaderboard` empty state | Confirm not regressed | Component returns `null` when no candidates | Open an auto-session with no leaderboard candidates → confirm the leaderboard area is cleanly empty (no crash, no stray header). |

---

## Backend-Only Changes (No UI Impact)

- `incredible_auto_dev/scripts/automation/browser-qa-phase.sh` — fixes the
  browser-QA port probe to target the app's real ports (`:3691`/`:8691` via the
  canonical `ensure_phase_ports` helper) and re-probes FE availability across a
  cold-start budget. Verification infrastructure only; no product surface, no
  endpoint, no data-contract change.
- `reports/qa/goal-financial_free-iter-8-evidence/` (seed + capture scripts,
  4 screenshots, README) — QA evidence artifacts, not shipped application code.

---

## Summary

- **Frontend surfaces changed:** 2 (status-strip gating; app-shell crash fix) +
  1 render-proven surface (leaderboard, no code change)
- **New pages/routes:** 0
- **Modified components:** 2 (`IterationPanel.tsx`, `useBacktest.ts`)
- **Navigation changes:** no
- **Backend-only changes:** 1 (browser-qa harness script; evidence artifacts not counted as code)
