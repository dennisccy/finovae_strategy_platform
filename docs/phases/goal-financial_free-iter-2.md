# Goal Iteration 2 — Layer-1 finish: backend-driven Auto Run, live UI tracking, stop

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** financial_free
- **Iteration:** 2
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes
- **Target journeys:** J-08, J-10, J-11
- **Required-still-passing journeys:** J-01, J-02, J-05, J-07, J-09 (and all other already_passing: J-03, J-04, J-06)
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - After the rewire, the iterate loop MUST exist only in the backend; the frontend MUST NOT run a second in-browser iterate loop.
  - The automated-session `autoRun` status MUST be persisted to the durable store and survive a worker restart and a browser reload; it MUST NOT live only in browser memory or a non-persisted in-process variable.
  - The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active (one-backtest-per-worker semaphore respected).
  - The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one.
  - `GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint.
  - The automated chain MUST reuse the existing `BacktestPipeline`; it MUST NOT bypass the RestrictedPython sandbox or the deterministic next-bar engine.
  - Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take "one more round" past the cap, even if targets are never met.

## GOAL

Make the backend auto-session loop the **only** Auto Run engine: clicking "Auto Run" in the UI starts the server-side loop, the open session tracks `running → terminal` live with no manual reload, the run survives a browser reload, and the UI stop control truly stops it server-side.

## BACKGROUND

iter-1 landed the Layer-1 core (J-07, J-09): `POST /api/auto-sessions` starts a durable server-side loop that reuses `BacktestPipeline`, writes byte-shape-identical artifacts via `session_store`, runs to a real terminal state, and marks a WFE-gated robust best on a persisted `autoRun` block. The frontend was intentionally left untouched: it still runs a **second** in-browser iterate loop (`useBacktest.ts:startAutoRun`, the `while` at lines 2067–2234, with its own duplicate `scoreIteration` at line 2100) and never reads the backend `autoRun` block. This iteration finishes Layer-1 by deleting that in-browser loop, rewiring the button to the backend, and surfacing the persisted `autoRun` block live. The evaluator scheduled exactly this (iter-1 eval §Next-Step Recommendation).

**Apply the iter-1 lesson (it Applies-to this exact code path).** Do **not** wrap the controller's `session_store` calls in `await asyncio.to_thread` *alone*. `write_session_meta` top-level-merges but replaces the whole `autoRun` dict, and both `_save_auto_run` (`auto_session.py:375`, which preserves `stopRequested` via its own read) and the `/stop` endpoint (`auto_session_routes.py:240`) do independent read-modify-write cycles on `autoRun`. Today the controller's RMW is event-loop-atomic (synchronous, no `await` between read and write), which is what currently *protects* the `/stop` flag. Splitting it with `to_thread` interleaves it against `/stop` and **drops the stop request** (TOCTOU). B1 (don't block the loop) and B2 (don't lose a concurrent stop) are one design problem — solve them **together** (single-writer / async-lock, or a separate stop-flag key the controller only reads), proven by a regression test.

## IN SCOPE

### Backend
- [ ] **B1+B2 concurrency, co-designed.** Move the controller's `autoRun` store reads/writes off the event loop **and** make `autoRun` persistence single-writer so a `/stop` issued concurrently with a controller `_save_auto_run` is never lost. Acceptable shapes (developer's choice, pick one): (a) a per-session `asyncio.Lock` shared between `AutoSessionController` and `stop_auto_session` (e.g., held on `app.state.auto_sessions[session_id]` alongside the task) guarding every `autoRun` read-modify-write, with the blocking I/O inside the lock via `to_thread`; or (b) keep the stop signal in its own top-level `session.json` key that `/stop` writes and the controller only *reads* (never rewrites), so the controller's `autoRun` writes can go off-loop without an RMW conflict. Either way: no new external infra, no `shared/contracts.py` change.
- [ ] Confirm the loop still honors `_stop_requested()` at its existing checkpoints (`auto_session.py:577`, `:637`) under the new persistence model, and transitions to `stopped` with the best-so-far retained.
- [ ] Keep `POST /api/auto-sessions` and `POST /api/auto-sessions/{id}/stop` contracts unchanged (already built iter-1); no new value-serving endpoint is added.

### Frontend
- [ ] **J-10 — rewire + remove the in-browser loop.** Replace the body of `startAutoRun` (`useBacktest.ts:2047`) so it POSTs `/api/auto-sessions` with the selected baseline iteration's NL prompt + params (`natural_language`, `symbol`, `timeframe`, `start_date`, `end_date`, `initial_capital`, `leverage`, `allow_short`, `model`) and a small `budget` (`max_iterations` = the existing Auto Run count + a bounded `max_wall_clock_sec`), then opens/switches to the returned `sessionId` and begins live tracking. **Delete** the in-browser iterate `while` loop (2067–2234) and the duplicate `scoreIteration` (2100), plus loop-only state that becomes dead (`autoRunStopRef`, `autoRunIterationIdsRef`, the auto-run worker-pool usage). Keep shared helpers used elsewhere (`generateAndExecute`, `editAndRerun`, `deleteIteration`, manual single-run path) intact.
- [ ] **J-08 — live tracking.** Surface the backend `autoRun` block (currently dropped during hydration, `useBacktest.ts:501–593`) into hook state, and **poll the existing canonical `GET /api/sessions/{id}`** (lightweight list/open path — NOT a new endpoint, NOT eager heavy-payload load) every ~2–3 s while `autoRun.status` is active (`queued`/`running`), stopping at a terminal status. Merge newly-appeared iteration cards from the lightweight list; lazy-load heavy detail only on selection (existing `fetchIterationDetail` path). Render the **Automated-session status strip** in the Right/Iterations panel (run state, stop reason, budget counters, best badge) — a home the blueprint already reserves.
- [ ] **Single source of truth for "running".** Derive the UI running indicator (`sessionStatus.isAutoRunning`, the SessionPicker spinner, the Auto Run / Stop button state) from the polled backend `autoRun.status`, **not** a local boolean — so after a browser reload (no local flag) an active session is still shown as running and polling resumes.
- [ ] **J-11 — stop control.** Rewire `stopAutoRun` (`useBacktest.ts:2245`) to POST `/api/auto-sessions/{sessionId}/stop` for a backend-driven session (instead of only aborting locally); reflect the resulting `stopped` status from the next poll.

### New user-facing capability
The user clicks "Auto Run" and the optimization runs **server-side**: they can close the laptop / reload the tab and the run keeps going; reopening the session shows it still progressing and then finished. The Stop button actually halts the server loop.

### New information displayed
The Automated-session status strip now shows the **live** backend run state (`running` → `criteria-met` / `budget-exhausted` / `stopped`), the visible stop reason, budget counters (iterations done / wall-clock), and the marked best iteration — all read from the canonical `autoRun` block, updating without a manual reload.

### New user actions
- "Auto Run" now starts a durable backend session (was an in-browser loop).
- "Stop" now issues a server-side cancellation (was a local abort).

### UI surface changes
Automated-session status strip rendered in the Right/Iterations panel; live-updating iteration cards; the Auto Run/Stop controls in the Left/Activity-Log config bar now reflect backend status. No new page, route, or nav section.

### Product surface delta
Auto Run becomes a real headless optimizer the UI observes, not a tab-bound script — matching the "backend is the single source of truth" product promise. A headless (API-started) run and a UI-started run are now indistinguishable in the UI (both are just backend sessions the UI polls).

### Blueprint conformance
All pages/controls live under existing Information-Architecture homes: Auto Run/Stop controls = **Left — Activity Log → Automated-session controls** (already in `blueprint.md`); status strip + live iteration cards = **Right — Iterations → Automated-session status strip** (already in `blueprint.md`). No nav-skeleton change; no re-approval requested.

### Data-contract additions
**None.** Every value surfaced (`autoRun.status`, `stopReason`, `bestIterationId`, `budget` counters) is already registered (the three Layer-1 rows added iter-1). The live-tracking poll reads the **existing** canonical `GET /api/sessions/{id}`; the stop command uses the **existing** `POST /api/auto-sessions/{id}/stop`. No second computation, no second serving endpoint — read the registered canonical sources. The internal `stopRequested` (or a new top-level stop-flag key, if approach (b) is chosen) is a control flag, not a displayed value, so it needs no Data-Contract row. A blueprint Notes clarification reflecting this iteration's retirement of the in-browser scorer/loop is applied as an additive edit.

## OUT OF SCOPE

- **All of Layer-2 (J-12…J-16):** open-universe search, hard token/USD budget enforcement, staged SCREEN/PROMOTE, global-history warm start, leaderboard/overfit-gating UI.
- Extending `POST /api/auto-sessions` to **append into an existing session** (in-place continuation). Default approach: clicking Auto Run mints a new backend auto-session (seeded from the baseline iteration's NL + params) that appears in the Session picker — this reuses the iter-1 endpoint unchanged and matches the blueprint ("the created session then appears in the Header Session picker"). Only revisit if Option A demonstrably breaks a required-still-passing journey.
- Any change to `shared/contracts.py` (frozen) or to the manual single-run / walk-forward / insights code paths beyond what the loop removal requires.
- SSE for the auto-session (polling the lightweight GET is sufficient; SSE is an optional dev choice but not required).

## DEFINITION OF DONE

- [ ] **J-08** passes via browser-qa-agent: open an auto-session (tiny budget), observe `running`, at least one iteration with a backtest result + suggestions appears, and status reaches a terminal state — **all without a manual reload**.
- [ ] **J-10** passes: click "Auto Run" on a completed iteration with a small budget; mid-run reload the tab and reopen the session; progress keeps advancing and reaches a terminal state (proves the loop is backend-driven). The in-browser iterate loop and duplicate `scoreIteration` are **removed** (grep-verifiable).
- [ ] **J-11** passes: start a run large enough to still be running, issue stop (UI control or `POST .../stop`), and the session transitions to `stopped`, appends no further iterations, and retains the best-so-far.
- [ ] Required-still-passing remain green: J-07 (`POST /api/auto-sessions` still 200 + appears in `GET /api/sessions`), J-09 (terminal stop-reason + WFE-gated best), J-01/J-02/J-05 (manual NL backtest, run-history browse, reference-data controls — the heavily-edited `useBacktest.ts` must not regress them).
- [ ] No anti-goal violation introduced — in particular: only the backend runs the iterate loop; `autoRun` survives reload from the durable store; the event loop stays responsive; the J-08 poll uses the lightweight GET (no eager heavy-payload parse); same file store / no schema fork.
- [ ] Backend unit/integration tests pass; the 40 iter-1 auto-session tests stay green; **a new regression test proves a `/stop` issued concurrently with a controller `_save_auto_run` is honored (not lost)** under the off-loop persistence model.
- [ ] Dev handoff written at `docs/handoffs/goal-financial_free-iter-2-dev.md`.

## TESTING REQUIREMENTS

- **Browser (load-bearing this iteration):** J-08, J-10, J-11 by ID. Honor the documented Chrome-MCP headless render-throttle — if pixels are blank (hidden-tab throttle, not an app bug), verify the journey via the backend endpoints the UI calls (`GET /api/sessions`, `GET /api/sessions/{id}`, `POST /api/auto-sessions`, `POST /api/auto-sessions/{id}/stop`) and the persisted `autoRun` block. Use tiny budgets (≤ 2 iterations, short date range, cheapest model, lenient targets) so verification stays fast/cheap.
- **Unit/integration:**
  - Concurrency: a `/stop` racing a controller `_save_auto_run` results in a persisted `stopRequested=True` and the loop reaching `stopped` (the B1+B2 regression test).
  - Event loop stays responsive while a run is active (extend / keep the iter-1 `test_post_returns_before_loop_completes_and_get_stays_responsive` style check).
  - autoRun round-trips through `session.json` and an orphaned `running` reconciles to `interrupted` on startup (iter-1 tests stay green).
  - Frontend: the rewired `startAutoRun` POSTs `/api/auto-sessions` (not the in-browser loop) and `stopAutoRun` POSTs `/stop`; the in-browser `scoreIteration`/iterate loop is gone.
- **Error cases:** stop on an unknown / non-auto session → 404; stop on an already-terminal session → idempotent 200; Auto Run with an open-universe (missing symbol/timeframe) still rejected 400 (Layer-2 boundary preserved).

## NOTES

- **Lesson surfaced (iter-1):** the `to_thread` + stop-flag fix is one co-design — see BACKGROUND. The reviewer/auditor should FAIL the iteration if `to_thread` is applied to the controller's `autoRun` writes without serialization against `/stop`.
- **Coherence advisory now actioned:** the in-browser `scoreIteration` (coherence iter-1 §C.1, blueprint legacy-duplicate note) is the duplicate scheduled for removal here; after this iteration the backend `RobustScorer` is the sole "best" definition.
- **Single-source poll discipline:** read `autoRun` only from `GET /api/sessions/{id}`; do not add a parallel status endpoint or recompute "best"/scores in the browser (that is exactly the drift the coherence-auditor FAILs).
- **Carry-forward (non-blocking, out of scope):** the pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (nice-to-have Capability #10, untouched module) is not a regression. The eager-load anti-goal verdict is **resolved** (conforms) — do not re-litigate.
- **Reference:** iter-1 eval `runs/goal-session-financial_free/iter-1/eval.md` §Next-Step Recommendation; iter-1 coherence `runs/goal-session-financial_free/iter-1/coherence.md` §C.1.
