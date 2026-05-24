# goal-financial_free-iter-7 Dev Handoff

**Phase:** goal-financial_free-iter-7 — J-16: robust-objective overfit-gating leaderboard UI (the FINAL journey)
**Date:** 2026-05-24
**Agent:** developer
**Status:** complete

## What Was Built

J-16 surfaces the optimizer's overfit-gating decision in the UI: after an open-universe automated run, the **Iterations** panel shows a ranked **leaderboard** of evaluated candidates, with the marked best highlighted and rejected candidates showing *why* they aren't best (gating reason). The robust objective already gated overfit at the scorer level (since iter-4); this iteration makes that gating **visible** — and adds the minimal enabler (`promote_k`) so it is demonstrable with real walk-forward-validated candidates.

**Backend (read-only projection — zero new scoring, zero new LLM tokens):**
- **Per-candidate `leaderboard` on the `autoRun` block.** As `_run_open_universe` scores each candidate at the EXISTING `self.scorer.score(...)` / `self.scorer.is_eligible(...)` call sites, the controller accumulates a `leaderboard` list (in-memory) and persists it via the existing `_save_auto_run` → `session_store.write_session_meta` path. Served by the existing `GET /api/sessions/{id}` (no new endpoint). Each entry carries ONLY the genuinely-new values: `iterationId`, `stage` (`screen`/`promote`), `robustScore` (the ONE `RobustScorer.score()` output; `-inf` → `null`), `eligible` (the ONE `is_eligible()`), `gatingReason` (a backend-narrated string). Display metrics are NOT duplicated — the FE joins them from `iterationHistory` by `iterationId`.
- **Dedup:** one row per `(symbol, timeframe)` family — a promoted family REPLACES its screen row with its PROMOTE node (its validated evaluation); screened-only families stay as screen rows.
- **`gatingReason`** is the only place the gate is narrated (`"best"`, `"WFE 0.21 < 0.30"`, `"over-leveraged (margin called)"`, `"0 trades"`, `"screened — not walk-forward validated"`, `"lower robust score"`), computed from the ONE `is_eligible` outcome + the one `bestIterationId`. The FE never re-derives it.
- **Bounded optional `promote_k` (1–3, default 1)** on `POST /api/auto-sessions` → threaded request → `AutoSessionConfig` → `_run_open_universe` as `k = min(config.promote_k or DEFAULT_PROMOTE_K, n_screened)`. Out of `[1,3]` → **422**. Omitted ⇒ byte-identical to today (locks J-12/J-13/J-14). The pinned path (`_run_inner`) ignores it.
- **No change** to `RobustScorer` / `BudgetTracker` / `select_best` / SCREEN-PROMOTE mechanics / seed bounds / `shared/contracts.py`. The best is still the one `bestIterationId` (no second best definition).

**Frontend (new render path — first since the auto-session UI):**
- **New `AutoSessionLeaderboard.tsx`** rendered inside `IterationPanel.tsx` after the status strip, before the iteration tree (both the populated and empty-state returns). Reads `autoRun.leaderboard`, joins each entry to its `iterationHistory` node by `iterationId` for display metrics, ranks rows by `robustScore` desc (ineligible/null last), highlights the row where `iterationId === autoRun.bestIterationId` with a violet "BEST" badge, shows family / stage badge / robust score / total return / color-graded WFE chip (emerald ≥0.5 / amber ≥0.3 / red <0.3; `—` for screen rows) / trades / drawdown / gating reason. Renders nothing for a manual session or a run with no candidates yet.
- **Additive types** in `sessionApi.ts`: `LeaderboardEntry` interface + `leaderboard?: LeaderboardEntry[]` on `AutoRunStatus` (re-exported from `useBacktest.ts`). No change to the lazy/heavy fetch model — the leaderboard rides the existing `GET /api/sessions/{id}` poll the UI already does (live updates without reload; survives reload).

## Files Changed
(matches `git diff --name-only HEAD -- apps/` + the two new untracked files under `apps/`)
- `apps/backend/backend/auto_session.py` — `_json_safe_score` helper; `AutoSessionConfig.promote_k`; controller leaderboard state (`_leaderboard`, `_leaderboard_metrics`) + methods (`_leaderboard_list`, `_gating_reason`, `_record_leaderboard`, `_refresh_gating_reasons`); `leaderboard` recorded at SCREEN + PROMOTE sites and persisted in `_save_auto_run`; `k = min(config.promote_k or DEFAULT_PROMOTE_K, n_screened)`; `leaderboard: []` added to `initial_auto_run`.
- `apps/backend/backend/auto_session_routes.py` — `promote_k: Optional[int]` on `CreateAutoSessionRequest` with a 1–3 `field_validator` (422 otherwise); threaded through `_build_config`.
- `apps/backend/tests/test_auto_session_leaderboard.py` — **NEW** J-16 hermetic tests (canonical-score, overfit-gating, over-leveraged variant, gating-reason branches, best==bestIterationId, default-k no-regression lock, promote_k=2 promotes-two, cost-cap-halts-mid-promote, empty leaderboard, persistence/reload survival, no-eager-parse via the route, no-secrets).
- `apps/backend/tests/test_auto_session_routes.py` — added `promote_k` route validation tests (1–3 → 200; 0/4 → 422; omitted → 200).
- `apps/frontend/src/components/AutoSessionLeaderboard.tsx` — **NEW** leaderboard component.
- `apps/frontend/src/components/IterationPanel.tsx` — render `<AutoSessionLeaderboard>` after the status strip in both returns.
- `apps/frontend/src/lib/sessionApi.ts` — `LeaderboardEntry` interface + `leaderboard?` on `AutoRunStatus` (additive).
- `apps/frontend/src/hooks/useBacktest.ts` — re-export `LeaderboardEntry` alongside `AutoRunStatus`.

## Tests Run
- **Backend:** `cd apps/backend && .venv/bin/python -m pytest` → **247 passed, 1 failed, 2 deselected**. The single failure is the documented carry-forward pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (unrelated — directions cache, untouched this iteration). All 12 new J-16 leaderboard tests + 4 new `promote_k` route tests pass.
- **Lint:** `cd apps/backend && .venv/bin/ruff check ...` → All checks passed.
- **Frontend:** `cd apps/frontend && npm run build` (tsc + vite) → clean; `npm run lint` (eslint, `--max-warnings 0`) → clean.

## Live verification (key-gated, optional — performed; non-blocking)
Started the backend on its offset port (`:8691`), POSTed an open-universe run with `promote_k: 2` and an 11-month range (`2023-01-01`→`2023-12-01`, ≥ IS+OOS so PROMOTE forms walk-forward windows). Result reached `budget-exhausted` and served a real **3-row deduped leaderboard** (2 PROMOTE + 1 SCREEN from 3 screened, 2 promoted):
- best (`bestIterationId`) = the highest-scoring **eligible** PROMOTE row, gating `"best"`, WFE-gated;
- 2nd PROMOTE row eligible, gating `"lower robust score"`;
- screened-only row gating `"screened — not walk-forward validated"`.
- Leaderboard entry keys were exactly `[eligible, gatingReason, iterationId, robustScore, stage]` — **no duplicated display metric**; the open path served **no eager `result.json`** payload; the leaderboard added **0 tokens** (real spend ~11.8k from the run's generates only); and it **persisted to `session.json`** (reload-survivable). Evidence captured at `/tmp/iter7_leaderboard_evidence.txt` during the run.
- Note: this real 2023 run happened to have all three candidates pass the WFE gate (so it did not by chance show a *rejected* overfit candidate). The deterministic **hermetic** overfit scenario (`test_overfit_gating_higher_return_wfe_fail_not_best`) is the binding proof that a higher-return/higher-score but WFE-failing candidate is present, `eligible:false`, and NOT best.

## Browser-QA (LOAD-BEARING — for the downstream browser-qa-agent)
This is a genuinely new front-end render path; per the iter-6 lesson an endpoint-only substitute is NOT acceptable. To verify pixels:
- **Harness port fix (the recurring root cause):** `./scripts/dev.sh` binds **FE `:3691` / BE `:8691`** (`base + sha1(repo)%1000`, offset `691`), but `browser-qa-phase.sh` defaults to probing `:3000`/`:8000`. Export `CHAIN_FRONTEND_PORT=3691 CHAIN_BACKEND_PORT=8691 CHAIN_FRONTEND_URL=http://localhost:3691 CHAIN_BACKEND_HEALTH_URL=http://localhost:8691/health` and **health-re-probe across the whole QA window** (FE is torn down mid-window in prior iters). Keep the QA tab **foreground and uncontended** (hidden-tab render throttle → blank pixels, per MEMORY — that's not an app bug). *This harness fix is out of product scope — commit separately if a maintainer applies it.*
- **Recipe:** trigger an open-universe run with `promote_k: 2` and a date range **≥ 9 months** (so PROMOTE forms ≥1 walk-forward window — else `wfe 0.0` → `best=None` and the demo is vacuous), open the session, confirm: ranked candidate rows, the best row highlighted with "BEST", color-graded WFE chips, a non-best row showing its gating reason. The live session created during dev (`.data/backtests/live/2a829f6e-9762-467e-b32d-d2336724b2df`) is a real populated example to open.

## Known Issues
- The leaderboard is **open-universe only** (the pinned `_run_inner` path produces an improvement-rounds tree, not a multi-candidate competition — `leaderboard` stays `[]` and the component renders nothing). This matches J-16 scope (open-universe).
- No frontend unit-test runner exists in this repo (no vitest/jest); the leaderboard's render is covered by `tsc`/`vite build` typecheck + lint + the load-bearing browser-QA step (not a component unit test).
- Carry-forward non-blockers (unchanged, out of scope): pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip`; flaky `test_post_returns_before_loop_completes_and_get_stays_responsive`; the out-of-scope `/health` probe still in the tree (release-manager reconciles handoff/changed_files at commit); `auto_session.py` size (~1.4k lines — future refactor).

## Suggested Next Phase
This is the **FINAL** must-have journey. With J-16 landed (data layer hermetically proven + live-validated, persisted, FE built and type-clean) and pending the load-bearing browser-QA pixel confirmation, all 16 must-have journeys pass → the evaluator should consider **GOAL_ACHIEVED**. Any follow-up is polish, not a must-have: e.g. column sorting/expandable rows on the leaderboard, or the separable `browser-qa-phase.sh` port-probe framework fix.
