# Goal Iteration 7 — Implementation Summary

**Phase:** goal-financial_free-iter-7 — J-16: robust-objective overfit-gating leaderboard (the final journey)
**Date:** 2026-05-24
**Written by:** developer

---

## Features Implemented

- **Candidate leaderboard after an automated search**: When you start an automated, open-universe optimization run, the right-hand **Iterations** panel now shows a ranked **leaderboard** of the strategy candidates the optimizer tried. Each row shows the trading pair and timeframe, whether it was a cheap first-pass ("SCREEN") or a fully-validated finalist ("PROMOTE"), its robust score, total return, walk-forward efficiency (WFE, color-graded green/amber/red), number of trades, and max drawdown.
- **The chosen "best" is highlighted and explained**: The candidate the optimizer marked as best is highlighted with a "BEST" badge. Every other candidate shows a short **reason it wasn't chosen** — for example "WFE 0.21 < 0.30" (failed the walk-forward gate), "over-leveraged (margin called)", "screened — not walk-forward validated", or "lower robust score". This makes the optimizer's skeptical, overfit-resistant decision transparent: you can see at a glance that a flashier higher-return candidate was rejected because it didn't hold up out-of-sample.
- **Control how many finalists are validated (`promote_k`)**: The automated-session request (`POST /api/auto-sessions`) accepts an optional `promote_k` (a whole number 1–3, default 1). It controls how many of the top screened candidates get the expensive full validation (walk-forward + the stronger model). Raising it to 2 or 3 lets the leaderboard show several validated finalists side by side. Values outside 1–3 are rejected with a clear error.

---

## Changed Behavior

- **Automated open-universe runs now record a leaderboard**: Previously, an open-universe automated run marked a single "best" iteration but kept the per-candidate competition hidden. Now the same run additionally records and displays the full ranked candidate list. The way the best is chosen is unchanged — it is still the walk-forward-validated, WFE-passing, drawdown-penalized winner. No extra AI tokens are spent to build the leaderboard (it is assembled from numbers the run already computes).
- **Pinned (single-strategy) automated runs are unchanged**: They continue to show an improvement-rounds tree with no leaderboard. The leaderboard appears only for open-universe searches.

---

## Backend-Only Items

- None. Every new value the backend serves (`leaderboard`) is shown in the UI; the new request field (`promote_k`) maps to existing run behavior.

---

## Incomplete Items

- **Browser/pixel verification is pending the downstream QA step**: The data layer is proven by automated tests and by a real live run (which produced a 3-row leaderboard with a correctly WFE-gated best), and the front-end compiles and lints clean. The final on-screen pixel confirmation in a real browser is performed by the browser-QA step that runs after development (the dev handoff documents the exact port settings and the run recipe it needs).

---

## Config and Environment Changes

- No new environment variables, no migrations, no new infrastructure. The leaderboard is stored on the existing automated-session record in the existing file store and served by the existing `GET /api/sessions/{id}` endpoint.
- New optional request field on `POST /api/auto-sessions`: `promote_k` (integer 1–3, default 1).

---

## Known Limitations

- The leaderboard is shown for **open-universe** automated searches only (the kind started without pinning a symbol/timeframe). A pinned single-strategy automated run does not produce a leaderboard.
- For the walk-forward efficiency (and therefore the best) to be meaningful in a live run, the run's date range must be at least ~9 months (the in-sample + out-of-sample windows need room to form). Shorter ranges produce no walk-forward windows and no gated best.
- One pre-existing, unrelated test (`test_directions_cache.py::test_write_and_read_full_round_trip`) remains red; it is a documented carry-forward item untouched by this work.
