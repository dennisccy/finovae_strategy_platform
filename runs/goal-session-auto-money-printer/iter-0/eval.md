# Iteration 0 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

Clean baseline. The prior `money-billions` session already delivered the core
platform: J-01, J-03, J-04, J-05, J-06 verified passing with live evidence
(real LLM compilation, real Binance fetch, deterministic warm-cache re-run).
J-02 is **partial** (selecting a prior run reloads its spec + metrics but the
right-hand analysis panel does not re-bind its trades table/equity curve).
The entire headless auto-optimizing session layer (Key Capability #11,
J-07–J-16) is **unimplemented** — `POST /api/auto-sessions` → 404, zero
auto-session OpenAPI paths, no backend module; the only automation is the
legacy in-browser iterate loop (`useBacktest.ts:2065`). This is the exact
separation a baseline exists to produce. Zero code changed; no anti-goal
introduced.

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run a backtest from NL | (none — baseline) | already_passing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-01-result.png |
| J-02 Inspect and browse run history | (none — baseline) | partial | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-02-result.png |
| J-03 Walk-forward validation | (none — baseline) | already_passing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-03-result.png |
| J-04 AI insights | (none — baseline) | already_passing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-04-result.png |
| J-05 Reference data loads | (none — baseline) | already_passing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-05-result.png |
| J-06 Warm-cache re-run end-to-end | (none — baseline) | already_passing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-06-result.png |
| J-07 Start headless auto-session via API | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-08 Track auto-run live in UI | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-09 Terminal stop on target/budget; best marked | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-10 Backend single source of truth (rewire, survives reload) | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-11 Stop a running auto-session | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-12 Open-universe from objective+budget | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-13 Hard token/cost budget | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-14 Staged SCREEN→PROMOTE | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-15 Global-history warm start + opt-out | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |
| J-16 Robust objective gates overfit | (none — baseline) | failing | reports/qa/goal-auto-money-printer-iter-0-evidence/UT-J-07-to-16-no-auto-sessions-api.png |

Backend unit baseline (recorded, not fixed): **124 passed / 1 failed**. The
single failure — `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
— is the nice-to-have directions cache (Key Capability #10), not a Must-have
journey; pre-existing, out of scope.

## Anti-goal Check

No code changed this iteration (`git diff HEAD` empty, `changed_files: []`,
review verdict PASS), so **no anti-goal could be introduced**. Observed
current-state signals (recorded, not violations):

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| No hard-coded credentials/keys | OK | Keys only in git-ignored `apps/backend/.env`; git tree clean |
| Sandbox blocks I/O/net/exec/import/open/os | OK | `tests/test_sandbox.py` PASS in baseline suite |
| No lookahead | OK | `tests/test_lookahead.py` PASS |
| Deterministic backtests | OK | J-06 byte-identical warm re-run; `tests/test_determinism.py` PASS |
| No paid SaaS beyond Anthropic/OpenAI | OK | none observed |
| `shared/contracts.py` not mutated | OK | zero code changes |
| OHLCV single-Parquet-per-(symbol,timeframe), no re-fetch on covering cache | OK | `loader.py` single-Parquet warm path; J-06 ~22s warm vs ~60s+ cold, deterministic. **Note (not a violation):** `.env` `MARKET_DATA_CACHE_DIR=/tmp/market_data` puts the Parquet under volatile `/tmp` (code default is durable `.data/market_data`); the literal anti-goal scopes the `/tmp` prohibition to `BACKTEST_STORE_DIR`, so this is a durability/perf hardening item, not a strict breach. |
| `BACKTEST_STORE_DIR` not volatile `/tmp`; survives restart | OK | Runtime + code default both `…/.data/backtests`; boot log confirms |
| No relational DB / SQLite | OK | repo scan for `*.db`/`*.sqlite*` returned nothing |
| `GET /api/sessions/{id}` not eager-parsing per-iteration payloads | OK (n/a) | core path unchanged this iter |
| J-07–J-16 auto-chain anti-goals (same store, hard budget, persisted autoRun, backend-only loop, sandbox reuse, bounded seed, robust best, SCREEN cheap, dedupe+cache reuse, read-only history, prompt caching, non-blocking, no new infra, no secrets in log) | Not applicable yet | The auto-session layer does not exist. The in-browser iterate loop at `useBacktest.ts:2065` is the **pre-rewire** state J-10 must replace — flagged as J-10 failing, not as a violation introduced this iter. |

No `anti_goal_violations` entries recorded — nothing was introduced or
breached per the literal anti-goal text.

## Next-Step Recommendation

Next iteration is the first **build** iteration. Recommended depth: **full**
(audit + ux-regression + closure gate) — the scope is large, net-new, and
dense with security/correctness anti-goals.

Priority order:
1. **Foundation first (J-07 → J-11):** create the headless auto-session
   backend — `POST /api/auto-sessions` (pinned-config), session/iteration
   artifacts written to the *existing* file store (no parallel store), a
   server-side iterate loop reusing the existing `BacktestPipeline` +
   RestrictedPython sandbox, a persisted `autoRun` status that survives a
   reload, terminal stop with a visible stop reason + best-marking, and
   `POST /api/auto-sessions/{id}/stop`. Rewire the UI "Auto Run" button to the
   backend and delete the in-browser loop (`useBacktest.ts:2065`) so J-10's
   anti-goal ("iterate loop only in backend") holds.
2. **Optimizer second (J-12 → J-16):** open-universe config search from a
   bounded seed, an immutable hard token/USD/wall-clock cost tracker,
   staged SCREEN→PROMOTE, global-history warm-start with `history_scope`
   opt-out, and robust (WFE-gated, drawdown-penalized, min-trades) best
   selection. Layer this only after Foundation lands.
3. **Cheap win alongside (J-02):** make selecting a prior run re-bind the
   right-hand analysis panel (trades table + equity curve), not just the
   left conversation panel — small, isolated, already-built-product fix.

Use tiny budgets (`max_iterations: 2`, short date range, cheapest model,
lenient targets) for all J-07–J-16 verification per the goal's cost guard.

## Halt Justification (if halting)

Not halting. CONTINUE: the baseline succeeded exactly as designed —
6 core journeys are already passing/partial, 10 are genuine, well-scoped,
tractable gaps with an unambiguous next target. No regression is possible
(iter 0, no prior state) and no critical anti-goal was violated (zero code
changes).
