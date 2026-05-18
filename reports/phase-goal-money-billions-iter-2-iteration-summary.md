# Iteration Summary — goal-money-billions-iter-2

**Verdict:** CONTINUE
**Iteration type:** goal-lean
**Date:** 2026-05-18
**Iteration:** 2

## Headline

Wired the Symbol and Timeframe parameter controls to the live backend reference endpoints (J-05).

## Direction

**Signal:** improving
**Why:** This iter closed J-05 — the last failing Must-have journey — by wiring `BacktestConfigBar.tsx` to `GET /api/symbols` and `GET /api/timeframes` (single-file, +97/−21, no backend touched). All five required journeys (J-01–J-04, J-06) re-verified passing with no regression from the control rewiring. GOAL_ACHIEVED stays blocked by design: the deferred `GET /api/sessions/{id}` eager-load anti-goal and the unasserted J-04 OOS-aware soft gap are scheduled for the next full-depth iteration.

**Trend (last 3 iters):**
- Newly passing this iter: J-05
- Newly passing in last 3 iters total: J-05 (iter-2); J-01–J-04, J-06 were baseline-passing from iter-0 (re-verified, not failing→passing transitions)
- Regressions in last 3 iters: none
- Anti-goal violations in last 3 iters: 0 new introduced; 2 resolved in iter-1 (single-Parquet OHLCV cache; durable `BACKTEST_STORE_DIR`); 1 carried unresolved (`GET /api/sessions/{id}` eager-load — minor, pre-existing, deferred)
- Iters with no journey state change: 1 of last 3 (iter-1)

**Latest evaluator reasoning:** Lean iter-2 closed J-05 — the last failing Must-have journey. `BacktestConfigBar.tsx` now fetches `GET /api/symbols` and `GET /api/timeframes` and renders an endpoint-backed symbol combobox (`<datalist>`) and timeframe `<select>`, replacing the hardcoded button row and the unguided free-text field. All five required-still-passing journeys (J-01, J-02, J-03, J-04, J-06) remain green with no regression from the control rewiring. GOAL_ACHIEVED is still blocked — by design — by the deferred `GET /api/sessions/{id}` eager-load anti-goal and the unasserted J-04 OOS-aware soft gap, both explicitly scheduled for the next full-depth iteration.

## What was done

- Converted the Symbol control to an endpoint-backed native combobox (`<input list>` + `<datalist>`) populated from `GET /api/symbols` (26 `BASE/USDT` pairs); free-text entry, regex validation, uppercase, and inline error preserved.
- Replaced the hardcoded `['1m','5m','15m','1h','4h','1d']` timeframe button row with a `<select>` populated from `GET /api/timeframes` (6 server `{value,label}` options; server labels shown, server `value` drives selection).
- Added a single self-contained mount-time `useEffect` in `BacktestConfigBar.tsx` using the existing `API_BASE_URL` convention — no prop-drilling, no backend file touched (single-file diff, +97/−21).
- Added loading/error fallbacks: `FALLBACK_TIMEFRAMES` + `isStringArray`/`isTimeframeOption` type guards + `.catch` keep the bar usable if either endpoint is unreachable; a `timeframeChoices` guard preserves the effective default and no value transform was introduced (request body to `/api/run-backtest` unchanged).
- `cd apps/frontend && npm run build` (tsc strict + Vite) passes with no new errors; changed file lint-clean under the project's installed react-ts plugins.
- Verified 6/6 journeys pass browser QA — J-05 newly passing (DOM + network inspection: 26 datalist opts == live `/api/symbols`, 6 `<select>` opts == live `/api/timeframes`, both fetched via `fetch()`); J-01–J-04, J-06 no regression.

## What's left

- Anti-goal still open: `GET /api/sessions/{id}` eager-load (`apps/backend/backend/session_routes.py:142-171` inlines per-iteration `result`/`rating` payloads) — minor, pre-existing, NOT introduced here; explicitly deferred to the next full-depth iteration. Blocks GOAL_ACHIEVED.
- J-04 soft gap (open since iter-0): "AI insights are OOS-aware when walk-forward data exists" is still not separately asserted — deferred to the next full iteration's QA. Blocks GOAL_ACHIEVED.
- Known limitation: repo-level `npm run lint` fails at the tooling level — no committed ESLint config anywhere in `apps/frontend` or its ancestors (confirmed pre-existing on the untouched baseline, not a regression). Recommend a future dedicated chore to add a committed `eslint.config.js`.
- Known limitation (non-blocking efficiency note): each of the 18 mounted `BacktestConfigBar` instances independently fetches `/api/symbols` + `/api/timeframes` on mount (×2 from React 18 StrictMode); requests settle within ~330 ms with no remount/poll loop. A shared cache/hook is explicitly out of scope per the iter spec.
- Evidence-process gap: browser-QA saved `UT-J-04-result.png` as a byte-identical duplicate of `UT-J-03-result.png` (walk-forward panel, not the insights pane). J-04 was corroborated via insight pills visible in UT-J-05/UT-J-01; the next full iter asserting J-04 OOS-awareness needs a dedicated, distinct insights-pane screenshot.

## Next step

Next iteration: **full depth**. Resolve the last open anti-goal — `GET /api/sessions/{id}` eager-load (`apps/backend/backend/session_routes.py:142-171`): stop `get_session` calling `read_iteration_full` per iteration; return a lightweight session/iteration list and lazy-load heavy `result`/`rating` detail via the existing per-iteration endpoint. This is a frontend+backend session-open contract change with **direct J-02 regression risk** (run-history open/reload), so it warrants the full pipeline (audit + ux-regression + closure). Fold into that iteration's QA the still-open **J-04 soft gap**: an explicit assertion that AI insights are *OOS-aware when walk-forward data exists* (request insights after running walk-forward; assert the suggestions reference OOS behavior). Required-still-passing for that iter: J-01–J-06 (J-02 highest watch). GOAL_ACHIEVED becomes reachable once both are closed with no journey regression.

## Artifacts

| Report | Verdict | Path |
|--------|---------|------|
| Iter spec | — | docs/phases/goal-money-billions-iter-2.md |
| Dev handoff | — | docs/handoffs/goal-money-billions-iter-2-dev.md |
| Frontend handoff | — | docs/handoffs/goal-money-billions-iter-2-frontend.md |
| Review | PASS_WITH_NOTES | reports/reviews/goal-money-billions-iter-2-review.md |
| Browser QA | PASS | reports/phase-goal-money-billions-iter-2-ui-test-results.md |
| Goal evaluation | CONTINUE | runs/goal-session-money-billions/iter-2/eval.md |
| Journey history | — | runs/goal-session-money-billions/state/journey-history.json |
