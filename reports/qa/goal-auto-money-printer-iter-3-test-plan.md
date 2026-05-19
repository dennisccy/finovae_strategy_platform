# goal-auto-money-printer-iter-3 Functional Test Plan

**Phase:** goal-auto-money-printer-iter-3
**Date:** 2026-05-19
**Frontend Present:** yes

## Phase Goal

Optimizer Foundation — the indivisible slice **J-12** (one API call with only an
objective + budget, no symbol/timeframe, explores ≥2 distinct configs from a
bounded seed universe) **+ J-13** (an immutable hard cost tracker enforcing
AI-token/USD/max-configs/wall-clock caps fixed at run start), with the recorded
spend made visible in the existing `AutoRunBar` and the robust objective
selecting best — no regression to J-01–J-11.

**Conventions:** backend `BASE=http://localhost:${CHAIN_BACKEND_PORT:-8000}`
(health `GET $BASE/api/health` → 200), frontend
`http://localhost:${CHAIN_FRONTEND_PORT:-3000}`. Backend unit:
`cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`
(+ any new `tests/test_cost_tracker.py` / `tests/test_model_pricing.py`); full
suite `cd apps/backend && .venv/bin/python -m pytest -q`. Frontend build
`cd apps/frontend && npm run build`. **All** J-12/J-13 cases use a **tiny
budget** (`max_iterations:2`, `max_configs:2`, omitted dates → fixed short
window, cheapest default model, lenient targets) per the goal's J-07–J-16
budget mandate. Baseline to preserve: full suite **150 passed / 1 failed** —
the ONLY tolerated failure is the pre-existing out-of-scope
`test_directions_cache.py::test_write_and_read_full_round_trip`.

## Test Cases

### TC-01 — Open-universe POST accepted (no symbol/timeframe) → 200 + appears in session list

**Type:** api
**Preconditions:** Backend running; `OPENAI_API_KEY` set.

**Steps:**
1. `curl -s -o /tmp/tc01.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'` (NO `symbol`/`timeframe`/`start_date`/`end_date`).
2. `curl -s "$BASE/api/sessions"` and look for the returned `sessionId`.

**Expected outcome:** The relaxed gate accepts the well-formed open-universe request (was hard-422 before this iteration); a session is created and listed.
**Pass criteria:** `http_code == 200`; `.sessionId` non-empty; `.status ∈ {running,queued}`; same id present in `GET /api/sessions` with no browser interaction.

---

### TC-02 — Open-universe run explores ≥2 distinct configs, terminal within budget, robust best marked (J-12 core)

**Type:** api
**Preconditions:** TC-01 session id `SID`.

**Steps:**
1. Poll `curl -s "$BASE/api/sessions/$SID"` every 3s up to 180s until `autoRun.status` is terminal.
2. Enumerate the session iterations; record each iteration's `(symbol,timeframe)` and the activity-log entries naming each explored config.
3. Record `bestIterationId` and the terminal `autoRun.status`/`stopReason`.

**Expected outcome:** ≥2 iterations with **distinct `(symbol,timeframe)`** (differing symbol and/or timeframe), drawn only from the bounded seed universe; run reaches a terminal state within budget; best set by the robust objective.
**Pass criteria:** ≥2 iterations exist and ≥2 are pairwise-distinct on `(symbol,timeframe)`; the activity log records each config explored; terminal `autoRun.status` reached (not still running) and within the supplied budget; `bestIterationId` non-null and equals the `select_best`/`robust_score` winner over all completed configs (not the raw-return max).

---

### TC-03 — Tiny token/USD budget → `budget-exhausted`, spend ≤ cap, no post-cap iteration (J-13 core)

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `curl -s -o /tmp/tc03.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_ai_tokens":1,"max_usd":0.0001,"max_configs":2,"max_iterations":2}}'`; capture `SID`.
2. Poll `GET $BASE/api/sessions/$SID` to terminal; record `autoRun.stopReason`, the recorded spend (tokens/USD/configs), and the iteration count at first-cap-observed vs. final.

**Expected outcome:** Run halts at the hard cap with `stopReason="budget-exhausted"`; recorded spend is bounded; no config/iteration starts after a cap is reached.
**Pass criteria:** `http_code == 200`; terminal `autoRun.stopReason == "budget-exhausted"`; recorded `tokens ≤ max_ai_tokens` and `usd ≤ max_usd` **within one in-flight-call tolerance** (one call may marginally exceed; no NEW round/config past the cap); final iteration count == count at first cap observation (zero post-cap iterations); spend object present in the `autoRun` block.

---

### TC-04 — Unsupported objective → clean 422 (single-robust-scalar Non-Goal)

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `curl -s -o /tmp/tc04.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"x","objective":"sharpe","budget":{"max_iterations":1}}'`.

**Expected outcome:** `objective` other than `"robust"` is rejected clearly.
**Pass criteria:** `http_code == 422`; JSON detail names the unsupported objective; **no** 500; no session created (`GET /api/sessions` count unchanged).

---

### TC-05 — Pinned path unchanged (J-07 regression) + malformed pinned still 422 not 500

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. Valid pinned: `POST $BASE/api/auto-sessions` with `{"natural_language":"Buy when RSI<30, sell when RSI>70","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-02-01","initial_capital":10000,"model":"gpt-5.4-mini","budget":{"max_iterations":2}}`.
2. Malformed pinned: same as (1) but `symbol` omitted (still pinned-shaped: `timeframe` present, no `objective`).
3. Malformed dates: valid pinned but `start_date":"01-2024"`.

**Expected outcome:** Pinned validation/behaviour is byte-identical to pre-iteration (J-07–J-11 unaffected); pinned-with-missing-dimension and bad dates still 422.
**Pass criteria:** (1) `http_code == 200`, session runs the single pinned config exactly as before; (2) and (3) `http_code == 422` with a clear detail; **never** 500; the open-universe path is taken only when symbol AND timeframe are both omitted with a valid `objective`.

---

### TC-06 — Malformed open-universe budget/dates → 422 (never 500)

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `POST` open-universe with a non-numeric budget cap: `{"natural_language":"x","objective":"robust","budget":{"max_ai_tokens":"lots"}}`.
2. `POST` open-universe with malformed explicit dates: `{"natural_language":"x","objective":"robust","start_date":"not-a-date","end_date":"2024","budget":{"max_iterations":1}}`.

**Expected outcome:** Malformed open-universe requests are rejected cleanly.
**Pass criteria:** Both return `http_code == 422` with a well-formed JSON detail; **no** 500/traceback; no session created.

---

### TC-07 — `history_scope` accepted & persisted, no cross-run learning (J-15 boundary)

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `POST` open-universe with `"history_scope":"this-run"` plus tiny budget; capture `SID`.
2. `GET $BASE/api/sessions/$SID`; inspect persisted session meta for the `history_scope` value and the activity log for any cross-session/prior-session citation.

**Expected outcome:** `history_scope` is accepted and persisted; the controller is a deterministic bounded enumerator that performs **no** cross-run learning and adds **no** uncached per-round LLM history/planner context this iteration.
**Pass criteria:** `http_code == 200`; the supplied `history_scope` is readable in the persisted session meta; activity log shows **no** prior-session/leaderboard warm-start citation; no mutation/deletion of any other session's artifacts.

---

### TC-08 — `GET /api/sessions/{id}` stays lazy for open-universe sessions (anti-goal regression)

**Type:** api
**Preconditions:** An open-universe session with ≥1 completed iteration (`SID` from TC-02).

**Steps:**
1. `curl -s "$BASE/api/sessions/$SID"` and inspect the payload shape.

**Expected outcome:** The list/open path returns metadata only — it does NOT eagerly inline full per-iteration `result.json`/`rating.json`.
**Pass criteria:** No full `equity_curve`/`trades`/full rating arrays inlined per iteration; iterations are metadata-only; heavy detail only via the dedicated per-iteration endpoint (byte-unchanged lazy behaviour).

---

### TC-09 — Durable spend survives a real backend restart + reload (J-13 durability)

**Type:** api
**Preconditions:** A terminal `budget-exhausted` open-universe session `SID` (reuse TC-03).

**Steps:**
1. Record the full `autoRun` block (`status`, `stopReason`, recorded spend tokens/USD/configs, `bestIterationId`, iteration count).
2. Restart the backend process (stop + re-start uvicorn against the same `BACKTEST_STORE_DIR`).
3. `curl -s "$BASE/api/sessions/$SID"` and re-read the `autoRun` block.

**Expected outcome:** The recorded spend and terminal state are written to the durable file store via the existing `_update_autorun`, not in-process memory — they survive a restart.
**Pass criteria:** After restart every recorded field (`stopReason`, tokens, USD, configs, `bestIterationId`, iteration count) is byte-identical to the pre-restart values; the store dir is not a volatile `/tmp` path.

---

### TC-10 — J-12 browser: ≥2 distinct configs visible as iterations, terminal within budget, robust BestBadge

**Type:** browser
**Preconditions:** Frontend + backend running; an open-universe session started as in TC-01 (tiny budget).

**Steps:**
1. Chrome MCP → open `http://localhost:${CHAIN_FRONTEND_PORT:-3000}`; open the created "Auto: …" session from the session list (no manual reload).
2. Inspect the iteration tree / activity log: count distinct explored configs (symbol/timeframe).
3. Wait (live poll, no manual reload) until the run reaches terminal; locate the `BestBadge`.

**Expected outcome:** The headless open-universe run is UI-indistinguishable from a manual session; ≥2 distinct configs render as iterations; terminal within budget; robust best badged. Screenshot saved under `reports/qa/goal-auto-money-printer-iter-3-evidence/`.
**Pass criteria:** ≥2 iterations with visibly distinct symbol and/or timeframe appear in the existing iteration tree/activity log; status transitions to terminal without a manual reload; exactly one iteration carries the existing `BestBadge` and it is the robust winner (matches TC-02 `bestIterationId`).

---

### TC-11 — J-13 browser: AutoRunBar shows recorded spend + legible `budget-exhausted`

**Type:** browser
**Preconditions:** The terminal `budget-exhausted` session from TC-03; frontend running.

**Steps:**
1. Chrome MCP → open that session; locate the existing `AutoRunBar` strip.
2. Read the spend readout (AI-tokens / USD / configs-run) and the terminal-reason text.

**Expected outcome:** The additive spend readout surfaces the recorded tokens/USD/configs from the polled durable `autoRun` block; `budget-exhausted` is clearly legible and visually distinct from `criteria-met`/`stopped`.
**Pass criteria:** `AutoRunBar` displays numeric tokens, USD, and configs-run matching the persisted `autoRun` spend (TC-03 values); the terminal reason reads `budget-exhausted` (distinct styling); no NaN/`undefined`; no new page/panel introduced. Screenshot saved under the evidence dir.

---

### TC-12 — J-08 regression browser: fresh still-running open-universe session is not a stale terminal

**Type:** browser
**Preconditions:** A freshly started, still-running open-universe session (larger budget so it stays running); ≥1 other session present; frontend running.

**Steps:**
1. Start the running session; in the UI rapidly switch between sessions and back to it (do not reload the page).
2. Observe the session-list spinner and the `AutoRunBar` status during/after the switch; wait one poll cycle.

**Expected outcome:** `AutoRunBar` authoritatively re-derives per-session `autoRun` on mount/switch — it shows "running", never a stale prior terminal; the live poll self-heals without a manual reload (iter-2 `try/finally` re-arm intact).
**Pass criteria:** After the rapid switch the `AutoRunBar` shows "running" (not a stale `budget-exhausted`/`stopped`) and the session-list spinner agrees; the poll continues to update with no manual reload.

---

### TC-13 — J-02 regression browser: prior-run RIGHT analysis panel re-binds

**Type:** browser
**Preconditions:** A session with ≥2 completed iterations (open-universe TC-02 session or any prior run); frontend running.

**Steps:**
1. Chrome MCP → open the session; select a prior completed iteration/run from history.
2. Inspect the RIGHT panel: trades table, equity curve, and walk-forward view.

**Expected outcome:** Selecting a prior run re-binds the RIGHT analysis panel (trades/equity/WF), not only the left summary — unchanged by the additive `AutoRunBar` work.
**Pass criteria:** The selected prior run's trades table, equity curve, and WF view all reload into the RIGHT panel and match that run (J-02 heavy-detail merge precedence byte-unchanged).

---

### TC-14 — Legacy/pinned sessions render gracefully when spend fields absent

**Type:** browser
**Preconditions:** A pinned (J-07-style) or pre-existing session with no cost-tracker spend fields; frontend running.

**Steps:**
1. Open the legacy/pinned session; inspect the `AutoRunBar`.

**Expected outcome:** Absent spend fields degrade gracefully — the bar renders unchanged for old/pinned sessions.
**Pass criteria:** No `NaN`/`undefined`/blank spend artifacts; the `AutoRunBar` for legacy sessions is visually unchanged from before this iteration (additive-only, no regression to existing rendering).

---

### TC-15 — Immutable cost tracker unit: monotonic, caps fixed at construction, per-cap stop, safe defaults

**Type:** artifact
**Preconditions:** Dev complete; `tests/test_cost_tracker.py` (or extended `test_auto_session.py`).

**Steps:**
1. Inspect/run the tracker unit tests.

**Expected outcome:** Accumulated spend is monotonic/append-only; caps are fixed at construction (attempting to lower OR raise mid-run is a no-op); `would_exceed`/stop fires **independently** on the **token**, **USD**, **max-configs**, and **wall-clock** caps, plus the `max_iterations`/`HARD_MAX_ITERATIONS` clamp; zero/negative caps fall back to a safe default that is still hard-bounded (never unbounded).
**Pass criteria:** Tests assert exact values (not "ran without error"): monotonic accumulation; a mid-run cap-mutation attempt leaves the effective cap unchanged; a dedicated test per cap (token / USD / max-configs / wall-clock) shows stop firing for that cap alone; zero/negative cap → documented safe default and a bounded terminal; all pass, none skipped/xfail.

---

### TC-16 — Real-usage-fed guard unit (iter-2 false-guard generalization)

**Type:** artifact
**Preconditions:** `test_auto_session.py` extended with a `FakePipeline` carrying deterministic fake SDK `.usage`.

**Steps:**
1. Inspect the budget test that drives the production usage-capture path (`compiler.py`/`insights_generator.py`/`script_generator.py` → `pipeline.py` non-frozen returns/accumulator → auto-session loop).

**Expected outcome:** The tracker accumulates the **token counts actually returned by the fake SDK `.usage`** flowing the real capture path — not an estimate, hardcoded constant, or number that passes by construction.
**Pass criteria:** The test asserts the tracker total equals the exact summed fake-usage token counts, AND a documented mutation (bypassing/hardcoding capture) makes the test FAIL; OpenAI (`prompt_tokens`/`completion_tokens`) and Anthropic (`input_tokens`/`output_tokens`, incl. cache fields) shapes both exercised; passes as written.

---

### TC-17 — Deterministic non-blocking guard unit for the multi-config run

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`.

**Steps:**
1. Inspect the regression test asserting every backtest in a ≥2-config open-universe run executed in a child process via the existing `_subprocess_backtest_executor` seam.

**Expected outcome:** Each multi-config backtest ran with `child_pid != os.getpid()`; the guard is **deterministic** (child-pid assertion), **NOT** a timing bound; it still fails if forced in-process.
**Pass criteria:** Test asserts `child_pid != os.getpid()` for each config's backtest; contains **no** `time.sleep`/elapsed-time threshold as the guard; a forced-in-process variant makes it FAIL; passes as written.

---

### TC-18 — Robust best across configs unit (not raw return)

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`.

**Steps:**
1. Inspect the test with ≥2 completed configs where one has a higher raw return but fails WFE / is over-leveraged and another satisfies the robust objective.

**Expected outcome:** `bestIterationId` = the robust-objective winner over the combined `RobustInputs`; the higher-raw-return WFE-failing/over-leveraged config is NOT best; selection reuses existing `select_best` (not re-implemented).
**Pass criteria:** Test asserts the exact expected `bestIterationId` (robust winner) AND explicitly asserts the raw-return candidate is NOT best; passes.

---

### TC-19 — Durable spend survives simulated restart + bounded seed universe + unknown-model safety (unit)

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py` / pricing tests.

**Steps:**
1. Inspect the test that, on cap, asserts `stopReason="budget-exhausted"` persisted to the durable `autoRun` via `_update_autorun`, then re-reads meta (simulated restart) and re-asserts the spend.
2. Inspect the seed-universe constant assertion and the price-table unknown-model lookup test.

**Expected outcome:** Durable spend survives a simulated restart (re-read meta); the seed universe is a small hard-coded constant (≤ ~8 entries, NOT the full 26×6 grid, NOT env-driven, NOT a live enumeration); an unknown model id in the price table keeps the token cap binding (no crash).
**Pass criteria:** Post-simulated-restart meta still carries the spend + `budget-exhausted` + no post-cap config; a test asserts the seed-universe constant size/shape; unknown-model pricing lookup returns a safe value (token cap still enforced, no exception); all pass.

---

### TC-20 — Backend suites green + frontend build clean (zero new regressions)

**Type:** artifact
**Preconditions:** Dev complete; backend venv + frontend deps installed.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v` (+ new `tests/test_cost_tracker.py`/`tests/test_model_pricing.py` if present) `2>&1 | tee reports/qa/goal-auto-money-printer-iter-3-test.log`.
2. `cd apps/backend && .venv/bin/python -m pytest -q` — record exact counts.
3. `cd apps/frontend && npm run build` — record exit code.

**Expected outcome:** Targeted suites pass (extended, not duplicated); the full suite shows zero new regressions; frontend compiles.
**Pass criteria:** `test_auto_session.py` (+ new tracker/pricing tests) exit 0, all pass; full suite **exactly 150 passed / 1 failed**, the single failure being only `test_directions_cache.py::test_write_and_read_full_round_trip` (counts recorded verbatim); `npm run build` EXIT 0.

---

### TC-21 — Anti-goal source guards (contracts/sandbox/engine, no new infra, no secrets)

**Type:** artifact
**Preconditions:** Dev complete; ≥1 open-universe run produced artifacts under the file store.

**Steps:**
1. `git diff --stat` / `git diff` — confirm `apps/backend/shared/contracts.py`, the RestrictedPython sandbox, the deterministic next-bar engine, backtest/fills/metrics internals, and `BacktestPipeline` orchestration are byte-unchanged (usage *capture* via non-frozen pipeline returns is allowed; engine bypass is not).
2. Inspect the diff for any new datastore/queue/scheduler/broker/vector-store import or any session-store schema fork (must reuse `_update_autorun`/`write_iteration`/`append_activity_entries`).
3. `grep -rni "sk-\|api[_-]\?key\|OPENAI_API_KEY\|ANTHROPIC_API_KEY\|Bearer " <session-store-dir>` over the run's `session.json`/activity/insights artifacts.

**Expected outcome:** Frozen contract + sandbox + engine + backtest internals unchanged; no new external infrastructure; no schema fork; no secrets persisted.
**Pass criteria:** Zero diff in `contracts.py`/sandbox/engine/backtest-internals/`BacktestPipeline` orchestration; no Celery/Redis/DB/broker/vector-store added; spend reuses the existing durable `autoRun` mechanism only (no parallel store); secret grep returns zero matches in any artifact or activity log.

---

### TC-22 — Closure artifacts present and non-vague

**Type:** artifact
**Preconditions:** Pipeline run for this phase.

**Steps:**
1. Verify `docs/handoffs/goal-auto-money-printer-iter-3-dev.md` exists and follows the handoff template.
2. Verify all 6 UI visibility artifacts exist for this phase (implementation-summary, user-visible-changes, ui-surface-map, ui-test-plan, ui-test-results, what-to-click) and the phase-closure gate passes.

**Expected outcome:** Dev handoff + all 6 UI artifacts exist and are concrete (exact click paths for the `AutoRunBar` spend readout / open-universe session open).
**Pass criteria:** All 7 files present and populated; no placeholder/empty sections; manual steps are concrete and ordered; phase-closure gate verdict passes.

---

## Summary

Total test cases: **22**
- API tests: **9** (TC-01–TC-09)
- Browser tests: **5** (TC-10–TC-14)
- Artifact / unit / source-diff checks: **8** (TC-15–TC-22)

Coverage map: J-12 → TC-01, TC-02, TC-10; J-13 → TC-03, TC-09, TC-11, TC-15,
TC-16, TC-19; regression J-07–J-11 → TC-05, TC-08; J-08 → TC-12; J-02 → TC-13;
graceful legacy state → TC-14; error cases → TC-04, TC-06, TC-07, TC-19;
anti-goal/lesson guards (subprocess seam, robust-best, real-usage, immutable
tracker, contracts/sandbox/engine, secrets, no new infra) → TC-15–TC-19, TC-21;
suites & closure → TC-20, TC-22.
