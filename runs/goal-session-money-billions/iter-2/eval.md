# Iteration 2 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

Lean iter-2 closed J-05 — the last failing Must-have journey. `BacktestConfigBar.tsx` now
fetches `GET /api/symbols` and `GET /api/timeframes` and renders an endpoint-backed symbol
combobox (`<datalist>`) and timeframe `<select>`, replacing the hardcoded button row and the
unguided free-text field. All five required-still-passing journeys (J-01, J-02, J-03, J-04,
J-06) remain green with no regression from the control rewiring. GOAL_ACHIEVED is still
blocked — by design — by the deferred `GET /api/sessions/{id}` eager-load anti-goal and the
unasserted J-04 OOS-aware soft gap, both explicitly scheduled for the next full-depth iteration.

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run a backtest from NL | passing | passing (no regression) | reports/qa/goal-money-billions-iter-2-evidence/UT-J-01-result.png |
| J-02 Inspect/browse run history | passing | passing (no regression) | reports/qa/goal-money-billions-iter-2-evidence/UT-J-02-result.png |
| J-03 Walk-forward validation | passing | passing (no regression) | reports/qa/goal-money-billions-iter-2-evidence/UT-J-03-result.png |
| J-04 AI insights | passing | passing (no regression; evidence note below) | reports/qa/goal-money-billions-iter-2-evidence/UT-J-04-result.png |
| **J-05 Reference data loads** | **failing** | **passing (TARGET — newly passing)** | reports/qa/goal-money-billions-iter-2-evidence/UT-J-05-result.png |
| J-06 Warm-cache re-run | passing | passing (no regression) | reports/qa/goal-money-billions-iter-2-evidence/UT-J-06-result.png |

**Journey deltas:** Newly passing: J-05. Newly failing: none. Regressed: none.

**Evidence verification performed (skeptical, not handoff-trusting):**
- Independently read `git diff HEAD -- apps/` → exactly one file changed
  (`BacktestConfigBar.tsx`, +97/−21); no backend file modified.
- Read the diff: `symbolOptions` initializes to `[]` (no hardcoded 26-element list) →
  the populated 26-item `<datalist>` can only have come from the endpoint;
  `update('timeframe', e.target.value)` writes the raw server value with no transform;
  `timeframeChoices` guard keeps the active selection selectable.
- Browser-QA DOM+network inspection: 26 datalist options byte-identical to live
  `/api/symbols`; 6 `<select>` options == live `/api/timeframes`; `performance` resource
  timing proves both fetched with `initiatorType:"fetch"` (not the coincidentally-identical
  `FALLBACK_TIMEFRAMES`).
- Inspected 9 evidence screenshots. J-01/J-06 show byte-identical deterministic output
  (−7.81%/39 trades) → endpoint-backed controls feed the unchanged request format and
  determinism/warm-cache survive. J-04 dedicated screenshot is a duplicate of J-03's, but
  the ranked insight pills are independently visible in UT-J-05/UT-J-01 screenshots.

## Anti-goal Check

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| No hard-coded credentials/keys | OK | `API_BASE_URL` from `import.meta.env.VITE_API_URL`; no secrets in diff |
| Sandbox blocks I/O/network/exec | OK | No backend/sandbox file touched (git diff confirms) |
| No lookahead | OK | No engine change; J-06 byte-identical to J-01 |
| No nondeterministic backtests | OK | J-01 vs J-06 identical (−7.81%/39 trades) on warm cache |
| No paid SaaS beyond Anthropic/OpenAI | OK | No new dependency or service |
| `shared/contracts.py` not mutated | OK | Not touched |
| Single-Parquet OHLCV cache | OK (resolved iter-1, unchanged) | Frontend-only iter; loader.py untouched; J-06 re-corroborates |
| `BACKTEST_STORE_DIR` durable, not /tmp | OK (resolved iter-1, unchanged) | session_store.py untouched; J-02 re-corroborates persistence |
| No relational DB / SQLite | OK | None introduced |
| `GET /api/sessions/{id}` no eager-load | **UNRESOLVED (minor, pre-existing, deferred)** | session_routes.py:142-171 still inlines per-iteration payloads; NOT introduced here (frontend-only); explicitly OUT OF SCOPE iter-2, deferred to next full iter. **Blocks GOAL_ACHIEVED.** Not a REGRESSION (pre-existing, minor severity). |
| No new reference-data caching layer | OK | Self-contained fetch only; no shared cache/endpoint added (per-instance refetch is a non-blocking efficiency note, explicitly out of scope) |

## Next-Step Recommendation

Next iteration: **full depth**. Resolve the last open anti-goal —
`GET /api/sessions/{id}` eager-load (`apps/backend/backend/session_routes.py:142-171`):
stop `get_session` calling `read_iteration_full` per iteration; return a lightweight
session/iteration list and lazy-load heavy `result`/`rating` detail via the existing
per-iteration endpoint. This is a frontend+backend session-open contract change with
**direct J-02 regression risk** (run-history open/reload), so it warrants the full pipeline
(audit + ux-regression + closure). Fold into that iteration's QA the still-open **J-04
soft gap**: an explicit assertion that AI insights are *OOS-aware when walk-forward data
exists* (request insights after running walk-forward; assert the suggestions reference OOS
behavior). Required-still-passing for that iter: J-01–J-06 (J-02 highest watch).
GOAL_ACHIEVED becomes reachable once both are closed with no journey regression.

## Halt Justification (if halting)

Not halting. CONTINUE: real progress (J-05 newly passing — the last failing Must-have
journey closed), no regression (all five required journeys still green, no critical/new
anti-goal), and clear tractable next work (one unresolved minor anti-goal + one soft gap,
both with a concrete plan). Not GOAL_ACHIEVED because the `GET /api/sessions/{id}`
eager-load anti-goal is unresolved (agent rule: never GOAL_ACHIEVED with an unresolved
anti-goal) and the J-04 OOS-aware sub-clause is still unasserted — both deferred to the
next full iteration exactly as the iter-2 spec and the iter-1 evaluator predicted. Not
ESCALATE: this lean iter executed exactly as planned with no uncovered ambiguity; the
full-depth recommendation is the pre-planned next step, not an escalation trigger.
