# goal-financial_free-iter-6 Audit Report

**Date:** 2026-05-24
**Auditor:** Hard audit pass — skeptical, evidence-based
**Phase:** goal-financial_free-iter-6 (RE-LAND of J-15 — global-history warm start, opt-out-able)

---

## 1. Executive Verdict

**Verdict:** PASS

J-15 was re-landed correctly and — the single point of this iteration — **persisted in the real working tree**, not in a discarded worktree or a stale pytest cache. I independently re-verified the persistence gate (`git diff HEAD` = 7 files, all four required paths, `history_planner.py` present, `history_scope` grep matches both backend files, `status.json` populated, handoff matches diff) and re-ran the full backend suite against the live tree: **231 passed, 1 failed (the documented pre-existing `test_directions_cache` red only), 2 deselected.** The warm-start path is read-only, meta-only, prompt-cached, budgeted, bounded to the seed, single-scorer, secret-free, and opt-out-honoring — each verified by a tight hermetic test that exercises the real file store, not a mock that masks the behavior. All findings are OBSERVATION-level; no critical or important gaps remain, so no fixes were applied.

---

## 2. Findings

### Backend Findings

**B1 — OBSERVATION (observation): planner+citation gate is "any *in-seed* family has history", narrower than the spec's literal "any prior family"**
`auto_session.py:1053` — `if any(f in families for f in seed_families):` gates mining→planner→citation on at least one *seed* family having prior history, rather than any prior family at all. This is the refinement the reviewer already flagged (NOTE) and the dev documented. It is correct and defensible: the planner orders only the bounded seed, so a prior family outside the seed is uncitable and unpromotable; firing the (token-spending) planner with nothing in-seed to cite would burn budget for a no-op. It does **not** weaken J-15 acceptance — J-15's "first promoted family matches the prior top performer" requires that prior top family to be in-seed (otherwise it cannot be promoted from the bounded seed), so the acceptance scenario always satisfies this gate. No action needed.

**B2 — OBSERVATION (observation): `FamilyHistory.iteration_id` captured but unread**
`auto_session.py:430` — the dataclass records `iteration_id`, but the citation uses only `symbol`/`timeframe`/`session_name`/`score`. Harmless provenance; keeping or dropping it is equivalent. No action needed (do not fix OBSERVATION-level items).

**B3 — OBSERVATION (observation): theoretical double-accounting in the planner failure path is unreachable**
`auto_session.py:1212–1226` — the success path accounts planner usage after `plan_warmstart` returns, then calls `coerce_family_order`; the `except` path accounts it again. If `coerce_family_order` could raise *after* the success-path accounting, usage would be booked twice. In practice `coerce_family_order` (`auto_session.py:483`) is pure list processing that cannot raise on the inputs given, so exactly-once accounting holds in all reachable paths. Confirmed by `test_planner_token_usage_threaded_into_budget` (budget == exactly the planner spend, 1000 tokens). No action needed.

### Frontend Findings

**F1 — N/A (observation): backend-only, spec-justified**
Frontend Present: no. J-15's only user-visible surface is a new `WARM-START …` Activity-Log entry rendered through the **existing** `auto-run` entry branch (the same path J-14's SCREEN/PROMOTE entries use). `git diff --name-only HEAD` confirms **no** `apps/frontend/**` path is touched. The display aspect is proven at the canonical endpoint the UI polls (`read_activity_log` / `read_iteration_meta` → `GET /api/sessions/{id}.activityLog` / `.iterationHistory`) by `test_global_endpoint_layer_activity_log_and_iteration_family`. This is spec-mandated, not a shortcut.

### Test Findings

**T1 — OBSERVATION (observation): dev handoff states "20 hermetic J-15 tests"; the file actually contains 18**
`pytest --collect-only tests/test_history_warmstart.py` collects **18** tests (the targeted run `test_history_warmstart.py` + `test_auto_session_routes.py` = 42 passed, of which 4 are the new route tests). The handoff's "20" is a prose miscount; it does not affect the DoD (which requires the tests to pass, not a specific count). All 18 J-15 tests + 4 route tests pass. Documentation-only; left as-is per the do-not-fix-OBSERVATION rule.

**T2 — OBSERVATION (strength, not a gap): test quality is high and not accidental**
Assertions are exact, not loose: `test_mine_history_families_keeps_max_score_per_family` asserts the family score equals `scorer.score(hi)` via `pytest.approx`; `test_mining_is_meta_only_does_not_parse_full_iteration` monkeypatches `read_iteration_full` to raise and still finds the families (proving meta-only); `test_read_only_mining_leaves_prior_artifacts_byte_identical` snapshots and byte-compares the prior session tree before/after a `global` run; `test_pre_exhausted_budget_terminates_before_planner_and_screen` asserts 0 planner calls **and** 0 iteration dirs **and** 0 execute calls. The citation tests assert the real prior session name ("Run One"/"Prior Search") appears — which is only possible if the miner genuinely read run #1's persisted artifacts through the real `session_store`, so these are not accidental passes.

---

## 3. Domain Assessment

The core domain logic is correct and matches the spec's intent precisely.

- **Read-only, meta-only mining** (`mine_history_families`, `auto_session.py:431`): scans prior sessions via `derive_session_tabs` / `read_session_meta` / `list_iteration_dirs` / `read_iteration_meta` only; excludes the in-flight session (`sid == current_session_id`) and any still-running session (`auto_run status in ACTIVE_STATUSES`); scores each prior iteration with the **one supplied canonical `RobustScorer`** and keeps the per-family max; omits `-inf` (min-trades-floor) results. No write/mutate/delete; no `read_iteration_full`. Honors the "read-only mining of the existing store" anti-goal.
- **Cached planner** (`history_planner.py`): mirrors `InsightsGenerator` — `last_usage` side channel + Anthropic system prompt carrying `cache_control: {"type": "ephemeral"}` (line 180). It **does not score**; it only orders. Its output is filtered strictly to `seed_set` (line 214), so even a hallucinated symbol cannot fan the search outside the bounded seed — a second layer of the bounded-seed guarantee. Best-effort by contract: raises on no-key / SDK error / malformed JSON / empty order, so the controller falls back deterministically.
- **Warm-start ordering** (`_run_open_universe` + `_warm_start`, `auto_session.py:1040`/`1197`): on `global` with in-seed history, it mines → checks budget (terminates `budget-exhausted` before the planner and before SCREEN, J-13) → calls the planner ≤ once → threads usage into the **one** `BudgetTracker` → emits **one** secret-free citation → reorders the bounded seed so the historically-strongest in-seed family screens first → ranks PROMOTE by `(history_priority, screen_score)`. Best-marking remains `RobustScorer.select_best(promoted)`, WFE-gated — unchanged.
- **Opt-out is byte-for-byte today's behavior**: for `this-run` / omitted / any non-`global` value, `history_priority` stays `{}`, the warm-start branch is skipped entirely, and the PROMOTE ranking uses the original `else` key (`auto_session.py:1139–1142`), character-identical to HEAD. The J-12/J-13/J-14 hermetic tests (which set no `history_scope`) pass unchanged, and `test_omitted_history_scope_behaves_byte_equivalent_to_today` locks the SCREEN/PROMOTE order.
- **Coherence gate honored**: exactly one `class RobustScorer` (line 242) and one `class BudgetTracker` (line 127) exist in the codebase; the miner reuses the controller's instance (`test_warm_start_uses_single_robust_scorer_instance` asserts `ctrl.scorer is sentinel`). No second scoring or best-definition path.
- **Frozen contract respected**: `apps/backend/shared/contracts.py` is absent from the diff.

The request plumbing is sound: `history_scope` is validated server-side to `{"global","this-run"}` with a 422 on any other value (`auto_session_routes.py:114`), and None/omitted is coerced to the opt-out default in `_build_config` (`:214`) — defense-in-depth matching the controller's own non-`global`-is-opt-out treatment.

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| — | — | — | None. All findings are OBSERVATION-level; no critical or important issue required a fix. |

---

## 5. Recommended Next Step

**Proceed.** J-15 is complete, correct, well-tested, and — critically for this RE-LAND — persisted in the working tree (DoD-0 satisfied, independently re-verified). The iter-5 COHERENCE-WARN (contract-ahead-of-code) is resolved by the code now matching the already-approved blueprint Data-Contract row; no blueprint edit or re-approval is required. Only **J-16** (the overfit-gating multi-candidate leaderboard UI) remains before GOAL_ACHIEVED — and it is the one journey that genuinely requires new frontend work, so the next iteration should budget for real browser QA rather than the endpoint-layer substitute used here.

Non-blocking carry-forwards (unchanged, out of scope this iteration): the pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip`; the flaky pinned-path timing test `test_post_returns_before_loop_completes_and_get_stays_responsive`; the `auto_session.py` file size (~1.3k lines, future refactor); and the separable `browser-qa-phase.sh` offset-port health-probe fix.
