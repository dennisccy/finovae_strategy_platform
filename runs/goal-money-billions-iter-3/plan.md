# goal-money-billions-iter-3 Execution Plan

Resolve the last open anti-goal: `GET /api/sessions/{id}` must stop eager-loading every
iteration's `result`/`rating`; the frontend lazy-loads heavy detail on selection. Plus
J-04 OOS-aware insights gets its first dedicated evidence (verification-only, no code).

**Goal alignment:** Directly implements `docs/goal.md` success criterion ("opening a
session renders the list without parsing full per-iteration result/rating; heavy detail
fetched lazily on selection") and resolves anti-goal #10. No drift, no scope creep —
spec explicitly excludes pagination/caching/new endpoints/storage changes.

## What to Build

- **Backend — stop eager-load in `get_session`** (`session_routes.py:142-171`): replace
  the per-iteration `read_iteration_full(session_id, parts[1])` call (line 154) with
  `read_iteration_meta(session_id, parts[1])`. `meta.json` is written by `write_iteration`
  excluding `_BULK_KEYS = {prompt, scriptCode, insights, result, rating, timeframeResults}`
  (`session_store.py:262`), so the lightweight node already carries `id`, `status`,
  `timestamp`, `params`, `strategyName`, parent linkage, selection and **no** heavy
  payload. Keep `meta`/`activityLog`/`backtestParams`/`selectedIterationId` and the
  404 condition behaviorally identical. Do NOT add a new endpoint; the lazy detail path
  `GET /{session_id}/iterations/{iteration_id}` (`session_routes.py:229-237`) already
  exists and stays unchanged.
- **Frontend — typed lazy fetch** (`sessionApi.ts`): add a GET sibling to
  `deleteIterationFromStore` (lines 139-150) — e.g. `fetchIterationDetail(sessionId,
  iterationId)` hitting `GET /api/sessions/${id}/iterations/${iterationId}`, returning the
  full `IterationNode` (or null on failure).
- **Frontend — lazy-load on hydration + selection** (`useBacktest.ts`): hydration
  (~492-570) keeps the lightweight list; lazy-fetch the full node for the
  initially-resolved/selected iteration so the detail view + `results` phase still render
  on session open. The `selectIteration` callback (line ~1480) must lazy-fetch + merge
  `result`/`rating`/`insights`/`scriptCode` into the in-memory node when the selected
  node lacks `result`.
- **Frontend — prevent write-amplification** (`useBacktest.ts`, highest correctness
  risk): `savedIterationVersionRef` is seeded at hydration as
  `` `${status}:${insights?.suggestions?.length ?? 0}` `` (line 544) — on lightweight
  nodes that is `complete:0`. When lazy detail merges real insights the save effect
  (line 582) recomputes a different key and **re-persists already-stored iterations**.
  When merging lazy detail into a node, update `savedIterationVersionRef` (and respect
  `savedActivityCountRef`) so the save effects do NOT re-save lazy-loaded detail.
- **Frontend — detail pane loading/error states** (`IterationPanel.tsx` /
  `SessionContainer.tsx`): explicit loading indicator while the per-iteration detail
  fetch is in flight; explicit error state if it fails (no silent blank pane). History
  list/tree + selection must work against lightweight nodes (don't assume
  `result`/`rating` until a node is selected and loaded).
- **J-04 (verification-only, NO code change):** confirm via browser-QA that after a
  walk-forward run, requesting/regenerating insights yields ≥1 OOS/walk-forward/WFE/
  robustness-aware suggestion. `insights_generator.py` and `/api/generate-insights`
  MUST NOT be modified.

## Agents Required

- backend-data: yes — one-line swap in `get_session` + backend response-shape tests.
- frontend-ux: yes — `sessionApi.ts` lazy fetch, `useBacktest.ts` hydration/selection
  lazy-merge + save-guard fix, detail-pane loading/error states.
- developer: yes — both backend and frontend changes above (TDD: backend tests first).

## Frontend Present
yes

## Files to Create/Modify

- `apps/backend/backend/session_routes.py` — `get_session`: `read_iteration_full` →
  `read_iteration_meta` (line 154); response shape otherwise unchanged.
- `apps/backend/tests/test_session_routes.py` *(new)* — API/response-shape tests (see
  Key Test Scenarios). Use a temp `BACKTEST_STORE_DIR` fixture + `write_iteration` to
  seed a completed iteration, then assert on `get_session`. FastAPI `TestClient` against
  `backend.api.app` OR directly awaiting the `get_session` coroutine are both acceptable
  (no existing API-test harness; `test_session_store.py` calls store fns directly —
  match that style, real on-disk fixture, no mocking the store).
- `apps/frontend/src/lib/sessionApi.ts` — add `fetchIterationDetail` (typed GET of one
  full iteration node).
- `apps/frontend/src/hooks/useBacktest.ts` — hydration lazy-load of resolved node;
  `selectIteration` lazy-fetch+merge; `savedIterationVersionRef` guard so merged detail
  is not re-saved; detail loading/error state exposed from the hook.
- `apps/frontend/src/components/IterationPanel.tsx` (and/or `SessionContainer.tsx`) —
  render detail-pane loading + error states; tolerate lightweight nodes in list/tree.

## UI Evolution

- New user-facing capability: none functional — behavior preservation + scalability
  (opening a session with many runs no longer parses every run's full payload).
- New information displayed: a brief loading indicator in the run-detail pane while
  heavy detail is lazily fetched on selection; an explicit error state if that fetch
  fails.
- New user actions: none. Selecting a run from history is unchanged for the user.
- UI surface changes: run-history list/tree + run-detail pane gain a lazy
  loading/error state. No layout restructure.
- Navigation changes: none.

## Visual Requirements

- Component patterns: reuse the existing `IterationPanel`/`SessionContainer` detail
  surface — no new component library elements; match existing dark analytical-
  workstation styling (Tailwind tokens already in use, Recharts for curves).
- Layout: unchanged two-panel session view (history left/tree, detail right).
- Key visual effects: none new — match the established panel styling.
- States to handle: detail-pane **loading** (clear spinner/skeleton, not a blank
  panel), detail-pane **error** (visible message, list still usable), and
  selecting an in-progress/error node with no `result` must not crash the detail view.

## Key Test Scenarios

**Backend (must pass — proves anti-goal resolved, not inferred from J-02):**
- `GET /api/sessions/{id}` (or `get_session`) for a session with ≥1 completed iteration
  → every `iterationHistory` entry contains **no** `result`, `rating`, `equity_curve`,
  or `trades` key (assert exact key absence, not present-but-null).
- `GET /{session_id}/iterations/{iteration_id}` for that same iteration still returns
  the full node **with** `result`/`rating` (lazy path intact).
- `get_session` still returns correct `meta`/`activityLog`/`backtestParams`/
  `selectedIterationId`; lightweight list preserves ordering + the fields the frontend
  tree/selection needs (`id`, `status`, `timestamp`, `params`, strategy name).
- 404 for a non-existent session unchanged.
- `read_iteration_full` no longer referenced by `get_session` (code inspection by
  reviewer/auditor).

**Browser (browser-qa-agent) — by journey ID:**
- **J-02 (primary regression watch):** complete ≥1 backtest, open a *distinct prior*
  run from history (select more than one, re-select) → strategy spec, metrics, trades
  reload into the detail view via the lazy fetch. Cross-layer bonus: inspect the
  `GET /api/sessions/{id}` network payload is lightweight.
- **J-04:** on a completed run, run walk-forward, then request/regenerate insights →
  capture a **dedicated, distinct screenshot of the insights pane** showing ≥1
  suggestion referencing OOS / out-of-sample / walk-forward / WFE / robustness. A
  J-04 capture that duplicates the J-03 walk-forward panel is INVALID and fails J-04
  (lessons.md iter-2).
- **J-01, J-03, J-05, J-06 (no-regression smoke):** J-01 NL run still appends a new
  `run_id` to history; J-03 walk-forward still renders WFE badge + per-window table +
  combined OOS curve; J-05 symbol/timeframe controls still populate from endpoints;
  J-06 warm-cache re-run still deterministic and appears in history.

**Error cases:**
- Per-iteration lazy fetch failure → detail pane shows explicit error state, session
  list still renders.
- Selecting an iteration with no `result` (error/in-progress) does not crash detail.

## Assumptions / Notes

- **Independence rule (lessons.md iter-0):** J-02 has passed every prior iteration *with*
  the eager-load present — a green J-02 does NOT prove the anti-goal resolved. Resolution
  rests on (a) final `get_session` source no longer calling `read_iteration_full` and
  (b) the backend response-shape test asserting heavy-payload absence.
- **J-04 evidence rule (lessons.md iter-2):** browser-QA must save a NON-duplicate
  insights-pane screenshot after a walk-forward run; evaluator rejects a J-03 duplicate.
  This is the iteration that finally closes the long-open J-04 OOS soft gap.
- No frontend unit-test harness exists (`apps/frontend` has no `*.test.*` / config) —
  per spec the browser J-02 flow is the binding frontend evidence; the handoff must
  state this explicitly.
- J-04 insight regeneration needs `OPENAI_API_KEY` in the QA env (capability/key
  already exercised in prior iterations). Verification-only; no code change.
- Pre-existing baseline failures (e.g. `test_directions_cache.py`, byte-identical to
  HEAD) are out-of-scope pre-existing — document, do not fix here.
- Watch `migrateSession` on lightweight nodes (no `result`/`insights`) — verify it does
  not drop/throw on absent bulk fields during hydration.
