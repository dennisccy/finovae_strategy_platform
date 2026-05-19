# goal-auto-money-printer-iter-3 Audit Report

**Date:** 2026-05-19
**Auditor:** Hard audit pass — skeptical, evidence-based

---

## 1. Executive Verdict

**Verdict:** PASS_WITH_GAPS

The indivisible Optimizer-Foundation slice — **J-12** (open-universe bounded-seed
search from only an objective + budget) and **J-13** (immutable hard
AI-token/USD/max-configs/wall-clock cost tracker fed by real captured SDK usage,
budget-exhausted terminal, durable + visible spend) — is genuinely implemented,
not merely summarized. I traced the relaxed 422 gate, the deterministic bounded
enumerator, the frozen `CostTracker`, the real-usage capture chain, and the
durable-spend writes through the actual source, re-ran the full backend suite
(**183 passed / 1 failed** — only the pre-existing out-of-scope
`test_directions_cache::test_write_and_read_full_round_trip`), the iter-3
targeted suites (**59 passed**), and the frontend build (**EXIT 0**), and
confirmed every anti-goal at source-diff level. One non-blocking GAP remains
(bounded one-config LLM overshoot when `generate` alone crosses a spend cap —
B1) and one IMPORTANT documentation inaccuracy in the dev handoff was corrected
during this audit (B2). The system is materially stronger and shippable.

---

## 2. Findings

### Backend Findings

**B1 — GAP (documented, not fixed): no mid-round spend-cap recheck between
`generate` and `insights`.**
`_run_auto_session_impl` (`apps/backend/backend/auto_session.py:801-845`) drains
`generate`'s real usage into the tracker, then unconditionally runs the
`insights` LLM call before the next round-top `would_exceed()` check
(`auto_session.py:723-727`). If `generate` *alone* crosses a token/USD cap, the
already-counted terminal config still issues its `insights` call — worst-case
overshoot is one config's remaining LLM call(s), marginally beyond a strict
"single in-flight LLM call" reading of the spec's "within one-call tolerance".

This is **non-blocking**: the load-bearing anti-goal ("MUST NOT loop unbounded
or take 'one more round' past the cap") is satisfied — the round-top
`would_exceed()` check (`auto_session.py:723`) guarantees **no new
config/round** starts once any cap is reached; the overshoot is *bounded* (one
config's residual call, never unbounded); spend is **honestly recorded** (real
captured usage including the overshoot — verified, not pass-by-construction);
and every *measurable* J-13 DoD criterion holds (budget-exhausted terminal,
zero post-cap config/iteration, durable + visible spend, spend ≤ cap + one
config). `test_hard_token_budget_exhausted_real_usage_and_durable_spend`
(`tests/test_auto_session.py:1066-1110`) constructs the favourable case
(`generate` 100 tok < 150 cap; `insights` is the single crossing call) and
asserts the exact summed real counts — correct for that scenario but it does
not exercise the generate-alone-crosses case.

**Not fixed during audit — deliberately.** The reviewer's suggested one-liner
(skip `insights` whenever `would_exceed()` is truthy post-generate) is **unsafe
as-is**: on the *pinned* path `_build_cost_tracker` sets the configs cap ==
`max_iter` (`auto_session.py:497-507`), so on the **final pinned iteration**
`would_exceed()` returns `"max-configs"` and the naive skip would suppress that
iteration's `insights` — a behavioural regression to J-07–J-11 that **no
existing test guards** (`test_pinned_path_unchanged_by_open_universe_addition`
does not assert `insight_calls`). A correct fix must distinguish the
`max-configs` sentinel (which only gates *starting* a new config, not finishing
an in-flight one) from true spend caps (tokens/USD/wall). That is more than a
surgical change and the spec explicitly forbids pinned-path behaviour drift, so
it belongs in a follow-up iteration (natural home: the J-14 cheap-first routing
work). **Correct follow-up fix:** after the post-`generate` `_drain_usage`, skip
`insights` (still record the iteration) only when
`would_exceed() in {"ai-tokens","usd","wall-clock"}` — never on `"max-configs"`.

**B2 — IMPORTANT (fixed: documentation): dev handoff falsely claimed an
implemented within-round LLM skip.**
The dev handoff stated "*within the round a second LLM call is skipped once a
cap is hit (true one-call tolerance)*". Reading `_run_auto_session_impl` in full
confirms **no such skip exists**. The phase spec's skeptical-evaluation note
(`docs/phases/goal-auto-money-printer-iter-3.md:402-406`) explicitly directed
the auditor to cross-check handoff claims against the post-fix source diff for
exactly this; the reviewer flagged it (NOTE) and QA acknowledged it, but the
handoff text itself remained uncorrected. Corrected in
`docs/handoffs/goal-auto-money-printer-iter-3-dev.md` to accurately describe the
implemented behaviour (cap enforced at the start of each config/round; an
in-flight config completes its generate+insights; bounded one-config overshoot;
no within-round skip). Zero behaviour risk — documentation only.

**B3 — verified (no issue): 422-gate relaxation is correct and pinned-safe.**
`_is_open_universe` (`auto_session.py:469`) routes to open-universe **iff both**
`symbol` and `timeframe` are omitted; a *partial* pin falls into the pinned
branch and 422s via the preserved `missing`-field check
(`auto_session.py:1100-1118`). Unsupported `objective` → clean 422
(`:1062-1070`); open-universe partial/garbled dates → clean 422, never 500
(`:1074-1092`). Confirmed by `test_unsupported_objective_is_422`,
`test_open_universe_partial_dates_is_422_not_500`,
`test_open_universe_endpoint_accepted_and_listed`, and QA TC-04/05/06.

**B4 — verified (no issue): bounded seed universe, no fan-out.**
`_SEED_UNIVERSE` (`auto_session.py:75-88`) is a hard-coded 6-entry constant
(BTC/ETH/SOL/BNB × 4h/1h) — not the 26×6 grid, not env-driven, not a live
enumeration. `_config_plan` draws **only** from it;
`test_open_universe_runs_multiple_distinct_configs` asserts
`cfgs <= set(_SEED_UNIVERSE)`. Anti-goal satisfied.

**B5 — verified (no issue): real usage capture is genuine, not
pass-by-construction.** The chain
`capture_usage` (`shared/llm_usage.py`) → `script_generator`/`insights_generator`
/`compiler` after the existing usage logging → `pipeline.generate_strategy`/
`generate_insights` forward `usage_sink` → `_drain_usage` →
`tracker.record_usage` is intact. `test_usage_capture.py` drives the **real**
generator/pipeline classes with fake SDK clients carrying real-shaped `.usage`
(OpenAI `prompt/completion`, Anthropic `input/output` + cache fields) and
asserts exact captured counts — fails if bypassed/hardcoded. Anti-goal /
iter-2-generalized false-guard lesson satisfied.

**B6 — verified (no issue): durable spend + accepted-config persistence
survive a real disk re-read.** `_update_autorun_sync` (`auto_session.py:560-575`)
is a read-merge-write that `.update()`s only the explicit per-round changes, so
the creation-time `objective`/`historyScope`
(`auto_session.py:1148-1158`) and the per-round `spend=tracker.snapshot()` are
preserved verbatim across every loop write and the terminal write.
`test_open_universe_objective_and_history_scope_persisted` and
`test_hard_token_budget_exhausted_real_usage_and_durable_spend` both assert a
**fresh `read_session_meta`** (the real restart/reload path) still carries the
values. Round-1 TC-07 blocker genuinely fixed.

### Frontend Findings

**F1 — verified (no issue): additive, well-guarded, no journey regression.**
`SessionContainer.tsx` adds a distinct amber `budget-exhausted` branch
(`CircleDollarSign`, "budget reached") and a right-aligned `formatSpend()`
readout gated by `autoRun.spend ? … : ''` with per-field
`typeof === 'number'` guards and `{spendText && (…)}` — no NaN/undefined on
legacy/pinned sessions. `useBacktest.ts` is **type-only** (`AutoRunSpend` +
optional `AutoRunStatus.spend`); the iter-2 live-poll `try/finally` re-arm and
the J-02 heavy-detail merge precedence are byte-unchanged (diff confirms no poll
logic touched). Build EXIT 0 independently re-run. QA browser-verified J-02
re-bind and J-08 no-stale-terminal live.

### Test Findings

**T1 — verified (no issue): tests assert exact values and fail on bypass.**
`test_cost_tracker.py` asserts `FrozenInstanceError` on mid-run cap mutation,
monotonicity, negative/None-ignored, **independent** per-cap firing
(token/USD/configs/wall), zero/neg→safe-default, huge→hard-ceiling,
JSON-serialisable snapshot. `test_open_universe_best_is_robust_not_raw_return`
asserts the higher-raw-return WFE-failing config is explicitly **not** best.
`test_open_universe_multi_config_runs_in_subprocess_distinct_pids` asserts
`child_pid != os.getpid()` deterministically via the unchanged
`_subprocess_backtest_executor` seam with **no** timing bound (iter-2 lesson
honoured for the multi-config run). No skips/xfail.

**T2 — OBSERVATION: pinned-path insights coverage gap.**
`test_pinned_path_unchanged_by_open_universe_addition` guards config-pinning,
gen-call count, stop reason and `configsRun`, but not `insight_calls`. This is
why B1's naive fix would silently regress the pinned path — noted so a future
fixer adds an `insight_calls`-on-final-pinned-iteration assertion alongside the
correct B1 fix. No action this iteration (pinned behaviour is currently
correct/unchanged).

---

## 3. Domain Assessment

The core domain logic is sound. Best-selection correctly reuses
`select_best`/`robust_score` over the combined `RobustInputs` of **all**
explored configs — raw return is never the selector (verified in code and by
`test_open_universe_best_is_robust_not_raw_return`). The cost tracker's
`would_exceed()` uses `>=` (cap *reached*, not *exceeded*) and is evaluated at
round-top before `start_config()` and any LLM call, which is the precise
semantics the anti-goal demands ("no one more round past the cap"). The frozen
`CostCaps` dataclass plus the absence of any public mutator makes "widen my own
budget mid-run" structurally impossible. USD is derived from real captured
tokens × a static in-repo constant table (not a pricing API); an unknown model
contributes 0 USD but its tokens still bind the hard token ceiling — fail-safe,
never crashing. Open-universe iterations are written through the exact
`_build_node`/`write_iteration`/`append_activity_entries` path as manual runs,
so the headless search is genuinely UI-indistinguishable, and every explored
config is logged ("Exploring config N: SYM TF") for auditability. The frozen
`shared/contracts.py`, the RestrictedPython sandbox, and the deterministic
next-bar engine are byte-unchanged (`git diff` empty — independently confirmed),
and no new infrastructure was introduced.

The only substantive limitation is B1's bounded one-config LLM overshoot when
`generate` alone crosses a spend cap — real, but small, honestly accounted, and
strictly weaker than the load-bearing "no unbounded loop / no extra round"
guarantee, which holds.

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| 1 | Important | `docs/handoffs/goal-auto-money-printer-iter-3-dev.md` | Corrected the false claim that a within-round second LLM call "is skipped once a cap is hit"; replaced with an accurate description of the implemented bounded one-config overshoot and a pointer to audit B1. Documentation only — zero behaviour risk; full suite re-run after edit unaffected (183 passed / 1 pre-existing fail). |

No source/behaviour fix was applied for B1 — see B1: the reviewer's naive
one-liner would regress the byte-unchanged pinned path (J-07–J-11) with no test
to catch it; the correct fix is non-surgical and is specified for a follow-up.

---

## 5. Recommended Next Step

**Proceed.** The phase goal (J-12 + J-13 indivisible slice) is achieved,
independently re-verified, and free of new regressions; all ~14 activated
anti-goals hold at source-diff level. Carry **B1** forward as a tracked,
non-blocking follow-up: in the J-14 iteration, gate the post-`generate`
`insights` call on `would_exceed() in {"ai-tokens","usd","wall-clock"}` (never
on `"max-configs"`, which must not suppress an in-flight config's insights),
and add an `insight_calls`-on-final-pinned-iteration regression assertion to
`test_pinned_path_unchanged_by_open_universe_addition` so the pinned path stays
guarded. No human decision is required to ship this iteration.
