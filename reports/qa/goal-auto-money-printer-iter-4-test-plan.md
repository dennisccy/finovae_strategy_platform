# goal-auto-money-printer-iter-4 Functional Test Plan

**Phase:** goal-auto-money-printer-iter-4
**Date:** 2026-05-19
**Frontend Present:** yes

## Phase Goal

Staged SCREEN→PROMOTE cheap-first routing for the open-universe automated run
(**J-14**): several seed configs are screened cheaply (`wfv_enabled=False`,
cheapest catalog model, no insights) and only the top-k (k < number screened)
are PROMOTEd to the full pipeline (`wfv_enabled=True` + `req.model` + insights,
reusing the screened strategy by code hash + warm Parquet cache) — visibly
staged in the existing session activity feed — while the carried **B1** fix
(skip insights only on a spend cap `{ai-tokens,usd,wall-clock}`, **never** on
`max-configs`) ships, and J-01–J-13 + every anti-goal still hold.

**Conventions:** backend `BASE=http://localhost:${CHAIN_BACKEND_PORT:-8000}`
(health `GET $BASE/api/health` → 200), frontend
`http://localhost:${CHAIN_FRONTEND_PORT:-3000}`. Backend unit:
`cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`;
full suite `cd apps/backend && .venv/bin/python -m pytest -q`. Frontend build
`cd apps/frontend && npm run build`. **Every** J-14 case uses a **tiny budget**
(no `symbol`/`timeframe`, `objective:"robust"`, short/omitted date window,
cheap model, k small, lenient/absent targets) so the run ends `budget-exhausted`
fast — SCREEN is cheap by construction (no WF, cheapest model, no insights,
warm shared Parquet cache), so screening several seeds while promoting a small
top-k is consistent with the goal's fast-and-cheap mandate. Baseline to
preserve: post-iter-3 full suite **183 passed / 1 failed**; the ONLY tolerated
failure remains the pre-existing out-of-scope
`test_directions_cache.py::test_write_and_read_full_round_trip` — **zero new
regressions** (new tests raise the passed count; the failed count stays 1).

## Test Cases

### TC-01 — Open-universe POST accepted (no symbol/timeframe) → 200 + listed

**Type:** api
**Preconditions:** Backend running; `OPENAI_API_KEY` set.

**Steps:**
1. `curl -s -o /tmp/tc01.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'` (NO `symbol`/`timeframe`/`start_date`/`end_date`).
2. `curl -s "$BASE/api/sessions"` and look for the returned `sessionId`.

**Expected outcome:** The open-universe request is accepted and a session is created and listed (J-14 trigger path unchanged from J-12).
**Pass criteria:** `http_code == 200`; `.sessionId` non-empty; `.status ∈ {running,queued}`; same id present in `GET /api/sessions` with no browser interaction.

---

### TC-02 — Staged SCREEN→PROMOTE in the activity feed (J-14 core, API)

**Type:** api
**Preconditions:** TC-01 session id `SID`.

**Steps:**
1. Poll `curl -s "$BASE/api/sessions/$SID"` every 3s up to 180s until `autoRun.status` is terminal.
2. Enumerate the session activity entries; count entries whose stage marker is `SCREEN` vs `PROMOTE`; record each SCREEN entry's `(symbol,timeframe)` + screen metric and each PROMOTE entry's `(symbol,timeframe)`.
3. For every iteration, record whether walk-forward result data and the model used (`req.model` vs the cheapest catalog model) are present.

**Expected outcome:** The run screens several seed configs cheaply then promotes only a small top-k; expensive walk-forward + the stronger model touch promoted configs only.
**Pass criteria:** ≥3 distinct `SCREEN` activity entries each carrying the cheap screen metric; exactly `k` `PROMOTE` entries with **k < number screened** and k small; every promoted iteration has walk-forward result data and used `req.model`; **no** screened-only iteration has walk-forward data or used `req.model`; terminal `autoRun.status` reached within the supplied tiny budget.

---

### TC-03 — Final best is a PROMOTED id by the robust objective (J-09/J-16 invariant under staging)

**Type:** api
**Preconditions:** TC-02 terminal session `SID` (or a fresh terminal open-universe run).

**Steps:**
1. `curl -s "$BASE/api/sessions/$SID"`; record `bestIterationId`, each iteration's stage (screened-only vs promoted), raw return, and WFE/robust score.
2. Identify the highest raw-return iteration and confirm whether it is screened-only or WFE-failing.

**Expected outcome:** Best is selected by `select_best`/`robust_score` over the **promoted** (walk-forward-bearing) iterations only; the cheap screen proxy never leaks into best-selection.
**Pass criteria:** `bestIterationId` is non-null and is a **promoted** iteration's id; it equals the `robust_score` winner over promoted iterations; a higher-raw-return screened-only candidate (no WF) and any WFE-failing/over-leveraged candidate are explicitly **not** `bestIterationId`.

---

### TC-04 — Hard budget under staging → `budget-exhausted`, no post-cap config (J-13)

**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `curl -s -o /tmp/tc04.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_ai_tokens":1,"max_usd":0.0001,"max_configs":2,"max_iterations":2}}'`; capture `SID`.
2. Poll `GET $BASE/api/sessions/$SID` to terminal; record `autoRun.stopReason`, recorded spend (tokens/USD/configs), and the count of SCREEN+PROMOTE activity entries at first-cap-observed vs final.

**Expected outcome:** The round-top `would_exceed()` check gates the start of every SCREEN **and** every PROMOTE candidate; on a hard cap the run reaches `budget-exhausted` with no further screen/promote config appended; SCREEN+PROMOTE LLM calls feed the same real-token `record_usage` path.
**Pass criteria:** `http_code == 200`; terminal `autoRun.stopReason == "budget-exhausted"`; recorded `tokens ≤ max_ai_tokens` and `usd ≤ max_usd` within one in-flight-call tolerance; **zero** SCREEN or PROMOTE entries appended after the cap was first observed; spend object present and durable in the `autoRun` block.

---

### TC-05 — Error/validation cases — 422 not 500; pinned path takes no SCREEN/PROMOTE

**Type:** api
**Preconditions:** Backend running; baseline `GET /api/sessions` count recorded.

**Steps:**
1. Partial pin: `POST $BASE/api/auto-sessions` with `timeframe":"1h"` but **no** `symbol` (no `objective`).
2. Bad objective: `POST` open-universe with `"objective":"sharpe"`.
3. Valid pinned: `POST` with `{"natural_language":"Buy when RSI<30, sell when RSI>70","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-02-01","initial_capital":10000,"model":"gpt-5.4-mini","budget":{"max_iterations":2}}`; capture `SID`; poll to terminal and inspect its activity feed.

**Expected outcome:** Malformed requests are rejected cleanly; the pinned path is byte-unchanged behaviourally (one config/iteration, full pipeline every iteration, prompt-refinement chain) with **no** SCREEN/PROMOTE staging.
**Pass criteria:** (1) and (2) return `http_code == 422` with a clear JSON detail and **no** 500/traceback; no session created (`/api/sessions` count unchanged for the 422s); (3) `http_code == 200`, exactly one config per iteration, **zero** `SCREEN`/`PROMOTE` activity entries, full pipeline (WF + insights) every iteration.

---

### TC-06 — SCREEN-stage failure does not abort the loop

**Type:** api
**Preconditions:** Backend running. (May reuse the TC-02 run if a generate/backtest failure naturally occurred and was recorded; otherwise a fresh tiny open-universe run.)

**Steps:**
1. Trigger a tiny open-universe run; poll to terminal.
2. Inspect the activity feed for any recorded SCREEN-stage generate-validation or backtest failure entry, and confirm subsequent SCREEN/PROMOTE entries and a terminal state still follow.

**Expected outcome:** A SCREEN-stage generate-validation failure or backtest failure is **recorded** and the loop continues to a terminal state — a single screened config failing must not abort the run.
**Pass criteria:** If a SCREEN failure occurs it appears as a recorded activity entry (no unhandled 500/crash); the run still reaches a terminal `autoRun.status` (`budget-exhausted`/`criteria-met`) with later entries appended after the failure; if no failure naturally occurs, note "not exercised — no SCREEN failure in this run" (non-blocking, covered by unit TC-13 resilience).

---

### TC-07 — J-14 browser (primary): staged feed visible — ≥3 SCREEN, k<screened PROMOTE

**Type:** browser
**Preconditions:** Frontend + backend running; an open-universe session started as in TC-01 (tiny budget).

**Steps:**
1. Chrome MCP → open `http://localhost:${CHAIN_FRONTEND_PORT:-3000}`; open the created "Auto: …" session from the session list (no manual reload).
2. Live-poll (no manual reload) until the run reaches a terminal state.
3. Read the session activity feed: count `SCREEN` vs `PROMOTE` entries; open a promoted iteration and a screened-only iteration and inspect for walk-forward data + which model was used; locate the `BestBadge`.
4. Save a screenshot of the staged activity feed to `reports/qa/goal-auto-money-printer-iter-4-evidence/TC-07-staged-screen-promote.png`.

**Expected outcome:** The headless run is UI-indistinguishable from a manual one; the existing activity feed legibly shows several SCREEN candidates then a small PROMOTE set; expensive WF + stronger model only on promoted; an operator can distinguish the two stages without a new component.
**Pass criteria:** ≥3 visibly distinct `SCREEN` entries (stage prefix readable, not flattened/truncated); exactly k `PROMOTE` entries with **k < screened** and k small; every promoted iteration shows walk-forward results and the stronger model, screened-only iterations show neither; terminal reached without a manual reload; exactly one `BestBadge` and it is on a promoted iteration (matches TC-03 `bestIterationId`); screenshot saved under the evidence dir.

---

### TC-08 — J-12 regression browser: open-universe still ≥2 distinct configs, UI-indistinguishable

**Type:** browser
**Preconditions:** TC-07 session (or a fresh tiny open-universe run); frontend running.

**Steps:**
1. Chrome MCP → open the session; enumerate the explored configs across SCREEN+PROMOTE entries / iteration tree.
2. Confirm the session renders through the existing session view (no new surface/page).

**Expected outcome:** Open-universe still explores ≥2 distinct seed configs and remains UI-indistinguishable from a manual session (J-12 preserved under staging).
**Pass criteria:** ≥2 pairwise-distinct `(symbol,timeframe)` configs visible across screened+promoted entries, drawn from the bounded seed universe; rendered in the existing iteration tree/activity feed with no new page/panel.

---

### TC-09 — J-13 regression browser: AutoRunBar spend + `budget-exhausted` under staging

**Type:** browser
**Preconditions:** The terminal `budget-exhausted` session from TC-04; frontend running.

**Steps:**
1. Chrome MCP → open that session; locate the existing `AutoRunBar` strip.
2. Read the spend readout (AI-tokens / USD / configs-run) and the terminal-reason text; save screenshot to `reports/qa/goal-auto-money-printer-iter-4-evidence/TC-09-autorunbar-budget-exhausted.png`.

**Expected outcome:** The recorded staged spend (SCREEN + PROMOTE LLM usage) surfaces in the existing `AutoRunBar`; `budget-exhausted` is legible and visually distinct.
**Pass criteria:** `AutoRunBar` shows numeric tokens, USD, and configs-run matching the persisted `autoRun` spend (TC-04 values); terminal reason reads `budget-exhausted` (distinct styling); no `NaN`/`undefined`; no new page/panel; screenshot saved.

---

### TC-10 — J-08 regression browser: still-running session is not a stale terminal under switching

**Type:** browser
**Preconditions:** A freshly started, still-running open-universe session (larger budget so it stays running); ≥1 other session present; frontend running.

**Steps:**
1. Start the running session; in the UI rapidly switch between sessions and back to it (do **not** reload the page).
2. Observe the session-list spinner and the `AutoRunBar` status during/after the switch; wait one poll cycle.

**Expected outcome:** `AutoRunBar` authoritatively re-derives per-session `autoRun` on mount/switch — it shows "running", never a stale prior terminal; the iter-2 live-poll `try/finally` re-arm is intact (byte-unchanged).
**Pass criteria:** After the rapid switch the `AutoRunBar` shows "running" (not a stale `budget-exhausted`/`stopped`); the session-list spinner agrees; the poll keeps updating with no manual reload.

---

### TC-11 — J-02 regression browser: prior-run RIGHT analysis panel re-binds

**Type:** browser
**Preconditions:** A session with ≥2 completed iterations (a promoted iteration from TC-07 or any prior run); frontend running.

**Steps:**
1. Chrome MCP → open the session; select a prior completed iteration/run from history.
2. Inspect the RIGHT panel: trades table, equity curve, and walk-forward view.

**Expected outcome:** Selecting a prior run re-binds the RIGHT analysis panel (trades/equity/WF), not only the left summary — unchanged by the staged-feed work (J-02 heavy-detail merge precedence byte-unchanged).
**Pass criteria:** The selected prior run's trades table, equity curve, and WF view all reload into the RIGHT panel and match that run.

---

### TC-12 — Legacy/pinned sessions show NO SCREEN/PROMOTE entries (graceful)

**Type:** browser
**Preconditions:** A pinned (J-07-style, e.g. TC-05 step 3) or pre-existing session; frontend running.

**Steps:**
1. Open the pinned/legacy session; inspect the activity feed and `AutoRunBar`.

**Expected outcome:** Staging is open-universe-only — pinned/legacy sessions render exactly as before with no SCREEN/PROMOTE entries; the feed is unchanged for old runs.
**Pass criteria:** Zero `SCREEN`/`PROMOTE` entries on the pinned/legacy session; activity feed + `AutoRunBar` visually unchanged from pre-iteration (additive-only, no regression).

---

### TC-13 — SCREEN-stage unit: `wfv_enabled=False` + cheapest catalog model + no insights

**Type:** artifact
**Preconditions:** Dev complete; `tests/test_auto_session.py` extended with a `FakePipeline` exercising SCREEN vs PROMOTE deterministically (no live LLM).

**Steps:**
1. Inspect/run the new SCREEN unit test(s).

**Expected outcome:** For every screened-only config the pipeline runs with `wfv_enabled=False`, generation uses the cheapest model **resolved at runtime from `shared/model_catalog.MODEL_PRICING`** (lowest per-token cost — not a hardcoded literal), and `generate_insights` is **not** called.
**Pass criteria:** Test asserts exact values: screened config call has `wfv_enabled=False`; the model id used equals the catalog-resolved cheapest (assertion derives from `MODEL_PRICING`, not a string literal that would pass by accident); `insight_calls == 0` for screened-only configs; a SCREEN generate/backtest failure is recorded and the loop continues (resilience). Passes as written, no skip/xfail.

---

### TC-14 — PROMOTE-stage unit: full pipeline, reuses screened strategy, k < screened

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`.

**Steps:**
1. Inspect/run the new PROMOTE unit test(s).

**Expected outcome:** Each promoted config runs `wfv_enabled=True` + `req.model` + insights and **reuses the SCREEN candidate's already-generated strategy (same code hash) and the warm Parquet cache** — no second `generate_strategy`, no OHLCV re-fetch; promotion is top-k with **k < number screened** and k small.
**Pass criteria:** Test asserts: promoted call `wfv_enabled=True` and model `== req.model`; `generate_strategy` call count for a promoted config is the SAME object/hash as its SCREEN candidate (no extra generate call; identical code hash); no re-fetch (cache hit / fetch count unchanged) for the shared window; number promoted `k < number screened` with k small (exact expected k asserted). Passes as written.

---

### TC-15 — Robust-best-is-promoted unit (not raw return, not screened-only)

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py` with ≥2 promoted configs and ≥1 higher-raw-return screened-only / WFE-failing candidate.

**Steps:**
1. Inspect/run the staged-form `test_open_universe_best_is_robust_not_raw_return`.

**Expected outcome:** `bestIterationId` is the `robust_score` winner over **promoted** iterations only; a higher-raw-return screened-only candidate (no WF) and any WFE-failing/over-leveraged candidate are not best; `select_best`/`robust_score` reused unchanged (no screen-aware best path).
**Pass criteria:** Test asserts the exact expected `bestIterationId` (a promoted id) AND explicitly asserts the higher-raw-return screened-only / WFE-failing candidate is **not** best; no re-implementation of `select_best`/`robust_score`. Passes as written.

---

### TC-16 — SCREEN backtests flow through the subprocess seam (deterministic, not timing)

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py` (parallel/extension of `test_open_universe_multi_config_runs_in_subprocess_distinct_pids`, ref `test_auto_session.py:1142`).

**Steps:**
1. Inspect/run the SCREEN subprocess-seam test.

**Expected outcome:** Every SCREEN backtest executes in a child process via the existing `_subprocess_backtest_executor` seam (iter-2 lesson: cheap in LLM/engine ≠ cheap in CPU; never in-process); guard is deterministic, not a timing bound.
**Pass criteria:** Test asserts `child_pid != os.getpid()` for a screened config's backtest; contains **no** `time.sleep`/elapsed-time threshold as the guard; a forced-in-process variant makes it FAIL. Passes as written.

---

### TC-17 — B1 regression guard unit (insights skipped only on a spend cap, never on `max-configs`)

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`; `test_pinned_path_unchanged_by_open_universe_addition` (`test_auto_session.py:1288`) carries the new `insight_calls` assertion.

**Steps:**
1. Inspect/run the augmented `test_pinned_path_unchanged_by_open_universe_addition` (3-iteration pinned run).
2. Inspect/run the new positive B1 test (a true `ai-tokens`/`usd`/`wall-clock` cap hit between `generate` and `insights`).

**Expected outcome:** On the **final pinned iteration** `tracker.would_exceed()` returns `"max-configs"` (the `_build_cost_tracker` `max_cfg==max_iter` branch, `auto_session.py:519`); the B1 gate must skip insights **only** when `would_exceed() in {"ai-tokens","usd","wall-clock"}`, **never** on `"max-configs"`, so the final pinned iteration's insights/refinement chain is preserved; a true spend cap between generate and insights **does** skip that one insights call while still building/writing the iteration node + recording activity.
**Pass criteria:** `assert pipe.insight_calls == 3` (every pinned iteration incl. the final one calls insights) — written so it goes **RED** under a naive truthy-`would_exceed()` gate and **GREEN** with the spend-cap-only gate; the positive test asserts exactly one insights call is skipped on a real spend-cap hit while the iteration is still written and activity recorded; the sentinel distinction is documented inline in `auto_session.py`. Both pass as written; neither skipped/xfail.

---

### TC-18 — Staged-form J-12/J-13 test updates (consciously updated, not loosened)

**Type:** artifact
**Preconditions:** Dev complete.

**Steps:**
1. Inspect `test_open_universe_runs_multiple_distinct_configs`, `test_max_configs_cap_stops_open_universe_no_post_cap_config`, `test_open_universe_best_is_robust_not_raw_return`, `test_hard_token_budget_exhausted_real_usage_and_durable_spend` and `git diff` for these tests.
2. Confirm each still asserts its invariant in the new staged semantics (not weakened to pass).

**Expected outcome:** Each test re-asserts its invariant under staging: ≥2 distinct seed configs explored; no SCREEN/PROMOTE config started past a hard cap; terminal `budget-exhausted`; exact real captured spend equals caps within one-call tolerance; robust-not-raw best over promoted iterations. The `max_configs` semantics under staging (screened vs promoted vs total counted as a "config") is documented inline in `auto_session.py`.
**Pass criteria:** The four tests pass with assertions that are *stronger or equivalently strict*, not removed/relaxed (diff shows staged-form assertions, not deleted ones); no `pytest.mark.skip`/`xfail` added; inline doc of the staged `max_configs` semantics present.

---

### TC-19 — Backend suite green + frontend build clean (zero new regressions)

**Type:** artifact
**Preconditions:** Dev complete; backend venv + frontend deps installed.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v 2>&1 | tee reports/qa/goal-auto-money-printer-iter-4-test.log`.
2. `cd apps/backend && .venv/bin/python -m pytest -q` — record exact pass/fail counts.
3. `cd apps/frontend && npm run build` — record exit code (only required if a frontend file was touched).

**Expected outcome:** All new + updated `test_auto_session.py` cases pass; the full suite shows zero new regressions vs the post-iter-3 baseline (183 passed / 1 failed); frontend (if touched) compiles.
**Pass criteria:** `test_auto_session.py` exits 0, all selected tests pass; full suite has **exactly one** failing test and it is only `test_directions_cache.py::test_write_and_read_full_round_trip` (passed count ≥ 183, raised by the new tests; failed count == 1); counts recorded verbatim; if a frontend file was modified, `npm run build` EXIT 0, else explicitly note "no frontend file touched — build not required".

---

### TC-20 — Anti-goal source guards (contracts/sandbox/engine, no new infra, cheapest-model-from-catalog, no secrets)

**Type:** artifact
**Preconditions:** Dev complete; ≥1 open-universe staged run produced artifacts under the file store.

**Steps:**
1. `git diff HEAD -- apps/backend/shared/contracts.py apps/backend/backend/sandbox.py` — confirm empty; confirm the deterministic next-bar engine / backtest fills/metrics and `BacktestPipeline` orchestration are byte-unchanged (usage *capture* via non-frozen pipeline returns allowed; engine bypass not).
2. Inspect the diff for any new datastore/queue/scheduler/broker/vector-store import, any session-store schema fork, any new external/pricing dependency, or any reintroduced in-browser iterate loop.
3. Confirm the cheapest model is resolved at runtime from `shared/model_catalog.MODEL_PRICING` (no hardcoded model-id literal driving SCREEN).
4. `grep -rni "sk-\|api[_-]\?key\|OPENAI_API_KEY\|ANTHROPIC_API_KEY\|Bearer " <session-store-dir>` over the staged run's `session.json`/activity (incl. SCREEN/PROMOTE entries)/insights artifacts.

**Expected outcome:** Frozen contract + sandbox + engine + backtest internals unchanged; no new infrastructure/dependency; no schema fork; staging open-universe-only; cheapest model catalog-resolved; no secrets persisted.
**Pass criteria:** `git diff HEAD -- shared/contracts.py sandbox.py` empty; zero engine/fills/metrics/`BacktestPipeline`-orchestration diff; no Celery/Redis/DB/broker/vector-store/new-dep import; no schema fork (reuses `_update_autorun`/`write_iteration`/`append_activity_entries`); cheapest model derived from `MODEL_PRICING` (not a literal); no in-browser iterate loop reintroduced; secret grep returns zero matches in any SCREEN/PROMOTE activity entry or persisted artifact.

---

### TC-21 — Closure artifacts present and non-vague

**Type:** artifact
**Preconditions:** Pipeline run for this phase.

**Steps:**
1. Verify `docs/handoffs/goal-auto-money-printer-iter-4-dev.md` exists and follows the handoff template.
2. Verify all 6 UI visibility artifacts exist for this phase (implementation-summary, user-visible-changes, ui-surface-map, ui-test-plan, ui-test-results, what-to-click) and the phase-closure gate passes.

**Expected outcome:** Dev handoff + all 6 UI artifacts exist and are concrete (exact click path to open the staged open-universe session and read SCREEN vs PROMOTE in the activity feed).
**Pass criteria:** All 7 files present and populated; no placeholder/empty sections; manual steps concrete and ordered; phase-closure gate verdict passes.

---

## Summary

Total test cases: **21**
- API tests: **6** (TC-01–TC-06)
- Browser tests: **6** (TC-07–TC-12)
- Artifact / unit / source-diff checks: **9** (TC-13–TC-21)

Coverage map: **J-14 (primary)** → TC-02, TC-03, TC-07, TC-13, TC-14, TC-15;
**J-13 under staging** → TC-04, TC-09, TC-18; **J-12 regression** → TC-01,
TC-08; **J-08 regression** → TC-10; **J-02 regression** → TC-11; **J-07–J-11
pinned-path unchanged** → TC-05, TC-12; **carried B1 fix (max-configs sentinel
trap)** → TC-17; **iter-2 subprocess-seam lesson** → TC-16; **error cases** →
TC-05, TC-06; **anti-goal/source guards (contracts/sandbox/engine, no new
infra, cheapest-model-from-catalog, no secrets, staged-form J-12/J-13 not
loosened)** → TC-18, TC-20; **suites & closure** → TC-19, TC-21.
