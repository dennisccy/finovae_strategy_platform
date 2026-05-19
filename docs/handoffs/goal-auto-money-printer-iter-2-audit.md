# goal-auto-money-printer-iter-2 Audit Report

**Date:** 2026-05-19
**Auditor:** Hard audit pass — skeptical, evidence-based

---

## 1. Executive Verdict

**Verdict:** PASS_WITH_GAPS

The Layer-1 Foundation closure is genuinely achieved. The backend is now the single
source of truth for the automated search: a public stop endpoint, a by-`sessionId`
in-process cancellation registry cleaned on all four terminal paths (incl. the crash
`finally`), a durable worker/restart-safe per-round stop signal, terminal `stopped`
with a non-null reason, and `bestIterationId` preserved by the robust objective (not
raw return). The legacy in-browser `startAutoRun`/`stopAutoRun` iterate loop is
**deleted** (verified by source read + grep, not by headline), both UI entrypoints
and the Stop control are rewired to the backend, and the two mandatory lessons
(iter-1 ownership re-derive; iter-0 J-02 right-panel re-bind) are correctly applied.
All anti-goals verified at source-diff + test level. One documented, non-blocking
GAP remains (stop-endpoint latency degrades under an unrealistic synthetic load),
plus minor type-honesty observations — none compromise the phase goal.

---

## 2. Findings

### Backend Findings

**B1 — OBSERVATION (verified-correct): subprocess backtest isolation is in-scope, anti-goal-compliant**
The QA-FAIL retry introduced a `multiprocessing` (`spawn`) child worker
(`auto_session.py:121-291`) to fix the CRITICAL event-loop-starvation anti-goal
(`The automated background job MUST NOT block the API event loop`). I verified this
is **not** an anti-goal violation and **not** scope creep:
- The child builds a real `BacktestPipeline()` and calls
  `execute_backtest(**payload)` verbatim (`_real_pipeline_backtest`,
  `auto_session.py:139-158`) — the RestrictedPython sandbox and the deterministic
  next-bar engine run **inside** the child via the unmodified pipeline. `git diff`
  confirms `pipeline.py`, `backtest/engine.py`, `backend/sandbox.py`,
  `backend/api.py`, `backend/robust_objective.py`, and `shared/contracts.py` have a
  **0-line diff**.
- `multiprocessing` is the Python **stdlib** (same class of in-process offload as
  the ThreadPoolExecutor already used here) — not Celery/Redis/DB/broker; no new
  external infra, no parallel store, no schema fork.
- The change is contained to the single backend file the plan authorises
  (`auto_session.py`) plus its test. It is the minimal correct remediation of an
  explicit DoD regression guard, so it is in-scope, not drift.

**B2 — OBSERVATION: durable `stopRequested` left set on a terminal `stopped` run**
`auto_session.py:1013-1020` short-circuits any already-terminal session and writes
nothing, and the loop never re-reads the flag once terminal. This is harmless and is
exactly what makes a re-stop idempotent — proven by
`test_stop_already_terminal_is_idempotent_no_state_regression` (asserts
`before == after` and `stopRequested NOT in after`). No action needed.

**B3 — OBSERVATION (spec-consistent): "no iterations after stop" semantics**
On the durable-only path the in-flight iteration completes and is persisted, then
the loop breaks at the top of the next round (`auto_session.py:599-613`); on the
live-token path the in-flight backtest is interrupted via `PipelineError`. No *new*
iteration starts after the stop. This matches the spec ("no further iterations are
appended after the stop") and is asserted tightly by
`test_durable_stop_signal_honored_no_post_stop_iterations` (`gen_calls == 1`,
exactly one iteration dir) and corroborated live by QA TC-17/TC-18
("stopped at 5/8, not run to budget=8"). Correct.

### Frontend Findings

**F1 — GAP/OBSERVATION (NOTE, type honesty): `AutoRunStatus.stopReason` union omits `'stopped'`**
The backend now writes `stopReason="stopped"` but the TS `stopReason` union
(`useBacktest.ts:~420`) does not list it. No runtime bug: `AutoRunBar`'s
`status==='stopped'` branch ignores `stopReason` and the value flows through an
any-cast, so there is no `tsc` error and the bar correctly renders "Automated run
stopped" (verified live by QA TC-17). Cosmetic type-honesty item; left as-is
(NOTE-level — not fixed per auditor rules; no functional impact).

**F2 — OBSERVATION: mandatory iter-1 lesson correctly implemented**
`useBacktest.ts:823-835` authoritatively re-derives this session's durable `autoRun`
from the backend on mount **and** on `isActive` flip (session switch); deps
`[isHydrated, isActive, sessionId]`. `sessionStatus.isAutoRunning = headlessRunning`
(`:880`) makes the session-list spinner and the in-session `AutoRunBar` derive from
the **same** durable status, so they cannot disagree. The Blocker #2 fix
(`:794-802`) re-arms the live poll in a `finally`, so a single transient
`apiLoadSession` failure no longer permanently freezes the bar (the iter-1
stale-terminal failure mode). Verified live by QA TC-20 (61 containers, rapid
switch, no stale terminal).

**F3 — OBSERVATION: iter-0 lesson (J-02) not regressed**
The live-poll merge preserves locally lazy-loaded heavy detail
(`result: n.result ?? null`, `useBacktest.ts:744-754`) and the `loadingDetailIdRef`
guard is intact (`:457`). The J-02 path is not in the diff. Verified live by QA
TC-19 (right panel rebinds equity/trades/WF to the selected run).

### Test Findings

**T1 — OBSERVATION (verified-tight): stop coverage asserts exact values, no skips**
I independently re-ran `tests/test_auto_session.py` → **26 passed**, and the full
backend suite → **150 passed, 1 failed** (the pre-existing out-of-scope
`test_directions_cache`, confirmed **not** in the iter-2 diff — zero new
regressions). The new tests assert exact values and cover failure/edge paths with
**no `pytest.skip`/`xfail`**: durable stop honored (`gen_calls==1`, best preserved),
restart-safe stop with no live token (`gen_calls==0`, real asserts),
best-on-stop = robust winner not the higher-raw-return WFE-failing candidate,
registry removed on all four terminal paths incl. the crash `finally`, idempotent
terminal (`before==after`), unknown→404 (direct + HTTP).

**T2 — OBSERVATION (addresses core.md "passes by accident"):**
`test_headless_loop_does_not_block_event_loop` was correctly rewritten. The old stub
used `await asyncio.to_thread(time.sleep, …)` which **releases** the GIL and could
never reproduce the starvation it claimed to guard. The new test drives real
GIL-holding CPU work through the production subprocess seam and asserts
**deterministically** that every backtest ran in a different OS process
(`child_pid != parent_pid`, `test_auto_session.py:665-677`), with a lenient
timing check as corroboration only. This is a genuine, non-flaky guard.

---

## 3. Domain Assessment

The core domain logic is correct. Stop is cooperative and dual-pathed (fast
in-process token cancel + durable per-round `stopRequested` read off the event-loop
thread), so it is honored in multi-`WEB_CONCURRENCY` / post-restart cases without a
parallel store. Terminal-state selection reuses the existing robust `select_best`:
on stop, `best_id = select_best(completed)` (`auto_session.py:776`) — never raw
return — and live QA confirmed a 6.45% robust winner was kept over a 12.08% raw
candidate (TC-17) and a 27.27% robust winner on API stop (TC-18). The hard budget
remains bounded (`_resolve_budget` clamps to `HARD_MAX_ITERATIONS`; budget/cancel
checks precede each round so no "one more round" past the cap). Open-universe is
still rejected with a clean 422 (`create_auto_session:887-904`), keeping J-12 out of
scope. The headless run writes the same file-store artifacts a manual run does
(`_build_node` canonical key set), keeping a headless run indistinguishable in the
UI. Anti-goals hold: `contracts.py` byte-unchanged, no in-place dataclass mutation,
no secrets in artifacts, lazy `GET /api/sessions/{id}`, `BACKTEST_STORE_DIR` not in
the diff (still non-`/tmp`).

**Documented GAP (non-blocking, escalated by QA for the auditor):**
`POST /api/auto-sessions/{id}/stop` latency is **0.027 s** in a clean environment
and under normal concurrency (TC-02/TC-05; unit asserts `< 1.0 s`), but degrades to
**~10.5 s** under an unrealistic synthetic load (6+ concurrently spawned
auto-sessions + a browser with 61 live-polling `SessionContainer`s — TC-18). Even
there it returned 200 **without awaiting loop completion** (an LLM iteration would
take far longer), the run reached terminal `stopped` cooperatively with best
preserved, and the UI converged with no reload, and TC-05 shows the event loop stays
non-blocking under normal concurrency. The residual cause is the multi-MB
`BacktestResult`/`WalkForwardResult` pickle across the child pipe (the dev handoff
identifies trimming to a scalar proxy as a future micro-optimisation). The spec's
anti-goal ("must not block / must not wait for the loop") and DoD event-loop guard
hold for the realistic single-run profile. This is an acceptable, documented
limitation, not a phase-goal-defeating defect — hence PASS_WITH_GAPS rather than a
clean PASS. Not fixed in this audit: a correct fix (result trimming / scalar proxy
across the pipe) is non-surgical and would risk the working stop/best-preservation
path; it belongs in a follow-up optimisation iteration, not a skeptical audit patch.

---

## 4. Fixes Applied During This Audit

| # | Severity | File | Change |
|---|----------|------|--------|
| — | — | — | None. No CRITICAL or IMPORTANT issues found. The single GAP (load-sensitive stop latency) is non-blocking, documented, and a non-surgical optimisation out of audit-fix scope; the remaining items are NOTE/OBSERVATION level and not fixed per auditor rules. |

---

## 5. Recommended Next Step

**Proceed.** Phase goal (J-10, J-11) is achieved and the required-still-passing
journeys (esp. J-02, J-08) are verified non-regressed at source-diff + live-test
level. The Layer-1 Foundation is closed and hardened: the iterate loop now exists
**only** in the backend (anti-goal satisfied), the run survives reload, and is
stoppable from API and UI with the robust best preserved.

Carry forward to iter-3 (Optimizer layer — J-12 open-universe, J-13 immutable
AI-token/USD + wall-clock cost tracker, J-14–J-16): include as a tracked,
non-blocking item the stop-endpoint pickle trimming (scalar result proxy across the
child pipe) to remove the load-sensitive latency tail surfaced here.
