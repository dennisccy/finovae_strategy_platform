# QA Report — goal-auto-money-printer-iter-5

**Verdict:** PASS

**Phase:** goal-auto-money-printer-iter-5
**Date:** 2026-05-19
**Agent:** qa (MODE 2 — QA validation)
**Frontend Present:** yes (browser checks executed, not skipped)
**Slice:** J-15 — read-only global-history warm start + `history_scope` opt-out

---

## Summary

J-15 validated end-to-end. A second open-universe run with `history_scope:"global"`
(or default/omitted) **warm-starts from prior sessions**: a read-only file-store
miner reorders the bounded `_SEED_UNIVERSE` SCREEN enumeration by mined family
strength and emits exactly one operator-readable planner-decision citation in the
existing activity feed. `history_scope:"this-run"` opts out entirely (no citation,
fixed seed order). Prior-session artifacts are byte-identical before/after the mine
(read-only proven live + unit). Budget / robust-best / pinned / J-01–J-14 invariants
hold. No anti-goal violation. Backend suite **200 passed / 1 pre-existing tolerated
red**, zero new regressions. Review verdict was PASS_WITH_NOTES (one cosmetic
non-blocking stale comment + one defensive-code NOTE — neither blocks).

> **Test-environment note (does not affect verdict).** The QA runner backend uses the
> **durable** store `.data/backtests` (correctly NOT `/tmp` — honours the durable-store
> anti-goal) which is the production-sized, **non-isolated** store (~113 sessions incl.
> prior auto-sessions). The test plan's API/browser cases (TC-01/TC-02) assume an
> *isolated* 3-session store. Where a sub-assertion depends on store isolation
> (TC-01 "empty store ⇒ no citation"; TC-02 "first promoted family == run-#1 F1"),
> the deterministic isolated-store proof is the corresponding **passing unit test**
> (`test_no_prior_history_fallback_is_fixed_seed_order`,
> `test_global_warm_start_reorders_and_cites_prior`), and the live run validates the
> observable J-15 behaviour. All such cases independently verified — none masked.

---

## Step 1 — Required Artifacts

| Artifact | Status |
|---|---|
| `docs/handoffs/goal-auto-money-printer-iter-5-dev.md` | ✅ present (133 lines, template-conformant) |
| `reports/reviews/goal-auto-money-printer-iter-5-review.md` | ✅ **PASS_WITH_NOTES** (1 MINOR stale comment, 1 NOTE defensive code — non-blocking) |
| `runs/goal-auto-money-printer-iter-5/status.json` | ✅ present |
| `reports/qa/goal-auto-money-printer-iter-5-test-plan.md` | ✅ present (19 test cases) |
| 6 UI visibility artifacts | ✅ all present & populated (impl-summary 92, user-visible-changes 82, ui-surface-map 62, ui-test-plan 425, ui-test-results 168, what-to-click 99 lines) |

---

## Step 2 — Backend Tests (exact output)

Command: `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v`
Result: **`53 passed, 4 warnings in 8.23s`** (was 41 in iter-4 → +12 net new; 2 consciously updated; zero regressions)

Command: `cd apps/backend && .venv/bin/python -m pytest -q`
Result: **`1 failed, 200 passed, 4 warnings in 13.26s`**

```
=========================== short test summary info ============================
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip - ...
1 failed, 200 passed, 4 warnings in 13.26s
```

The single red is **only** `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
— pre-existing, out-of-scope, explicitly tolerated by the spec & plan (iter-4 baseline
188 passed / 1 failed → **+12 passing, zero new regressions**). `directions_cache.py`
untouched. No failure digest needed (the failing test is the documented tolerated red,
not a regression). Full log: `reports/qa/goal-auto-money-printer-iter-5-test.log`.

---

## Step 3 — Frontend Tests

No frontend file modified (`git diff HEAD --stat -- apps/backend` shows only
`auto_session.py` +231 / `test_auto_session.py` +482; no `apps/frontend/*` change).
Per the test plan TC-17, `npm run build` is **not required** when no frontend file is
touched — documented, not skipped. Verify-first held: the existing
`ActivityLogEntry.tsx` renders the citation verbatim with zero frontend changes
(confirmed live below).

---

## Step 3.5 — Functional Test Plan Results (19/19 PASS)

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---|---|---|---|---|---|---|
| TC-01 | Run #1 producer, terminal + promoted best | api | 200; terminal `budget-exhausted`; promoted best; F1 recorded | 200; `SID1=f1b3c401`; `complete`/`budget-exhausted`; best `1b4f10fb`; promoted BTC/USDT 4h + ETH/USDT 4h; spend $0.0107/14436 tok/2 cfg | **PASS** | Non-isolated store ⇒ run #1 (default) also resolved effective-`global`; the "empty store ⇒ no citation, fixed order" assertion is the passing unit `test_no_prior_history_fallback_is_fixed_seed_order`. Core (terminal + promoted best, evidence for #2) holds. |
| TC-02 | Run #2 `global` → citation + reorder | api | 200; exactly 1 planner-decision entry citing family+robust+count; SCREEN permutation F-first; persisted `historyScope=global`; effective `global`; no secrets | 200; `SID2=789de3fa`; **1** entry: `"Warm start (global history): prioritising ETH/USDT 4h — prior best robust 1.70 across 17 prior sessions"`; SCREEN 1 = ETH/USDT 4h (reorder applied, permutation of seed); `historyScope='global'`, `effectiveHistoryScope='global'`; 0 secrets | **PASS** | First **promoted** = BTC/USDT 4h (best screener Sharpe 0.34) not the warm-start family — correctly demonstrates *warm-start changes SCREEN order only, not selection* (robust-best invariant intact live). Deterministic "first promoted==F1" proven by unit `test_global_warm_start_reorders_and_cites_prior`. |
| TC-03 | Run #3 `this-run` opt-out | api | 200; terminal; **0** warm-start entries; SCREEN == fixed `_SEED_UNIVERSE`; `historyScope=this-run`, effective `this-run` | 200; `SID3=6e9e76bc`; `complete`/`budget-exhausted`; **0** warm-start entries; SCREEN 1=BTC/USDT 4h,2=ETH/USDT 4h,3=SOL/USDT 4h,4=BNB/USDT 1h (fixed seed, NOT reordered); `historyScope='this-run'`, `effectiveHistoryScope='this-run'` | **PASS** | Opt-out honoured despite abundant prior history present. |
| TC-04 | Default omitted → effective `global`, raw `null` | api | citation present + reorder; raw `historyScope` null; effective `global`; additive key only | `SID4=05be7bb1`; 1 citation; raw `historyScope=None`; `effectiveHistoryScope='global'`; reorder applied (SCREEN 1=ETH/USDT 4h) | **PASS** | Additive `autoRun.effectiveHistoryScope` key, no schema fork. |
| TC-05 | Garbage scope / corrupt dir / pinned | api | garbage→200 not 422/500, clean default, terminal; corrupt prior dir skipped; pinned no mining/citation | garbage `SID5=dec16560` → **200** (not 422/500), raw persists `'garbage-value'`, `effectiveHistoryScope='global'`, terminal; ~19 of 100+ prior dirs mined w/ incomplete dirs present (e.g. stuck `Auto: ema crossover`) → run completed, no hang/traceback; pinned `SIDP=b9481199` → 200, `effectiveHistoryScope=None`, **0** warm-start/SCREEN/PROMOTE entries, normal "Automated iteration 1/2" flow | **PASS** | Corrupt-dir-skip also proven by unit `test_corrupt_prior_session_dir_skipped_best_effort`. Pinned path byte-unchanged (J-07–J-11). |
| TC-06 | **J-15 PRIMARY browser** — citation visible on global, absent on this-run | browser | run#2 feed shows readable citation (family+robust+count), untruncated, in existing feed; run#3 no entry; screenshots saved | Run#2 active: visible `<span class="text-xs text-violet-600 font-medium">` = byte-exact `"Warm start (global history): prioritising ETH/USDT 4h — prior best robust 1.70 across 17 prior sessions"` at **top** of feed (✦ violet), SCREEN 1=ETH/USDT 4h; Run#3 active: **no** visible warm-start, feed starts `SCREEN 1 done — BTC/USDT 4h` (fixed order). Screenshots `TC-06-run2-warmstart-citation.png`, `TC-06-run3-no-citation.png` | **PASS** | Renders in the **existing** activity feed, no new component/page — UI-indistinguishable from a manual run. Independently navigated & verified (not the carried headline). |
| TC-07 | Regression browser — J-02/J-08/J-12/J-13/J-14 | browser | prior history browse intact; live terminal w/o reload; ≥2 distinct configs; durable spend; SCREEN→PROMOTE staging | **J-02**: run#1 6-iteration history list + full iteration detail (strategy/equity curve/walk-forward/ratings/metrics) reload intact post-mining (`TC-07-run1-iterations-list.png`, `TC-07-run1-iteration-detail.png`) + run#1 38 files byte-identical pre/post mine; **J-08**: all runs observed running→complete via poll, UI banner "Automated run complete · budget reached"; **J-12**: 4 distinct SCREEN configs; **J-13**: banner `14,146 tok · $0.0102 · 2 cfg` + budget-reached, no NaN; **J-14**: SCREEN 1-4 → PROMOTE staged feed | **PASS** | No still-passing journey regressed by the ordering-only warm-start. |
| TC-08 | Warm-start reorder unit (F1 first, permutation, first promoted==F1) | artifact | passes, no skip/xfail | `test_global_warm_start_reorders_and_cites_prior` + `test_reorder_configs_is_stable_bounded_permutation` + `test_mine_history_read_only_filters_and_excludes_current` **PASSED** | **PASS** | Isolated-store deterministic proof of the F1-first invariant. |
| TC-09 | Opt-out unit (`this-run` byte-identical, no citation) | artifact | passes | `test_this_run_opt_out_no_mining_no_citation_fixed_order` **PASSED** | **PASS** | |
| TC-10 | Default→global unit (consciously updated, not loosened) | artifact | persistence retained + new behavioural assertions; no skip/xfail; stale comment corrected | `test_history_scope_defaults_to_none_when_omitted` + `test_default_omitted_history_scope_resolves_to_global` **PASSED**; diff retains `assert historyScope is None` + adds effective-global/no-citation assertions; **no skip/xfail added**; stale "J-15/OUT" comment corrected | **PASS** | Strengthened, not relaxed. |
| TC-11 | Read-only proof unit (prior files byte-identical) | artifact | passes | `test_history_mining_is_read_only_no_prior_artifact_mutation` **PASSED** + live: run#1 38 files sha256 byte-identical before/after run#2 mine (file-set + mtime unchanged) | **PASS** | iter-0 lesson / J-02 not regressed — proven twice (unit + live). |
| TC-12 | Once-per-run / off-thread / no LLM planner | artifact | call-count==1; `asyncio.to_thread`; no LLM call | `test_warm_start_mined_exactly_once_per_run` **PASSED**; source: `_warm_start_configs` → `await asyncio.to_thread(_mine_history, …)` once at run start; **no** chat/completions/messages.create added in diff | **PASS** | Structural once-per-run satisfies "not re-sent uncached every round"; deterministic surrogate, no LLM (spec core design). |
| TC-13 | No-history fallback + existing J-12/J-13/J-14/pinned green | artifact | empty-store == fixed seed; existing tests pass unmodified | `test_no_prior_history_fallback_is_fixed_seed_order`, `test_open_universe_runs_multiple_distinct_configs`, `test_open_universe_best_is_robust_not_raw_return`, `test_max_configs_cap_stops_open_universe_no_post_cap_config`, `test_pinned_path_unchanged_by_open_universe_addition`, `test_hard_token_budget_exhausted_real_usage_and_durable_spend` **all PASSED** | **PASS** | J-12/J-13/J-14 byte-preserved. |
| TC-14 | Persistence test not loosened | artifact | original asserts retained + new `this-run` behaviour; no skip/xfail; comment corrected | `test_open_universe_objective_and_history_scope_persisted` **PASSED**; retains `objective`/`historyScope=='this-run'` asserts + adds "no planner-decision entry / fixed order" asserts; no skip/xfail | **PASS** | Equivalently/stricter, not relaxed. |
| TC-15 | Robust-best invariant under warm-start | artifact | warm-start family that promotes worse is NOT best | `test_warm_start_changes_order_not_robust_best_selection` **PASSED**; live corroboration TC-02 (warm-start ETH/USDT 4h NOT promoted-best; BTC/USDT 4h is) | **PASS** | `select_best`/`robust_score` untouched. |
| TC-16 | Error cases unit (garbage/corrupt) | artifact | garbage→clean default; corrupt dir skipped; both terminal | `test_garbage_history_scope_clean_default_no_crash` + `test_corrupt_prior_session_dir_skipped_best_effort` **PASSED** + live TC-05 | **PASS** | Best-effort, mirrors SCREEN/PROMOTE `except` discipline. |
| TC-17 | Backend suite green + frontend build | artifact | ≥188 passed, exactly 1 tolerated red; frontend build if touched | 200 passed / 1 failed (only the tolerated `test_directions_cache`); **no frontend file touched** → build not required (documented) | **PASS** | +12 passing, zero new regressions. |
| TC-18 | Anti-goal source guards | artifact | frozen-files diff empty; no new infra/LLM; additive key; off-thread; 0 secrets | `git diff HEAD -- contracts.py sandbox.py pipeline.py backtest/` = **0 lines**; only `auto_session.py`+`test_auto_session.py` changed; no celery/redis/db/broker/vector/LLM import; additive `effectiveHistoryScope` via `_update_autorun` (no schema fork); `asyncio.to_thread` mine; **0** secret matches across warm-started artifacts incl. citation | **PASS** | All load-bearing anti-goals proven. |
| TC-19 | Closure artifacts present & non-vague | artifact | dev handoff + 6 UI artifacts populated | All 7 present & non-empty (handoff 133 + 6 UI artifacts 62–425 lines) | **PASS** | |

**19 / 19 functional test cases passed.** (TC-01/TC-02 carry a documented
non-isolated-store nuance whose deterministic form is covered by the corresponding
passing isolated-store unit tests — no assertion masked, no failure.)

---

## Step 4 — Chrome MCP Browser Checks (executed, not skipped)

Frontend reachable at `http://localhost:3691` (HTTP 200). All three J-15 runs and
the producer/regression sessions exercised through the real React frontend.

- **Run #2 (`global`) — planner-decision citation rendered:** the visible/active
  session's activity feed shows, as the **first** entry, a distinctly-styled violet
  `<span class="text-xs text-violet-600 font-medium">` with the **untruncated**
  byte-exact text *"Warm start (global history): prioritising ETH/USDT 4h — prior
  best robust 1.70 across 17 prior sessions"*, above the iteration entries — exactly
  as iter-2/iter-4 `auto-run` markers render. SCREEN 1 = ETH/USDT 4h (reorder
  visibly applied). Screenshot: `goal-auto-money-printer-iter-5-evidence/TC-06-run2-warmstart-citation.png`
  (+ `-zoom`, `_probe-after-select-run2.png`).
- **Run #3 (`this-run`) — citation correctly absent:** active feed has **no**
  visible warm-start span; first entry is `SCREEN 1 done — BTC/USDT 4h` (fixed
  `_SEED_UNIVERSE` order, not warm-start's ETH/USDT 4h). Screenshot:
  `…/TC-06-run3-no-citation.png`.
- **Regression (TC-07):** run #1 prior-run history fully browsable post-mining —
  6-iteration list + full iteration detail (strategy script, equity curve,
  walk-forward, ratings, metrics) reload intact (`TC-07-run1-iterations-list.png`,
  `TC-07-run1-iteration-detail.png`); live terminal banner, ≥2 distinct configs,
  durable numeric spend, SCREEN→PROMOTE staging all render.

Independent verification: I navigated and switched sessions myself (tab-recency
selection — the app's own default-session mechanism) and extracted the rendered DOM;
the browser-qa `ui-test-results.md` "PASS" headline is **corroborated**, not trusted
blindly (iter-1 reconciled-headline caution satisfied — cross-checked against live
API, live DOM, source diff, and the unit suite).

> Operational note: the QA-runner frontend mounts **all ~113** non-isolated-store
> SessionContainers simultaneously (App.tsx maps every session); under that load
> Chrome CDP intermittently timed out on heavy `eval`/`screenshot`. Mitigated by
> reloading (resets the React tree) with the target run as most-recent tab so the
> app auto-selects it. This is an environment/store-size artefact (test plan assumes
> an isolated 3-session store), **not** an iter-5 defect — every J-15 assertion was
> still captured with screenshots.

---

## Step 4b — UI Evolution Audit

1. **Did the UI evolve to reflect the new capability?** Yes — the cross-run
   warm-start decision surfaces as a first-class, distinctly-styled planner-decision
   entry at the top of the existing session activity feed (no new code needed; the
   existing renderer carries it verbatim, untruncated).
2. **Can the user see, understand, and control it?** Yes — the citation states the
   prioritised family, the concrete prior robust score, and how many prior sessions
   informed it, in plain operator language; the user controls it via
   `history_scope: "global" | "this-run"` (opt-out visibly removes the entry and
   restores fixed seed order).
3. **Still relying on old generic pages?** No — it renders in the purpose-built
   activity feed alongside SCREEN/PROMOTE markers; a headless warm-started run is
   UI-indistinguishable from a manual one (intended).
4. **Technically complete but underexposed?** No — the capability is visible,
   readable, and demonstrably opt-out-able in the UI.

**Verdict:** UI-PASS

---

## Step 5 — Blockers

None. Review verdict PASS_WITH_NOTES carries only non-blocking items:

- **MINOR (reviewer, cosmetic — non-blocking):** `apps/backend/backend/auto_session.py:~116`
  retains a stale comment ("the history-surrogate/bandit + LLM planner … is J-15 /
  OUT OF SCOPE") — now factually inaccurate (J-15 is implemented here; warm-start
  reorders within the bounded seed). Two sibling stale comments were corrected; this
  third was missed. **Zero runtime/behavioural effect**, no test impact; the spec's
  "correct stale J-15/OUT comments" directive is satisfied for the docstring + the
  accept-&-persist inline comment but not this enumerator comment. Recommend a
  one-line follow-up tidy; does not block QA per `.claude/core.md` (PASS_WITH_NOTES
  with non-blocking notes is shippable).
- **NOTE (reviewer):** `_strongest_family` third tie-break is unreachable defensive
  code — harmless, correct, documentation-only.

No functional test failures. No anti-goal violation. No new regression.

---

## Step 5b — Servers

The backend (uvicorn :8691, pid 68002) and frontend (next dev :3691, pid 68116/68138)
are **runner-managed** per the task instructions. QA started **no** servers — nothing
to kill (terminating runner-managed processes would break the pipeline). Both healthy
at report time (frontend 200, backend `/api/health` 200).

---

## Definition of Done — Cross-check

- ✅ Target journey **J-15** passes via browser-qa (citation visible on `global`,
  absent on `this-run`, reorder applied, screenshots captured).
- ✅ Required-still-passing **J-01–J-14** green (J-12/J-13/J-14 open-universe tests
  pass unchanged; pinned J-07–J-11 byte-unchanged; J-02 history browse unaffected —
  live + hash + unit).
- ✅ No anti-goal violation (read-only proven by before/after content-hash live +
  unit; opt-out honoured; bounded-seed permutation only; once-per-run/off-thread;
  budget/robust-best/pinned intact; 0 secrets; no schema fork; no new infra; no LLM
  planner).
- ✅ Unit/integration pass; full backend suite **200 passed / 1 pre-existing tolerated
  red**, zero new regressions.
- ✅ Dev handoff + all 6 UI visibility artifacts present and populated.

**Overall QA Verdict: PASS**
