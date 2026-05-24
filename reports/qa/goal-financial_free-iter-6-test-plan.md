# goal-financial_free-iter-6 Functional Test Plan

**Phase:** goal-financial_free-iter-6
**Date:** 2026-05-24
**Frontend Present:** no

## Phase Goal

Re-land J-15: an open-universe automated run started with `history_scope: "global"` warm-starts from prior sessions — read-only mines the existing file store, emits one cached-planner Activity-Log entry citing a prior session's performance, and promotes the historically-strongest seed family first — while `history_scope: "this-run"` (the default / opt-out) behaves byte-for-byte as today; and the code MUST persist in the real working tree (not a discarded worktree).

## Test Cases

### TC-00 — Persistence gate (LOAD-BEARING — run FIRST, gates everything)

**Type:** artifact
**Preconditions:** Developer has completed implementation and written the dev handoff.

**Steps:**
1. Run `git diff --stat HEAD -- apps/backend/` and capture output.
2. Run `test -f apps/backend/strategy/history_planner.py`.
3. Run `grep -rl history_scope apps/backend/backend/`.
4. Read `runs/goal-financial_free-iter-6/status.json` (`changed_files`, `tests_run`).
5. Confirm `docs/handoffs/goal-financial_free-iter-6-dev.md` exists and its "Files Changed" list matches `git diff --name-only HEAD -- apps/`.

**Expected outcome:** The `apps/backend/` diff is non-empty and includes `strategy/history_planner.py` (new), `backend/auto_session.py` (modified), `backend/auto_session_routes.py` (modified), and the new J-15 test file(s); `history_planner.py` exists; grep returns matches; `status.json.changed_files` non-empty with `tests_run: true`; handoff files-changed list matches the diff.
**Pass criteria:** ALL of the above true. An empty `apps/` diff, a missing `history_planner.py`, or no `history_scope` match is an **automatic FAIL** — a green pytest cache does NOT substitute. (DoD-0)

---

### TC-01 — Invalid `history_scope` rejected with 422

**Type:** api
**Preconditions:** Backend running; `POST /api/auto-sessions` reachable.

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auto-sessions -H 'Content-Type: application/json' -d '{"history_scope":"bogus", ...valid-session-body}'`

**Expected outcome:** HTTP 422 with a clear validation message naming the allowed `{"global","this-run"}` set.
**Pass criteria:** Status code is 422; response body cites an invalid `history_scope` value. (Error cases / spec IN-SCOPE request plumbing)

---

### TC-02 — `global` warm-start emits cited planner Activity-Log entry & promotes top prior family

**Type:** api
**Preconditions:** A prior **completed** session exists in the file store with a clear top `(symbol, timeframe)` family. Hermetic fake planner injected via the `app.state.auto_pipeline` test override.

**Steps:**
1. Seed run #1 (`this-run`/default, tiny budget) to completion.
2. Start run #2 with `history_scope: "global"`; let it reach a terminal state.
3. `GET /api/sessions/{run2_id}` and inspect `activityLog` and `iterationHistory`.

**Expected outcome:** `activityLog` contains exactly ONE warm-start planner-decision entry (existing `auto-run` type) citing run #1's prior-session performance (e.g. "WARM-START — prioritizing BTC/USDT 1h (prior session …: robust score +0.42)"). The first PROMOTEd iteration's `params` `(symbol, timeframe)` equals run #1's top performer family.
**Pass criteria:** ≥1 cross-run citation entry present AND first promoted family == prior top family. (J-15 acceptance / DoD item J-15)

---

### TC-03 — `this-run` (and omitted default) opt-out honored — no cross-run citation

**Type:** api
**Preconditions:** Prior completed session exists (as TC-02).

**Steps:**
1. Start run #3 with `history_scope: "this-run"` (and a separate run with the field omitted).
2. `GET /api/sessions/{id}` → inspect `activityLog`.

**Expected outcome:** No warm-start / cross-run citation entry in either run; deterministic seed ordering and SCREEN-score promotion ranking identical to today.
**Pass criteria:** Zero planner-decision/cross-run citation entries; ordering byte-equivalent to current deterministic behavior. (Opt-out honored / DoD)

---

### TC-04 — Read-only mining: prior artifacts byte-identical before/after a `global` run

**Type:** artifact
**Preconditions:** Prior completed session artifacts present.

**Steps:**
1. Hash/snapshot the prior session's `session.json`, `meta.json`, and iteration files.
2. Execute a `global` warm-start run.
3. Re-hash the same files.

**Expected outcome:** All prior-session artifacts are byte-identical; no file mutated, created in, or deleted from prior sessions.
**Pass criteria:** Pre vs post hashes match for every prior artifact. (Anti-goal: read-only mining)

---

### TC-05 — Meta-only reads (no eager full-payload parse)

**Type:** artifact
**Preconditions:** Miner code present.

**Steps:**
1. Inspect the miner implementation / its test asserting it uses `read_iteration_meta` (and `read_session_meta` / `derive_session_tabs`), NOT `read_iteration_full`.

**Expected outcome:** Miner reads lightweight meta only; `read_iteration_full` is not called for history mining.
**Pass criteria:** No `read_iteration_full` (or full `result.json`/`rating.json` parse) in the mining path; corresponding hermetic test passes. (iter-0 lesson, DoD)

---

### TC-06 — Prompt caching marker present & planner invoked ≤ once per run

**Type:** artifact
**Preconditions:** Hermetic tests with fake/spy planner.

**Steps:**
1. Assert the planner request system prompt carries `cache_control: {"type": "ephemeral"}`.
2. Assert planner call count == 1 for a `global` run and == 0 for a `this-run` run.

**Expected outcome:** Cache marker present; planner called at most once (global), never (this-run); history not re-sent uncached each round.
**Pass criteria:** Marker assertion passes AND call-count assertions (1 / 0) pass. (Anti-goal: prompt caching; DoD)

---

### TC-07 — Planner failure is non-fatal (deterministic fallback)

**Type:** artifact
**Preconditions:** Hermetic test injects a raising/empty planner.

**Steps:**
1. Run a `global` session with the failing planner.
2. Observe ordering and terminal state.

**Expected outcome:** Run falls back to the deterministic mined-family ordering (sorted by historical score), reaches a terminal state, never crashes.
**Pass criteria:** Run terminates normally; warm-start ordering still applied via deterministic fallback. (DoD / spec planner best-effort)

---

### TC-08 — Budget compliance (J-13): planner usage accounted; pre-exhausted budget terminates before SCREEN

**Type:** artifact
**Preconditions:** Hermetic tests with the one `BudgetTracker`.

**Steps:**
1. Assert planner token usage is threaded via `_account_usage(pipeline.last_planner_usage)` into the `BudgetTracker`.
2. Start a `global` run with a pre-exhausted token/USD budget.

**Expected outcome:** Planner usage accumulates into the budget; a pre-exhausted cap terminates the run `budget-exhausted` before SCREEN starts.
**Pass criteria:** Budget reflects planner tokens AND pre-exhausted run reaches `budget-exhausted` state without starting SCREEN. (J-13, DoD)

---

### TC-09 — Bounded seed preserved (no exchange-wide fan-out)

**Type:** artifact
**Preconditions:** Hermetic test of a `global` run.

**Steps:**
1. Enumerate every `(symbol, timeframe)` the `global` run evaluates.
2. Compare against `SEED_SYMBOLS` / `SEED_TIMEFRAMES` and the count against `SEED_UNIVERSE_MAX`.

**Expected outcome:** Every evaluated config is within the bounded seed universe; count never exceeds `SEED_UNIVERSE_MAX`; warm-start only reprioritizes within the seed.
**Pass criteria:** No `(symbol, timeframe)` outside the seed; count ≤ `SEED_UNIVERSE_MAX`. (Anti-goal: bounded seed)

---

### TC-10 — Coherence: exactly one `RobustScorer` and one `BudgetTracker`

**Type:** artifact
**Preconditions:** Implementation present.

**Steps:**
1. Grep/inspect the diff and runtime path: history-strength scoring uses the single canonical `RobustScorer.score`; no second scoring or best-definition path introduced; one `BudgetTracker`.

**Expected outcome:** One `RobustScorer`, one `BudgetTracker`; best-marking remains `RobustScorer.select_best(promoted)` WFE-gated, unchanged.
**Pass criteria:** No second scorer/best-path in the diff; coherence test passes. (Coherence gate, DoD)

---

### TC-11 — No secrets in activity log or persisted artifacts

**Type:** artifact
**Preconditions:** A `global` run executed.

**Steps:**
1. Search the planner Activity-Log entry and persisted session artifacts for `api_key` / `sk-` material.

**Expected outcome:** No API keys / secret material present anywhere in the activity log or artifacts.
**Pass criteria:** Zero `api_key` / `sk-` matches. (Anti-goal: no secrets)

---

### TC-12 — `global` with empty store degrades gracefully

**Type:** api
**Preconditions:** No prior completed sessions in the store.

**Steps:**
1. Start a `global` run against an empty history store.
2. `GET /api/sessions/{id}` → inspect `activityLog` and terminal state.

**Expected outcome:** No citation entry, deterministic seed ordering, no crash, terminal state reached.
**Pass criteria:** Run completes to a terminal state; no cross-run citation; deterministic ordering. (Error cases, DoD)

---

### TC-13 — `shared/contracts.py` frozen (not in diff)

**Type:** artifact
**Preconditions:** Implementation complete.

**Steps:**
1. Run `git diff --name-only HEAD` and confirm `apps/backend/shared/contracts.py` is absent; confirm no `apps/frontend/**` changes.

**Expected outcome:** Contracts file and frontend untouched.
**Pass criteria:** Neither `shared/contracts.py` nor any `apps/frontend/**` path appears in the diff. (Out of scope / DoD)

---

### TC-14 — Suite health: full hermetic backend suite green (one known red allowed)

**Type:** artifact
**Preconditions:** All code committed to the working tree.

**Steps:**
1. Run the backend test suite (per `.claude/project-template.md`), capturing exact pass/fail counts.

**Expected outcome:** Full suite green EXCEPT the single known pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (out of scope). New J-15 tests pass.
**Pass criteria:** Only the one documented pre-existing failure is red; all J-15 and J-12/J-13/J-14 no-regression tests pass. (DoD)

---

### TC-15 — No-regression: J-12 / J-13 / J-14 hermetic tests pass UNCHANGED

**Type:** artifact
**Preconditions:** Existing J-12/J-13/J-14 tests set no `history_scope`.

**Steps:**
1. Run the J-12 (≥2 distinct bounded-seed configs), J-13 (token/USD/`max_configs` hard-enforced), and J-14 (cheap-no-WF SCREEN, k<n_screened PROMOTE, WFE-gated best from promoted only) test modules without modification.

**Expected outcome:** All pass byte-for-byte under the new `this-run` default; SCREEN ordering + promotion ranking byte-equivalent to current deterministic behavior.
**Pass criteria:** J-12/J-13/J-14 tests pass with no edits. (Required-still-passing journeys, DoD)

---

### TC-16 — Live key-gated run pair (OPTIONAL, non-blocking)

**Type:** api
**Preconditions:** LLM API key available; run only if key present.

**Steps:**
1. Seed run #1 (`this-run`/default, tiny budget) over a date range **≥ 9 months** (≥ `IS_months + OOS_months` at 6/3 defaults).
2. Run #2 (`history_scope: "global"`), same ≥9-month range.
3. Run #3 (`history_scope: "this-run"`).
4. Inspect each run's `activityLog` and first promoted family.

**Expected outcome:** Run #2 cites run #1's performance and its first promoted family matches run #1's best; run #3 shows no citation; PROMOTE walk-forward forms ≥1 window (promote→best not vacuous).
**Pass criteria:** Citation + family match for run #2, no citation for run #3, WF window count ≥1. **Skip (not FAIL) if no API key.** (Live test; iter-4 ≥9-month lesson)

---

## Summary

Total test cases: 17
- API tests: 5 (TC-01, TC-02, TC-03, TC-12, TC-16)
- Artifact checks: 12 (TC-00, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09, TC-10, TC-11, TC-13, TC-14, TC-15)
- Browser tests: 0 (Frontend Present: no — J-15 reuses the existing `auto-run` render path; verified at the endpoint layer. A single best-effort browser pixel capture is explicitly NON-BLOCKING and must NOT gate J-15.)

**Gating note:** TC-00 (persistence gate) is load-bearing and runs FIRST — an empty `apps/` diff is an automatic FAIL regardless of pytest results. TC-16 is optional/non-blocking (key-gated).
