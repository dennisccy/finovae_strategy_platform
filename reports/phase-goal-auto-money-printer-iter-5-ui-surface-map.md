# Phase goal-auto-money-printer-iter-5 — UI Surface Map

**Phase:** goal-auto-money-printer-iter-5
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## Affected UI Surfaces

No frontend code changed. The single new user-visible artifact (the warm-start
planner-decision note) flows through the **existing** Activity feed renderer
unchanged. Surfaces below are affected by **new data / changed backend behaviour**,
not by changed UI code. App is a single-page app served at `/`; the Activity feed is
the left half of the selected session (desktop `lg:` always visible; mobile under the
"Activity" tab).

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| `/` (selected session, Activity tab) | `ActivityLog` → `ActivityLogEntry` (`type === 'auto-run'`) — violet ⚡ row | Changed behavior (new content through existing renderer) | J-15 appends one planner-decision `auto-run` entry on a global/default open-universe warm-started run | Start an open-universe auto-session (omit `symbol`+`timeframe`, `objective:"robust"`, tiny budget) **with prior promoted open-universe history present** and `history_scope:"global"` (or omitted). Select that session; in the Activity feed confirm a violet entry with a ⚡ icon reading `Warm start (global history): prioritising <SYM> <TF> — prior best robust <0.NN> across <N> prior session(s)`, the `<SYM> <TF>` matching the prior run's top family, full text **not truncated** |
| `/` (selected session, Activity tab) | `ActivityLog` ungrouped region (top of feed, above iteration accordions) | Changed behavior (placement of new entry) | Citation is emitted with an empty `iterationId` → routed to `groupByIteration` `ungrouped` and rendered before any iteration group | On the global-scope run above, confirm the warm-start ⚡ entry renders **above** the first collapsible iteration group (not hidden inside an accordion) and is visible without expanding anything |
| `/` (selected session, Activity tab) | `ActivityLog` / `ActivityLogEntry` — absence on opt-out | Changed behavior | `history_scope:"this-run"` must NOT mine, reorder, or emit the citation | Start the same open-universe auto-session but with `history_scope:"this-run"` (prior history still present). Select that session; confirm **no** "Warm start (global history)" entry appears anywhere in the feed and the run still completes (fixed seed order) |
| `/` (selected session, Activity tab) | `ActivityLog` / `ActivityLogEntry` — absence with empty history | Changed behavior | No usable prior history → byte-identical no-warm-start fallback (no citation) | Start a global-scope open-universe auto-session against a store with **no prior promoted history**. Confirm **no** "Warm start" entry appears and the run completes normally with ≥2 distinct configs |
| `/` (header, Sessions dropdown) | `SessionPicker` (App.tsx 5s `fetchSessionTabs` merge) | No change — re-verify (navigation path to the citation) | The J-15 browser test reaches the citation only via headless-session discovery; this path must still work | Start a headless open-universe run via `POST /api/auto-sessions` with no browser interaction. Without reloading, confirm a new `Auto: …` entry appears in the Sessions dropdown within ~5s and is selectable, opening its Activity feed |
| `/` (selected session, AutoRunBar) | `AutoRunBar` (live status + spend readout) | No change — re-verify (regression) | Warm-start runs once before the SCREEN loop; budget/spend wiring untouched | During a warm-started global run, confirm the AutoRunBar still shows live `running` status and the spend/iteration readout updates, then reaches a terminal status (J-08/J-13 unaffected) |
| `/` (selected session, right panel) | Iteration detail / history browse | No change — re-verify (regression, iter-0 lesson) | Read-only mining must not mutate/regress prior sessions; J-02 must not regress | Open a **prior** session and confirm its iteration history, equity chart, and metrics still load unchanged and identically to before the new run (no missing/altered/reordered prior iterations) |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/backend/auto_session.py` — `_resolve_history_scope` (effective
  scope), `_mine_history` (read-only durable-store surrogate), `_reorder_configs`
  (stable bounded-seed permutation), `_strongest_family` (deterministic citation
  pick), `_warm_start_configs` (once-per-run off-thread orchestrator), and the
  open-universe-only wire-in to `_run_auto_session_impl`. Cross-run learning logic;
  no UI surface of its own. Its only user-visible output is the Activity-feed note
  above.
- `apps/backend/backend/auto_session.py` — additive `autoRun.effectiveHistoryScope`
  key (open-universe only) and idempotent persistence of the raw `autoRun.historyScope`.
  Returned by `GET /api/sessions/{id}` and consumed by the existing live poll, but
  **not rendered as a labeled UI element** — API/durable-record only by design.
  Optional API-level check: after a `"global"`/default run, `autoRun.historyScope` is
  the raw value (`null` if omitted) and `autoRun.effectiveHistoryScope == "global"`;
  after a `"this-run"` run, `autoRun.effectiveHistoryScope == "this-run"`; a pinned
  run has neither key.
- `apps/backend/tests/test_auto_session.py` — 12 new tests + 2 consciously-updated
  tests (read-only content-hash proof, opt-out, default→global, once-per-run,
  bounded-seed permutation, robust-best, error cases). Test code only — no UI impact.

---

## Summary

- **Frontend surfaces changed:** 0 code changes; 4 existing surfaces show new/changed
  data (Activity-feed entry presence, placement, opt-out absence, empty-history absence)
- **New pages/routes:** 0
- **Modified components:** 0 (existing `ActivityLog`/`ActivityLogEntry` render new
  `auto-run` content verbatim with no code change)
- **Navigation changes:** no
- **Backend-only changes:** 3 (warm-start logic, additive `effectiveHistoryScope`
  durable/API key, test suite)
