# Goal Iteration 6 — Re-land J-15: global-history warm start for the open-universe search (opt-out-able)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** financial_free
- **Iteration:** 6
- **Mode:** next
- **Depth:** full
- **Frontend Present:** no (backend-only; reuses the existing `auto-run` Activity-Log render path — zero new FE code)
- **Target journeys:** J-15
- **Required-still-passing journeys:** J-07, J-08, J-09, J-10, J-11, J-12, J-13, J-14 (J-12 / J-13 / J-14 are MOST-AT-RISK — this iteration edits `_run_open_universe`), plus J-01, J-02, J-03, J-04, J-05, J-06 (no-regression)
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - "Global history learning MUST be read-only mining of the existing store (it MUST NOT mutate or delete prior sessions' artifacts); the `history_scope` opt-out MUST be honored."
  - "The LLM-planner / history context MUST use prompt caching; the leaderboard/history MUST NOT be re-sent uncached every round."
  - "Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify."
  - "The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one."
  - "No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store."
  - "API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts."
  - "The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected)."
  - "Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take 'one more round' past the cap."
  - "The automated 'best' MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best."
  - "Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are reserved for promoted candidates."
  - "The frozen dataclasses in `shared/contracts.py` must not be mutated in place."
  - "`GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads."
  - Coherence gate (re-confirmed iter-2 / iter-4): there is exactly ONE `RobustScorer` and ONE `BudgetTracker`. History prioritization MUST reuse the one `RobustScorer`; it MUST NOT introduce a second scoring or best-definition path.

## GOAL

An open-universe automated run started with `history_scope: "global"` warm-starts from prior sessions: it mines the existing file store (read-only), emits a planner-decision Activity-Log entry citing a prior session's performance, and prioritizes the historically-strongest seed family so that family is screened first and is the first PROMOTEd config — while a run with `history_scope: "this-run"` (the default / opt-out) behaves exactly as today with no cross-run citation. **This code MUST land and persist in the working tree this iteration** (see the Persistence gate — iter-5 built this and lost it).

## BACKGROUND

J-15 is the last Layer-2 capability before the J-16 leaderboard UI. Of the 16 must-have journeys, only J-15 and J-16 remain failing; the iter-5 evaluator recommended **J-15 at full depth this iteration**, then J-16 next.

**This is a RE-LAND, not net-new design.** Iteration 5 fully built J-15 and its eight named tests ran **green** — but the work was done in an ephemeral `isolation: worktree` copy that was removed **without merging back**, so the working tree has **zero** J-15 code and the implementation is **not recoverable from git** (HEAD `4e999fb` is the iter-5 bookkeeping commit; `git diff HEAD -- apps/` is empty; the iter-5 snapshot differs from iter-4 by one telemetry line; the only `history_scope` in dangling commits belongs to the *abandoned, different-lineage* `auto-money-printer` session and MUST NOT be cherry-picked). Independently re-verified at the start of this iteration: a tree-wide grep of `apps/**.py` for `history_scope` / `mine_history_families` / `history_planner` / `plan_warmstart` / `WARM-START` returns **no source matches**, and `apps/backend/strategy/history_planner.py` does not exist. The design below is intact and proven coherent (COHERENCE-WARN at iter-5 was ONLY because the blueprint described J-15 while the code was absent — not a design problem). **Rebuild from this spec; do NOT hunt for the lost code.**

The implementation surface is unchanged from iter-4: `_run_open_universe` (`apps/backend/backend/auto_session.py:835`) orders the bounded seed configs **deterministically** (`seed_universe_configs`, `auto_session.py:386`), SCREENs them cheap on `cheapest_model()` (no walk-forward), ranks survivors by the one canonical `RobustScorer` (`auto_session.py:242`), PROMOTEs the top-`k` (`DEFAULT_PROMOTE_K = 1`, `auto_session.py:95`) on the stronger model + walk-forward, and marks best WFE-gated from the promoted set via `RobustScorer.select_best` (`auto_session.py:279`). J-15 replaces only the **ordering / promotion priority** with a history-informed plan when opted in; it does NOT change the staging mechanics, the scorer, the budget, or the best definition.

This is full depth: it adds a cross-session read surface, a new LLM-planner call (new failure modes), a prompt-caching requirement, and a new request field — beyond a browser smoke.

Lessons carried into this spec (from `lessons.md`, **Applies to** matched):
- **iter-5 (LOAD-BEARING — lost work):** "An iteration can finish 'green' in an isolated worktree and leave ZERO code in the real tree — a passing pytest cache is NOT evidence the work persisted." The fix that MUST be adopted: assert persistence before declaring done (`git diff HEAD -- apps/` non-empty + `status.json.changed_files` populated + `tests_run:true` + dev handoff present). This is now a hard gate — see DEFINITION OF DONE item 0 and TESTING. **If the harness loses this iteration's work the same way, that WOULD trip a STALL** — the persistence check is the difference between CONTINUE and ESCALATE.
- **iter-4 (live-QA recipe):** any walk-forward-dependent live QA MUST use a date range ≥ `IS_months + OOS_months` (≥ 9 months at the 6/3 defaults), or the PROMOTE walk-forward yields 0 windows → `wfe 0.0` → `best=None` and the promote→best path is silently vacuous. J-15's run-#2 promote→best path depends on WF, so its live QA MUST use a ≥ 9-month range.
- **iter-4 (harness, NOT effort):** the recurring "pixel debt" is a `browser-qa-phase.sh` frontend-lifecycle root cause (the dev server runs on a deterministic **offset** port, e.g. `:3692`, while the harness health-probes `:3000`), not agent effort. This spec formally adopts endpoint-layer proof for the display aspect (see DEFINITION OF DONE / TESTING); the pixel capture is best-effort, non-blocking. Do NOT carry a 5th "pixel debt" instruction.
- **iter-0 (no eager parse):** history mining MUST read the lightweight `read_iteration_meta` (meta: metrics + params) — NOT `read_iteration_full` result/rating payloads across many sessions.

## IN SCOPE

### Backend

- [ ] **Request + config plumbing.** Add `history_scope: Optional[str]` to `CreateAutoSessionRequest` (`apps/backend/backend/auto_session_routes.py:77`), validated to `{"global", "this-run"}`, **default `"this-run"`** (the opt-out value — preserves today's deterministic open-universe behavior so J-12 / J-13 / J-14 stay green; warm-start is explicitly opt-**IN** via `"global"`, matching J-15's journey "Run #2 with `history_scope: \"global\"`"). Reject any other value with a **422** and a clear message. Thread it through `_build_config` (`auto_session_routes.py:178`) → a new `history_scope: str = "this-run"` field on the frozen `AutoSessionConfig` dataclass (`auto_session.py:332`). The pinned (`_run_inner`, `auto_session.py:722`) path ignores it.
- [ ] **Read-only history miner.** A new helper (e.g. `mine_history_families(...)` in `auto_session.py`, or a small `backend/history_mining.py`) that, using ONLY existing read APIs (`session_store.derive_session_tabs`, `read_session_meta`, `read_iteration_meta`), scans prior **completed** sessions and builds a per-`(symbol, timeframe)` family leaderboard. Each family's historical strength is the **max of the one `RobustScorer.score(...)`** computed from each prior iteration's already-stored meta (`totalReturn`, `sharpe`, `numTrades`, `maxDrawdown`, and `wfe` from `walkForwardResult` when present) — reuse the single `RobustScorer`, do NOT add a second scoring path. It MUST NOT open/parse full `result.json` / `rating.json` payloads (read **meta only** — iter-0 lesson) and MUST NOT write, mutate, or delete any prior-session artifact (read-only). It MUST exclude the current in-flight session.
- [ ] **Cached LLM-planner.** A planner step (new `apps/backend/strategy/history_planner.py` mirroring `InsightsGenerator`'s structure — `last_usage: Optional[TokenUsage]`, prompt-cached system prompt — invoked through the shared `BacktestPipeline` as e.g. `pipeline.plan_warmstart(...)` returning `(plan, TokenUsage)` with `pipeline.last_planner_usage` exposed for budget accounting) that is given the mined family-leaderboard summary and returns a prioritized ordering over the **bounded seed families** plus a one-line rationale citing a concrete prior session / family / metric. The planner's system prompt MUST carry `cache_control: {"type": "ephemeral"}` (match `insights_generator.py:357`). It is called **at most once per run** (before SCREEN), so the leaderboard/history is never re-sent uncached each round. Planner token usage MUST be threaded into the budget via `_account_usage(pipeline.last_planner_usage)` (`auto_session.py:548`) (J-13). The planner MUST be best-effort: on ANY failure (no key, error, malformed output) fall back to the **deterministic** mined-family ordering (sorted by historical score) so warm-start still works without the LLM and the loop never crashes.
- [ ] **Warm-start ordering in `_run_open_universe`** (`auto_session.py:835`). When `config.history_scope == "global"`:
  - mine history (read-only) and, if at least one prior family exists, run the planner;
  - emit ONE warm-start planner-decision Activity-Log entry (existing `auto-run` type) whose content cites the prior session's performance (e.g. `WARM-START — prioritizing BTC/USDT 1h (prior session …: robust score +0.42)`), containing NO secrets;
  - build `seed_configs` ordered so the historically-strongest in-seed family is **first**, still drawn strictly from the bounded seed universe (`SEED_SYMBOLS` / `SEED_TIMEFRAMES` / `SEED_UNIVERSE_MAX` unchanged, `auto_session.py:79/87` — reprioritize *within* the seed, NEVER fan out);
  - rank SCREEN survivors for PROMOTE by `(history_priority, screen_score)` so the historically-strongest screened family is promoted first (with `k = min(DEFAULT_PROMOTE_K, n_screened)` and `k < n_screened` preserved). Best is still `RobustScorer.select_best(promoted)` — unchanged, WFE-gated.

  When `config.history_scope == "this-run"` (default) — or any unexpected/None value reaching the controller (defense-in-depth) — skip mining + planner + citation entirely and keep today's deterministic seed ordering and SCREEN-score promotion ranking (J-12 / J-14 behavior **byte-for-byte unchanged**), never crashing.
- [ ] **Budget compliance.** The planner call counts against the immutable `BudgetTracker` (token/USD) before SCREEN; if a cap is already exceeded the run terminates `budget-exhausted` without starting SCREEN, exactly as today.

### Frontend (if applicable)

- None. The warm-start planner-decision entry reuses the existing `auto-run` Activity-Log entry type and its existing render branch (the same path J-14's SCREEN/PROMOTE entries use). Zero new FE code, no new render path.

### New user-facing capability
A headless open-universe run can be told to learn from past runs: `POST /api/auto-sessions` now accepts `history_scope: "global"` (warm-start from prior sessions) or `"this-run"` (ignore history — the default / opt-out). With `global`, the session's Activity Log shows the planner's decision citing a prior session's result and the search spends its first expensive (PROMOTE) evaluation on the historically-strongest family.

### New information displayed
A new **warm-start planner-decision Activity-Log entry** (rendered through the existing `auto-run` entry path) citing the mined prior-session performance that drove the prioritization. No new numeric / served value.

### New user actions
`history_scope` is a new optional field on the existing `POST /api/auto-sessions` request (the IA already lists `history_scope` inputs under the Left-panel Automated-session controls). No new button / screen.

### UI surface changes
None beyond the new Activity-Log entry text (existing render path).

### Product surface delta
The optimizer becomes adaptive across runs: a second `global` run prioritizes families that performed well historically (visible as a cited planner decision), realizing the goal's "learns from prior sessions to spend tokens where payoff is highest." The opt-out (`this-run`) keeps each run independent and self-contained.

### Blueprint conformance
No new screen and no nav-skeleton change. J-15's canonical home already exists in `blueprint.md` Information Architecture ("J-15 Warm start from global history + opt-out → Activity Log planner-decision entries → Left — Activity Log"), and `history_scope` inputs are already listed under the Left-panel Automated-session controls. The blueprint's Layer-2 open-universe Data-Contract row (`blueprint.md:74`) **already** pre-registers this exact J-15 warm-start (read-only, prompt-cached, opt-out-able, one `RobustScorer` / one `BudgetTracker`, no new value/endpoint). **No blueprint edit and no re-approval are required this iteration** — the contract already describes the target state, and landing the code resolves the iter-5 COHERENCE-WARN (contract-ahead-of-code) by making code match contract.

### Data-contract additions
**None (no new served / displayed value).** The history leaderboard the planner mines is derived transiently, read-only, from records ALREADY in the Data Contract (the shared session / iteration records and `autoRun.bestIterationId`, served by `GET /api/sessions` / `GET /api/sessions/{id}`) — it is not a new persisted or served value; it surfaces only as cited text inside the existing `auto-run` Activity-Log entry. Any score the miner computes MUST come from the one registered `RobustScorer`.

## OUT OF SCOPE

- **J-16** multi-candidate overfit-gating leaderboard UI — the next (final) iteration. After J-15 lands green, J-16 is all that remains before GOAL_ACHIEVED.
- Any new datastore, index, vector store, queue, or scheduler for history — read-only mining of the existing file store ONLY.
- Expanding the seed universe beyond `SEED_UNIVERSE_MAX` — warm-start reprioritizes WITHIN the bounded seed; it never fans out exchange-wide.
- The pinned path (`_run_inner`) — J-15 is open-universe only; pinned runs ignore `history_scope`.
- Any change to `shared/contracts.py`, the SCREEN/PROMOTE staging mechanics, the `RobustScorer`, the `BudgetTracker`, or the best-marking definition.
- Multi-objective / Pareto optimization (single robust scalar objective remains).
- A `browser-qa-phase.sh` harness rewrite (framework tooling, separable — see NOTES; must NOT gate J-15).
- Hunting for / cherry-picking the lost iter-5 implementation or the `auto-money-printer` dangling commits — rebuild from this spec only.

## DEFINITION OF DONE

- [ ] **0. PERSISTENCE GATE (LOAD-BEARING — the single reason iter-5 failed; verify BEFORE writing the handoff).** The J-15 code MUST exist in *this* working tree, not only in a worktree or a green pytest cache:
  - `git diff --stat HEAD -- apps/backend/` is **non-empty** and includes `apps/backend/strategy/history_planner.py` (new), `apps/backend/backend/auto_session.py` (modified), `apps/backend/backend/auto_session_routes.py` (modified), and the new J-15 test file(s).
  - `test -f apps/backend/strategy/history_planner.py` succeeds; `grep -rl history_scope apps/backend/backend/` returns matches.
  - `runs/goal-financial_free-iter-6/status.json` has `changed_files` **non-empty** and `tests_run: true`.
  - The dev handoff at `docs/handoffs/goal-financial_free-iter-6-dev.md` exists and its "Files Changed" list matches `git diff --name-only HEAD -- apps/`.
  - **If any implementation work was done in an isolated worktree, it MUST be merged back into the pipeline's working tree before this gate is checked.** A green pytest cache is NOT evidence the code landed. Downstream review / QA / audit MUST treat an empty `apps/` diff as an automatic FAIL and MUST NOT trust the handoff or a pytest cache over the actual tree.
- [ ] **J-15 passes** (endpoint-layer proof accepted — see TESTING): with a seeded prior run, a `history_scope: "global"` run's Activity Log (`GET /api/sessions/{id}` → `activityLog`) contains a planner-decision entry citing prior-session performance, AND its first PROMOTEd iteration's `params` `(symbol, timeframe)` family matches the top performer of the prior run; a `history_scope: "this-run"` run contains NO such cross-run citation (opt-out honored).
- [ ] Required-still-passing journeys remain green — especially **J-12** (≥ 2 distinct configs from the bounded seed), **J-13** (token/USD/`max_configs` hard-enforced), **J-14** (SCREEN/PROMOTE staging: cheap-no-WF SCREEN, k < n_screened PROMOTE, WFE-gated best from promoted only). Their existing hermetic tests (which set no `history_scope`) MUST still pass **unchanged** under the new default.
- [ ] No anti-goal violation introduced (read-only mining verified by a before/after artifact-unchanged assertion; prompt-cache marker present; opt-out honored; bounded seed preserved; same file store; no new infra; no secrets in the activity log; event loop non-blocking; one `RobustScorer` / one `BudgetTracker`).
- [ ] `shared/contracts.py` is NOT in the diff (frozen).
- [ ] Unit/integration tests pass; the full hermetic backend suite is green except the single known pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (untouched nice-to-have, Capability #10).
- [ ] Dev handoff written at `docs/handoffs/goal-financial_free-iter-6-dev.md`, with a "Files Changed" list that matches `git diff` (reconcile any incidental file — see iter-4 `/health` documentation-gap lesson).

## TESTING REQUIREMENTS

- **Persistence (run FIRST, gates everything):** after implementation and before the handoff, the developer MUST run and record the DoD-0 checks above (`git diff --stat HEAD -- apps/backend/` non-empty with the four expected paths; `history_planner.py` present; `status.json.changed_files` non-empty + `tests_run:true`). QA/audit re-run the same checks against the live tree.
- **Endpoint / display (ACCEPTED as sufficient for J-15's display aspect):** verify J-15 via the canonical `GET /api/sessions/{id}` the UI polls — `activityLog` contains the warm-start planner-decision entry for the `global` run and NOT for the `this-run` run; `iterationHistory` shows the first PROMOTEd node's family matching the prior run's best family. This is the documented Chrome-MCP headless-throttle substitute AND J-15 adds zero new FE render path (reuses the `auto-run` entry branch). Run ONE best-effort browser-qa pixel capture of the planner-decision Activity-Log entry against the live FE; **this pixel capture is explicitly NON-BLOCKING** — endpoint-layer + zero-new-FE-code proof closes J-15. Do not carry a 5th "pixel debt" item.
- **Unit/integration (hermetic, no live LLM — inject a fake planner via the test pipeline):**
  - read-only mining: assert prior sessions' `session.json`, `meta.json`, and iteration files are byte-identical before vs after a `global` warm-start run (no mutation/deletion);
  - `global`: a warm-start/planner `auto-run` activity entry is emitted citing a mined prior family, SCREEN runs the historically-strongest in-seed family first, and the first PROMOTEd node's `(symbol, timeframe)` equals the mined top family;
  - `this-run` (and the default with no field): NO cross-run citation entry, and the SCREEN ordering + promotion ranking are byte-equivalent to the current deterministic behavior (lock in J-12 / J-14 no-regression);
  - prompt caching: the planner request carries the `cache_control: {"type": "ephemeral"}` marker and the planner is invoked **at most once per run** (assert call count == 1 for `global`, == 0 for `this-run`);
  - planner failure is non-fatal: a raising/empty planner falls back to the deterministic mined-family ordering and the run still reaches a terminal state;
  - budget: planner token usage is accumulated into `BudgetTracker` (J-13); a pre-exhausted token/USD budget terminates `budget-exhausted` before SCREEN;
  - bounded seed: a `global` run never enumerates a `(symbol, timeframe)` outside the seed universe and never exceeds `SEED_UNIVERSE_MAX`;
  - coherence: exactly one `RobustScorer` instance and one `BudgetTracker` drive scoring/budget (no second scorer);
  - secrets: the planner activity entry and persisted artifacts contain no `api_key` / `sk-` material.
- **Live (key-gated, one cheap run pair):** seed run #1 (`this-run`/default, tiny budget) then run #2 (`history_scope: "global"`); use a date range **≥ 9 months** (≥ `IS_months + OOS_months` at the 6/3 defaults) so the PROMOTE walk-forward forms ≥ 1 window and the promote→best path is NOT vacuous (iter-4 lesson). Confirm run #2's activity log cites run #1's performance and its first promoted family matches; a `this-run` run #3 shows no citation.
- **Error cases:** `history_scope` outside `{"global","this-run"}` → **422**; `global` with an empty store (no prior sessions) degrades gracefully — no citation entry, deterministic ordering, no crash, terminal state reached.

## NOTES

- **Persistence is the whole point of this iteration.** Iteration 5 produced identical (green) work that vanished because an `isolation: worktree` copy was discarded without merging. The DoD-0 gate exists solely to prevent a recurrence. The stall guard is explicit: a *second* consecutive lost-work iteration would justify STALLED/ESCALATE, so verify the diff landed in the real tree before declaring done.
- **Design decision — default `this-run` (warm-start opt-IN via `global`).** This follows the iter-5 spec and the iter-5 evaluator's re-land instruction, and is the regression-safe choice: J-12 / J-13 / J-14 hermetic tests issue open-universe runs WITHOUT a `history_scope` field and assert deterministic seed ordering / staging, so defaulting to the opt-out value keeps them byte-for-byte green with no dependency on whether a test store happens to be empty. The goal's J-15 journey triggers warm-start by explicitly setting `history_scope: "global"` (run #2) and opts out with `this-run` (run #3); the **default (omitted) value is not exercised by J-15 acceptance**, so `this-run` is both correct and safe. "Opt-out-able" is satisfied: `this-run` is the opt-out value.
- **Do NOT reconstruct the lost test names verbatim.** The lost iter-5 implementation's pytest cache listed e.g. `test_default_omitted_history_scope_resolves_to_global` and `test_history_scope_defaults_to_none_when_omitted` — these encode the OPPOSITE default (omitted→global) from this spec and from the authoritative re-land instruction, so the lost build deviated from its own spec on that point. Write tests to **this spec** (default `this-run`); do not recreate contradictory tests, and do not treat the lost names as a checklist. The lost code is unrecoverable; the `auto-money-printer` dangling commits are a *different lineage* and MUST NOT be cherry-picked (consult only as a design reference if at all).
- **Acceptance nuance (first promoted family):** with `DEFAULT_PROMOTE_K = 1`, only the top-ranked SCREEN survivor is promoted. To make "first promoted config's family matches a top performer from run #1" robust, the PROMOTE ranking under `global` is `(history_priority, screen_score)` — the historically-strongest *screened* family wins promotion. Best-marking stays WFE-gated among promoted (a history-prioritized promote that fails WFE is simply not marked best — that is correct and does not fail J-15, which is about promotion *selection*, not best-marking).
- **Pixel-debt resolution (decisive, per iter-4 evaluator option b):** J-15's display reuses the existing `auto-run` render path, so there is no new pixel surface; endpoint-layer + code confirmation is the formal definition of done for the display aspect. The recurring miss has a concrete framework-tooling root cause — `browser-qa-phase.sh` health-probes the frontend on the `:3000` default while `./scripts/dev.sh` binds a deterministic **offset** port (evidence: `:3692`). Fixing that port detection is a **separable, non-blocking** harness improvement; if a maintainer makes it, commit it separately from this product change. It MUST NOT gate J-15.
- **Do NOT re-litigate** settled items: the eager-load anti-goal (resolved iter-1), the in-browser scorer/loop removal (done iter-2), and the single-`RobustScorer`/single-`BudgetTracker` coherence gate (re-confirmed iter-4). Carry-forward non-blockers unchanged: pre-existing red `test_directions_cache`; flaky `test_post_returns_before_loop_completes_and_get_stays_responsive` (de-flake opportunistically, out of scope).
- After J-15 lands green **and persists**, only **J-16** (overfit-gating leaderboard UI) remains before GOAL_ACHIEVED.
