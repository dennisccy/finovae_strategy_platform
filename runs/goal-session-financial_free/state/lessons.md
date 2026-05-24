# Goal Session financial_free — Lessons Learned

Append-only ledger of takeaways from prior iterations. The goal-evaluator
appends one entry per iteration; the goal-decomposer reads this file before
planning each iteration to avoid repeating known pitfalls.

Each entry should be 1-3 sentences capturing a non-obvious lesson — surprising
failures, regression triggers, or decisions that worked well. Avoid
restating the verdict (the evaluator-log.md already does that).

## iter-0 — 2026-05-23T01:01:12Z

**Verdict:** CONTINUE
**Lesson:** A functionally-green J-02 (run-history browse) does NOT prove the eager-load
anti-goal is satisfied: the `GET /api/sessions` list path and the per-iteration detail
fetch are correctly lazy, yet the single-session OPEN path `GET /api/sessions/{id}` still
ships ~245KB and embeds `equity_curve` in its summary nodes. Heavy detail being lazy does
not mean the open payload is lean — these are separate code paths that must be checked
independently.
**Applies to:** any iter touching `apps/backend/backend/session_routes.py` /
`session_store.py` or the session-open contract, and the coherence-auditor when a diff
reaches the sessions surface — deliver a definitive verdict on whether the open-path
`equity_curve` embed violates the "no eager full-payload parse" anti-goal.

## iter-1 — 2026-05-23T08:33:05Z

**Verdict:** CONTINUE
**Lesson:** The obvious fix for the "store writes block the event loop" note (wrap the controller's `session_store` calls in `await asyncio.to_thread`) must NOT be applied alone — it converts the controller's currently event-loop-atomic read-modify-write of the persisted `autoRun.stopRequested` flag into an interleaved RMW against the lock-free `/stop` writer, *widening* a TOCTOU race that drops a stop request. The non-blocking fix (B1) and the stop-flag integrity fix (B2) are one design problem (single-writer / async lock), to be solved together when J-10/J-11 actually claim the stop journey. Also: byte-shape identity between the manual SSE path and the headless loop was guaranteed by *extracting* serialization into one shared `result_serialization.py` (not by a parallel reimplementation) — keep this single source when the frontend rewire lands; do not re-fork it.
**Applies to:** any iter touching `apps/backend/backend/auto_session.py` autoRun persistence, the `/stop` endpoint, or wiring `to_thread` around the controller's store I/O (J-10/J-11/iter-2); and any iter that changes backtest result/rating/walk-forward serialization (keep `result_serialization.py` as the one source).

## iter-2 — 2026-05-23T10:11:19Z

**Verdict:** CONTINUE
**Lesson:** UI-load-bearing journeys keep failing to capture browser pixels for a *different* reason each iteration — iter-0 was the hidden-tab render throttle (blank pixels), iter-2 the Vite dev server returned HTTP 000 (up at QA start, **down by the browser-qa window**). Both fell back to backend-endpoint + static-code verification, which is spec-sanctioned and sufficient for a CONTINUE, but it means J-08's "live strip updates / cards stream without reload" and J-10's reload-survival have *never* been confirmed at the pixel layer — the debt is now compounding into Layer-2 (also UI-bearing). Don't just launch the frontend before browser-qa; **health-check it is still serving for the whole window** (and re-probe mid-run), or the pixel debt will silently roll forward again.
**Applies to:** any iteration whose Definition-of-Done lists browser journeys by ID as load-bearing (Layer-2 J-16 leaderboard UI; any future UI-surfacing iter) — verify the frontend stays up across the entire browser-qa window, and treat an accumulated unverified-pixel journey as a debt to clear, not re-defer.

## iter-3 — 2026-05-23T21:48:32Z

**Verdict:** CONTINUE
**Lesson:** The dedicated browser-qa-agent has now SKIPPED two iterations running (iter-2, iter-3) because the FE/BE were torn down in *its* window (HTTP 000) — even though the full-QA agent in the *same* iteration had live services and captured real evidence. The two passes are not sharing a service lifecycle, so a pixel-layer journey (J-08/J-10 status-strip chips) can stay unconfirmed across 3+ iterations while every functional check passes. iter-3 also hit a *second* contention mode: a concurrent QA run on another port held the Chrome-MCP foreground tab, suspending the Finovae tab to an empty DOM (compounding the documented hidden-tab throttle). The decompose/dispatch wrapper must run browser-qa against the same live services the full-QA uses, in the same window, on an uncontended foreground tab — otherwise "clear the live-pixel debt" keeps slipping no matter how many times the spec mandates it.
**Applies to:** any iteration whose DoD includes browser/pixel verification of an auto-session or live-polling UI surface; especially the J-14 iteration (new SCREEN/PROMOTE activity-log UI) that must finally capture the J-08/J-10 strip + reload-mid-run pixels.

## iter-4 — 2026-05-23T23:05:08Z

**Verdict:** CONTINUE
**Lesson:** Two non-obvious takeaways. (1) **A spec mandate to "try harder" does not fix an environmental/harness root cause.** iter-4's spec explicitly ordered the 3-iteration pixel debt cleared and declared "services down is NOT an acceptable reason this time" — yet browser-qa SKIPPED again ("frontend not running") and QA's own FE :3692 died mid-window (no listener from poll 3, confirmed NOT the Chrome-MCP throttle). The blocker is the `browser-qa-phase.sh` frontend lifecycle (FE not started / torn down / crashes within the window), so the fix is to harden the harness FE startup + health-re-probe (or formally accept endpoint-layer proof for display-only journeys), NOT to re-issue the instruction a 5th time. (2) **A too-short live-QA date range silently makes walk-forward vacuous.** The live open-universe QA used a 2-month range (2024-01-01→2024-03-01) against the default 6mo-IS/3mo-OOS walk-forward config, so the PROMOTE node produced 0 windows (`errors: ['Not enough data to form any IS+OOS windows']`) → wfe 0.0 → best=None. That is a *correct gated outcome* and doesn't fail J-14 (whose acceptance needs the staging, not a marked best — and the positive best-marking is proven hermetically), but it left the live promote→best path untested. Any WF-dependent live QA MUST use a range ≥ IS_months+OOS_months (≥9mo at defaults) or the walk-forward, and anything keyed off it, is silently empty.
**Applies to:** (1) every future iteration that runs browser-qa for the auto-session UI (J-08/J-10/J-14/J-15/J-16) — verify the FE process lifecycle before requiring pixel claims. (2) any iteration whose live QA exercises walk-forward (J-03, J-09, J-14, J-16) — pick a date range long enough to form ≥1 IS+OOS window.

## iter-5 — 2026-05-23T23:41:14Z

**Verdict:** CONTINUE
**Lesson:** **An iteration can finish "green" in an isolated worktree and leave ZERO code in the real tree — a passing pytest cache is NOT evidence the work persisted.** iter-5's J-15 (global-history warm start) was fully built and its 8 named tests ran green (proven by `apps/backend/.pytest_cache/v/cache/nodeids` listing them while `lastfailed` held only the pre-existing red), yet the working tree has none of it: no `history_scope`/`mine_history_families`/`history_planner.py`, `status.json` frozen at `current_step:"starting"` with `changed_files:[]`, no dev/review/qa/audit artifacts, and `git diff HEAD -- apps/` is empty. The work was done in an ephemeral `isolation: worktree` copy that was removed without merging back, and it is **not recoverable from git** (HEAD still iter-4; the iter-5 snapshot commit differs by one telemetry line; the only `history_scope` in dangling commits belongs to a *different, abandoned* session — `auto-money-printer` — so cherry-picking would import the wrong lineage). Two consequences future evaluators must internalize: (a) **judge the target journey against the actual tree (grep the source / hit the endpoint), never against the dev handoff or the decomposer's blueprint Notes** — the coherence-auditor correctly flagged COHERENCE-WARN because `blueprint.md` had been advanced to describe J-15 as landed while the code was absent; (b) the verdict is **CONTINUE, not REGRESSION/STALLED** — nothing that was passing broke (empty `apps/` diff guarantees J-01…J-14 are byte-identical), and the next step is fully specified, so this is a lost-work redo, not intractability. The load-bearing fix the next dispatch MUST adopt: **assert persistence before declaring done** (`git diff HEAD -- apps/` non-empty + `status.json.changed_files` populated + dev handoff present). If the harness loses work this way twice in a row, the second occurrence WOULD justify STALLED/ESCALATE.
**Applies to:** any goal-mode iteration that runs the developer in a worktree (the framework default) — verify the diff landed in the real tree before evaluating; and any evaluator facing an iteration with missing handoff/review/QA artifacts — treat "artifacts absent + status stuck at 'starting'" as a lost-work signal, grep the tree to confirm, and CONTINUE with a re-land + persistence-check recommendation rather than trusting a green test cache.

## iter-6 — 2026-05-24T01:03:13Z

**Verdict:** CONTINUE
**Lesson:** The DoD-0 persistence gate that iter-5's failure motivated *worked*: iter-6 re-landed J-15 with a non-empty `git diff HEAD -- apps/` (7 files, +1123/−9), and dev/review/QA/audit/evaluator each re-ran the gate against the live tree — the empty-diff lost-work failure mode is now caught by construction. Separately, a journey-classification turning point arrives at J-16: every headless journey J-07–J-15 reused the EXISTING `auto-run` Activity-Log render branch, so endpoint-layer proof (`GET /api/sessions/{id}`) was a legitimate, spec-sanctioned substitute for the Chrome-MCP headless throttle; J-16 (overfit-gating leaderboard UI) is the FIRST journey since the auto-session UI to add a genuinely NEW front-end render path, so the recurring "pixel debt" stops being deferrable — endpoint-layer proof cannot close a new render surface, and the `browser-qa-phase.sh` `:3000`-vs-offset-`:3692` health-probe root cause must be fixed (or a real foreground browser-QA window budgeted) for J-16.
**Applies to:** the final J-16 iteration specifically, and any future iter that adds a NET-NEW front-end render path (component/page/render branch) — such an iter MUST NOT accept endpoint-layer proof as a substitute for browser QA, and MUST re-apply the `git diff HEAD -- apps/` persistence gate before declaring done.

## iter-7 — 2026-05-24T03:20:00Z

**Verdict:** CONTINUE
**Lesson:** Documenting the harness port fix in the *dev handoff prose* does NOT make browser-QA succeed — the browser-qa-agent re-ran its hardcoded `:3692`/`:8692` probe (frontend dead), saw nothing, and SKIPPED all 10 tests, while the dev handoff's correct `CHAIN_FRONTEND_PORT=3691 CHAIN_BACKEND_PORT=8691` export sat unread. The fix must live in `browser-qa-phase.sh` itself (auto-detect the deterministic offset `base + sha1(repo)%1000`), not in a handoff. Separately: a fully-green data/endpoint layer + a single *empty* full-app render frame is NOT evidence a genuinely-new render component paints its rows — for J-16 the leaderboard rows were never captured (hidden-tab throttle in a contended QA env), so "endpoint proves the data, therefore the pixels are fine" is exactly the inference the spec forbade for a new render path.
**Applies to:** any goal-mode iteration whose DoD makes browser/pixel proof LOAD-BEARING for a NEW front-end render path — fix the `browser-qa-phase.sh` port probe (or run a real foreground/uncontended window) BEFORE the QA window, and treat a repeated skip on the same unfixed harness bug as a process stall, not a deferral.

## iter-8 — 2026-05-24T05:30:00Z

**Verdict:** GOAL_ACHIEVED
**Lesson:** The load-bearing pixel gate paid off on the very iteration it was meant to close: the first real-browser capture exposed a whole-app-blanking crash that 6 consecutive browser-QA SKIPs and every data-layer test had hidden. `App.tsx` keeps a `SessionContainer` (hence a `useBacktest`) mounted for EVERY session, so a single legacy record whose `autoRun` predates the `budget` schema (`currentIteration`/`spend`, no `budget` block) made an unguarded `autoRun.budget.iterationsDone` throw with no error boundary → the entire app blanked, leaderboard included. Two transferable rules: (1) a net-new render path can carry a crash invisible to endpoint/data-layer proof — never accept "the endpoint returns the right JSON, therefore the pixels are fine"; (2) when one component mounts per-record across a durable store that has accumulated multiple schema generations, render-derivations MUST null-guard every post-schema field (`obj?.newBlock?.field`), because old records will be missing it. Separately: fixing a harness SCRIPT (`browser-qa-phase.sh` port probe) is necessary but NOT sufficient to make the native browser-qa step pass — it still SKIPPED here because services were simply down in its window (the port-reconciliation correctly cannot fire when the base port is also dead); reliable `ensure_services_running` (actually booting the app within the step's own window) is the other half. The spec's pre-authorized Playwright (visible-context) + seeded-component capture mechanisms were the anti-stall floor that let the iteration close anyway.
**Applies to:** any iter adding/verifying a net-new render path (insist on real pixels, not endpoint proof); any component that mounts once per persisted record in a long-lived file store (guard every schema-evolved field); any iter relying on the native browser-qa step (verify services actually boot in-window, not just that the port math is right).
