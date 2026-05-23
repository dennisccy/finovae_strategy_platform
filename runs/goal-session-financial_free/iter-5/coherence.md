**Verdict:** COHERENCE-WARN

# Coherence Audit — goal-financial_free-iter-5 (J-15 global-history warm start)

Audited the iteration diff against the session blueprint (Information Architecture + Data Contract).
Snapshot SHA `ccc06b214a6f99b5c78d2a5db95e1685fa7d5097` (a WIP commit whose parent is iter-4 `9e977ab`,
capturing the working tree at the start of iter-5).

**No objective Step-1 (Data Contract) or Step-2 (Information Architecture) violation is present** — because
the diff contains **no product source code at all**. There is therefore no new computation path, endpoint,
displayed value, route, nav entry, or shell to fail on. The blueprint edit is a clean, additive, internally
consistent Notes change. → not COHERENCE-FAIL.

This is **WARN, not PASS**, because of one significant advisory: the iteration's contract (the blueprint) was
advanced to describe J-15 as landed while the implementing code is **absent from the working tree** — a
contract-vs-reality mismatch the goal-evaluator must catch. Details below.

---

## What is actually in the diff

`git diff <snapshot>` / `git diff HEAD` (verified — HEAD is still iter-4 `9e977ab`, reflog shows no reset):

| File | Nature |
|---|---|
| `runs/goal-session-financial_free/state/blueprint.md` | Additive Notes edit (decomposer pre-registration) — see Step 1 |
| `runs/goal-session-financial_free/telemetry.jsonl` | Harness bookkeeping (not product) |
| `runs/goal-session-financial_free/trace/.next-step`, `trace/trace.jsonl` | Harness bookkeeping (not product) |
| `docs/phases/goal-financial_free-iter-5.md` (untracked) | The iteration spec |
| `runs/goal-financial_free-iter-5/`, `runs/goal-session-financial_free/iter-5/` (untracked) | Bookkeeping (`status.json`, `snapshot-sha`) |

**Zero `apps/backend/**` or `apps/frontend/**` changes.** No product code, no tests, no dev handoff.

## Step 1 — Data Contract check → PASS (no violation)

- The spec declares **"Data-contract additions: None (no new served/displayed value)"** and J-15 is meant to
  reuse the one `RobustScorer` + one `BudgetTracker` and surface only as cited text inside the existing
  `auto-run` Activity-Log entry. Consistent with the contract by design.
- The blueprint's open-universe row (`runs/.../state/blueprint.md:74`) gained an additive Notes sentence
  describing the J-15 read-only, prompt-cached, opt-out-able warm start, explicitly: *"scored by the **one**
  `RobustScorer` … tokens threaded into the one `BudgetTracker` … no new value, no new endpoint, no parallel
  store."* This is exactly the additive Notes edit the spec authorized — no new value registered, no duplicate
  concept, no second scorer/budget path introduced in the contract.
- Because the diff contains **no new function, service, or endpoint**, there is no duplicate-computation and no
  non-canonical-source violation to cite. I cannot point at offending `file:line` code (the prerequisite for a
  FAIL), so per the methodology this is not a FAIL.

## Step 2 — Information Architecture check → PASS (no violation)

- The spec is **backend-only** ("Frontend Present: no … zero new FE code") and reuses the existing `auto-run`
  Activity-Log render branch. J-15's canonical home already exists in the IA
  ("J-15 Warm start from global history + opt-out → Activity Log planner-decision entries → Left — Activity Log").
- The diff introduces **no new route, page, sidebar entry, or parallel shell**. No hidden feature, no duplicate
  home, no >2-click reachability concern — there is no new surface at all. Not a FAIL.

## Step 3 — Advisory observations (WARN — does not block the goal)

1. **[PRIMARY — for the goal-evaluator] The J-15 implementation named in the spec is absent from this working
   tree.** Verified:
   - `apps/backend/strategy/history_planner.py` — **missing**.
   - No `mine_history_families` / `history_scope` / `plan_warmstart` / `WARM-START` in `auto_session.py`,
     `auto_session_routes.py`, or `pipeline.py` (full-tree grep of `apps/` returns hits **only** inside
     `.pytest_cache`).
   - Current `apps/backend/tests/test_auto_session.py` (1082 lines) and `apps/backend/backend/auto_session.py`
     contain **zero** history/warm/scope/mine tokens.
   - No dev handoff at `docs/handoffs/goal-financial_free-iter-5-dev.md`; `runs/goal-financial_free-iter-5/status.json`
     reports `current_step: "starting"`, `changed_files: []`, `tests_run: false`.

   **Strong evidence the work existed during the iteration and was then lost (not persisted into this tree):**
   `apps/backend/.pytest_cache/v/cache/nodeids` (mtime 2026-05-24 00:03, inside iter-5's window — started
   23:20) lists eight J-15 tests —
   `test_global_warm_start_reorders_and_cites_prior`, `test_warm_start_mined_exactly_once_per_run`,
   `test_resolve_history_scope_semantics`, `test_warm_start_changes_order_not_robust_best_selection`,
   `test_open_universe_objective_and_history_scope_persisted`, `test_default_omitted_history_scope_resolves_to_global`,
   `test_history_scope_defaults_to_none_when_omitted`, `test_garbage_history_scope_clean_default_no_crash` —
   while `lastfailed` contains **only** the known pre-existing red (`test_directions_cache.py::test_write_and_read_full_round_trip`),
   i.e. the J-15 tests had **passed**. The source files' mtimes (23:32–23:33) predate that passing run (00:03),
   consistent with the implementation having been built/tested in an ephemeral copy (e.g. a worktree) that was
   not merged back into this tree.

   **Why this is advisory, not a coherence FAIL:** completeness / "does J-15 work" is the goal-evaluator's
   mandate, not the coherence gate's (I FAIL only on objective IA/Data-Contract drift I can cite to offending
   code, and there is none). But the evaluator MUST be told, because the blueprint Notes (next item) could
   otherwise read as if J-15 shipped.

2. **[SECONDARY] Contract-vs-code mismatch — the blueprint now describes J-15 in completed tense while no code
   implements it.** `blueprint.md:74` ("(iter-5, J-15) Global-history warm start … *the controller mines prior
   sessions* …") and the footnote ("*iter-5 lands global-history warm start (J-15)* …") assert the capability as
   delivered. With the implementation absent, the coherence contract has moved ahead of the code. This is the
   decomposer's normal pre-registration pattern, so it is advisory — but it should be reconciled.

## Required follow-up (concrete, finite)

- **goal-evaluator:** evaluate J-15 against **actual code/endpoints**, NOT the blueprint Notes. Expect to find
  J-15 absent (no `history_scope` field on `POST /api/auto-sessions`, no warm-start `auto-run` citation entry,
  no `mine_history_families`) → this iteration is **not** GOAL_ACHIEVED for J-15; CONTINUE.
- **next dev pass:** re-land the J-15 work in **this** tree (the version captured in the pytest cache was not
  persisted): `history_scope` on `CreateAutoSessionRequest` + a `history_scope` field on the frozen
  `AutoSessionConfig`; `mine_history_families(...)` (read-only, meta-only); `strategy/history_planner.py` with the
  `cache_control: {"type": "ephemeral"}` marker, called at most once per run; warm-start ordering in
  `_run_open_universe`; and the eight tests above. Confirm with a `git diff` that shows `apps/backend/**` changes
  and a dev handoff at `docs/handoffs/goal-financial_free-iter-5-dev.md`.
- **optional tidy:** if J-15 will not land this iteration, change the blueprint's iter-5 Notes from completed to
  forward-looking tense so the contract does not assert an unbuilt capability.

## Scope note

Per my mandate I did not edit any source file and did not judge whether J-15 "works" — I only audited the diff
for IA + Data-Contract drift and recorded the coherence-relevant advisory (contract advanced past absent code).
No COHERENCE-FAIL is warranted because no objective Step-1/Step-2 violation can be traced to offending code in
the diff.
