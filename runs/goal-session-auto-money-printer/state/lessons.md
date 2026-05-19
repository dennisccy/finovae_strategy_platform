# Goal Session auto-money-printer — Lessons Learned

Append-only ledger of takeaways from prior iterations. The goal-evaluator
appends one entry per iteration; the goal-decomposer reads this file before
planning each iteration to avoid repeating known pitfalls.

Each entry should be 1-3 sentences capturing a non-obvious lesson — surprising
failures, regression triggers, or decisions that worked well. Avoid
restating the verdict (the evaluator-log.md already does that).

## iter-0 — 2026-05-19T01:45:00Z

**Verdict:** CONTINUE
**Lesson:** J-02 ("browse run history") is *partial*, not passing, in the
core platform a prior session marked GOAL_ACHIEVED: selecting an older run
reloads its spec+metrics into the LEFT conversation panel but the RIGHT
analysis panel (trades table + equity curve + WF) stays pinned to the latest
run and never re-binds. This is easy to misread as "history works" because
the left panel does update — any iter must verify the prior run's *trades
table* actually reloads, not just its summary.
**Applies to:** any iter touching session/run-history selection or the
right-hand analysis panel (`apps/frontend` `SessionContainer.tsx` /
`IterationPanel.tsx` / `useBacktest.ts`); also the build iters for J-07–J-16,
which must not regress this existing manual-history path.

## iter-1 — 2026-05-19T07:20:00Z

**Verdict:** CONTINUE
**Lesson:** J-08's "live tracking" passes the happy path but the in-session
`AutoRunBar` can show a *stale terminal* status for a freshly-opened
still-running session when many `SessionContainer`s are mounted and the user
switches sessions rapidly (only masked because the session-list running
spinner is independently correct). This is a real ownership/concurrency bug
(per-session status not authoritatively re-derived on mount/switch), not
cosmetic polish — it will become a hard correctness failure once J-10 makes
the backend the single source of truth and deletes the in-browser loop.
Separately: the canonical `ui-test-results.md` headline was a *stale pre-fix
FAIL* reconciled to PASS by the auditor — never trust that headline alone;
verify the post-fix source diff + the QA MODE-2 (full-mode) report.
**Applies to:** iter-2 J-10/J-11 and any iter touching
`apps/frontend/src/components/SessionContainer.tsx` /
`AutoRunBar` / `apps/frontend/src/hooks/useBacktest.ts` autoRun status wiring —
J-10 MUST harden AutoRunBar ownership (re-derive per-session status on
mount/switch), not just rewire the button. Also: any evaluator reading a
reconciled UI-test artifact must cross-check source diffs + QA MODE-2, not the
top headline.

## iter-2 — 2026-05-19T12:30:00Z

**Verdict:** CONTINUE
**Lesson:** A timing-based "event loop not blocked" guard that stubs the
backtest with `await asyncio.to_thread(time.sleep, …)` is a FALSE guard:
`time.sleep` *releases* the GIL, so it can never reproduce the real
starvation. The actual root cause was that the RestrictedPython engine is
pure-Python GIL-holding CPU work, and `asyncio.to_thread` offload still shares
the API worker's GIL — so a *continuous* headless loop starves every other
file-IO thread (the `/api/sessions` poll, the stop endpoint). The correct fix
required real process isolation: a `multiprocessing` `spawn` child running the
unmodified `BacktestPipeline` (`auto_session.py:121-291`), and a guard that
deterministically asserts `child_pid != os.getpid()` (not a timing bound).
Separately: the iter-1 lesson held — the live poll's `tick` re-armed only on
the fully-successful path, so a single GIL-starved `apiLoadSession()→null`
permanently froze the AutoRunBar until a manual reload; the fix was re-arming
in a `finally`.
**Applies to:** any iter touching the headless/automated loop or
`auto_session.py`; any iter asserting "event loop non-blocking" or adding
per-round CPU/LLM work under a continuous server-side loop (directly relevant
to iter-3 Optimizer J-12–J-16, which adds SCREEN/PROMOTE + planner work each
round); any frontend live-poll/`setTimeout`-chain change (re-arm in `finally`,
never only on success).

## iter-3 — 2026-05-19T17:40:00Z

**Verdict:** CONTINUE
**Lesson:** The B1 carried fix ("skip the post-`generate` `insights` call once
a spend cap is hit, to tighten the one-call tolerance") has a non-obvious
cross-path trap: `_build_cost_tracker` sets the **configs cap == `max_iter`**
on the *pinned* path (`auto_session.py:497-507`), so on the **final pinned
iteration** `would_exceed()` returns the `"max-configs"` sentinel — a naive
"skip insights whenever `would_exceed()` is truthy" would silently suppress
that legitimate in-flight iteration's insights and regress J-07–J-11, and
`test_pinned_path_unchanged_by_open_universe_addition` does **not** assert
`insight_calls` so nothing would catch it. The correct fix must gate only on
true spend caps `{"ai-tokens","usd","wall-clock"}` (never `"max-configs"`,
which only gates *starting* a new config, not finishing an in-flight one) and
must ship with an `insight_calls`-on-final-pinned-iteration regression
assertion.
**Applies to:** any iter touching the `auto_session.py` budget/`would_exceed`
loop or the post-`generate`→`insights` call sequencing (directly: the J-14
iteration that carries the B1 fix) — distinguish the `max-configs` sentinel
from spend caps, and add the pinned-path `insight_calls` guard before changing
in-flight LLM-call gating.

## iter-4 — 2026-05-19T18:19:36Z

**Verdict:** CONTINUE
**Lesson:** A `status.json` of `blocked`/`closure_failed` (phase-closure
CLOSURE-FAIL) is NOT automatically a goal-mode REGRESSION. Here it was caused
solely by two UI-test-design artifacts (`reports/phase-…-ui-test-plan.md`,
`…-what-to-click.md`) being transient stub placeholders after
`ui-test-design-phase.sh`'s Claude CLI exited code 1 — an artifact-completeness
gate trip with a one-command outer-loop remediation, NOT an implementation,
quality, journey, or anti-goal failure (the closure verdict itself, QA, and the
audit all explicitly say so, and the stub's substance was independently verified
in ui-test-results.md + 6 screenshots + the audit source read). The evaluator
must separate "pipeline-tooling artifact gap, downstream-owned" from "a prior
passing journey broke / a critical anti-goal was violated"; only the latter is
REGRESSION. Surface the remediation command in next-step (outer-loop action,
not a developer/source fix, not the evaluator's fix) so the stub is regenerated
before the iteration closes — but do not let it flip the journey/anti-goal
verdict.
**Applies to:** any iteration where `status.json` is `blocked`/`closure_failed`
or the closure verdict is CLOSURE-FAIL — check whether the block is an
implementation/journey/anti-goal failure or a transient downstream
pipeline-artifact gap before considering REGRESSION/ESCALATE.

## iter-5 — 2026-05-19T21:15:00Z

**Verdict:** CONTINUE
**Lesson:** Two non-obvious takeaways from the J-15 verification. (1) For a
"read-only mine of prior artifacts" anti-goal, a *write-primitive scan of the
entire added diff* (`grep -E '\.write\(|open\([^)]*[\"'"'"']w|json\.dump|\.unlink|
\.rename|shutil\.|os\.remove|derive_session_tabs'` over `git diff HEAD`) is a
**stronger** structural proof than a content-hash before/after assertion alone
— hashes only verify the *one* run that's tested, the scan forecloses every
*possible* future write at source level. The only legitimate writes were
`session_store.append_activity_entries` + `_update_autorun` on the **current**
session. Use this scan as the first check on any future "read-only X" claim.
(2) The durable-store anti-goal (`BACKTEST_STORE_DIR` MUST NOT be `/tmp`)
implicitly *prevents* a browser-QA test plan from achieving an "empty store"
precondition without restarting the backend with a different env — `~113`
prior sessions accumulate by design. When a J-15-style test needs a known
initial state (empty history, single F1 family, etc.), ship the assertion as a
deterministic isolated-store **unit test** with the `store` fixture; do NOT
expect browser-QA to produce empty/isolated state, and do NOT mark the unit
proof as a "fallback" — it's the primary proof, the live browser run is the
observable corroboration.
**Applies to:** Any future iter touching `session_store` reads, claiming
read-only behaviour on prior artifacts, or whose test plan presupposes
isolated/empty durable-store state. Especially iter-6 (J-16 leaderboard /
overfit-gating) which will read promoted iterations across the same store.
