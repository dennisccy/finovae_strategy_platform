# Phase goal-auto-money-printer-iter-4 — Implementation Summary

**Phase:** goal-auto-money-printer-iter-4
**Date:** 2026-05-19
**Written by:** developer

---

## Features Implemented

- **Cheap-first staged screening for headless open-universe runs (J-14)**:
  A headless "explore the open universe" run now spends cheaply first. It
  quickly *screens* several candidate market configs (symbol + timeframe)
  using the cheapest available AI model, no walk-forward, and no AI
  improvement-insights — then *promotes* only a small handful of the best
  screened candidates to the full, expensive analysis (walk-forward
  validation + the stronger AI model + AI insights). The platform spends the
  expensive budget only on survivors.
- **Visible SCREEN vs PROMOTE staging in the existing activity feed**: The
  operator sees, in the same session activity panel as before, a row per
  screened config (`SCREEN config N: …` with its cheap in-sample score) and
  a row per promoted config (`PROMOTE config: …`). Promoted iterations carry
  walk-forward results and the stronger model; screened-only ones do not.
  No new screen, page, or component.
- **"Cheapest model" is always the genuinely cheapest catalog model**:
  Resolved at run time from the model price table, so it automatically
  tracks any future price change or newly added cheaper model.
- **Carried budget-accounting correctness fix (B1)**: When a hard *spend*
  budget (AI tokens / USD / wall-clock) is reached partway through a config,
  that config's AI insights call is now skipped (the iteration is still
  recorded) instead of overspending. Reaching only the *number-of-configs*
  limit does **not** skip insights — so the pinned (single-strategy) run's
  final iteration still gets its insights and improvement suggestions.

---

## Changed Behavior

- **Headless open-universe run (no symbol/timeframe supplied)**: Previously
  every explored config ran the full expensive pipeline (walk-forward + the
  requested model + insights), shown as `Exploring config N: …`. Now it runs
  the staged SCREEN→PROMOTE flow described above; the activity feed shows
  `SCREEN …` then `PROMOTE …` instead of `Exploring config …`. The "best"
  strategy is still chosen by the same robust walk-forward objective, now
  drawn only from the promoted (walk-forward-bearing) iterations — a
  higher-raw-return but unvalidated candidate is still never marked best.
- **Hard budget under the open-universe run**: The number-of-configs cap now
  counts the *expensive promoted* configs; cheap screening is bounded by the
  fixed seed list and the token/USD/wall-clock caps. The run still stops at
  `budget-exhausted` with no extra config started past any cap, and the
  recorded spend is still the real captured token usage.
- **Pinned (single-strategy) headless run**: Behaviour is unchanged for the
  operator — one config per iteration, full pipeline every iteration, the
  same prompt-refinement chain, no SCREEN/PROMOTE rows. (The only internal
  addition is the spend-cap insights fix above, which does not change a
  normal run.)

---

## Backend-Only Items

- None. The new capability is surfaced through the existing session activity
  feed (verified the renderer preserves the SCREEN/PROMOTE labelling without
  any frontend change). Browser QA validates the user-visible result.

---

## Incomplete Items

- None for this iteration's scope (J-14 + the carried B1 fix). Out of scope
  by design and **not** built: J-15 (cross-run global-history warm start /
  prompt-cached planner / `history_scope` *learning* — still
  accept-and-persist only) and J-16 (deep overfit-gating demonstration /
  leaderboard). The robust-best invariant J-16 relies on is preserved here.

---

## Config and Environment Changes

- None. No new environment variable, config file, datastore, queue,
  scheduler, external dependency, or pricing API. Optimizer state continues
  to persist in the existing durable file store.

---

## Known Limitations

- Live end-to-end validation with a real AI provider key is performed by
  browser QA under a tiny budget (the unit tests use a deterministic fake
  pipeline; no new external system was introduced to validate in isolation).
- The number of configs screened (4) and promoted (2) are small fixed
  constants chosen so a tiny-budget run still shows ≥3 screened and a
  smaller promoted set; they are not operator-configurable this iteration.
- If an extremely tiny *spend* cap is exhausted during the cheap screening
  stage itself, the run ends `budget-exhausted` before any config is
  promoted, so no "best" is marked for that run. This is the correct
  no-overspend behaviour; a normal tiny-budget run screens then promotes at
  least one config before any cap bites.
- A promoted iteration's recorded "model used" is the stronger requested
  model (it ran that iteration's insights); the underlying strategy code was
  generated once by the cheap screening model and reused unchanged (no
  regeneration) — this is intentional and documented in code.
