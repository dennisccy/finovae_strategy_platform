**Verdict:** COHERENCE-PASS

# Coherence Audit — goal-financial_free-iter-2

- **Session:** financial_free  · **Iteration:** 2  · **Iter name:** goal-financial_free-iter-2
- **Auditor:** coherence-auditor
- **Snapshot SHA audited:** `2223a1bccf046a2410241e793b423c4c36eaa473` (`git diff <sha>` + working tree)
- **Blueprint:** `runs/goal-session-financial_free/state/blueprint.md`
- **UI surface map:** `reports/phase-goal-financial_free-iter-2-ui-surface-map.md` (present, used)

This iteration finishes Layer-1 by deleting the second in-browser iterate loop and its duplicate
`scoreIteration`, rewiring "Auto Run"/"Stop" to the existing backend command endpoints, and surfacing
the persisted `autoRun` block live. No new objective Data-Contract or Information-Architecture
violation. The iteration also **resolves** the iter-1 coherence §C.1 advisory (the legacy duplicate
scorer). Two trivial, non-blocking advisory notes are recorded below.

---

## Part A — Data Contract (objective → FAIL gate): PASS

| Check | Result | Evidence |
|---|---|---|
| **Duplicate computation of the robust "best" marker removed** | ✅ removed | `grep -rn scoreIteration apps/frontend/src/` → 0 hits; diff shows `scoreIteration` (def + 2 call sites) deleted from `useBacktest.ts`. Only remaining frontend match is the comment `useBacktest.ts:2135` ("backend RobustScorer is now the sole 'best' definition (no local score)"). |
| No client-side score/best recomputation left | ✅ none | `grep -rni 'robustscor\|computescore\|scoreiteration' apps/frontend/src/` → only the explanatory comment; no scoring code. The strip's best badge reads `autoRun.bestIterationId` (`AutoSessionStatusStrip.tsx:79-83`) — the canonical marker, sliced for display only. |
| Run state / stop reason / best / budget served from **canonical** `GET /api/sessions/{id}` | ✅ canonical | Live poll calls `apiLoadSession(sessionId)` (`useBacktest.ts:772`), i.e. the existing `loadSession` → `GET /api/sessions/{id}`. No new status endpoint added. |
| Poll uses the **lightweight** list/open path (no eager heavy-payload parse) | ✅ conforms | `mergePolledSession` (`useBacktest.ts:706-756`) appends lightweight nodes via `normalizeLightweightNode` and explicitly preserves heavy fields (`result`, `rating`, `insights`, `scriptCode`) for existing nodes; heavy detail stays lazy-loaded on selection. |
| New frontend API helpers hit **command** (not value-serving) endpoints | ✅ conforms | `sessionApi.ts`: `startAutoSession` → `POST /api/auto-sessions`; `stopAutoSession` → `POST /api/auto-sessions/{id}/stop`. Both are the unchanged iter-1 command endpoints; backend `auto_session_routes.py` exposes only `POST ""` and `POST /{session_id}/stop` (no new GET). |
| Status strip only **re-formats** canonical values | ✅ allowed | `AutoSessionStatusStrip.tsx` reads the `autoRun` block and applies display-only transforms (`.slice(0,8)`, `Math.round`, label maps `STATUS_META`/`STOP_REASON_LABEL`). No recomputation. |
| No new displayed value introduced | ✅ none | All surfaced values (`status`, `stopReason`, `bestIterationId`, budget counters) are already registered (the three Layer-1 rows). Blueprint diff is an **additive Notes clarification** only (2 rows' Notes columns; no canonical source/endpoint changed). |
| Backend: same file store, no parallel store / schema fork | ✅ conforms | `_save_auto_run` still reads/writes the same `session.json` `autoRun` block via `session_store.read_session_meta`/`write_session_meta` (`auto_session.py:79-91`); B1+B2 co-design adds only `_run_off_loop` (`to_thread`) + a per-session `asyncio.Lock`. No new file/store, no `.parquet`/sqlite, **`shared/contracts.py` untouched**. |

**Note on `Math.max` in the diff:** the two `Math.max` occurrences added to `useBacktest.ts`
(`maxIterations` clamp, `max_wall_clock_sec` floor, lines ~2168/2182) are **budget control-value
clamps**, not displayed-value computations. The pre-existing `sessionStatus.bestReturn =
Math.max(...totalReturn)` (`useBacktest.ts:795`) is **untouched** by this iteration (not in the diff)
and is a session-picker max-return summary aggregating canonical `total_return` — conceptually
distinct from the registered robust `autoRun.bestIterationId`. Neither is a violation.

## Part B — Information Architecture (objective → FAIL gate): PASS

| Check | Result | Evidence |
|---|---|---|
| New `AutoSessionStatusStrip` lives in its blueprint-reserved home (Right — Iterations) | ✅ correct home | Rendered by `IterationPanel.tsx` at the top of the Iterations panel in both the empty state (`:255-256`, "Waiting for the first iteration…") and the populated state (`:281`). Blueprint reserves "Right — Iterations → Automated-session status strip". |
| Auto Run / Stop controls stay in Left — Activity Log config bar | ✅ correct home | Controls unchanged in location; state now derives from `autoRun.status`. Matches blueprint "Left — Activity Log → Automated-session controls". |
| New auto-session reachable via the existing Header Session picker | ✅ conforms | `startAutoRun` → `onAutoSessionCreated(res.sessionId, label)` (`useBacktest.ts:2186`) → `App.tsx:handleAutoSessionCreated` adds the session to `liveSessions` and selects it. Matches blueprint ("the created session then appears in the Header Session picker"). |
| No new route / nav section / parallel shell | ✅ none | Single-page app; the strip is rendered inline inside an existing panel (0 extra clicks — visible immediately on the active session). No router/nav change; surface map confirms "New pages/routes: 0", "Navigation changes: no". |
| No duplicate home for an existing entity | ✅ none | The strip is the first home for the `autoRun` block (no prior page showed it); iteration cards continue to live in the one Iterations tree. |

## Part C — Advisory (WARN-only; does NOT affect the verdict)

1. **Blueprint run-state enum is missing `error` (pre-existing, documentation only).** The frontend
   `AutoRunStatusValue` (`sessionApi.ts`) and `STATUS_META` correctly include `'error'`, mirroring the
   backend's canonical `STATUS_ERROR` terminal status (`auto_session.py:79`, in `TERMINAL_STATUSES`).
   The blueprint Data-Contract prose enumerates only `queued / running / stopped / criteria-met /
   budget-exhausted / interrupted`. This is **not drift introduced this iteration** (the backend
   `error` status pre-exists from iter-1) and the frontend reads it from the canonical source — so no
   violation. *Suggested tidy:* the decomposer may add `error` to that row's enumerated values for
   completeness.
2. **"rounds" vs "iterations" label nuance.** The strip's budget counter shows `X/Y rounds`
   (`AutoSessionStatusStrip.tsx:67-68`, tooltip "Improvement rounds done / max") while the iteration
   tree header shows "Iterations (N)" (`IterationPanel.tsx`). These are related-but-distinct counts
   (budget improvement-rounds-done vs total tree nodes incl. baseline) and the strip's wording is
   tooltip-clarified and deliberate, so it is a minor terminology nuance, not a same-value formatting
   conflict.

---

## Summary

- **Part A (Data Contract):** PASS — the duplicate in-browser `scoreIteration` and second iterate loop
  are removed; the backend `RobustScorer` is the sole "best"/engine definition; the status strip and
  live tracking read exclusively from the canonical `GET /api/sessions/{id}` (lightweight, no heavy
  parse); the only new API helpers call the unchanged command endpoints; same file store, no schema
  fork, `contracts.py` untouched.
- **Part B (Information Architecture):** PASS — the new status strip is placed in its blueprint-reserved
  Right/Iterations home; Auto Run/Stop stay in the Left config bar; new sessions surface through the
  existing Header Session picker; no new route, nav section, parallel shell, or duplicate home.
- **Part C:** two trivial, non-blocking advisory notes (blueprint `error` enum completeness; "rounds"
  label nuance).
- **Bonus:** this iteration **closes** the iter-1 coherence §C.1 advisory (legacy duplicate scorer
  retired) — a net coherence improvement.

No objective violation found. **COHERENCE-PASS.**
