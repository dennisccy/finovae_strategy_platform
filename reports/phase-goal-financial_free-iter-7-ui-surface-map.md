# Phase goal-financial_free-iter-7 — UI Surface Map

**Phase:** goal-financial_free-iter-7 — J-16: robust-objective overfit-gating leaderboard UI (the FINAL journey)
**Date:** 2026-05-24
**Written by:** ui-impact-analyst

---

## Affected UI Surfaces

| Route / Page | Component / Element | Change Type | Why Changed | What to Test |
|-------------|--------------------|-----------:|------------|-------------|
| `/` (session view, right-hand **Iterations** panel) | `AutoSessionLeaderboard` (new card) | New component | J-16 surfaces the optimizer's per-candidate overfit-gating decision as a ranked leaderboard | Open a session that ran an open-universe auto-run with ≥2 candidates; confirm a "Candidate leaderboard" card appears between the status strip and the iteration tree, with one row per evaluated candidate |
| `/` (Iterations panel) | `AutoSessionLeaderboard` — row ordering | New component | Rows ranked by canonical robust score descending | Confirm rows are ordered by robust score high→low; null/ineligible-score rows sort to the bottom; verify the `#1` row has the highest displayed robust score |
| `/` (Iterations panel) | `AutoSessionLeaderboard` — BEST highlight | New component | Mark which candidate the optimizer chose (`bestIterationId`) | Confirm exactly one row has a violet background + "BEST" badge, and its `iterationId` equals `autoRun.bestIterationId`; confirm it is a WFE-passing PROMOTE candidate |
| `/` (Iterations panel) | `AutoSessionLeaderboard` — gating reason | New component | Show why a higher-return candidate was NOT chosen | Set up / open a run where a higher-return candidate has WFE < 0.3 or is over-leveraged; confirm that candidate is present, is NOT marked best, and shows a red gating reason citing the cause (e.g. "WFE 0.21 < 0.30" or "over-leveraged (margin called)") |
| `/` (Iterations panel) | `AutoSessionLeaderboard` — WFE chip | New component | Reuse the established emerald/amber/red WFE semantics | Confirm a WFE ≥0.5 row shows an emerald chip, ≥0.3 amber, <0.3 red, and a SCREEN-stage row shows `WFE —` (no walk-forward) |
| `/` (Iterations panel) | `AutoSessionLeaderboard` — stage badge | New component | Distinguish cheap SCREEN candidates from walk-forward-validated PROMOTE candidates | Confirm each row carries a SCREEN (slate) or PROMOTE (blue) badge, and only one row per `SYMBOL TIMEFRAME` family appears (deduped) |
| `/` (Iterations panel, empty/terminal state) | `AutoSessionLeaderboard` — empty handling | New component | Avoid crash on manual sessions or zero-candidate runs | Open a manual (non-auto) session and a terminal auto-run with zero completed candidates; confirm the leaderboard renders nothing (no error, no empty card) |
| `/` (Iterations panel) | `IterationPanel` (wiring) | Updated layout | Mounts `<AutoSessionLeaderboard>` after the status strip in both populated and empty-state returns | Confirm the leaderboard position is consistent (immediately under the status strip, above the iteration tree) in both the populated and the "Waiting for the first iteration…" states |
| `/` (mobile "Iterations" tab) | `AutoSessionLeaderboard` (responsive) | Updated layout | Leaderboard must be usable on mobile | On a narrow viewport, switch to the "Iterations" tab; confirm rows wrap cleanly and all metrics/badges remain readable |
| `POST /api/auto-sessions` | `promote_k` request field | New form / changed behavior (API) | Bounded enabler so ≥2 candidates reach walk-forward and the gating is demonstrable | Send `promote_k: 2` → 200 and the run promotes up to 2 candidates; send `promote_k: 0` or `4` → 422 with a clear message; omit the field → 200 with default-1 behavior |

---

## Backend-Only Changes (No UI Impact)

- `apps/backend/backend/auto_session.py` — leaderboard accumulation state (`_leaderboard`, `_leaderboard_metrics`), helper methods (`_leaderboard_list`, `_gating_reason`, `_record_leaderboard`, `_refresh_gating_reasons`, `_json_safe_score`), `AutoSessionConfig.promote_k`, and `k = min(config.promote_k or DEFAULT_PROMOTE_K, n_screened)` — these compute and persist the data the leaderboard reads, but are not themselves a UI surface (the data is served verbatim via the existing `GET /api/sessions/{id}` poll the UI already does).
- `apps/backend/tests/test_auto_session_leaderboard.py` (new) and `apps/backend/tests/test_auto_session_routes.py` — hermetic tests; no UI impact.
- `apps/frontend/src/lib/sessionApi.ts` — additive `LeaderboardEntry` type + `leaderboard?` on `AutoRunStatus`; type-only, consumed by the component above.
- `apps/frontend/src/hooks/useBacktest.ts` — re-export of `LeaderboardEntry`; type-only, no rendered change.

---

## Summary

- **Frontend surfaces changed:** 1 new component (`AutoSessionLeaderboard`) rendered in the Iterations panel, plus the `IterationPanel` wiring and the `POST /api/auto-sessions` request contract.
- **New pages/routes:** 0 (no new route — new card inside the existing session view's Iterations panel).
- **Modified components:** 1 (`IterationPanel` — adds the leaderboard mount point in both returns).
- **Navigation changes:** no (no new screen, no nav-skeleton change; home is the pre-registered "Best badge / leaderboard → Right — Iterations" blueprint slot).
- **Backend-only changes:** 4 files (`auto_session.py`, two test files, plus the type-only `sessionApi.ts`/`useBacktest.ts` extensions that feed the component).

> **Browser-QA note (LOAD-BEARING):** J-16 is a genuinely new front-end render path — pixel verification in a real, foreground, uncontended browser tab is mandatory and an endpoint-only substitute is NOT acceptable. The FE binds an offset port (FE `:3691` / BE `:8691` per `scripts/dev.sh`); the browser-QA harness must probe those ports (export `CHAIN_FRONTEND_PORT=3691 CHAIN_BACKEND_PORT=8691 …`), not the default `:3000`/`:8000`. Use a `promote_k: 2` open-universe run with a date range ≥ 9 months so PROMOTE forms ≥1 walk-forward window. A real populated session is available at `.data/backtests/live/2a829f6e-9762-467e-b32d-d2336724b2df`.
