# goal-financial_free-iter-8 Execution Plan

**This is the FINAL iteration before GOAL_ACHIEVED.** It delivers NO new product capability.
It closes the single remaining gate for J-16: a **load-bearing browser/pixel proof** that the
already-shipped `AutoSessionLeaderboard` component paints its rows. The work is (1) fixing the
`browser-qa-phase.sh` port-probe root cause and (2) capturing real pixels in a visible browser
context. All 16 Must-have journeys pass once this lands.

## What to Build

- **Harness fix (load-bearing, NOT product code) — `scripts/automation/browser-qa-phase.sh`:**
  - Make the port/URL derivation (lines ~112–115) target the SAME ports the app binds
    (FE `:3691` / BE `:8691`, offset `691`) by calling the already-sourced canonical helper
    `ensure_phase_ports` (common.sh:~316) BEFORE that block — do **not** re-implement the offset
    math (duplicate-and-drift is what produced the earlier `:3692`-vs-`:3691` miss).
  - Make the frontend-availability gate (line ~152) **re-probe across a cold-start budget**
    (Next.js dev can take >10s) instead of deciding once — reuse `_wait_for_url` (line ~54) /
    `ensure_services_running` so a slow boot is not misread as "frontend not available."
  - **Verify the resolved `FRONTEND_URL` actually returns 2xx/3xx** before driving the browser; the
    agent must NOT SKIP for "frontend not available" when the app is in fact up.
- **Capture the J-16 pixels** of the real `AutoSessionLeaderboard` render in a **foreground/visible**
  context (see Capture mechanisms below). Screenshots saved under
  `reports/qa/goal-financial_free-iter-8-evidence/`.
- **Product code: NONE expected.** The only permitted product change is a *minimal render-defect fix*
  IF (and only if) the pixel capture reveals a genuine rendering bug (layout break, broken
  `iterationId` join, crash, empty-when-rows-exist) — confined to the existing
  `AutoSessionLeaderboard.tsx` / `IterationPanel.tsx` and their existing canonical data reads, and
  it MUST add a regression test. No new endpoint, value, store, second-best definition, or FE
  recompute of a canonical metric.

## ⚠️ Critical implementation nuance (the 6-iteration recurring trap)

`scripts/dev.sh` and `scripts/start-frontend.sh` resolve the port as `3000 + offset` **directly**
(→ `:3691`). But `ensure_phase_ports` uses `_find_free_port(3000+offset)` which **scans upward** if
`:3691` is already LISTENing — yielding `:3692`, which is then dead. To avoid reintroducing the
off-by-one:
- Call `ensure_phase_ports` **once, early** (before any service is started in this script and before
  the stale-server kill), and **export** `CHAIN_BACKEND_PORT`/`CHAIN_FRONTEND_PORT` so the
  URL-derivation, `ensure_services_running`, and `start-frontend.sh` all inherit the **same** resolved
  port. (Idempotent: if the caller already exported `CHAIN_*_PORT` — e.g. `CHAIN_SHARED_SERVICES=true`
  — the helper respects it and does NOT scan.)
- After resolution + re-probe, **confirm the probe URL reaches the live app**. If `ensure_phase_ports`
  scanned past a live app on `:3691` to `:3692`, the verify step must catch it and reconcile to the
  port the app is actually serving on. The end-to-end invariant: *the port browser-qa probes ==
  the port the frontend is bound to.*

## Agents Required

- **developer: yes** — apply the `browser-qa-phase.sh` harness fix; apply a minimal
  `AutoSessionLeaderboard.tsx`/`IterationPanel.tsx` render fix ONLY if the pixel capture reveals a real
  render bug (add a regression test if so). Write the dev handoff.
- backend-data: **no** — no backend product code changes. (Driving a live `POST /api/auto-sessions`
  run is verification against existing endpoints, not backend development.)
- frontend-ux: **no** net-new work — the leaderboard component already shipped at iter-7; only a
  conditional defect fix is in play.
- browser-qa-agent (pipeline-driven): captures the load-bearing pixels — see Capture mechanisms.

## Frontend Present

yes

(Browser/pixel QA is the entire point of this iteration — `qa-phase.sh`/`browser-qa-phase.sh` MUST run
the Chrome MCP checks. This is `yes` because the iteration's DoD is a pixel proof, even though it adds
no new product UI.)

## Files to Create/Modify

- `scripts/automation/browser-qa-phase.sh` — **fix** port/URL derivation to call `ensure_phase_ports`
  (→ `:3691`/`:8691`); make the FE-availability gate health-re-probe across a cold-start budget; verify
  the probe reaches the live app. *(Harness/infra, not product code — coherence-neutral.)*
- `reports/qa/goal-financial_free-iter-8-evidence/*.png` — **new** load-bearing leaderboard
  screenshots referenced by the browser-qa results report.
- `docs/handoffs/goal-financial_free-iter-8-dev.md` — **new** dev handoff.
- *(conditional only)* `apps/frontend/src/components/AutoSessionLeaderboard.tsx` and/or
  `apps/frontend/src/components/IterationPanel.tsx` — minimal render-defect fix **iff** pixels reveal a
  genuine bug, plus a regression test. Otherwise untouched.
- **MUST NOT touch:** `apps/backend/shared/contracts.py`, `auto_session.py` scoring, any endpoint,
  `useBacktest.ts` polling/visibility logic, the `autoRun.leaderboard` schema, `blueprint.md`.

## UI Evolution

- **New user-facing capability:** None. The leaderboard surface shipped at iter-7. This iteration only
  obtains pixel evidence that it renders.
- **New information displayed:** None. Leaderboard rows (`iterationId`, `stage`, `robustScore`,
  `eligible`, `gatingReason` + display metrics joined from `iterationHistory`) were registered iter-7
  and are unchanged.
- **New user actions:** None.
- **UI surface changes:** None new. The Right-panel "Iterations" leaderboard (registered home for
  J-16) is rendered/captured, not added.
- **Navigation changes:** None.
- **Blueprint:** No edit, no `blueprint.reapproval-requested` — no new displayed value, page, or
  nav-skeleton change. (Deliberately not advancing the blueprint ahead of verified state — avoids the
  iter-5 contract-ahead-of-code COHERENCE-WARN.)

## Visual Requirements (acceptance for the pixel capture)

The captured screenshot(s) of the **real** `AutoSessionLeaderboard` render MUST show:
- **≥ 2 ranked candidate rows** (multiple walk-forward-validated candidates; enabled by `promote_k:2`),
  ranked by `robustScore` desc with ineligible/null last.
- The **BEST row highlighted** (violet "BEST" badge) and equal to `autoRun.bestIterationId` — best is
  marked **solely** by `entry.iterationId === autoRun.bestIterationId`.
- **Color-graded WFE chips** — emerald ≥ 0.5 / amber 0.3–0.5 / red < 0.3 (`—` for screen rows).
- A **non-best candidate's `gatingReason` text** visible (the WFE-failing / over-leveraged rejection).
- Layout/effects: dense dark analytical-workstation styling already in the component (badges, chips,
  per-row metrics). No restyling — capture as-is.
- Empty state remains correct: component returns `null` (renders nothing) when there are no candidates.

## Capture mechanisms (pick whichever sustains a frame — ANY ONE satisfies the gate)

The Chrome-MCP **hidden-tab render throttle** (a documented env limit, NOT an app bug — see memory
`browser-qa-headless-render-throttle`) starves React/poll timers in a backgrounded/contended tab, so an
empty frame paints. The remedy is a **visible, uncontended** context — NOT an app change. Note: the
usual "fall back to backend endpoints" is **explicitly disallowed** here — endpoint proof does not close
a NEW render path (iter-6/7 lesson). Three real-pixel options:
- **(a) Chrome-MCP foreground tab** (preferred now that the port is fixed): keep the tab foreground and
  do NOT run a contending QA on another port in the same window.
- **(b) Deterministic Playwright capture** in its own visible context (same engine as
  `incredible_auto_dev/scripts/automation/lib/demo_runner.py`) — not subject to the hidden-tab throttle.
- **(c) Seeded component render (anti-stall FLOOR):** mount the REAL `AutoSessionLeaderboard` with a
  representative `autoRun.leaderboard` payload (one `eligible:false` WFE-failing row + the
  `bestIterationId` row) and screenshot it. Renders the real component to real pixels; an acceptable
  floor that closes the new-render-path gate (NOT an endpoint substitute).

**STALL WATCH:** a 7th consecutive pixel miss on this same unfixed harness bug is a process stall, not a
deferral. The harness root cause MUST be fixed (not the probe retried), AND a visible capture context
MUST be used. Mechanism (c) exists so there is no excuse to miss again.

## Live-run recipe (for options a/b — real rows)

After the port fix, start services as the app binds them (`scripts/dev.sh` → FE `:3691`/BE `:8691`) and
confirm `curl http://localhost:3691` is 2xx/3xx, then:
1. `POST /api/auto-sessions` with **no `symbol`/`timeframe`** (open-universe), `objective:"robust"`,
   **`promote_k:2`** (≥ 2 WF-validated candidates rank), a date range **≥ 9 months** (e.g.
   `2023-01-01`→`2023-12-01`; shorter ranges form 0 WF windows → vacuous, iter-4 lesson), the cheapest
   SCREEN model, a tiny budget, lenient targets.
2. Poll `GET /api/sessions/{id}` until `autoRun.leaderboard` has ≥ 2 entries and a terminal state.
3. **Make a rejection visible:** prefer a run/range where a higher-raw-return candidate fails WFE
   (< 0.3) or is over-leveraged. If a live run can't produce a rejection within the tiny budget, use the
   seeded-render floor (c) with the deterministic
   `test_overfit_gating_higher_return_wfe_fail_not_best` fixture (candidate A: higher return, WFE < 0.3
   → `eligible:false`; candidate B: WFE-passing → best).

## Key Test Scenarios

- **(GATING) J-16 pixel proof:** ≥ 1 screenshot of the actual `AutoSessionLeaderboard` render showing
  ≥ 2 ranked rows, the highlighted BEST row (== `bestIterationId`), color-graded WFE chips, and a
  non-best row's `gatingReason`. Genuine pixels, not JSON. → makes all 16 journeys pass → GOAL_ACHIEVED.
- **Harness proven:** `browser-qa-phase.sh` targets `:3691`/`:8691` via `ensure_phase_ports` with health
  re-probe; browser-qa-agent reaches the app and does NOT SKIP for an unreachable frontend.
- **Opportunistic pixel debt (now that the port is fixed):** re-confirm at the pixel layer **J-08**
  (cards appear live without manual reload), **J-09** (best badge marked), **J-10** (state survives a
  mid-run reload). J-16 is the gating one; these clear long-standing live-pixel debt.
- **J-01…J-15 stay green:** full hermetic backend suite (expected ~247 passed / 1 known pre-existing red
  `test_directions_cache` / 2 deselected, plus any render-fix regression test); the 12 J-16 + 27
  open-universe/WFE/budget/staged + 4 `promote_k` route tests stay green. FE stays `tsc` + `vite build` +
  `eslint` clean. (Harness fix touches no product code → product-regression risk ≈ 0.)
- **Error cases not regressed:** leaderboard renders clean empty state (`null`) with no candidates;
  `promote_k` validation still 1–3 → 200, `0`/`4` → 422, omitted → 200.

## DoD-0 persistence gate (re-apply — iter-5 lesson)

`git diff HEAD` MUST show the `browser-qa-phase.sh` fix (and any render fix) landed in the working tree;
`status.json.changed_files` non-empty with `tests_run:true`; dev handoff present at
`docs/handoffs/goal-financial_free-iter-8-dev.md`. A green pytest cache is NOT evidence the change
persisted.

## Anti-goal guardrails (must all hold)

`shared/contracts.py` not in diff; no new `RobustScorer(`/`BudgetTracker(` construction; no new
endpoint/value/store; FE still reads `robustScore` verbatim; best marked solely by `bestIterationId`;
no secrets in artifacts; **no product polling/visibility change** (`useBacktest.ts` untouched — changing
it to defeat the throttle would risk regressing J-08's live poll). The coherence gate (single
`RobustScorer` / one-best-definition / one-endpoint) continues to hold — editing a harness script is
coherence-neutral.

## Scope & Alignment

- **Aligned with `docs/goal.md`:** J-16 is the last Must-have journey; this iteration closes its pixel
  verification with zero product change. No drift, no scope creep — the spec is disciplined about adding
  no product code.
- **Out of scope (do not touch):** new product feature/endpoint/value/store/nav; modifying app
  polling/visibility to defeat the throttle; re-litigating settled gates (eager-load resolved iter-1,
  in-browser loop removed iter-2, single-scorer/budget re-confirmed iter-4/6/7); the pre-existing red
  `test_directions_cache`; the flaky `test_post_returns_before_loop_completes_and_get_stays_responsive`
  (de-flake opportunistically only); the `/health` probe reconciliation and `auto_session.py` size
  (release-manager handles at commit).
