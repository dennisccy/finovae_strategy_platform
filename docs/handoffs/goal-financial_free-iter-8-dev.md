# goal-financial_free-iter-8 Dev Handoff

**Phase:** goal-financial_free-iter-8
**Date:** 2026-05-24
**Agent:** developer
**Status:** complete

## What Was Built

This is the final iteration before GOAL_ACHIEVED. It delivers **no new product
capability** — it closes the single remaining J-16 gate: the load-bearing
browser/pixel proof that the already-shipped `AutoSessionLeaderboard` paints its
rows. Three things landed:

1. **Harness root-cause fix (the load-bearing fix) — `scripts/automation/browser-qa-phase.sh`.**
   The browser-QA port probe defaulted to base `:8000`/`:3000`, but `scripts/dev.sh`
   binds the deterministic offset ports `:8691`/`:3691` (offset 691). So the probe
   hit a dead port, the frontend-availability gate saw "no frontend," and all 10
   browser tests SKIPPED — six iterations running. Fixed by:
   - Calling the canonical `ensure_phase_ports` helper (no re-implemented offset
     math) so the probe resolves to the same ports the app binds.
   - **Reconciling drift to the live app:** if the resolved port (whether
     `_find_free_port` scanned past a LISTENing app, or the caller exported a stale
     `CHAIN_FRONTEND_PORT`) does NOT answer 2xx/3xx but the base offset port does,
     the probe is reconciled to the base. Enforces the invariant *probe port == the
     port the app is actually bound to*. (Verified live: with the real pipeline env
     `CHAIN_FRONTEND_PORT=3692` (dead) it reconciles to the live `:3691`.)
   - Making the frontend-availability gate **re-probe across a cold-start budget**
     (`_wait_for_url … 90`) instead of deciding once, so a slow dev boot is not
     misread as "frontend not available."

2. **A minimal render-defect (crash) fix — the pixel gate caught a real bug.**
   The first pixel capture revealed that the app **crashed before the leaderboard
   could paint**. `App.tsx` mounts a `SessionContainer` (and thus a `useBacktest`
   hook) for **every** session; 70 of the ~140 sessions in the durable store carry a
   legacy/partial `autoRun` block (pre-`budget`-schema: `currentIteration`/`spend`,
   no `budget`). `useBacktest.ts:482` derived `autoRun.budget.iterationsDone` guarded
   only by `autoRun` being truthy → `Cannot read properties of undefined (reading
   'iterationsDone')` → unhandled (no error boundary) → the whole app blanked. This
   was invisible to data-layer tests and had been masked by six browser-QA SKIPs.
   Fix (minimal, surgical):
   - `useBacktest.ts` — guard the derivation: `autoRun?.budget ? {…} : null`.
   - `IterationPanel.tsx` — gate the budget-dependent status strip:
     `{autoRun?.budget && <AutoSessionStatusStrip …/>}` (the leaderboard itself reads
     `leaderboard`/`bestIterationId`, never `budget`, so it is untouched and renders
     for any session).

3. **The J-16 pixel proof itself** (Playwright, dedicated visible context — not the
   Chrome-MCP throttled tab). Two captures under
   `reports/qa/goal-financial_free-iter-8-evidence/`:
   - **Seeded (option c):** the binding J-16 fixture rendered by the REAL component
     — 3 ranked rows, BEST badge on `bestIterationId`, color-graded WFE chips, and a
     non-best **WFE-failing rejection** (`WFE 0.10 < 0.30`). The highest-score / highest
     -return row is NOT best (the overfit gating made visible).
   - **Live (option b):** the real iter-7 open-universe run (`2a829f6e…`) painting
     genuine data (clears the long-standing J-08/J-09 live-pixel debt too).

## Files Changed

- `incredible_auto_dev/scripts/automation/browser-qa-phase.sh` (via the `scripts/`
  symlink) — port reconciliation + cold-start FE re-probe. **Harness/infra, not
  product code — coherence-neutral.**
- `apps/frontend/src/hooks/useBacktest.ts` — guard `autoRun?.budget` in the
  `autoRunProgress` render-derivation (crash fix). **Not poll/visibility logic.**
- `apps/frontend/src/components/IterationPanel.tsx` — gate `AutoSessionStatusStrip`
  on `autoRun?.budget` (2 call sites). Leaderboard mounts unchanged.
- `reports/qa/goal-financial_free-iter-8-evidence/` (new) — 4 screenshots, the
  `seed_leaderboard_session.py` + `capture_leaderboard.py` reproduction scripts, and
  a README.

## Scope note on `useBacktest.ts`

The plan listed `useBacktest.ts` under "must not touch" — but specifically its
**polling/visibility logic** (changing it to defeat the throttle would risk
regressing J-08's live poll). The change here is a **null-guard on a render-derived
value** (`autoRunProgress`); it does not alter poll cadence, visibility handling, or
throttle behavior in any way. The crash is physically located in this hook (it runs
during the hook body, before any JSX), so the fix is unavoidable there. The spec
explicitly permits "a minimal render-defect fix if … the pixel capture reveals a
genuine rendering bug (… crash …)" — which is exactly what happened. No new
endpoint/value/store/second-best-definition was introduced and no canonical metric
is recomputed.

## Tests Run

- **Backend (hermetic):** `cd apps/backend && .venv/bin/python -m pytest -q`
  → **247 passed, 1 failed, 2 deselected.** The single failure is the known
  pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  (nice-to-have Capability #10, explicitly out of scope). The previously-flaky
  `test_post_returns_before_loop_completes_and_get_stays_responsive` passed (verified
  flaky: 3/3 green on isolated re-run). No product-logic regression (the harness fix
  is a shell script; the FE fix is a null-guard).
- **Frontend:** `npm run build` (tsc && vite build) → **clean (exit 0)**;
  `npm run lint` (eslint, `--max-warnings 0`) → **clean (exit 0)**.
- **Browser/pixel (load-bearing):** Playwright capture of the real
  `AutoSessionLeaderboard` — seeded render (all 4 DoD elements incl. rejection,
  clean exit 0) + live-run render (real data). Screenshots in the evidence dir.
- **Harness fix proven:** simulated the real pipeline env (`CHAIN_FRONTEND_PORT=3692`
  dead, `CHAIN_BACKEND_PORT=8691` live) → reconciles to `:3691`, both probes 200,
  `FRONTEND_AVAILABLE=yes` (would NOT SKIP).

## DoD-0 persistence gate

`git diff HEAD` shows all three files modified in the working tree
(`incredible_auto_dev/scripts/automation/browser-qa-phase.sh`,
`apps/frontend/src/hooks/useBacktest.ts`,
`apps/frontend/src/components/IterationPanel.tsx`); evidence dir is untracked-new;
`status.json.changed_files` non-empty with `tests_run:true`.

## Anti-goal guardrails (all hold)

- `shared/contracts.py` NOT in diff. ✓
- No new `RobustScorer(`/`BudgetTracker(` construction in **product** code. ✓
  (The evidence seed script constructs `BudgetTracker(...)` to drive the REAL
  controller for seeding — it reuses the canonical classes, does not fork them, and
  lives under `reports/qa/…`, not `apps/`.)
- No new endpoint / Data-Contract value / store / nav. ✓ (the seed writes standard
  artifacts via the existing controller + file store.)
- FE still reads `robustScore` verbatim; best still marked solely by
  `bestIterationId`. ✓ (leaderboard component untouched.)
- No secrets in artifacts. ✓ (FakePipeline; no keys.)
- No product polling/visibility change. ✓

## Known Issues

- The crash fix means **70 legacy auto-sessions** (pre-`budget` schema) now render
  without their status strip (graceful degradation) instead of crashing the app.
  This is correct behavior; those old sessions never had a budget block to show.
- The seeded proof session `j16-leaderboard-proof` remains in the durable store
  (most-recently-accessed) as the default the pipeline browser-QA will open. It is a
  real, standard-schema session created via the real controller; delete with
  `ss.delete_session("j16-leaderboard-proof")` if undesired. Re-create with the
  idempotent seed script.
- Pre-existing red `test_directions_cache` and flaky
  `test_post_returns_before_loop_completes_and_get_stays_responsive` are unchanged
  (out of scope per the spec).
