# goal-financial_free-iter-7 Functional Test Plan

**Phase:** goal-financial_free-iter-7
**Date:** 2026-05-24
**Frontend Present:** yes

## Phase Goal

After an open-universe automated run, the right-hand Iterations panel shows a ranked **leaderboard** of evaluated candidates (canonical robust score, served per-candidate), with the WFE-gated best highlighted and a higher-raw-return-but-WFE-failing/over-leveraged candidate visibly **not** selected as best (gating reason shown) — closing J-16, the final must-have journey.

## Test Cases

### TC-01 — Persistence gate (DoD-0, LOAD-BEARING, run FIRST)

**Type:** artifact
**Preconditions:** Dev work claimed complete on the pipeline working tree (not a worktree).

**Steps:**
1. `git diff --stat HEAD -- apps/`
2. `git diff --name-only HEAD -- apps/`
3. Read `runs/goal-financial_free-iter-7/status.json`
4. Read `docs/handoffs/goal-financial_free-iter-7-dev.md` "Files Changed" list

**Expected outcome:** Diff is non-empty and includes `apps/backend/backend/auto_session.py`, `apps/backend/backend/auto_session_routes.py`, the NEW `apps/frontend/src/components/AutoSessionLeaderboard.tsx`, `apps/frontend/src/lib/sessionApi.ts`, `apps/frontend/src/components/IterationPanel.tsx`, and a new J-16 backend test file.
**Pass criteria:** All listed files present in `git diff`; `status.json.changed_files` non-empty AND `tests_run: true`; handoff "Files Changed" matches `git diff --name-only HEAD -- apps/`. **Empty `apps/` diff or missing FE component = automatic FAIL.**

---

### TC-02 — Canonical robust score (one scorer, no FE recompute)

**Type:** artifact
**Preconditions:** J-16 hermetic test file present; backend suite runnable.

**Steps:**
1. Run the canonical-score hermetic test (FakePipeline, open-universe).
2. `git diff HEAD -- apps/ | grep -E 'RobustScorer\(|BudgetTracker\('`

**Expected outcome:** Every `leaderboard[*].robustScore` equals `RobustScorer.score(metrics)` for that candidate; the grep finds NO new `RobustScorer(...)`/`BudgetTracker(...)` construction in the diff.
**Pass criteria:** Test passes asserting equality against the single scorer; grep returns no new construction sites.

---

### TC-03 — Overfit-gating: WFE-failing higher-return candidate not best (binding J-16 assertion)

**Type:** api
**Preconditions:** Hermetic FakePipeline run with `promote_k=2`; candidate A = higher raw return + `wfe<0.3`, candidate B = lower raw return + `wfe>=0.3`.

**Steps:**
1. Trigger the run and load `GET /api/sessions/{id}`.
2. Inspect `autoRun.leaderboard` and `autoRun.bestIterationId`.

**Expected outcome:** `bestIterationId == B`; A is in the leaderboard with `eligible:false` and a `gatingReason` citing WFE (e.g. `"WFE 0.21 < 0.30"`); A (higher return) is NOT best.
**Pass criteria:** Best is B; A present, `eligible:false`, gatingReason names WFE; A.iterationId != bestIterationId.

---

### TC-04 — Overfit-gating: over-leveraged candidate not best

**Type:** api
**Preconditions:** Hermetic run including a high-return `margin_called` candidate.

**Steps:**
1. Load `GET /api/sessions/{id}` after the run.
2. Inspect the margin-called candidate's leaderboard entry.

**Expected outcome:** The over-leveraged candidate has `eligible:false`, `gatingReason` cites over-leverage (margin called), and is not `bestIterationId`.
**Pass criteria:** `eligible:false` + gatingReason mentions over-leverage/margin; not best.

---

### TC-05 — Gating-reason correctness across outcomes

**Type:** artifact
**Preconditions:** Hermetic tests covering WFE-fail / margin-called / below-trades-floor / screened-only / lower-score / best.

**Steps:**
1. Run the gating-reason hermetic test.

**Expected outcome:** Each `gatingReason` string matches its `is_eligible`/best outcome (`""`/`"best"`, WFE-fail, over-leveraged, `"0 trades"`/below-floor, `"screened — not walk-forward validated"`, `"lower robust score"`).
**Pass criteria:** All gatingReason assertions pass; no mismatch between reason string and eligibility outcome.

---

### TC-06 — Best == bestIterationId (no separate best field)

**Type:** api
**Preconditions:** Hermetic promoted set.

**Steps:**
1. Load `autoRun.leaderboard`.
2. Verify no entry has a `best` field; confirm best is identified only by `iterationId === bestIterationId`.

**Expected outcome:** The entry FE would mark best equals the WFE-gated `select_best(promoted)` result; no `best` field served in any entry.
**Pass criteria:** `bestIterationId` matches `select_best(promoted)`; leaderboard entries contain only `{iterationId, stage, robustScore, eligible, gatingReason}`.

---

### TC-07 — No-regression lock (J-12/J-13/J-14 byte-identical with promote_k omitted)

**Type:** artifact
**Preconditions:** Existing J-12/J-13/J-14 hermetic tests (which set no `promote_k`).

**Steps:**
1. Run J-12/J-13/J-14 hermetic tests unchanged.
2. Compare SCREEN ordering, `wfv` pattern (`[F,F,…,T]`), marked best, and token/USD tallies vs HEAD.

**Expected outcome:** With `promote_k` omitted (default 1), SCREEN ordering, wfv pattern, marked best, and J-13 budget tallies are byte-identical to HEAD; leaderboard adds 0 tokens.
**Pass criteria:** All three suites pass unchanged; no budget/ordering/best delta.

---

### TC-08 — promote_k validation (1–3 range, 422 otherwise)

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `POST /api/auto-sessions` with `promote_k: 0` → expect 422.
2. `POST` with `promote_k: 4` → expect 422.
3. `POST` with `promote_k` omitted → expect accepted, default 1.
4. `POST` with `promote_k: 2` → accepted; verify `k = min(promote_k, n_screened)` and budget gating still halts mid-promote.

**Expected outcome:** Out-of-range → 422 with clear message; omitted → default 1; valid values accepted and clamped by `n_screened`; cost cap still halts mid-promote.
**Pass criteria:** Status codes 422 / 422 / accepted / accepted exactly; clamping and budget-gating preserved.

---

### TC-09 — No eager parse + reload survival

**Type:** api
**Preconditions:** Hermetic run completed; `read_iteration_full` monkeypatched to raise.

**Steps:**
1. With `read_iteration_full` raising, call `GET /api/sessions/{id}`.
2. Simulate a worker restart and re-read the session.

**Expected outcome:** `autoRun.leaderboard` is returned (built from in-memory metrics, persisted in the `autoRun` block of `session.json`) without parsing per-iteration `result.json`/`rating.json`; leaderboard persists across restart.
**Pass criteria:** Endpoint returns leaderboard even when full-payload parse raises; leaderboard identical after simulated restart.

---

### TC-10 — No secrets in leaderboard / gating strings

**Type:** artifact
**Preconditions:** Hermetic run with leaderboard built.

**Steps:**
1. Scan all `leaderboard[*]` fields and `gatingReason` strings for `api_key` / `sk-` material.

**Expected outcome:** No API key or secret material in any leaderboard entry or gating string.
**Pass criteria:** Zero matches for secret patterns.

---

### TC-11 — Empty/terminal-state leaderboard (no crash)

**Type:** browser
**Preconditions:** A session whose run reached a terminal state with zero completed candidates (e.g. budget exhausted before SCREEN), or no run started.

**Steps:**
1. Open the session in the UI Iterations panel.

**Expected outcome:** The leaderboard shows an empty/placeholder treatment (or is hidden when `autoRun?.leaderboard` is empty); no crash.
**Pass criteria:** Panel renders without error; placeholder/empty state shown.

---

### TC-12 — Backend + frontend build/lint green

**Type:** artifact
**Preconditions:** Code present.

**Steps:**
1. Run the hermetic backend suite.
2. Run frontend `npm run build` (`tsc && vite build`) and `npm run lint`.

**Expected outcome:** Backend suite green except the single known pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip`; FE build and lint clean.
**Pass criteria:** No new test failures; FE tsc/vite/lint exit 0.

---

### TC-13 — Browser/pixel render verification (LOAD-BEARING — must not be skipped or substituted)

**Type:** browser
**Preconditions:** FE + BE running on offset ports (FE `:3691`, BE `:8691` per `scripts/dev.sh`); a seeded/triggered open-universe run with ≥2 promoted candidates (live run uses `promote_k:2` + date range ≥ 9 months; otherwise seed a fixture session). Real foreground, uncontended Chrome-MCP tab.

**Steps:**
1. Export `CHAIN_FRONTEND_PORT=3691 CHAIN_BACKEND_PORT=8691 CHAIN_FRONTEND_URL=http://localhost:3691 CHAIN_BACKEND_HEALTH_URL=http://localhost:8691/health` and health-re-probe across the QA window.
2. Navigate to the session; open the Iterations panel (and the mobile "Iterations" tab).
3. Observe leaderboard rows, ranking, best highlight, WFE chips, gating reason on the non-best higher-return candidate.
4. Capture screenshots to `reports/qa/goal-financial_free-iter-7-evidence/`.

**Expected outcome:** Leaderboard renders: rows ranked by robust score descending; best row highlighted (consistent with existing best badge); WFE chips color-graded (emerald ≥0.5 / amber ≥0.3 / red <0.3, `—` for screen rows); the higher-return non-best candidate visibly shows its gating reason.
**Pass criteria:** Genuine browser render confirmed with screenshots in the evidence dir; ranked order, best highlight, WFE color-grading, and visible gating reason all present. Keep tab foreground (hidden-tab throttle = blank, not an app bug). **An endpoint-only substitute is NOT acceptable for J-16.**

---

### TC-14 — Endpoint ⨝ iterationHistory join yields correct ranked view

**Type:** api
**Preconditions:** Session with a populated leaderboard.

**Steps:**
1. `GET /api/sessions/{id}`.
2. For each `leaderboard` entry, join to the `iterationHistory` node by `iterationId` and read display metrics (`params.symbol/timeframe`, `totalReturn`, `sharpe`, `numTrades`, `maxDrawdown`, `walkForwardResult.wfe`).

**Expected outcome:** Each entry joins to exactly one iterationHistory node; metrics come from that node (NOT duplicated in the entry); rows ordered by `robustScore` desc give a correct ranked view; best is WFE-gated and equals `bestIterationId`. Dedup holds: a promoted family appears only as its promote node, screened-only families only as their screen node.
**Pass criteria:** Every entry joins 1:1; leaderboard entry contains no duplicated display metrics; ranking and best correct; no family listed as both screen and promote.

---

## Summary

Total test cases: 14
- API tests: 6 (TC-03, TC-04, TC-06, TC-08, TC-09, TC-14)
- Browser tests: 2 (TC-11, TC-13 — TC-13 LOAD-BEARING)
- Artifact checks: 6 (TC-01, TC-02, TC-05, TC-07, TC-10, TC-12)

**Gating notes:** TC-01 (persistence) runs FIRST and gates everything — empty `apps/` diff or missing FE component is an automatic FAIL. TC-03 is the binding J-16 overfit-gating assertion. TC-13 (browser/pixel) is LOAD-BEARING for this new render path and cannot be substituted with an endpoint-only check.
