# Iteration 0 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

Baseline established truthfully: verify-only iteration with **zero source changes**
(independently confirmed — no `git diff` under `apps/`, `scripts/`, or
`incredible_auto_dev/`; only the pre-existing untracked `.gitignore` + generated
artifacts). 5 of 6 Must-have journeys (J-01, J-02, J-03, J-04, J-06) already pass
end-to-end against the unmodified codebase and are seeded `already_passing`;
**J-05 fails** (a real frontend code gap — reference-data endpoints work but the
UI never calls them). Three **pre-existing** anti-goal postures are corroborated
at cited file:line and recorded for remediation; none were introduced by this
iteration, so this is CONTINUE, not REGRESSION (empty baseline → nothing can
regress; a verify-only iteration violated nothing).

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run a backtest from natural language | (none — fresh) | already_passing | `reports/qa/goal-money-money-iter-0-evidence/UT-J-01-result.png` |
| J-02 Inspect and browse run history | (none — fresh) | already_passing | `reports/qa/goal-money-money-iter-0-evidence/UT-J-02-trades.png`, `UT-J-02-detail.png` |
| J-03 Walk-forward validation | (none — fresh) | already_passing | `reports/qa/goal-money-money-iter-0-evidence/UT-J-03-walkforward.png` |
| J-04 AI insights | (none — fresh) | already_passing | `reports/qa/goal-money-money-iter-0-evidence/UT-J-04-insights.png` |
| J-05 Reference data loads | (none — fresh) | failing | `reports/qa/goal-money-money-iter-0-evidence/UT-J-05-controls.png` |
| J-06 Warm-cache re-run works end-to-end | (none — fresh) | already_passing | `reports/qa/goal-money-money-iter-0-evidence/UT-J-06-rerun.png` |

Evidence notes (skeptical cross-check performed):
- J-01: screenshot shows "BTC 1h RSI Mean Reversion" run — −34.98% return, 116 trades, 57% win, −1.18 Sharpe, ALPHA −202.06%, Equity Curve, Strategy Script, run in history. Acceptance met.
- J-02: `UT-J-02-trades.png` shows the reloaded prior run "BNB 4h EMA9 Pullback Confirmed" — +291.76%, Equity Curve, **Trade History (144 trades)** populated; 144 ≠ active run's 116, confirming a correct distinct reload (not stale).
- J-03 / J-04: `UT-J-03-walkforward.png` and `UT-J-04-insights.png` are **byte-identical (md5 8eb37896…)** — one capture, not two. That single frame nonetheless shows *both* the Walk-Forward panel (WFE **0.31** yellow-tier badge, 2-window table, "Combined OOS Equity Curve (2 windows chained)") and the AI-insights panel (substantive analysis paragraph + 10 ranked suggestion chips). Both journeys' acceptances are visually corroborated despite the shared file. J-04's "OOS-aware" sub-clause is not explicitly verifiable from the generic chip labels (recorded as a refinement to verify later, not a baseline failure — the stated acceptance "at least one ranked suggestion renders" is clearly met).
- J-05: `UT-J-05-controls.png` confirms the failure — Symbol is a free-text `<input>` (default "BNB/USDT"), Timeframe is a static hardcoded button group (1m…1D); browser perf entries show `/api/symbols` & `/api/timeframes` are never requested though both return 200 with valid data (26 symbols / 6 timeframes). Real frontend wiring gap, not environmental.
- J-06: re-run produced byte-identical metrics to J-01 (116 trades, −34.98%) → consistent with deterministic backtests + warm single-file-cache reuse at the UI layer; "Iterations (2)" in history. (Cold-vs-warm timing — goal.md's ≥10× criterion — is a backend concern not measured at the UI; J-06's own acceptance only requires a clean second render + history entry, which is met.)

## Anti-goal Check

All postures are **pre-existing** (corroborated at cited file:line; backend suite
107 passed / 1 pre-existing unrelated fail) and were **not introduced** by this
verify-only iteration (zero diff). Recorded `resolved:false` for the decomposer.

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| No hard-coded credentials/keys in source | OK | None found; both API keys via git-ignored `.env`. |
| Sandbox blocks file I/O / network / exec / __import__ / open / os | OK | Not exercised this iter; no change. |
| No lookahead | OK | Not changed; deterministic re-run (J-06) consistent with no lookahead. |
| No nondeterministic backtests | OK | J-01 vs J-06 byte-identical metrics. |
| No paid SaaS beyond Anthropic/OpenAI | OK | None added. |
| `shared/contracts.py` frozen dataclasses not mutated | OK | Zero source changes. |
| **OHLCV cached as single Parquet per (symbol,tf), NOT per-day file** | **VIOLATED (pre-existing)** | `apps/backend/data/loader.py:63` writes `{symbol}/{tf}/{YYYY-MM-DD}.csv` per calendar day; `:51` defaults `MARKET_DATA_CACHE_DIR` to `/tmp`; `:302` `rglob("*.csv")`. Direct anti-goal violation. Not introduced here. |
| `BACKTEST_STORE_DIR` MUST NOT default to volatile `/tmp`; history survives restart | **VIOLATED-in-code (pre-existing, runtime-mitigated)** | `apps/backend/backend/session_store.py:26` default `/tmp/backtests`; same pattern `apps/backend/backend/directions_cache.py:23` (`/tmp/initial_directions`). Durability holds **only** via `.env` override (boot log: `.data/backtests`). The code default itself is the violation. |
| `GET /api/sessions/{id}` (open path) MUST NOT eager-parse full per-iter payloads | **VIOLATED (pre-existing)** | `apps/backend/backend/session_routes.py:150-156` loops `read_iteration_full()` for every iteration. Runtime proof: open path = **53,920,916 B (~51 MB)**, 26 full entries, vs lightweight `/iterations` = 1,273,461 B (~42×). |
| No relational DB / SQLite for OHLCV/session/directions | OK | File store + CSV only (no SQLite); the *CSV-vs-Parquet* breach is captured above. |

None of the violations match the REGRESSION "critical" set (committed secrets /
unapproved paid SaaS / license / security backdoor) and none were introduced by
this iteration → classified `minor` for halt purposes (→ CONTINUE with explicit
remediation directive), **not** product-trivial: these are the central
storage/perf work items.

## Next-Step Recommendation

Run the next iteration at **full** depth with **J-01, J-02, J-03, J-04, J-06 as
required-still-passing** (they pass today; the remediations below are
data-layout / open-path changes that can silently regress them — full pipeline's
audit + ux-regression + closure gates are warranted).

Target, in priority order:
1. **Anti-goal: single-file Parquet OHLCV cache** — replace the per-day CSV
   fan-out in `apps/backend/data/loader.py` with one Parquet file per
   `(symbol, timeframe)`; serve covering ranges from cache with no Binance
   re-fetch (also satisfies goal.md's ≥10× warm-load criterion). Highest
   regression risk to J-01 / J-06 → must keep them green.
2. **Anti-goal: durable store default** — change the *code* default of
   `BACKTEST_STORE_DIR` (`session_store.py:26`) and `DIRECTIONS_CACHE_DIR`
   (`directions_cache.py:23`) off volatile `/tmp` to a durable repo-relative
   path; do not rely on `.env` to mask it. Low risk.
3. **Anti-goal: lazy session open path** — make `GET /api/sessions/{id}`
   (`session_routes.py:150-156`) return lightweight metas and defer
   `read_iteration_full()` to the existing per-iteration endpoint. Protect J-02.
4. **J-05** — wire the Symbol and Timeframe controls in the frontend to
   `/api/symbols` and `/api/timeframes` (currently free-text + static buttons).
   Lowest risk; can ride in the same iteration or go first.

(`apps/backend/tests/test_directions_cache.py::test_write_and_read_full_round_trip`
is a pre-existing red off the J-01..J-06 path — fold the fix into item 1/3 if the
directions cache is touched; otherwise leave for a later iteration.)

## Halt Justification (if halting)

Not halting. CONTINUE: the baseline is established with concrete per-journey
evidence; one tractable journey gap (J-05) and three corroborated, actionable
pre-existing anti-goal postures remain. No REGRESSION — the journey-history was
empty (nothing to regress from) and a verify-only iteration with zero code
changes introduced no anti-goal violation; halting a baseline would block the
very remediation iterations it exists to enable.
