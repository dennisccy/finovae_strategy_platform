# goal-auto-money-printer-iter-5 Audit Report

**Date:** 2026-05-19
**Auditor:** Hard audit pass — skeptical, evidence-based (code traced, tests re-run, not handoff-trusted)

---

## 1. Executive Verdict

**Verdict:** PASS

The phase goal — a read-only global-history **warm start** that reorders the bounded
`_SEED_UNIVERSE` SCREEN enumeration by mined prior-session family strength, with an
explicit `history_scope: "this-run"` **opt-out** and a planner-decision citation in the
existing activity feed — is genuinely and verifiably achieved. The causal chain is real
(not theatre): `_warm_start_configs` reorders `configs` → `_run_staged_open_universe`
takes `screen_configs = configs[:_SCREEN_SET_SIZE]` → the historically strongest family
is screened/promoted first. All ~12 load-bearing cross-run anti-goals (read-only,
opt-out, bounded-seed permutation, once-per-run/off-thread, no-LLM, robust-best, pinned
byte-unchanged, no schema fork, no secrets) are each backed by an exact-assert test and
several also by live browser QA. The one MINOR documentation defect the reviewer flagged
(a third stale "J-15/OUT" comment the spec explicitly mandated correcting) **was fixed
during this audit**. The backend suite was independently re-run: **200 passed / 1
pre-existing tolerated red**, zero new regressions.

---

## 2. Findings

### Backend Findings

**B1 — MINOR (fixed): stale "J-15 / OUT OF SCOPE" comment at `auto_session.py:115-116`**
The comment above `_SEED_UNIVERSE` still read *"The deterministic bounded enumerator
below walks it in order (the history-surrogate/bandit + LLM planner that would prioritise
within it is J-15 / OUT OF SCOPE)"* — now factually false: J-15 is implemented six lines
below, and warm-start returns the seed as a stable permutation, not always "in order".
The spec's TESTING REQUIREMENTS explicitly mandated correcting the stale "J-15/OUT"
comments; the dev handoff implied all were fixed ("corrected the two stale … comments")
but this third occurrence was missed (the docstring and the accept-&-persist inline
comment *were* correctly fixed — confirmed in the diff). **Fix applied this audit:**
rewrote `auto_session.py:113-119` to accurately describe the iter-5 effective semantics
(fixed order by default; J-15 stable-permutation warm-start on effective-`"global"`;
`"this-run"` opt-out; still only the bounded set, no fan-out; no LLM planner), matching
the style of the two already-corrected sibling comments. Verified: `ruff check
backend/auto_session.py` → All checks passed; syntax OK; **zero** residual
"J-15/OUT"/"walks it in order" comments remain. Comment-only — no runtime change
possible, so the 200-test suite was not re-run (token policy; ruff is the project gate).

**B2 — OBSERVATION: `_strongest_family` third tie-break is unreachable defensive code
(`auto_session.py:~685`)**
`-ord(fam[0][0]) if fam[0] else 0` never decides ordering: only `stage=="promote"`
open-universe iterations are mined, all distinct `_SEED_UNIVERSE` members, so
`(score, -seed_index)` already uniquely orders every family. Harmless, deterministic,
correct. Per auditor rules, OBSERVATION-level — not fixed, documented only (matches the
reviewer's NOTE).

### Frontend Findings

**F1 — OBSERVATION: zero frontend code changed, correctly.**
`git diff HEAD --stat` shows only `auto_session.py` (+) and `test_auto_session.py` (+);
no `apps/frontend/*` change. The verify-first clause held: the citation is emitted with
an empty `iterationId` so the existing `ActivityLog.groupByIteration` renders it
ungrouped at the top of the feed, and `ActivityLogEntry.tsx` renders an `auto-run`
entry's content verbatim (no `truncate`). Browser QA (TC-06) independently confirmed the
untruncated violet citation span renders at the top of the existing feed and is absent
on the `"this-run"` run, with screenshots. UI-indistinguishable from a manual run, as
the goal requires. No frontend handoff needed.

### Test Findings

**T1 — OBSERVATION: tests are strong and causally isolating, not pass-by-accident.**
`_F1_DEFAULT_UNSCREENED = _SEED_UNIVERSE[5]` is a *default-unscreened* family (beyond the
4-config SCREEN prefix). Without warm-start it is never screened/promoted; the opt-out
test explicitly asserts `_F1_DEFAULT_UNSCREENED not in _distinct_cfgs(sid)`, proving the
reorder is the *causal* mechanism for the global test, not a coincidence. Exact-value
assertions throughout (`fam_best == {("ETH/USDT","1h"): 0.81}` after `extra_noise`
seeding of screen-only/no-WF/error iters proves the promote∧WF∧finite filter and
current-session exclusion). `test_warm_start_changes_order_not_robust_best_selection`
genuinely proves the invariant: the history-favoured family is screened AND promoted
first but, being WFE=0.0, `final["bestIterationId"]` is the other family — warm-start
changes order, never selection. The read-only proof snapshots sha256 + `st_mtime_ns` +
the full relpath set. The two consciously-updated tests retain their original
persistence assertions and add behavioural ones (strengthened, no skip/xfail). Re-run
independently: `test_auto_session.py` **53 passed**; full suite **200 passed / 1
failed**.

**T2 — GAP (documented, compensated, non-blocking): QA browser run used the
non-isolated production-sized store.**
The QA runner backend uses the durable `.data/backtests` store (~113 sessions) — which
*correctly* honours the no-`/tmp` durable-store anti-goal — not the isolated 3-session
store the test plan's TC-01/TC-02 assume. Consequently the *isolated-store* sub-assertions
"empty store ⇒ no citation" (TC-01) and "first promoted family == run-#1 F1" (TC-02)
could not be shown live in isolation; QA fell back to the corresponding **passing**
isolated-store unit tests (`test_no_prior_history_fallback_is_fixed_seed_order`,
`test_global_warm_start_reorders_and_cites_prior`), which I independently re-ran and
read — they deterministically prove exactly those assertions. The live browser run still
verified the *observable* J-15 behaviour (citation present on `"global"`, absent on
`"this-run"`, reorder visibly applied, screenshots) and even *corroborated* the
robust-best invariant live (warm-start family ETH/USDT 4h screened first but BTC/USDT 4h
promoted-best). QA documented this honestly and pointed to the exact compensating tests;
no assertion was masked or skipped. This is an environment artefact of honouring the
durable-store anti-goal, **not an iter-5 defect**, and is fully compensated by
deterministic unit proof.

**N1 — OBSERVATION (not iter-5 work): outer-loop carryover.**
The spec NOTES record that iter-4's transient closure trip needs the *outer loop* to
regenerate two iter-4 UI-test-design stubs (`ui-test-design-phase.sh` then
`phase-closure-check.sh` for `goal-auto-money-printer-iter-4`). The spec explicitly
states this is orchestrator work, NOT iter-5 source/test/journey work, and MUST NOT flip
any verdict. Recorded here for completeness; it does not affect this audit verdict.

---

## 3. Domain Assessment

The core domain logic is correct and minimal:

- **Read-only mining (`_mine_history`)**: enumerates `session_store.BASE_DIR/"live"`
  directly and uses only `list_iteration_dirs` + `read_iteration_meta` (→ `find_iter_dir`
  → `_read_json_safe`) — I read all four; every one is a pure read with no write/migration
  path. It deliberately does *not* call `derive_session_tabs` (which would write
  `_index.json`), so the read-only / J-02-not-regressed anti-goal holds at the code level,
  corroborated by the content+mtime+fileset hash test and the live 38-file pre/post hash.
  Current session excluded; only `stage=="promote"` ∧ non-null `walkForwardResult` ∧
  finite non-bool `robustScore` count; best-effort `except` discipline mirrors SCREEN/
  PROMOTE so a corrupt prior dir is skipped, never hangs/raises out.
- **Reorder (`_reorder_configs`)**: a strict stable permutation — mined families (group 0)
  before unseen (group 1), strongest first, original index as the deterministic stable
  tie-break. `set`/`len` equality to `_SEED_UNIVERSE` is asserted; no add/drop/fan-out
  is structurally possible.
- **Effective-scope (`_resolve_history_scope`)**: only the explicit (whitespace-tolerant)
  `"this-run"` opts out; `None`/`""`/`"global"`/garbage/non-string → `"global"`, never
  raises (garbage is a clean default, not a 500). Raw value persisted verbatim; effective
  value an *additive* `effectiveHistoryScope` key via the existing `_update_autorun`
  (no schema fork — mirrors iter-4's additive `stage`).
- **Wiring**: the mine+reorder+citation runs exactly once, off-thread via
  `asyncio.to_thread`, inside the `if is_open:` branch only, guarded by
  `effective_scope == _HISTORY_SCOPE_GLOBAL`, *before* `_run_staged_open_universe`. The
  pinned `else:` branch (`_run_pinned`, `configs[0]`) is byte-untouched: no
  `effectiveHistoryScope`, no mine, no citation. No LLM call exists anywhere in the path
  (deterministic surrogate, per the spec's explicit core design); the "never re-sent
  uncached every round" anti-goal is satisfied structurally by the once-per-run
  guarantee, exactly as the spec reasons. `shared/contracts.py`, `sandbox.py`,
  `pipeline.py`, `backtest/`, `session_store.py` diffs are empty (verified).

The robust-best path (`select_best`/`robust_score` over promoted iterations) is
untouched — warm-start only changes SCREEN *order*, never selection — and this is proven
both by an exact-assert unit test and corroborated live.

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| 1 | MINOR | `apps/backend/backend/auto_session.py:113-119` | Rewrote the stale `_SEED_UNIVERSE` header comment that still claimed the history-surrogate "is J-15 / OUT OF SCOPE" and the enumerator "walks it in order" — now accurately describes the iter-5 effective semantics (default fixed order; J-15 stable-permutation warm-start on effective-`global`; `"this-run"` opt-out; bounded-set-only, no fan-out; no LLM planner). Satisfies the spec's explicit "correct stale J-15/OUT comments" mandate (all three now corrected). Comment-only — `ruff check` passes, syntax OK, zero behavioural change. |

---

## 5. Recommended Next Step

**Proceed.** Phase goal fully achieved; the only actionable defect (a stale comment the
spec mandated fixing) is fixed; remaining items are OBSERVATION-level or honestly
documented, compensated environment notes. The backend suite is green (200 passed / 1
pre-existing out-of-scope tolerated red — `test_directions_cache::test_write_and_read_full_round_trip`,
`directions_cache.py` untouched; iter-4 188/1 → +12 passing, 0 new regressions). Dev
handoff and all 6 UI visibility artifacts are present and populated.

Next iteration is **iter-6 = J-16** (deep overfit-gating stress demonstration /
leaderboard) — its robust-best invariant is only *preserved* here, not extended. Per the
agent rule, J-16 remaining failing means the goal-evaluator should still CONTINUE (not
GOAL_ACHIEVED). The recorded iter-4 outer-loop carryover (regenerate two iter-4
UI-test-design stubs) is orchestrator work and must not flip any journey/anti-goal
verdict.
