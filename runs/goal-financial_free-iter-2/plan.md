# goal-financial_free-iter-2 Execution Plan

> **Goal-mode iter-2 — Layer-1 finish.** Make the backend auto-session loop the **only** Auto Run
> engine: clicking "Auto Run" starts the server-side loop, the open session tracks
> `running → terminal` live with no manual reload, the run survives a browser reload, and the UI
> Stop control truly stops it server-side. Targets **J-08, J-10, J-11**; must keep
> **J-01/J-02/J-05/J-07/J-09** (and J-03/J-04/J-06) green.
> iter-1 landed the backend loop (J-07/J-09); the frontend was left untouched and still runs a
> *second* in-browser iterate loop. This iteration deletes that loop, rewires the button to the
> backend, and surfaces the persisted `autoRun` block live. Directly implements iter-1 audit
> §5 Recommended Next Step #1.

## What to Build

**Backend (B1+B2, co-designed as ONE concurrency fix):**
- Make every `autoRun` read-modify-write **single-writer** so a `/stop` issued concurrently with a
  controller `_save_auto_run` is never lost, **and** move the controller's blocking store I/O off the
  event loop. Developer picks ONE shape (both are in-spec):
  - **(a) async lock** — a per-session `asyncio.Lock` shared between `AutoSessionController` and
    `stop_auto_session`, held around every `autoRun` RMW, with the blocking I/O inside the lock via
    `to_thread`; or
  - **(b) separate stop-flag key** — `/stop` writes a top-level `session.json` stop-flag key that the
    controller only *reads* (never rewrites), so the controller's `autoRun` writes can go off-loop with
    no RMW conflict.
- Confirm the loop still honors `_stop_requested()` at its existing checkpoints
  (`auto_session.py:577`, `:637`) under the new model and transitions to `stopped` with best-so-far retained.
- **Keep `POST /api/auto-sessions` and `POST /api/auto-sessions/{id}/stop` contracts unchanged** (built
  iter-1). No new value-serving endpoint. No `shared/contracts.py` change. No new external infra.

**Frontend (rewire to backend; delete the in-browser loop):**
- **J-10** — replace the body of `startAutoRun` (`useBacktest.ts:2047`) so it POSTs `/api/auto-sessions`
  with the selected baseline iteration's NL prompt + params (`natural_language`, `symbol`, `timeframe`,
  `start_date`, `end_date`, `initial_capital`, `leverage`, `allow_short`, `model`) and a small `budget`
  (`max_iterations` = the existing Auto Run count; a bounded `max_wall_clock_sec`), then opens/switches to
  the returned `sessionId` and begins live tracking. **Delete** the in-browser iterate `while` loop
  (`2067–2234`) and the duplicate `scoreIteration` (`2100`), plus now-dead loop state (`autoRunStopRef`
  `:454`, `autoRunIterationIdsRef` `:455`, the auto-run worker-pool usage). Keep shared helpers used
  elsewhere intact (`generateAndExecute`, `editAndRerun`, `deleteIteration`, manual single-run path).
- **J-08** — surface the backend `autoRun` block into hook state during hydration (`:501–593`, where it is
  currently dropped) and **poll the existing canonical `GET /api/sessions/{id}`** (the lightweight
  list/open path — NOT a new endpoint, NOT an eager heavy-payload load) every ~2–3 s while
  `autoRun.status` is active (`queued`/`running`), stopping at a terminal status. Merge newly-appeared
  iteration cards from the lightweight list; lazy-load heavy detail only on selection (existing
  `fetchIterationDetail` path). Render the **Automated-session status strip** in the Right/Iterations
  panel (run state, stop reason, budget counters, best badge).
- **Single source of truth for "running"** — derive the running indicator (`sessionStatus.isAutoRunning`,
  the SessionPicker spinner, the Auto Run/Stop button state) from the polled backend `autoRun.status`,
  **not** a local boolean — so after a browser reload (no local flag) an active session still shows as
  running and polling resumes.
- **J-11** — rewire `stopAutoRun` (`useBacktest.ts:2245`) to POST `/api/auto-sessions/{sessionId}/stop`
  for a backend-driven session (instead of only aborting locally); reflect the `stopped` status from the
  next poll.

## Agents Required
- **developer: yes** — both backend and frontend in one phase.
  - **backend-data: yes** — B1+B2 concurrency co-design in `auto_session.py` / `auto_session_routes.py`
    (+ possibly `api.py` for a per-session lock on `app.state.auto_sessions`); new concurrency
    regression test.
  - **frontend-ux: yes** — rewire `useBacktest.ts` (delete in-browser loop, add polling, single-source
    running), add auto-session API client calls, render the status strip, derive controls/spinner from
    backend status.

## Frontend Present
yes

## Files to Create/Modify

**Backend**
- `apps/backend/backend/auto_session.py` — implement B1+B2 single-writer `autoRun` persistence (shape a
  or b); keep `_stop_requested()` honored at `:577`/`:637`; off-loop blocking I/O.
- `apps/backend/backend/auto_session_routes.py` — `/stop` participates in the chosen model (shape a: take
  the shared per-session lock; shape b: write the separate top-level stop-flag key). Contract unchanged.
- `apps/backend/backend/api.py` — only if shape (a): store the per-session `asyncio.Lock` alongside the
  task on `app.state.auto_sessions`. No other change.
- `apps/backend/tests/test_auto_session.py` (and/or `test_auto_session_routes.py`) — **NEW** regression
  test: a `/stop` racing a controller `_save_auto_run` results in persisted `stopRequested=True` and the
  loop reaching `stopped` (the B1+B2 proof). Keep the iter-1 event-loop-responsiveness test green.

**Frontend**
- `apps/frontend/src/hooks/useBacktest.ts` — the core change: rewire `startAutoRun`/`stopAutoRun`, delete
  the in-browser loop + `scoreIteration` + dead refs, add `autoRun` hydration + the active-status poll of
  `GET /api/sessions/{id}`, derive `isAutoRunning` from backend status.
- `apps/frontend/src/lib/sessionApi.ts` — add `startAutoSession(...)` (POST `/api/auto-sessions`) and
  `stopAutoSession(sessionId)` (POST `/api/auto-sessions/{id}/stop`) client fns; reuse the existing
  lightweight `apiLoadSession` for polling (do NOT add a heavier fetch).
- `apps/frontend/src/components/IterationPanel.tsx` — render the **Automated-session status strip**
  (status, stop reason, budget counters, best badge) above the iteration tree; live-updating cards.
- `apps/frontend/src/components/BacktestConfigBar.tsx` and `apps/frontend/src/components/IterationCard.tsx`
  — Auto Run / Stop controls reflect backend `autoRun.status` (enable/disable, label, Stop visibility).
- `apps/frontend/src/components/SessionPicker.tsx` — running spinner driven by backend status.
- `apps/frontend/src/components/SessionContainer.tsx` — wire the new hook state/controls through to the
  panels as needed.
- (New component file optional) `apps/frontend/src/components/AutoSessionStatusStrip.tsx` — if cleaner than
  inlining the strip in `IterationPanel.tsx`. Developer's choice.

## UI Evolution
- **New user-facing capability:** "Auto Run" now runs **server-side** — the user can close the laptop /
  reload the tab and the run keeps going; reopening the session shows it still progressing and then
  finished. The Stop button actually halts the server loop.
- **New information displayed:** the Automated-session status strip shows the **live** backend run state
  (`running` → `criteria-met` / `budget-exhausted` / `stopped` / `interrupted`), the visible stop reason,
  budget counters (iterations done / max, wall-clock / max), and the marked-best iteration — all read from
  the canonical `autoRun` block, updating without a manual reload.
- **New user actions:** "Auto Run" starts a durable backend session (was an in-browser loop); "Stop"
  issues a server-side cancellation (was a local abort).
- **UI surface changes:** Automated-session status strip in the Right/Iterations panel; live-updating
  iteration cards; Auto Run/Stop controls in the Left/Activity-Log config bar now reflect backend status.
- **Navigation changes:** **none.** No new page, route, or nav section. All controls live under existing
  Information-Architecture homes already reserved in `blueprint.md` (Left — Activity Log →
  Automated-session controls; Right — Iterations → Automated-session status strip). No re-approval.

## Visual Requirements
- **Component patterns:** reuse existing hand-rolled components (no external UI lib in this repo). The
  status strip is a compact horizontal info bar consistent with `IterationCard`/`MetricsCard` styling;
  budget counters as small labeled stats; status as a colored badge; best marker reuses the existing
  best/total-return badge treatment. Icons via `lucide-react` (already a dependency).
- **Layout:** persistent two-panel shell unchanged. Status strip pinned at the top of the Right/Iterations
  panel, above the iteration history tree.
- **Key visual effects:** match the existing dark, dense, data-forward "analytical workstation" aesthetic
  (Tailwind, dark surfaces, muted borders); status-color semantics — running = active/info accent,
  `criteria-met` = success, `budget-exhausted`/`interrupted` = warning, `stopped` = neutral/danger. A
  subtle running spinner/pulse on the active state; no new design language.
- **States to handle:** **queued/running** (spinner + live counters, Stop visible/enabled, Auto Run
  disabled), **terminal** (stop reason + best badge, Auto Run re-enabled, Stop hidden/disabled),
  **no auto-run** (strip hidden or shows "manual session"), **reload mid-run** (status derived from poll,
  not local flag — strip + spinner reappear and polling resumes), **poll error** (degrade gracefully; keep
  last known status, don't crash the panel).

## Key Test Scenarios
- **J-08 (browser):** open an auto-session (tiny budget), observe `running`, at least one iteration with a
  backtest result + suggestions appears, and status reaches a terminal state — **all without a manual reload.**
- **J-10 (browser):** click "Auto Run" on a completed iteration (small budget); mid-run reload the tab and
  reopen the session; progress keeps advancing and reaches a terminal state. The in-browser iterate loop
  and duplicate `scoreIteration` are **removed (grep-verifiable)**.
- **J-11 (browser):** start a run large enough to still be running, issue stop (UI control or
  `POST .../stop`); session transitions to `stopped`, appends no further iterations, retains best-so-far.
- **B1+B2 regression (backend unit/integration):** a `/stop` racing a controller `_save_auto_run` →
  persisted `stopRequested=True` and the loop reaches `stopped` (the request is not dropped). Plus the
  iter-1 event-loop-responsiveness check stays green.
- **Required-still-passing:** J-07 (`POST /api/auto-sessions` 200 + appears in `GET /api/sessions`), J-09
  (terminal stop-reason + WFE-gated best), J-01/J-02/J-05 (manual NL backtest, run-history browse,
  reference-data controls — the heavily-edited `useBacktest.ts` must not regress them). The 40 iter-1
  auto-session tests stay green.
- **Error cases:** stop unknown/non-auto session → 404; stop already-terminal → idempotent 200; Auto Run
  with open-universe (missing symbol/timeframe) still rejected 400 (Layer-2 boundary preserved).

## Test Commands & Verification Notes
- **Backend:** `cd apps/backend && .venv/bin/python -m pytest` (hermetic; `-m "not integration"` is the
  default via `addopts`). The B1+B2 regression test must be added here.
- **Frontend:** **no unit-test runner exists** (`package.json` has only `dev`/`build`/`lint`/`preview`).
  Frontend verification = `npm run build` (tsc typecheck must pass) + `npm run lint` (max-warnings 0) +
  **grep** proving the in-browser loop and `scoreIteration` are gone + **browser QA** for J-08/J-10/J-11.
  The spec's "frontend test" requirements are satisfied by grep + build + browser QA, not by a JS unit test.
- **Browser QA (load-bearing this iteration):** Honor the documented **Chrome-MCP headless render
  throttle** — if pixels are blank (hidden-tab throttle, not an app bug), verify the journey via the
  backend endpoints the UI calls (`GET /api/sessions`, `GET /api/sessions/{id}`, `POST /api/auto-sessions`,
  `POST /api/auto-sessions/{id}/stop`) and the persisted `autoRun` block. Use **tiny budgets**
  (≤ 2 iterations, short date range, cheapest model, lenient targets) so verification stays fast/cheap.

## Critical Gate for Reviewer / Auditor (do not skip)
- **B1+B2 is ONE design.** **FAIL the iteration** if `to_thread` is applied to the controller's `autoRun`
  writes **without** serialization against `/stop` (that splits the currently event-loop-atomic RMW and
  drops a concurrent stop request — TOCTOU). Require the regression test as proof.
- **Single-source poll discipline.** Read `autoRun` only from `GET /api/sessions/{id}`. Do **not** add a
  parallel status endpoint and do **not** recompute "best"/scores in the browser — after this iteration the
  backend `RobustScorer` is the sole "best" definition. (This is exactly the drift the coherence-auditor FAILs.)
- **No eager heavy-payload parse** on the list/open poll path; lazy iteration detail preserved.

## Scope, Alignment & Assumptions
- **Aligned with `docs/goal.md`:** advances Layer-1 Must-have journeys J-08/J-10/J-11; respects every
  anti-goal (only the backend runs the iterate loop after rewire; `autoRun` survives reload from the
  durable store; event loop stays responsive; lightweight GET poll; same file store / no schema fork;
  reuses `BacktestPipeline`). No drift detected.
- **Out of scope (excluded):** all of Layer-2 (J-12…J-16: open-universe search, hard token/USD enforcement,
  SCREEN/PROMOTE, global-history warm start, leaderboard/overfit-gating UI); appending into an existing
  session (Auto Run mints a **new** backend auto-session seeded from the baseline iteration's NL + params
  and it appears in the Session picker — reuses the iter-1 endpoint unchanged); any `shared/contracts.py`
  change; SSE for the auto-session (polling the lightweight GET is sufficient).
- **Data-contract additions: NONE.** Every surfaced value (`autoRun.status`, `stopReason`,
  `bestIterationId`, `budget` counters) is already registered (the three Layer-1 rows added iter-1). The
  internal stop signal (`stopRequested` or a new top-level stop-flag key under shape b) is a control flag,
  not a displayed value → no Data-Contract row. A blueprint **Notes** clarification reflecting the
  retirement of the in-browser scorer/loop is an additive edit only.
- **Assumptions (documented, not blocking):**
  1. Auto Run click mints a **new** backend auto-session (Option A in the spec), seeded from the selected
     baseline iteration's NL + params; in-place continuation is explicitly out of scope.
  2. `max_wall_clock_sec` default is a small bounded value (e.g. tens of seconds, sized so a ≤2-iteration
     tiny-budget run completes quickly in QA) — developer picks a sensible bound; not user-gated.
  3. Poll cadence ~2–3 s; stop polling at any terminal status; resume polling on reload if the loaded
     `autoRun.status` is active.
  4. The pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` is a known
     carry-forward on an untouched module — **not** a regression for this iteration.

## References
- iter-1 dev handoff: `docs/handoffs/goal-financial_free-iter-1-dev.md`
- iter-1 audit (Recommended Next Step #1 = this iteration's B1+B2): `docs/handoffs/goal-financial_free-iter-1-audit.md`
- Blueprint (IA + data contract; reserves both UI homes): `runs/goal-session-financial_free/state/blueprint.md`
- Phase spec: `docs/phases/goal-financial_free-iter-2.md`
