# goal-financial_free-iter-3 QA Report

**Verdict:** PASS

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Agent:** qa (MODE 2 — validation)
**Frontend Present:** yes
**Backend:** http://localhost:8691 (healthy at `/api/health`) · **Frontend:** http://localhost:**3691** (the prompt said 3692; the QA-runner Vite actually served on 3691, backend-paired via proxy → `localhost:8691`)

---

## Summary

J-12 (open-universe multi-config search) and J-13 (hard token/USD/configs budget) are functionally
verified **end-to-end with real LLM runs** against the live backend. A single API call carrying only
`objective` + `budget` (+ a date range, which the contract still requires) launches a server-side
open-universe search, explores ≥2 **distinct** configs from a bounded seed universe, accrues **real**
token/USD spend, terminates inside a hard budget (`stopReason="budget-exhausted"`), and marks the best
by the WFE-gated robust objective. The pinned J-07/J-09 path and J-11 server-side stop remain intact.
Reference data (J-05) and the manual NL backtest (J-01) still work. No secrets persisted.

Two non-blocking notes: (1) a **flaky** timing test in the route suite, and (2) interactive
status-strip **pixel** capture was blocked by the documented Chrome-MCP hidden-tab render throttle
(compounded by a concurrent QA holding the foreground tab) — verified instead via the exact backend
endpoints the UI consumes, per the spec's sanctioned fallback. One clean real-pixel render of the app
workstation was captured.

---

## Step 1 — Artifact verification

| Artifact | Status |
|----------|--------|
| `docs/handoffs/goal-financial_free-iter-3-dev.md` | ✅ present, non-empty |
| `docs/handoffs/goal-financial_free-iter-3-frontend.md` | ✅ present |
| `reports/reviews/goal-financial_free-iter-3-review.md` | ✅ PASS_WITH_NOTES |
| `runs/goal-financial_free-iter-3/status.json` | ✅ present |
| `reports/qa/goal-financial_free-iter-3-test-plan.md` | ✅ present (executed below) |

---

## Step 2 — Backend test results

Command: `cd apps/backend && .venv/bin/python -m pytest` (full suite). Log: `reports/qa/goal-financial_free-iter-3-test.log`

```
=========== 2 failed, 193 passed, 1 deselected, 4 warnings in 6.47s ===========   (first run)
=========== 1 failed, 194 passed, 1 deselected, 4 warnings in 6.45s ===========   (re-run)
```

- **194 passed** on re-run. **1 deselected** = the optional live key-gated smoke.
- **1 pre-existing red** — `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  (Capability #10 nice-to-have, untouched; identical failure in iter-1/iter-2). **Documented
  carry-forward, not a regression.**
- **1 FLAKY failure (NOTE, non-blocking)** — `tests/test_auto_session_routes.py::test_post_returns_before_loop_completes_and_get_stays_responsive`
  failed on the first full-suite run, then **passed in isolation** and **passed on the immediate full
  re-run** (194 passed). Repeated runs of the route file: 1 fail / 2 pass (3 runs). Root cause is a
  **test-scaffolding timing race**: the test gates the background loop on an `asyncio.Event` and
  asserts the run is still `"running"` immediately after POST; under full-suite load the gate/status
  window occasionally races. The **product** behavior (POST returns 200 immediately, loop runs async)
  is correct. Flagged for the dev to de-flake (e.g. await the gate-park signal before asserting), but
  it is **not a product regression**.

Targeted / invariant suites (all green):
- `test_lookahead`, `test_determinism`, `test_sandbox`, `test_model_rates` → **45 passed**.
- auto-session caps/token/usd/open-universe/dedup/race keyword subset → **27 passed**.

## Step 3 — Frontend tests

Per dev/frontend handoffs: `npm run build` (tsc + vite) passes; `npm run lint` (`--max-warnings 0`)
passes. `AutoRunBudget` TS type extended with `configsDone`/`maxConfigs`/`maxTokens`/`maxUsd`,
mirroring backend `to_dict()`. Not re-run here (no source change since dev); covered by review PASS.

---

## Step 3.5 — Functional test plan results

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---------|------|------|----------|--------|---------|-------|
| TC-01 | Open-universe POST → 200 | api | 200 (was 400) | **200** | PASS | Test-plan payload was incomplete (missing `start_date`/`end_date`/`max_iterations`, which the contract still requires → it 422'd); with a contract-valid open-universe body → 200, `autoRun.status=running`, budget block carries `configsDone/maxConfigs/maxTokens/maxUsd`. |
| TC-02 | Pinned POST → 200 (J-07) | api | 200 + listed | **200**, listed in `/api/sessions` | PASS | Pinned path unchanged. |
| TC-03 | Rejection matrix | api | 400/400/422/422×3 | **400** (bad tf), **400** (obj≠robust), **422** (no budget), **422/422/422** (`max_configs`/`max_tokens`/`max_usd` ≤0) | PASS | All exact. |
| TC-04 | ≥2 distinct configs, best by robust score | api | ≥2 distinct; best WFE-gated | **2 distinct** (`BTC/USDT 1h`, `ETH/USDT 1h`) from seed universe; **best set when a config passes the WFE gate** (run SID4 → `bestIterationId=722cdad7`) | PASS | Best=`None` when **no** config passes the WFE gate (short range → 0 walk-forward windows, or both gate-fail) — **correct gating** per anti-goal (a WFE-failing candidate must not be marked best). Demonstrated both: a positive best (722cdad7) and correct None. Configs drawn from the bounded seed universe, never `/api/symbols`. |
| TC-05 | Token/USD cap → budget-exhausted, no overrun | api | cap → exhausted; spend ≤ cap | Live runs terminated `budget-exhausted`; **tokens/usd ≤ caps** every run; `configsDone` never exceeded `maxConfigs` | PASS | Live tiny LLM usage didn't trip the token/USD cap itself (it tripped configs/wall-clock first), but the **token-cap and USD-cap `exceeded()` stops are deterministically proven by unit tests** (independent caps, checked before next unit). No iteration appended after a cap. |
| TC-06 | `max_configs` hard cap ≤ N | api | ≤2 configs | First open-universe run stopped at **exactly `configsDone=2 / maxConfigs=2`** | PASS | Cap checked before starting each config (never "one more"). |
| TC-07 | BudgetTracker: independent caps + immutability + exact rate | artifact | all assert | Covered by passing unit tests (token cap, USD cap, `with_usage`/`with_config_completed` return new instances, tokens→USD exact vs `model_catalog`) | PASS | 27 targeted + `test_model_rates` (6) green. |
| TC-08 | Token/USD threads real (faked) SDK usage | artifact | usage threaded end-to-end | Unit tests thread faked SDK usage → pipeline → `with_usage`; **live runs recorded REAL token/USD** (e.g. 4720 tok / $0.001025, 71786 tok / $0.020338) | PASS | Frozen `GenerateStrategyResult`/`contracts.py` untouched (side channel). |
| TC-09 | Non-fatal per-config failure; all-fail clean | artifact | continue / clean terminal | Covered by passing unit tests (single-fail continues; all-fail → clean `budget-exhausted`) | PASS | |
| TC-10 | No secrets in store/activity log | api | 0 matches | **0** key-pattern matches across **2964** store files (`sk-…`, `sk-ant-`, `sk-proj-`, `OPENAI/ANTHROPIC_API_KEY`) | PASS | |
| TC-11 | B1+B2 race, cache reuse, dedup, invariants | artifact | all green | Full suite 194 passed; invariants + race + dedup green | PASS | Only pre-existing `test_directions_cache` red (untouched). |
| TC-12 | Status strip token/USD/configs counters (live) | browser | counters render from `autoRun.budget` | App renders **real pixels** (workstation captured); **status-strip data contract fully present** in `autoRun.budget` (`tokens/maxTokens/usd/maxUsd/configsDone/maxConfigs`) | PASS (data-layer) / pixel-PARTIAL | Interactive strip pixel capture **blocked by the documented Chrome-MCP hidden-tab render throttle** (compounded by a concurrent QA on the foreground tab — background Finovae tab suspended to empty DOM between actions). Sanctioned fallback: verified via the exact endpoint the strip polls. One clean real-pixel render saved. |
| TC-13 | J-08 live tracking + J-10 reload survival (open-universe) | browser | cards stream; reload restores | Live poll showed **2 distinct config cards** + budget accruing (`configsDone 0→1→2`, tokens accruing) without reload; full `autoRun` (status + all budget keys) **persisted server-side** → reload restores from `GET /api/sessions/{id}`, not browser memory | PASS (endpoint) | Same throttle as TC-12 prevented interactive pixel capture; verified via the UI's exact poll endpoint. |
| TC-14 | J-01 + J-05 manual regressions | browser | both work | **J-05**: `/api/symbols`=200 (26), `/api/timeframes`=200 (6) — and symbol/timeframe controls **visibly populated** in the captured screenshot. **J-01**: manual `POST /api/run-backtest` (NL + symbol/tf/dates) → **200**, `run_id=cf1308bd`, equity curve **2183 points**, metrics + `strategy_spec` returned, run history grew 28→29 | PASS | J-01's 0 trades is a valid strategy outcome (RSI strategy didn't trigger in-window); metrics/equity/run_id all present. |
| TC-15 | J-09 / J-11 backend journeys | api | terminal + WFE best / server-side stop | **J-09**: pinned run → `budget-exhausted`, iterations capped 2/2, `bestIterationId=72115c78`, real spend 71786 tok/$0.0203. **J-11**: `/stop` on active run → transitions to `stopped` (`stopReason=stopped`) | PASS | |
| TC-16 | Dev handoff present | artifact | exists | `docs/handoffs/goal-financial_free-iter-3-dev.md` present & detailed | PASS | |
| TC-17 | Live key-gated open-universe smoke | api | terminal w/ real token/USD ≤ caps | **Effectively executed**: ≥4 real open-universe/pinned runs reached terminal with real token/USD spend ≤ caps | PASS | Not skipped — real key present and exercised. |

**17/17 test cases pass** (TC-12 at the data-contract layer + one real-pixel app render; interactive
strip pixels blocked by the documented throttle and verified via the UI's exact poll endpoint).

### Representative live evidence (real LLM runs)

```
open-universe run #1 (5-mo range): status=budget-exhausted stopReason=budget-exhausted
  configsDone=2/maxConfigs=2  tokens=4720/50000  usd=0.001025/0.05  wall=45.5s/120s
  iterations: BTC/USDT 1h (complete), ETH/USDT 1h (complete)   best=None (no config passed WFE gate → correct)

open-universe run SID4 (2.5-yr range): status=budget-exhausted (wall-clock 237>180)
  configsDone=1  best=722cdad7  (WF completed → robust-scored best MARKED)   tokens=2363 usd=0.000515

open-universe run LIVE (2.5-yr): budget-exhausted (wall 317>300) configsDone=2/3
  BTC/USDT 1h + ETH/USDT 1h complete; budget accrued live across polls

pinned J-09 run: budget-exhausted iterationsDone=2/maxIterations=2 best=72115c78
  tokens=71786 usd=0.020338  maxConfigs=null (pinned keeps rounds — correct)

J-11 stop: active run + POST /stop → status=stopped stopReason=stopped
```

---

## Step 4 — Chrome MCP browser checks

Frontend health: served **200** on `http://localhost:3691` at QA start and re-probed mid-window
(the prompt's `:3692` was not the live port; Vite was on `:3691`, proxy → backend `:8691`).

- **One clean real-pixel render captured** (`TC-12-app-loaded.png`): full Finovae workstation —
  Strategy Builder with 20 strategy cards for `BNB/USDT · 4h`, populated symbol/timeframe/exchange
  controls (J-05 visual), model dropdown, NL input, "No Iterations Yet" right panel, "Sessions 130".
  This proves the frontend serves and renders real pixels this iteration (better than iter-0/iter-2,
  which captured none).
- **Interactive status-strip capture BLOCKED** by the **documented Chrome-MCP hidden-tab render
  throttle** (per project memory: blank Chrome-MCP page = hidden-tab throttle, not an app bug). A
  **concurrent QA run was driving a second tab** (Gap Filler on `:3073`), holding foreground priority;
  the background Finovae tab repeatedly suspended to an **empty DOM** between actions. Multiple genuine
  attempts (navigate, show_browser, eval-introspect, navigate+immediate-eval) confirmed the app does
  hydrate (one eval saw 2863 buttons / 130 session forms; `await_text "Auto"` succeeded) but the
  suspend window made multi-step interaction (open session → read strip chips) unreliable.
- **Sanctioned fallback applied** (spec + qa.md): the status strip is read-only from
  `GET /api/sessions/{id}` → `autoRun.budget`. That exact endpoint was verified to carry every field
  the strip renders (`tokens/maxTokens/usd/maxUsd/configsDone/maxConfigs/wallClockSec/maxWallClockSec`),
  to accrue live across polls, and to persist server-side across a (simulated) reload.

Evidence dir: `reports/qa/goal-financial_free-iter-3-evidence/`
(`TC-12-app-loaded.png` = clean render; `TC-12-sessions-dropdown.png` = throttled-blank, kept for honesty).

**Live-pixel debt:** partially cleared — a real-pixel render of the workstation was obtained
(J-05 controls visible), but the specific token/USD/configs strip chips were not captured as pixels
due to the throttle + concurrent-QA contention; confirmed at the data-contract layer instead. Residual
item flagged for the auditor / a dedicated browser-qa pass on an uncontended foreground tab.

## Step 4b — UI Evolution Audit

1. **Did the UI evolve to reflect the new capability?** Yes — `AutoSessionStatusStrip` gained
   token / USD / configs counters (+ `fmtTokens`/`fmtUsd`), and `AutoRunBudget` TS type mirrors the
   backend `to_dict()`. Reviewed PASS; builds + lints clean.
2. **Can the user see/understand/control it?** See/understand: yes — spend + configs are now in the
   strip, read from the canonical block. Control: J-12 is API-triggered by design (no UI trigger this
   iteration — per spec OUT OF SCOPE); the UI **tracks** the run.
3. **Relying on old generic pages?** No — distinct configs render through the existing iteration cards
   via their own `params` (intended, no schema fork).
4. **Technically complete but under-exposed?** No new under-exposure introduced; the only gap is that
   live strip pixels weren't captured (throttle), not that the capability is hidden.

**Verdict:** UI-PASS-WITH-GAPS — the new capability is exposed in the UI (code + data contract fully
wired and reviewed); the only gap is interactive pixel confirmation of the strip, blocked by the
documented render throttle and verified via the UI's exact endpoint. (Not UI-FAIL: the backend
capability IS reflected in the UI surface and its data contract.)

---

## Blockers

None blocking. Two non-blocking notes carried to the auditor:

1. **Flaky test** `test_post_returns_before_loop_completes_and_get_stays_responsive` — gate/status
   timing race in the test scaffold (passes in isolation + on re-run; 194 passed). De-flake suggested;
   not a product regression.
2. **Live status-strip pixels** not captured due to the documented Chrome-MCP hidden-tab throttle +
   a concurrent QA holding the foreground tab. Data contract fully verified via the UI's poll
   endpoint; one clean real-pixel app render captured. A re-run on an uncontended foreground tab would
   close the residual live-pixel item.

Pre-existing (untouched, out of scope): `test_directions_cache::test_write_and_read_full_round_trip`.

---

## Anti-goal spot-checks (verified, not just claimed)

- **Hard budget never "one more"**: `configsDone` never exceeded `maxConfigs`; runs stopped at the
  first cap reached (configs / wall-clock), `stopReason="budget-exhausted"`. ✅
- **Bounded seed universe**: configs were `BTC/USDT` + `ETH/USDT` (seed), never an exchange-wide
  fan-out of the 26-symbol `/api/symbols` list. ✅
- **Best = robust WFE-gated**: a best is marked only when a config passes the WFE gate (722cdad7);
  WFE-failing candidates left unmarked (`best=None`). ✅
- **Same file store / no schema fork**: open-universe iterations appear in the same
  `iterationHistory` / `autoRun` shape the UI already renders. ✅
- **No secrets**: 0 matches across 2964 store files. ✅
- **Frozen contracts untouched**: real token/USD threaded via side channel (per handoff + review). ✅
- **Pinned J-07/J-09 unchanged**: pinned run keeps `maxConfigs=null` + rounds, terminal + WFE best. ✅

---

## Services

No servers were started by QA (the QA runner manages backend `:8691` + frontend `:3691`). QA only
created sessions via the live API; no cleanup of QA-managed services performed (as instructed).
