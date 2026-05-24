**Verdict:** COHERENCE-PASS

# Coherence Audit — goal-financial_free-iter-6

- **Session:** financial_free | **Iteration:** 6 | **Iter name:** goal-financial_free-iter-6
- **Snapshot SHA:** `83547c89ee5ffe68194147923656fdba29fe18ae`
- **Scope of change:** backend-only (re-land of J-15 global-history warm start). UI surface map: `N/A — Backend-only phase (no UI surfaces affected)`.
- **Files in diff:** `apps/backend/backend/auto_session.py` (+274), `apps/backend/backend/auto_session_routes.py` (+14), `apps/backend/backend/pipeline.py` (+36), `apps/backend/strategy/history_planner.py` (new, +225), plus three test files. `shared/contracts.py` is NOT in the diff (frozen, untouched). No frontend file changed.

## Step 1 — Data Contract check (the "numbers don't match" gate) → PASS

The blueprint's Layer-2 open-universe Data-Contract row (`blueprint.md:74`) **already pre-registers this exact J-15 warm-start**: read-only, prompt-cached, opt-out-able, "reusing the one RobustScorer + one BudgetTracker," "no new value/endpoint." This iteration makes code match that contract. Each registered value was checked for duplicate computation / non-canonical source:

- **Robust objective score + best marker** (canonical: `RobustScorer` in `apps/backend/backend/auto_session.py`, served on `autoRun.bestIterationId` via `GET /api/sessions/{id}`). The most at-risk value here. The new miner `mine_history_families(current_session_id, scorer)` (`auto_session.py:435`) scores each prior family with `scorer.score(m)` using the **injected `self.scorer`** — the controller passes `self.scorer` at the call site (`auto_session.py:1054`), which is the single instance set in `__init__` (`self.scorer = scorer or RobustScorer()`, `auto_session.py:643`). The `IterationMetrics` it builds (`auto_session.py`) is the **existing canonical input dataclass** for `RobustScorer.score()` (`auto_session.py:226/262`), not a parallel structure. Grep of the diff confirms **no new `RobustScorer(...)` construction** anywhere. → No duplicate computation; one scorer, one best definition. Best-marking still `RobustScorer.select_best` over promoted, WFE-gated (unchanged).
- **Budget counters** (canonical: immutable `BudgetTracker`). Warm-start reuses the existing `self.budget` (`with_wall_clock`/`exceeded`/`_account_usage` at `auto_session.py:1059–1078`); the planner's real SDK token usage is threaded via `_account_usage(pipeline.last_planner_usage)` (`auto_session.py:1213`/`1219`). Grep confirms **no new `BudgetTracker(...)` construction**. → One authoritative tracker.
- **New served value / endpoint?** None. `auto_session_routes.py` adds only the `history_scope` field + validator to the existing `CreateAutoSessionRequest` — **no new route decorator** (grep for `@router/@app.(get|post|...)` in the diff returns nothing). The mined family leaderboard (`FamilyHistory`, `history_brief`) is a **transient in-memory** structure fed only to the planner prompt; it is never persisted to a store nor served by any endpoint. → No non-canonical source, no parallel store, no schema fork.
- **New displayed value?** None, consistent with the spec's "Data-contract additions: None." The warm-start emits ONE `_append_activity("auto-run", …)` entry (`auto_session.py:1244`) citing a robust score (`{h.score:+.4f}`). That score is the canonical `RobustScorer.score()` output **re-formatted into sentence text** — the explicit "re-format is fine" case, and the blueprint anticipates it ("surfaces only as cited text inside the existing `auto-run` Activity-Log entry"). It is served by the canonical `GET /api/sessions/{id}` → `activityLog`. The planner (`history_planner.py`) computes **no** metric — it only returns an ordering over the seed families and validates the result is a permutation of them (`history_planner.py:207–225`).

No Data Contract violation.

## Step 2 — Information Architecture check (the "where do I find it" gate) → PASS

- **New page/route/feature?** None. Backend-only; zero frontend files in the diff; UI surface map says "No UI surfaces affected."
- **Canonical home exists.** J-15's home is already in the IA table — "J-15 Warm start from global history + opt-out → Activity Log planner-decision entries → Left — Activity Log" — and `history_scope` inputs are already listed under the Left-panel Automated-session controls. The new capability is a field on the existing `POST /api/auto-sessions` command endpoint, which the IA already lists under "Command endpoints (headless surface, not value-serving)."
- **Activity type.** The citation reuses the existing `"auto-run"` type (the only activity literals in the file are `auto-run`/`error`/`user-prompt`; no new type introduced) and therefore the existing render branch — no new render path, no parallel shell, no duplicate home, no hidden/undiscoverable feature.

No Information Architecture violation.

## Step 3 — Advisory observations (WARN-only; none blocking)

- **Formatting consistency (positive):** the cited robust score uses `{:+.4f}`, matching the existing score formatting elsewhere in the controller (`auto_session.py:985/1105/1134`). No formatting drift.
- **Prior WARN resolved:** the iter-5 COHERENCE-WARN was *only* "blueprint describes J-15 but the code is absent" (contract-ahead-of-code). Landing this code makes the implementation match the already-approved contract, clearing that note. No blueprint edit was required or made this iteration, which is correct.

## Conclusion

No objective Step 1 or Step 2 violation. The iteration adds a cross-session read-only miner + cached LLM planner that reprioritize the **bounded** seed within the existing staged open-universe loop, reusing the one `RobustScorer` and one `BudgetTracker`, surfacing only as a cited `auto-run` Activity-Log entry served by the canonical endpoint — no new value, no new endpoint, no parallel store, no nav/shell change. Code now conforms to the pre-registered Layer-2 contract row.

**Verdict: COHERENCE-PASS** — no remediation required.
