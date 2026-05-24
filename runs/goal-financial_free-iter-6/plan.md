# goal-financial_free-iter-6 Execution Plan

> **RE-LAND of J-15** (global-history warm start, opt-out-able). Iter-5 built this fully
> green in an `isolation: worktree` copy that was discarded without merging — the working
> tree has **zero** J-15 code (verified this iteration: `git diff HEAD -- apps/` empty,
> `history_planner.py` absent, no `history_scope`/`mine_history_families`/`plan_warmstart`
> match in `apps/`, no iter-5 handoff). Rebuild from this spec; do **not** hunt the lost code
> or cherry-pick the different-lineage `auto-money-printer` dangling commits.
>
> **The single reason iter-5 failed was non-persistence. DoD-0 (Persistence Gate) is the
> load-bearing exit criterion — see Key Test Scenarios #0.** A green pytest cache is NOT
> evidence the code landed. If work is done in a worktree, it MUST be merged back into the
> pipeline working tree before the persistence gate is checked.

## What to Build

- **Request + config plumbing.** Add `history_scope: Optional[str]` to `CreateAutoSessionRequest`
  (`auto_session_routes.py:77`), validated to `{"global","this-run"}`, **default `"this-run"`**
  (the opt-out / today's behavior). Reject any other value with **422** + clear message. Thread
  through `_build_config` (`auto_session_routes.py:178`) → a new `history_scope: str = "this-run"`
  field on the frozen `AutoSessionConfig` dataclass (`auto_session.py:332`). The pinned path
  (`_run_inner`, `auto_session.py:722`) ignores it.
- **Read-only history miner** (`mine_history_families(...)` in `auto_session.py`, or a small new
  `backend/history_mining.py`). Using ONLY existing read APIs (`session_store.derive_session_tabs`,
  `read_session_meta`, lightweight `read_iteration_meta` — **never** `read_iteration_full`), scan
  prior **completed** sessions (exclude the current in-flight session) into a per-`(symbol,timeframe)`
  family leaderboard. Each family's strength = **max of the one `RobustScorer.score(...)`**
  (`auto_session.py:242`) over that family's stored iteration meta (`totalReturn`, `sharpe`,
  `numTrades`, `maxDrawdown`, `wfe` from `walkForwardResult` when present). MUST be read-only
  (no write/mutate/delete of any prior artifact) and meta-only (no eager `result.json`/`rating.json`
  parse — iter-0 lesson). Reuse the single `RobustScorer`; do NOT add a second scoring path.
- **Cached LLM-planner** — new `apps/backend/strategy/history_planner.py` mirroring `InsightsGenerator`
  (`insights_generator.py:66` — `last_usage: Optional[TokenUsage]`, system prompt carrying
  `cache_control: {"type":"ephemeral"}` exactly as `insights_generator.py:357`). Invoked through
  the shared `BacktestPipeline` as `pipeline.plan_warmstart(...) -> (plan, TokenUsage)` with
  `pipeline.last_planner_usage` exposed (mirror `generate_insights` / `last_insights_usage` at
  `pipeline.py:746/790`). Given the mined family-leaderboard summary, returns a prioritized ordering
  over the **bounded seed families** + a one-line rationale citing a concrete prior session / family /
  metric. Called **at most once per run** (before SCREEN). **Best-effort:** on ANY failure (no key,
  error, malformed output) fall back to the **deterministic** mined-family ordering (sorted by
  historical score) — warm-start still works without the LLM and the loop never crashes. Planner
  token usage threaded into the budget via `_account_usage(pipeline.last_planner_usage)`
  (`auto_session.py:548`) (J-13).
- **Warm-start ordering in `_run_open_universe`** (`auto_session.py:835`). When
  `config.history_scope == "global"`: mine history (read-only); if ≥1 prior family exists, run the
  planner; emit **ONE** warm-start planner-decision Activity-Log entry (existing `auto-run` type,
  via `_append_activity`) citing the prior session's performance (e.g.
  `WARM-START — prioritizing BTC/USDT 1h (prior session …: robust score +0.42)`), **no secrets**;
  build `seed_configs` so the historically-strongest in-seed family is **first** (still strictly from
  the bounded seed — `SEED_SYMBOLS`/`SEED_TIMEFRAMES`/`SEED_UNIVERSE_MAX` unchanged; reprioritize
  WITHIN the seed, NEVER fan out); rank SCREEN survivors for PROMOTE by `(history_priority, screen_score)`
  so the historically-strongest screened family is promoted first (`k = min(DEFAULT_PROMOTE_K, n_screened)`,
  `k < n_screened` preserved). Best stays `RobustScorer.select_best(promoted)` — unchanged, WFE-gated.
  When `history_scope == "this-run"` (default) — or any unexpected/None value reaching the controller
  (defense-in-depth) — **skip mining + planner + citation entirely** and keep today's deterministic seed
  ordering + SCREEN-score promotion ranking **byte-for-byte unchanged** (J-12/J-14 safety), never crashing.
- **Budget compliance.** The planner call counts against the immutable `BudgetTracker` (token/USD)
  **before** SCREEN; a pre-exceeded cap terminates `budget-exhausted` without starting SCREEN, exactly
  as today.

## Agents Required

- developer: **yes** — backend-only implementation (request plumbing, read-only miner, cached planner,
  warm-start ordering, budget threading) following TDD; writes hermetic tests (fake planner injected via
  the `app.state.auto_pipeline` test override that `_resolve_pipeline` already honors) and runs the
  persistence gate (DoD-0) **before** writing the handoff.
- backend-data: **yes**
- frontend-ux: **no** (zero new FE code — see Frontend Present)

## Frontend Present

no

> **Justification (spec-mandated, not a shortcut).** J-15's only user-visible surface is a new
> **warm-start planner-decision Activity-Log entry** that reuses the **existing `auto-run` entry type
> and its existing render branch** — the exact path J-14's SCREEN/PROMOTE entries already use. There is
> **no new component, page, panel, button, or render branch** to build. `history_scope` is a new optional
> field on the existing `POST /api/auto-sessions` request (no new screen). No `shared/contracts.py` change,
> no new served/displayed value, no nav/blueprint change. The display aspect is proven at the **endpoint
> layer** (`GET /api/sessions/{id}` → `activityLog` — the canonical surface the UI polls), which is the
> documented Chrome-MCP headless-throttle substitute AND is sufficient because there is zero new render
> path. A single best-effort browser pixel capture is **explicitly NON-BLOCKING** and MUST NOT gate J-15.
> Per lessons iter-2/3/4, the recurring "pixel debt" has a `browser-qa-phase.sh` frontend-lifecycle root
> cause (health-probes `:3000` while `./scripts/dev.sh` binds an offset port, e.g. `:3692`) — a separable
> harness fix, NOT this product change; **do not carry a 5th pixel-debt instruction.**

## Files to Create/Modify

- `apps/backend/strategy/history_planner.py` — **NEW.** Cached LLM-planner (mirror `InsightsGenerator`:
  `last_usage`, ephemeral `cache_control` system prompt). Given the mined family-leaderboard summary,
  returns a prioritized seed-family ordering + one-line rationale; deterministic fallback on any failure.
- `apps/backend/backend/pipeline.py` — **MODIFY.** Add `plan_warmstart(...) -> (plan, TokenUsage)` and
  expose `last_planner_usage` (mirror `generate_insights` / `last_insights_usage`).
- `apps/backend/backend/auto_session.py` — **MODIFY.** Add `history_scope: str = "this-run"` to frozen
  `AutoSessionConfig` (:332); add `mine_history_families(...)` read-only miner (or import from
  `history_mining.py`); add the `global` warm-start branch in `_run_open_universe` (:835) — mine → plan
  → one `auto-run` citation entry → reorder `seed_configs` within the bounded seed → `(history_priority,
  screen_score)` PROMOTE ranking → `_account_usage(last_planner_usage)` (:548). `this-run`/None path
  unchanged.
- `apps/backend/backend/auto_session_routes.py` — **MODIFY.** Add validated `history_scope` to
  `CreateAutoSessionRequest` (:77, 422 on invalid, default `"this-run"`); thread through `_build_config` (:178).
- `apps/backend/backend/history_mining.py` — **NEW (optional).** Only if the miner is extracted into its
  own small module instead of living in `auto_session.py`; developer's choice per spec.
- `apps/backend/tests/test_history_warmstart.py` (or similarly named) — **NEW.** J-15 hermetic tests
  (inject a fake planner via the `app.state.auto_pipeline` override). **Do NOT** recreate the lost iter-5
  test names — several encoded the OPPOSITE default (omitted→global); write tests to **this** spec
  (default `this-run`).
- `runs/goal-financial_free-iter-6/status.json` — developer records `changed_files` (non-empty) and
  `tests_run: true` (part of the persistence gate).
- `docs/handoffs/goal-financial_free-iter-6-dev.md` — **NEW.** Dev handoff; "Files Changed" list MUST
  match `git diff --name-only HEAD -- apps/`.

**Out of bounds (must NOT appear in the diff):** `apps/backend/shared/contracts.py` (frozen);
`apps/frontend/**` (zero new FE code); the SCREEN/PROMOTE staging mechanics, `RobustScorer`,
`BudgetTracker`, or the best-marking definition (reuse, don't fork); any new datastore/index/queue/
scheduler.

## Anti-Goal & Coherence Guardrails (verify in review/QA)

- Read-only mining — prior-session artifacts byte-identical before/after a `global` run; meta-only reads.
- Prompt-cache marker present; planner invoked **≤ once per run** (call count == 1 for `global`, == 0 for
  `this-run`); leaderboard/history never re-sent uncached each round.
- Opt-out honored — `this-run` (and omitted default) produces NO cross-run citation; deterministic order.
- Bounded seed preserved — never enumerate a `(symbol,timeframe)` outside the seed; never exceed
  `SEED_UNIVERSE_MAX`.
- Exactly **one** `RobustScorer` and **one** `BudgetTracker` drive scoring/budget — no second scoring or
  best-definition path (re-confirmed coherence gate).
- No secrets (`api_key` / `sk-`) in the activity log or persisted artifacts.
- Same file store, no new infra; event loop stays non-blocking (one-backtest-per-worker semaphore).

## Goal Alignment

Advances `docs/goal.md` success criterion: *"A second automated run with global history scope demonstrably
warm-starts from prior sessions (prioritizes historically strong families) and is opt-out-able."* J-15 is one
of only two must-have journeys still failing; landing it green **and persisted** leaves only **J-16**
(overfit-gating leaderboard UI) before GOAL_ACHIEVED. The spec does **not** drift from or contradict the goal;
the blueprint Data-Contract row 74 already pre-registers this exact warm-start (contract-ahead-of-code), so
**no blueprint edit and no re-approval are required** — landing the code resolves the iter-5 COHERENCE-WARN by
making code match the already-approved contract.

## Key Test Scenarios

- **#0 — PERSISTENCE GATE (run FIRST; gates everything; the sole reason iter-5 failed).**
  `git diff --stat HEAD -- apps/backend/` is **non-empty** and includes all four:
  `apps/backend/strategy/history_planner.py` (new), `apps/backend/backend/auto_session.py` (modified),
  `apps/backend/backend/auto_session_routes.py` (modified), and the new J-15 test file(s).
  `test -f apps/backend/strategy/history_planner.py` succeeds; `grep -rl history_scope apps/backend/backend/`
  returns matches. `runs/goal-financial_free-iter-6/status.json` has non-empty `changed_files` +
  `tests_run: true`. Dev handoff exists with a "Files Changed" list matching `git diff --name-only HEAD -- apps/`.
  **Downstream review/QA/audit MUST treat an empty `apps/` diff as an automatic FAIL and MUST NOT trust the
  handoff or a pytest cache over the actual tree.**
- **J-15 (endpoint-layer proof accepted).** With a seeded prior run, a `history_scope: "global"` run's
  `GET /api/sessions/{id}` → `activityLog` contains a planner-decision entry citing prior-session performance,
  AND its first PROMOTEd iteration's `params` `(symbol,timeframe)` family == the prior run's top performer; a
  `history_scope: "this-run"` run contains NO such cross-run citation (opt-out honored).
- **No-regression (hermetic, MUST pass unchanged — they set no `history_scope`):** J-12 (≥ 2 distinct
  bounded-seed configs), J-13 (token/USD/`max_configs` hard-enforced), J-14 (cheap-no-WF SCREEN, `k < n_screened`
  PROMOTE, WFE-gated best from promoted only). `this-run` / omitted-default SCREEN ordering + promotion ranking
  are **byte-equivalent** to current deterministic behavior.
- **Read-only mining:** prior sessions' `session.json`, `meta.json`, and iteration files byte-identical before
  vs after a `global` warm-start run.
- **Prompt caching:** planner request carries `cache_control: {"type":"ephemeral"}`; call count == 1 (`global`),
  == 0 (`this-run`).
- **Planner failure non-fatal:** a raising/empty planner falls back to the deterministic mined-family ordering
  and the run still reaches a terminal state.
- **Budget (J-13):** planner token usage accumulated into `BudgetTracker`; a pre-exhausted token/USD budget
  terminates `budget-exhausted` **before** SCREEN.
- **Bounded seed:** a `global` run never enumerates a `(symbol,timeframe)` outside the seed and never exceeds
  `SEED_UNIVERSE_MAX`.
- **Coherence:** exactly one `RobustScorer` instance + one `BudgetTracker` drive scoring/budget.
- **Secrets:** planner activity entry + persisted artifacts contain no `api_key` / `sk-` material.
- **Error cases:** `history_scope` outside `{"global","this-run"}` → **422**; `global` with an empty store
  (no prior sessions) degrades gracefully — no citation, deterministic ordering, no crash, terminal state.
- **Suite health:** full hermetic backend suite green **except** the single known pre-existing red
  `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (untouched, out of scope).
- **Live (key-gated, OPTIONAL, one cheap run pair):** seed run #1 (`this-run`/default, tiny budget) → run #2
  (`global`) → run #3 (`this-run`). **Use a date range ≥ 9 months** (≥ `IS_months + OOS_months` at the 6/3
  defaults) so the PROMOTE walk-forward forms ≥ 1 window and the promote→best path is not vacuous (iter-4
  lesson). Confirm run #2 cites run #1 + first promoted family matches; run #3 shows no citation.

## Assumptions (documented, not blocking)

- **Default `this-run` (warm-start opt-IN via `global`)** per the spec and iter-5 re-land instruction. J-12/J-13/J-14
  hermetic tests issue open-universe runs WITHOUT a `history_scope` field, so the opt-out default keeps them
  byte-for-byte green; J-15 acceptance triggers warm-start by explicitly setting `global` (run #2) and opts out
  with `this-run` (run #3) — the omitted default is not exercised by J-15 acceptance.
- **First-promoted-family robustness:** with `DEFAULT_PROMOTE_K = 1`, only the top-ranked SCREEN survivor is
  promoted; the `(history_priority, screen_score)` PROMOTE ranking under `global` makes the historically-strongest
  *screened* family win promotion. Best-marking stays WFE-gated among promoted (a history-prioritized promote that
  fails WFE is simply not marked best — correct, and does NOT fail J-15, which is about promotion *selection*).
- **Pixel capture is non-blocking** and the browser-qa harness FE-lifecycle issue is a separable maintainer fix —
  not in scope and not a gate.
