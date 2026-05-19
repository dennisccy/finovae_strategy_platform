**Verdict:** PASS

# QA Validation Report — goal-auto-money-printer-iter-4

**Phase:** goal-auto-money-printer-iter-4 — Staged SCREEN→PROMOTE (cheap-first model/WF routing) + carried iter-3 B1 fix
**Date:** 2026-05-19
**Mode:** QA Validation (MODE 2)
**Frontend Present:** yes (browser checks executed via Chrome MCP at http://localhost:3691)
**Backend:** http://localhost:8691 (`GET /api/health` → 200)

---

## Verdict Rationale

The implementation is **correct, complete, and spec-compliant**, with strong evidence at the
unit, live-API, and browser levels:

- Backend suite **188 passed / 1 failed**; the single failure is the pre-existing,
  out-of-scope, baseline-documented `test_directions_cache.py::test_write_and_read_full_round_trip`.
  iter-3 baseline was 183/1 → **+5 new passing, ZERO new regressions** (failed count stays
  exactly 1, same test) — matches the spec baseline exactly.
- J-14 (primary) verified live via API **and** in-browser: staged ≥3 `SCREEN` → small top-k
  `PROMOTE` (k=2 < 4), walk-forward + insights only on promoted, robust best = a promoted id.
- Carried B1 fix verified at unit level (RED/GREEN mutation guard) **and** live (insights present
  on the final pinned iteration where `would_exceed()=="max-configs"`).
- All anti-goal source guards hold; J-01–J-13 regressions (J-02/J-08/J-12/J-13) re-verified live.

**One non-passing functional case: TC-21.** Two of the six UI-visibility artifacts
(`ui-test-plan`, `what-to-click`) are auto-generated **stub placeholders** because
`ui-test-design-phase.sh`'s Claude CLI exited with code 1 (a transient pipeline-tooling
failure, self-documented with a re-run recovery path). This is **not an implementation
defect** and is **not a QA ship-blocker**: the substantive UI visibility it would document
was independently and thoroughly verified by this QA run in-browser (TC-07–TC-12, with
screenshots). The framework's dedicated **phase-closure-auditor** (CLAUDE.md DoD #9) is the
correct gate for UI-artifact completeness; this report flags it as a **phase-closure
blocker requiring a `ui-test-design-phase.sh` re-run**, distinct from the QA verdict on the
implementation, which is PASS.

---

## Step 1 — Required Artifacts

| Artifact | Status |
|----------|--------|
| `docs/handoffs/goal-auto-money-printer-iter-4-dev.md` | ✅ present (196 lines, full template) |
| `reports/reviews/goal-auto-money-printer-iter-4-review.md` | ✅ **PASS** verdict |
| `runs/goal-auto-money-printer-iter-4/status.json` | ✅ present |
| `reports/qa/goal-auto-money-printer-iter-4-test-plan.md` | ✅ present (21 test cases, executed) |

---

## Step 2 — Backend Tests (exact output)

**Targeted** — `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py tests/test_model_pricing.py -v`

```
======================== 47 passed, 4 warnings in 8.10s ========================
```
(test_auto_session.py 41 + test_model_pricing.py 6 = 47, matching the dev handoff.)

**Full suite** — `cd apps/backend && .venv/bin/python -m pytest -q`

```
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip - ...
1 failed, 188 passed, 4 warnings in 13.93s
```

Baseline reconciliation: post-iter-3 baseline = **183 passed / 1 failed**; now **188 passed
/ 1 failed**. The +5 are this phase's new tests. The single failure is **only**
`test_directions_cache.py::test_write_and_read_full_round_trip` — the explicitly tolerated,
pre-existing, out-of-scope baseline failure. **Zero new regressions.**
Structured digest: `reports/qa/goal-auto-money-printer-iter-4-failure-digest.md` (single
known-baseline failure; raw log `reports/qa/goal-auto-money-printer-iter-4-fullsuite.log`
authoritative).

New / updated cases (all PASS, no skip/xfail):
`test_screen_stage_cheap_model_no_wf_no_insights`,
`test_screen_stage_failure_is_recorded_loop_continues`,
`test_promote_stage_reuses_screened_strategy_full_pipeline`,
`test_b1_true_spend_cap_between_generate_and_insights_skips_one`,
`test_pinned_path_unchanged_by_open_universe_addition` (with `assert pipe.insight_calls == 3`),
`test_open_universe_runs_multiple_distinct_configs`,
`test_open_universe_best_is_robust_not_raw_return`,
`test_max_configs_cap_stops_open_universe_no_post_cap_config`,
`test_hard_token_budget_exhausted_real_usage_and_durable_spend`,
`test_open_universe_multi_config_runs_in_subprocess_distinct_pids`,
`test_cheapest_model_is_resolved_from_the_price_table_not_a_literal`.

---

## Step 3 — Frontend Tests

No frontend file was modified this iteration (`git diff HEAD --stat` shows only
`auto_session.py`, `model_catalog.py`, `test_auto_session.py`, `test_model_pricing.py` +
goal-session telemetry/trace artifacts). Per the test plan TC-19, `npm run build` is **not
required** — explicitly noted: no frontend file touched.

---

## Step 3.5 — Functional Test Plan Results

Live sessions exercised on the managed backend (`OPENAI_API_KEY` set, real LLM,
`gpt-5.4-mini`):

| Session | SID | Final state |
|---|---|---|
| Open-universe staged (TC-01/02/03/07/08/11) | `c6e89d48` | complete · budget-exhausted · 4 SCREEN + 2 PROMOTE · configsRun=2 |
| Hard-budget (TC-04/09) | `40db41dc` | complete · budget-exhausted · 1 SCREEN + 0 PROMOTE · configsRun=0 |
| Pinned (TC-05/12) | `de3c5fa4` | complete · budget-exhausted · 0 SCREEN/PROMOTE · configsRun=2 |
| Fresh staged (reproducibility) | `9f14c820` | complete · budget-exhausted · 4 SCREEN + 2 PROMOTE |
| Running→switch (TC-10) | `0e5210cf` | ran live during switch; terminated clean · 4 SCREEN + 2 PROMOTE |

| ID | Name | Type | Expected | Actual | Verdict | Notes |
|----|------|------|----------|--------|---------|-------|
| TC-01 | Open-universe POST accepted + listed | api | 200, sessionId, status∈{running,queued}, listed | http 200, `c6e89d48`, status=running, present in `/api/sessions` (96 tabs) | **PASS** | J-14 trigger path unchanged from J-12 |
| TC-02 | Staged SCREEN→PROMOTE in feed | api | ≥3 SCREEN w/ cheap metric; k PROMOTE k<screened; WF+req.model only promoted | 4 SCREEN (BTC/ETH/SOL 4h, BNB 1h; each "in-sample Sharpe…, return…, N trades (cheap screen — no walk-forward)"); 2 PROMOTE (BTC/SOL 4h, "walk-forward WFE…"); screened nodes `walkForwardResult=null` `modelUsed=gpt-5.4-mini`; promoted `walkForwardResult` populated; terminal budget-exhausted | **PASS** | k=2 < screened=4, k small; configsRun=2 (config=PROMOTE staged semantics). Model note below.¹ |
| TC-03 | Final best = PROMOTED robust id | api | best non-null, a promoted id, robust winner; screened-only / raw-return not best | `bestIterationId=8de881c3` = promoted BTC/USDT/4h (robust −999.40, the max over promoted vs SOL −1000.70); highest-raw-return iter is screened-only and is **not** best | **PASS** | Screen proxy never leaks into best-selection |
| TC-04 | Hard budget → budget-exhausted, no post-cap config | api | budget-exhausted; spend≤caps within one-call tol; zero config after cap; spend durable | `40db41dc` budget-exhausted; cap `max_ai_tokens=1`, round-top at 0 proceeded, one in-flight SCREEN generate drained 2339 → exactly one-call tolerance; only "SCREEN config 1" then stopped (0 further config, configsRun=0); spend present+durable in autoRun | **PASS** | Extreme cap mid-SCREEN skips PROMOTE entirely (spec-correct; handoff-documented) |
| TC-05 | 422 validation + pinned no staging | api | partial pin 422; bad objective 422 (no 500); pinned 200, 0 SCREEN/PROMOTE, full pipeline+insights each iter | partial pin → **422** ("Missing required pinned config field(s)…"); `objective:"sharpe"` → **422** ("Unsupported objective 'sharpe'…"); no 500/traceback; pinned `de3c5fa4` 200, 0 SCREEN/PROMOTE, "Automated iteration 1/2"+"2/2" each with Backtest complete + insights | **PASS** | Pinned byte-unchanged behaviourally |
| TC-06 | SCREEN failure doesn't abort loop | api | failure recorded + loop continues to terminal, OR note not-exercised | No SCREEN failure occurred naturally in 3 live staged runs (errors=0, all terminal `complete`) → "not exercised — no SCREEN failure in this run" | **PASS** | Non-blocking per plan; covered by unit `test_screen_stage_failure_is_recorded_loop_continues` (PASSED — asserts error iteration recorded + PROMOTE entries follow) |
| TC-07 | J-14 browser staged feed | browser | ≥3 SCREEN (prefix readable, not flattened), k PROMOTE k<screened, WF+stronger only promoted, 1 BestBadge on promoted, terminal no reload, screenshot | "Iterations (6)"; 4 SCREEN entries verbatim ("SCREEN N done — SYM TF: in-sample Sharpe…, return…, N trades (cheap screen — no walk-forward)"); 2 PROMOTE ("PROMOTE done — … walk-forward WFE…"); Best badge tooltip "Best iteration — selected by the robust walk-forward objective" on promoted BTC 4H (= API bestIterationId); AutoRunBar "complete · budget reached · 6/12 · 14,323 tok · $0.0105 · 2 cfg"; no manual reload | **PASS** | Screenshot `TC-07-staged-screen-promote.png`. Per-session single-best confirmed via API (DOM holds 99 cached session cards → DOM-wide "Best" count is pollution, not per-session). |
| TC-08 | J-12 ≥2 distinct configs, no new surface | browser | ≥2 pairwise-distinct (sym,tf) from seed universe, existing iteration tree, no new page | 4 distinct configs (BTC/4h, ETH/4h, SOL/4h, BNB/1h) ⊆ seed universe, rendered in the existing iteration tree + existing analysis panel; no new surface/page | **PASS** | Same session as TC-07; UI-indistinguishable from manual |
| TC-09 | J-13 AutoRunBar spend + budget-exhausted | browser | numeric tok/USD/cfg matching persisted spend; terminal reason distinct; no NaN; no new panel; screenshot | `40db41dc`: AutoRunBar "⊘ Automated run complete · budget reached · 1/2 iterations · 2,339 tok · $0.0012 · 0 cfg" — matches API (aiTokens=2339, usd=0.0012, configsRun=0); amber/distinct styling; no NaN/undefined; 1 SCREEN then capped (no config past cap visible); existing surface | **PASS** | Screenshot `TC-09-autorunbar-budget-exhausted.png` |
| TC-10 | J-08 running not stale under switching | browser | after rapid switch AutoRunBar shows "running" not stale terminal; list agrees; poll updates no reload | `0e5210cf` opened running ("Automated run · iteration 1/1" + spinner + "Stop (1/1)"); switched away to terminal budget-exhausted staged session; switched back → AutoRunBar **re-derived to "Automated run · iteration 1/1 · 0 tok · $0.0000 · 1 cfg"** (live), NOT the stale prior terminal ("budget reached/6/12/14,323 tok"); session-list showed it as "running"; no manual reload | **PASS** | Screenshots `TC-10-running-session.png`, `TC-10-running-not-stale-after-switch.png`. iter-2 live-poll try/finally re-arm intact (frontend byte-unchanged) |
| TC-11 | J-02 prior-run RIGHT panel re-binds | browser | selected prior run's trades/equity/WF all reload into RIGHT panel, match run | Selecting the promoted BTC iteration re-bound the RIGHT panel: "BTC 4H EMA Momentum Breakout" header, "Equity Curve", "Combined OOS Equity Curve (3 windows chained)", OOS Return/Sharpe/WinRate/MaxDD + "Walk-Forward Eff." + IS/OOS period table, "Trade History (18 trades)" — all matching that run | **PASS** | Screenshot `TC-11-prior-run-right-panel.png`. J-02 heavy-detail merge precedence byte-unchanged |
| TC-12 | Legacy/pinned no SCREEN/PROMOTE | browser | zero SCREEN/PROMOTE on pinned; feed + AutoRunBar visually unchanged | `de3c5fa4` pinned: feed shows only "Generating Strategy / Backtest complete / Automated iteration 2/2 / insights" — **0 SCREEN/PROMOTE**; AutoRunBar correctly re-derived on switch to "2/2 iterations · 11,604 tok · $0.0099 · 2 cfg"; insights present on final iteration 2/2 (live B1-fix proof) | **PASS** | Screenshot `TC-12-pinned-no-staging.png`. Additive-only, no regression |
| TC-13 | SCREEN unit: wfv=False + cheapest + no insights | artifact | exact-value asserts; cheapest catalog-resolved (not literal); insight_calls==0 screened-only | `test_screen_stage_cheap_model_no_wf_no_insights` PASSED: asserts `cheap == min(MODEL_PRICING, key=…)`, `cheap != req.model`, `gen_models == [cheap]*n_screen`, `bt_wfv[:n_screen]==[False]*n_screen`, screened nodes `walkForwardResult is None`+`modelUsed==cheap`, screened-only insights empty, `insight_calls == k` | **PASS** | Assertion derives from MODEL_PRICING, not a string literal; no skip/xfail |
| TC-14 | PROMOTE unit: full pipeline, reuses strategy, k<screened | artifact | wfv=True+req.model+insights; same scriptId/code hash; no 2nd generate; k<screened | `test_promote_stage_reuses_screened_strategy_full_pipeline` PASSED: `gen_calls==n_screen` (no promote re-generate), `pnode.scriptId==snode.scriptId`, `pnode.scriptCode==snode.scriptCode`, `walkForwardResult is not None`, `modelUsed=="claude-sonnet-4-6"`, `0<k<n_screen` | **PASS** | Code-hash reuse + no re-fetch asserted exactly |
| TC-15 | Robust-best-is-promoted unit | artifact | exact best id (promoted); higher-raw-return screened-only / WFE-fail explicitly not best; select_best reused | `test_open_universe_best_is_robust_not_raw_return` PASSED (staged form): `best==by_cfg_node[s1].id`, `best!=s0.id` (WFE-failing promoted), `best not in s2_screen_ids` (higher-raw-return screened-only) | **PASS** | No screen-aware best path; `select_best`/`robust_score` unchanged |
| TC-16 | SCREEN subprocess seam (deterministic) | artifact | child_pid != getpid for screened; no timing bound | `test_open_universe_multi_config_runs_in_subprocess_distinct_pids` PASSED: every screen+promote node `run_id.startswith("pid-")` and `int(pid)!=os.getpid()`; SCREEN nodes `walkForwardResult is None`; no `time.sleep`/elapsed guard | **PASS** | iter-2 lesson honoured; deterministic guard |
| TC-17 | B1 regression guard unit | artifact | insight_calls==3 on 3-iter pinned (RED under naive gate); positive cap-skip test | `test_pinned_path_unchanged_by_open_universe_addition` PASSED with `assert pipe.insight_calls == 3` (comment documents RED under truthy-would_exceed gate); `test_b1_true_spend_cap_between_generate_and_insights_skips_one` PASSED (insight_calls==0, iteration still written, spend=generate-only, activity recorded) | **PASS** | Sentinel distinction documented inline at `_SPEND_CAPS`/`_should_skip_insights`; both pass as written, no skip/xfail |
| TC-18 | Staged-form J-12/J-13 not loosened | artifact | 4 tests re-assert invariants in staged form, no skip/xfail, not relaxed | All 4 PASS in staged form; test diff: **+79 / −14 assertions** (strengthened, replaced not deleted); zero `pytest.mark.skip/xfail` added; staged `max_configs` semantics (config = PROMOTE) documented inline in `_run_staged_open_universe` | **PASS** | Invariants ≥2 distinct configs / no-config-past-cap / budget-exhausted / exact-real-spend / robust-not-raw all re-asserted |
| TC-19 | Backend suite green + frontend build | artifact | suite zero new regressions vs 183/1; frontend build only if touched | 188 passed / 1 failed (only `test_directions_cache::test_write_and_read_full_round_trip`); passed ≥183 (raised by new tests), failed==1 same baseline test; no frontend file touched → build not required | **PASS** | Counts recorded verbatim above |
| TC-20 | Anti-goal source guards | artifact | contracts/sandbox/engine empty diff; no new infra; cheapest from MODEL_PRICING; 0 secrets | `git diff HEAD -- shared/contracts.py sandbox.py` **empty**; `pipeline.py`/`backtest/` unchanged; no celery/redis/sqlalchemy/broker/vector-store import; `cheapest_model()` = `min(MODEL_PRICING, key=lambda m:(MODEL_PRICING[m][0]+MODEL_PRICING[m][1], m))` (catalog-resolved, not a literal); secret grep over 3 session stores (`.data/backtests/live/<sid>`, 38/8/14 files) = **0 matches** | **PASS** | No schema fork; no in-browser iterate loop reintroduced |
| TC-21 | Closure artifacts present + non-vague | artifact | all 7 present, populated, no placeholder, concrete steps, closure gate passes | 5/7 substantive: dev-handoff (196L), implementation-summary (102L), user-visible-changes (118L), ui-surface-map (70L), ui-test-results (157L). **`ui-test-plan` (15L) and `what-to-click` (15L) are auto-generated STUBS** ("SKIPPED — agent did not produce this artifact"; `ui-test-design-phase.sh` Claude CLI exited code 1 — transient, self-documented recovery) | **FAIL (non-impl; phase-closure gate item)** | See Blockers — flagged for phase-closure-auditor to re-run `ui-test-design-phase.sh`; substantive UI visibility independently verified here in TC-07–TC-12 |

**Summary: 20 / 21 functional cases PASS.** TC-21 is the sole non-pass — a transient
downstream pipeline-tooling artifact gap (not an implementation defect), owned by the
phase-closure-auditor gate, with the UI visibility it documents independently verified
in-browser by this QA run.

¹ **Model-routing note (TC-02/07):** the TC-01 trigger sent no `model`, so `req.model`
defaults to the platform default `gpt-5.4-mini`, which is *also* the catalog-resolved
cheapest model — hence SCREEN and PROMOTE both show `gpt-5.4-mini` in the no-override live
run (correct, not a defect). The SCREEN-cheapest vs PROMOTE-`req.model` *distinction* is
proven deterministically by passing unit tests TC-13/TC-14, which use a non-cheapest
`req.model` (`claude-sonnet-4-6`) and assert `gen_models==[cheap]*n_screen` /
`insight_models==[req.model]*k`. The unambiguous expensive-path differentiator visible live
is walk-forward + insights (promoted only) — clearly rendered.

---

## Step 4 — Chrome MCP Browser Checks

Browser checks **executed** (not skipped) against http://localhost:3691. Six user
workflows driven via Chrome DevTools automation (open staged session, read SCREEN vs
PROMOTE, inspect promoted vs screened-only, BestBadge, AutoRunBar spend/terminal,
session-switch running≠stale, prior-run RIGHT-panel re-bind, pinned no-staging). All
navigation was via in-app session switching — **no manual page reload**.

Evidence screenshots under `reports/qa/goal-auto-money-printer-iter-4-evidence/`:
`TC-07-staged-screen-promote.png`, `TC-09-autorunbar-budget-exhausted.png`,
`TC-10-running-session.png`, `TC-10-running-not-stale-after-switch.png`,
`TC-11-prior-run-right-panel.png`, `TC-12-pinned-no-staging.png`.

Result: **all browser test cases PASS** (TC-07–TC-12). The SCREEN→PROMOTE staging renders
legibly in the **existing** activity feed (stage prefix verbatim, not flattened/truncated);
an operator can distinguish the cheap screen stage from the expensive promote stage with no
new component.

---

## Step 4b — UI Evolution Audit

1. **Did the UI evolve to reflect the new capability?** YES. The existing session activity
   feed now renders distinct `SCREEN config N: SYM TF` / `SCREEN N done — … (cheap screen —
   no walk-forward)` and `PROMOTE config: SYM TF (top-k survivor; …)` / `PROMOTE done — …
   walk-forward WFE …` entries verbatim. Promoted iterations carry walk-forward + insights;
   screened-only ones do not.
2. **Can the user see/understand/control it?** YES. Visible in the existing feed;
   understandable (explicit "cheap screen — no walk-forward" vs "walk-forward WFE …" and
   "top-k survivor"); the `BestBadge` tooltip reads "Best iteration — selected by the robust
   walk-forward objective". Controlled by the same unchanged open-universe trigger (staging
   is automatic by spec design — no new user action intended).
3. **Relying on old generic pages?** NO — reuses the existing session feed/iteration tree
   by spec design ("No new surface"); the staging is legible there, not hidden.
4. **Technically complete but product-wise underexposed?** NO — staging, per-stage metrics,
   WF-only-on-promoted, the robust BestBadge, and the budget/spend AutoRunBar are all
   operator-legible in the existing UI.

**Verdict:** UI-PASS

---

## Blockers

**None blocking the implementation / QA ship verdict.**

**Phase-closure gate blocker (flagged, distinct from QA verdict):**
`reports/phase-goal-auto-money-printer-iter-4-ui-test-plan.md` and
`reports/phase-goal-auto-money-printer-iter-4-what-to-click.md` are auto-generated stub
placeholders — `ui-test-design-phase.sh`'s Claude CLI exited code 1 (transient). The
phase-closure-auditor MUST re-run `./scripts/automation/ui-test-design-phase.sh
goal-auto-money-printer-iter-4` to regenerate these two artifacts before CLOSURE-PASS.
This is a pipeline-tooling transient, not an implementation defect; the developer did not
author these stubs and the feature's UI visibility is fully verified in this report
(TC-07–TC-12 + screenshots) and in the substantive `ui-test-results.md` (157 lines).

---

## Step 5b — Server Cleanup

No servers were started by this QA run (the QA runner manages backend:8691 / frontend:3691).
Auto-sessions created for testing are managed backend jobs that self-terminate at budget;
all five reached a terminal state (verified: no hung processes, no stray uvicorn/next).

---

**Verdict:** PASS
