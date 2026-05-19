# Goal Iteration 3 — Optimizer Foundation: open-universe search + hard cost budget

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** auto-money-printer
- **Iteration:** 3
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes
- **Target journeys:** J-12, J-13
- **Required-still-passing journeys:** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09, J-10, J-11
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify.
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - Identical generated strategies (by code hash) MUST NOT be re-generated or re-backtested; the OHLCV Parquet cache MUST be reused across configs (no re-fetch when a covering cache exists).
  - Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are reserved for promoted candidates.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - The automated-session `autoRun` status MUST be persisted to the durable store and survive a worker restart and a browser reload; it MUST NOT live only in browser memory or a non-persisted in-process variable.
  - The LLM-planner / history context MUST use prompt caching; the leaderboard/history MUST NOT be re-sent uncached every round.
  - Global history learning MUST be read-only mining of the existing store (it MUST NOT mutate or delete prior sessions' artifacts); the `history_scope` opt-out MUST be honored.
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.
  - The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
  - `BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart.
  - No nondeterministic backtests (slippage is seeded; identical inputs → identical output).
  - The RestrictedPython sandbox MUST block file I/O, network, `exec`/`eval`, `__import__`, `open`, and `os`; no lookahead; no hard-coded credentials/keys/tokens in source.

## GOAL

One API call with **no symbol/timeframe** — only an objective and a budget —
starts a headless session that explores **multiple distinct configs** from a
bounded seed universe, runs server-side to a terminal state strictly within a
**hard AI-token/USD/max-configs/wall-clock budget enforced by an immutable cost
tracker**, marks the best by the existing robust objective, and shows the
explored configs + the recorded spend live in the existing UI.

## BACKGROUND

Layer-1 Foundation (J-07–J-11) is closed and hardened: `POST
/api/auto-sessions` drives a durable, stoppable, backend-owned, event-loop-safe
**pinned-config** loop. This iteration opens Layer-2 (Optimizer) with its
indivisible foundation slice: **J-12** (open-universe — explore ≥2 distinct
configs from only an objective + budget) and **J-13** (the hard, immutable
AI-token/USD + max-configs + wall-clock cost tracker).

These two are paired deliberately and are not separable: the moment
open-universe exploration lands, the goal's strongest budget anti-goal is
*activated* — an open universe with only `max_iterations`/wall-clock (all that
exists today) would be an immediate, unbounded-cost anti-goal exposure.
Shipping J-12 without J-13 is not responsible. This mirrors the iter-1 pattern
the evaluator praised: land the indivisible vertical slice, harden the rest in
later iterations. The prior evaluator explicitly recommended iter-3 at **full**
depth "starting with the Optimizer Foundation: J-12 … and J-13".

J-14 (staged SCREEN→PROMOTE), J-15 (global-history warm start + prompt-cached
planner + `history_scope` learning), and J-16 (the deep robust-overfit-gating
stress demonstration over the open universe) are explicitly **later
iterations** and are OUT OF SCOPE here.

**Lessons that MUST be applied this iteration (from `lessons.md`):**

- **iter-2 lesson — DIRECTLY flagged as applying to iter-3 J-12–J-16.** A
  timing-based "event loop not blocked" guard is a FALSE guard (`time.sleep`
  releases the GIL; a thread-offloaded RestrictedPython backtest still holds
  the API worker's GIL during a *continuous* server-side loop and starves every
  other file-IO request). The correct, already-shipped fix is real process
  isolation via `_subprocess_backtest_executor` (a `spawn` child running the
  unmodified `BacktestPipeline`), guarded **deterministically** by asserting
  `child_pid != os.getpid()` — never by a timing bound. J-12 multiplies the
  per-run work (≥2 configs ⇒ more CPU-bound backtests + more LLM calls), so
  this iteration MUST keep every backtest flowing through the existing
  subprocess seam and MUST NOT reintroduce event-loop blocking; the
  non-blocking regression guard MUST stay deterministic (child-pid assertion),
  not timing-based. Any new per-round/per-config LLM work (token-usage capture,
  any planner) must be network-I/O off the event-loop thread, never CPU work on
  it. Separately: any frontend live-poll / `setTimeout`-chain change must
  re-arm in a `finally`, never only on the success path (the iter-2 AutoRunBar
  freeze root cause) — relevant to the small `AutoRunBar` spend-display change.
- **iter-1 / iter-0 lessons (protect required-still-passing J-08 / J-02).**
  The in-session `AutoRunBar` must authoritatively re-derive per-session
  `autoRun` status on mount/switch (no stale terminal); selecting a prior run
  must re-bind the RIGHT analysis panel (trades/equity/WF), not just the left
  summary. Both are passing and required-still-passing; the small additive
  `AutoRunBar` change in this iteration MUST NOT regress either.

## Current code state (grounding — verified before writing this spec)

- **Open-universe is hard-422-rejected today.** `apps/backend/backend/auto_session.py:884-904`
  (`create_auto_session`) builds `missing = [symbol, timeframe, start_date,
  end_date]` and raises `HTTPException(422, "Open-universe search (omitting
  symbol/timeframe) is not yet supported.")`. This gate must be **relaxed for
  the open-universe path** (objective present, symbol/timeframe omitted) while
  the pinned path keeps its existing validation.
- **No open-universe controller / seed universe / config search exists.** The
  loop `_run_auto_session_impl` (`auto_session.py:546-786`) runs ONE pinned
  config `max_iter` times, only refining the NL prompt from prior suggestions.
- **No AI-token / USD / cost accounting exists.** Budget is `max_iterations` +
  optional `max_wall_clock_seconds` only (`AutoSessionBudget`
  `auto_session.py:308-314`; `_resolve_budget` `:398-414`; `HARD_MAX_ITERATIONS
  = 50` `:63`). The "no one more round past the cap" check pattern is
  `auto_session.py:591-613`.
- **Real LLM token usage is available but discarded.** The SDK `.usage` object
  is read and `logger.info`-logged then dropped at
  `apps/backend/strategy/compiler.py:287-310`,
  `apps/backend/strategy/insights_generator.py:327-334` (OpenAI) and `:359-372`
  (Anthropic, incl. `cache_read_input_tokens`/`cache_creation_input_tokens`),
  and the same pattern in `apps/backend/strategy/script_generator.py`.
  `BacktestPipeline.generate_strategy` (`pipeline.py:277-289` →
  `GenerateStrategyResult` `:380-387`) and `generate_insights`
  (`pipeline.py:736-754` → `(summary, suggestions, errors)`) return **no**
  usage. `GenerateStrategyResult` is a pipeline-level (NOT frozen-contract)
  type.
- **No USD price table exists anywhere.** `shared/model_catalog.py` `ModelInfo`
  is `id/label/provider/default` only (`:16-37`). `model_catalog.py` is the
  single source of truth for model config and is **not** the frozen
  `shared/contracts.py`.
- **Robust best-selection already exists and is correct.**
  `backend/robust_objective.py` `robust_score`/`targets_met`/`select_best`
  (WFE-gated, min-trades floor, drawdown/over-leverage penalised). The loop
  already calls `select_best(completed)` (`auto_session.py:736,774`). The
  multi-config run reuses this verbatim over **all** configs' `RobustInputs`.
- **Subprocess backtest isolation seam exists.** `_subprocess_backtest_executor`
  / `_run_backtest_in_subprocess` / `_BacktestWorker`
  (`auto_session.py:252-291`); injected by `create_auto_session`
  (`:956`); `None` ⇒ in-process (unit fakes). Must be reused unchanged.
- **Symbols/timeframes source.** Hardcoded lists in `backend/api.py` —
  `GET /api/symbols` `:874-914` (26 pairs) and `GET /api/timeframes`
  `:949-970` (6 entries). The seed universe is a **small bounded constant**,
  NOT this full 26×6 grid.
- **UI renders headless iterations indistinguishably; no new surface needed
  for J-12.** `IterationPanel.tsx` → `IterationTreeItem` → `IterationCard.tsx`
  render manual and auto iterations via the same path; `BestBadge`
  (`IterationCard.tsx:19-28`) marks the robust-best via `bestIterationId`. The
  durable `autoRun` block renders via `AutoRunBar` (defined in
  `SessionContainer.tsx`); `stopReason` (incl. `budget-exhausted`) already
  displays. Only a **small additive** spend readout is net-new frontend work.
- **session_store contract for persistence.** `read_session_meta` /
  `write_session_meta` (top-level merge) / `write_iteration` /
  `append_activity_entries`; the durable `autoRun` sub-dict is updated via the
  existing `_update_autorun` read-merge-write (`auto_session.py:432-457`).
- **Existing tests to extend, not duplicate.** `apps/backend/tests/test_auto_session.py`
  (26 passing) — `FakePipeline` `steps`-list harness, monkeypatched temp
  `session_store.BASE_DIR`, `CancellationToken`, deterministic subprocess
  guard. Full backend baseline: **150 passed, 1 failed** (the pre-existing,
  out-of-scope `test_directions_cache.py::test_write_and_read_full_round_trip`).

## IN SCOPE

### Backend

- [ ] **Request schema (no `shared/contracts.py` change).** Extend
      `AutoSessionRequest` so the J-12 shape validates: add `objective:
      Optional[str]` (default `"robust"`; v1 supports **only** `"robust"` —
      reject any other value with a clear 422, honoring the single-robust-scalar
      Non-Goal) and `history_scope: Optional[str]` (accepted & persisted; its
      cross-run *learning* behaviour is J-15 / OUT OF SCOPE — see below).
- [ ] **Relax the 422 gate for the open-universe path.** When `symbol`/
      `timeframe` (and optionally `start_date`/`end_date`) are omitted and the
      request is a well-formed open-universe request (valid `objective`, valid
      `budget`), accept it and run the open-universe controller. The **pinned**
      path keeps its existing required-field validation and behaviour unchanged
      (J-07–J-11 must not regress). A malformed request still 422s cleanly
      (never a 500).
- [ ] **Bounded seed universe constant.** A small, hard-coded constant set of
      `(symbol, timeframe)` candidates (a handful of liquid pairs × a couple of
      timeframes — keep it tight, e.g. ≤ ~8 entries; NOT the full 26×6 grid,
      NOT env-driven, NOT a live exchange enumeration). Open-universe
      exploration draws **only** from this seed set this iteration.
- [ ] **Open-universe config-search controller.** Drive the existing
      generate→backtest(+WF)→insights→record path across **≥2 distinct configs**
      (differing symbol and/or timeframe) within **one** session, selecting
      configs **deterministically** from the bounded seed universe (a simple
      bounded enumerator — the history-surrogate/bandit + LLM planner is J-15 /
      OUT OF SCOPE). Each config's iteration is written via the existing
      `write_iteration`/`_build_node`/`append_activity_entries` path so a
      headless open-universe run is **UI-indistinguishable** from a manual run.
      The activity log MUST record each config explored (symbol/timeframe) so
      the exploration is visible/auditable. When `start_date`/`end_date` are
      omitted, use a **fixed deterministic short** historical window (tiny-budget
      rule) that the OHLCV Parquet cache can serve/cache.
- [ ] **Best across all configs by the existing robust objective.** Reuse
      `select_best`/`robust_score` over the combined `RobustInputs` of every
      completed config-iteration; `bestIterationId` is set/finalised by the
      robust objective only — never by raw return. (No new selection logic; the
      deep overfit-gating stress demonstration is J-16 / OUT OF SCOPE.)
- [ ] **Real AI-token usage capture.** Surface the **real** SDK `.usage`
      (OpenAI `prompt_tokens`/`completion_tokens`; Anthropic
      `input_tokens`/`output_tokens`) from the existing call sites
      (`compiler.py`, `insights_generator.py`, `script_generator.py`) up to the
      auto-session loop so the cost tracker accumulates **actual** tokens — not
      an estimate, not a hardcoded constant. Do NOT mutate `shared/contracts.py`
      and do NOT touch the sandbox / deterministic engine / backtest internals;
      thread usage through pipeline-level (non-frozen) return values or a
      lightweight accumulator passed into the LLM calls — developer's choice
      within these constraints.
- [ ] **Per-model USD price table.** A small constant input/output USD-per-token
      map keyed by model id (extend `shared/model_catalog.py` — the
      single-source-of-truth model-config module, NOT the frozen
      `shared/contracts.py`; or a sibling constant module). USD spend is derived
      from **real** captured token counts × this table. It is a static constant
      — NOT a paid pricing API / new SaaS dependency. Unknown model ⇒ the token
      cap remains binding (never crash).
- [ ] **Immutable hard cost tracker.** A small tracker whose accumulated spend
      is **monotonic / append-only** and whose caps are **fixed at run start**
      (cannot be raised mid-run). It enforces a hard ceiling on **all** of: AI
      tokens, USD, **max-configs**, and wall-clock — *plus* the existing
      `max_iterations` clamp (the loop is bounded even with no budget supplied;
      sane defaults + an absolute hard ceiling, mirroring `HARD_MAX_ITERATIONS`).
      The cap is checked **before** starting each config/round ("no one more
      round / one more config past the cap"); a single in-flight LLM call may
      marginally exceed (the goal's "within one-call tolerance"), but no new
      config/round starts once any cap is reached. `AutoSessionBudget` gains the
      corresponding optional fields (e.g. `max_ai_tokens`, `max_usd`,
      `max_configs`) with safe defaults + hard clamps.
- [ ] **Budget-exhausted terminal + durable, visible spend.** When any hard cap
      is reached the run reaches the existing terminal state with
      `stopReason="budget-exhausted"`, **no further iteration/config is
      appended**, and the recorded spend (tokens, USD, configs run) is written
      into the durable `autoRun` block via the existing `_update_autorun`
      mechanism (no parallel store, no schema fork) so it survives a worker
      restart and a browser reload and is readable from `GET /api/sessions/{id}`.

### Frontend

- [ ] **Small additive spend readout in the existing `AutoRunBar`.** Surface
      the recorded cost-tracker spend (tokens / USD / configs run) and make the
      `budget-exhausted` terminal reason clearly legible, reading the new fields
      already present in the durable polled `autoRun` block. This is the only
      net-new frontend work: additive, confined to the existing `AutoRunBar`
      (and its data plumbing in `useBacktest.ts` only if a new field must be
      passed through). **No** new page/panel/leaderboard; **no** redesign; the
      iter-2 live-poll `try/finally` re-arm semantics and the J-02 heavy-detail
      merge precedence MUST remain byte-unchanged.

### New user-facing capability

The user can start a fully headless strategy *search* with a single API call
that supplies only an objective and a budget (no symbol/timeframe), watch the
session explore ≥2 distinct configs live in the existing UI, see the best
config marked by the robust objective, and see exactly how much AI
token/USD/config/wall-clock budget was spent — with the run guaranteed to stop
at the hard cap.

### New information displayed

In the existing `AutoRunBar`: the recorded AI-token / USD / configs-run spend
for the auto-session and a clear `budget-exhausted` terminal reason. In the
existing iteration tree: the ≥2 distinct explored configs as iterations, with
the robust-best `BestBadge` (existing component, no change).

### New user actions

None net-new — open-universe is API-triggered (`POST /api/auto-sessions` with
only objective + budget); the existing UI start/stop/observe affordances and
discovery poll are unchanged.

### UI surface changes

No new pages or panels. One additive readout inside the existing `AutoRunBar`.

### Product surface delta

The automated chain graduates from "automate one pinned strategy" to "search a
bounded universe of configs under a hard, auditable cost budget" — the first
genuinely *optimizing* capability, with spend made transparent in the UI.

## OUT OF SCOPE

- **J-14** (staged SCREEN→PROMOTE / cheap-first model routing). This iteration
  has **no SCREEN stage**: every explored config runs the existing full
  pipeline incl. walk-forward (the robust objective needs WFE). Because no
  SCREEN stage exists yet, the "cheap SCREEN must not run WF/strong model"
  anti-goal is **not violated** — it is an un-built optimization, and total
  cost is still hard-bounded by J-13. Do NOT add a SCREEN/PROMOTE stage here.
- **J-15** (global-history warm start, history-surrogate/bandit planner,
  prompt-cached planner context, `history_scope` *learning*). `history_scope`
  is accepted & persisted but performs **no** cross-run learning this
  iteration; the controller is a deterministic bounded enumerator and adds
  **no** uncached per-round LLM history/planner context. Any history access in
  the future must be read-only — do NOT mutate/delete prior sessions here.
- **J-16** (the deep overfit-gating stress *demonstration* — a higher-raw-return
  WFE-failing/over-leveraged candidate visibly rejected in a leaderboard). The
  robust selector is reused as-is; a dedicated leaderboard UI is not built.
- Any change to `shared/contracts.py`, the RestrictedPython sandbox, the
  deterministic next-bar engine, the backtest/fills/metrics internals, or
  `BacktestPipeline`'s orchestration (token-usage *capture* is allowed; engine
  bypass is not).
- Any new datastore/queue/scheduler/broker/vector-store; any schema fork of the
  session file store.
- Re-implementing or re-tuning the robust objective / `select_best`.
- The carried-forward stop-endpoint pickle-trim micro-optimization (scalar
  result proxy across the child pipe) — tracked, non-blocking; only touch it if
  trivially adjacent, otherwise leave it for a later iteration.
- Cosmetic redesign of `AutoRunBar` beyond the additive spend readout.

## DEFINITION OF DONE

- [ ] **J-12** passes via browser-qa: `POST /api/auto-sessions` with **no**
      `symbol`/`timeframe` — only `objective:"robust"` + a tiny `budget` (and
      optionally `history_scope`) — returns 200; the session opens in the
      existing UI; **≥2 distinct configs (differing symbol and/or timeframe)
      appear as iterations**; the run reaches a terminal state within budget;
      the best is marked by the robust objective (`BestBadge`).
- [ ] **J-13** passes via browser-qa: a run with a tiny token/USD budget
      reaches a terminal state with `stopReason="budget-exhausted"`; the
      recorded token/cost spend is ≤ the cap (within one-call tolerance) and is
      **visible in the status block / `AutoRunBar`**; **no** iterations are
      appended after the cap is reached.
- [ ] Required-still-passing journeys J-01–J-11 remain green. Explicitly
      re-verify **J-07–J-11** (the pinned auto-session path through the
      heavily-edited `auto_session.py`), **J-08** (no stale `AutoRunBar`
      terminal; live poll still self-heals), and **J-02** (prior-run RIGHT
      analysis panel re-bind).
- [ ] No anti-goal violation introduced (see reminders) — verified at
      source-diff + test level, not from a report headline. In particular:
      bounded seed universe (no blind fan-out); immutable monotonic cost tracker
      with caps fixed at start; best by robust objective not raw return; backtest
      still in the subprocess seam (event-loop non-blocking, **deterministic**
      child-pid guard, not timing); Parquet cache reused across configs;
      `contracts.py`/sandbox/engine byte-unchanged; `autoRun` spend durable
      across restart+reload; no secrets in artifacts/activity log.
- [ ] Unit/integration tests pass; the existing `test_auto_session` suite stays
      green and is extended (see TESTING REQUIREMENTS); the only tolerated
      failure remains the pre-existing out-of-scope
      `test_directions_cache.py::test_write_and_read_full_round_trip`; **zero
      new regressions**.
- [ ] Dev handoff written at `docs/handoffs/goal-auto-money-printer-iter-3-dev.md`.
- [ ] All 6 UI visibility artifacts produced; phase-closure gate passes.

## TESTING REQUIREMENTS

All J-12/J-13 verification MUST use a **tiny budget** (≤ 2 screen iterations
per config, a short date range, the cheapest model, `max_configs: 2`, lenient
targets) per the goal's J-07–J-16 budget mandate — verification stays fast and
cheap.

- **Browser (named):**
  - **J-12** — `POST /api/auto-sessions` with only `objective:"robust"` + tiny
    `budget` (no symbol/timeframe) → open the created "Auto: …" session in the
    UI → confirm ≥2 distinct configs appear as iterations (differing symbol
    and/or timeframe, visible in the iteration tree / activity log), the run
    reaches terminal within budget, and the robust `BestBadge` is marked.
  - **J-13** — `POST /api/auto-sessions` with a tiny token/USD `budget` → wait
    for terminal → `AutoRunBar`/status shows `budget-exhausted` and a recorded
    spend ≤ cap (one-call tolerance); no iteration appears after the cap.
  - Re-verify **J-08** (open a freshly-started still-running open-universe
    session while switching sessions rapidly — status "running", not a stale
    terminal; session-list spinner and `AutoRunBar` agree) and **J-02** (open a
    prior run; trades table + equity curve + WF re-bind in the RIGHT panel).
- **Unit/integration (must have tests, assert exact values):**
  - Open-universe request (no symbol/timeframe, valid objective+budget) is
    accepted (not 422) and produces **≥2 distinct `(symbol,timeframe)`**
    iterations in one session; pinned requests still validate/behave exactly as
    before; `objective` other than `"robust"` → 422; malformed → 422 not 500.
  - **Immutable cost tracker:** accumulated spend is monotonic and caps are
    fixed at construction (attempting to lower/raise mid-run has no effect);
    `would_exceed`/stop fires on the **token**, **USD**, **max-configs**, and
    **wall-clock** caps independently; on cap → `stopReason="budget-exhausted"`,
    **no** post-cap iteration/config appended, spend persisted in the durable
    `autoRun` block and survives a simulated restart (re-read meta).
  - **Real-usage (not faked) guard** — analogous to the iter-2 false-guard
    lesson: the budget test MUST assert the tracker accumulated the **token
    counts actually returned by the (fake) SDK usage flowing the production
    capture path**, and MUST fail if usage capture is bypassed/hardcoded — not
    a number that passes by construction.
  - **Event-loop non-blocking stays deterministic:** the regression guard for
    the multi-config run asserts each backtest executed in a **child process
    (`child_pid != os.getpid()`)** via the existing subprocess seam — NOT a
    timing bound (iter-2 lesson). It must still fail if forced in-process.
  - **Robust best across configs:** with ≥2 completed configs, `bestIterationId`
    is the robust-objective winner; a higher-raw-return but WFE-failing /
    over-leveraged config is NOT marked best.
  - Regression guards stay green: pinned J-07–J-11 paths; durable `autoRun`
    survives restart/reload; `GET /api/sessions/{id}` still lazy;
    `contracts.py`/sandbox/engine unchanged; no secrets persisted.
- **Error cases (rejected/handled cleanly):** unsupported `objective` → 422;
  malformed budget/dates → 422 (never 500); unknown model in price table → token
  cap still binds (no crash); zero/negative caps treated as the safe default
  (still hard-bounded, never unbounded).

## NOTES

- **Depth = full** is mandated by the prior evaluator's explicit recommendation
  and the structural risk profile: a new config-search controller, a new
  immutable cost tracker, new request/budget fields, relaxing the 422 gate,
  a multi-config loop refactor of the heavily-load-bearing `auto_session.py`,
  cross-module real-token-usage plumbing, plus a small additive frontend
  change — activating ~14 strong anti-goals with J-07–J-11 regression
  exposure. Run the full 11-step pipeline (audit + ux-regression + closure).
- **J-12 + J-13 are an indivisible slice** — see BACKGROUND. Do not attempt to
  land open-universe without the hard cost tracker; that would itself breach
  the budget anti-goal the moment it ships.
- The robust selector, the subprocess backtest seam, the durable-`autoRun`
  mechanism, the cancellation/stop machinery, and the UI iteration-rendering
  path **already exist and are correct** — reuse them verbatim. Net-new work is
  the controller + cost tracker + usage capture + price table + the small
  spend readout. Resist re-implementing what iter-1/iter-2 landed.
- Skeptical-evaluation note for QA/reviewer/auditor: do not accept a reconciled
  `ui-test-results.md` headline at face value — cross-check the post-fix source
  diff and the QA MODE-2 report (iter-1 lesson); and verify the cost tracker is
  fed **real** captured SDK usage, not a constant that makes the budget test
  pass by construction (iter-2 false-guard lesson generalized).
- Implementation wiring (exact seed-universe entries, default open-universe date
  window, usage-plumbing shape, tracker class shape, `AutoRunBar` layout) is
  the developer's to decide within the constraints above; this spec fixes
  outcomes, anti-goals, and the mandatory lessons — not the micro-implementation.
