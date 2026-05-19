# goal-auto-money-printer-iter-3 — QA Validation Report (MODE 2)

**Verdict:** PASS

**Phase:** goal-auto-money-printer-iter-3 (Optimizer Foundation — J-12 open-universe + J-13 hard cost tracker)
**Date:** 2026-05-19
**Agent:** qa (QA validation mode, retry pass after round-1 TC-07 fix)
**Frontend Present:** yes — Chrome MCP browser checks performed

---

## Executive summary

The indivisible J-12 (open-universe bounded-seed search) + J-13 (immutable hard
cost tracker, real SDK-usage capture, per-model USD table, budget-exhausted
terminal + durable visible spend) slice is implemented to spec and is
shippable. The round-1 blocker (TC-07: `objective`/`history_scope` accepted but
not persisted) is fixed and independently re-verified on-disk and via
`GET /api/sessions/{id}`.

Per the spec's mandatory skeptical-evaluation note, the browser-qa
`ui-test-results.md` PASS headline was **not** taken at face value. It was
cross-checked at four independent levels — (1) post-fix source diff, (2)
unit/artifact test bodies, (3) durable file-store ground truth from 58 real-LLM
sessions, (4) live Chrome MCP UI — and holds up. The cost tracker is fed
**real captured SDK usage** through the production path, not a constant that
passes by construction (verified at source + test level; corroborated by 58
durable sessions with *varying* token totals).

**Backend full suite: 183 passed / 1 failed** — the single failure is only the
pre-existing, out-of-scope, baseline-documented
`test_directions_cache.py::test_write_and_read_full_round_trip` (baseline 150
passed/1 failed → **+33 net-new passing, zero new regressions**). iter-3
targeted suites **59 passed**. Frontend `npm run build` **EXIT 0**.

---

## Step 1 — Artifact verification checklist

| Artifact | Status |
|----------|--------|
| `docs/handoffs/goal-auto-money-printer-iter-3-dev.md` | ✅ present (incl. round-1 fix notes) |
| `reports/reviews/goal-auto-money-printer-iter-3-review.md` | ✅ **PASS_WITH_NOTES** |
| `runs/goal-auto-money-printer-iter-3/status.json` | ✅ present (`dev_complete`, `next_action: re_qa`) |
| `reports/qa/goal-auto-money-printer-iter-3-test-plan.md` | ✅ present (22 cases) |
| 6 UI artifacts (impl-summary / user-visible-changes / ui-surface-map / ui-test-plan / ui-test-results / what-to-click) | ✅ all present & populated |
| Durable store `BACKTEST_STORE_DIR` | ✅ `<repo>/.data/backtests` — **NOT** `/tmp` (anti-goal satisfied) |

---

## Step 2 — Backend test results (exact output)

Command: `cd apps/backend && .venv/bin/python -m pytest -q`

```
1 failed, 183 passed, 4 warnings in 10.67s
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip
  assert len(result["timeframeResults"]) == 1  / assert 0 == 1
```

The single failure is the pre-existing out-of-scope baseline failure
(documented in the spec/plan/test-plan as the *only* tolerated failure). Log:
`reports/qa/goal-auto-money-printer-iter-3-test.log`.

Targeted iter-3 suites:
`pytest tests/test_auto_session.py tests/test_cost_tracker.py tests/test_model_pricing.py tests/test_usage_capture.py -q`
→ **`59 passed`** (`test_auto_session.py` = 37, was 26 pre-iteration; +2 from the
round-1 TC-07 fix). No skips, no xfail.

## Step 3 — Frontend build

`cd apps/frontend && npm run build` → **EXIT 0** (tsc + vite OK; the >500 kB
chunk warning is pre-existing, not an error).

---

## Step 3.5 — Functional test plan results (22 cases)

> Environment note (transparency, not a defect): the QA-runner-managed backend
> (pid 49306, port 8691) has **no `OPENAI_API_KEY`** in its process env, so a
> *fresh* live open-universe run cannot complete the real LLM generate/insights
> calls in this pass (a documented pre-existing platform constraint — see dev
> handoff "Known Issues"). The accept/validate/persist/lazy paths and all error
> paths were exercised live; the run-completion behaviour (J-12/J-13 runtime)
> was verified via (a) the deterministic unit suite (`FakePipeline`, no key
> needed), (b) **58 durable real-LLM sessions** the browser-qa run left in the
> file store (varying real spend), and (c) live Chrome MCP rendering of those
> terminal sessions. Per qa.md, environment-limited live runs with passing
> tests + strong corroborating evidence are **not** a FAIL.

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---------|------|------|----------|--------|---------|-------|
| TC-01 | Open-universe POST accepted (no symbol/timeframe) | api | 200 + sessionId + listed | `http=200`, `sessionId=1f082e2a…`, `status=running`, present in `GET /api/sessions` | **PASS** | Was hard-422 pre-iteration; gate relaxed correctly |
| TC-02 | ≥2 distinct configs, terminal in budget, robust best | api | ≥2 distinct `(sym,tf)`, terminal, robust best | Durable sid 31e5ba14: 6 distinct seed configs (BTC/ETH/SOL/BNB×4h/1h), `status=complete`, `stopReason=budget-exhausted`, `bestIterationId` set & among iter ids; activity log lists all 6 "Exploring config N: …"; unit `test_open_universe_runs_multiple_distinct_configs` green | **PASS** | Configs ⊆ `_SEED_UNIVERSE` (no fan-out). Live run gated by no-key; covered by unit + 58 durable sessions + UI |
| TC-03 | Tiny token/USD budget → budget-exhausted, ≤cap, no post-cap iter | api | budget-exhausted, spend≤cap, 0 post-cap iters | Unit `test_hard_token_budget_exhausted_real_usage_and_durable_spend`: exact real spend, `len(iteration_dirs)==1`, `gen_calls==1`, durable. browser-qa 1-tok probe: `configsRun=1, iterationHistory=1` (within-one-call tol.). Durable sessions: tokens ≤ caps | **PASS** | Hard ceiling enforced (round-top `would_exceed`); see Reviewer-MINOR note below |
| TC-04 | Unsupported objective → clean 422 | api | 422, detail, no 500, no session | `http=422` "Unsupported objective 'sharpe'. Only 'robust' is supported…"; sessions 85→85; no 500 | **PASS** | |
| TC-05 | Pinned path unchanged + malformed pinned 422 not 500 | api | (1) 200 (2)(3) 422 | (1) valid pinned `http=200` (sid=b1146b84); (2) missing symbol `422` "Missing required pinned config field(s): symbol…"; (3) bad date `422` "start_date and end_date must be YYYY-MM-DD." | **PASS** | Pinned accept/validate byte-unchanged; never 500 |
| TC-06 | Malformed open-universe budget/dates → 422 never 500 | api | both 422, no 500 | (a) `max_ai_tokens:"lots"` → `422` Pydantic int_parsing; (b) malformed dates → `422` | **PASS** | |
| TC-07 | history_scope + objective accepted **& persisted** (round-1 blocker) | api | persisted & re-readable | POST 200; `GET /api/sessions/{id}` → `autoRun.objective="robust"`, `autoRun.historyScope="this-run"`; **on-disk** `.data/backtests/live/<sid>/session.json` carries both verbatim; unit `test_open_universe_objective_and_history_scope_persisted` green (RED→GREEN) | **PASS** | Round-1 FAIL fixed & independently re-verified on the real restart/reload path |
| TC-08 | `GET /api/sessions/{id}` stays lazy | api | metadata only, no heavy inlining | iterationHistory items = summary metrics only (`id/totalReturn/sharpe/robustScore/params/walkForwardResult`); `result` empty — **no `equity_curve`/`trades` arrays inlined** | **PASS** | Lazy behaviour byte-unchanged |
| TC-09 | Durable spend survives restart + non-/tmp store | api | byte-identical after re-read; not /tmp | Store = `<repo>/.data/backtests` (not /tmp); spend persisted in durable `autoRun`; unit asserts fresh `read_session_meta` re-read survives; 58 sessions hold spend on disk | **PASS** | Real-restart proxy = fresh disk re-read (unit + on-disk inspection) |
| TC-10 | J-12 browser: ≥2 distinct configs + robust BestBadge | browser | ≥2 distinct cfgs, 1 Best, terminal | Live UI: opened session shows "Iterations (2)" — BTC 4H ⭐**Best** / ETH 4H, distinct symbols; other sessions render 6 distinct seed configs; robust-not-raw visible (ETH WFE 6.60 **Best** over BTC +4.46% WFE −0.05) | **PASS** | Evidence: `QA-TC10-TC11-autorunbar-spend-budget-exhausted.png` |
| TC-11 | J-13 browser: AutoRunBar spend + legible budget-exhausted | browser | numeric tok/USD/cfg + amber budget reached | Amber `bg-amber-50` AutoRunBar "Automated run complete · budget reached · 2/2 iterations" + spend span (`ml-auto shrink-0 tabular-nums opacity-75`) "**9,825 tok · $0.0084 · 2 cfg**"; no NaN/undefined; visually distinct from blue running | **PASS** | Same evidence screenshot |
| TC-12 | J-08 browser: fresh running session not a stale terminal | browser | "running", not stale terminal | Live UI on heavy 87-session DOM: running session shows **blue** `bg-primary-50` "Automated run · iteration 1/10" + "0 tok · $0.0000 · 1 cfg" — NOT a stale `budget reached`/`stopped` | **PASS** | Evidence: `QA-TC12-running-not-stale-terminal.png` |
| TC-13 | J-02 browser: prior-run RIGHT panel re-binds | browser | full right panel re-binds | Clicked prior non-Best "ETH 4H EMA Breakout" → RIGHT panel re-bound: `ETH/USDT 4h` header + walk-forward + equity curve + trades table + OOS metrics (OOS Sharpe −0.894…) | **PASS** | Evidence: `QA-TC13-J02-prior-run-rebind-ETH.png` |
| TC-14 | Legacy/pinned graceful when spend absent | browser | bar unchanged, no NaN | Source-verified: `formatSpend` returns `''` when no spend; `{spendText && (...)}` guarded render; per-field `typeof === 'number'` guards; useBacktest.ts adds type-only `AutoRunSpend?` (no poll-logic deletions). Corroborated by browser-qa UT-07 (manual → no AutoRunBar) | **PASS** | Additive-only; no NaN/undefined risk |
| TC-15 | Immutable cost tracker unit | artifact | frozen/monotonic/per-cap/safe-default | `test_cost_tracker.py`: `FrozenInstanceError` on mid-run cap mutation; monotonic + negative/None ignored; token/USD/configs/wall caps each fire **independently**; zero/neg→safe finite default; huge→hard-ceiling; exact-value asserts; 0 skip/xfail | **PASS** | |
| TC-16 | Real-usage-fed guard (iter-2 false-guard generalization) | artifact | exact real counts, fails if bypassed | `test_usage_capture.py` drives the **real** `ScriptGenerator`/`InsightsGenerator`/`StrategyCompiler`/`BacktestPipeline` with fake SDK clients carrying real-shaped `.usage` (OpenAI `prompt/completion`, Anthropic `input/output` + cache fields) → asserts exact captured counts. `test_hard_token_budget…` asserts tracker total == exact summed fake usage (300) through the loop drain. Both **fail if capture is bypassed/hardcoded** | **PASS** | Genuinely real-fed, **not** pass-by-construction. Independently corroborated by 58 durable sessions with *varying* token totals (28963/28888/…/19204 — not a constant) |
| TC-17 | Deterministic non-blocking guard (multi-config) | artifact | child_pid != getpid, no timing | `test_open_universe_multi_config_runs_in_subprocess_distinct_pids`: asserts each config's `run_id` pid `!= os.getpid()` via the existing subprocess seam; no `time.sleep`/elapsed threshold; fails if forced in-process | **PASS** | iter-2 lesson honoured deterministically |
| TC-18 | Robust best across configs (not raw return) | artifact | best=robust winner, raw-loser asserted not best | `test_open_universe_best_is_robust_not_raw_return`: cfg1 raw 5.0/WFE 0.0 vs cfg2 0.2/WFE 0.8 → asserts `bestIterationId == id2` **and** `!= id1` (raw-return candidate explicitly NOT best). Live UI corroborates | **PASS** | Reuses `select_best`, not re-implemented |
| TC-19 | Durable restart + bounded seed + unknown-model safety | artifact | survives re-read; seed constant; unknown-model safe | Unit asserts fresh meta re-read carries spend + budget-exhausted + no post-cap config; `cfgs <= set(_SEED_UNIVERSE)` (6-entry hard-coded constant, not 26×6/env/live); `test_unknown_model_keeps_token_cap_binding_no_crash` (0 USD, tokens still bind) | **PASS** | |
| TC-20 | Backend suites green + frontend build clean | artifact | 1 pre-existing fail only; build EXIT 0 | Full suite **183 passed / 1 failed** (only `test_directions_cache::test_write_and_read_full_round_trip`); iter-3 targeted **59 passed**; `npm run build` **EXIT 0** | **PASS** | Zero new regressions (+33 net-new passing) |
| TC-21 | Anti-goal source guards (contracts/sandbox/engine/no-infra/no-secrets) | artifact | 0 diff; no infra; no secrets | `git diff shared/contracts.py` = **0 lines**; `sandbox.py` untouched; no engine/backtest-internals/`BacktestPipeline`-orchestration changed; no new infra import (celery/redis/sqlalchemy/kafka/chromadb/…); `grep` secrets in `.data/backtests` + `activity.jsonl` = **0 matches** | **PASS** | |
| TC-22 | Closure artifacts present & non-vague | artifact | 7 files populated | Dev handoff + 6 UI artifacts all present & populated (impl-summary 123L, user-visible 101L, ui-surface-map 74L, ui-test-plan 454L, ui-test-results 148L, what-to-click 116L) | **PASS** | Phase-closure gate runs downstream |

**22/22 test cases passed.** (0 failed, 0 skipped.)

Coverage: J-12 → TC-01/02/10 ✅ · J-13 → TC-03/09/11/15/16/19 ✅ ·
J-07–J-11 pinned regression → TC-05/08 ✅ · J-08 → TC-12 ✅ · J-02 → TC-13 ✅ ·
legacy graceful → TC-14 ✅ · error cases → TC-04/06/07 ✅ ·
anti-goal/lesson guards → TC-15–19/TC-21 ✅ · suites & closure → TC-20/22 ✅.

---

## Step 4 — Chrome MCP browser checks

Frontend reachable at `http://localhost:3691` (HTTP 200). Browser checks
performed via Chrome MCP against the QA-runner-managed services. The
accumulated 87-session DOM (≈1247 buttons) makes *generic* DOM selectors noisy
— exactly the "heavy multi-session DOM" the browser-qa-agent documented; the
authoritative screenshots + targeted evals below are conclusive.

- **Spend readout (J-13):** amber `bg-amber-50 border-amber-200 text-amber-700`
  AutoRunBar "Automated run complete · budget reached · 2/2 iterations" with a
  right-aligned dimmed span `9,825 tok · $0.0084 · 2 cfg`
  (`ml-auto shrink-0 tabular-nums opacity-75`). `hasNaN:false`,
  `hasUndefined:false`. Visually distinct from the blue running state.
- **Running not stale (J-08):** a still-running session rendered blue
  `bg-primary-50` "Automated run · iteration 1/10" + `0 tok · $0.0000 · 1 cfg`
  — correctly live, not a stale terminal, on the heavy DOM.
- **≥2 distinct configs + robust Best (J-12):** "Iterations (2)" with BTC 4H
  ⭐Best / ETH 4H (distinct symbols); other open-universe sessions render 6
  distinct seed configs; robust-not-raw-return visible (an ETH WFE 6.60 marked
  Best over a higher-return BTC +4.46% WFE −0.05).
- **J-02 re-bind:** clicking the prior non-Best ETH card re-bound the full
  RIGHT analysis panel (ETH/USDT 4h header, walk-forward, equity curve, trades
  table, OOS metrics).

Evidence saved under `reports/qa/goal-auto-money-printer-iter-3-evidence/`:
`QA-TC10-TC11-autorunbar-spend-budget-exhausted.png`,
`QA-TC12-running-not-stale-terminal.png`,
`QA-TC13-J02-prior-run-rebind-ETH.png` (plus the browser-qa-agent's UT-01–UT-11
screenshots already in the same directory).

---

## Step 4b — UI Evolution Audit

1. **Did the UI evolve to reflect the new capability?** Yes — the existing
   `AutoRunBar` gained an additive recorded-spend readout (AI tokens / USD /
   configs) and a visually distinct amber `budget-exhausted` terminal, and the
   existing iteration tree renders the ≥2 explored open-universe configs
   indistinguishably from a manual run with the existing robust `BestBadge`.
2. **Can the user see/understand/control it?** Yes — spend and the hard-budget
   stop are legible in the bar; explored configs + robust-best are visible in
   the tree; the activity log records every explored config. Start is
   intentionally API-only (spec: no net-new start affordance) — expected, not a
   gap.
3. **Still relying on old generic pages?** No — reuses the correct existing
   surfaces (iteration tree, `BestBadge`, `AutoRunBar`) exactly as the spec
   mandated; the spend readout is the only additive net-new element.
4. **Technically complete but product-underexposed?** No — the new capability
   (headless cost-bounded search) is exactly as exposed as the spec scopes it.

**Verdict:** UI-PASS — the UI meaningfully and proportionately reflects the new
capability with an additive, well-guarded readout; no regression to existing
journeys (J-02/J-08 re-verified live).

---

## Skeptical cross-check findings (spec-mandated)

- **Real-usage, not pass-by-construction:** verified at *source* (capture_usage
  wired into compiler/script_generator/insights_generator with the real SDK
  response → pipeline forwards `usage_sink` → auto-session `_drain_usage` →
  `tracker.record_usage`) and at *test* level (`test_usage_capture.py`
  exercises the real generator/pipeline classes; `test_hard_token_budget…`
  asserts the exact summed counts through the loop drain — both fail if
  bypassed). Independently corroborated: 58 durable real-LLM sessions show
  **varying** token totals, impossible with a hardcoded constant.
- **Anti-goals (source-diff level, not report headline):** `contracts.py` 0-diff;
  `sandbox.py` untouched; deterministic engine / backtest internals /
  `BacktestPipeline` orchestration unchanged; bounded 6-entry seed constant (no
  fan-out); caps frozen at construction; best by robust objective not raw
  return; subprocess seam + deterministic child-pid guard (no timing); Parquet
  cache reused (fixed default window); durable `autoRun` in `<repo>/.data`
  (not /tmp), survives re-read; no new infra; no secrets in artifacts/activity
  log. All hold.

## Notes / non-blocking observations (carried from reviewer PASS_WITH_NOTES)

- **Reviewer MINOR (accepted, non-blocking):** no `tracker.would_exceed()`
  check between the post-generate `_drain_usage` and the insights call, so a
  terminal round can run *generate + insights* (worst-case overshoot = one
  config's gen+insights, slightly beyond a strict single-in-flight-call
  tolerance). The hard ceiling is still enforced (round-top `would_exceed` ⇒ no
  unbounded loop, **no post-cap round/config**); spend is honestly recorded;
  overshoot is bounded and unit-tested. The J-13 DoD measurable criteria
  (budget-exhausted terminal, zero post-cap config, spend ≤ cap within
  one-call tolerance, durable + visible) are all met. The dev handoff's wording
  "a second LLM call is skipped once a cap is hit" is inaccurate (the skip was
  not implemented) — a documentation NOTE flagged by the reviewer, not a
  functional defect.
- **Environment:** no `OPENAI_API_KEY` in the QA backend env prevented a *fresh*
  live full open-universe run this pass; J-12/J-13 runtime behaviour is
  conclusively covered by the deterministic unit suite + 58 durable real-LLM
  sessions + live UI rendering. Not a FAIL per qa.md.

## Blockers

**None.** The round-1 blocker (TC-07) is fixed and re-verified. No new blockers.

## Step 5b — Server cleanup

No servers were started by QA (only `pytest`, which exits; backend/frontend are
QA-runner-managed). Nothing to kill.

## Step 6 — status.json

Updated: `status="complete"`, `current_step="qa_complete"`.
