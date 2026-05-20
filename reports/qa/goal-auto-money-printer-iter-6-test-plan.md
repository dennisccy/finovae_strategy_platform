# goal-auto-money-printer-iter-6 Functional Test Plan

**Phase:** goal-auto-money-printer-iter-6
**Date:** 2026-05-19
**Frontend Present:** yes

## Phase Goal

**J-16** — Every promoted candidate's `complete` activity entry in an open-universe
run carries an operator-readable robust-best rationale tag (`"Best — WF-validated
(WFE ≥ 0.30, ≥ 5 trades)"` or `"Not best — <specific gate that failed>"` —
e.g. `"WFE 0.00 below 0.30 gate"`, `"under min-trades floor (2 < 5)"`,
`"over-leveraged (5.0×)"`). The marked `Best` badge sits on a WF-validated
candidate; a higher-raw-return-but-WFE-failing candidate is plainly NOT best
with the reason printed inline. Rationale is purely additive via the existing
`session_store.append_activity_entries` path (no schema fork, no parallel store,
no new component); `robust_objective.py`, `_run_pinned`, SCREEN entries, and
`shared/contracts.py` are byte-unchanged. J-01–J-15 must remain green.

**Conventions:** backend `BASE=http://localhost:${CHAIN_BACKEND_PORT:-8000}`
(health `GET $BASE/api/health` → 200); frontend
`http://localhost:${CHAIN_FRONTEND_PORT:-3000}`. Backend unit:
`cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`;
full suite `cd apps/backend && .venv/bin/python -m pytest -q`. Frontend build
`cd apps/frontend && npm run build`. Baseline to preserve: post-iter-5 full
suite — the ONLY tolerated red is the pre-existing out-of-scope
`test_directions_cache.py::test_write_and_read_full_round_trip` (zero new
regressions; new tests raise the passed count; failed stays at 1).
`DEFAULT_MIN_WFE = 0.30`, `DEFAULT_MIN_TRADES = 5` (from `robust_objective.py`,
NO new constants).

## Test Cases

### TC-01 — Open-universe tiny-budget API run terminates and emits PROMOTE `complete` rationale

**Type:** api
**Preconditions:** Backend running; isolated/empty session store; `_OPEN_UNIVERSE_*` default window.

**Steps:**
1. `curl -s -o /tmp/tc01.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_iterations":4,"max_configs":4}}'`; capture `SID`.
2. Poll `GET $BASE/api/sessions/$SID` every 3s up to 300s until `autoRun.status` is terminal.
3. Enumerate the session activity feed: collect all `complete` entries from PROMOTE iterations; record each entry's `detail` field.
4. Read `autoRun.bestIterationId`; locate the `complete` entry for that iteration; record its `detail`.

**Expected outcome:** Run reaches a terminal state within budget. Every PROMOTE `complete` entry carries a non-empty `detail` rationale in plain operator language; the entry pointed at by `bestIterationId` begins with `"Best — "` (or `"Best (sole survivor) — "` if it was the only completed PROMOTE); all others begin with `"Not best — "`.
**Pass criteria:** `http_code == 200`; terminal `autoRun.status` reached; **every** PROMOTE `complete` entry has a non-empty `detail` string; the entry whose `iterId == bestIterationId` has `detail` beginning `"Best — "` or `"Best (sole survivor) — "`; if ≥ 2 PROMOTE candidates completed, exactly one entry begins `"Best — …"` / `"Best (sole survivor) — …"` and every other PROMOTE entry begins `"Not best — …"`; no `null`/`undefined`/`NaN`/`Infinity` literal substrings inside the `detail` text; no API-key-shaped string (`sk-`, `Bearer `) anywhere in the activity log.

---

### TC-02 — Terminal-state summary row emitted when ≥ 2 PROMOTE completed; NOT emitted on single-PROMOTE run

**Type:** api
**Preconditions:** Backend running; isolated store. Two scenarios are exercised: a 2-PROMOTE run (TC-01 SID can be reused if it produced ≥2 PROMOTE completes) and a forced-single-PROMOTE run.

**Steps:**
1. Re-use `SID` from TC-01 (or run a new open-universe tiny-budget request producing ≥ 2 PROMOTE completes). Read the activity feed; locate any final `_activity("auto-run", …)` row whose text starts with `"Robust-best: "`; record it.
2. Trigger a second open-universe run with a budget tight enough to yield exactly 1 PROMOTE complete (`budget.max_configs == 1` or equivalent); capture `SID_SINGLE`; poll to terminal; enumerate the feed for any `"Robust-best:"` auto-run row.

**Expected outcome:** With ≥ 2 PROMOTE completes, exactly one final `auto-run` summary row is appended just before the loop returns, naming the winning iter id, the count of other promoted candidates, and the gate set (`WFE ≥ 0.30, ≥ 5 trades, no over-leverage`). With a single PROMOTE complete, this summary row is NOT emitted.
**Pass criteria:** ≥ 2 PROMOTE: **exactly one** `auto-run` activity row matching `^Robust-best: ` exists, its iter id equals `autoRun.bestIterationId`, and the row literally cites the gate thresholds (`0.30` and `5`); single PROMOTE: **zero** `^Robust-best: ` rows in the feed.

---

### TC-03 — J-16 browser (PRIMARY observable corroboration of the renderer)

**Type:** browser
**Preconditions:** Frontend + backend running; the open-universe session(s) from TC-01 / TC-02 visible in the session list.

**Steps:**
1. Chrome MCP → open `http://localhost:${CHAIN_FRONTEND_PORT:-3000}`; open the TC-01 open-universe session from the list (no manual reload); live-poll until terminal if not already.
2. Locate the session activity feed; scroll to each PROMOTE `complete` row; confirm the rationale sub-line renders as muted text directly beneath the existing `complete` content (same emerald card, no new panel/badge/icon).
3. Confirm the iteration list's `Best` badge sits on the same iteration whose rationale begins `"Best — …"` (or `"Best (sole survivor) — …"`).
4. Save screenshot capturing **both** the rationale sub-line text and the `Best` badge co-located in the same view → `reports/qa/goal-auto-money-printer-iter-6-evidence/TC-03-best-badge-and-rationale.png`. If a `"Not best — …"` rationale is present in the same view, the same screenshot suffices; otherwise take a second screenshot of one `"Not best — …"` row → `reports/qa/goal-auto-money-printer-iter-6-evidence/TC-03-not-best-rationale.png`.

**Expected outcome:** A headless open-universe run is UI-indistinguishable in feed shape from a manual one; the rationale renders legibly (not flattened/truncated); the `Best` badge and the `"Best — …"` rationale point at the same iteration. No new component/badge/icon/panel/tab introduced.
**Pass criteria:** Every PROMOTE `complete` row visible in the feed has a non-empty muted sub-line; the `Best` badge in the iteration list sits on the entry whose rationale begins `"Best — …"`/`"Best (sole survivor) — …"`; rendered text contains no `null`/`undefined`/`NaN`/`Infinity` literals and no API-key-shaped substring; ≥1 screenshot saved under the evidence dir; no new component / badge / icon / panel / tab introduced (renders in the existing activity feed card).

---

### TC-04 — J-01–J-15 browser regression spot-check (no regression from rationale enrichment)

**Type:** browser
**Preconditions:** TC-01 / TC-02 sessions terminal; frontend running.

**Steps:**
1. **J-02:** Open a prior completed iteration from history — confirm its strategy spec, metrics, trades, equity/WF reload into the detail panel (rationale enrichment did not corrupt prior reads).
2. **J-08:** Start a fresh tiny open-universe run; without manual reload, observe live status `running → terminal` with ≥1 iteration appearing.
3. **J-12 / J-14:** On the TC-01 session, enumerate explored configs and SCREEN vs PROMOTE markers — confirm ≥2 pairwise-distinct `(symbol,timeframe)` configs and the SCREEN → PROMOTE staging still render; confirm **NO SCREEN entry** displays a rationale sub-line.
4. **J-13:** Locate `AutoRunBar`; confirm numeric tokens/USD/configs spend and the `budget-exhausted` reason render (no `NaN`/`undefined`).
5. **J-15:** If a TC-01-like session is available with `history_scope: "global"` (or default) AND a prior session exists in the store, confirm a single warm-start / planner-decision citation entry is still rendered (iter-5 invariant unchanged by the rationale wire-in).

**Expected outcome:** Rationale enrichment (additive `detail` on PROMOTE `complete`) regresses none of J-01–J-15: prior-run history browse, live tracking, staged SCREEN → PROMOTE, ≥2 distinct configs, durable spend, and iter-5 warm-start citation all still hold.
**Pass criteria:** J-02 prior iteration re-binds correctly; J-08 reaches terminal with no manual reload; J-12 shows ≥2 pairwise-distinct seed configs; J-14 SCREEN → PROMOTE staging visible and **no SCREEN entry has a rationale sub-line**; J-13 `AutoRunBar` shows spend ≤ caps + `budget-exhausted`; J-15 (if exercisable) planner-decision/warm-start citation entry still appears unchanged. Any one failing is a blocker.

---

### TC-05 — J-16 deterministic demo unit (PRIMARY deterministic proof): A overfit-tempting NOT best, B WF-validated IS best

**Type:** artifact
**Preconditions:** `apps/backend/tests/test_auto_session.py` extended with a `FakePipeline(by_cfg=...)` test on the isolated `store` fixture; two PROMOTE survivors A (overfit-tempting) and B (robust) per the spec.

**Steps:**
1. Inspect / run the new J-16 demonstration test. `by_cfg`:
   A = `{total_return: 0.50, sharpe: 4.0, num_trades: 30, max_drawdown: 0.40, wfe: 0.0, oos_sharpe: -0.5, num_windows: 2}` (overfit-tempting);
   B = `{total_return: 0.10, sharpe: 1.1, num_trades: 25, max_drawdown: 0.08, wfe: 0.7, oos_sharpe: 1.0, num_windows: 3}` (robust).

**Expected outcome:** `autoRun.bestIterationId` resolves to B's iter id; A's `complete` activity entry carries `detail == "Not best — WFE 0.00 below 0.30 gate"`; B's `complete` entry has `detail` starting with `"Best — WF-validated"`; both entries are reachable through `session_store` read-back.
**Pass criteria:** Asserts `bestIterationId == B.iter_id`; asserts A's `complete` entry has the exact `detail` string `"Not best — WFE 0.00 below 0.30 gate"`; asserts B's `complete` entry's `detail` starts with `"Best — WF-validated"`; both entries readable via the session_store activity log API; passes as written, no `skip` / `xfail`.

---

### TC-06 — Min-trades-floor rationale unit

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`.

**Steps:**
1. Inspect / run the min-trades-floor test: PROMOTE candidate with `num_trades=2`, `wfe=0.8`, `num_windows≥1`.

**Expected outcome:** Reason-resolution order picks the trades floor over the lower-robust fallback because `num_trades < DEFAULT_MIN_TRADES` is a hard gate; `wfe` passes.
**Pass criteria:** Asserts the `complete` entry's `detail == "under min-trades floor (2 < 5)"` exactly (matches the `DEFAULT_MIN_TRADES` constant); test passes as written.

---

### TC-07 — No-walk-forward rationale unit

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`.

**Steps:**
1. Inspect / run the no-WF test: PROMOTE candidate with `num_windows=0` (no walk-forward windows).

**Expected outcome:** Reason-resolution order picks "no walk-forward windows" FIRST in the chain (before WFE / trades / leverage).
**Pass criteria:** Asserts `detail == "no walk-forward windows"` exactly; test passes as written.

---

### TC-08 — Best-as-sole-survivor edge case unit (gates pass and gates fail variants)

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`; isolated `store` fixture.

**Steps:**
1. Inspect / run the sole-survivor test, two sub-scenarios:
   (a) one PROMOTE completes with `wfe=0.7, num_trades=25, num_windows=3` (gates pass) — others bt_none / gen_fail;
   (b) one PROMOTE completes with `wfe=0.0, num_trades=25, num_windows=2` (gates fail) — others bt_none / gen_fail.

**Expected outcome:** A best is always marked (the `Best` badge logic is unchanged). When the sole survivor's gates pass, its rationale matches the WF-validated shape; when its gates fail, the rationale uses the sole-survivor fallback wording naming the failing gate.
**Pass criteria:** (a) asserts `detail` starts with `"Best — WF-validated"` AND `bestIterationId` is set; (b) asserts `detail` starts with `"Best (sole survivor) — gates not met: "` AND the reason string contains the WFE-gate phrase (e.g. `"WFE 0.00 below 0.30 gate"`) AND `bestIterationId` is set. Both variants pass as written.

---

### TC-09 — Pinned path byte-unchanged: no `detail` rationale on pinned `complete`

**Type:** artifact
**Preconditions:** Existing `test_pinned_path_unchanged_by_open_universe_addition` plus one delta assertion.

**Steps:**
1. `git diff HEAD -- apps/backend/backend/auto_session.py` — inspect the diff hunks; confirm zero edits inside `_run_pinned` (`auto_session.py:1125-1234`) and its `complete` activity entry site (`auto_session.py:1192-1204`).
2. Inspect / run `test_pinned_path_unchanged_by_open_universe_addition`; confirm its `insight_calls == 3` (iter-4 carry) assertion stays green.
3. Inspect / run the new delta assertion: a pinned-path run produces **zero** PROMOTE `complete` entries with a `detail` field set by the rationale helper.

**Expected outcome:** Pinned path (J-07–J-11) is byte-unchanged at source and at behaviour; no rationale tag leaks onto pinned `complete` entries.
**Pass criteria:** `git diff HEAD -- apps/backend/backend/auto_session.py` shows **zero** edits inside `_run_pinned`; `test_pinned_path_unchanged_by_open_universe_addition` green unchanged (including `insight_calls == 3`); delta assertion asserts pinned-run `complete` entries have **no rationale-shaped `detail`** (no `"Best — "` / `"Not best — "` / `"Best (sole survivor) — "` substring); passes as written.

---

### TC-10 — SCREEN entries unchanged (J-14): no `detail` from rationale helper

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`.

**Steps:**
1. Inspect / run the SCREEN-invariance test on an open-universe run with at least one SCREEN-only iteration that does not promote.

**Expected outcome:** SCREEN `complete` / `SCREEN done` activity entries do NOT carry a rationale-shaped `detail` (rationale is open-universe PROMOTE-only).
**Pass criteria:** Asserts no SCREEN entry's `detail` matches any rationale-shaped prefix (`"Best — "`, `"Not best — "`, `"Best (sole survivor) — "`); passes as written.

---

### TC-11 — Once-per-promote / not-per-round call-count unit

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`; the J-16 scenario (TC-05) or equivalent 2-PROMOTE scenario.

**Steps:**
1. Inspect / run the call-count assertion: a 2-PROMOTE-completed run; count the number of `detail`-bearing PROMOTE `complete` entries appended across the run (use activity-log read-back and / or `FakePipeline.bt_calls`).

**Expected outcome:** Rationale row is appended exactly once per promoted iteration, not once per round per promoted iteration; the helper is invoked exactly once per `complete` append; the `auto_session.py` source uses the existing `asyncio.to_thread(session_store.append_activity_entries, …)` pattern (iter-2 lesson).
**Pass criteria:** Asserts the count of rationale-bearing PROMOTE `complete` entries `== 2` for the 2-PROMOTE scenario (NOT `4` for 2 rounds × 2 entries); source inspection confirms the new append uses `asyncio.to_thread` (no `time.sleep`, no timing-based assertion); passes as written.

---

### TC-12 — Robust-best invariant unit reused unchanged

**Type:** artifact
**Preconditions:** Existing `test_robust_objective_rejects_high_return_wfe_failing_overleveraged` (`apps/backend/tests/test_auto_session.py:307-318`).

**Steps:**
1. Run the existing test verbatim with no modifications.
2. `git diff HEAD -- apps/backend/tests/test_auto_session.py` — confirm this specific test body / signature is byte-unchanged (added tests above it are fine; this test is the unit proof of the invariant the rationale text describes).

**Expected outcome:** The structural robust-best invariant (`_GATE_FAIL_PENALTY` puts any gate-failing candidate strictly behind any gate-passing one) remains green; iter-6 does not re-implement or re-tune the gate semantics, only describes them in rationale text.
**Pass criteria:** Test passes unchanged; the diff for its body is empty (added lines elsewhere in the file are fine); passes as written.

---

### TC-13 — Error-case rationale unit: corrupt RobustInputs + non-finite robust score

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`.

**Steps:**
1. Inspect / run two error-case tests:
   (a) corrupt / all-`None` `RobustInputs` (synthesised partial result) passed into the rationale helper;
   (b) a non-finite robust score (`±inf` / `nan`) in the comparison branch ("lower robust score (X vs Y)").

**Expected outcome:** (a) helper returns a finite, JSON-safe fallback string (e.g. `"Not best — gate evaluation unavailable"`), never raises, never emits the empty string, never crashes the loop. (b) helper substitutes a finite display (e.g. `"−∞"` or an internal finite sentinel) so the activity log JSON contains **no** `nan` / `inf` literals (mirroring `_json_safe` discipline at `auto_session.py:452-468`).
**Pass criteria:** (a) asserts the helper returns a non-empty finite string and never raises; the returned `detail` string contains no `nan`/`inf`/`null` substring; (b) asserts the resulting `detail` string is JSON-safe (a `json.dumps` / `json.loads` round-trip yields the same string and the parsed object contains no `nan`/`inf` numeric literals); both passes as written.

---

### TC-14 — Anti-goal source guards (write-primitive scan, frozen modules, no new infra, no secrets, event-loop discipline)

**Type:** artifact
**Preconditions:** Dev complete; ≥1 open-universe run produced artifacts under the file store.

**Steps:**
1. `git diff HEAD -- apps/backend/backend/robust_objective.py apps/backend/shared/contracts.py apps/backend/backend/session_store.py apps/backend/backend/pipeline.py apps/backend/backend/sandbox.py apps/backend/backtest/` — confirm every one is empty (frozen module / contract / store / engine / sandbox / backtest internals byte-unchanged).
2. Iter-5 write-primitive scan over the iter-6 diff:
   `git diff HEAD -- apps/backend/backend/auto_session.py | grep -E '\.write\(|open\([^)]*[\"'"'"']w|json\.dump|\.unlink|\.rename|shutil\.|os\.remove|derive_session_tabs'` — confirm the only matches (if any) are additional `append_activity_entries` calls on the current session.
3. Inspect the diff for any new infrastructure import (Celery / Redis / DB / broker / vector-store / new top-level external dep), any new LLM call (`messages.create` / `chat.completions`), any new in-browser iterate loop in `apps/frontend/src/components/AutoRunBar.tsx`, `apps/frontend/src/components/SessionContainer.tsx`, or `apps/frontend/src/hooks/useBacktest.ts`, any change to `would_exceed` / `_SPEND_CAPS` / `max-configs` distinction (`auto_session.py:100-107`, `1381-1385`).
4. Confirm every new `_activity` append in the diff uses `asyncio.to_thread(session_store.append_activity_entries, …)` (iter-2 event-loop discipline; no synchronous append).
5. `grep -rniE "sk-|api[_-]?key|OPENAI_API_KEY|ANTHROPIC_API_KEY|Bearer " <session-store-dir-of-tc01-run>/session.json <store>/activity.jsonl` over the run from TC-01 — confirm zero matches.

**Expected outcome:** Frozen modules byte-unchanged; no new write/rename/delete path outside the existing `append_activity_entries` primitive; no new infrastructure / dep / LLM call / in-browser loop; budget gate / spend-cap distinction unchanged; new appends off-thread; no secrets persisted in the rationale text or any new activity entry.
**Pass criteria:** All git diffs in step 1 are empty; write-primitive scan in step 2 yields ONLY new `append_activity_entries` lines (no new write/open-w/json.dump/unlink/rename/shutil/os.remove/derive_session_tabs matches); no new infra/LLM/in-browser-loop additions; `would_exceed` and `_SPEND_CAPS` unchanged (no edits in the diff in the relevant line ranges); every new `_activity` append goes through `asyncio.to_thread`; the secret-grep in step 5 returns **zero** matches.

---

### TC-15 — Frontend: `entry.detail` rendered on `complete` rows; absent on non-rationale rows; safe when missing

**Type:** artifact
**Preconditions:** Dev complete; `apps/frontend/src/components/ActivityLogEntry.tsx` modified per the plan; frontend deps installed.

**Steps:**
1. Read the diff for `apps/frontend/src/components/ActivityLogEntry.tsx` — confirm it is a single additive conditional sub-line inside the `complete` branch (lines ~144-153), reusing the existing emerald card and a muted typography class (e.g. `text-xs text-emerald-700/70` or equivalent). Confirm zero new components / states / icons / badges.
2. Confirm zero edits to `apps/frontend/src/components/AutoRunBar.tsx`, `apps/frontend/src/components/SessionContainer.tsx`, `apps/frontend/src/hooks/useBacktest.ts`, and `apps/frontend/src/components/IterationCard.tsx` (the `Best` badge remains driven by `bestIterationId`).
3. `cd apps/frontend && npm run build` — record exit code.

**Expected outcome:** A single additive muted sub-line is rendered for `complete` entries when `entry.detail` is a non-empty string; non-`complete` entries are unaffected; entries without a `detail` field render byte-identically to today's single-line `complete` row; no new component / state / icon / badge; the in-browser iterate loop is NOT reintroduced; the frontend build is clean.
**Pass criteria:** `ActivityLogEntry.tsx` diff is a single conditional additive sub-line in the `complete` branch (no new component, no new state hook, no new icon, no new badge); the four files in step 2 have empty diffs; `npm run build` exit code is `0`; no TypeScript errors; the `Best` badge in `IterationCard.tsx` continues to be driven by `bestIterationId` alone.

---

### TC-16 — Backend suite green; zero new regressions

**Type:** artifact
**Preconditions:** Dev complete; backend venv installed.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v 2>&1 | tee reports/qa/goal-auto-money-printer-iter-6-test.log`.
2. `cd apps/backend && .venv/bin/python -m pytest -q 2>&1 | tee -a reports/qa/goal-auto-money-printer-iter-6-test.log` — record exact pass/fail counts.

**Expected outcome:** All new + updated `test_auto_session.py` cases pass; the full suite shows zero new regressions vs the post-iter-5 baseline.
**Pass criteria:** `test_auto_session.py` exits 0; full suite has **exactly one** failing test and it is only `test_directions_cache.py::test_write_and_read_full_round_trip` (the passed count is ≥ the post-iter-5 passed count, raised by the new tests; failed count == 1); counts recorded verbatim in the QA report.

---

### TC-17 — Closure artifacts present and non-vague

**Type:** artifact
**Preconditions:** Pipeline run for this phase.

**Steps:**
1. Verify `docs/handoffs/goal-auto-money-printer-iter-6-dev.md` exists and follows the handoff template.
2. Verify all 6 UI visibility artifacts exist for this phase (implementation-summary, user-visible-changes, ui-surface-map, ui-test-plan, ui-test-results, what-to-click) and the phase-closure gate passes.

**Expected outcome:** Dev handoff + all 6 UI artifacts exist and are concrete (exact click path to open an open-universe session and read the rationale sub-line beneath a PROMOTE `complete` entry; how to confirm the `Best` badge and the `"Best — …"` rationale point at the same iteration).
**Pass criteria:** All 7 files present and populated; no placeholder/empty sections; manual steps concrete and ordered; phase-closure gate verdict passes (`CLOSURE-PASS`).

---

## Summary

Total test cases: **17**
- API tests: **2** (TC-01, TC-02)
- Browser tests: **2** (TC-03 primary J-16, TC-04 J-01–J-15 regression)
- Artifact / unit / source-diff checks: **13** (TC-05–TC-17)

Coverage map: **J-16 (primary)** → TC-01, TC-02, TC-03, TC-05, TC-06, TC-07,
TC-08, TC-11, TC-12, TC-13; **J-01–J-15 regression** → TC-04;
**pinned path byte-unchanged (J-07–J-11)** → TC-09; **SCREEN unchanged
(J-14)** → TC-10; **robust-best invariant test reused** → TC-12;
**once-per-promote / event-loop discipline (iter-2 lesson)** → TC-11;
**error cases** → TC-13; **anti-goal source guards (frozen
`robust_objective.py` / `contracts.py` / `session_store.py` / engine /
sandbox / backtest internals, no new infra, no new writes outside
`append_activity_entries`, no new LLM call, no in-browser loop, no
secrets, write-primitive scan)** → TC-14; **frontend additive sub-line
(no new component / state / badge / icon, build clean)** → TC-15;
**suites & closure** → TC-16, TC-17.
