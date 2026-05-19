# Phase goal-auto-money-printer-iter-3 — UX Regression Review

**Date:** 2026-05-19

**Verdict:** UX-REGRESSION-PASS

Frontend Present: yes. New capabilities (open-universe results, recorded
spend, distinct budget-exhausted terminal) are all discoverable in ≤2 clicks
and correctly labeled. The frontend diff is purely additive and the
prior-journey-bearing components are byte-unchanged, so there is no regression
risk to J-01–J-11. Two captured-but-unrendered data fields (budget-cap
headroom, wall-clock) are explicitly scoped out of this iteration's spec and
are forward-looking refinements, not hidden delivered capabilities.

---

## New Capability Discoverability

### J-12 — Open-universe search (objective + budget, no symbol/timeframe)

| Question | Assessment |
|---|---|
| Navigation path to results? | Yes — created session appears in the session list/sidebar via the existing iter-1 ~5 s discovery poll, under **LIVE SESSIONS** with a running indicator. |
| Reachable within 2 clicks? | Yes — Sessions button → Live Sessions row → opens the normal two-panel view; ≥2 distinct configs render in the existing iteration tree as `IterationCard`s. Browser QA UT-02/UT-03/UT-11 confirm ≤2 clicks. |
| Label clear to a non-technical user? | Yes — configs render in the standard `<symbol> · <timeframe> · <range> · $<capital>` card format; exactly one carries the existing robust `BestBadge` ("Best iteration — selected by the robust walk-forward objective"). |
| Visual feedback when used? | Yes — iterations stream live into the tree; `AutoRunBar` shows running → terminal without a manual reload. |

**Trigger is API-only by explicit, goal-aligned design — not a flaggable
hidden capability.** The phase spec ("New user actions: None net-new —
open-universe is API-triggered"), the execution plan, and `docs/goal.md`'s
J-12 journey itself all define the trigger as `POST /api/auto-sessions`. There
is deliberately no UI start-search/leaderboard control this iteration; the
*results* are fully surfaced through the existing UI. This is a documented
product boundary, consistent with the goal, not an undiscoverable feature.

### J-13 — Recorded spend + budget-exhausted terminal

| Question | Assessment |
|---|---|
| Navigation path? | Yes — surfaced in the existing always-visible `AutoRunBar` strip at the top of any auto-session view. |
| Reachable within 2 clicks? | Yes — same ≤2-click path as J-12; no extra navigation. |
| Label clear? | Yes — `<tok> tok · $<usd> · <n> cfg` with tooltip "AI tokens / USD / configs spent under the hard budget"; terminal text "Automated run complete · budget reached · X/Y iterations". |
| Visual feedback? | Yes — spend increments live across poll cycles, freezes at terminal, and persists across a hard reload (durable `autoRun.spend`). `budget-exhausted` is now its own amber + `CircleDollarSign` style, distinct from emerald `criteria-met` and red `stopped`. Browser QA UT-04/UT-05/UT-06 confirm. |

## Regression Risk

Method: ui-regression-scout intersection of this phase's `ui-surface-map`
changed components against prior-phase handoff components.

| Shared component | Prior feature served | This phase's change | Risk |
|---|---|---|---|
| `AutoRunBar` (`SessionContainer.tsx`) | J-08 live status, J-09 terminal stop reason, J-11 `stopped` state | Purely additive: split `budget-exhausted` out of the generic green branch into its own amber branch (this *strengthens* J-09's "visible stop reason"); appended an `ml-auto` spend `<span>`. `stopped`/red and `criteria-met`/emerald branches functionally unchanged. | **Low** — browser QA UT-05/UT-08 PASS |
| `useBacktest.ts` | J-02 heavy-detail merge precedence, J-08 mount re-derive, iter-2 `try/finally` live-poll re-arm | **Type-only** — added `AutoRunSpend` interface + optional `spend?` field. Verified via diff: zero poll/effect/merge lines changed (the existing poll already passes the whole `autoRun` object through `setAutoRun`, so the field flows automatically). | **Low** |
| `App.tsx`, `IterationPanel.tsx`, `IterationCard.tsx`, `IterationDetailView.tsx`, `sessionApi.ts` | J-02 right-panel re-bind, J-08 discovery poll, J-09 `BestBadge` | **Not touched this iteration** (verified via `git diff --stat`). | **None** |
| `auto_session.py` (backend, drives the UI data for J-07–J-11) | Pinned auto-session journeys J-07–J-11 | Heavily edited (multi-config controller + cost tracker), but the 422 gate relaxation only fires for the open-universe shape; the pinned path keeps byte-for-byte validation. Reviewer + QA verified zero new regressions (183 passed / 1 pre-existing out-of-scope fail). Browser QA UT-10 confirms pinned/validation behavior; UT-09 re-verifies J-02 right-panel re-bind; UT-08 re-verifies J-08 no-stale-terminal. | **Low** — well-guarded, re-verified |

No prior user journey regresses: the only user-journey-bearing frontend
component touched (`AutoRunBar`) changed additively, and every prior-feature
component was either byte-unchanged or independently re-verified PASS by
browser QA (UT-07 legacy/manual graceful, UT-08 J-08, UT-09 J-02).

## UI vs Backend Parity

| Backend capability built | UI exposure | Status |
|---|---|---|
| Open-universe bounded-seed controller (J-12) | ≥2 distinct configs in the existing iteration tree + robust `BestBadge` | **Surfaced** |
| Immutable cost tracker — token/USD/configs spend (J-13) | `AutoRunBar` spend readout (live + durable) | **Surfaced** |
| `budget-exhausted` hard-stop terminal | Distinct amber + `CircleDollarSign` `AutoRunBar` state | **Surfaced** |
| Real SDK usage capture + per-model USD price table | Feeds the `$<usd>` figure (indirect, appropriate) | **Surfaced (indirect)** |
| Durable budget **caps** (`caps.aiTokens/usd/configs/wallClockSeconds`) | Not rendered — bar shows spend, not "spent / allowed" | **Captured, not shown** (spec-scoped-out) |
| `wallClockSeconds` spend | Captured + typed (`AutoRunSpend.wallClockSeconds?`) but not rendered | **Captured, not shown** (spec-scoped-out) |
| `history_scope` request field | Accepted & persisted; no visible effect | **Correctly invisible** — its learning behavior is J-15 / OUT OF SCOPE |

The core delivered capabilities are all surfaced and discoverable. The
unshown caps/wall-clock are **not hidden delivered capabilities** — the
phase spec's "New information displayed" section mandates only
tokens/USD/configs + a clear budget-exhausted reason (all delivered), and
`user-visible-changes.md` explicitly documents caps/wall-clock as "Not
Visible Yet" / future-iteration refinements. The goal.md J-13 acceptance
("recorded spend ≤ cap, visible in the status block; hard stop") is met:
spend is visible and the hard-stop guarantee is communicated by the distinct
amber terminal state.

## Flags

### Hidden Capabilities
- None. The open-universe **trigger** is API-only, but that is an explicit,
  goal-aligned spec decision (the J-12 journey in `docs/goal.md` itself
  triggers via `POST /api/auto-sessions`), not a built-but-unreachable UI
  capability. The *results* have a clear ≤2-click navigation path.

### Undiscoverable Capabilities
- None. Open-universe results and the spend readout are both reachable in
  ≤2 clicks (Sessions → Live Sessions row), confirmed by browser QA UT-11.

### Potential Regressions
- None blocking. `AutoRunBar` is shared with J-08/J-09/J-11 but the change is
  purely additive; the J-02/J-08/J-09 components (`useBacktest.ts` poll/merge,
  `App.tsx`, `IterationPanel/Card/DetailView`) are byte-unchanged; browser QA
  re-verified J-02 (UT-09), J-08 (UT-08), legacy/manual (UT-07) — all PASS.
- Informational: every automated run (including prior pinned J-07–J-11
  sessions) now records spend and shows the readout once spend exists. This is
  an additive enhancement, gracefully degrading (UT-07: no `spend` →
  byte-identical pre-iter-3 bar, no NaN/undefined), not a regression.
- Informational (not label confusion): an `Auto: <nl>` session is renamed to
  the generated strategy title once its first config generates. This
  *satisfies* the anti-goal "a headless run MUST be indistinguishable in the
  UI from a manual one" and does not impede discovery (the row stays under
  LIVE SESSIONS with a running indicator — UT-02 PASS). Intentional, not a
  defect.

### Visual Consistency
- New pages: none (single-page app; one additive readout inside the existing
  `AutoRunBar` strip — by spec design).
- The new `budget-exhausted` amber branch (`bg-amber-50 border-amber-200
  text-amber-700`, `text-amber-600` icon) is structurally identical to the
  established `red`/`emerald`/`primary` tone-class pattern in the same
  component, and amber is already the app's attention color (the iter-1 "★
  Best" pill, the session-list `running` label). `CircleDollarSign` is from
  the existing `lucide-react` set (`Loader2`/`CheckCircle2`/`StopCircle`).
- Spend `<span>` uses only DESIGN-SYSTEM tokens: `ml-auto shrink-0
  tabular-nums opacity-75 text-xs`. **No arbitrary hex, inline `style`, or
  bracket values introduced** (verified via diff). Visually consistent with
  prior phases — dense, dark, data-forward; no invented effects.

## Recommendation

**No blocking action required — shippable from a UX-regression standpoint.**

Forward-looking (non-blocking; for a future iteration, explicitly out of this
phase's scope):

1. **Render spend against its cap** ("`12,480 / 20,000 tok`") so a user can
   judge headroom *during* a run, not only infer it from the terminal amber
   state. The `caps.*` data already rides in the durable `autoRun` block /
   `GET /api/sessions/{id}`; only the `AutoRunBar` readout would need to read
   it. This closes the one real (currently scoped-out) UI-vs-backend
   legibility gap.
2. **Surface wall-clock spend** alongside tokens/USD/configs —
   `wallClockSeconds` is already captured and typed in `AutoRunSpend`.

These are refinements to information already in the API payload, not new
capabilities, and were correctly deferred per the phase spec's IN SCOPE
boundary.
