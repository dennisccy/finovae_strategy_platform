# Phase goal-money-billions-iter-3 — UX Regression Review

**Date:** 2026-05-18

**Verdict:** UX-REGRESSION-WARN

> Frontend Present: yes. This iteration ships **no new feature** — it resolves
> the `GET /api/sessions/{id}` eager-load anti-goal (backend lightweight open +
> frontend lazy-detail-on-selection) and gives J-04 its first dedicated
> evidence (verification-only, no code change). All six must-have journeys were
> re-exercised post-change and pass. WARN (not PASS) is assigned for two
> documented-but-user-perceptible regressions of *pre-existing, non-journey
> conveniences* and a J-04 insights-discoverability soft gap. None is blocking;
> all are explicitly out-of-scope to fix this iteration.

---

## New Capability Discoverability

This iteration adds **no new user feature**. The only new visible UI is three
states inside the existing run-detail pane (`IterationPanel` → `DetailStatusPane`):

| New UI state | Navigation path | Clicks from session view | Label clarity | Verdict |
|---|---|---|---|---|
| Detail **Loading** spinner | Select any run in the history list | 1 click | "Loading run detail…" + "Fetching this run's strategy, metrics, and trades." | Discoverable, plain-English (UT-16 PASS) |
| Detail **Error** + Retry | Select a run when the per-iteration fetch fails | 1 click | "Couldn't load this run's detail" + error text + **Retry** + **Back to history** | Discoverable, recoverable, never trapped (UT-06/UT-16 PASS) |
| **No-detail** pane | Select an errored/in-progress run with no result | 1 click | "No detailed results for this run" + "Back to history" | Discoverable, non-crashing (UT-07 PASS) |

These states appear exactly where the detail view used to render, triggered by
the same single click (select a run) that already existed. No navigation/layout
restructure (UT-01 PASS), single-page app, no router. **Discoverability of the
new UI is fully satisfied — every state is reachable in 1 click and labelled in
plain English with a permanent "Back to history" affordance.**

---

## Regression Risk

iter-3 modifies four components that **every must-have journey flows through**:
`useBacktest.ts` (central state hook, +107 lines: hydration, lazy-load,
selection, write-amplification guard), `IterationPanel.tsx` (+116),
`SessionContainer.tsx` (+6 plumbing), `IterationCard.tsx` (+6). This is the
highest shared-component overlap possible in this SPA — so the regression
surface is large and was treated as the primary watch.

| Prior feature (phase) | Shared component touched by iter-3? | Risk | Post-change re-verification |
|---|---|---|---|
| J-05 symbol/timeframe controls (iter-2, `BacktestConfigBar.tsx`) | **No** — `git diff` confirms `BacktestConfigBar.tsx` is untouched (explicitly out-of-scope in spec) | None | UT-13 PASS (26-symbol datalist + 6-label timeframe select) |
| Single-Parquet OHLCV / durable store (iter-1, `loader.py`, `session_store.py`) | **No** — backend storage layer untouched (`git diff` shows only `session_routes.py` backend-side) | None | J-06 warm re-run completed + appended under the new lazy contract (UT-14 PASS*) |
| J-01 run-from-NL | `useBacktest`/`SessionContainer`/`IterationCard` (history append + card render) | **High** (shared hook) | UT-11 PASS — "Iterations (3)→(4)", new Complete card w/ metrics, detail auto-displays |
| J-02 browse/reopen run history | `useBacktest` hydration + `IterationPanel` detail + `IterationCard` (the core changed path) | **High** (primary watch) | UT-04/05/08 PASS — lazy fetch fires on select, A→B→A no stale bleed, F5 auto-loads restored selection, re-select uses in-memory cache |
| J-03 walk-forward | `IterationPanel`/detail view (WF reached via opened detail; needs lazy-loaded `scriptCode`) | **High** (depends on lazy detail) | UT-12 PASS — WFE badge + per-window table + combined OOS curve; scriptCode lazy-loaded, no WF error |
| J-04 AI insights | `useBacktest` insights path (auto-insights-on-open path changed) | **Medium** | UT-09 PASS (no auto-fire on open) + UT-10 PASS (user-initiated OOS-aware insights) |

**No must-have journey regressed.** The large shared-component overlap was
directly mitigated by full browser re-verification of all six journeys (17/17
UT cases pass, all 9 P1 pass). The independence rule (lessons iter-0) is
respected: the anti-goal resolution is proven by the `session_routes.py` code
change (`read_iteration_full` → `read_iteration_meta`, verified in `git diff`)
and the new `test_session_routes.py` (5 passed), **not** inferred from green J-02.

### Documented behavior deltas (pre-existing non-journey conveniences — WARN)

1. **Auto-insights on session open no longer fires.** Previously, opening a
   session could auto-generate AI insights for the latest completed run if it
   had none. The lightweight list gives the latest node no in-memory `result`
   at mount, so the `useBacktest` auto-insights effect no longer triggers on
   open (UT-09 PASS confirms 0 `generate-insights` POSTs on open). Intended,
   arguably better (no surprise paid AI calls per open), no must-have journey
   depends on it — but it **is** a user-perceptible loss of a prior convenience.
2. **Card-level "Rerun" / "improve on previous code" now requires opening the
   run first.** `scriptCode` is a lazy heavy field, so triggering Rerun / a
   follow-up-from-previous-code from an *un-opened old run's history card* now
   has empty previous-code context. UT-15 confirms this is a **non-crashing
   documented no-op** (history count unchanged, app interactive). A
   previously-working one-click card action now silently does nothing useful
   unless the user opens the run first — a real (small) UX regression of a
   pre-existing, non-journey capability. Prefetching to restore it is
   explicitly OUT OF SCOPE for iter-3.

Both are documented in the dev/frontend handoffs and user-visible-changes, are
accepted intended consequences of the lightweight-open contract, and break no
must-have journey → WARN, not FAIL.

---

## UI vs Backend Parity

- **Lightweight session-open + lazy per-iteration detail:** fully surfaced. The
  backend lightweight `get_session` and the (pre-existing) per-iteration
  endpoint are consumed by the new `fetchIterationDetail` + loading/error/
  no-detail states. No backend capability is hidden or backend-only. Confirmed
  via API in browser QA (`heavy_keys=[]` for completed iterations) and the
  backend response-shape tests.
- **J-04 OOS-aware insights:** the capability exists in the backend
  (`insights_generator.py` / `POST /api/generate-insights` accepts
  `walk_forward_result`) and **is** surfaced in the UI insights pane — UT-10
  produced a dedicated, distinct LEFT-pane screenshot whose WFE 1.256 / OOS
  -7.22% / -1.02 Sharpe exactly match the real walk-forward run, resolving the
  iter-2 duplicate-screenshot defect. Capability/parity is real and proven.
  **Soft gap (see flag below):** the in-UI path to *(re)generate* insights with
  walk-forward data is weak — there is no dedicated "regenerate insights"
  button; the only native regeneration path is the heavy multi-backtest Auto
  Run loop. Combined with delta #1 (auto-insights-on-open removed), a returning
  user has a weaker in-UI route to OOS-aware insights than before. This is
  pre-existing, not introduced by iter-3, and J-04 is verification-only this
  iteration.

---

## Flags

### Hidden Capabilities
- None. No capability lacks a navigation path. The new detail-pane states are
  reachable in 1 click via the existing run-selection action.

### Undiscoverable Capabilities
- **J-04 OOS-aware insights regeneration (soft, pre-existing, WARN).** After a
  walk-forward run there is no dedicated one-click "regenerate insights"
  affordance; the only native regeneration path is the heavy Auto Run loop
  (regenerates only after exhausting ~10 suggestions). iter-3 additionally
  removed auto-insights-on-open, so a returning user's in-UI route to fresh
  OOS-aware insights is now indirect. Capability is proven present and J-04 is
  verification-only this iteration — flagging for the backlog, not as a blocker.

### Potential Regressions
- **Card-rerun / build-on-previous-code from an un-opened history card**
  (`SessionContainer` handlers, `useBacktest` lazy `scriptCode`): previously
  one click from any history card; now an effective no-op until the run is
  opened (UT-15 PASS — non-crashing, documented). Medium-risk shared path,
  contained: no must-have journey depends on it, fix (prefetch) explicitly
  out-of-scope.
- **Auto-insights-on-open** (`useBacktest`): silently no longer fires on open
  (UT-09 PASS). Low risk, intended, documented; user-initiated insights
  unaffected (UT-10 PASS).
- **All six journeys (high shared-component overlap):** mitigated — every prior
  journey re-exercised post-change and green (UT-04/05/08 J-02 primary watch,
  UT-11 J-01, UT-12 J-03, UT-13 J-05, UT-14 J-06, UT-10 J-04). No observed
  regression.

### Visual Consistency
- New UI matches the established light analytical-workstation styling: slate
  palette, existing button styles, `lucide-react` icons (`Loader2` w/
  `animate-spin`, `AlertCircle`, `ChevronLeft`, `GitBranch`), Tailwind tokens
  already in use — no arbitrary values, no new component library, no layout
  restructure (UT-01/UT-16 PASS). `DetailStatusPane` reuses the same
  panel/border/background classes as the surrounding session view. **Consistent
  — no visual inconsistency flagged.**

---

## Recommendation

Verdict **UX-REGRESSION-WARN** — ship-eligible. No must-have journey regressed;
the anti-goal is code-proven resolved; J-04 has dedicated distinct evidence; the
new loading/error/no-detail UI is fully discoverable and visually consistent.

Non-blocking backlog items (do NOT fix in iter-3 — explicitly out of scope):

1. **Restore card-level rerun / build-on-previous from an un-opened run** —
   prefetch `scriptCode` for the targeted card, or disable/relabel the card
   Rerun action with a tooltip ("open this run first") so it is not a silent
   no-op. (Future iteration; prefetch is out-of-scope here.)
2. **Add a lightweight "Regenerate insights" affordance** on a selected
   completed run so OOS-aware insights are reachable in one click after a
   walk-forward, without the heavy Auto Run loop — closes the J-04
   discoverability soft gap and offsets the removed auto-insights-on-open.
3. Carry deltas #1/#2 forward as known UX trade-offs in the goal-mode journey
   history so a returning user's weaker insights-refresh path is tracked.
