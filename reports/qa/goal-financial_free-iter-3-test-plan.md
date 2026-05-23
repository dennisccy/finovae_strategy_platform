# goal-financial_free-iter-3 Functional Test Plan

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Frontend Present:** yes

## Phase Goal

A single API call carrying only objective + budget launches a server-side open-universe search that explores ≥2 distinct configs from a bounded seed universe, runs to a terminal state inside a hard token/USD/configs/wall-clock budget enforced by the immutable cost tracker, marks the best by the robust WFE-gated objective, and streams live into the existing session UI with token + USD spend now visible in the status strip.

## Test Cases

### TC-01 — Open-universe POST returns 200 (no symbol/timeframe)
**Type:** api
**Preconditions:** Backend running on localhost:8000; no live LLM key required (hermetic/fake pipeline acceptable).

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auto-sessions -H 'Content-Type: application/json' -d '{"objective":"robust","budget":{"max_configs":2,"max_tokens":50000,"max_usd":0.05,"max_wall_clock_seconds":120}}'`

**Expected outcome:** Request accepted; routed to open-universe controller, not 400-rejected.
**Pass criteria:** HTTP status `200` (was `400` before this iteration).

---

### TC-02 — Pinned-config POST still returns 200 (J-07 unchanged)
**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. POST `/api/auto-sessions` with both `symbol` + `timeframe` present, `objective:"robust"`, valid `budget`, and a `natural_language` idea.
2. GET `/api/sessions` and locate the created session.

**Expected outcome:** Pinned single-config improvement-rounds loop runs unchanged; session appears in list.
**Pass criteria:** HTTP `200`; session present in `/api/sessions`; pinned path behavior byte-for-byte unchanged (no open-universe branch taken).

---

### TC-03 — Route matrix: rejection cases preserved
**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. POST pinned request with an unsupported `timeframe` → expect 400.
2. POST with `objective` != `"robust"` → expect 400.
3. POST with `budget` omitted → expect 422.
4. POST with `max_configs` ≤ 0 (and separately `max_tokens` ≤ 0, `max_usd` ≤ 0) → expect 422 each.

**Expected outcome:** Validation and unsupported cases rejected as before; new budget fields validated > 0.
**Pass criteria:** Statuses are exactly 400 / 400 / 422 / 422 (×3) respectively.

---

### TC-04 — Open-universe explores ≥2 distinct configs, best by robust score
**Type:** api
**Preconditions:** Hermetic fake pipeline or live key; small budget (`max_configs`≥2).

**Steps:**
1. POST open-universe request (objective+budget only).
2. Poll `GET /api/sessions/{id}` until terminal state.
3. Inspect iterations and `autoRun.bestIterationId`.

**Expected outcome:** ≥2 iterations created with differing `params` (symbol and/or timeframe) drawn from the bounded seed universe; best marked by `RobustScorer` across configs.
**Pass criteria:** ≥2 distinct-config iterations present; `autoRun.bestIterationId` set to the highest robust-score config (not merely highest raw return / WFE-failing). Configs come from the seed universe, not the full `/api/symbols` list.

---

### TC-05 — Hard budget: token/USD cap → budget-exhausted, no overrun
**Type:** api
**Preconditions:** Tiny token/USD budget guaranteed to trip after ≤1 config.

**Steps:**
1. POST open-universe with a tiny `max_tokens` (and separately a tiny `max_usd`).
2. Poll `GET /api/sessions/{id}` to terminal state.
3. Read `autoRun.status`, `autoRun.stopReason`, and `autoRun.budget` (`tokens`/`maxTokens`, `usd`/`maxUsd`).

**Expected outcome:** Run stops at the cap; no iteration appended after the cap is reached.
**Pass criteria:** `status="budget-exhausted"` and `stopReason="budget-exhausted"`; recorded `tokens`/`usd` ≤ cap within one-call tolerance; iteration count does not grow after the cap (cap checked before starting each config — never "one more").

---

### TC-06 — max_configs hard cap evaluates exactly ≤ N configs
**Type:** api
**Preconditions:** Budget with `max_configs=2`, token/USD/wall-clock large enough not to trip first.

**Steps:**
1. POST open-universe with `max_configs=2`.
2. Poll to terminal; count iterations.

**Expected outcome:** Search stops after 2 configs.
**Pass criteria:** Exactly ≤2 config iterations evaluated; terminal `stopReason="budget-exhausted"`.

---

### TC-07 — BudgetTracker unit: independent token and USD caps + immutability
**Type:** artifact
**Preconditions:** `tests/test_auto_session.py` with hermetic fake pipeline.

**Steps:**
1. Run the unit test asserting `BudgetTracker.exceeded()` returns True at the token cap and at the USD cap independently, evaluated before the next unit of work.
2. Assert `with_usage()` / `with_config_completed()` return new instances (frozen dataclass, no in-place mutation).
3. Assert tokens→USD mapping equals an exact value against the `model_catalog.py` rate table.

**Expected outcome:** Caps enforced independently; tracker immutable; rate math exact.
**Pass criteria:** All three assertions pass; tokens→USD asserted to an exact value matching the catalog constant.

---

### TC-08 — Token/USD accounting threads real (faked) SDK usage
**Type:** artifact
**Preconditions:** Fake generators expose `prompt_tokens`/`completion_tokens` (OpenAI) or `input_tokens`/`output_tokens` (Anthropic) on the side channel.

**Steps:**
1. Run the hermetic test that feeds faked SDK usage through `generate_strategy`/`generate_insights` → pipeline → controller `BudgetTracker.with_usage()`.
2. Verify `autoRun.budget.tokens`/`usd` reflect threaded usage (not estimation).

**Expected outcome:** Real SDK usage propagates end-to-end without touching frozen `GenerateStrategyResult`/`shared/contracts.py`.
**Pass criteria:** Recorded tokens/USD match the faked usage; no token fields added to frozen contracts.

---

### TC-09 — Non-fatal per-config failure; all-fail run terminates cleanly
**Type:** artifact
**Preconditions:** Hermetic test injecting generation/backtest failure for one or all configs.

**Steps:**
1. Run test where one config's generation/backtest fails → search continues to remaining configs.
2. Run test where every config fails → run terminates.

**Expected outcome:** Single failure logged and non-fatal; all-fail run ends cleanly without crash.
**Pass criteria:** Single-fail case completes remaining configs; all-fail case terminates `budget-exhausted` with no unhandled exception/crash.

---

### TC-10 — No secrets in activity log or autoRun block
**Type:** api
**Preconditions:** A completed open-universe run.

**Steps:**
1. GET `/api/sessions/{id}` and inspect `autoRun` block and the activity log.
2. Grep for API-key patterns (e.g. `sk-`, `OPENAI_API_KEY`, Anthropic key prefixes).

**Expected outcome:** No API key or secret persisted anywhere.
**Pass criteria:** Zero key/secret matches in `autoRun` block or activity log artifacts.

---

### TC-11 — B1+B2 race, cache reuse, dedup, invariants (regression suite)
**Type:** artifact
**Preconditions:** Full backend test suite runnable.

**Steps:**
1. Run the auto-session suite incl. the B1+B2 (`stop` vs `save` under shared lock) race regression on the open-universe loop.
2. Run `test_lookahead`, `test_determinism`, `test_sandbox`.
3. Confirm OHLCV Parquet cache reused across configs (no re-fetch with covering cache) and identical strategies (by code hash) not re-backtested.

**Expected outcome:** Concurrency invariant green; determinism/lookahead/sandbox green; cache + dedup honored.
**Pass criteria:** All listed tests pass. Pre-existing red `test_directions_cache::test_write_and_read_full_round_trip` remains the only known failure (non-blocking, untouched).

---

### TC-12 — Status strip shows token / USD / configs counters (live)
**Type:** browser
**Preconditions:** Vite frontend serving (health-check at start AND re-probe mid-window); an open-universe run active or recently completed. Falls back to backend-endpoint verification only if pixels blank under the documented hidden-tab render throttle (and say so).

**Steps:**
1. Navigate to the session workstation; locate the Iterations panel `AutoSessionStatusStrip`.
2. Observe the budget counter group while a run is active (~2.5s poll).
3. Verify token chip (`spend / cap`, compact e.g. `1.2k / 50k tok`), USD chip (`$0.0123 / $0.05`), and configs chip (`configsDone/maxConfigs configs`) alongside existing rounds + wall-clock.

**Expected outcome:** Counters render read-only from `autoRun.budget`, accrue live, no recomputation in UI; cap shown only when present.
**Pass criteria:** Token, USD, and configs counters visible and update live; values mirror `GET /api/sessions/{id}` → `autoRun.budget`. Pinned sessions (no `max_configs`) render cleanly with the configs chip omitted. Screenshot saved to `reports/qa/goal-financial_free-iter-3-evidence/`.

---

### TC-13 — J-08 live tracking + J-10 reload-mid-run survival (open-universe)
**Type:** browser
**Preconditions:** Frontend serving; open-universe run active.

**Steps:**
1. With a run active, observe distinct-config iteration cards streaming in without manual reload (J-08); each card shows its `params` symbol/timeframe.
2. Reload the browser mid-run (J-10); confirm `autoRun` status + counters restore from the durable store.

**Expected outcome:** Cards stream live; reload survives (status persisted server-side, not browser memory).
**Pass criteria:** New config cards appear without reload; after reload the active run state + budget counters are restored from `GET /api/sessions/{id}`. Screenshots saved under the evidence dir. Clears accumulated J-08/J-10 live-pixel debt.

---

### TC-14 — J-01 + J-05 manual regressions (no-regression pixels)
**Type:** browser
**Preconditions:** Frontend serving across the whole window.

**Steps:**
1. Exercise the J-01 manual flow (existing core session flow) end-to-end.
2. Exercise the J-05 manual flow end-to-end.

**Expected outcome:** Both pre-existing manual journeys still work — no regression from the open-universe/budget changes.
**Pass criteria:** J-01 and J-05 complete successfully with real pixels (or documented backend-endpoint fallback). Screenshots saved under the evidence dir.

---

### TC-15 — Required-still-passing backend journeys J-09 / J-11
**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. J-09: run a pinned auto-session to terminal; verify terminal `stopReason` and WFE-gated best selection.
2. J-11: issue server-side `/stop` on an active run; verify it halts server-side.

**Expected outcome:** Terminal stop-reason + WFE best (J-09) and server-side stop (J-11) intact.
**Pass criteria:** J-09 terminal run sets a valid `stopReason` and a WFE-gated `bestIterationId`; J-11 `/stop` transitions the run to a stopped terminal state.

---

### TC-16 — Dev handoff artifact present
**Type:** artifact
**Preconditions:** Implementation complete.

**Steps:**
1. Check `docs/handoffs/goal-financial_free-iter-3-dev.md` exists and summarizes the changes.

**Expected outcome:** Handoff written.
**Pass criteria:** File exists and is non-empty.

---

### TC-17 — Optional: live key-gated open-universe smoke
**Type:** api
**Preconditions:** `OPENAI_API_KEY` present (skip otherwise).

**Steps:**
1. POST one tiny real open-universe run (≤2 configs, short date range, cheapest model).
2. Poll to terminal state.

**Expected outcome:** Real run reaches a terminal state within budget; real token/USD recorded.
**Pass criteria:** Run terminates (`budget-exhausted` or natural completion) with non-zero real token/USD spend ≤ caps. Marked SKIPPED if no key.

---

## Summary

Total test cases: 17
- **API tests: 9** — TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-10, TC-15, TC-17
- **Browser tests: 3** — TC-12, TC-13, TC-14
- **Artifact checks: 5** — TC-07, TC-08, TC-09, TC-11, TC-16
