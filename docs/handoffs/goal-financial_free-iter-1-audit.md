# goal-financial_free-iter-1 Audit Report

**Date:** 2026-05-23
**Auditor:** Hard audit pass — skeptical, evidence-based (code traced, tests re-run)

---

## 1. Executive Verdict

**Verdict:** PASS_WITH_GAPS

The phase goal is genuinely achieved. A single `POST /api/auto-sessions` call starts a server-side, budget-bounded loop that reuses the injected `BacktestPipeline`, writes byte-shape-identical session/iteration/activity/suggestion artifacts through `session_store`, runs to a real terminal state (`criteria-met` / `budget-exhausted` / `stopped`), marks a WFE-gated robust best, and exposes a durable `autoRun` block on `GET /api/sessions/{id}`. I verified the integration seams against the real `BacktestPipeline`/`session_store` signatures (not just the fakes), traced the terminal state machine and budget enforcement in code, and **re-ran the suite myself**: 164 passed / 1 deselected / 1 pre-existing-unrelated failure; the 40 new + 39 invariant tests pass. The gaps are minor, documented, and either in-spec deferrals (token/USD hard cap → J-13; `/stop` journey → J-11; no UI → by design) or low-impact best-practice deviations — none compromise the phase goal.

---

## 2. Findings

### Backend Findings

**B1 — GAP (gap): Controller store I/O runs synchronously on the event loop**
`apps/backend/backend/auto_session.py:375-393` (`_save_auto_run`, `_stop_requested`) and the in-loop `session_store.write_iteration` calls (`auto_session.py:609`, `:643-644`, `:680`) execute synchronously on the asyncio event loop, unlike `session_routes.py` which wraps every store call in `await asyncio.to_thread(...)`. The dominant cost (LLM generation + backtest + walk-forward) **is** correctly `await`ed and guarded by the shared `app.state.backtest_semaphore` (`auto_session.py:468`), and `test_post_returns_before_loop_completes_and_get_stays_responsive` proves `GET /api/sessions` stays responsive while a run is active — so the non-blocking anti-goal's *measurable* requirement holds. But persisting an iteration node embeds the `result` (incl. `equity_curve`), so each write is a non-trivial synchronous block (tens of ms) repeated per iteration. This is a partial deviation from "MUST NOT block the API event loop." Matches the reviewer's MINOR note.
**Fix applied:** None. Deliberately not auto-fixed — see Domain Assessment. Wrapping these in `to_thread` would convert the currently event-loop-atomic read-modify-write in `_save_auto_run` into an interleaved RMW, **widening** the `stopRequested` race with `/stop` (B2). The correct home is iter-2 (J-10/J-11), where the stop journey is actually claimed and the autoRun-write concurrency model can be designed holistically (e.g., an async lock). Documented as an accepted limitation.

**B2 — OBSERVATION: Narrow TOCTOU race on the persisted `stopRequested` flag**
`_save_auto_run` (`auto_session.py:375-389`) reads the persisted `stopRequested`, then writes the whole `autoRun` block back to preserve it. The `/stop` endpoint (`auto_session_routes.py:248-261`) reads + writes via `asyncio.to_thread` (real OS threads, unlocked file writes). In principle the `/stop` thread's write can land between the controller's read and write, losing one stop request. Impact is low: the loop re-reads `_stop_requested()` at every round checkpoint, and the run terminates by budget regardless; `/stop` is explicitly J-11 infrastructure and the J-11 journey is not claimed this iteration. This is a property of the lock-free file store (pre-existing pattern), not a regression introduced here.

**B3 — OBSERVATION: Baseline iteration is not walk-forward validated, so an un-validated baseline can remain "best"**
The baseline is created with `wfv_enabled=False` (`auto_session.py:549`), giving `wfe=None`; the scorer's gate intentionally treats `wfe is None` as eligible (`auto_session.py:206`, tested at `test_wfe_gate_eligibility`). If every improvement candidate fails the WFE gate, the un-walk-forward-validated baseline stays the marked best. This faithfully matches the spec's Step-0 definition (baseline = generate→backtest→rating→insights, no WFV) and the in-browser reference being ported, and is documented in the dev handoff's Known Issues. Acceptable; noted for transparency.

### Frontend Findings

**F1 — N/A:** Backend-only iteration (`Frontend Present: no`). The created session renders through the existing session-open path because it appears in `GET /api/sessions` (`test_created_session_appears_immediately_in_sessions_list`) and exposes `autoRun` on `GET /api/sessions/{id}` (`session_routes.py:179-180`, `test_get_session_exposes_auto_run_block`). No new screens/nav — consistent with the blueprint (no IA/nav change). Correct scope.

### Test Findings

**T1 — OBSERVATION (good quality): Assertions are tight and prove the right behavior**
Spot-checked the load-bearing tests: `test_score_matches_inbrowser_formula` asserts the exact hand-computed `0.13`; `test_budget_exhausted_runs_exactly_max_iterations` pins `iterationsDone == 2`, exactly 3 persisted iterations, and the `wfv_enabled` call sequence `[False, True, True]` (proving baseline-no-WFV / candidates-WFV and no over-cap round); `test_best_is_wfe_gated_not_highest_raw_return` proves a 0.9-return / WFE-0.1 candidate is persisted-but-not-best while the 0.2 / WFE-0.6 one wins; `test_artifacts_are_byte_shape_compatible_with_manual_run` asserts the persisted `result`/`rating` are byte-identical to the canonical `result_to_dict`/`rating_to_dict`. These are exact-value, edge-inclusive assertions, not "something returned."

**T2 — OBSERVATION: Two minor coverage gaps (non-blocking)**
(a) The "no remaining suggestions → `budget-exhausted`" terminal branch (`auto_session.py:585-588`) has no dedicated test — the `FakePipeline` always returns ≥1 suggestion. It is a defensive/documented branch. (b) `test_no_secrets_in_artifacts` only exercises the happy path, so error-activity content (e.g. `auto_session.py:655`, `:660`) is not asserted secret-free; that content originates from pipeline validation/backtest errors, not auth, so the risk is low. Neither blocks the phase.

---

## 3. Domain Assessment

The core domain logic is correct and faithful to the spec:

- **Hard budget** — `BudgetTracker` is frozen (`@dataclass(frozen=True)`, `auto_session.py:101`), "increment" returns new instances, and `exceeded()` is checked at the **top** of each round (`auto_session.py:574`) while `with_round_completed()` runs only **after** a round's candidates (`auto_session.py:612`). Traced: with `max_iterations=2`, exactly 2 rounds run and 3 iterations persist — the loop never starts "one more round" past a cap. Wall-clock is enforced at round boundaries, which is precisely "before starting each round" per the spec (not a mid-round interrupt).
- **Robust best** — `RobustScorer` ports the in-browser base formula and adds the spec-mandated `- 0.5·max_drawdown` penalty; eligibility correctly rejects under-min-trades (`-inf`), `margin_called`, and WFE-below-0.3 candidates (`auto_session.py:193-215`). `select_best` returns the highest-scoring **eligible** candidate. This is the single canonical "best" definition; metrics are read off the canonical `BacktestResult`/`WalkForwardResult` (no recomputation).
- **Terminal machine** — priority order targets→budget→stop→no-suggestions (`auto_session.py:566-588`) matches the spec; `criteria-met` only fires when the robust-best satisfies **every** supplied target (`targets_satisfied`, `auto_session.py:234-255`), and absent targets correctly never satisfy (run goes to budget). `_finish` always writes the final status + `bestIterationId`.
- **Same-artifacts guarantee** — the key engineering move: the manual SSE serializer was extracted verbatim to `result_serialization.py` and re-imported into `api.py` under its original private names (`api.py` diff confirms `execute_backtest` now calls the shared `_serialize_backtest_result`). The headless loop writes through the *same* `serialize_*` functions, so byte-shape identity is guaranteed by construction, not by parallel reimplementation. Verified the extraction is behavior-preserving (full session/walk-forward suite green) and that `shared/contracts.py` is untouched (not in `changed_files`).
- **Pipeline reuse / no bypass** — the controller only calls `pipeline.generate_strategy / execute_backtest / generate_insights` and obtains WFE via `execute_backtest(wfv_enabled=True)` (the canonical pipeline path). I confirmed `execute_backtest` really returns the 5-tuple `(result, errors, rating, timings, wf_result)` the controller unpacks (`pipeline.py:412`), and that all `session_store` functions used exist with matching signatures (`write_session_meta` confirmed to merge keys — supporting "no schema fork"). The 317s live smoke (key-gated, documented as passed) is the end-to-end proof the real seams line up.

On B1: I weighed applying the `to_thread` fix. Because it carries a real concurrency tradeoff (it widens B2's stop race) and the reviewer/QA both classed it non-blocking, I followed the auditor rule "fix surgical issues only; do not rewrite working implementations" and documented it instead. The implementation as shipped is materially correct and the anti-goal's observable requirement is satisfied.

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| — | — | — | None. No CRITICAL or IMPORTANT issues found. All findings are GAP/OBSERVATION level and documented above. |

---

## 5. Recommended Next Step

**Proceed.** The phase goal (J-07 start + J-09 terminal/best-marking) is achieved with strong, tight test coverage and verified live-pipeline reuse. Carry the following into iter-2 (J-08/J-10/J-11), where they belong:

1. **B1 + B2 together** — when wiring the in-browser Auto Run to this backend loop and claiming the stop journey, move the controller's `autoRun` reads/writes off the event loop *and* serialize them against `/stop` (an async lock or a single-writer pattern) so the non-blocking convention and the stop-flag integrity are both fully closed. They must be solved as one design.
2. The carried-forward `~245KB GET /api/sessions/{id}` `equity_curve` embed remains for the coherence-auditor's verdict; this iteration did not worsen it (the `autoRun` block is strings/ids/integer counters) and left lazy iteration loading intact — confirmed.
3. Optional: add a test for the "no remaining suggestions → budget-exhausted" branch and a secret-hygiene assertion on an error-injected run.

The single red (`test_directions_cache::test_write_and_read_full_round_trip`) is pre-existing, on an untouched module, and explicitly the only known red carried forward by the spec — not a blocker.
