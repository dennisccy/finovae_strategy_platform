# Iteration 0 Evaluation

**Verdict:** CONTINUE
**Depth Recommendation For Next Iteration:** full

## Summary

Clean verify-only baseline (zero code changes — `git diff HEAD` and `--cached` both empty). The six manual journeys J-01…J-06 are **already implemented and functionally verified** against the live backend (marked `already_passing`); the ten automated-session journeys J-07…J-16 **fail-by-absence** — `POST /api/auto-sessions` returns 404 and no auto/optimizer routes exist, confirming net-new scope. This is the expected, useful baseline (separates "done" from "to build"); it is **not** a regression and **not** goal-achieved.

## Journey Results This Iteration

| Journey | Prior Status | This Iteration | Evidence |
|---------|--------------|----------------|----------|
| J-01 Run backtest from NL | (none) | **already_passing** | `…/api-probe-and-journey-evidence.md` §J-01 — `generate-strategy` 200 + `execute-backtest` SSE (103 evt) → 143 trades, +5.97%, 8784-pt equity, run_id `db758f99` in `/api/runs` |
| J-02 Browse run history | (none) | **already_passing** | §J-02 — `/api/sessions` 122 lightweight tabs; lazy `/sessions/{id}/iterations/{id}` 200 → full detail (metrics, 21 trades, script, 5-cat rating, WF, insights) |
| J-03 Walk-forward | (none) | **already_passing** | §J-03 — `execute-walk-forward` 200, wfe=0.4218 (yellow), 8-window IS/OOS table, combined OOS equity 720 pts |
| J-04 AI insights | (none) | **already_passing** | §J-04 — `generate-insights` 200, 10 ranked suggestions, OOS-aware=TRUE; content-distinct from J-03 |
| J-05 Reference data | (none) | **already_passing** | `UT-J-05-rendered-ui-domtext.txt` — 26 symbols / 6 timeframes, DOM-confirmed controls populated from endpoints |
| J-06 Warm-cache re-run | (none) | **already_passing** | §J-06 — warm re-run 10.2s vs 43.5s cold, 143 trades, run_id `7ba262dd`, no Binance re-fetch |
| J-07 Start headless session (pinned) | (none) | **failing** | §GATE — `POST /api/auto-sessions` → 404; route absent from OpenAPI |
| J-08 Track auto run live in UI | (none) | **failing** | §GATE — no start endpoint, nothing to track |
| J-09 Stop on target/budget; best marked | (none) | **failing** | §GATE — no controller / stop-reason / best-marking surface |
| J-10 Backend single source of truth | (none) | **failing** | §GATE — Auto Run is in-browser today (`useBacktest.ts`, `IterationCard.tsx`); no backend loop |
| J-11 Stop a running auto session | (none) | **failing** | §GATE — `POST /api/auto-sessions/{id}/stop` → 404 |
| J-12 Open-universe run | (none) | **failing** | §GATE — superset of absent Layer-1 endpoint |
| J-13 Hard token/USD budget | (none) | **failing** | §GATE — no budget cost-tracker surface |
| J-14 Staged SCREEN/PROMOTE | (none) | **failing** | §GATE — no staging surface |
| J-15 Global-history warm start + opt-out | (none) | **failing** | §GATE — no planner/history-scope surface |
| J-16 Robust objective gates overfit | (none) | **failing** | §GATE — no leaderboard/robust-selection surface |

**Verification-method note:** Pixel screenshots came back blank — the headless Chrome-MCP tab ran backgrounded (`visibilityState=hidden`), throttling async-init + GPU compositing (a known automation-environment limitation, not an app defect). Each passing journey was therefore verified against the **authoritative backend endpoints the UI calls** (HTTP status + parsed payloads) plus the captured rendered DOM. Evidence is concrete (specific trade counts, run_ids, WFE value, suggestion count) — not summary-trust.

## Anti-goal Check

No anti-goal can be *introduced* this iteration (zero code changes). Observable signals at baseline:

| Anti-goal | Status | Notes |
|-----------|--------|-------|
| No hard-coded credentials/keys in source | OK | No code changes; keys via env (`OPENAI_API_KEY` resolved from env, functionally working) |
| Sandbox blocks IO/network/exec/eval/import/open/os | OK | `tests/test_sandbox.py` passes |
| No lookahead | OK | `tests/test_lookahead.py` passes |
| No nondeterministic backtests (seeded slippage) | OK | `tests/test_determinism.py` passes |
| No paid SaaS beyond Anthropic/OpenAI | OK | No dependency changes |
| Frozen `shared/contracts.py` not mutated in place | OK | No code changes |
| OHLCV single Parquet per (symbol,timeframe); no re-fetch when cached | OK | `loader.py` single-parquet path; J-06 warm re-run did not re-fetch Binance |
| `BACKTEST_STORE_DIR` default non-`/tmp`; survives restart | OK | Default `<repo>/.data/backtests` (abs, repo-rooted); guarded by `test_session_store.py` |
| No relational DB / SQLite | OK | No DB routes; no `*.db`/`*.sqlite`; no `sqlite`/`sqlalchemy` in backend source |
| `GET /api/sessions/{id}` not eager-parsing full result/rating | **SIGNAL — needs coherence verdict** | List path lightweight ✓; per-iteration detail IS lazy ✓ (J-02). But the single-session OPEN payload (~245KB) embeds `equity_curve`. PRE-EXISTING contract (not introduced this iter; accepted at GOAL_ACHIEVED in `money-billions`). Recorded as a signal for a future coherence pass — **not** a violation attributed to iter-0. |
| All J-07…J-16 automated-session anti-goals (same artifacts, hard budget, persisted autoRun, backend-only loop, reuse BacktestPipeline, bounded seed universe, robust-best, SCREEN/PROMOTE, code-hash dedup, read-only history mining, prompt caching, non-blocking event loop, no new infra, no secrets in logs) | N/A — not yet built | The entire automated surface is absent (404). These become live, enforceable anti-goals the moment Layer-1/2 code lands; the decomposer must bake them into the build spec. |

**Coherence:** No `coherence.md` for iter-0 — expected, since a zero-diff verify-only baseline introduces no surfaces or values to audit. No `COHERENCE-FAIL`; no structural veto.

## Next-Step Recommendation

Begin **Layer-1 Foundation (J-07…J-11)** — the headless, backend-driven automated session — at **full** depth. Concretely, the first feature iteration should establish the core backend auto-session loop and its endpoints, reusing the existing `BacktestPipeline` (no sandbox/engine bypass):
- `POST /api/auto-sessions` (start; pinned config first — symbol/timeframe/dates/model/targets/`budget.max_iterations`) and `POST /api/auto-sessions/{id}/stop` → unblocks J-07, J-11.
- A backend iterate loop that writes the **same** session/iteration/activity/suggestion artifacts the UI already renders (no parallel store, no schema fork) → J-08 live tracking, J-09 terminal + stop-reason + best-marking.
- Durable `autoRun` status persisted to the file store (survives worker restart + browser reload) and the in-browser Auto Run **rewired** to the backend loop (remove the second in-browser iterate loop) → J-10.
- An immutable hard budget/cost tracker (tokens/USD + max-configs + wall-clock) from the start, even though the tight enforcement journey (J-13) lands with Layer-2.

The decomposer may split Layer-1 across more than one iteration; **land Layer-1 green before Layer-2 (J-12…J-16)** per goal.md's layering. Defer the open-universe optimizer (planner/bandit, SCREEN/PROMOTE, global-history warm start, robust/WFE overfit gating) to subsequent iterations.

Two baseline items to carry forward (neither blocks the next iteration):
1. **Eager-load signal:** have the coherence-auditor (or an early `Mode: next` touching `session_routes.py`) deliver a definitive verdict on the ~245KB `GET /api/sessions/{id}` open payload embedding `equity_curve`.
2. **Pre-existing test failure:** `test_directions_cache.py::test_write_and_read_full_round_trip` (nice-to-have Capability #10) is red on HEAD — fix opportunistically if a future iteration touches the directions cache; it is out of the Must-have journey set.

## Halt Justification (if halting)

N/A — not halting. CONTINUE.
