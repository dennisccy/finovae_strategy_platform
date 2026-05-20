# Goal Iteration 6 — Robust-best overfit-gating demonstration (J-16)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** auto-money-printer
- **Iteration:** 6
- **Mode:** next
- **Depth:** full
- **Target journeys:** J-16
- **Required-still-passing journeys:** J-01, J-02, J-03, J-04, J-05, J-06, J-07, J-08, J-09, J-10, J-11, J-12, J-13, J-14, J-15
- **Frontend Present:** yes — a single additive render of an existing-but-currently-ignored `detail:` field on the `complete` activity-feed row. No new component, no new panel, no new state, no new in-browser loop.
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - The automated "best" MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best.
  - Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are reserved for promoted candidates.
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.
  - Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify.
  - Identical generated strategies (by code hash) MUST NOT be re-generated or re-backtested; the OHLCV Parquet cache MUST be reused across configs (no re-fetch when a covering cache exists).
  - Global history learning MUST be read-only mining of the existing store (it MUST NOT mutate or delete prior sessions' artifacts); the `history_scope` opt-out MUST be honored.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - `GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint.
  - `BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST NOT run a second in-browser iterate loop.
  - The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
  - API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts.
  - No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store.
  - The LLM-planner / history context MUST use prompt caching; the leaderboard/history MUST NOT be re-sent uncached every round.

## GOAL

An open-universe headless run **visibly gates out** overfit-tempting candidates in the existing session activity feed. Each PROMOTE `complete` row carries an operator-readable robust-best rationale: either `"Best — WF-validated (WFE X.XX, N trades)"` or `"Not best — <specific gate that failed>"` (e.g. `"WFE 0.00 below 0.30 gate"`, `"under min-trades floor (2 < 5)"`, `"over-leveraged (5.0×)"`). The `Best` badge sits on a walk-forward-validated candidate; a higher-raw-return but WFE-failing / under-traded / over-leveraged candidate is plainly visible as NOT best with the reason printed inline. The operator no longer has to mentally decode the `robust −999.x` sentinel to understand why an overfit candidate was rejected.

## BACKGROUND

15/16 Must-have journeys pass. J-16 is the last failing journey and gates `GOAL_ACHIEVED`. The robust-best **invariant** is already structurally guaranteed (`backend/robust_objective.py`: `_GATE_FAIL_PENALTY = 1000.0` is subtracted on any hard-gate fail, so any gate-passing candidate strictly outranks any gate-failing one — proven by unit `test_robust_objective_rejects_high_return_wfe_failing_overleveraged` and corroborated by every iter-2–5 PROMOTE run). What J-16 needs is a **demonstration as a journey**: a deliberately overfit-tempting open-universe scenario where the leaderboard / activity feed makes the gating decision auditable end-to-end. Today's PROMOTE `complete` entry shows `return X%, N trades, robust Y, walk-forward WFE Z` — operator-readable for the numbers, but the *gate decision* is implicit in the `robust = -999.x` sentinel (cryptic for a non-developer audience). The fix is an **additive operator-readable rationale tag** on every PROMOTE `complete` entry, written exactly when the round-current `select_best` runs — same store path, same activity-entry shape, zero new schema.

**Design decision — additive activity-feed rationale, NOT a new leaderboard panel.** The goal text says "visible in the leaderboard / activity log" (slash = or). The existing session activity feed already serves as the leaderboard surrogate (one row per promoted iteration with return / trades / robust / WFE) and already renders the `Best` badge on the chosen iteration. Adding the rationale as an *additive `detail:` field* on the existing PROMOTE `complete` entry (the `_activity(...)` helper already accepts `detail`) satisfies the visibility requirement at the smallest surface, mirrors iter-4's additive `stage` and iter-5's additive `effectiveHistoryScope` patterns, and avoids inventing a parallel UI surface. No new entry type, no new schema key on the iteration node, no new component.

**Design decision — deterministic unit demonstration is the PRIMARY proof; browser is observable corroboration.** Per the iter-5 lesson, the durable `BACKTEST_STORE_DIR` cannot be emptied for browser QA (`~113` prior sessions accumulate by anti-goal design), and a real open-universe browser run cannot deterministically guarantee that an overfit-tempting candidate co-occurs with a WF-validated one in the same tiny budget. The journey's deterministic proof is therefore a `FakePipeline(by_cfg=...)` integration test on an **isolated `store` fixture**: two PROMOTE configs, one crafted as high-raw / WFE-failing, one as modest-return / WF-validated; assert `bestIterationId` resolves to the WF candidate, the high-raw `complete` entry carries the `"Not best — WFE 0.00 below 0.30 gate"` rationale, and the WF candidate carries the `"Best — WF-validated …"` rationale. Browser QA is the observable corroboration that the *rendering surface* works (rationale text visible on a real open-universe run, `Best` badge on the chosen iteration). Do NOT mark the unit test as a "fallback" — it is the primary proof.

**Lesson — iter-2** (Applies to: any iter touching the headless loop / event-loop non-blocking). Every new activity append MUST go through `asyncio.to_thread(session_store.append_activity_entries, …)` — the same pattern every iter-2–5 append already uses. No timing-based "non-blocking" assertion. The backtest subprocess seam (deterministic `child_pid != os.getpid()`) stays unchanged.

**Lesson — iter-3** (Applies to: any iter touching the `would_exceed` / budget loop). This iteration adds **zero** new tokens, no new LLM call, no new budget-affecting work — it is a pure metadata enrichment of an existing activity entry already inside the PROMOTE branch. The `would_exceed()` round-top gate and the `_SPEND_CAPS = {"ai-tokens","usd","wall-clock"}` vs `"max-configs"` distinction MUST stay byte-identical. No reordering of the existing `tracker.start_config()` → evaluate → `select_best` → `_update_autorun` chain in a way that changes the budget-gate ordering.

**Lesson — iter-5** (Applies to: any iter claiming "additive Y" / "no new writes outside the existing path"). The iter-5 write-primitive scan — `grep -E '\.write\(|open\([^)]*[\"'"'"']w|json\.dump|\.unlink|\.rename|shutil\.|os\.remove|derive_session_tabs'` over the full added diff — is the strongest structural proof. Apply it to the iter-6 diff: the only legitimate writes MUST be additional `append_activity_entries` calls on the *current* session (same primitive iter-4 / iter-5 used) plus the existing `_update_autorun` writes. Pinned (J-07–J-11) and SCREEN-only (J-14) paths MUST be byte-untouched.

**Lesson — iter-4** (Applies to: any iter where closure may emit transient stub artifacts). A `status.json` of `closure_failed` from `ui-test-design-phase.sh` exit-1 stubs is NOT a J-16 / journey / anti-goal failure — it is an outer-loop pipeline-artifact gap with a documented one-command remediation. Evaluator: classify accordingly, do NOT flip the journey verdict.

## IN SCOPE

### Backend

- [ ] **Robust-best rationale helper** — a pure function in `apps/backend/backend/auto_session.py` (dependency-light, no new module, no new import beyond `DEFAULT_MIN_TRADES` / `DEFAULT_MIN_WFE` from `backend.robust_objective`). Signature: `_robust_best_rationale(iter_id, RobustInputs, best_id, score, best_score, *, min_wfe=DEFAULT_MIN_WFE, min_trades=DEFAULT_MIN_TRADES) -> str`. Output shapes (exhaustive — always returns a finite, JSON-safe, non-empty string; never raises):
  - `iter_id == best_id` AND gates pass → `"Best — WF-validated (WFE X.XX, N trades)"`.
  - `iter_id == best_id` AND gates fail → `"Best (sole survivor) — gates not met: <reason>"` (a best is always marked because `select_best` always names one; this is the only-one-PROMOTE-completed edge case).
  - `iter_id != best_id` AND gates fail → `"Not best — <reason>"`. Reason resolution order: no walk-forward (`num_windows == 0` or `wfe is None`) → `"no walk-forward windows"`; `wfe < DEFAULT_MIN_WFE` → `"WFE X.XX below 0.30 gate"`; `num_trades < DEFAULT_MIN_TRADES` → `"under min-trades floor (n < 5)"`; `leverage > 1.0` → `"over-leveraged (X.X×)"`.
  - `iter_id != best_id` AND gates pass → `"Not best — lower robust score (X.XX vs best Y.YY)"`.
  - Internal helpers (`_robust_best_reason`, `_finite_display`) MUST handle `None`/`nan`/`inf` cleanly — `json.dumps` would otherwise emit `NaN`/`Infinity` literals that the browser's `JSON.parse` rejects (the same hazard `_json_safe` addresses).

- [ ] **Wire the rationale into the PROMOTE `complete` activity entry** at the existing append site in `_run_staged_open_universe`. Resolve `select_best(completed)` (and look up the round-current `best_score`) BEFORE appending the PROMOTE `complete` row so the rationale can be passed as the `detail` kwarg to the existing `_activity("complete", …, iter_id, detail=…)` call. Still appended via `asyncio.to_thread(session_store.append_activity_entries, …)`. Appended exactly ONCE per promoted iteration. Each PROMOTE's `detail` is a write-time snapshot of the round-current decision — re-evaluating prior PROMOTE rows' rationale across later rounds is OUT OF SCOPE; the round-final `bestIterationId` on `autoRun` remains the single source of truth for the `Best` badge.

- [ ] **Terminal-state robust-best summary row (open-universe only).** When at least 2 PROMOTE candidates completed and a `bestIterationId` exists, append ONE `_activity("auto-run", "Robust-best: <best-iter-id> selected over <N-1> other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage", iter_id_of_best)` row before the loop returns, via the existing `session_store.append_activity_entries` off-thread. Single-promote runs (trivially "best") and pinned runs MUST NOT emit this row.

- [ ] **Pinned path (J-07–J-11) byte-unchanged.** The rationale helper is open-universe-only; `_run_pinned` and its `complete` activity entry are NOT modified. Structural assertion: a `git diff` over the iter-6 diff shows zero edits inside `_run_pinned`. No `detail` field added to pinned `complete` rows; no terminal summary on pinned runs.

- [ ] **SCREEN entries (J-14) byte-unchanged.** No rationale on SCREEN `complete` entries — they intentionally skip walk-forward; a `Not best — no walk-forward windows` tag would be misleading and would leak SCREEN/PROMOTE staging into the wrong audience. The rationale lives only on PROMOTE `complete` and the terminal summary.

- [ ] **`backend/robust_objective.py` UNTOUCHED.** `robust_score`, `select_best`, `targets_met`, `_GATE_FAIL_PENALTY`, gate thresholds — all byte-identical. The iter-6 work is purely a presentation layer on top of the existing invariant.

### Frontend

- [ ] **Render the `detail` field on `complete` activity entries** in `apps/frontend/src/components/ActivityLogEntry.tsx`. The existing render path for the `complete` row is the emerald success card with the message paragraph. Wrap that paragraph in a flex column and conditionally render a second `<p>` line with the `detail` text in muted/secondary emerald (e.g. `text-xs text-emerald-700/70 mt-1`) — the same visual register iter-4 used for SCREEN/PROMOTE `stage` and iter-5 used for the warm-start citation. The new sub-line MUST only render when `entry.detail` is truthy. No new component, no new icon, no new badge, no new state machinery, no new polling. The `Best` badge on `IterationCard.tsx` is untouched (already correct — driven by `bestIterationId`).
- [ ] **No new in-browser iterate loop.** Zero changes to `useBacktest.ts`, `SessionContainer.tsx`, `AutoRunBar.tsx`, or any polling / auto-run state machinery. Reading the new `detail` field is purely render-time.

### New user-facing capability

A user (or API caller) who runs the open-universe optimizer can now **audit the robust-best decision in plain language** in the session activity feed: each promoted candidate carries either a `"Best — WF-validated …"` rationale or a specific `"Not best — <gate that failed>"` reason. An overfit-tempting candidate with higher raw return but failed walk-forward is plainly NOT selected as best, and the operator sees exactly *which gate* it failed without reading the `robust` numeric.

### New information displayed

A short operator-readable rationale string on every PROMOTE `complete` activity entry; one terminal-state summary row naming the winner and the gate set (open-universe runs with ≥ 2 PROMOTEs only). No new columns, no new pages, no new badges.

### New user actions

None — this is a read-only audit enrichment of the existing activity feed.

### UI surface changes

The PROMOTE `complete` row gains one additional muted-emerald sub-line beneath its existing content when `detail` is present. The terminal summary appears as a normal `auto-run` row at the bottom of the activity feed. Exactly mirrors iter-4's additive `stage` and iter-5's additive warm-start citation pattern.

### Product surface delta

The robust-best gate becomes **auditable in operator language**: the existing structural invariant ("WFE-failing / over-leveraged candidate cannot be best") is now visibly explained in the same feed the user is already reading, closing the loop between the abstract Key Capability #11 ("robust walk-forward profit objective") and the user-facing artifact.

## OUT OF SCOPE

- A new "leaderboard" page, panel, table, sortable grid, or top-N component.
- Plumbing a `leverage` request parameter through the API → engine → `RobustInputs.leverage`. Leverage > 1.0 is already a recognised gate in `robust_score`; the demonstration works on the WFE-failing and min-trades-failing axes alone, which are fully wired today (`leverage = 1.0` hard-coded at `_robust_inputs`). The rationale helper MUST still surface `"over-leveraged …"` reason text (gate signature is complete) but no in-this-iter scenario exercises it through a real backtest.
- Editing `backend/robust_objective.py` (gate thresholds, scoring formula, `_GATE_FAIL_PENALTY`, function signatures).
- Recomputing a prior PROMOTE iteration's `detail` rationale across later rounds when a later promotion changes `best_id`. Write-time snapshot only.
- Editing the SCREEN path's activity entries.
- Editing the pinned path (`_run_pinned`) or its activity entries.
- Editing `shared/contracts.py` (frozen).
- Any change to `select_best`, `robust_score`, or `targets_met` signatures or semantics.
- The iter-4 closure carryover (regenerate the two transient `ui-test-design-phase.sh` stub artifacts for `goal-auto-money-printer-iter-4`) — see NOTES; outer-loop work, not iter-6 developer work.

## DEFINITION OF DONE

- [ ] Target journey **J-16** passes via browser-qa: an open-universe tiny-budget run renders the rationale text on each PROMOTE `complete` entry; the `Best` badge sits on a WF-validated candidate (when one exists in the run); a higher-raw-return but WF-failing candidate (when one occurs in the run) plainly carries the `"Not best — <reason>"` rationale. If the natural run does NOT happen to produce a WFE-failing candidate alongside a passing one in the tiny budget (best-case healthy data), J-16 still passes as long as **every** PROMOTE `complete` entry carries a coherent rationale tag AND the deterministic unit test (below) proves the rejection branch fires when it should.
- [ ] At least one screenshot of the rationale text and the `Best` badge co-located in the same activity-feed view.
- [ ] Required-still-passing journeys **J-01–J-15** remain green. Concrete proofs: pinned test `test_pinned_path_unchanged_by_open_universe_addition` (including the iter-4 `insight_calls == 3` assertion) stays green; SCREEN/PROMOTE staged tests green; iter-5 warm-start + read-only tests green; iter-5 write-primitive scan stays clean over the iter-6 diff.
- [ ] No anti-goal violation introduced. Specific structural assertions:
  - rationale is appended through `session_store.append_activity_entries` only (no parallel store / no schema fork);
  - `git diff HEAD -- apps/backend/backend/auto_session.py` over the iter-6 diff shows zero edits inside `_run_pinned`;
  - `git diff HEAD -- apps/backend/backend/robust_objective.py` is empty;
  - `git diff HEAD -- apps/backend/shared/contracts.py` is empty;
  - no API keys / secrets in any rationale text (it is purely numeric + gate-name + iteration-id);
  - no new external infrastructure import in the iter-6 diff.
- [ ] Unit and integration tests pass. Full backend suite shows no new regressions (the pre-existing out-of-scope `test_directions_cache::test_write_and_read_full_round_trip` remains the only tolerated red, unchanged from iter-5's 200p/1f baseline).
- [ ] Dev handoff written at `docs/handoffs/goal-auto-money-printer-iter-6-dev.md`.
- [ ] All 6 UI visibility artifacts produced and non-vague (`implementation-summary`, `user-visible-changes`, `ui-surface-map`, `ui-test-plan`, `ui-test-results`, `what-to-click`). The `phase-closure-auditor` gives `CLOSURE-PASS`.

## TESTING REQUIREMENTS

### Browser (J-16)

One tiny-budget open-universe run against the real backend (default `_OPEN_UNIVERSE_*` window).
- Observe at least two PROMOTE `complete` entries in the activity feed; verify each carries a rationale sub-line (`"Best — …"` exactly once across the run, `"Not best — …"` on every other PROMOTE).
- Verify the `Best` badge on the iteration list sits on the entry whose rationale starts with `"Best — "`.
- Verify the rationale text is plain operator language (no secrets, no API jargon, no `null`/`undefined`/`NaN` literals visible).
- Verify the terminal `"Robust-best: <id> selected over N other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage"` row appears at the bottom of the activity feed when ≥ 2 PROMOTEs completed.
- Capture at least one screenshot showing the rationale sub-line and the `Best` badge co-located.

### Unit / integration

Deterministic, tiny budgets, isolated `BACKTEST_STORE_DIR` via the existing `store` fixture, `FakePipeline(by_cfg=...)` (the same harness iter-2–5 used). Add to `apps/backend/tests/test_auto_session.py`:

- **J-16 primary demonstration (deterministic):** open-universe request with `_SEED_UNIVERSE` reduced (test-monkeypatched) to two configs. `FakePipeline.by_cfg`:
  - A = `{total_return: 0.50, sharpe_ratio: 4.0, num_trades: 30, max_drawdown: 0.40, wfe: 0.0, oos_sharpe: -0.5, num_windows: 2}` (overfit-tempting — high raw return, WFE fails).
  - B = `{total_return: 0.10, sharpe_ratio: 1.1, num_trades: 25, max_drawdown: 0.08, wfe: 0.7, oos_sharpe: 1.0, num_windows: 3}` (genuinely robust).
  - Assert: `bestIterationId` resolves to B's iter id; A's `complete` activity entry has `detail == "Not best — WFE 0.00 below 0.30 gate"`; B's `complete` activity entry has `detail` starting with `"Best — WF-validated"` and embedding `WFE 0.70`.
- **Min-trades floor rationale:** a PROMOTE candidate with `num_trades=2` and `wfe=0.8, num_windows=3` is rejected with `detail == "under min-trades floor (2 < 5)"`.
- **No-walk-forward rationale:** a PROMOTE candidate with `num_windows=0, wfe=None` is rejected with `detail == "no walk-forward windows"`.
- **Over-leveraged rationale unit-tested directly** at the helper level (no pipeline scenario needed since `leverage = 1.0` is hard-coded in `_robust_inputs`): construct a `RobustInputs(leverage=5.0, wfe=0.8, num_trades=30, num_windows=3, …)` and assert the helper returns `detail == "Not best — over-leveraged (5.0×)"` when not best. This keeps the gate signature complete and ready for a future leverage-plumbing iteration.
- **Best-as-sole-survivor edge case:** open-universe run where only one PROMOTE completes (others `bt_none`/`gen_fail`). Assert its `detail` is `"Best — WF-validated …"` when its own gates pass, else `"Best (sole survivor) — gates not met: <reason>"`. The `Best` badge must still appear (`select_best` always names one).
- **Terminal robust-best summary row:** in the 2-PROMOTE scenario assert exactly one `auto-run` activity row at the end whose content starts with `"Robust-best: "` and names B's iter id; in a 1-PROMOTE scenario assert NO such terminal summary row is appended.
- **Pinned-path byte-unchanged:** existing `test_pinned_path_unchanged_by_open_universe_addition` (including the iter-4 `insight_calls == 3` assertion) stays green unmodified. Add one delta assertion: no `complete` activity entry on a pinned-path run carries a `detail` field set by the rationale helper.
- **SCREEN entries untouched:** assert no SCREEN `auto-run` / `SCREEN done` `complete` entry has a `detail` field set by the rationale helper.
- **Robust-best invariant test reused:** the existing `test_robust_objective_rejects_high_return_wfe_failing_overleveraged` MUST stay green unchanged — it is the unit proof of the invariant the rationale text describes.
- **Once-per-PROMOTE, not per-round:** in the 2-PROMOTE scenario, rationale-bearing `detail` rows appear exactly twice — once per PROMOTE. Use activity-log read-back / `FakePipeline.bt_calls` to assert call count.

### Error cases

- **Corrupt / partial `RobustInputs`** (e.g. all-`None` numeric fields): helper returns a graceful finite string (`"Best — gate evaluation unavailable"` for best or `"Not best — gate evaluation unavailable"` otherwise); never raises, never emits empty string, never crashes the loop.
- **Non-finite `robust_score`** in the gates-pass `"Not best — lower robust score (X vs Y)"` branch: helper substitutes `"−∞"` / `"+∞"` / `"0.00"` for `-inf` / `+inf` / `nan` — never emits raw `nan` / `inf` literals (would break browser `JSON.parse`, mirroring `_json_safe`).

## NOTES

- **Evaluator-driven scope.** iter-5 eval (`runs/goal-session-auto-money-printer/iter-5/eval.md`, "Next-Step Recommendation") and the inlined evaluator log both pin iter-6 = J-16 at **full** depth — the last failing journey, gates `GOAL_ACHIEVED`. Full pipeline is consistent with every Optimizer-layer iteration (iter-2 through iter-5).
- **Lessons applied (cross-reference).**
  - iter-1 (UI-test headline reconciliation caution — for the evaluator: cross-check post-fix source + QA MODE-2, never trust a stale reconciled headline alone).
  - iter-2 (every activity append off the event-loop via `asyncio.to_thread`; no timing-based assertion; backtest subprocess seam unchanged).
  - iter-3 (no new tokens, no new budget gate, `would_exceed` / `max-configs`-vs-spend-cap distinction byte-preserved).
  - iter-4 (`Best` badge already exists, do not invent a new one; do not let a transient `ui-test-design-phase.sh` CLI exit-1 flip the journey verdict — see outer-loop carryover).
  - iter-5 (write-primitive scan over the full added diff is the strongest "additive only" proof — apply it; the durable store cannot be empty for browser, so the J-16 deterministic demonstration is a unit test on the isolated `store` fixture, with browser as the observable corroboration of the *renderer*, not a re-derivation of the gate semantics).
- **GOAL_ACHIEVED gate.** With J-16 passing, all 16 Must-have journeys pass and zero anti-goals are violated. The evaluator may then declare `GOAL_ACHIEVED` (per the agent rule "every journey passing + no critical anti-goal violation"). If any J-01–J-15 regresses, the evaluator MUST emit `CONTINUE` or `REGRESSION`, not `GOAL_ACHIEVED`.
- **Outer-loop carryover (NOT iter-6 developer/source work).** The iter-4 closure-fail residue — two transient `ui-test-design-phase.sh` stub artifacts at `reports/phase-goal-auto-money-printer-iter-4-ui-test-plan.md` and `reports/phase-goal-auto-money-printer-iter-4-what-to-click.md` — remains orchestrator/outer-loop work. Remediation is a one-command pair: `./scripts/automation/ui-test-design-phase.sh goal-auto-money-printer-iter-4` then `./scripts/automation/phase-closure-check.sh goal-auto-money-printer-iter-4`. It does not flip any journey or anti-goal verdict and MUST NOT consume iter-6 source / test / journey budget. Recorded here only so it is not lost across iterations.
- **Existing partial implementation in the working tree.** A prior aborted iter-6 attempt left the rationale helper (`_robust_best_rationale`, `_robust_best_reason`, `_finite_display`), the PROMOTE `detail` wiring, the terminal robust-best summary row, and the frontend `ActivityLogEntry.tsx` `detail` render in the working tree. The developer should inspect what is already in place (`git diff HEAD`) before adding new code — if a required item is already implemented correctly and matches this spec, leave it; do NOT duplicate, refactor, or rewrite. The TDD discipline still applies to whatever delta remains (typically: the J-16 demonstration test, the over-leveraged unit test, the terminal-summary test, and the pinned/SCREEN delta assertions).
