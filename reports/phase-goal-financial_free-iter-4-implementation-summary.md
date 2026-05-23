# goal-financial_free-iter-4 — Implementation Summary

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering for the open-universe search (J-14)
**Date:** 2026-05-23
**Written by:** developer

---

## Features Implemented

- **Cheap-first open-universe search (SCREEN→PROMOTE):** When you start an automated open-universe run (no specific symbol/timeframe), the optimizer now triages candidates cheaply before spending on the expensive work. It **SCREENs** several seed configurations on the cheapest available model with **no walk-forward**, then **PROMOTEs only the single best survivor** to a full evaluation — walk-forward analysis **and** a stronger model. You stop paying full price for every candidate.
- **Both stages are visible in the Activity Log:** The left-hand Activity Log shows a "SCREEN —" header (naming the cheap model and the number of candidates), one line per screened candidate with its score, then a "PROMOTE —" header ("top-1 of N") and the promoted winner. You can watch the cost-saving decision happen.
- **The marked "best" is trustworthy:** The single best result is chosen **only** from promoted candidates that passed walk-forward validation. A cheaply-screened candidate with a flashy raw return but no walk-forward can never be crowned best.
- **Visible lineage:** A promoted result appears in the iteration tree as a child of the screened candidate it came from. Promoted cards show the stronger model and a walk-forward section; screened-only cards show the cheap model and no walk-forward.

---

## Changed Behavior

- **Open-universe automated run:** Previously every seed configuration was evaluated identically — walk-forward analysis and the chosen model ran on **all** of them. Now only a cheap screening pass runs on all of them (no walk-forward, cheapest model), and the expensive walk-forward + stronger model run only on the top survivor. For an N-config run this turns N full evaluations into N cheap screens + 1 full evaluation.
- **"Best" marking on an open-universe run:** Previously the best could come from any evaluated config. Now it comes only from the promoted, walk-forward-validated candidate(s). If a run is stopped before anything is promoted, no "best" is marked yet (the screened candidates are still saved and browsable).
- **The single-strategy ("pinned") automated run is unchanged** — it still runs its improvement-rounds loop exactly as before.

---

## Backend-Only Items

- None. The new behavior is fully visible in the existing Activity Log and iteration cards/tree (which read the canonical `GET /api/sessions/{id}`). No new endpoint or hidden capability was added.

---

## Incomplete Items

- None of the in-scope J-14 items are deferred. All SCREEN/PROMOTE behavior, model routing, budget gating, activity-log visibility, and the required test scenarios are implemented and passing.
- **Browser pixel capture** of the live status-strip updates (J-08), reload-mid-run survival (J-10), and the new SCREEN/PROMOTE entries (J-14) is performed by the downstream browser-QA step against live services — it is not a developer deliverable. The backend behavior those pixels reflect is verified by a live end-to-end test.

---

## Config and Environment Changes

- None. No new environment variables, request fields, settings, or data-store changes. The PROMOTE model is the run's existing requested model; the SCREEN model is derived automatically from the model price table (cheapest tier). Live runs use the already-configured `OPENAI_API_KEY` (cheap SCREEN model) and `ANTHROPIC_API_KEY` (only when a Claude model is the requested PROMOTE model).

---

## Known Limitations

- **Stopping during the cheap SCREEN phase leaves no "best" yet.** This is intentional: the best is defined as a walk-forward-validated, promoted candidate, so before any promotion there is nothing eligible to crown. All screened candidates remain saved and browsable; nothing is lost. Stopping during/after promotion preserves the promoted best so far.
- **How many candidates get promoted is fixed at one** (the most cost-efficient setting) and is not user-configurable this iteration — there is deliberately no new request field. A future leaderboard journey (J-16) will surface multiple promoted candidates.
- **One pre-existing, unrelated test remains red** (`test_directions_cache` — about a different feature's data round-trip). It predates this work, is explicitly out of scope, and was not touched.
