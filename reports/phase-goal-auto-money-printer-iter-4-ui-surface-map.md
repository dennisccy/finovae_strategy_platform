# Phase N — UI Surface Map

**Phase:** goal-auto-money-printer-iter-4
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

> **App structure note:** the frontend is a single-page tabbed app (Vite SPA,
> no client-side URL router). There are no per-feature route paths; surfaces
> are addressed by the session view and its panels. The "Route / Page" column
> below uses the app root (`/`) + the in-app panel. No frontend code changed
> this phase — every surface below is the **existing** renderer carrying new
> backend-produced content (verified in `ActivityLogEntry.tsx` /
> `ActivityLogGroup.tsx`, not assumed).

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| `/` → Session view, **Activity** panel (left) | `ActivityLogGroup` accordion list | Changed behavior | Open-universe run now staged SCREEN→PROMOTE; each config is its own group | Start an open-universe run (chat: no symbol/timeframe, `objective:"robust"`, tiny budget, Auto-Run); after it reaches terminal, count accordion groups in the left Activity panel — assert **≥3 groups whose header begins `SCREEN N done — …`** and **exactly k groups whose header begins `PROMOTE done — …`** with **k < the SCREEN count** (expected 4 SCREEN / 2 PROMOTE) |
| `/` → Session view, **Activity** panel | `ActivityLogEntry` (`type:"auto-run"`, violet row, `Zap` icon) | Changed behavior | New per-config markers `SCREEN config N: …` / `PROMOTE config: …` | Expand a screened group — assert the violet marker row reads exactly `SCREEN config <N>: <SYMBOL> <TF>`; expand a promoted group — assert it reads `PROMOTE config: <SYMBOL> <TF> (top-<k> survivor; in-sample Sharpe <num>)` |
| `/` → Session view, **Activity** panel | `ActivityLogEntry` (`type:"complete"`, green callout) / `ActivityLogGroup` collapsed header status line | Changed behavior | Screen vs promote completion summaries differ; "no walk-forward" stated for screen | On a `SCREEN` group assert the green summary contains `in-sample Sharpe` AND the literal `(cheap screen — no walk-forward)`; on a `PROMOTE` group assert the green summary contains `robust ` AND `walk-forward WFE ` (a numeric or `n/a`) — and that the SCREEN summary does **not** contain `walk-forward WFE` |
| `/` → Session view, **Activity** panel | `ActivityLogEntry` (`type:"insights"`, blue card + suggestion chips) | Changed behavior | Insights spent only on promoted survivors | Expand every `SCREEN` group → assert **no** blue insights card present; expand every `PROMOTE` group → assert a blue insights card **is** present with ≥1 suggestion chip |
| `/` → Session view, **Iterations** panel (right) | `IterationPanel` rows + "best" badge | Changed behavior | Best is robust-selected from promoted (WF-bearing) iterations only | After the run, locate the highlighted "best" iteration in the right panel — assert it corresponds to a **PROMOTE** iteration (carries walk-forward data + the stronger requested model), and that a screened-only iteration (no walk-forward, cheaper model) is **not** marked best even if its raw return is higher |
| `/` → Session view, **Iterations** panel | `IterationPanel` per-iteration walk-forward / model display | Changed behavior | Promoted iterations carry WF + stronger model; screened-only do not | Open a screened iteration — assert it shows **no** walk-forward result and the cheaper screening model name; open a promoted iteration — assert it shows a populated walk-forward result and the stronger requested model name |
| `/` → Session view, **AutoRunBar** (top of session) | `AutoRunBar` status text + spend readout | Changed behavior | Configs-spent now counts promoted configs only; staged run still terminates within budget | After the tiny-budget run, assert the bar shows `Automated run complete · budget reached · i/max iterations` (amber, `CircleDollarSign` icon) and the right-aligned spend readout `… tok / $… / N cfg` where **N equals the number of PROMOTE groups**, not screened+promoted |
| `/` → Session view, **Activity** panel (pinned run) | `ActivityLogGroup` / `ActivityLogEntry` | No change (regression guard) | Pinned path byte-unchanged; B1 must not suppress final-iteration insights | Start a **pinned** headless run (symbol+timeframe supplied, e.g. 3 iterations); assert rows read `Automated iteration i/max` + `Backtest complete — …` with **no** `SCREEN`/`PROMOTE` text, and that the **final** iteration's group still contains a blue insights card (B1 regression: final iteration insights NOT suppressed by the configs cap) |
| `/` → Session view (session switching) | Session tabs + `AutoRunBar` live status | No change (regression guard) | J-08: live status must not go stale under switching | While an open-universe run is active, switch to another session tab and back — assert the `AutoRunBar` resumes showing live `running … iteration i/max` (not a stale terminal state) and the Activity panel keeps appending new `SCREEN`/`PROMOTE` groups |
| `/` → Session view (prior run rebind) | `IterationPanel` trades table + right analysis panel | No change (regression guard) | J-02: prior run's trades table + analysis panel must re-bind | Open a session that already has a completed prior run, select a prior iteration — assert the trades table and right-hand analysis panel re-populate with that iteration's data (not blank, not stale from a different iteration) |

<!-- Change Type used: "Changed behavior" (existing surface, new content) and
     "No change (regression guard)" for required-still-passing journeys. No
     "New page / New component / Added navigation" — zero new UI surface. -->

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/shared/model_catalog.py` — new `cheapest_model()` helper
  (lowest combined per-token cost in `MODEL_PRICING`, table-resolved, ties
  broken on model id). Pure internal resolution; no API/response shape change.
  Its only indirect UI effect is the model name shown on screened iteration
  nodes — no dedicated surface.
- `apps/backend/backend/auto_session.py` internal control flow —
  `_run_pinned` / `_run_staged_open_universe` extraction, `_evaluate_one`
  shared evaluator, `_should_skip_insights` / `_SPEND_CAPS` (carried B1 gate),
  `_read_stop_requested`, staged `max_configs` semantics, SCREEN-via-subprocess
  seam. These determine *what content* the existing activity feed receives but
  add **no** new endpoint, response field consumed by new UI, or surface. The
  additive `stage` field on iteration nodes is written but not rendered as a
  distinct UI element (see user-visible-changes "Not Visible Yet").
- `apps/backend/tests/test_auto_session.py`, `tests/test_model_pricing.py` —
  test-only; no UI surface.

---

## Summary

- **Frontend surfaces changed:** 0 new (5 existing surfaces carry new
  content/behaviour: Activity panel groups, auto-run markers, complete
  summaries, insights cards, Iterations panel; AutoRunBar spend semantics)
- **New pages/routes:** 0 (single-page tabbed app; no router; no new surface)
- **Modified components:** 0 frontend files modified (verified — existing
  `ActivityLogEntry` / `ActivityLogGroup` / `IterationPanel` / `AutoRunBar`
  render the new backend-produced content unchanged)
- **Navigation changes:** no
- **Backend-only changes:** 4 files (`model_catalog.py`,
  `auto_session.py` internal flow, 2 test files) — surfaced to the user only
  through the existing session activity feed + iterations panel
