# Goal Iteration 5 — Global-history warm start + `history_scope` opt-out (read-only, cached)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** auto-money-printer
- **Iteration:** 5
- **Mode:** next
- **Depth:** full
- **Target journeys:** J-15
- **Required-still-passing journeys:** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09, J-10, J-11, J-12, J-13, J-14
- **Frontend Present:** no (code); the new capability is visible through the **existing** session activity feed — browser-qa MUST verify the planner-decision entry renders, exactly as iter-4's SCREEN/PROMOTE entries do.
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - Global history learning MUST be read-only mining of the existing store (it MUST NOT mutate or delete prior sessions' artifacts); the `history_scope` opt-out MUST be honored.
  - The LLM-planner / history context MUST use prompt caching; the leaderboard/history MUST NOT be re-sent uncached every round.
  - Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify.
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - Identical generated strategies (by code hash) MUST NOT be re-generated or re-backtested; the OHLCV Parquet cache MUST be reused across configs (no re-fetch when a covering cache exists).
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - `GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint.
  - `BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST NOT run a second in-browser iterate loop.
  - The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.

## GOAL

A second open-universe automated run started with `history_scope: "global"` **warm-starts from prior sessions**: a read-only miner of the existing file store reorders the bounded-seed SCREEN enumeration so the historically strongest (symbol, timeframe) family is screened — and therefore promoted — first, and records a **planner-decision activity entry citing the prior-session performance it used**, visible in the existing session activity feed. A run started with `history_scope: "this-run"` opts out entirely (no cross-run mining, no citation, deterministic fixed seed order). Prior sessions' artifacts are never mutated; the hard budget, robust-best, and the unchanged pinned path all still hold.

## BACKGROUND

14/16 journeys pass; the only remaining Optimizer work is J-15 (this iteration) then J-16. The iter-4 evaluator and journey history both recommend iter-5 = **J-15** at **full** depth. Today `history_scope` is *accept-and-persist only* (`auto_session.py:390-401,1565-1568`) and the open-universe SCREEN enumeration is a fixed deterministic walk of `_SEED_UNIVERSE` (`_config_plan`, `auto_session.py:511-533`); there is **no** cross-run learning and **no** planner at all. J-15 introduces a read-only global-history surrogate that reorders that seed enumeration by mined prior performance, an opt-out, and the planner-decision citation. This crosses the open-universe controller, the durable file store (read-only), the cost tracker, and the activity feed, and it activates three load-bearing cross-run anti-goals — hence **full** depth (full 11-step pipeline), as the evaluator mandated.

**Design decision — deterministic history surrogate is the core; LLM-planner is optional but, if present, MUST be cached.** The J-15 acceptance is satisfiable cheaply and *deterministically* by a read-only history *surrogate* (the "history surrogate/bandit" half of Key Capability 11): mine prior sessions' promoted-iteration robust scores by `(symbol, timeframe)` family and reorder the bounded seed enumeration. This keeps the tiny-budget rule and avoids flaky LLM tests. The goal's "cached LLM-planner" and the prompt-caching anti-goal still bind: **if** any LLM call is used for planning, the large history-context block MUST carry `cache_control: {"type": "ephemeral"}` (reuse the exact `strategy/insights_generator.py:344-351` pattern) and MUST NOT be re-sent uncached; **regardless** of LLM use, the warm-start plan MUST be computed **exactly once per run** (not re-mined / re-sent every round) — that structural once-per-run guarantee is the testable form of "MUST NOT be re-sent uncached every round". Do NOT add an LLM planner call the acceptance does not require; do NOT violate the caching anti-goal if you do.

**Lesson — iter-0 (Applies to: any iter touching session/run-history reads).** J-02's history browse is a still-passing journey. The miner reads prior sessions/iterations **read-only**; it MUST NOT mutate, rewrite, re-order, or delete any prior `session.json` / `meta.json` / `result.json` / `rating.json` / activity log, and MUST NOT regress J-02. Ship a test that snapshots prior-session file content hashes before the warm-start run and asserts byte-identical after.

**Lesson — iter-2 (Applies to: any iter touching the headless loop / event-loop non-blocking).** History mining walks potentially many prior session directories — that is blocking file I/O. It MUST run off the event-loop thread via `asyncio.to_thread` (the same pattern `_update_autorun` / `append_activity_entries` already use), exactly once at run start — never a per-round synchronous walk on the event-loop thread, and never a timing-based "non-blocking" assertion (the iter-2 false-guard). Backtests still flow through the unchanged `multiprocessing` subprocess seam (deterministic `child_pid != os.getpid()`).

**Lesson — iter-3 (Applies to: any iter touching the `would_exceed` / budget loop).** If a planning LLM call is added, its real captured tokens MUST drain into the cost tracker through the existing `_drain_usage` → `record_usage` path and the round-top `tracker.would_exceed()` gating MUST be unchanged; distinguish the `"max-configs"` sentinel from the spend caps `{"ai-tokens","usd","wall-clock"}` (`_SPEND_CAPS`, `auto_session.py:100-107`). A surrogate-only planner adds no tokens but still must not start work past a reached cap.

## IN SCOPE

### Backend

- [ ] **Read-only global-history surrogate** (new helper in `auto_session.py`, dependency-light like `cost_tracker.py`): mine the **existing** `session_store` (`BASE_DIR` / `live/`, the same durable store — no parallel store, no schema fork) for prior auto-sessions' **promoted, walk-forward-bearing** iterations and aggregate the **best robust score per `(symbol, timeframe)` family**. Read-only: no writes, renames, deletes, or in-place mutation of any prior artifact. Must reuse existing `session_store` read helpers (`read_session_meta`, `list_iteration_dirs`/`read_iteration_meta`/`read_iteration_full`); MUST NOT make `GET /api/sessions/{id}` eager (mining is a separate one-time server-side read at run start, not on the list/open path). Exclude the current run's own session id (cross-run only).
- [ ] **Warm-start reorder of the SCREEN seed enumeration** (the evaluator's named injection point — `_config_plan` open-universe branch / the seed order consumed by `_run_staged_open_universe`): when warm-start is active, return the bounded `_SEED_UNIVERSE` **as a stable permutation** ordered by mined family strength (strongest historical family first; deterministic stable tie-break preserving the existing fixed seed order). It MUST remain a permutation of the **same bounded seed universe** — no new symbols/timeframes, no fan-out beyond `_SEED_UNIVERSE`.
- [ ] **`history_scope` effective semantics** (replace the accept-and-persist-only behaviour, documented inline):
  - `"global"` → warm-start ON: mine all prior sessions, reorder, emit the planner-decision citation.
  - `"this-run"` → **opt-out**: no cross-run mining, no citation, deterministic fixed `_SEED_UNIVERSE` order (byte-identical to today's pre-iter-5 enumeration).
  - omitted / `null` (default) → treated as **`"global"`** warm-start (the vision is "learns from prior sessions to spend tokens where payoff is highest"; opt-out is the explicit `"this-run"`). The raw supplied value still persists verbatim (`null` stays `null`); the *effective* resolved scope MUST be derivable/visible (e.g. recorded in the warm-start activity entry and/or the durable `autoRun` block — no schema fork: an additive key in the existing `autoRun` dict is acceptable, mirroring iter-4's additive `stage`).
- [ ] **Planner-decision activity entry** (only when warm-start is active): one `_activity(...)` entry appended via the existing `session_store.append_activity_entries`, citing the concrete prior-session evidence used — e.g. `"Warm start (global history): prioritising BTC/USDT 4h — prior best robust 0.78 across 2 prior session(s)"`. Plain operator language; **no API keys/secrets**; same shape the existing feed renders (UI-indistinguishable from a manual run). When `history_scope: "this-run"` or there is no usable prior history, **no** such entry is appended.
- [ ] **No-prior-history fallback is byte-identical to today.** Empty store / no prior promoted iterations / opt-out → the open-universe SCREEN enumeration is exactly the current fixed `_SEED_UNIVERSE` order, so J-12 (≥2 distinct configs), J-13 (hard budget), and J-14 (SCREEN→PROMOTE) are preserved unchanged. The existing J-12/J-13/J-14 tests (isolated `store` fixture, no prior history) MUST continue to pass.
- [ ] **Once-per-run, off-thread.** The warm-start mine + reorder + citation happens **exactly once** at run start, via `asyncio.to_thread` (off the event-loop thread). It is NOT recomputed or re-sent per round/SCREEN/PROMOTE candidate. If a planning LLM call is introduced, its history-context block MUST carry `cache_control: {"type": "ephemeral"}` (the `insights_generator.py:344-351` pattern), its tokens MUST drain via `_drain_usage`→`record_usage`, and the round-top `would_exceed()` gating MUST be unchanged (`"max-configs"` vs spend-cap distinction preserved).
- [ ] **Robust-best invariant preserved.** Warm-start only changes SCREEN *order*; `select_best`/`robust_score` over **promoted** iterations is unchanged. A historically-favoured family that screens/promotes poorly MUST NOT be marked best over a genuinely better promoted candidate (J-09/J-16 invariant intact).
- [ ] **Pinned path byte-unchanged.** Warm-start / history mining is open-universe-only. A pinned request (J-07–J-11) runs exactly as today: no mining, no reorder, no planner-decision entry, prompt-refinement chain intact.

### Frontend

- [ ] None expected — the existing session activity feed already renders arbitrary activity entries (iter-2 "Exploring config", iter-4 SCREEN/PROMOTE). **If and only if** the existing renderer flattens/truncates so an operator cannot read the planner-decision citation, a *minimal additive* presentation tweak (preserve the entry text; no new component) is in scope. Do not add frontend the acceptance does not require; the iter-4 lesson on no second in-browser loop still applies (zero frontend loop change).

### New user-facing capability

A user (or an API caller) who runs the headless optimizer a second time can have it **learn from prior runs**: with `history_scope: "global"` it visibly prioritises the (symbol, timeframe) families that performed best historically and shows *why* in the session activity feed; with `history_scope: "this-run"` it runs fresh with no cross-run influence.

### New information displayed

A new planner-decision entry in the existing session activity feed citing the prior-session performance that drove the warm-start ordering (only on global-scope runs with usable history).

### New user actions

`POST /api/auto-sessions` with `history_scope: "global" | "this-run"` now changes behaviour (warm-start vs opt-out), not just persisted metadata.

### UI surface changes

None structural — the planner-decision entry renders in the existing session activity feed; a headless warm-started run remains UI-indistinguishable from a manual one.

### Product surface delta

The automated optimizer becomes *cross-run adaptive*: repeat runs spend the cheap-first SCREEN budget on historically strong families first, with an auditable, opt-out-able, read-only basis for that decision.

## OUT OF SCOPE

- **J-16** (deep overfit-gating stress demo / leaderboard) — next iteration; its robust-best invariant is only *preserved* here, not extended.
- Any bandit/Thompson/UCB exploration policy beyond a deterministic best-family-first reorder of the bounded seed (single-robust-scalar Non-Goal; no fan-out).
- Any new datastore/index/vector store, schema fork, or migration of prior artifacts.
- Mutating, compacting, or back-filling prior sessions' artifacts in any way.
- Mining or warm-starting on the **pinned** path.

## DEFINITION OF DONE

- [ ] Target journey **J-15** passes via browser-qa (planner-decision citation visible in the activity feed on a `"global"` run; absent on a `"this-run"` run; first promoted config's family matches the prior run's top family).
- [ ] Required-still-passing journeys **J-01–J-14** remain green (J-12/J-13/J-14 open-universe tests pass unchanged; pinned J-07–J-11 byte-unchanged; J-02 history browse unaffected).
- [ ] No anti-goal violation introduced (read-only mining proven by a before/after content-hash assertion; opt-out honored; bounded-seed permutation only; once-per-run / cached; budget/robust-best/pinned invariants intact; no secrets in artifacts).
- [ ] Unit/integration tests pass; full backend suite shows no new regressions (the pre-existing out-of-scope `test_directions_cache::test_write_and_read_full_round_trip` failure is the only tolerated red, unchanged).
- [ ] Dev handoff written at `docs/handoffs/goal-auto-money-printer-iter-5-dev.md`.

## TESTING REQUIREMENTS

- **Browser (J-15):** three tiny-budget open-universe runs against one shared isolated store — Run #1 (no prior history, default/global) producing a promoted best in a known family F1; Run #2 (`history_scope: "global"`) → activity feed shows the planner-decision entry citing run #1's performance AND F1 is the first promoted family; Run #3 (`history_scope: "this-run"`) → no planner-decision/warm-start entry, fixed seed order. Capture screenshots of the run #2 citation entry and the run #3 absence.
- **Unit/integration (deterministic, tiny budgets, isolated `BACKTEST_STORE_DIR` via the existing `store` fixture, `FakePipeline`):**
  - Warm-start reorder: seed a prior session whose promoted best family is F1; assert run #2's resolved SCREEN enumeration places F1 first and is a permutation of `_SEED_UNIVERSE` (`set(order) == set(_SEED_UNIVERSE)`); assert the first **promoted** config's family == F1.
  - Opt-out: `history_scope: "this-run"` → SCREEN order byte-identical to the fixed `_SEED_UNIVERSE`; **no** planner-decision activity entry; no cross-run influence even with prior history present.
  - Default resolves to global: omitted `history_scope` with prior history present → warm-start active (citation present, reorder applied); the raw persisted `historyScope` is still `null` while the *effective* scope is observable.
  - **Read-only proof:** snapshot a content hash (and mtime) of every prior-session file before run #2; assert byte-identical after — no mutation/delete/rename of any prior artifact.
  - **Once-per-run / not-per-round:** assert the miner/planner is invoked exactly once per run (call-count == 1), not per SCREEN/PROMOTE candidate; if an LLM planner is used, assert its history block carries `cache_control:{"type":"ephemeral"}` and its tokens drained into the cost tracker.
  - No-history fallback: empty store → enumeration == today's fixed `_SEED_UNIVERSE` order (J-12/J-13/J-14 preserved); explicitly re-run/keep the existing `test_open_universe_*` and `test_max_configs_cap_*` and `test_pinned_path_unchanged_by_open_universe_addition` green.
  - Update the existing `test_open_universe_objective_and_history_scope_persisted` and `test_history_scope_defaults_to_none_when_omitted` **deliberately to the new effective semantics** (persistence still asserted; behaviour now asserted) — do NOT loosen them merely to pass; their stale "J-15/OUT" comments must be corrected.
  - Robust-best invariant: a historically-favoured family that promotes worse than another candidate is NOT selected as best (warm-start changes order, not selection).
- **Error cases:** unknown/garbage `history_scope` value → treated as a clean default (no 500); empty/corrupt prior session dir skipped without aborting the run (mining is best-effort and never hangs/raises out, mirroring the SCREEN/PROMOTE `except` discipline).

## NOTES

- **Evaluator-driven scope.** iter-4 eval (`runs/goal-session-auto-money-printer/iter-4/eval.md`) and the inlined evaluator log both pin iter-5 = J-15 at full depth, naming the deterministic SCREEN seed-order enumeration in `_run_staged_open_universe` as the injection point and "reuse the iter-3 durable file store read-only (no schema fork)". This spec follows that exactly.
- **Lessons applied:** iter-0 (read-only, J-02 not regressed — content-hash proof), iter-2 (off-event-loop file I/O via `asyncio.to_thread`, no timing guard, subprocess backtest seam unchanged), iter-3 (`would_exceed` / `max-configs`-vs-spend-cap distinction if a planner LLM call is added). The iter-1 reconciled-UI-test-headline caution is for the evaluator: cross-check the post-fix source + QA MODE-2, not the `ui-test-results.md` headline alone.
- **Outer-loop carryover (NOT iter-5 developer/source work).** Per the iter-4 evaluator + iter-4 lesson, iter-4's `blocked`/`closure_failed` was solely two transient UI-test-design stub artifacts from a `ui-test-design-phase.sh` CLI exit-1 — an artifact-completeness gate trip, not a journey/anti-goal/implementation failure. The outer loop (`run-goal.sh`/orchestrator) should run `./scripts/automation/ui-test-design-phase.sh goal-auto-money-printer-iter-4` then `./scripts/automation/phase-closure-check.sh goal-auto-money-printer-iter-4` to regenerate them. This is recorded here only so it is not lost; it implies **no** code/test/journey work in iter-5 and MUST NOT flip any journey/anti-goal verdict.
- **GOAL_ACHIEVED gate:** after J-15 passes, only J-16 remains failing — the agent rule forbids GOAL_ACHIEVED with any failing journey, so the evaluator should still CONTINUE to iter-6 (J-16) unless J-16 is independently demonstrated.
