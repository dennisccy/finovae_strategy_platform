# Phase goal-auto-money-printer-iter-3 — UI Surface Map

**Phase:** goal-auto-money-printer-iter-3
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

The app is a single-page React workspace (no client router). "Route / Page" =
the main session workspace at `/`; surfaces are reached by selecting a session
from the session list/sidebar, which renders `SessionContainer`.

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| `/` (session view) | `AutoRunBar` → spend `<span>` (right-aligned, `tabular-nums opacity-75`, in `SessionContainer.tsx`) | New element | J-13: surface recorded hard-budget spend in the existing status strip | Start an open-universe run (`POST /api/auto-sessions` with only `objective:"robust"` + tiny `budget`), open the created "Auto: …" session; while it runs, confirm the bar's right side shows `<N> tok · $<X.XXXX> · <N> cfg` and the token/cfg numbers **increase** across the 2.5 s poll; hover it and confirm tooltip "AI tokens / USD / configs spent under the hard budget". |
| `/` (session view) | `AutoRunBar` → `budget-exhausted` terminal branch | Changed behavior | J-13: budget-reached finish made visually distinct from criteria-met | Run an open-universe session with a tiny token/USD `budget` to force budget exhaustion; when terminal, confirm the bar is **amber** (`bg-amber-50`/`text-amber-700`), shows the `CircleDollarSign` icon, and reads "Automated run complete · budget reached · X/Y iterations" — not the green `CheckCircle2` style. |
| `/` (session view) | `AutoRunBar` → spend `<span>` (absent-spend path) | Changed behavior | Graceful no-op for legacy/manual/just-created sessions | Open a pre-iter-3 / manual session (no `autoRun.spend`); confirm **no** spend readout appears, no `NaN`/`$undefined`, and the bar is byte-identical to its pre-iter-3 appearance. |
| `/` (session view) | `AutoRunBar` persistence after reload | New element (durability) | J-13: spend read from durable `autoRun.spend` via `GET /api/sessions/{id}` | After a budget-exhausted open-universe run finishes, hard-reload the browser, reopen the same session; confirm the final spend readout and amber budget-reached state still render (no value lost on reload). |
| `/` (session view) | Iteration tree / `IterationCard` / `BestBadge` (existing, unchanged components) | Changed behavior (new data, no component change) | J-12: open-universe controller writes ≥2 distinct configs via the existing iteration path | Open the open-universe "Auto: …" session; confirm **≥2 iterations with differing symbol and/or timeframe** appear in the iteration tree (read each card's config), the run reaches a terminal state within budget, and exactly one card shows the existing robust `BestBadge`. |
| `/` (session view) | Session list / sidebar entry + `AutoRunBar` mount-status | Changed behavior (regression-sensitive) | J-08: open-universe is a new still-running source; mount must re-derive live status | Start an open-universe run; while it is still running, rapidly switch to another session and back; confirm `AutoRunBar` shows **"running"** (spinner) — not a stale terminal — and the session-list spinner agrees with the bar. |
| `/` (session view) | Right analysis panel (trades table / equity curve / WF) | Changed behavior (regression-sensitive) | J-02: heavily-edited `auto_session.py`; prior-run right-panel re-bind must not regress | In an open-universe session with ≥2 completed configs, click a prior (non-selected) iteration; confirm the **right** panel re-binds — trades table, equity curve, and walk-forward all update to that run, not just the left summary. |
| (API, consumed by existing UI) | `POST /api/auto-sessions` open-universe acceptance | Changed behavior | J-12: 422 gate relaxed for the open-universe shape | `POST /api/auto-sessions` with `{objective:"robust", budget:{…}}` and **no** symbol/timeframe → expect **200** and a session id; same call with `objective:"sharpe"` → **422**; with timeframe but no symbol → **422**; malformed budget/date → **422** (never 500); a full pinned request → behaves exactly as pre-iter-3. |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/backend/cost_tracker.py` (**NEW**) — immutable monotonic
  `CostTracker` + frozen `CostCaps`. No direct UI surface; it *produces* the
  `spend` snapshot rendered by `AutoRunBar` (indirect — covered by the spend
  rows above).
- `apps/backend/shared/llm_usage.py` (**NEW**) — `capture_usage()` real SDK
  `.usage` → caller sink. No UI surface.
- `apps/backend/shared/model_catalog.py` — `MODEL_PRICING` table /
  `usd_cost()`. No UI surface; feeds the `$<usd>` figure shown in `AutoRunBar`
  (indirect — covered above).
- `apps/backend/backend/pipeline.py` — forwards optional `usage_sink` through
  `generate_strategy`/`generate_insights`. No engine/orchestration change, no
  UI surface.
- `apps/backend/strategy/{compiler,script_generator,insights_generator}.py` —
  optional `usage_sink` param + `capture_usage(...)` after existing usage
  logging. No behavioural change without a sink; no UI surface.
- `apps/backend/backend/auto_session.py` — open-universe controller, seed
  universe, cost-tracker integration, durable spend write. Internal except for
  the relaxed `POST /api/auto-sessions` behaviour and the durable
  `autoRun.spend` it writes (both covered as indirect surfaces above).
- `apps/backend/tests/{test_auto_session,test_cost_tracker,test_model_pricing,test_usage_capture}.py`
  — test code only, no UI surface.
- `apps/frontend/src/hooks/useBacktest.ts` — **type-only** (`AutoRunSpend`
  interface + optional `AutoRunStatus.spend`). No poll/effect/merge change; it
  enables the spend field to flow into `AutoRunBar` (covered above) but adds no
  independent UI surface of its own.

---

## Summary

- **Frontend surfaces changed:** 1 component (`AutoRunBar` in
  `SessionContainer.tsx`) — additive spend readout + distinct
  `budget-exhausted` styling; 4 distinct testable behaviors on it (live spend,
  budget-exhausted style, absent-spend graceful path, reload durability).
- **New pages/routes:** 0 (single-page app; no new page, panel, route, or
  leaderboard — by design per spec).
- **Modified components:** 1 (`AutoRunBar`); `useBacktest.ts` type-only;
  iteration tree / `IterationCard` / `BestBadge` render new open-universe data
  through **unchanged** components.
- **Navigation changes:** no.
- **Backend-only changes:** 9 files (2 new backend modules + price
  table + pipeline/generator usage plumbing + controller/tracker wiring in
  `auto_session.py` + 4 test files); 2 of these (relaxed
  `POST /api/auto-sessions`, durable `autoRun.spend`) surface **indirectly**
  through existing UI and are covered as testable rows above.
