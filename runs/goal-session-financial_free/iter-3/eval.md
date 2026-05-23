# Iteration 3 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

Layer-2 opens cleanly: J-12 (open-universe multi-config search from objective + budget) and J-13
(hard token/USD/`max_configs` budget) are both newly **passing** on real live-LLM backend runs plus a
hermetic test suite I re-ran myself (194 passed / 1 pre-existing red / 1 deselected). The five Layer-1
journeys (J-07–J-11) remain green and J-01–J-06 show no regression; coherence is PASS and no anti-goal
was violated (frozen `contracts.py` untouched, zero secrets, no new infra). Not GOAL_ACHIEVED — J-14,
J-15, J-16 are still failing (Layer-2 incomplete). The recurring **live-pixel debt** for the auto-session
status-strip chips (J-08/J-10) is again only partially cleared (a real-pixel app render *was* captured
this time, clearing J-05's pixel debt, but the interactive strip chips and the reload-mid-run step were
blocked by the documented Chrome-MCP hidden-tab throttle plus a concurrent QA contending for the
foreground tab; the dedicated browser-qa-agent SKIPPED because services were down in its window).

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run a backtest from NL | already_passing | already_passing (no-regression) | QA TC-14: manual `POST /api/run-backtest` (NL+symbol/tf/dates) → 200, `run_id=cf1308bd`, equity 2183 pts, metrics + `strategy_spec`; run history 28→29. Workstation render (`TC-12-app-loaded.png`) shows the Strategy Builder. |
| J-02 Browse run history | already_passing | already_passing (no-regression) | Lazy list/open path untouched; full suite green (my re-run). iter-1 eager-load verdict still resolved. |
| J-03 Walk-forward validation | already_passing | already_passing (no-regression) | `walk_forward.py` untouched; WFE-gated scorer exercised by open-universe best-selection tests; suite green. |
| J-04 AI insights | already_passing | already_passing (no-regression) | Insights path unchanged (open-universe carries `insights:null`, a shape the UI already handles); suite green. |
| J-05 Reference data loads | already_passing | already_passing (**pixel cleared**) | QA TC-14: `/api/symbols`=200 (26), `/api/timeframes`=200 (6); **real-pixel** `TC-12-app-loaded.png` shows Symbol/Timeframe/date/capital/exchange controls visibly populated. |
| J-06 Warm-cache re-run | already_passing | already_passing (no-regression) | Parquet loader untouched; open-universe reuses the OHLCV cache across configs (no re-fetch); suite green. |
| J-07 Headless pinned start | passing | passing | QA TC-02: pinned `POST` → 200 + appears in `/api/sessions`; pinned path byte-for-byte unchanged (regression test green; my re-run). |
| J-08 Live UI tracking | passing | passing (pixel still owed) | QA TC-13: live poll of `GET /api/sessions/{id}` showed 2 distinct config cards + budget accruing (`configsDone 0→1→2`, tokens accruing) without reload. Interactive strip pixels blocked by throttle — carry-forward. |
| J-09 Terminal stop-reason + WFE best | passing | passing | QA TC-15: pinned run → `budget-exhausted`, iterations 2/2, `bestIterationId=72115c78`, real spend 71786 tok/$0.020338. |
| J-10 Backend single source / survives reload | passing | passing (pixel still owed) | QA TC-13: full `autoRun` (status + all budget keys) persisted server-side → reload restores from the endpoint, not browser memory. Reload-mid-run pixel step not captured (throttle) — carry-forward. |
| J-11 Server-side stop | passing | passing | QA TC-15: `POST /stop` on active run → `stopped` (`stopReason=stopped`); B1+B2 race test green (my re-run). |
| J-12 Open-universe run | **failing** | **passing** | QA TC-04: 2 **distinct** configs (`BTC/USDT 1h`, `ETH/USDT 1h`) from the bounded seed universe; best marked when a config passes the WFE gate (`722cdad7`), `None` when none do (correct gating); terminal within budget. Code: `_run_open_universe` (auto_session.py:809), `SEED_UNIVERSE_MAX=4` (:87). Unit tests: distinct-configs/best/terminal-at-max-configs. Coherence PASS. |
| J-13 Hard token/USD budget | **failing** | **passing** | QA TC-05/TC-08: real token/USD recorded (4720 tok/$0.001025; 71786 tok/$0.020338), `budget-exhausted`, spend ≤ caps, visible in `autoRun.budget`, no iteration after cap. Code: `exceeded()` enforces `max_tokens`/`max_usd` at auto_session.py:172-175; `cost_usd` single source (model_catalog.py:115). Unit tests: token-cap + USD-cap independently True, immutability, exact rate. |
| J-14 Staged screening | failing | failing (out of scope) | Deferred per spec; `_create_iteration` left as one reusable method so J-14 can wrap it in SCREEN/PROMOTE without a rewrite. |
| J-15 Global-history warm start | failing | failing (out of scope) | Deferred per spec. |
| J-16 Overfit leaderboard | failing | failing (out of scope) | Single best badge exists (WFE-gated); ranked board is J-16. |

## Anti-goal Check

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| No hard-coded credentials | OK | QA: 0 key-pattern matches across 2964 store files; no secrets in diff. |
| Sandbox blocks I/O/exec/import/os | OK | `test_sandbox` green (in my 194-passed re-run). |
| No lookahead | OK | `test_lookahead` green. |
| No nondeterministic backtests | OK | `test_determinism` green. |
| No paid SaaS beyond Anthropic/OpenAI | OK | No new dependency added. |
| `contracts.py` not mutated | OK | `git diff HEAD -- shared/contracts.py` empty; token usage threaded via a side channel. |
| OHLCV single Parquet, no re-fetch | OK | Shared loader reused across configs; code-hash dedup cache added (returns cached result, recomputes nothing — coherence note). |
| `BACKTEST_STORE_DIR` not `/tmp` | OK | Store path unchanged. |
| No relational DB / SQLite | OK | Grep of backend diff: no celery/redis/sqlite/sqlalchemy/subprocess/`os.system`/`/tmp`. |
| List/open path not eager-parse | OK | Open-universe persists via `write_iteration`/lazy-detail; resolved iter-1, not re-litigated. |
| Same file store, no parallel store | OK | Coherence verified: `session_store.write_iteration` / same `autoRun` block; no schema fork. |
| Hard budget, never "one more" | OK | `exceeded()` checked before each config (auto_session.py:158); QA: `configsDone` never exceeded `maxConfigs`. |
| `autoRun` persisted, survives reload | OK | QA TC-13: full `autoRun` persisted server-side, reload restores. |
| Iterate loop only in backend | OK | In-browser loop removed iter-2, not reintroduced (diff scoped to status-strip display + type). |
| Reuse `BacktestPipeline`, no sandbox bypass | OK | Coherence: `_create_iteration` → existing pipeline + scorer. |
| Bounded seed universe, no exchange-wide fan-out | OK | `SEED_UNIVERSE_MAX=4` (BTC/ETH × 1h/4h) in code; QA: only seed symbols, never `/api/symbols`. |
| Best = robust WFE-gated objective | OK | QA TC-04: best=None when no config passes WFE gate; WFE-failing candidate not marked best. |
| SCREEN skips WF / strongest model | N/A | J-14 deferred; iter-3 evaluates each config uniformly — not a "cheap SCREEN" stage, so the anti-goal isn't triggered (spec-acknowledged). |
| Background job doesn't block event loop | OK | B1+B2 preserved (off-loop store I/O, semaphore-guarded backtests); race test green. |
| No new external infra | OK | No queue/broker/DB/vector-store added. |
| No secrets in activity log / artifacts | OK | QA: 0 matches. |

## Next-Step Recommendation

Continue Layer-2 at **full** depth with **J-14 (staged SCREEN→PROMOTE cost tiering + model routing)** —
wrap the now-reusable `_create_iteration` per-config evaluation in a cheap `SCREEN` stage (no
walk-forward, cheapest model) that promotes only the top-k survivors to full evaluation (walk-forward +
stronger model), honoring the "SCREEN-skips-WF / strongest-model" anti-goal. The activity log must show
the `SCREEN` candidates and the `PROMOTE` subset (k < screened). J-14 is the prerequisite for J-15
(global-history warm start, read-only, opt-out) and J-16 (multi-candidate overfit-gating leaderboard
UI), which follow.

**Clear the recurring live-pixel debt this time, decisively (J-08/J-10).** This is the *second* iteration
where the dedicated browser-qa-agent SKIPPED because the frontend/backend were torn down in its window,
and the third where the auto-session status-strip chips were never confirmed at the pixel layer (iter-0
throttle, iter-2 FE down, iter-3 throttle + concurrent-QA + browser-qa SKIP). J-14 adds genuinely new UI
(SCREEN/PROMOTE in the activity log), so browser-qa runs again — the next iteration MUST run the
browser-qa-agent against the **same** live services the full-QA used, in the **same** window, on an
**uncontended** foreground tab, and capture: the strip token/USD/configs chips live-updating, config
cards streaming without reload, and the reload-mid-run survival step. Do not re-defer.

Carry-forward (non-blocking): pre-existing red `test_directions_cache::test_write_and_read_full_round_trip`
(untouched Capability #10 nice-to-have); review NOTEs (`_backtest_cache_key` omits
`initial_capital`/`commission` — harmless today, seed configs never vary them; `AutoSessionConfig.symbol/timeframe`
typed `str` but `None` in open-universe — mypy not gated); the flaky route timing test
`test_post_returns_before_loop_completes_and_get_stays_responsive` (de-flake the test scaffold; not a
product regression). Do NOT re-litigate the eager-load anti-goal (resolved iter-1) or the in-browser
scorer/loop removal (done iter-2).
