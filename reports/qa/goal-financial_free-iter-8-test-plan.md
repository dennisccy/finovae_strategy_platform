# goal-financial_free-iter-8 Functional Test Plan

**Phase:** goal-financial_free-iter-8
**Date:** 2026-05-24
**Frontend Present:** yes

## Phase Goal

Close J-16's single remaining gate by (1) fixing the `browser-qa-phase.sh` port-probe root cause so the harness targets the SAME ports the app binds (FE `:3691` / BE `:8691`, offset 691) with a cold-start health re-probe, and (2) capturing load-bearing real-pixel evidence that the already-shipped `AutoSessionLeaderboard` component paints its rows — with NO new product capability. When the pixel proof lands, all 16 Must-have journeys pass → GOAL_ACHIEVED.

## Test Cases

### TC-01 — Harness port derivation targets the app's bound ports

**Type:** artifact
**Preconditions:** `scripts/automation/browser-qa-phase.sh` has been modified; repo offset is 691.

**Steps:**
1. Inspect `browser-qa-phase.sh` around the port/URL-derivation block (lines ~112–115).
2. Confirm it calls the canonical `ensure_phase_ports` helper (sourced from `common.sh`) BEFORE deriving `FRONTEND_URL`/`BACKEND_URL`, rather than re-implementing offset math or defaulting to base `:8000`/`:3000`.
3. Confirm `CHAIN_BACKEND_PORT`/`CHAIN_FRONTEND_PORT` are exported so URL-derivation, `ensure_services_running`, and `start-frontend.sh` inherit the same resolved ports.

**Expected outcome:** Script resolves FE `:3691` / BE `:8691` for this repo via the single canonical helper; no duplicated offset math.
**Pass criteria:** `ensure_phase_ports` is invoked once early; `FRONTEND_URL` resolves to `http://localhost:3691` (no `:3692` off-by-one; no base `:3000`/`:8000`).

---

### TC-02 — Frontend-availability gate re-probes across a cold-start budget

**Type:** artifact
**Preconditions:** TC-01 fix present.

**Steps:**
1. Inspect the FE-availability gate (`browser-qa-phase.sh` ~line 152).
2. Confirm it retries the health `curl` (via `_wait_for_url`-style helper / `ensure_services_running`) across a reasonable Next.js cold-start budget (>10s) instead of deciding once.

**Expected outcome:** A slow FE boot is not misread as "frontend not available."
**Pass criteria:** The gate loops/waits on the health probe before setting `FRONTEND_AVAILABLE=no`; single-shot decision is removed.

---

### TC-03 — Frontend reachable on corrected port; no SKIP

**Type:** api
**Preconditions:** Services started as the app binds them (`scripts/dev.sh` → FE `:3691`, BE `:8691`).

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" http://localhost:3691`
2. `curl -s -o /dev/null -w "%{http_code}" http://localhost:8691/health` (or backend root)

**Expected outcome:** FE responds 2xx/3xx; backend responds 2xx.
**Pass criteria:** FE returns HTTP 200/3xx on `:3691`; browser-qa-agent reaches the app and does NOT SKIP for "frontend not available." (Per qa.md, a justified SKIP for an unrelated env reason is NOT an automatic FAIL — but an unreachable-frontend SKIP on the corrected port IS a blocker for this iteration.)

---

### TC-04 — Live open-universe run produces ≥ 2 ranked leaderboard rows

**Type:** api
**Preconditions:** Services up on `:3691`/`:8691`; TC-03 passed.

**Steps:**
1. `POST http://localhost:8691/api/auto-sessions` with body: no `symbol`/`timeframe` (open-universe), `objective:"robust"`, `promote_k:2`, date range `2023-01-01`→`2023-12-01` (≥ 9 months), cheapest SCREEN model, tiny budget, lenient targets.
2. Poll `GET http://localhost:8691/api/sessions/{id}` until terminal state.

**Expected outcome:** Session reaches a terminal state with `autoRun.leaderboard` populated.
**Pass criteria:** `autoRun.leaderboard` has ≥ 2 entries; `autoRun.bestIterationId` is set and equals exactly one entry's `iterationId`.

---

### TC-05 — `GET /api/sessions/{id}` does not eagerly parse per-iteration payloads (anti-goal)

**Type:** api
**Preconditions:** A session with multiple iterations exists.

**Steps:**
1. `GET /api/sessions/{id}` (list/open path).
2. Inspect response shape vs. per-iteration detail endpoint.

**Expected outcome:** List/open path returns summary + `autoRun` without full per-iteration `result.json`/`rating.json` bodies inlined.
**Pass criteria:** Iteration detail is lazy-loaded via the existing per-iteration endpoint; no eager full payload in the list path.

---

### TC-06 — J-16 leaderboard rows render in a visible browser (LOAD-BEARING pixel proof)

**Type:** browser
**Preconditions:** TC-03 passed; a session with ≥ 2 leaderboard rows available (TC-04 live run, or the deterministic seeded-render floor mechanism (c)). Capture in a foreground/visible context (Chrome-MCP foreground tab, OR deterministic Playwright, OR seeded real-component render) — endpoint/JSON proof is explicitly disallowed.

**Steps:**
1. Open the app, navigate to the session's Right-panel "Iterations" leaderboard surface.
2. Wait for the `autoRun` poll surface to load rows in a sustained (visible, uncontended) frame.
3. Screenshot the actual `AutoSessionLeaderboard` render to `reports/qa/goal-financial_free-iter-8-evidence/TC-06-leaderboard.png`.

**Expected outcome:** Real pixels of the leaderboard with ranked rows visible.
**Pass criteria:** Screenshot shows ALL of: (a) ≥ 2 ranked candidate rows (sorted by `robustScore` desc, ineligible/null last); (b) the BEST row highlighted (violet "BEST" badge) and equal to `autoRun.bestIterationId`; (c) color-graded WFE chips (emerald ≥ 0.5 / amber 0.3–0.5 / red < 0.3; `—` for screen rows); (d) a non-best candidate's `gatingReason` text visible (WFE-failing / over-leveraged rejection). The screenshot is genuine pixels, not a JSON/endpoint substitute.

---

### TC-07 — Best selected by robust objective, not raw return (anti-goal)

**Type:** browser
**Preconditions:** TC-06 render available (live or seeded with the `test_overfit_gating_higher_return_wfe_fail_not_best` fixture: candidate A higher return + WFE < 0.3 → `eligible:false`; candidate B WFE-passing → best).

**Steps:**
1. In the rendered leaderboard, identify the highest raw-return candidate and the BEST-marked row.
2. Compare against `autoRun.bestIterationId`.

**Expected outcome:** A higher raw-return but WFE-failing / over-leveraged candidate is marked `eligible:false` with a `gatingReason` and is NOT marked best.
**Pass criteria:** The "BEST" badge sits solely on `entry.iterationId === autoRun.bestIterationId` (the WFE-gated winner), NOT on the higher-raw-return WFE-failing row; the rejected row shows its `gatingReason`.

---

### TC-08 — Opportunistic live-pixel re-confirm: J-08 / J-09 / J-10

**Type:** browser
**Preconditions:** TC-03 passed; a live run in progress/terminal on the corrected port.

**Steps:**
1. J-08: observe iteration/leaderboard cards appear during a run WITHOUT a manual reload.
2. J-09: confirm the best badge is marked on the winning iteration.
3. J-10: reload the page mid-run and confirm state survives.
4. Screenshot each to `reports/qa/goal-financial_free-iter-8-evidence/`.

**Expected outcome:** Live cards paint without manual reload; best badge present; reload preserves state.
**Pass criteria:** J-08/J-09/J-10 each verified at the pixel layer. (Opportunistic — J-16/TC-06 is the gating proof; a SKIP here due to env render throttle is not a hard FAIL.)

---

### TC-09 — Full hermetic backend suite stays green (J-01…J-15 no regression)

**Type:** api
**Preconditions:** Working tree includes the harness fix (and any conditional render fix).

**Steps:**
1. Run the full hermetic backend test suite (test command from `.claude/project-template.md`), capturing stdout+stderr.
2. Confirm the 12 J-16 leaderboard tests (`tests/test_auto_session_leaderboard.py`), 27 open-universe/WFE/budget/staged tests, and 4 `promote_k` route tests are green.

**Expected outcome:** Same counts as iter-7.
**Pass criteria:** ~247 passed / 1 known pre-existing red (`test_directions_cache::test_write_and_read_full_round_trip`, out of scope) / 2 deselected, plus any render-fix regression test. No NEW failures. `test_overfit_gating_higher_return_wfe_fail_not_best` passes.

---

### TC-10 — Frontend build/lint/type clean

**Type:** api
**Preconditions:** FE source present (untouched unless a conditional render fix landed).

**Steps:**
1. Run FE `tsc`, `vite build`, and `eslint` (commands from project-template.md).

**Expected outcome:** All three pass.
**Pass criteria:** `tsc` no errors; `vite build` succeeds; `eslint` clean.

---

### TC-11 — `promote_k` validation not regressed (error cases)

**Type:** api
**Preconditions:** Backend up on `:8691`.

**Steps:**
1. `POST /api/auto-sessions` with `promote_k:1`, `:2`, `:3` → expect 200.
2. `POST` with `promote_k:0` and `promote_k:4` → expect 422.
3. `POST` omitting `promote_k` → expect 200 (default).

**Expected outcome:** In-range accepted, out-of-range rejected, omitted defaulted.
**Pass criteria:** 1–3 → 200; 0/4 → 422; omitted → 200.

---

### TC-12 — Leaderboard empty state renders nothing

**Type:** browser
**Preconditions:** A session/state with no candidates in `autoRun.leaderboard`.

**Steps:**
1. Render the surface for a session with an empty leaderboard.

**Expected outcome:** Component returns `null` — no leaderboard chrome, no crash.
**Pass criteria:** No leaderboard rows or empty-table placeholder painted; no console error; component renders nothing.

---

### TC-13 — Anti-goal guardrails hold in the diff

**Type:** artifact
**Preconditions:** Changes staged; `git diff HEAD` available.

**Steps:**
1. `git diff HEAD --stat` and inspect changed files.

**Expected outcome:** Only harness + evidence + handoff (and conditional render fix + its test) changed.
**Pass criteria:** `apps/backend/shared/contracts.py` NOT in diff; no new `RobustScorer(`/`BudgetTracker(` construction; no new endpoint/value/store; `useBacktest.ts` polling/visibility UNCHANGED; FE still reads `robustScore` verbatim; best marked solely by `bestIterationId`; no secrets/API keys in evidence or artifacts; `blueprint.md` not edited; no `blueprint.reapproval-requested`.

---

### TC-14 — DoD-0 persistence gate (change actually landed)

**Type:** artifact
**Preconditions:** Iteration work complete.

**Steps:**
1. `git diff HEAD -- scripts/automation/browser-qa-phase.sh` shows the port/probe fix.
2. Inspect `runs/goal-financial_free-iter-8/status.json` for non-empty `changed_files` and `tests_run:true`.
3. Confirm `docs/handoffs/goal-financial_free-iter-8-dev.md` exists.
4. Confirm evidence PNG(s) exist under `reports/qa/goal-financial_free-iter-8-evidence/`.

**Expected outcome:** The fix is persisted on disk (not just a green pytest cache).
**Pass criteria:** Diff present in working tree; `status.json.changed_files` non-empty + `tests_run:true`; dev handoff exists; ≥ 1 evidence screenshot saved.

---

## Summary

Total test cases: 14

- **API tests:** 6 (TC-03, TC-04, TC-05, TC-09, TC-10, TC-11)
- **Browser tests:** 4 (TC-06, TC-07, TC-08, TC-12)
- **Artifact checks:** 4 (TC-01, TC-02, TC-13, TC-14)

**Gating test:** TC-06 (J-16 load-bearing pixel proof). When TC-06 + TC-01/02/03 (harness root-cause fix proven) pass, all 16 Must-have journeys pass → GOAL_ACHIEVED. Endpoint/JSON proof is explicitly NOT an acceptable substitute for TC-06.
