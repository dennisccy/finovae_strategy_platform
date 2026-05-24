**Verdict:** COHERENCE-PASS

# Coherence Audit — goal-financial_free-iter-8

- **Session:** financial_free
- **Iteration:** 8 (target J-16 render proof → GOAL_ACHIEVED)
- **Audited diff:** `git diff 9d52cbff4535593f3d333495da5e7b9429cc21ce` (snapshot SHA resolved; matches `runs/goal-session-financial_free/iter-8/snapshot-sha`)
- **Blueprint:** `runs/goal-session-financial_free/state/blueprint.md` (unchanged this iteration — no `blueprint.reapproval-requested`)

## What changed (entire diff)

| File | Kind | Coherence relevance |
|---|---|---|
| `apps/frontend/src/hooks/useBacktest.ts` (+9/-1) | Render-derivation null-guard | Reads canonical `autoRun.budget` only — checked |
| `apps/frontend/src/components/IterationPanel.tsx` (4 lines) | Render gate on `autoRun?.budget` | No new surface/value — checked |
| `incredible_auto_dev/scripts/automation/browser-qa-phase.sh` (+67) | Verification harness (port probe + FE re-probe) | Coherence-neutral (harness script) |
| `runs/.../telemetry.jsonl`, `trace/.next-step`, `trace/trace.jsonl` | Bookkeeping artifacts | Not product code |

`apps/frontend/src/components/AutoSessionLeaderboard.tsx` is **NOT** in the diff (empty `git diff`, exit 0). Its verbatim reads survive verbatim: `entry.robustScore`, `entry.eligible`, `entry.gatingReason` read straight from `autoRun.leaderboard`, and best is still marked solely by `autoRun?.bestIterationId` (`AutoSessionLeaderboard.tsx:54,107,132-137`). The J-16 data contract is untouched.

## Step 1 — Data Contract check (the "numbers don't match" gate) → PASS

No new computing function, service, or endpoint was introduced. Both frontend edits are defensive null-guards, not new code paths.

- **`useBacktest.ts:482-490`** — `autoRunProgress` now derives from `autoRun?.budget ? { current: autoRun.budget.iterationsDone, max: autoRun.budget.maxIterations } : null`. The two values (`iterationsDone`, `maxIterations`) are read from the **canonical** `autoRun.budget` block served by `GET /api/sessions/{id}` (Data Contract row: "Budget counters … `GET /api/sessions/{id}` — `autoRun.budget` block … UI and API read the same tally"). Re-packaging the canonical fields into `{current, max}` for a progress readout is a permitted **re-format**, not a recomputation, and the guard adds no second/separate count — when `budget` is absent (legacy pre-schema records) it simply yields `null` (no readout). No duplicate computation, no non-canonical source.
- **`IterationPanel.tsx:260,283`** — `AutoSessionStatusStrip` render is gated on `autoRun?.budget` at both call sites. This only **suppresses** a render when the canonical `budget` block is missing; it introduces, recomputes, and re-sources nothing.
- **No new displayed value.** The change set can only suppress an existing readout on legacy records; it adds nothing to display, so there is no unregistered-value case (Part A5) and no synonym/re-derivation of an existing value.

## Step 2 — Information Architecture check (the "where do I find it" gate) → PASS

- **No new page, route, or feature.** Both edits modify existing components living in their already-registered home — the Right-panel "Iterations" surface (`AutoSessionStatusStrip` + `AutoSessionLeaderboard` inside `IterationPanel`). The leaderboard's canonical home (IA: "J-16 → Best badge / leaderboard → Right — Iterations") is unchanged.
- **No new navigation, no duplicate home, no parallel shell.** The single two-panel shell is untouched; nothing was added that needs a nav path.

## Step 3 — Subjective observations (advisory only) → none blocking

- The two guards are mutually consistent (`autoRun?.budget`). There is a deliberate and **correct** asymmetry: `AutoSessionStatusStrip` is gated on `autoRun?.budget` while `AutoSessionLeaderboard` remains gated on just `autoRun`. This is appropriate, not a defect — the status strip dereferences budget counters (would crash without `budget`), whereas the leaderboard reads `autoRun.leaderboard` and already returns `null` on empty, managing its own empty state. No formatting/labeling drift introduced.

## Scope note (informational, not a coherence finding)

The spec marks "modifying product polling/visibility logic … to defeat the Chrome-MCP throttle" OUT OF SCOPE. The `useBacktest.ts` edit is a render-derivation null-guard (crash fix), **not** poll/visibility logic — no timer, `setInterval`, or `visibilityState` is touched (confirmed in the diff; the inline comment states the same). Whether the crash fix was in-scope is a question for the reviewer/auditor; from the coherence lens it is clean because it touches neither the Data Contract nor the Information Architecture. The blueprint was deliberately not advanced ahead of code (no contract-ahead-of-code drift — the iter-5 WARN pattern is avoided).

## Conclusion

No Part A (Data Contract) or Part B (Information Architecture) violation. The only product changes are coherence-neutral defensive null-guards that read existing canonical values; the J-16 leaderboard surface, its verbatim reads, the single `RobustScorer`-derived best definition (`bestIterationId`), and the one serving endpoint (`GET /api/sessions/{id}`) all remain intact. The harness/bookkeeping changes are coherence-neutral. **COHERENCE-PASS.**
