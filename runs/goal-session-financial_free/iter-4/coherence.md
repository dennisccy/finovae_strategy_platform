**Verdict:** COHERENCE-PASS

# Coherence Audit — goal-financial_free-iter-4

- **Session:** financial_free  · **Iteration:** 4  · **Iter name:** goal-financial_free-iter-4
- **Auditor:** coherence-auditor
- **Snapshot SHA audited:** `664aaff8e0977bca3c348f12649d8ffc73e17ed0` (`git diff <sha>` + working tree; all changes uncommitted)
- **Blueprint:** `runs/goal-session-financial_free/state/blueprint.md`
- **UI surface map:** `reports/phase-goal-financial_free-iter-4-ui-surface-map.md` (present, used)

This iteration restructures the open-universe loop `_run_open_universe` into a two-stage **SCREEN→PROMOTE**
cost-tiering (J-14): a cheap SCREEN pass (cheapest model, no walk-forward) over the budget-bounded seed
configs, then a PROMOTE pass that escalates only the top-`k` survivors (k < n_screened) to walk-forward +
the stronger request model, with the cross-config best marked from the **promoted** candidates only. No
objective Data-Contract or Information-Architecture violation. The hard-FAIL gate this spec explicitly
flagged — "any displayed score flows from the **one** `RobustScorer` … no second computing path" — holds
decisively: there is exactly one scorer, used for every score (SCREEN entry, survivor ranking, PROMOTE
best). The new `BudgetTracker.cost_exceeded()` is a gate *predicate* over the same canonical counters, not
a new tally. Zero frontend code changed — the two stages surface through the existing Activity Log
`auto-run` branch (the J-14 home already reserved in the blueprint IA). One **advisory** note: an
out-of-scope `GET /health` liveness probe was added (infra, serves no registered value, not a UI route) —
does not affect the verdict.

---

## Part A — Data Contract (objective → FAIL gate): PASS

| Check | Result | Evidence |
|---|---|---|
| Robust score computed by **one** scorer (THE hard-FAIL gate per spec NOTES) | ✅ single source | Exactly one `RobustScorer` class (`auto_session.py:242`) with one `score()` (`:262`) and one `select_best()` (`:279`); one instance `self.scorer = scorer or RobustScorer()` (`:470`). Every score in the staged path routes through it: SCREEN per-candidate entry `self.scorer.score(m)` (`:906`), survivor ranking `self.scorer.score(screened[i][1])` (`:927`), PROMOTE best `self.scorer.select_best(promoted)` (`:962`) + display `self.scorer.score(best)` (`:970`). **No** second `score`/`select_best`, no new scorer class/instance in the diff. |
| Best marker (`autoRun.bestIterationId`) stays WFE-gated, one definition | ✅ canonical | Best chosen via `self.scorer.select_best(promoted)` over the **PROMOTED** list only (`:962`) — screened-only nodes are never passed to `select_best`, so the "best derives from walk-forward OOS, WFE-gated" invariant (J-16/J-09) is intact. `self.best_id` = the canonical `bestIterationId`, served by the existing `GET /api/sessions/{id}`. |
| Budget counters on **one** immutable tracker; no new counter | ✅ single source | New `BudgetTracker.cost_exceeded()` (`:186-202`) is a new gate *predicate* reading the **same** fields (`wall_clock_sec`/`tokens`/`usd` + their caps) — it adds NO counter and leaves `exceeded()` (the J-13 tests depend on it) and `to_dict()` (the `autoRun.budget` serialization) **unchanged**. PROMOTE work accrues onto the same frozen tracker via `with_config_completed`/`with_wall_clock`; spend threaded by the existing `_account_usage` (iter-3). No parallel tally. |
| Open-universe controller is **orchestration only** (computes no new metric) | ✅ conforms | `_run_open_universe` (`:835`) evaluates every unit through the same `_create_iteration` → `BacktestPipeline` (generate → backtest → optional walk-forward), scores via the existing `RobustScorer`, and marks `self.best_id`. Docstring + code match the new blueprint row verbatim: writes only iteration `params`, `autoRun.bestIterationId`, `autoRun.budget`, and SCREEN/PROMOTE activity records. The pinned path `_run_inner` is untouched (J-07/J-09 protected). |
| SCREEN/PROMOTE stages are **activity records** (registered "Shared records" row); no new value/store | ✅ conforms | Both stages emit via the existing `self._append_activity("auto-run", …)` (`:893,901,945,966`) — the already-rendered `auto-run` type with `SCREEN —` / `PROMOTE —` prefixes — persisted by the canonical `session_store` path. Nodes built by the existing `_create_iteration`/`_build_node` and persisted via `_persist_new` → `session_store.write_iteration`; the screen→promote lineage uses the existing `parentId` field (`parent_id=screen_node["id"]`, `:953`). No schema fork, no new store, `shared/contracts.py` untouched. |
| No **new** displayed value introduced outside the contract | ✅ none | SCREEN/PROMOTE entries show only: symbol/timeframe (existing config `params`), the **canonical** `self.scorer.score(...)`, model names (routing labels, below), and orchestration counts ("top-`k` of `N`"). None is a new "same-everywhere" value or a synonym/re-derivation of a registered one. `modelUsed` + `walkForwardStatus`/`walkForwardResult` on the per-stage nodes already exist on the node contract. |
| Model routing has a **single source of truth** (no displayed metric) | ✅ conforms | New `cheapest_model()` (`shared/model_catalog.py:124-139`) returns the min-blended-rate catalog model id from `MODEL_RATES` (deterministic, ties by id) — a routing helper that computes **no** displayed value. SCREEN uses `cheapest_model()`, PROMOTE uses the request `base.model` (`auto_session.py:865-866`); model tiering reads the rate table, not a hard-coded id. |
| Blueprint edited **additively** (Data-Contract Notes only) | ✅ conforms | The blueprint diff touches **only** the "(Layer-2, iter-3 → iter-3; staged iter-4) Open-universe search" row: computing column gains "model tier from `…cheapest_model()`", serving column gains "SCREEN/PROMOTE stage **activity records**", Notes rewritten to record the staged invariants. **Serving endpoint unchanged** (`GET /api/sessions/{id}`); no new row, no new value, no new endpoint. Information-Architecture section untouched. Matches the spec's "additive Notes edit only, no nav change." |

## Part B — Information Architecture (objective → FAIL gate): PASS

| Check | Result | Evidence |
|---|---|---|
| New stage entries live in their blueprint-reserved home | ✅ correct home | SCREEN/PROMOTE `auto-run` entries render in the Left **Activity Log** via the existing `ActivityLogEntry` `auto-run` branch — the blueprint IA row "J-14 Staged screening (SCREEN/PROMOTE) | Activity Log stage entries | Left — Activity Log". No parallel shell, no new panel. |
| Zero frontend code changed; content-only behavior change | ✅ conforms | No `apps/frontend/` file in the diff (diff-stat + `git status` confirm; surface map: "Frontend surfaces changed: 0 code changes; Modified components: 0"). The new content displays through existing components. |
| Promoted/screened nodes + lineage reachable through the existing surface | ✅ conforms | Distinct configs stream through the **existing** Right-panel iteration cards/tree; the promoted node nests as a **child** of its screened candidate via the existing `parentId` — no new route, 1-click iteration detail unchanged. |
| No new page / route / nav section / parallel shell | ✅ none | api.py adds no value-serving route (canonical `GET /api/sessions/{id}`, `POST /api/run-backtest`, `POST /api/execute-walk-forward`, `POST /api/auto-sessions[/{id}/stop]` all unchanged); no new UI page/panel/nav entry. Single-page shell intact, 0 extra clicks. |
| No duplicate home for an existing entity | ✅ none | Activity Log keeps its single home; iteration cards/tree keep theirs. No second page for stages, configs, score, or budget was introduced. |

## Part C — Advisory (WARN-only; does NOT affect the verdict)

- **Out-of-scope `GET /health` endpoint (infra, not a coherence violation).** `api.py:163-171` adds a new
  `GET /health` returning a static `{"status": "ok"}` liveness probe, per its docstring for the dev-chain
  automation scripts (qa/browser-qa/demo/goal pollers), mirroring the existing `/api/health`. This is
  **not** a Part A or Part B violation: it serves **no** registered Data-Contract value (the Data Contract
  has no "health"/"status" displayed value to point at) and it is **not** a UI page/route in the
  Information-Architecture nav skeleton. Two notes for the reviewer/auditor (scope, not coherence): (1) the
  iter-4 spec explicitly said the iteration "introduces **no** new … endpoint" — this is a deviation from
  that stated scope; (2) `/health` and `/api/health` now both report liveness — a minor infra duplication a
  later tidy could consolidate or document. Zero impact on the "numbers don't match" / scattered-nav
  failure modes this gate exists to prevent → recorded as a transparency note only.

- **No product-coherence advisories.** No label inconsistency, no value formatted differently across pages,
  no layout drift. SCREEN/PROMOTE reuse the existing `auto-run` entry styling and the one
  `self.scorer.score` formatting (`:+.4f`), so display stays consistent with prior auto-run entries.

---

### Conclusion

The staged SCREEN→PROMOTE restructure is genuine orchestration over the existing pipeline, scorer, budget
tracker, and file store. There is exactly **one** `RobustScorer` (every shown/ranked/best score flows
through it — the hard-FAIL gate the spec called out), exactly **one** `BudgetTracker` (the new
`cost_exceeded()` only reads its existing fields), the new stage entries are canonical `auto-run` activity
records served by the unchanged `GET /api/sessions/{id}`, and `cheapest_model()` is pure model routing with
no displayed metric. Zero frontend code changed; the two stages surface in their blueprint-reserved Activity
Log home with no nav change. The blueprint edit is additive (Notes/columns only, same serving endpoint). The
only note is an out-of-scope `GET /health` infra probe that touches neither the Data Contract nor the UI
IA. The app stays coherent.

**Verdict:** COHERENCE-PASS
