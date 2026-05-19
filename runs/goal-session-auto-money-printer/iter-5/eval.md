# Iteration 5 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

J-15 — read-only global-history warm start + `history_scope` opt-out — is
genuinely and verifiably achieved as a deterministic surrogate (no LLM, the
spec's explicit core design). 15/16 Must-have journeys now pass; only J-16
remains failing by design (out of iter-5 scope; its invariant is preserved but
not demonstrated as a journey, so per the agent rule GOAL_ACHIEVED is
forbidden). No anti-goal violated; no regression. Suite independently re-run:
**200 passed / 1 pre-existing tolerated red**, zero new regressions vs iter-4.

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run a backtest from natural language | passing | passing (carried — code path not in 2-file diff; suite green) | reports/qa/goal-auto-money-printer-iter-2-evidence/TC-21-manual-backtest.png |
| J-02 Inspect and browse run history | passing | passing (re-verified live: prior session list+detail intact post-mining) | reports/qa/goal-auto-money-printer-iter-5-evidence/UT-11-prior-session-detail.png |
| J-03 Walk-forward validation | passing | passing (carried) | reports/qa/goal-auto-money-printer-iter-1-evidence/UT-14-wf-result.png |
| J-04 AI insights | passing | passing (carried) | reports/qa/goal-auto-money-printer-iter-4-evidence/UT-07-pinned-final-iter-insights-B1.png |
| J-05 Reference data loads | passing | passing (carried) | reports/qa/goal-auto-money-printer-iter-1-evidence/UT-15-legacy-autorun.png |
| J-06 Warm-cache re-run | passing | passing (carried) | reports/qa/goal-auto-money-printer-iter-1-evidence/UT-13-state.png |
| J-07 Headless pinned POST | passing | passing (pinned `else:` branch byte-untouched at source; TC-05 + UT-02 discovery) | reports/qa/goal-auto-money-printer-iter-5-qa.md#TC-05 |
| J-08 Track live in UI | passing | passing (re-verified live: UT-10 running→terminal without reload, no NaN, spend monotonic) | reports/qa/goal-auto-money-printer-iter-5-evidence/UT-10-autorunbar-terminal-warmstarted.png |
| J-09 Stop on target/budget; best marked | passing | passing (TC-02 best marked by robust over higher-raw; UT-10 terminal "budget reached") | reports/qa/goal-auto-money-printer-iter-5-qa.md#TC-02 |
| J-10 Backend source of truth | passing | passing (re-verified live: UT-10 selected-while-running → terminal without browser driving; pinned-source byte-unchanged) | reports/qa/goal-auto-money-printer-iter-5-evidence/UT-10-autorunbar-terminal-warmstarted.png |
| J-11 Stop a running session | passing | passing (cancellation registry/source untouched in diff; not exercised this iter) | reports/qa/goal-auto-money-printer-iter-4-qa.md#TC-05 |
| J-12 Open-universe ≥2 configs | passing | passing (re-verified live: TC-07 4 distinct SCREEN configs across all open runs) | reports/qa/goal-auto-money-printer-iter-5-evidence/TC-06-run2-warmstart-citation.png |
| J-13 Hard budget enforced | passing | passing (re-verified live: UT-10 `14,3xx tok · $0.0105 · 2 cfg` + budget-reached, no NaN, durable) | reports/qa/goal-auto-money-printer-iter-5-evidence/UT-10-autorunbar-terminal-warmstarted.png |
| J-14 SCREEN→PROMOTE staged | passing | passing (re-verified live: TC-07 SCREEN 1-4 → PROMOTE feed) | reports/qa/goal-auto-money-printer-iter-5-evidence/TC-06-run2-warmstart-citation.png |
| J-15 Learns from global history + opt-out | **failing** | **passing** (PRIMARY — citation visible on global, absent on this-run, ETH/USDT 4h-first reorder vs BTC/USDT 4h-first fixed) | reports/qa/goal-auto-money-printer-iter-5-evidence/TC-06-run2-warmstart-citation.png |
| J-16 Robust objective gates overfit | failing | failing (out of iter-5 scope; invariant preserved but not demonstrated as a journey) | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |

## Anti-goal Check

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| Read-only mining (no mutation of prior artifacts; `history_scope` opt-out honoured) | OK | **Structural proof**: write-primitive scan over the full added `auto_session.py` diff finds ZERO `open(...w`/`json.dump`/`unlink`/`rename`/`shutil`/`derive_session_tabs` calls — only `append_activity_entries` + `_update_autorun` on the *current* session. Corroborated by live 38-file content+mtime hash byte-identical pre/post mine (TC-11) + unit `test_history_mining_is_read_only_no_prior_artifact_mutation` + UT-11 (S-1 detail intact, values match). Opt-out: `_resolve_history_scope` only strips/matches `"this-run"`; UT-06 BTC/USDT 4h-first fixed seed + 0 citations vs UT-03 ETH/USDT 4h-first reorder + 1 citation. |
| Prompt-caching / history MUST NOT be re-sent uncached every round | OK | **Structurally satisfied without LLM**: no `messages.create`/`chat.completions`/`client.`/`cache_control` anywhere in the diff (deterministic surrogate, spec's explicit core design). Once-per-run guaranteed: `_warm_start_configs` called exactly once at `auto_session.py:1538` before SCREEN loop, off-thread via `asyncio.to_thread(_mine_history,…)`; unit `test_warm_start_mined_exactly_once_per_run` asserts call-count == 1. The spec itself endorses this satisfaction (lines 38 + 58). |
| Bounded-seed permutation only; MUST NOT fan out across exchange | OK | `_reorder_configs` is `sorted(enumerate(configs), key=…)` of the same list — output is a strict permutation of `_SEED_UNIVERSE`. Unit `test_reorder_configs_is_stable_bounded_permutation` asserts `set(order) == set(_SEED_UNIVERSE)` and `len == len`. |
| No new infrastructure (no Celery/Redis/DB/broker/vector store) | OK | Diff imports nothing new; only stdlib + existing `session_store` + `_activity`/`asyncio.to_thread`. |
| Same artifacts / no schema fork / UI-indistinguishable from manual | OK | Citation via existing `session_store.append_activity_entries`; `effectiveHistoryScope` is an **additive** key via the existing `_update_autorun` (mirrors iter-4's additive `stage`). UT-08 byte-identical DOM (row wrapper, icon, text-span classes match SCREEN row exactly); UT-04 renders ungrouped at top of feed via existing `ActivityLog.groupByIteration`; **zero frontend code change**. |
| Robust-best by walk-forward OOS / WFE-gated (warm-start does not bias selection) | OK | `select_best`/`robust_score` over promoted untouched (diff confirms). Unit `test_warm_start_changes_order_not_robust_best_selection` proves history-favoured family is screened+promoted first but NOT selected best when its WFE=0; live TC-02 corroborates (warm-start ETH/USDT 4h screened first; BTC/USDT 4h promoted-best by Sharpe 0.34). |
| Identical strategies not re-generated/re-backtested; cache reused | OK | Code-hash dedup + Parquet reuse untouched (diff). Warm-start only reorders the SCREEN enumeration, then the existing dedup paths run as before. |
| Hard budget (ai-tokens AND usd AND max-configs AND wall-clock); MUST NOT loop past cap | OK | Cost tracker / `_SPEND_CAPS` / `would_exceed` / `max-configs` vs spend-cap distinction unchanged (no diff to `cost_tracker.py`, no LLM tokens added). |
| `autoRun` status durable / survives reload | OK | `_update_autorun` calls write to durable session.json (existing path). Diff adds only the `effectiveHistoryScope` key. UT-10 across-reload-coherent terminal observed. |
| No second in-browser iterate loop | OK | Zero frontend diff (`apps/frontend/*` git diff empty); UT-08 confirms no new component/badge/button. |
| Reuses BacktestPipeline / not bypass sandbox or engine | OK | `pipeline.py`/`sandbox.py`/`backtest/`/`contracts.py`/`session_store.py` git diff **empty** (independently verified). Backtest subprocess seam unchanged. |
| Open-universe started from bounded seed (no exchange fan-out) | OK | `_SEED_UNIVERSE` unchanged (6 entries); warm-start returns a permutation of the same set. |
| Cheap SCREEN MUST NOT run WF or strongest model | OK | Staged SCREEN→PROMOTE separation from iter-4 untouched (no diff to that path); TC-07 staged feed observed live. |
| Event-loop non-blocking | OK | Mining offloaded via `asyncio.to_thread(_mine_history,…)` (iter-2 lesson honoured); citation append also `asyncio.to_thread`. Backtest subprocess seam unchanged. |
| `GET /api/sessions/{id}` MUST NOT eagerly parse iteration full payloads | OK | Mining is a separate one-time server-side read at run start (line 1538), not in the list/open path. The mine deliberately enumerates `BASE_DIR/"live"` directly to avoid calling `derive_session_tabs` (which would write `_index.json`). |
| `BACKTEST_STORE_DIR` MUST NOT default to `/tmp` | OK | QA-runner using `.data/backtests` (durable, not `/tmp`); store correctly honoured (in fact this is why UT-07 empty-store could not be live-reproduced — the deterministic isolated-store unit test compensates exactly). |
| `shared/contracts.py` frozen-dataclasses not mutated | OK | `git diff HEAD -- apps/backend/shared/contracts.py` empty (independently verified). |
| No API keys / secrets in artifacts / activity log | OK | Citation is plain operator language (`"Warm start (global history): prioritising X — prior best robust Y across N prior sessions"`); QA 0 secret matches across all warm-started artifacts incl. the citation. |

## Next-Step Recommendation

**iter-6 = J-16 at full depth.** J-16 ("Robust objective gates overfit") is the
only remaining failing journey. Its acceptance is that the marked best
satisfies WFE ≥ threshold and the min-trades floor and its score derives from
walk-forward OOS — and that a higher raw-return but WFE-failing or
over-leveraged candidate is **visibly not** selected as best (leaderboard /
activity log). The robust-best invariant is *preserved* in iter-5 (warm-start
changes SCREEN order, never selection — proven by source + unit + TC-02 live
corroboration), but J-16 is a **demonstration** journey: it requires an
open-universe stress run with deliberately overfit-tempting candidates so the
leaderboard / activity-feed evidence shows a higher-raw / WFE-failing
candidate being marked NOT-best.

Full pipeline depth — consistent with every Optimizer-layer iteration (iter-2
through iter-5) — since J-16 is the last journey, activates the robust-best
anti-goal as a demonstrated journey, and gates GOAL_ACHIEVED.

**Outer-loop, not iter-6 developer work:** the recorded iter-4 closure
carryover — regenerate the two transient `ui-test-design-phase.sh`
stub artifacts for `goal-auto-money-printer-iter-4` via
`./scripts/automation/ui-test-design-phase.sh goal-auto-money-printer-iter-4`
then `./scripts/automation/phase-closure-check.sh goal-auto-money-printer-iter-4`
— remains orchestrator/outer-loop work. It does not flip any journey or
anti-goal verdict and must not consume iter-6 source/test/journey budget.

## Halt Justification

N/A — verdict is CONTINUE, not a halt.
