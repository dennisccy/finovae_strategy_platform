**Verdict:** COHERENCE-PASS

# Coherence Audit — goal-financial_free-iter-1

- **Session:** financial_free · **Iteration:** 1 · **Iter name:** goal-financial_free-iter-1
- **Snapshot SHA:** `41c03503ac2491d1d300f1251f10dfebf7005849` (matches `iter-1/snapshot-sha`)
- **Scope audited:** `git diff 41c03503…` + uncommitted/untracked (`git status`)
- **Frontend Present:** no (backend-only iteration) — UI surface map: *N/A, no UI surfaces affected*

## Summary

No objective Data-Contract (Part A) or Information-Architecture (Part B) violation. This iteration
implements three values **already reserved** in the blueprint Data Contract, computes them in the
registered canonical module, serves them from the registered canonical endpoint, and writes them to
the **same** file store the UI renders. It also **reduces** duplication by extracting backtest
serialization into one shared module. Only two advisory notes, both already documented/scheduled in
the contract.

---

## Part A — Data Contract check

### A.1 New values implemented this iteration are registered + canonical — PASS

The three Layer-1 rows in `blueprint.md` (lines 71–73) are concretized exactly as the blueprint
reserved them:

| Registered value | Computed by (canonical) | Served by (canonical) | Verified |
|---|---|---|---|
| Auto-session run state + stop reason | `AutoSessionController` (`auto_session.py:334`), written via `session_store.write_session_meta` (`auto_session.py:388`) | `GET /api/sessions/{id}` → `autoRun.status`/`stopReason` (`session_routes.py:182`) | ✓ |
| Budget counters | immutable `BudgetTracker` (`auto_session.py:101`) → `to_dict()` (`auto_session.py:140`) | `autoRun.budget` on same GET | ✓ |
| Robust objective score + best marker | `RobustScorer` (`auto_session.py:172`), derived from canonical `BacktestResult`+`WalkForwardResult` via `IterationMetrics` (`auto_session.py:156`, `_metrics_from` `auto_session.py:436`) | `autoRun.bestIterationId` on same GET | ✓ |

No new value is unregistered. The robust *score* (a genuinely new derived value) is the registered
"Robust objective score" row — not a synonym of an existing value. ⇒ no A4/A5 issue.

### A.2 Existing canonical values are reused, never recomputed — PASS

- **Backtest metrics** (`total_return`, `sharpe`, `max_drawdown`, `num_trades`, `margin_called`, …):
  `_metrics_from` (`auto_session.py:436`) and `_build_node` (`auto_session.py:410`) **read** these off
  the pipeline's frozen `BacktestResult` (`result.total_return`, `result.sharpe_ratio`, …). No second
  `MetricsCalculator`. The `min(1.0, float(result.max_drawdown))` at `auto_session.py:427` is the same
  display clamp the serializer applies — re-format, not recompute (contract allows re-format).
- **Walk-forward efficiency** (`wfe`): obtained from the pipeline's `execute_backtest(..., wfv_enabled=True)`
  (`auto_session.py:463`) and read as `wf_result.wfe` (`auto_session.py:445`). No independent WFE math —
  the canonical `walk_forward.py` computation (owned by `BacktestPipeline`) is reused.
- **5-category rating**: taken from the pipeline's return tuple (`auto_session.py:657`) and serialized,
  never re-derived.

### A.3 Serialization consolidated to ONE source — duplication REDUCED — PASS (notable positive)

New module `result_serialization.py` was **extracted verbatim from `backend.api`** (`api.py` diff:
`-_safe_float`, `-_equity_point`, `-_serialize_rating`, `-_serialize_walk_forward`, and the inline
`BacktestResultSchema` block all deleted, replaced by imports at `api.py` `from backend.result_serialization import …`).
The manual SSE path (`POST /api/execute-backtest`) and the headless loop now call the **same**
`serialize_backtest_result`/`serialize_rating`/`serialize_walk_forward`, guaranteeing byte-shape-identical
`result`/`rating`/`walk_forward` payloads. This is a single-source-of-truth move — the opposite of a
divergent-copy violation.

### A.4 Same store, no schema fork — PASS

`auto_session.py` persists exclusively through canonical `session_store` functions —
`write_session_meta` (`:388`), `write_iteration` (`:680`), `append_activity_entries` (`:406`),
`read_session_meta`/`read_iteration_full`/`list_iteration_dirs`. No parallel store, no new on-disk
schema. The iteration node assembled in `_build_node` (`:413`) mirrors the manual node shape, with
`result`/`rating`/`walkForwardResult` produced by the shared serializer.

---

## Part B — Information Architecture check

- **No frontend changed** — verified: `git diff`/`status` show zero `apps/frontend/**` files;
  `useBacktest.ts` untouched. UI surface map = N/A. No new page/route/component, no parallel shell.
- **New endpoints are command endpoints already in the blueprint.** `POST /api/auto-sessions` and
  `POST /api/auto-sessions/{id}/stop` (`auto_session_routes.py:176`, `:240`) match the blueprint's
  "Command endpoints (headless surface, not value-serving)" line (`blueprint.md:38`). The created
  session surfaces through the **existing** Header → Session picker via `GET /api/sessions` (written
  store-first at `auto_session_routes.py:214`), and its `autoRun` reads on the existing Right-panel
  status strip. No new home invented; nothing to navigate to. ⇒ no B1/B2/B3/B4.
- **autoRun served from the canonical GET only.** There is no competing value-serving `GET` for the
  status — `auto_session_routes.py` exposes only the two POSTs, which **echo the just-persisted**
  `autoRun` dict as command acknowledgement (`:237`, `:255`/`:261`). The display/poll source remains
  `GET /api/sessions/{id}` (`session_routes.py:182`). No non-canonical serve path.

---

## Part C — Advisory observations (do NOT block; recorded for context)

1. **Transitional duplicate scorer (documented, scheduled — not introduced here).** The in-browser
   `scoreIteration` in `apps/frontend/src/hooks/useBacktest.ts` still computes "best" for the *manual*
   in-browser Auto Run. The new backend `RobustScorer` is now the **canonical** definition (registered
   in the Data Contract). This is **pre-existing** (untouched by this diff) and the blueprint row
   (`blueprint.md:73`) plus the iter spec NOTES explicitly schedule its removal at **J-10 / iter-2**
   when Auto Run is rewired to the backend loop. Per the audit rules (FAIL only on a *newly introduced*
   recompute), this is advisory/transitional, not drift. **Action for iter-2:** delete the in-browser
   scorer when J-10 lands; until then the canonical home is unambiguous.

2. **Carried-forward eager-load verdict (requested by the iter spec NOTES) — this iteration does NOT
   worsen it.** Definitive verdict: the `GET /api/sessions/{id}` open path **conforms** to the
   "no eager full-payload parse" anti-goal *as currently written* — `get_session` builds its iteration
   list from `read_iteration_meta` (lightweight per-iteration metadata) and lazy-loads each run's heavy
   `result`/`rating`/`equity_curve`/`trades` only via `GET /{session_id}/iterations/{iteration_id}`
   (`session_routes.py:142–185`, docstring `:144–154`). This iteration's sole change to the route is the
   **additive** `autoRun` field (`:182`) — an O(1) block (status string, ids, integer budget counters,
   no curve data) — so the open payload is not enlarged and the lazy-loading behavior is preserved.
   If the iter-0 "~245 KB" figure persists, it is dominated by per-iteration metadata + activity log
   across many runs (pre-existing), not by eager `equity_curve` embedding, and is outside this
   iteration's Data-Contract/IA scope. **No regression; no coherence violation.**

---

## Rule trace (why PASS, not WARN/FAIL)

- Part A: 0 objective violations (no duplicate computation; no non-canonical source; new values registered).
- Part B: 0 objective violations (backend-only; command endpoints pre-registered; canonical serve path).
- Part C: 2 advisory notes, both already documented & scheduled in the contract → "minor advisory notes"
  under PASS, not blocking. The one duplicate is pre-existing and not introduced by this diff, so it
  cannot raise a FAIL under the "*new* function that computes the same value" rule.
