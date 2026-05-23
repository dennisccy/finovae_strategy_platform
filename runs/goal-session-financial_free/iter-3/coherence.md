**Verdict:** COHERENCE-PASS

# Coherence Audit — goal-financial_free-iter-3

- **Session:** financial_free  · **Iteration:** 3  · **Iter name:** goal-financial_free-iter-3
- **Auditor:** coherence-auditor
- **Snapshot SHA audited:** `eaaacc4144030bd8ad1d232ab8e73b2786d68be1` (`git diff <sha>` + working tree)
- **Blueprint:** `runs/goal-session-financial_free/state/blueprint.md`
- **UI surface map:** `reports/phase-goal-financial_free-iter-3-ui-surface-map.md` (present, used)

This iteration starts Layer-2: an **open-universe** controller path (`_run_open_universe`) that explores
a budget-bounded subset of a bounded seed universe, plus **hard token/USD/`max_configs` budget**
enforcement and **real SDK token→USD accounting** surfaced in the status strip. No new objective
Data-Contract or Information-Architecture violation. The token side channel is threaded cleanly, USD is
computed in exactly one place, and the open-universe loop is genuine orchestration — it reuses the
existing `BacktestPipeline` + `RobustScorer` and writes only already-canonical records. The iter-2
advisory (run-state enum missing `error`) is now **resolved** in the blueprint. No new advisories.

---

## Part A — Data Contract (objective → FAIL gate): PASS

| Check | Result | Evidence |
|---|---|---|
| USD cost computed by **one** module/function | ✅ single source | `cost_usd()` defined once at `apps/backend/shared/model_catalog.py:115`; the only caller is `auto_session.py:532` inside `_account_usage`. Repo-wide grep for `cost_usd` returns exactly those two lines. Grep for `per_1m`/`usd_per`/`MODEL_RATES` outside `model_catalog.py` → 0 hits. No second pricing path. |
| Token spend accumulated on **one** canonical tracker | ✅ single source | `_account_usage` (`auto_session.py:519-532`) maps tokens→USD via `cost_usd` and accumulates on the frozen `BudgetTracker.with_usage` (`auto_session.py:155-157`) — a new instance, never mutated in place. No parallel counter. |
| Real SDK usage threaded as a **side channel** (no frozen-contract mutation) | ✅ conforms | `TokenUsage` (frozen, `model_catalog.py`) captured at the SDK boundary in `script_generator.py:414-419/450-454` and `insights_generator.py:335-339/372-376`, surfaced via `pipeline.last_strategy_usage` / `last_insights_usage` (`pipeline.py:104-109,349,789`), read by the controller through `getattr(...)`. `GenerateStrategyResult`/`shared/contracts.py` untouched (anti-goal honored). |
| Budget counters served by the **one** registered endpoint | ✅ canonical | `BudgetTracker.to_dict()` (`auto_session.py:163-178`) adds `configsDone`/`maxConfigs`/`maxTokens`/`maxUsd` (and rounds `usd`) to the `autoRun.budget` block, served by the existing `GET /api/sessions/{id}`. No new value-serving endpoint: `auto_session_routes.py` still exposes only `POST ""` and `POST /{id}/stop` (command, not value). |
| UI **re-formats** canonical values only (no recomputation) | ✅ allowed | `AutoSessionStatusStrip.tsx` reads `budget.tokens`/`budget.usd`/`budget.configsDone` and applies display-only transforms `fmtTokens` (compact `1.2k`) / `fmtUsd` (4-dp) (`:37-42,90-96`); configs/rounds chosen by `budget.maxConfigs != null` (`:60-61,79-86`). No arithmetic on the values. `sessionApi.ts` only **extends the `AutoRunBudget` type** to mirror `to_dict()` — no second fetch added. |
| No **new** displayed value introduced outside the contract | ✅ none | All newly-shown fields (`configsDone`/`maxConfigs`, `tokens`/`maxTokens`, `usd`/`maxUsd`) belong to the already-registered **Budget-counters** row, edited additively in the blueprint diff. No synonym/re-derivation of an existing value. |
| Open-universe controller is **orchestration only** (computes no new metric) | ✅ conforms | `_run_open_universe` (`auto_session.py:805-873`) calls the shared `_create_iteration` → `_generate`/`_backtest` (existing `BacktestPipeline`), scores via `self.scorer.select_best`/`.score` (existing `RobustScorer`), and marks `self.best_id` = `autoRun.bestIterationId`. Nodes built by the existing `_build_node` and persisted via `_persist_new` → `session_store.write_iteration`. Matches the new blueprint row's claim verbatim: writes only iteration `params`, `autoRun.bestIterationId`, `autoRun.budget`. |
| Distinct configs reuse the **canonical** node byte-shape (no schema fork) | ✅ conforms | `_build_node` now takes `config` and writes `config.backtest_params()` / `config.model` (`auto_session.py:554,561`) so each open-universe card carries its own symbol/timeframe — surfaced through the **existing** iteration cards. `result_to_dict`/`rating_to_dict` reused (no re-fork of `result_serialization.py`, per the iter-1 lesson). |
| Same file store, no parallel store | ✅ conforms | Persistence stays on `session_store.write_iteration` / `_save_auto_run` (same `session.json` `autoRun` block). No new datastore, no `.parquet`/sqlite, `shared/contracts.py` untouched. |

**Note on the dedup cache (`_backtest_cache`, `auto_session.py:464,594-619`):** an in-process
result-reuse cache keyed on code-hash + params. It returns a **previously-computed** `BacktestResult`
unchanged — it does **not** recompute any metric — so it is not a second computing source. Not a
violation.

## Part B — Information Architecture (objective → FAIL gate): PASS

| Check | Result | Evidence |
|---|---|---|
| New counters live in their blueprint-reserved home | ✅ correct home | The token/USD/configs chips render inside `AutoSessionStatusStrip`, mounted by `IterationPanel.tsx:259,281` at the top of the Iterations panel — the blueprint's "Right — Iterations → Automated-session status strip" home. No parallel shell. |
| Open-universe configs reachable through the existing surface | ✅ conforms | Distinct configs stream through the **existing** iteration history cards (Right — Iterations tree); the iteration-detail (1 click from a card) is unchanged. Surface map confirms "New pages/routes: 0", "Navigation changes: no". |
| Open-universe **started** via the existing command endpoint | ✅ conforms | Dispatched on the same `POST /api/auto-sessions` (`auto_session_routes.py:227-292`) by omitting `symbol`+`timeframe`; the blueprint IA already records "pinned or open-universe" on this endpoint. No new screen, no new route. |
| No new route / nav section / parallel shell | ✅ none | Single-page shell unchanged; only an existing component (`AutoSessionStatusStrip`) and an existing type (`AutoRunBudget`) changed. 0 extra clicks. |
| No duplicate home for an existing entity | ✅ none | Budget counters keep their single home (the status strip); no second page for budget/configs/cost was introduced. |
| Blueprint edited additively (no nav change → no re-approval) | ✅ conforms | The blueprint diff touches **only** the Data-Contract table — the Budget-counters row Notes (token/USD hard-enforced iter-3 + `max_configs`/`configsDone`) and a new orchestration-only **"(Layer-2, iter-3) Open-universe search"** row. The Information-Architecture section is untouched. Matches the spec's "Blueprint conformance: No nav-skeleton change → no re-approval." |

## Part C — Advisory (WARN-only; does NOT affect the verdict)

- **None for iter-3.** No formatting drift, no label inconsistency, no unregistered value. The
  token/USD chips now also appear on **pinned** runs (previously rounds + wall-clock only); this reads
  the same `autoRun.budget` block with the same single `fmtTokens`/`fmtUsd` formatting, so it improves
  consistency rather than introducing drift.

- **iter-2 advisory resolved (positive note).** The iter-2 §C.1 advisory — blueprint run-state enum
  omitted `error` — is now fixed: the run-state row lists `… / interrupted / error`
  (`blueprint.md:70`), matching the backend `STATUS_ERROR` and the frontend `AutoRunStatusValue`. The
  iter-2 §C.2 "rounds vs iterations" label nuance is unchanged and remains a harmless non-issue (the
  strip correctly shows `rounds` for pinned, `configs` for open-universe).

---

### Conclusion

No objective Data-Contract or Information-Architecture violation. USD is computed once
(`model_catalog.cost_usd`), token usage is threaded as a clean side channel and accumulated once on the
frozen `BudgetTracker`, every displayed value reads the single canonical `GET /api/sessions/{id}` →
`autoRun.budget` block (UI re-formats only), and the open-universe controller is true orchestration over
the existing pipeline + scorer with no schema fork and no new endpoint. The app stays coherent.

**Verdict:** COHERENCE-PASS
