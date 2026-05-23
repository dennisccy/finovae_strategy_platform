# Iteration 2 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

Layer-1 is **complete**: the backend auto-session loop is now the only Auto Run engine. J-08, J-10, and J-11 move from `failing` → `passing` — the in-browser iterate loop and duplicate `scoreIteration` are deleted (grep-verified), "Auto Run"/"Stop" are rewired to the existing backend command endpoints, and the persisted `autoRun` block is surfaced live in the new status strip. The spec-mandated B1+B2 critical gate passes (verified in the actual code, not just claimed): the controller's off-loop `autoRun` read-modify-write is held inside a per-session `asyncio.Lock` that `/stop` shares, and the new race regression test is green. Coherence is PASS (it also closes the iter-1 §C.1 duplicate-scorer advisory). Not GOAL_ACHIEVED — Layer-2 (J-12…J-16) is entirely unbuilt.

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run a backtest from NL | already_passing | already_passing (no regression) | `useBacktest.ts` builds/lints clean; manual helpers intact (grep, QA TC-01/TC-15); data endpoints respond. Live-pixel re-check deferred (FE down). |
| J-02 Browse run history | already_passing | already_passing (no regression) | QA TC-15: `GET /api/sessions`=200, lazy `…/iterations/{id}`=200; lazy-load path preserved. |
| J-03 Walk-forward | already_passing | already_passing (no regression) | Untouched code path; suite green (my run + QA TC-03). |
| J-04 AI insights | already_passing | already_passing (no regression) | Untouched; suite green. |
| J-05 Reference data loads | already_passing | already_passing (no regression) | Controls untouched; build clean. Live-pixel re-check deferred (FE down). |
| J-06 Warm-cache re-run | already_passing | already_passing (no regression) | Parquet loader untouched; suite green. |
| J-07 Start headless session (API) | passing | **passing** (re-verified) | QA TC-06 live: `POST /api/auto-sessions` → 200 + `sessionId`, appears in `GET /api/sessions`. My run: route/criteria tests green. |
| **J-08 Track run live in UI** | failing | **passing** (via sanctioned fallback) | QA TC-07 live poll: `autoRun.status` advanced `running → budget-exhausted`, nodes grew 1→11 with summary metrics, `bestIterationId` set live. Poll wiring `apiLoadSession`@2500ms→terminal (`useBacktest.ts:766-780`); strip in Right/Iterations home (coherence verified). **Live-pixel confirmation owed** (browser-qa SKIPPED). |
| **J-09 Terminal stop-reason + WFE best** | passing | **passing** (re-verified) | QA TC-10: `status=budget-exhausted`, `bestIterationId` set by backend `RobustScorer`. My run: `test_best_is_wfe_gated_not_highest_raw_return` + budget/criteria tests green. |
| **J-10 Backend single source of truth / survives reload** | failing | **passing** | QA TC-06/TC-08: run completed **entirely server-side with no browser attached** (strictly dominates reload-survival); in-browser loop + `scoreIteration` removed (my grep: NONE FOUND); running indicator derived from polled `autoRun.status`, not a local flag (`useBacktest.ts:535/766`). Reload-pixel step not captured (FE down). |
| **J-11 Stop a running session** | failing | **passing** | QA TC-09 live: `POST …/stop` → 200, next poll `status=stopped`, `stopRequested=True`, nodes frozen at 1, best retained, still `stopped` +10s. Acceptance allows the API stop path; `stopAutoRun` rewired to `/stop`. B1+B2 race test green (my run). |
| J-12 Open-universe run | failing | failing (Layer-2, not built) | QA TC-14: open-universe `POST` correctly rejected 400 (Layer-2 boundary preserved). |
| J-13 Hard token/USD budget | failing | failing (Layer-2, not built) | `max_iterations` is primary terminator; hard token/USD cap is J-13. |
| J-14 Staged SCREEN→PROMOTE | failing | failing (Layer-2, not built) | Not in scope. |
| J-15 Global-history warm start | failing | failing (Layer-2, not built) | Not in scope. |
| J-16 Robust objective gates overfit | failing | failing (Layer-2, not built) | Scorer exists as canonical best; leaderboard/overfit-gating UI is J-16. |

## Anti-goal Check

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| **`to_thread` on `autoRun` writes must be serialized vs `/stop` (spec FAIL condition)** | OK | **Critical gate PASS.** `auto_session.py:409-422`: `async with self._lock:` wraps the off-loop read (410) + write (421) and preserves `stopRequested` (415). `auto_session_routes.py:278-292`: `/stop` acquires the **same shared lock** from `AutoSessionHandle` and does its RMW off-loop inside it. Regression test `test_stop_racing_save_auto_run_is_not_dropped` green in my own run; dev verified it goes red without the shared lock. |
| Iterate loop only in backend; no second in-browser loop | OK | `grep scoreIteration / autoRunStopRef / autoRunIterationIdsRef` → NONE FOUND (my run). Coherence §A confirms. |
| `autoRun` persisted to durable store; survives reload/restart | OK | Written to `session.json` `autoRun` block; running indicator derived from polled status (no local flag); startup reconciliation intact (iter-1 tests green). |
| Background job must not block event loop | OK | `test_post_returns_before_loop_completes_and_get_stays_responsive` green (QA TC-05, my run). |
| Same file store / no schema fork / no parallel store | OK | Coherence §A: same `session.json` autoRun block; `contracts.py` untouched (my diff: empty). |
| `GET /api/sessions/{id}` poll must not eager-parse heavy payloads | OK | Coherence TC-11: `mergePolledSession` appends lightweight nodes, preserves heavy fields lazily; no new status endpoint. |
| Reuse `BacktestPipeline`; no sandbox/engine bypass | OK | Loop body untouched; `test_sandbox`/`test_lookahead`/`test_determinism` green in my run. |
| Hard budget honored (no unbounded loop) | OK | `max_iterations` primary terminator + bounded `max_wall_clock_sec`; `budget-exhausted` reached in QA TC-07/TC-10. |
| No new external infra (Celery/Redis/DB/broker/vector-store) | OK | My diff grep: NONE. |
| No hardcoded secrets in source | OK | My diff grep: NONE. |
| `shared/contracts.py` frozen | OK | `git diff HEAD` empty for that file. |

No anti-goal violation introduced. Coherence audit: **COHERENCE-PASS** (no structural veto; net coherence improvement — closes iter-1 §C.1).

## Next-Step Recommendation

**Begin Layer-2 (J-12…J-16) at full depth** — the most complex slice of the goal and the one with a real new UI surface:
- **J-12** open-universe search from a **bounded seed universe** (anti-goal: no blind exchange-wide fan-out); ≥2 distinct configs as iterations; best marked by robust score.
- **J-13** hard token/USD budget enforced by the **immutable cost tracker** — wire real token accounting from the pipeline; `stop reason = budget-exhausted`; spend ≤ cap (one-call tolerance) visible in the status block; no iterations after the cap.
- **J-14** staged **SCREEN → PROMOTE** (cheap-first); walk-forward + strong model only on promoted top-k (k < screened) — visible in the activity log.
- **J-15** **global-history warm start**, read-only mining of the existing store, `history_scope` opt-out honored; LLM-planner/history context must use **prompt caching**.
- **J-16** robust-objective overfit gating surfaced in a **leaderboard** (WFE ≥ threshold + min-trades floor; a higher-raw-return but WFE-failing/over-leveraged candidate must NOT be marked best).

**Carry-forward (must clear, non-blocking now):**
1. **Live-pixel UI debt.** J-08 (live strip + cards streaming without reload), J-10 (reload-mid-run survival), and the J-01/J-05 manual regressions were verified via the spec-sanctioned backend-endpoint + code fallback only — the dedicated browser-qa-agent returned SKIPPED because the Vite dev server went down mid-window. Layer-2 adds UI (the leaderboard), so browser-QA will run again: **ensure the frontend is reliably serving and capture real pixels for J-08/J-10 + the manual regressions** in that window.
2. Pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (nice-to-have Capability #10, untouched module) — not a regression; opportunistic fix only.
3. Coherence advisory tidies (non-blocking): add `error` to the blueprint run-state enum row; "rounds vs iterations" label is tooltip-clarified and acceptable.

Do **not** re-litigate the eager-load anti-goal (resolved iter-1) or the in-browser-scorer removal (done this iter).

## Halt Justification (if halting)

N/A — not halting. CONTINUE: three target journeys newly passing (Layer-1 done), no regressions, no critical anti-goal violation, coherence PASS, and a clear, tractable Layer-2 roadmap remains (J-12…J-16 still `failing`).
