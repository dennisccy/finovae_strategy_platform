# Phase N — User-Visible Changes

**Phase:** goal-auto-money-printer-iter-4
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

<!-- The trigger and controls are unchanged; the new capability is what the
     operator now SEES happen during/after an open-universe run. -->

- Start a headless **open-universe** run exactly as before — chat panel, no
  symbol/timeframe, `objective:"robust"`, small budget, "Auto-Run" — and now
  watch the run **screen several cheap candidates first and promote only a
  small handful to the full expensive analysis**, all in the existing session
  Activity panel (left side of the session view). No new button, page, or
  control.
- Read, per screened candidate, a `SCREEN config N: <SYMBOL> <TF>` row and a
  `SCREEN N done — <SYMBOL> <TF>: in-sample Sharpe …, return …%, … trades
  (cheap screen — no walk-forward)` summary — i.e. see the cheap shortlist and
  its cheap score, with an explicit "no walk-forward" disclaimer.
- Read, per promoted survivor, a `PROMOTE config: <SYMBOL> <TF> (top-k
  survivor; in-sample Sharpe …)` row and a `PROMOTE done — <SYMBOL> <TF>:
  return …%, … trades, robust …, walk-forward WFE …` summary, plus an AI
  **insights** card — visible proof that walk-forward, the stronger model, and
  insights were spent **only on survivors**.
- Confirm at a glance that fewer configs were promoted than screened (e.g. 4
  `SCREEN` groups, 2 `PROMOTE` groups) by counting the accordion groups in the
  Activity panel.
- See the run still reach a terminal state within the tiny budget — the
  `AutoRunBar` shows `Automated run complete · budget reached · i/max
  iterations` (amber, dollar icon) with the live spend readout
  (`… tok / $… / … cfg`).

---

## What Changed in the Visible UI

<!-- No frontend code changed. These are content/behaviour changes that flow
     through the existing renderer (verified, not assumed). -->

- The session **Activity panel** (left panel of the session view, rendered by
  `ActivityLog → ActivityLogGroup → ActivityLogEntry`) now shows, for an
  open-universe run, a sequence of `SCREEN …` accordion groups followed by a
  smaller set of `PROMOTE …` accordion groups, instead of the prior
  `Exploring config N: …` groups. Each config is its own collapsible group;
  the collapsed header status line begins with the literal `SCREEN N done — …`
  or `PROMOTE done — …` text (the leading stage word is never truncated — only
  a trailing single-line ellipsis applies on overflow).
- A blue **AI insights** card with suggestion chips now appears **only inside
  `PROMOTE` groups**. Screened-only groups have no insights card.
- The right **Iterations panel** shows promoted iterations carrying
  walk-forward results and the stronger requested model, while screened-only
  iterations show no walk-forward result and the cheaper screening model name.
  (Iteration nodes also carry a new additive `stage` value of `"screen"` /
  `"promote"`; the typed frontend does not render this field explicitly and
  ignores it at runtime — see "Not Visible Yet".)
- The `AutoRunBar` spend readout's `… cfg` figure now counts **promoted**
  (expensive) configs only; cheap screened candidates are not counted toward
  the configs figure. The bar component itself is unchanged.

---

## What Old Behavior Changed

<!-- Regression-relevant: what testers must re-verify. -->

- **Open-universe run activity text:** previously every explored config showed
  `Exploring config N: …` and ran the full pipeline (walk-forward + requested
  model + insights). Now the same run shows `SCREEN …` then `PROMOTE …`, and
  only the promoted configs run walk-forward / the stronger model / insights.
- **"Best" selection (unchanged invariant, changed candidate pool):** the
  final best iteration is still chosen by the robust walk-forward objective —
  but now drawn **only from promoted (walk-forward-bearing) iterations**. A
  screened-only candidate (no walk-forward) can never be marked best, even
  with a higher raw return. Operators must re-verify the highlighted "best"
  badge points at a `PROMOTE` iteration, not a `SCREEN`-only one.
- **Configs-spent count:** the `… cfg` number in the spend readout now
  increments per **promoted** config, not per explored config. A J-13
  re-verification must read it against the new staged semantics (it equals
  promoted configs, not screened+promoted).
- **Pinned (single-strategy) headless run:** behaviourally **unchanged** for
  the operator — still `Automated iteration i/max` + `Backtest complete — …`
  rows, full pipeline every iteration, the same prompt-refinement chain, and
  **no** `SCREEN`/`PROMOTE` rows. The only internal change (the B1 spend-cap
  insights gate) is a no-op on a normal run; its observable guarantee is that
  the **final pinned iteration still gets its insights/suggestions** (it must
  NOT be silently suppressed by the configs cap).
- **Legacy / pre-existing sessions:** old open-universe or pinned sessions
  reopened from history show their original entries with **no** SCREEN/PROMOTE
  rows (graceful — feed unchanged for old runs).

---

## Not Visible Yet

<!-- Backend capability with no dedicated UI affordance. Distinguishable, but
     not surfaced as an explicit labelled control. -->

- **No dedicated stage badge/label.** Iteration nodes carry a new `stage`
  field (`"screen"` / `"promote"`), but the frontend does not render it as a
  chip, color, or label. An operator distinguishes the two stages only by the
  `SCREEN`/`PROMOTE` text prefix in the activity content and by the
  presence/absence of walk-forward data — there is no explicit "Stage: screen"
  UI element. This is intentional for this iteration (no new component), but
  the staging is inferred from text, not shown as structured UI.
- **`cheapest_model()` resolution is internal.** Which model is "cheapest" is
  resolved from the price table at run time; the operator only sees its
  *effect* (the cheaper model name on screened iteration nodes / the stronger
  model on promoted ones), never the catalog lookup itself.
- **The in-sample rank proxy and top-k (k) cutoff are not displayed as
  numbers.** The operator sees *which* configs were promoted (they get
  `PROMOTE` groups) and the screened in-sample Sharpe in text, but the ranking
  computation and the exact k value are not shown as a dedicated UI element —
  k is inferred by counting `PROMOTE` groups (currently 2) vs `SCREEN` groups
  (currently 4).
