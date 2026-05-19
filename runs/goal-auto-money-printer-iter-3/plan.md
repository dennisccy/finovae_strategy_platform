# goal-auto-money-printer-iter-3 Execution Plan

**Optimizer Foundation — indivisible slice: J-12 (open-universe search) + J-13 (immutable hard cost tracker).**
Layer-1 Foundation (J-07–J-11) is closed/hardened. This iteration opens Layer-2.
Aligned with `docs/goal.md` success criterion "one API call … explores multiple
distinct configs … within the stated AI-token/cost budget … best by the robust
objective." No goal drift; J-14/J-15/J-16 are explicitly OUT OF SCOPE.

## What to Build

**Backend (`apps/backend`)**
- Extend `AutoSessionRequest` (NOT `shared/contracts.py`): add `objective: Optional[str]`
  (default `"robust"`; any other value → clean 422 — single-robust-scalar Non-Goal) and
  `history_scope: Optional[str]` (accepted & persisted only; cross-run *learning* is J-15/OUT).
- Relax the open-universe 422 gate (`auto_session.py:884-911`): when symbol/timeframe
  (and optionally start/end) are omitted AND objective+budget are well-formed → accept and
  run the open-universe controller. **Pinned path keeps its existing required-field
  validation byte-for-byte** (J-07–J-11 must not regress). Malformed → 422, never 500.
- Bounded seed universe: a small hard-coded constant of `(symbol, timeframe)` candidates
  (≤ ~8 entries; a few liquid pairs × a couple timeframes). NOT the 26×6 grid, NOT
  env-driven, NOT a live exchange enumeration. Open-universe draws **only** from this set.
- Open-universe config-search controller: a **deterministic bounded enumerator** (NOT a
  bandit/LLM planner — that's J-15) that drives the existing
  generate→backtest(+WF)→insights→record path across **≥2 distinct configs** (differing
  symbol and/or timeframe) in ONE session. Each config writes via the existing
  `_build_node`/`write_iteration`/`append_activity_entries` path so a headless run is
  UI-indistinguishable from a manual one; the activity log records each config explored.
  Omitted start/end → a fixed deterministic short historical window (tiny-budget rule).
- Best across all configs via the existing `select_best`/`robust_score` over the combined
  `RobustInputs` — no new selection logic, never raw return.
- Real AI-token usage capture: surface the real SDK `.usage` already read-and-discarded at
  `compiler.py:303-309`, `insights_generator.py:327-333`/`:361-363`,
  `script_generator.py:405-411`/`:438-440` up to the auto-session loop via pipeline-level
  (non-frozen) returns or a lightweight accumulator passed into the LLM calls — developer's
  choice. Do NOT touch `shared/contracts.py`, the sandbox, the engine, or backtest internals.
- Per-model USD price table: a small static input/output USD-per-token constant keyed by
  model id (extend `shared/model_catalog.py` or a sibling constant module — NOT
  `shared/contracts.py`, NOT a pricing API). Unknown model → token cap still binds, no crash.
- Immutable hard cost tracker: monotonic/append-only spend; caps fixed at run start
  (cannot be raised/lowered mid-run); independently enforces AI-tokens, USD, **max-configs**,
  and wall-clock, plus the existing `max_iterations` clamp. Cap checked **before** each
  config/round ("no one more round/config past the cap"); one in-flight LLM call may
  marginally exceed (goal's within-one-call tolerance). `AutoSessionBudget` gains optional
  `max_ai_tokens`/`max_usd`/`max_configs` with safe defaults + hard clamps (mirror
  `HARD_MAX_ITERATIONS`); zero/negative caps → safe default, still hard-bounded.
- Budget-exhausted terminal: on any hard cap → existing terminal state,
  `stopReason="budget-exhausted"`, no further iteration/config appended; recorded spend
  (tokens, USD, configs run) written into the durable `autoRun` block via the existing
  `_update_autorun` (no parallel store, no schema fork) — survives worker restart + browser
  reload, readable from `GET /api/sessions/{id}` (still lazy).

**Frontend (`apps/frontend`)**
- Additive spend readout in the existing `AutoRunBar` (`SessionContainer.tsx:31`): show
  recorded tokens / USD / configs-run and make `budget-exhausted` clearly legible, reading
  the new fields on the polled durable `autoRun` block. Plumb the new field(s) through
  `useBacktest.ts`/`sessionApi.ts` only if required. **No** new page/panel/leaderboard, no
  redesign. The iter-2 live-poll `try/finally` re-arm semantics and the J-02 heavy-detail
  merge precedence MUST remain byte-unchanged.

## Mandatory Lessons (from `runs/.../state/lessons.md` — reviewer/QA/auditor enforce)
- **iter-2 (CRITICAL, directly flagged for iter-3):** every backtest MUST keep flowing
  through the existing `_subprocess_backtest_executor` seam (`auto_session.py:188-289`,
  injected at `:956`). ≥2 configs multiplies CPU-bound backtests + LLM calls — MUST NOT
  reintroduce event-loop blocking. The non-blocking regression guard MUST stay
  **deterministic** (`child_pid != os.getpid()`), NEVER a timing bound. New per-round LLM
  work (usage capture) must be network-I/O off the event-loop thread.
- **iter-2 frontend:** any live-poll/`setTimeout`-chain change re-arms in a `finally`,
  never only on success (the AutoRunBar-freeze root cause).
- **iter-1/iter-0:** `AutoRunBar` must authoritatively re-derive per-session `autoRun` on
  mount/switch (no stale terminal — J-08); selecting a prior run re-binds the RIGHT
  analysis panel (trades/equity/WF), not just the left summary (J-02). The additive change
  MUST NOT regress either.

## Agents Required
- developer: **yes** — backend (controller + cost tracker + usage capture + price table +
  request/budget fields + 422-gate relaxation) and frontend (additive `AutoRunBar` spend
  readout). Single TDD developer pass covers both; backend is the dominant surface.
- Full 11-step pipeline (audit + ux-regression + closure) — depth=full, ~14 strong
  anti-goals activated with J-07–J-11 regression exposure.

## Frontend Present
yes

## Files to Create/Modify
- `apps/backend/backend/auto_session.py` — relax 422 gate; `AutoSessionRequest`
  `objective`/`history_scope`; `AutoSessionBudget` `max_ai_tokens`/`max_usd`/`max_configs`
  + clamps; bounded seed-universe constant; open-universe config-search controller
  (multi-config loop reusing the subprocess seam + `select_best` + `_build_node`);
  immutable cost-tracker integration; budget-exhausted terminal + durable spend write.
- `apps/backend/backend/cost_tracker.py` (likely **NEW**) — immutable monotonic tracker
  (caps fixed at construction; per-cap `would_exceed`/stop). Developer's class shape.
- `apps/backend/shared/model_catalog.py` (or sibling constant module) — static per-model
  input/output USD-per-token table; unknown-model-safe lookup. NOT `contracts.py`.
- `apps/backend/strategy/compiler.py`, `strategy/insights_generator.py`,
  `strategy/script_generator.py` — surface the already-read `.usage` (return/accumulator;
  no behavioural change to compilation/insights/codegen).
- `apps/backend/backend/pipeline.py` — thread captured usage through pipeline-level
  (non-frozen) return values ONLY (`generate_strategy`/`generate_insights`); NO engine /
  sandbox / orchestration / `execute_backtest`-internals change.
- `apps/backend/tests/test_auto_session.py` — extend (do not duplicate): open-universe
  accepted + ≥2 distinct configs; pinned still validates; bad objective→422; malformed→422
  not 500; immutable tracker (monotonic, caps fixed, per-cap stop, real-usage-fed guard);
  deterministic child-pid non-blocking guard for the multi-config run; robust-best across
  configs; durable spend survives simulated restart; regression guards green.
- `apps/backend/tests/` — new `test_cost_tracker.py` / `test_model_pricing.py` as needed.
- `apps/frontend/src/components/SessionContainer.tsx` — additive spend readout in
  `AutoRunBar`; `budget-exhausted` legibility.
- `apps/frontend/src/hooks/useBacktest.ts`, `src/lib/sessionApi.ts` — pass the new spend
  field(s) through ONLY if required; iter-2 `try/finally` poll + J-02 merge byte-unchanged.

## UI Evolution
- New user-facing capability: start a fully headless strategy *search* with one API call
  supplying only an objective + budget (no symbol/timeframe); watch ≥2 distinct configs
  explored live in the existing UI; see the robust-best marked and exactly how much
  AI-token/USD/config budget was spent, with a guaranteed hard stop.
- New information displayed: in the existing `AutoRunBar` — recorded AI-token / USD /
  configs-run spend and a clear `budget-exhausted` terminal reason; in the existing
  iteration tree — the ≥2 explored configs as iterations with the existing `BestBadge`.
- New user actions: none net-new (open-universe is API-triggered `POST /api/auto-sessions`;
  existing start/stop/observe + discovery poll unchanged).
- UI surface changes: no new pages/panels — one additive readout inside `AutoRunBar`.
- Navigation changes: none.

## Visual Requirements
- Component patterns: reuse the existing `AutoRunBar` strip and existing `BestBadge`
  (no new component); spend rendered as a compact inline readout consistent with the
  current bar's status/iteration text.
- Layout: unchanged two-panel session view; the spend readout sits inside the existing
  `AutoRunBar` strip — no new layout region.
- Key visual effects: match the existing `AutoRunBar` styling (dense, dark, data-forward);
  no new effects; `budget-exhausted` visually distinct from `criteria-met`/`stopped`.
- States to handle: running (spend accumulating, may be partial), terminal
  `budget-exhausted` (final spend ≤ cap, clearly legible), spend fields absent on legacy/
  pinned sessions (graceful — no NaN/`undefined` render, bar unchanged for old sessions).

## Key Test Scenarios
- **J-12 (browser):** `POST /api/auto-sessions` with only `objective:"robust"` + tiny
  `budget` (no symbol/timeframe) → 200; session opens in the UI; **≥2 distinct configs
  (differing symbol and/or timeframe)** appear as iterations; terminal within budget; the
  robust `BestBadge` is marked.
- **J-13 (browser):** tiny token/USD budget → terminal `stopReason="budget-exhausted"`;
  recorded spend ≤ cap (one-call tolerance) and **visible in `AutoRunBar`/status**; **no**
  iteration appended after the cap.
- **Regression (browser):** J-08 (rapid session switch on a fresh still-running
  open-universe session → "running", not stale terminal; list spinner + `AutoRunBar`
  agree) and J-02 (open a prior run → trades + equity + WF re-bind in the RIGHT panel).
- **Unit/integration (assert exact values, no skip/xfail):** open-universe accepted (not
  422) → ≥2 distinct `(symbol,timeframe)` iterations; pinned still validates/behaves
  exactly as before; non-`"robust"` objective → 422; malformed → 422 not 500. Immutable
  tracker: spend monotonic; caps fixed at construction (mid-run lower/raise no-ops);
  token / USD / max-configs / wall-clock caps fire independently; on cap →
  `budget-exhausted`, no post-cap config, spend persisted in durable `autoRun` and
  survives a simulated restart (re-read meta). **Real-usage guard:** tracker accumulates
  the token counts actually returned by the fake SDK usage flowing the production capture
  path — MUST fail if usage is bypassed/hardcoded (iter-2 false-guard generalization).
  **Deterministic non-blocking guard:** each multi-config backtest ran in a child process
  (`child_pid != os.getpid()`) via the subprocess seam — fails if forced in-process; NO
  timing bound. **Robust best across configs:** `bestIterationId` = robust winner; a
  higher-raw-return WFE-failing/over-leveraged config is NOT best. Regression guards green:
  pinned J-07–J-11; durable `autoRun` survives restart/reload; `GET /api/sessions/{id}`
  still lazy; `contracts.py`/sandbox/engine byte-unchanged; no secrets in artifacts/log.
- **Error cases:** unsupported objective → 422; malformed budget/dates → 422 (never 500);
  unknown model in price table → token cap still binds (no crash); zero/negative caps →
  safe default (still hard-bounded).
- Baseline to preserve: full backend suite **150 passed, 1 failed**; the ONLY tolerated
  failure remains the pre-existing out-of-scope
  `test_directions_cache.py::test_write_and_read_full_round_trip`. **Zero new
  regressions.** Frontend `npm run build` EXIT 0.

## Out of Scope (exclude — flagged to prevent scope creep)
- J-14 (SCREEN→PROMOTE / cheap-first routing) — every explored config runs the existing
  full pipeline incl. walk-forward; do NOT add a SCREEN/PROMOTE stage.
- J-15 (global-history warm start, bandit/LLM planner, prompt-cached planner context,
  `history_scope` *learning*) — `history_scope` accepted & persisted only; the controller
  is a deterministic enumerator adding NO uncached per-round LLM history/planner context;
  no cross-run mutation/read.
- J-16 (deep overfit-gating *demonstration* / leaderboard UI) — robust selector reused
  as-is; no leaderboard built.
- Any change to `shared/contracts.py`, the RestrictedPython sandbox, the deterministic
  next-bar engine, backtest/fills/metrics internals, or `BacktestPipeline` orchestration
  (usage *capture* allowed; engine bypass is not).
- Any new datastore/queue/scheduler/broker/vector-store; any session-store schema fork.
- Re-implementing/re-tuning the robust objective / `select_best`.
- The carried-forward stop-endpoint pickle-trim micro-optimization (tracked,
  non-blocking) — only touch if trivially adjacent, else leave for a later iteration.
- Cosmetic `AutoRunBar` redesign beyond the additive spend readout.

## Assumptions (documented per token policy — not blocking)
- Seed universe, default open-universe date window, usage-plumbing shape, cost-tracker
  class shape, and `AutoRunBar` spend layout are the developer's to choose within the
  constraints above (the spec explicitly delegates these).
- `test_auto_session.py` `FakePipeline` is extended with deterministic fake SDK `.usage`
  so the real-usage capture path is exercised without live LLM calls (tiny-budget mandate).
- Definition of Done also requires: dev handoff at
  `docs/handoffs/goal-auto-money-printer-iter-3-dev.md`; all 6 UI visibility artifacts;
  phase-closure gate passes.
