# goal-auto-money-printer-iter-5 Functional Test Plan

**Phase:** goal-auto-money-printer-iter-5
**Date:** 2026-05-19
**Frontend Present:** yes

## Phase Goal

**J-15** — a second open-universe automated run with `history_scope: "global"`
(or default) **warm-starts from prior sessions**: a read-only miner of the
existing durable file store reorders the bounded `_SEED_UNIVERSE` SCREEN
enumeration so the historically strongest `(symbol, timeframe)` family is
screened/promoted first, and emits exactly one **planner-decision** activity
entry citing the prior-session performance used (visible in the existing
session activity feed). `history_scope: "this-run"` opts out entirely (no
cross-run mining, no citation, deterministic fixed seed order). Default /
omitted resolves to effective `"global"` while the raw persisted value stays
`null`. Read-only mining is proven byte-identical; once-per-run off-thread; no
LLM planner added; budget / robust-best / pinned-path / J-01–J-14 invariants
all still hold.

**Conventions:** backend `BASE=http://localhost:${CHAIN_BACKEND_PORT:-8000}`
(health `GET $BASE/api/health` → 200); frontend
`http://localhost:${CHAIN_FRONTEND_PORT:-3000}`. Backend unit:
`cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`;
full suite `cd apps/backend && .venv/bin/python -m pytest -q`. Frontend build
`cd apps/frontend && npm run build`. Every J-15 run uses a **tiny budget** (no
`symbol`/`timeframe`, `objective:"robust"`, omitted/short date window, cheap
model, small `max_configs`, lenient/absent targets) so each run ends
`budget-exhausted` fast. Baseline to preserve: post-iter-4 full suite
**188 passed / 1 failed**; the ONLY tolerated failure remains the pre-existing
out-of-scope `test_directions_cache.py::test_write_and_read_full_round_trip`
— **zero new regressions** (new tests raise the passed count; failed stays 1).
`_SEED_UNIVERSE` = `(BTC/USDT,4h),(ETH/USDT,4h),(SOL/USDT,4h),(BNB/USDT,1h),
(BTC/USDT,1h),(ETH/USDT,1h)`; "family" = `(symbol,timeframe)`.

## Test Cases

### TC-01 — Run #1: producer, default/global, no prior history → terminal + promoted best in family F1

**Type:** api
**Preconditions:** Backend running; an empty/isolated session store (no prior auto-sessions).

**Steps:**
1. `curl -s -o /tmp/tc01.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'` (NO `symbol`/`timeframe`/`history_scope`); capture `SID1`.
2. Poll `GET $BASE/api/sessions/$SID1` every 3s up to 180s until `autoRun.status` is terminal.
3. Record the first **promoted** iteration's `(symbol,timeframe)` family as **F1**, `bestIterationId`, and the SCREEN enumeration order.

**Expected outcome:** With no prior history, run #1 behaves byte-identically to today's fixed `_SEED_UNIVERSE` order, reaches a terminal state within the tiny budget, and marks a promoted best — establishing the prior-session evidence run #2 mines.
**Pass criteria:** `http_code == 200`; `.sessionId` non-empty and listed in `GET /api/sessions`; terminal `autoRun.status` with `stopReason == "budget-exhausted"`; **no** planner-decision/warm-start activity entry on run #1 (empty store → no citation); SCREEN order == fixed `_SEED_UNIVERSE`; `bestIterationId` non-null on a promoted iteration; F1 recorded.

---

### TC-02 — Run #2: `history_scope: "global"` → planner-decision citation + F1 screened/promoted first

**Type:** api
**Preconditions:** TC-01 terminal (run #1 in the **same** store, family F1 known).

**Steps:**
1. `curl -s -o /tmp/tc02.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","objective":"robust","history_scope":"global","budget":{"max_iterations":2,"max_configs":2}}'`; capture `SID2`.
2. Poll to terminal. Enumerate the session activity feed; locate the **planner-decision / warm-start** entry; record its text. Record the SCREEN enumeration order and the **first promoted** iteration's family.
3. Read `autoRun` from `GET $BASE/api/sessions/$SID2`: record `historyScope` and the additive effective-scope key (e.g. `effectiveHistoryScope`).

**Expected outcome:** Run #2 mines run #1 read-only, reorders the bounded seed so F1 is screened/promoted first, and appends exactly one planner-decision entry citing run #1's concrete robust performance — UI-indistinguishable in shape from existing feed entries.
**Pass criteria:** `http_code == 200`; terminal reached; **exactly one** planner-decision/warm-start activity entry present, in plain operator language, citing the prior `(symbol,timeframe)` family + a concrete prior robust score + prior-session count (e.g. "Warm start (global history): prioritising BTC/USDT 4h — prior best robust 0.78 across 1 prior session(s)"); the resolved SCREEN order is a **permutation of `_SEED_UNIVERSE`** with **F1 first**; the **first promoted** config's family **== F1**; persisted `historyScope == "global"`; the effective-scope key resolves to `"global"`; no secrets in the entry.

---

### TC-03 — Run #3: `history_scope: "this-run"` → opt-out honored (no citation, fixed seed order)

**Type:** api
**Preconditions:** TC-01 + TC-02 terminal in the **same** store (prior history present).

**Steps:**
1. `curl -s -o /tmp/tc03.json -w "%{http_code}" -X POST "$BASE/api/auto-sessions" -H 'Content-Type: application/json' -d '{"natural_language":"momentum breakout","objective":"robust","history_scope":"this-run","budget":{"max_iterations":2,"max_configs":2}}'`; capture `SID3`.
2. Poll to terminal. Enumerate the activity feed; record SCREEN enumeration order and any planner-decision/warm-start entry. Read `autoRun.historyScope` + effective-scope key.

**Expected outcome:** `"this-run"` fully opts out: no cross-run mining, no planner-decision entry, deterministic fixed `_SEED_UNIVERSE` order even though prior history (run #1, run #2) exists.
**Pass criteria:** `http_code == 200`; terminal reached; **zero** planner-decision/warm-start activity entries; SCREEN enumeration **byte-identical** to the fixed `_SEED_UNIVERSE` order (NOT F1-first — unaffected by TC-01/TC-02 history); persisted `historyScope == "this-run"` and the effective-scope key reads `"this-run"`.

---

### TC-04 — Default (omitted) resolves to effective `"global"` while raw persists `null`

**Type:** api
**Preconditions:** Prior history present (TC-01/TC-02 store) so warm-start can act.

**Steps:**
1. `POST $BASE/api/auto-sessions` open-universe with `objective:"robust"`, tiny budget, and **no** `history_scope` key; capture `SID4`; poll to terminal.
2. Inspect the activity feed for a planner-decision entry and the SCREEN order; read `autoRun.historyScope` (raw) and the effective-scope key.

**Expected outcome:** Omitted `history_scope` warm-starts (vision: "learns from prior sessions") while the raw supplied value still persists verbatim as `null`; the *effective* resolved scope is observable.
**Pass criteria:** Planner-decision entry **present** and reorder applied (warm-start active, like TC-02); raw persisted `historyScope` is `null` (unchanged from iter-4 persistence); the additive effective-scope key resolves to `"global"`; no schema fork (only an additive key in the existing `autoRun` dict).

---

### TC-05 — Error/edge: garbage scope → clean default (no 500); corrupt prior dir skipped; pinned path untouched

**Type:** api
**Preconditions:** Backend running; a store containing one deliberately corrupt/empty prior session dir alongside ≥1 valid prior session; baseline `GET /api/sessions` count recorded.

**Steps:**
1. `POST $BASE/api/auto-sessions` open-universe with `"history_scope":"garbage-value"`, tiny budget; capture status code and `SID`; poll to terminal.
2. With a corrupt/empty prior session dir present, trigger a `"global"` open-universe run; poll to terminal.
3. Valid pinned run: `POST` with `{"natural_language":"Buy when RSI<30, sell when RSI>70","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-02-01","initial_capital":10000,"model":"gpt-5.4-mini","budget":{"max_iterations":2}}`; capture `SIDP`; poll to terminal; inspect its activity feed.

**Expected outcome:** Unknown/garbage `history_scope` is treated as a clean default (no 500); a corrupt/empty prior session dir is skipped (mining is best-effort, never hangs/raises out, mirroring the SCREEN/PROMOTE `except` discipline); the pinned path takes NO mining/reorder/citation (warm-start is open-universe-only).
**Pass criteria:** (1) `http_code == 200` (NOT 422/500), run reaches a terminal state, behaves as the safe default (effective `"global"`); (2) the `"global"` run with a corrupt prior dir still reaches a terminal state — the corrupt dir is skipped, no traceback/hang; (3) `SIDP` `http_code == 200`, exactly one config/iteration per round, **zero** planner-decision/warm-start/SCREEN/PROMOTE entries, prompt-refinement chain intact (J-07–J-11 byte-unchanged).

---

### TC-06 — J-15 browser (PRIMARY): three-run sequence, citation visible on global, absent on this-run

**Type:** browser
**Preconditions:** Frontend + backend running against ONE shared isolated store; the three sessions from TC-01 (run #1, default/global no prior), TC-02 (run #2 `"global"`), TC-03 (run #3 `"this-run"`).

**Steps:**
1. Chrome MCP → open `http://localhost:${CHAIN_FRONTEND_PORT:-3000}`; open the **run #2** ("global") session from the session list (no manual reload); live-poll until terminal.
2. Read the session activity feed: confirm the planner-decision/warm-start entry is legibly rendered (not flattened/truncated — operator can read the cited family + prior robust score). Confirm the first promoted iteration's family == TC-01's F1.
3. Save screenshot → `reports/qa/goal-auto-money-printer-iter-5-evidence/TC-06-run2-warmstart-citation.png`.
4. Open the **run #3** ("this-run") session; confirm NO planner-decision/warm-start entry anywhere in its feed; save screenshot → `reports/qa/goal-auto-money-printer-iter-5-evidence/TC-06-run3-no-citation.png`.

**Expected outcome:** A headless warm-started run is UI-indistinguishable from a manual one; the global run's planner-decision citation is operator-readable in the existing feed; the opt-out run shows no such entry.
**Pass criteria:** Run #2 feed shows the planner-decision citation with readable prior-session evidence (family + prior robust score + session count), and run #2's first promoted family == F1; run #3 feed shows **zero** planner-decision/warm-start entries; both screenshots saved under the evidence dir; no new page/panel/component introduced (renders in the existing activity feed).

---

### TC-07 — Regression browser (re-verify live, NOT carried headline): J-02, J-08, J-12, J-13, J-14

**Type:** browser
**Preconditions:** The TC-06 shared-store sessions terminal; frontend running.

**Steps:**
1. **J-02:** Open run #1's session; select a prior completed iteration from history — confirm its strategy spec, metrics, trades, and equity/WF reload into the detail panel and match that run (read-only mining did not corrupt prior history).
2. **J-08:** Start a fresh tiny open-universe run; without manual reload, observe the status indicator move "running" → terminal with ≥1 iteration + suggestions appearing.
3. **J-12/J-14:** On run #2, enumerate explored configs and the SCREEN vs PROMOTE markers — confirm ≥2 distinct seed configs and the staged SCREEN→PROMOTE feed still render.
4. **J-13:** Open the `budget-exhausted` session; locate `AutoRunBar`; confirm numeric tokens/USD/configs spend and the `budget-exhausted` reason render (no `NaN`/`undefined`).

**Expected outcome:** Warm-start (ordering-only) regresses none of the still-passing journeys; prior-run history browse is unaffected; live tracking, staged SCREEN→PROMOTE, ≥2 distinct configs, and durable spend all still hold.
**Pass criteria:** J-02 prior run re-binds correctly (unchanged by mining); J-08 reaches terminal with no manual reload; J-12 ≥2 pairwise-distinct `(symbol,timeframe)` configs from the bounded seed; J-14 SCREEN→PROMOTE staging visible; J-13 `AutoRunBar` shows spend ≤ caps + `budget-exhausted`. Any one failing is a blocker.

---

### TC-08 — Warm-start reorder unit: F1 placed first, permutation of `_SEED_UNIVERSE`, first promoted family == F1

**Type:** artifact
**Preconditions:** `tests/test_auto_session.py` extended (deterministic, tiny budget, isolated `store` fixture + `FakePipeline`); a prior session seeded via the real store path whose promoted best family is F1.

**Steps:**
1. Inspect/run the warm-start-reorder test.

**Expected outcome:** With a prior promoted session for family F1, run #2's resolved SCREEN enumeration places F1 first and stays a permutation of the bounded seed; the first promoted config's family == F1.
**Pass criteria:** Test asserts `resolved_order[0]`'s family == F1; `set(resolved_order) == set(auto_session._SEED_UNIVERSE)` (no new symbols/timeframes, no fan-out); the first **promoted** iteration's family == F1; deterministic stable tie-break preserves the existing fixed seed order for unseen/tied families. Passes as written, no skip/xfail.

---

### TC-09 — Opt-out unit: `"this-run"` byte-identical fixed seed order, no citation, no cross-run influence

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`; a prior promoted session for F1 present in the isolated store.

**Steps:**
1. Inspect/run the opt-out test (`history_scope:"this-run"` with prior history present).

**Expected outcome:** `"this-run"` performs no mining and no reorder even when prior history exists; SCREEN order is byte-identical to the fixed `_SEED_UNIVERSE`; no planner-decision activity entry.
**Pass criteria:** Test asserts resolved SCREEN order **==** `list(auto_session._SEED_UNIVERSE)` (exact equality, not F1-first); **zero** planner-decision/warm-start activity entries; behaviour identical to an empty store despite prior history. Passes as written.

---

### TC-10 — Default→global unit (updated `test_history_scope_defaults_to_none_when_omitted`)

**Type:** artifact
**Preconditions:** Extended/updated `test_auto_session.py`; prior history present.

**Steps:**
1. Inspect the `git diff` of `test_history_scope_defaults_to_none_when_omitted` and run it.

**Expected outcome:** The test is *consciously updated* to the new effective semantics (NOT loosened): raw persisted `historyScope` is still asserted `None`; the *effective* scope is now asserted `"global"` and warm-start active (citation present, reorder applied); the stale "J-15/OUT" comment corrected.

**Pass criteria:** Diff shows the persistence assertion retained (`historyScope is None`) PLUS new behavioural assertions (effective scope `"global"`, planner-decision entry present, reorder applied); no `pytest.mark.skip`/`xfail`; the stale "J-15/OUT" comment is corrected, not deleted-to-pass. Passes as written.

---

### TC-11 — Read-only proof unit: prior-session files byte-identical before/after run #2 (iter-0 lesson, J-02)

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`; ≥1 seeded prior session in the isolated store.

**Steps:**
1. Inspect/run the read-only-proof test: snapshot a content hash (and mtime) of **every** prior-session file (`session.json`, `meta.json`, `result.json`, `rating.json`, activity log) before run #2; assert byte-identical after.

**Expected outcome:** The miner reads prior sessions strictly read-only — no write, rename, delete, re-order, or in-place mutation of any prior artifact (J-02 history browse not regressed).
**Pass criteria:** Test asserts every prior-session file's content hash is identical pre/post run #2 AND the set of prior-session files is unchanged (no added/removed/renamed files); mtimes unchanged. Passes as written, no skip/xfail.

---

### TC-12 — Once-per-run unit: miner invoked exactly once per run (not per SCREEN/PROMOTE), off-thread, no LLM planner

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py` with a call-count probe on the mining helper.

**Steps:**
1. Inspect/run the once-per-run test for a warm-started open-universe run.
2. Confirm in source that the mine+reorder+citation runs via `asyncio.to_thread` once at run start (open-universe only, before the SCREEN loop), and that **no LLM planner call** was added.

**Expected outcome:** The mine+reorder+citation happens exactly once at run start, off the event-loop thread; it is NOT recomputed per round/SCREEN/PROMOTE candidate; structurally satisfies the "MUST NOT be re-sent uncached every round" anti-goal via the once-per-run guarantee; no LLM planner is introduced (spec's explicit core design — deterministic surrogate only).
**Pass criteria:** Miner call-count **== 1** per run (asserted, not per SCREEN/PROMOTE candidate); the mine site uses `asyncio.to_thread` (off-thread; no `time.sleep`/elapsed-time guard); **no** new LLM planner call exists (no new chat/completions call in the planning path). Conditional: *if* an LLM planner were added (it must NOT be), its history-context block must carry `cache_control:{"type":"ephemeral"}` and its tokens must drain via `_drain_usage`→`record_usage` — verify absence of an LLM call is the expected result here. Passes as written.

---

### TC-13 — No-history fallback unit + existing J-12/J-13/J-14 tests GREEN unchanged

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`; existing `test_open_universe_runs_multiple_distinct_configs`, `test_open_universe_best_is_robust_not_raw_return`, `test_max_configs_cap_stops_open_universe_no_post_cap_config`, `test_pinned_path_unchanged_by_open_universe_addition` present.

**Steps:**
1. Inspect/run the empty-store fallback test and the four named existing open-universe/cap/pinned tests; `git diff` the four.

**Expected outcome:** Empty store → SCREEN enumeration == today's fixed `_SEED_UNIVERSE` order; the existing J-12/J-13/J-14/pinned tests pass unchanged (their isolated `store` fixture has no prior history, so behaviour is byte-identical to pre-iter-5).
**Pass criteria:** Fallback test asserts enumeration `== list(auto_session._SEED_UNIVERSE)` for an empty store; the four existing tests pass **without modification** (diff for them is empty OR only intentional staged-form parity, no weakening); no skip/xfail added. Passes as written.

---

### TC-14 — Consciously-updated persistence test not loosened (`test_open_universe_objective_and_history_scope_persisted`)

**Type:** artifact
**Preconditions:** Updated `test_auto_session.py`.

**Steps:**
1. Inspect the `git diff` of `test_open_universe_objective_and_history_scope_persisted` and run it.

**Expected outcome:** Updated to the new effective semantics (NOT loosened): persistence of `objective`+`historyScope` still asserted; `"this-run"` behaviour now also asserted (no citation, no reorder); the stale "J-15/OUT" comment corrected to the new in-scope semantics.
**Pass criteria:** Diff shows the original persistence assertions retained PLUS new behavioural assertions for `"this-run"` (no planner-decision entry, fixed seed order); assertions are *stronger or equivalently strict*, not removed/relaxed; stale "J-15/OUT" comment corrected; no skip/xfail. Passes as written.

---

### TC-15 — Robust-best invariant unit: historically-favoured family that promotes worse is NOT best

**Type:** artifact
**Preconditions:** Extended/staged `test_open_universe_best_is_robust_not_raw_return` with a warm-started prior favouring a family that then promotes worse than another candidate.

**Steps:**
1. Inspect/run the robust-best-under-warm-start test.

**Expected outcome:** Warm-start changes SCREEN *order* only; `select_best`/`robust_score` over **promoted** iterations is unchanged. A historically-favoured (F1-first) family that promotes worse than another candidate is NOT marked best; a higher-raw-return WFE-failing/over-leveraged candidate is NOT best (J-09/J-16 invariant intact).
**Pass criteria:** Test asserts the exact expected `bestIterationId` is the genuine `robust_score` winner over promoted iterations (NOT the warm-start-favoured family merely because it screened first); the higher-raw-return / WFE-failing candidate is explicitly **not** best; `select_best`/`robust_score` not re-implemented or re-tuned. Passes as written.

---

### TC-16 — Error-cases unit: garbage scope → clean default; corrupt/empty prior dir skipped, run still terminal

**Type:** artifact
**Preconditions:** Extended `test_auto_session.py`.

**Steps:**
1. Inspect/run the error-cases tests: (a) unknown/garbage `history_scope` value; (b) a corrupt/empty prior session dir present during a `"global"` run.

**Expected outcome:** Garbage `history_scope` resolves to the safe default (effective `"global"`) with no exception/500; a corrupt or empty prior session/iteration dir is skipped without aborting or hanging the run (mining is best-effort, mirrors the SCREEN/PROMOTE `except` discipline).
**Pass criteria:** (a) garbage value → no raise, run reaches a terminal state, resolved as the safe default; (b) corrupt/empty prior dir skipped, mining returns (does not raise out or hang), run still reaches a terminal `autoRun.status`; both assert exact terminal states. Passes as written, no skip/xfail.

---

### TC-17 — Backend suite GREEN + frontend build clean (zero new regressions)

**Type:** artifact
**Preconditions:** Dev complete; backend venv + frontend deps installed.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v 2>&1 | tee reports/qa/goal-auto-money-printer-iter-5-test.log`.
2. `cd apps/backend && .venv/bin/python -m pytest -q` — record exact pass/fail counts.
3. `cd apps/frontend && npm run build` — record exit code (only required if a frontend file was modified).

**Expected outcome:** All new + updated `test_auto_session.py` cases pass; the full suite shows zero new regressions vs the post-iter-4 baseline (188 passed / 1 failed); frontend (if touched) compiles.
**Pass criteria:** `test_auto_session.py` exits 0, all selected tests pass; full suite has **exactly one** failing test and it is only `test_directions_cache.py::test_write_and_read_full_round_trip` (passed count ≥ 188, raised by the new tests; failed count == 1); counts recorded verbatim; if a frontend file was modified `npm run build` EXIT 0, else explicitly note "no frontend file touched — build not required".

---

### TC-18 — Anti-goal source guards (read-only, no schema fork, no new infra, no LLM planner, no secrets, off-thread)

**Type:** artifact
**Preconditions:** Dev complete; ≥1 warm-started open-universe run produced artifacts under the file store.

**Steps:**
1. `git diff HEAD -- apps/backend/shared/contracts.py apps/backend/backend/sandbox.py apps/backend/backend/pipeline.py apps/backend/backtest/` — confirm empty (frozen contract / sandbox / engine / fills / metrics byte-unchanged).
2. Inspect the diff for any new datastore/index/queue/scheduler/broker/vector-store import, any session-store **schema fork** (effective-scope must be an *additive* `autoRun` key via the existing `_update_autorun`, mirroring iter-4's additive `stage`), any new write/rename/delete path against prior sessions, any new LLM planner chat/completions call, and any reintroduced in-browser iterate loop.
3. Confirm the warm-start mine runs off the event loop via `asyncio.to_thread` (open-universe only, before the first SCREEN) — not a per-round synchronous walk, not a timing-based guard.
4. `grep -rniE "sk-|api[_-]?key|OPENAI_API_KEY|ANTHROPIC_API_KEY|Bearer " <session-store-dir>` over the warm-started run's `session.json` / activity log (including the planner-decision entry) / insights artifacts.

**Expected outcome:** Frozen contract + sandbox + engine + backtest internals unchanged; no new infrastructure/dependency; no schema fork; mining read-only and open-universe-only; no LLM planner added; no in-browser loop; no secrets persisted.
**Pass criteria:** `git diff HEAD --` of `contracts.py`/`sandbox.py`/`pipeline.py`/`backtest/` is empty; no Celery/Redis/DB/broker/vector-store/new-dep import; effective-scope is an additive `autoRun` key (no schema fork, no parallel store); zero new write/rename/delete against prior session dirs; no new LLM planner call; no in-browser iterate loop reintroduced; mine via `asyncio.to_thread`; secret grep returns **zero** matches in any persisted artifact incl. the planner-decision entry.

---

### TC-19 — Closure artifacts present and non-vague

**Type:** artifact
**Preconditions:** Pipeline run for this phase.

**Steps:**
1. Verify `docs/handoffs/goal-auto-money-printer-iter-5-dev.md` exists and follows the handoff template.
2. Verify all 6 UI visibility artifacts exist for this phase (implementation-summary, user-visible-changes, ui-surface-map, ui-test-plan, ui-test-results, what-to-click) and the phase-closure gate passes.

**Expected outcome:** Dev handoff + all 6 UI artifacts exist and are concrete (exact click path to open a global-scope warm-started session and read the planner-decision citation in the existing activity feed; how to confirm a `"this-run"` session shows no citation).
**Pass criteria:** All 7 files present and populated; no placeholder/empty sections; manual steps concrete and ordered; phase-closure gate verdict passes.

---

## Summary

Total test cases: **19**
- API tests: **5** (TC-01–TC-05)
- Browser tests: **2** (TC-06 primary J-15, TC-07 regressions)
- Artifact / unit / source-diff checks: **12** (TC-08–TC-19)

Coverage map: **J-15 (primary)** → TC-01, TC-02, TC-03, TC-06, TC-08, TC-09;
**default→global semantics** → TC-04, TC-10; **opt-out honored** → TC-03,
TC-09, TC-14; **read-only / J-02 not regressed (iter-0 lesson)** → TC-05,
TC-07, TC-11, TC-18; **once-per-run / no LLM planner / off-thread (iter-2
lesson)** → TC-12, TC-18; **no-history fallback / J-12/J-13/J-14 preserved** →
TC-01, TC-07, TC-13; **robust-best invariant (J-09/J-16) intact** → TC-15;
**pinned path (J-07–J-11) byte-unchanged** → TC-05; **consciously-updated
tests not loosened** → TC-10, TC-14; **error cases** → TC-05, TC-16;
**anti-goal source guards (frozen contract/sandbox/engine, no new infra, no
schema fork, no secrets)** → TC-18; **suites & closure** → TC-17, TC-19.
