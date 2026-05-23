# goal-financial_free-iter-1 Functional Test Plan

**Phase:** goal-financial_free-iter-1
**Date:** 2026-05-23
**Frontend Present:** no

## Phase Goal

A single `POST /api/auto-sessions` call starts a server-side, budget-bounded automated strategy session that reuses `BacktestPipeline`, writes standard session/iteration/activity/suggestion artifacts to the existing file store, runs to a terminal state (`criteria-met` / `budget-exhausted` / `stopped` / `interrupted`), and marks a WFE-gated robust best — all with no browser involvement.

> **Verification method:** API-grounded. Per documented Chrome-MCP headless render-throttle, the sanctioned substitute for browser checks is asserting against the backend endpoints the UI calls (HTTP status + parsed `autoRun`/iteration payloads with concrete values). Loop tests run hermetically with an injected fake pipeline (no live LLM); the live smoke is gated on `OPENAI_API_KEY`.

## Test Cases

### TC-01 — Start headless session (J-07)
**Type:** api
**Preconditions:** Backend running; injected fake pipeline available for hermetic run.

**Steps:**
1. `POST /api/auto-sessions` with a pinned config (`natural_language`, `symbol`, `timeframe`, `start_date`, `end_date`, `initial_capital`) and `budget: { max_iterations: 2 }`.
2. Capture the returned `sessionId`.
3. `GET /api/sessions`.

**Expected outcome:** Start returns HTTP 200 with `{ sessionId, status, autoRun }`, `status` ∈ {`running`, `queued`}; the returned `sessionId` is present in `GET /api/sessions` immediately (before the loop completes).
**Pass criteria:** HTTP 200; `sessionId` non-empty; `status` is `running` or `queued`; same `sessionId` found in the `GET /api/sessions` list.

---

### TC-02 — Terminal: criteria-met with satisfied targets (J-09)
**Type:** api
**Preconditions:** Hermetic fake pipeline producing a candidate that satisfies lenient targets.

**Steps:**
1. `POST /api/auto-sessions` with **lenient** `targets` (e.g. trivially satisfiable `min_total_return`/`min_sharpe`) and a small `budget.max_iterations`.
2. Wait for the loop to reach a terminal state.
3. `GET /api/sessions/{sessionId}` and read `autoRun`.
4. `GET /api/sessions/{sessionId}/iterations/{bestIterationId}`.

**Expected outcome:** `autoRun.status` terminal with `stopReason: "criteria-met"`; `bestIterationId` set; the best iteration's metrics satisfy **every** supplied target.
**Pass criteria:** `stopReason == "criteria-met"`; `bestIterationId` non-null; each supplied target field is satisfied by the best iteration's metrics.

---

### TC-03 — Terminal: budget-exhausted respects hard cap (J-09 + hard-budget anti-goal)
**Type:** api
**Preconditions:** Hermetic fake pipeline; targets unsatisfiable or absent.

**Steps:**
1. `POST /api/auto-sessions` with **unsatisfiable/absent** `targets` and `budget.max_iterations: 2`.
2. Wait for terminal state.
3. `GET /api/sessions/{sessionId}` → read `autoRun.budget` and `stopReason`.
4. `GET /api/sessions/{sessionId}/iterations` and count iterations.

**Expected outcome:** `stopReason: "budget-exhausted"`; `iterationsDone == maxIterations` (or wall-clock cap hit); no iteration appended past the cap; `bestIterationId` still marked.
**Pass criteria:** `stopReason == "budget-exhausted"`; `autoRun.budget.iterationsDone == maxIterations`; appended iteration count does not exceed the cap; `bestIterationId` non-null.

---

### TC-04 — Same-artifacts: no parallel store / no schema fork (anti-goal)
**Type:** artifact
**Preconditions:** A completed hermetic run from TC-02/TC-03.

**Steps:**
1. `GET /api/sessions/{sessionId}/iterations/{id}` for a loop-produced iteration.
2. Inspect on-disk `live/{sessionId}/` (session.json, iterations, activity).
3. Confirm iterations were written via `session_store` (`write_iteration`/`append_activity_entries`), not a separate path.

**Expected outcome:** Loop-produced iterations return full result + rating via the standard endpoint; activity entries and suggestions are present; artifacts are byte-shape-compatible with a manual run; no parallel store directory or forked schema exists.
**Pass criteria:** Iteration endpoint returns complete result/rating; activity + suggestions present; all artifacts under the existing `live/{sessionId}/` store; no new/parallel store path.

---

### TC-05 — Persisted autoRun survives restart + orphan reconciliation (persisted-status anti-goal)
**Type:** api
**Preconditions:** A session with a persisted `autoRun` block; ability to simulate a fresh store read / startup.

**Steps:**
1. `GET /api/sessions/{sessionId}` and confirm `autoRun` block is present and well-formed.
2. Simulate a fresh store read (reload meta from `session.json`) and re-check `autoRun`.
3. Leave a session in `running`/`queued`, then trigger the startup reconciliation path.

**Expected outcome:** `autoRun` round-trips through `session.json` and is returned by `GET /api/sessions/{id}`; a fresh read still shows the persisted status; an orphaned `running`/`queued` session is reconciled to terminal `interrupted` on startup.
**Pass criteria:** `autoRun` present after fresh read with all fields (`status`, `stopReason`, `stopRequested`, `bestIterationId`, `budget{…}`, `startedAt`, `endedAt`); orphaned run becomes `status: "interrupted"` after startup reconciliation.

---

### TC-06 — Robust best is WFE-gated + min-trades-floored (robust-best anti-goal)
**Type:** api
**Preconditions:** Hermetic fake pipeline producing one candidate with higher raw return but WFE < 0.3 (or below the min-trades floor), and another lower-return but WFE-passing candidate.

**Steps:**
1. Run a loop where the higher-raw-return candidate fails the WFE 0.3 gate (or the min-trades floor).
2. `GET /api/sessions/{sessionId}` → read `bestIterationId`.
3. Compare against the WFE-passing, floor-satisfying candidate.

**Expected outcome:** The WFE-failing / under-floor (zero/under min-trades) candidate is **not** marked best despite higher raw return; the robust, WFE-passing candidate is marked best.
**Pass criteria:** `bestIterationId` points to the WFE-passing, min-trades-satisfying iteration; the higher-raw-return WFE-failing candidate is excluded.

---

### TC-07 — Budget tracker immutable & hard-enforced (hard-budget anti-goal)
**Type:** api
**Preconditions:** Unit-level access to `BudgetTracker`; loop with small caps.

**Steps:**
1. Construct/increment a `BudgetTracker` and assert each operation returns a new value object (no in-place mutation) and never yields a state exceeding an enforced cap.
2. Run the loop with `max_iterations`/`max_wall_clock_sec` set and confirm `exceeded()` is checked **before** each round.

**Expected outcome:** Tracker is immutable; the loop stops before exceeding `max_iterations`/`max_wall_clock_sec` and never starts "one more round" past a cap.
**Pass criteria:** Mutating attempts produce new objects (or raise); no state exceeds enforced caps; loop halts at the cap with `iterationsDone <= maxIterations`.

---

### TC-08 — Stop infrastructure (cancellation; infra for J-11)
**Type:** api
**Preconditions:** A running auto-session.

**Steps:**
1. `POST /api/auto-sessions/{sessionId}/stop`.
2. Wait for the loop's next checkpoint.
3. `GET /api/sessions/{sessionId}` → read `autoRun`.
4. Count iterations after the stop.

**Expected outcome:** Stop returns 200 and flips persisted `stopRequested`; loop transitions to `status`/`stopReason` `stopped` with best-so-far retained; no iterations appended after stop.
**Pass criteria:** HTTP 200; `autoRun.stopRequested == true` then terminal `stopped`; `bestIterationId` retained; iteration count unchanged after the stop checkpoint.

---

### TC-09 — Non-blocking launch keeps event loop responsive (non-blocking anti-goal)
**Type:** api
**Preconditions:** Backend running; a run that takes measurable time.

**Steps:**
1. `POST /api/auto-sessions` and confirm the response returns before the loop finishes (status still `running`/`queued`).
2. While the run is active, issue `GET /api/sessions` and confirm it responds promptly.

**Expected outcome:** Start returns before loop completion; `GET /api/sessions` stays responsive during an active run (the loop awaits the `backtest_semaphore`, never blocking the event loop).
**Pass criteria:** Start response received while status is non-terminal; concurrent `GET /api/sessions` returns 200 promptly during the active run.

---

### TC-10 — Error: open-universe rejected (J-12 deferral)
**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `POST /api/auto-sessions` with `symbol`/`timeframe` **omitted** but a valid `budget`.

**Expected outcome:** Rejected with a clear 4xx and an explanatory message (not silently defaulted).
**Pass criteria:** HTTP 4xx; response message clearly indicates open-universe is unsupported this iteration.

---

### TC-11 — Error: missing required budget (validation)
**Type:** api
**Preconditions:** Backend running.

**Steps:**
1. `POST /api/auto-sessions` with a valid pinned config but **no** `budget` (and separately, `budget` without `max_iterations`).

**Expected outcome:** Request rejected by schema validation.
**Pass criteria:** HTTP 422 for both missing `budget` and missing `budget.max_iterations`.

---

### TC-12 — Error: stop on unknown / already-terminal session
**Type:** api
**Preconditions:** Backend running; one terminal session available.

**Steps:**
1. `POST /api/auto-sessions/{unknownId}/stop`.
2. `POST /api/auto-sessions/{terminalSessionId}/stop`.

**Expected outcome:** Unknown session → 404; already-terminal session → idempotent no-op 200.
**Pass criteria:** Unknown → HTTP 404; already-terminal → HTTP 200 with no state change.

---

### TC-13 — Backend regression suite + invariants
**Type:** api
**Preconditions:** Test env per `.claude/project-template.md`.

**Steps:**
1. Run the backend test suite.
2. Confirm `test_lookahead`, `test_determinism`, `test_sandbox` pass.

**Expected outcome:** No new regressions; the three invariant tests pass; J-01…J-06 manual flows unaffected.
**Pass criteria:** Suite green except the pre-existing, unrelated `test_directions_cache::test_write_and_read_full_round_trip` (known red); the three invariant tests pass.

---

### TC-14 — Secret hygiene (no keys in artifacts)
**Type:** artifact
**Preconditions:** A completed run.

**Steps:**
1. Grep `live/{sessionId}/` artifacts (session.json, activity log, iterations) for API keys / secret material.

**Expected outcome:** Only NL prompt, config, metrics, ids, and counters persisted; no API key/secret in the activity log or `autoRun` block.
**Pass criteria:** No secret/key strings present in any persisted artifact.

---

### TC-15 — Live smoke with tiny real budget (key-gated)
**Type:** api
**Preconditions:** `OPENAI_API_KEY` present.

**Steps:**
1. `POST /api/auto-sessions` with a **tiny real budget** (`max_iterations: 1–2`, short date range, cheapest default model).
2. Wait for terminal state; `GET /api/sessions/{id}`.

**Expected outcome:** Reaches a real terminal state with a marked `bestIterationId`. If `OPENAI_API_KEY` is absent, documented as **skipped** in the dev handoff (not silently passed).
**Pass criteria:** Terminal `autoRun.status` with non-null `bestIterationId`; OR explicit skip note in the handoff when key absent.

---

### TC-16 — Carry-forward verdict: get_session payload not worsened
**Type:** artifact
**Preconditions:** `session_routes.py:get_session` modified to add `autoRun`.

**Steps:**
1. Inspect the `get_session` change; confirm only `"autoRun": meta.get("autoRun")` is added.
2. Confirm lazy iteration-loading behavior is unchanged and the `autoRun` block is tiny (strings, ids, integer counters).

**Expected outcome:** The pre-existing ~245KB `equity_curve` embed is **not worsened**; route stays lightweight/lazy; coherence verdict on the embed delivered (fix out of scope).
**Pass criteria:** `autoRun` addition is additive and tiny; no change to lazy iteration loading; no increase in baseline open-payload size attributable to this change.

---

## Summary

Total test cases: 16
- API tests: 12 (TC-01, TC-02, TC-03, TC-05, TC-06, TC-07, TC-08, TC-09, TC-10, TC-11, TC-12, TC-13, TC-15) — note TC-15 is key-gated
- Artifact checks: 4 (TC-04, TC-14, TC-16) and the artifact portion of TC-04/TC-05
- Browser tests: 0 — backend-only iteration; per the documented Chrome-MCP headless render-throttle, J-07's "appears as a session" is verified via `GET /api/sessions` (TC-01), the sanctioned API-grounded substitute.

Journey coverage: **J-07** → TC-01; **J-09** → TC-02, TC-03. Anti-goals: same-artifacts → TC-04; persisted-status → TC-05; robust-best → TC-06; hard-budget → TC-03/TC-07; non-blocking → TC-09; secret-hygiene → TC-14. Stop infrastructure → TC-08. Error cases → TC-10/TC-11/TC-12. Regression/invariants → TC-13. Live smoke → TC-15. Carry-forward verdict → TC-16.
