# Phase goal-financial_free-iter-7 — User-Visible Changes

**Phase:** goal-financial_free-iter-7 — J-16: robust-objective overfit-gating leaderboard UI (the FINAL journey)
**Date:** 2026-05-24
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

- After an open-universe automated run, users can now see a **ranked candidate leaderboard** in the right-hand **Iterations** panel — every candidate the optimizer evaluated, ordered top-to-bottom by the robust score.
- Users can now tell **at a glance which candidate was chosen as best** — the winning row is highlighted in violet and tagged with a "BEST" badge.
- Users can now see **why a rejected candidate was not chosen** — each non-best row shows a plain-language gating reason (e.g. "WFE 0.21 < 0.30", "over-leveraged (margin called)", "0 trades", "screened — not walk-forward validated", "lower robust score").
- Users can now compare candidates side by side on the metrics that matter: robust score, total return, walk-forward efficiency (WFE, color-graded), number of trades, and max drawdown.
- Users can now distinguish **SCREEN** vs **PROMOTE** candidates via a stage badge — telling cheaply-screened candidates apart from the ones that went through walk-forward validation.
- Users can now request a run that promotes **more than one** candidate to walk-forward validation by sending the optional `promote_k` field (1–3) on the `POST /api/auto-sessions` request — making the overfit-gating competition visible with multiple validated candidates.

---

## What Changed in the Visible UI

- The right-hand **Iterations** panel now renders a new **"Candidate leaderboard"** card, between the auto-session status strip and the iteration tree. It appears in both the populated view and the empty-state view, and also under the mobile "Iterations" tab.
- The leaderboard header shows a Trophy icon, the title "Candidate leaderboard · ranked by robust score", and a live count of candidates ("N candidates").
- Each leaderboard row shows: rank (#1, #2, …), family (`SYMBOL TIMEFRAME`), a SCREEN/PROMOTE stage badge, the canonical robust score, total return, a color-graded WFE chip (emerald ≥0.5 / amber ≥0.3 / red <0.3, or `WFE —` for screen-only rows), trade count, and max drawdown.
- The marked-best row is visually highlighted (violet background) with a violet "BEST" badge and Award icon — consistent with the existing best badge in the status strip.
- Non-best rows display their gating reason below the metrics: muted gray for eligible-but-not-best candidates, red for ineligible (gated-out) candidates.

---

## What Old Behavior Changed

- **`POST /api/auto-sessions` request:** now accepts an optional `promote_k` field. When omitted, behavior is byte-identical to before (default 1 candidate promoted). A value outside 1–3 is rejected with HTTP 422. Existing callers that never send `promote_k` are unaffected.
- **No change** to how the "best" candidate is determined, scored, or marked — the leaderboard only surfaces existing decisions; it does not change them. Manual (non-auto) sessions and pinned-path runs show no leaderboard (unchanged behavior).

---

## Not Visible Yet

- The leaderboard is **open-universe only**. A pinned-path automated run (`_run_inner`) produces an improvement-rounds tree rather than a multi-candidate competition, so its `leaderboard` stays empty and the component renders nothing for pinned runs. This is intentional and matches J-16 scope.
- There is no in-UI control for setting `promote_k` — it is currently only settable via the API request body, not via a form field in the UI.
