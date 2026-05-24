# Goal Iteration 8 — Close the leaderboard PIXEL-render gate (J-16) → GOAL_ACHIEVED

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** financial_free
- **Iteration:** 8
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes
- **Target journeys:** J-16
- **Required-still-passing journeys:** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09, J-10, J-11, J-12, J-13, J-14, J-15 (all of them — this iteration adds no product logic)
- **Most-at-risk-of-regression:** J-08 (live cards), J-09 (best badge), J-10 (reload survival), J-12/J-13/J-14 (the open-universe `promote_k:2` run used to produce the leaderboard exercises these)
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - "The automated 'best' MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best."
  - "The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one."
  - "`GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint."
  - "The frozen dataclasses in `shared/contracts.py` must not be mutated in place."
  - "No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session."
  - "API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts."

## GOAL

Obtain the **load-bearing browser/pixel proof** that the `AutoSessionLeaderboard` component renders its rows in a real browser — the single remaining gate to GOAL_ACHIEVED — by fixing the `browser-qa-phase.sh` port-probe root cause and capturing the leaderboard in a foreground/visible browser context. No new product capability is delivered.

## BACKGROUND

J-16's data/endpoint/persistence/coherence layer is **complete and persisted** (verified at iter-7): `apps/frontend/src/components/AutoSessionLeaderboard.tsx` exists (real 147-line component, reads `entry.robustScore` verbatim, joins display metrics from `iterationHistory`, marks best solely by `entry.iterationId === autoRun.bestIterationId`, returns `null` when empty), 12 hermetic tests pass (including the binding `test_overfit_gating_higher_return_wfe_fail_not_best`), and live endpoint `TC-14` served deduped leaderboard rows on `:8691`. **The ONLY thing missing is positive pixel evidence that those rows actually paint.** The iter-7 spec made this render proof a hard, load-bearing DoD ("endpoint-only does NOT close a new render path"; "a 5th endpoint-only substitute is NOT acceptable") and it was not obtained — so the evaluator correctly withheld GOAL_ACHIEVED.

This has now slipped for the same two reasons, both confirmed in code this iteration:
1. **Harness port-probe drift (FIXABLE, must be fixed here).** `scripts/automation/browser-qa-phase.sh:112-113` defaults to base `:8000`/`:3000`, but `scripts/dev.sh` and `scripts/automation/lib/common.sh::ensure_phase_ports` bind the deterministic offset `8000 + _project_port_offset` / `3000 + _project_port_offset` = **`:8691` / `:3691`** for this repo (offset 691, verified). So browser-qa-agent probed a dead port, saw no frontend, and **SKIPPED all 10 tests**. `browser-qa-phase.sh` already `source`s `common.sh` (line 11) — the canonical helpers `_project_port_offset()` (common.sh:287) and `ensure_phase_ports()` (common.sh:~315) are present but **unused** by the port-derivation block.
2. **Chrome-MCP hidden-tab render throttle (documented env limit, NOT an app bug).** A backgrounded/contended Chrome-MCP tab reports `visibilityState:'hidden'`, which starves React 18's scheduler and the `useBacktest` poll timers, so the data-loaded frame never sustains and only empty frames are captured. The fix is a **foreground, visible, uncontended** browser context — or a deterministic Playwright capture that runs in its own visible context — NOT a change to the app's polling/visibility behavior.

**Lessons applied (from `lessons.md`, matched to this plan):**
- **iter-7:** "the fix must live in `browser-qa-phase.sh` itself … not in a handoff" and "treat a repeated skip on the same unfixed harness bug as a process stall, not a deferral." → The port fix is IN-SCOPE harness work this iteration; retrying the broken probe a 7th time is NOT acceptable.
- **iter-6:** a NET-NEW front-end render path "MUST NOT accept endpoint-layer proof as a substitute for browser QA," and the `git diff HEAD -- apps/` persistence gate must be re-applied. → Pixel proof is mandatory; persistence gate re-applied to the harness fix.
- **iter-4:** any walk-forward-dependent live QA "MUST use a date range ≥ IS_months + OOS_months (≥9mo)" or PROMOTE forms 0 windows → vacuous; and "construct/seek a WFE-failing higher-return candidate" so a rejection is visible. → Baked into the live-run recipe below.
- **iter-2/3:** verify the FE stays serving for the **whole** browser-qa window (health re-probe), don't just launch it once.
- **Memory `browser-qa-headless-render-throttle`:** blank Chrome-MCP page = hidden-tab throttle, not an app defect.

## IN SCOPE

### Harness / verification infrastructure (the load-bearing fix — NOT product code)
- [ ] Fix `scripts/automation/browser-qa-phase.sh` port derivation to target the SAME ports `scripts/dev.sh` binds. Preferred minimal fix: call the already-sourced canonical helper `ensure_phase_ports` (idempotent; respects caller-provided `CHAIN_*_PORT`, otherwise derives `8000 + _project_port_offset` / `3000 + _project_port_offset` and scans for a free port) **before** the URL-derivation block (lines ~112-115), so `_BACKEND_PORT`/`_FRONTEND_PORT` resolve to `:8691`/`:3691` for this repo instead of base `:8000`/`:3000`. Do not duplicate-and-drift the offset math — use the one helper (this is what produced the earlier `:3692`-vs-`:3691` mismatch).
- [ ] Make the frontend-availability gate **re-probe across the window** rather than decide once: the FE health check (`browser-qa-phase.sh:~152`) must retry the `curl` health probe for a reasonable cold-start budget (Next.js dev can take >10s) before declaring `FRONTEND_AVAILABLE=no` — reuse the existing `wait_for`-style curl helper (`browser-qa-phase.sh:~60`) / `ensure_services_running`.
- [ ] Verify the browser-qa-agent reaches the live app on the corrected port (HTTP 2xx/3xx on `FRONTEND_URL`) and does NOT SKIP for "frontend not available."

### Browser QA (the proof itself)
- [ ] Capture **real pixels** of the actual `AutoSessionLeaderboard` component rendering its rows, in a **foreground / visible** browser context (Chrome-MCP foreground tab preferred; a deterministic Playwright capture in its own visible context is an equally valid mechanism — see Verification recipe). The screenshot(s) MUST show:
  - **≥ 2 ranked candidate rows** (multiple walk-forward-validated candidates, enabled by `promote_k:2`);
  - the **BEST row highlighted** and equal to `autoRun.bestIterationId`;
  - **color-graded WFE chips** (green ≥ 0.5 / yellow 0.3–0.5 / red < 0.3);
  - a **non-best candidate's `gatingReason`** text visible (the WFE-failing / over-leveraged rejection).
- [ ] Save evidence screenshots under `reports/qa/goal-financial_free-iter-8-evidence/` and reference them in the browser-qa results report.

### Product code
- **None expected.** The component is built, type-clean, coherent, and data-proven. The ONLY product change permitted is a **minimal render-defect fix** if (and only if) the pixel capture reveals a genuine rendering bug (layout break, broken `iterationId` join, crash, or empty-when-rows-exist) — confined to the existing `AutoSessionLeaderboard.tsx` / `IterationPanel.tsx` and their existing canonical data reads. Any such fix MUST add a regression test and MUST NOT introduce a new endpoint, a new Data-Contract value, a second best definition, or any FE recompute of a canonical metric.

### New user-facing capability
None. This iteration converts J-16 from `partial` (data proven) to `passing` (render proven). The leaderboard surface itself already shipped at iter-7.

### New information displayed
None new. The leaderboard rows (`iterationId`, `stage`, `robustScore`, `eligible`, `gatingReason`, plus display metrics joined from `iterationHistory`) were registered at iter-7 and remain unchanged.

### New user actions
None.

### UI surface changes
None new. The Right-panel "Iterations" leaderboard (registered home for J-16) is rendered/captured, not added.

### Product surface delta
The user sees no change. The change is in the verification harness and in obtaining evidence of an already-shipped surface.

### Blueprint conformance
**No blueprint edit.** J-16's `autoRun.leaderboard` Data-Contract row and its Right-panel "Iterations" home were registered at iter-7 (`blueprint.md` Data Contract, the iter-7 best-marker extension row, and the IA "J-16 → Best badge / leaderboard → Right — Iterations"). This iteration introduces **no new displayed value, no new page, and no nav-skeleton change**, so there is no additive Data-Contract edit and **no `blueprint.reapproval-requested` file**. Deliberately not advancing any blueprint narrative ahead of verified state (avoids the iter-5 contract-ahead-of-code COHERENCE-WARN).

### Data-contract additions
None.

## OUT OF SCOPE

- Any new product feature, endpoint, Data-Contract value, store, or nav change.
- **Modifying product polling/visibility logic** (`apps/frontend/src/hooks/useBacktest.ts` or any component) to defeat the Chrome-MCP hidden-tab throttle. The throttle is an environment limit; the remedy is a foreground/visible capture context, NOT an app change (changing it would risk regressing J-08's live-poll behavior).
- Re-litigating settled gates: the eager-load anti-goal (resolved iter-1), the in-browser scorer/iterate-loop removal (done iter-2), and the single-`RobustScorer` / single-`BudgetTracker` coherence gate (re-confirmed iter-4/6/7).
- Pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (nice-to-have Capability #10, not a Must-have journey nor anti-goal).
- The flaky `test_post_returns_before_loop_completes_and_get_stays_responsive` (de-flake opportunistically only).
- The out-of-scope `/health` probe reconciliation and `auto_session.py` size — release-manager handles at commit.

## DEFINITION OF DONE

- [ ] **J-16 passes with real pixel evidence:** at least one screenshot from the actual `AutoSessionLeaderboard` render showing ≥ 2 ranked rows, the highlighted BEST row (== `bestIterationId`), color-graded WFE chips, and a non-best row's `gatingReason`. (This is the gate that, when met, makes all 16 journeys pass → GOAL_ACHIEVED.)
- [ ] **Harness root cause fixed and proven:** `browser-qa-phase.sh` targets `:3691`/`:8691` via the canonical `_project_port_offset`/`ensure_phase_ports` helper with health re-probe; the browser-qa-agent reaches the app and does NOT SKIP for an unreachable frontend.
- [ ] **Required-still-passing journeys J-01…J-15 remain green** — the full hermetic suite passes (expected: same counts as iter-7, **247 passed / 1 known pre-existing red (`test_directions_cache`) / 2 deselected**, plus any render-fix regression test); the 12 J-16 + 27 open-universe + 4 `promote_k` route tests stay green. (The harness fix touches no product code, so product-logic regression risk is ~zero.)
- [ ] **No anti-goal violation introduced:** `shared/contracts.py` not in diff; no new `RobustScorer(`/`BudgetTracker(` construction; no new endpoint/value/store; FE still reads `robustScore` verbatim; best still marked solely by `bestIterationId`; no secrets in artifacts; no product polling/visibility change.
- [ ] **DoD-0 persistence gate re-applied (iter-5 lesson):** `git diff HEAD` shows the `browser-qa-phase.sh` fix (and any render fix) actually landed in the working tree; `status.json.changed_files` is non-empty with `tests_run:true`; the dev handoff exists. (A green pytest cache is NOT evidence the change persisted.)
- [ ] Dev handoff written at `docs/handoffs/goal-financial_free-iter-8-dev.md`.

## TESTING REQUIREMENTS

- **Browser (LOAD-BEARING — the whole point of this iteration):**
  - **J-16** — leaderboard rows render in a real, visible browser context (ranked rows, highlighted best, WFE chips, non-best gating reason). This MUST be a genuine pixel capture, not an endpoint/JSON substitute.
  - Opportunistically, now that the port is fixed, re-confirm at the pixel layer: **J-08** (iteration/leaderboard cards appear live without manual reload), **J-09** (best badge marked), **J-10** (state survives a mid-run reload). These ride the same `autoRun` poll surface; capturing them clears the long-standing live-pixel debt but J-16 is the gating one.
- **Unit/integration:** full hermetic backend suite green; the J-16 leaderboard suite (`tests/test_auto_session_leaderboard.py`), the open-universe / WFE-gated / budget / staged suites, and the `promote_k` route tests stay green. No new tests are strictly required (the data layer is already covered) — but if a render-defect fix is applied, add a render/regression test for it. FE must still `tsc` + `vite build` + `eslint` clean.
- **Error cases:** confirm not regressed — the leaderboard renders a clean empty state (component returns `null`) when there are no candidates; `promote_k` validation still rejects out-of-range values (1–3 → 200, `0`/`4` → 422, omitted → 200).

### Verification recipe (how to make the pixels appear)

1. **Fix the port probe first**, then start services exactly as the app binds them (`scripts/dev.sh` → FE `:3691`, BE `:8691`) and confirm `curl http://localhost:3691` returns 2xx/3xx before driving the browser.
2. **Drive a live open-universe run for real rows:** `POST /api/auto-sessions` with **no `symbol`/`timeframe`** (open-universe), `objective: "robust"`, **`promote_k: 2`** (so ≥ 2 walk-forward-validated candidates rank), a **date range ≥ 9 months** (e.g. `2023-01-01` → `2023-12-01`, iter-4 lesson — shorter ranges form 0 WF windows → vacuous), the cheapest SCREEN model, a tiny budget, and lenient targets. Poll `GET /api/sessions/{id}` until `autoRun.leaderboard` has ≥ 2 entries and a terminal state.
3. **Make a REJECTION visible.** iter-7's live 2023 run happened to have *all* candidates pass the WFE gate, so no rejected row showed. To guarantee a `eligible:false` row with a `gatingReason` in pixels, prefer a run/range where a higher-raw-return candidate fails WFE (< 0.3) or is over-leveraged. If a live run cannot produce a rejection within the tiny budget/window, **seed the component render with the deterministic fixture data** used by `test_overfit_gating_higher_return_wfe_fail_not_best` (candidate A: higher return, WFE < 0.3 → `eligible:false`; candidate B: WFE-passing → best) — this still renders the real component and proves the rejection path paints.
4. **Capture in a visible context — pick whichever sustains a frame in this env (any ONE satisfies the gate):**
   - **(a) Chrome-MCP foreground tab** (preferred; native browser-qa path now that the port is correct). Keep the tab foreground/visible — do not background it and do not run a contending QA against another port in the same window.
   - **(b) Deterministic Playwright capture** in its own visible browser context (the same engine `scripts/automation/lib/demo_runner.py` drives). Playwright launches a visible context that does not suffer the Chrome-MCP hidden-tab throttle, so the React poll/scheduler runs and the leaderboard paints.
   - **(c) Seeded component render** — mount `AutoSessionLeaderboard` with a representative `autoRun.leaderboard` payload (including one `eligible:false` WFE-failing row and the `bestIterationId` row) and screenshot it. This renders the REAL component to real pixels and is an acceptable floor that closes the new-render-path gate (it is NOT an endpoint-only substitute).

   Path (a) or (b) on live data is strongest; (c) is the anti-stall floor so this iteration cannot miss again for lack of a sustainable live frame.

## NOTES

- **This is the final iteration before GOAL_ACHIEVED.** When the leaderboard pixel proof lands, all 16 Must-have journeys pass and the evaluator can declare GOAL_ACHIEVED.
- **STALL WATCH (explicit, from iter-7):** a 7th consecutive pixel miss on the *same unfixed* `browser-qa-phase.sh` port-probe bug is to be treated as a **process stall**, not another deferral. This iteration MUST fix the harness root cause (not retry the broken probe) AND must use a foreground/visible capture context. The three capture mechanisms above (esp. the seeded component render floor) exist specifically so the iteration has no excuse to miss the pixel again.
- **Exact fix location:** `scripts/automation/browser-qa-phase.sh` lines ~112-115 (port/URL derivation) and ~152 (one-shot FE availability gate). The canonical helpers are already sourced from `scripts/automation/lib/common.sh` (`_project_port_offset` @287, `ensure_phase_ports` @~315). The correct ports for this repo are FE `:3691` / BE `:8691` (offset 691, verified by `printf '%s' "$REPO_ROOT" | sha1sum | cut -c1-4` mod 1000).
- **Why the render proof matters even though the data layer is green:** the 12 hermetic tests + live endpoint prove the *data* and the *verbatim read*, but a genuinely-new render path can still carry a layout/join/crash bug invisible to data-layer tests. The pixel gate is exactly the check for that — do not treat "endpoint proves the data, therefore the pixels are fine" as sufficient (the inference the spec forbade at iter-6/7).
- **Do not** alter the app to work around the env throttle, change the `autoRun.leaderboard` schema, add an endpoint, or touch `shared/contracts.py`. The coherence-auditor's single-`RobustScorer` / one-best-definition / one-endpoint gate must continue to hold (it is coherence-neutral to edit a harness script).
