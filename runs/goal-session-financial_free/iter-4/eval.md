# Iteration 4 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

J-14 (staged SCREEN→PROMOTE cost-tiering for the open-universe search) is **newly passing** — verified independently, not on trust. The open-universe loop now SCREENs the budget-bounded seed configs cheaply (`cheapest_model()`, `wfv_enabled=False`), ranks them by the **one** canonical `RobustScorer`, PROMOTEs only the top-`k` (`DEFAULT_PROMOTE_K=1`, k<N) to a stronger model + walk-forward, and marks best from the PROMOTED candidates only — all as pure orchestration over the existing pipeline/scorer/store with **zero** `contracts.py`, endpoint (see scope note), page, route, request-field, or datastore change. Coherence = COHERENCE-PASS, so no structural veto. Not GOAL_ACHIEVED (J-15, J-16 still failing); not REGRESSION (nothing regressed, no critical anti-goal); not STALLED (J-14 newly passing, clear J-15→J-16 roadmap).

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 | already_passing | already_passing (no-regression) | backtest/data paths not in diff; full suite green (evaluator re-run 209 passed) |
| J-02 | already_passing | already_passing (no-regression) | lazy list/open path untouched; eager-load verdict still resolved (not re-litigated) |
| J-03 | already_passing | already_passing (no-regression) | `walk_forward.py` untouched; WFE-gated scorer exercised by promote best-selection tests |
| J-04 | already_passing | already_passing (no-regression) | insights path unchanged; open-universe carries `insights:null` (UI-handled) |
| J-05 | already_passing | already_passing (no-regression) | `/api/symbols`+`/api/timeframes` paths unchanged; iter-3 real-pixel render still valid |
| J-06 | already_passing | already_passing (no-regression) | Parquet warm-cache path untouched; cache reused across SCREEN/PROMOTE configs |
| J-07 | passing | passing (re-verified) | pinned path `_run_inner` byte-untouched; `test_pinned_path_unchanged` green; restructure scoped to `_run_open_universe` |
| J-08 | passing | passing (endpoint; pixel debt 4th carry-forward) | `J08-live-counter-progression.json`: configs 0→1→2→3, tokens 0→9913, usd→$0.0061 across 12 polls, no reload. **Pixel NOT captured (FE down).** |
| J-09 | passing | passing (re-verified) | terminal stop-reason + WFE-gated best logic intact (`select_best(promoted)`); pinned path untouched |
| J-10 | passing | passing (endpoint; pixel debt 4th carry-forward) | `J10-reload-refetch.json`: re-fetch after termination returns identical persisted `autoRun` terminal state. **Pixel NOT captured (FE down).** |
| J-11 | passing | passing (re-verified) | `..._stop_request_transitions_to_stopped_mid_screen` + `..._stop_during_promote_preserves_best` green; B1+B2 preserved |
| J-12 | passing | passing (re-verified, most-at-risk) | live: 3 distinct configs (BTC/1h, ETH/1h, BTC/4h) as nodes, terminal in budget; `test_open_universe_explores_distinct_configs_and_marks_best` preserves ≥2-distinct invariant under staged flow |
| J-13 | passing | passing (re-verified, most-at-risk) | `exceeded()` byte-unchanged (J-13 tests depend on it); `cost_exceeded()` added separately; live halted `budget-exhausted` at configs 3/3, spend ≤ cap; token/USD cap tests green |
| **J-14** | **failing** | **passing (NEW)** | hermetic: 16 staged tests incl. stage-routing `execute_calls.wfv==[F,F,F,T]`, k=1<3, best-WFE-gated-from-promoted-only (positive+negative), stop-mid-screen/promote, degenerate-single, promote-fail-non-fatal, 5× `cost_exceeded`. Live (real gpt-5.4-mini SCREEN + claude-haiku-4-5 PROMOTE): `J14-screen-promote-evidence.json` / `J14-final-session-snapshot.json`. Coherence PASS, Review PASS_WITH_NOTES, QA PASS. |
| J-15 | failing | failing (out of scope) | not built this iter (deferred); SCREEN ordering is deterministic seed order, not history-informed |
| J-16 | failing | failing (out of scope) | not built this iter; single WFE-gated best badge exists, multi-candidate leaderboard is J-16 |

**Independent verification performed (not trusting the handoff):** re-ran the full hermetic suite → **209 passed / 1 known pre-existing red (`test_directions_cache`, out-of-scope, untouched module) / 2 deselected** (matches QA + reviewer exactly); read the SCREEN→PROMOTE flow (`auto_session.py:855-982`) and confirmed it matches every claim; read both best-marking tests (`test_auto_session.py:569,616`) and confirmed the positive best-marking + WFE-gating paths are asserted with the FakePipeline producing real WF; confirmed `cheapest_model()` is a single-source min-rate helper; confirmed `contracts.py` is NOT in the diff; confirmed the `api.py` change is solely a benign `GET /health` liveness probe.

## Anti-goal Check

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| Cheap SCREEN MUST NOT run walk-forward or strongest model | OK | `wfv_enabled=False`+`cheapest_model()` on SCREEN; test asserts `execute_calls.wfv==[F,F,F,T]`; live SCREEN nodes `modelUsed=gpt-5.4-mini`, `wfStatus=None` |
| Best WFE-gated from PROMOTED only (not highest raw return / over-leveraged) | OK | `select_best(promoted)`; screened-only never in candidate list; `test_..._best_is_wfe_gated_not_highest_return` asserts the 0.9 screened node is never best |
| Reuse `BacktestPipeline` / sandbox / deterministic engine | OK | `_create_iteration` reused unchanged; lookahead/determinism/sandbox invariant tests in the 209-passed run |
| Bounded seed universe, no full-exchange fan-out | OK | `seed_universe_configs(base, max_configs)`, `SEED_UNIVERSE_MAX` unchanged; live used BTC/ETH × 1h/4h |
| Code-hash dedup + Parquet cache reuse across configs | OK | `_create_iteration` reused; SCREEN(wfv=F)/PROMOTE(wfv=T) distinct dedup keys (added fidelity, not a re-backtest) |
| Hard budget (tokens/USD/configs/wall-clock), immutable tracker, no "one more round" | OK | `exceeded()` gates SCREEN, `cost_exceeded()` (cost-caps only) gates PROMOTE; immutable `with_*`; live halted `budget-exhausted` ≤ cap |
| Same file store, no schema fork, headless indistinguishable from manual | OK | `_build_node`/`_persist_new`/`write_iteration`/`append_activity_entries` reused; `auto-run` entry type reused; coherence PASS |
| `autoRun` persisted, survives restart/reload | OK | `_save_auto_run` off-loop; re-fetch returns persisted terminal state (`J10-reload-refetch.json`) |
| No second in-browser iterate loop; loop only in backend | OK | zero FE code change; in-browser loop removed iter-2, not reintroduced |
| No new infra (Celery/Redis/DB/SQLite/broker/vector-store) | OK | none added; optimizer state in existing file store |
| No secrets in activity log / session artifacts | OK | tests assert no `api_key`/`sk-`; live evidence entries carry none |
| Frozen `contracts.py` not mutated | OK | not in diff (verified) |
| Event loop non-blocking; one-backtest-per-worker semaphore | OK | store I/O off-loop, backtests semaphore-guarded, B1+B2 preserved |
| No lookahead / nondeterminism / sandbox escape | OK | invariant tests green in 209-passed run |
| eager-parse of per-iteration payloads on list/open | OK | list/open path untouched (resolved iter-1, not re-litigated) |
| LLM-planner/history prompt-caching | N/A | J-15 deferred; SCREEN ordering is deterministic seed order (spec-correct this iter) |

**No anti-goal violations.** One **scope note** (not a violation): the spec said the iteration "introduces no new endpoint," but a `GET /health` static liveness probe was added to `api.py` (mirrors `/api/health`, used by the dev-chain pollers). The coherence-auditor flagged it advisory-only — it serves no Data-Contract value and is not a UI/nav route, so zero coherence impact. It is also absent from the dev handoff "Files Changed" and `status.json.changed_files` — a documentation gap the release-manager should reconcile.

## Next-Step Recommendation

Proceed to **J-15 (learns from global history / warm start, opt-out-able) at full depth**. J-15 replaces this iteration's deterministic seed-universe SCREEN ordering with a history-informed plan: read-only mining of prior sessions in the existing file store, a cached LLM-planner that cites prior-session performance, with `history_scope: "global"|"this-run"` honored as the opt-out. Enforce the anti-goals that bind J-15 specifically: history mining MUST be **read-only** (never mutate/delete prior artifacts), the planner/leaderboard context MUST use **prompt caching** (not re-sent uncached each round), and the `history_scope` opt-out MUST be honored (run #3 shows no cross-run citation). It needs the full pipeline (new cross-session surface, new failure modes, browser-qa on the planner-decision activity entries). Then J-16 (multi-candidate overfit-gating leaderboard UI) visualizes the promoted, WFE-gated candidates this iteration now produces.

**Decisively address the now-4×-recurring live-pixel gap — but fix the ROOT CAUSE, not the instruction.** iter-4's spec mandated clearing the J-08/J-10/J-14 pixel debt and stated "services down is NOT an acceptable reason this time" — yet the browser-qa-agent SKIPPED again ("frontend not running") and QA's own FE (`:3692`) died mid-window (no listener from poll 3). Re-issuing the same "try harder" instruction a 5th time will not work: the failure mode is the **harness frontend lifecycle** (the FE is not started, or is torn down/crashes within the browser-qa/QA window), not agent effort. The next iteration should either (a) fix `browser-qa-phase.sh` so the frontend is started and **stays serving for the entire window** (health-re-probed, on an uncontended tab) before any pixel claim is required, or (b) formally accept the endpoint-layer proof + zero-FE-change code confirmation as sufficient for these display-only journeys and stop carrying it as "debt." Since J-15/J-16 add genuinely new UI (planner-decision entries, leaderboard), one more genuine pixel attempt against a stabilized FE is warranted.

**Non-blocking carry-forward (do NOT re-litigate resolved items):** pre-existing red `test_directions_cache` (untouched nice-to-have, Capability #10); de-flake `test_post_returns_before_loop_completes_and_get_stays_responsive`; reviewer NOTEs (the `incredible_auto_dev/.../demo*.sh` framework-tooling changes are not part of J-14 — release-manager should exclude/note them; the cosmetic "PROMOTE header before the boundary cost-check" log ordering; reconcile the `/health` addition into the handoff/changed_files). The eager-load anti-goal (resolved iter-1), the in-browser scorer/loop removal (done iter-2), and the single-`RobustScorer`/single-`BudgetTracker` coherence gate (re-confirmed iter-4) are settled — do not revisit.
