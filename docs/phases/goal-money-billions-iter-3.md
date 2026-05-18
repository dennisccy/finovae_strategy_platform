# Goal Iteration 3 — Resolve the `GET /api/sessions/{id}` eager-load anti-goal + assert J-04 OOS-aware insights

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** money-billions
- **Iteration:** 3
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes
- **Target journeys:** J-02, J-04
- **Required-still-passing journeys:** J-01, J-03, J-05, J-06
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - No hard-coded credentials, API keys, or tokens in source files (keys only via env / git-ignored `.env`).
  - The RestrictedPython sandbox MUST block file I/O, network, `exec`/`eval`, `__import__`, `open`, and `os`.
  - No lookahead: a generated signal must never observe future bars.
  - No nondeterministic backtests (slippage is seeded; identical inputs → identical output).
  - No dependency on a paid SaaS service other than Anthropic/OpenAI (already in Constraints).
  - The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
  - OHLCV market data MUST be cached as a single Parquet file per (symbol, timeframe) — NOT one CSV or file per calendar day — and MUST NOT be re-fetched from Binance when a covering local cache exists.
  - `BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart.
  - No relational database or SQLite is introduced for OHLCV, session, or directions storage (Parquet + durable file store only).
  - **`GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint.** ← **this iteration resolves this anti-goal**

## GOAL

Opening or reloading a session renders its run-history list without the backend
parsing every iteration's heavy `result`/`rating` payload; the selected run's full
detail (spec, metrics, trades) is lazy-loaded on demand and still reloads correctly,
and AI insights are demonstrably OOS-aware after a walk-forward run.

## BACKGROUND

This is the final blocker to GOAL_ACHIEVED. All six Must-have journeys currently pass,
but the goal-evaluator never declares GOAL_ACHIEVED while an anti-goal is unresolved.
One minor anti-goal remains: `apps/backend/backend/session_routes.py:142-171`
`get_session` loops every iteration directory and calls `read_iteration_full(...)`
(line 154), inlining each iteration's `result.json`/`rating.json` into the
`GET /api/sessions/{id}` response — exactly the eager-load the anti-goal forbids. A
lightweight, lazy alternative already exists in the codebase: `GET /{session_id}/iterations`
(`session_routes.py:205-219`, uses `read_iteration_meta`, "no result/rating data") and the
per-iteration detail endpoint `GET /{session_id}/iterations/{iteration_id}`
(`session_routes.py:229-237`, returns the full node). The backend lazy endpoint is
already in place; only `get_session` must stop eager-loading and the frontend must
lazy-load detail on selection.

The iter-2 evaluator scheduled exactly this work at **full depth** because it is a
backend+frontend session-open contract change with **direct J-02 regression risk**
(`useBacktest.ts` hydration at lines ~492-570 currently consumes `data.iterationHistory`
as fully-populated `IterationNode[]` — it filters on `n.result`/`n.status === 'complete'`,
derives `latestComplete` from `n.params`, and enters the `results` phase only when a node
carries `result`). If the list goes lightweight without a lazy-detail path, J-02
("the selected run's strategy spec, metrics, and trades reload into the detail view")
regresses.

The OOS-aware sub-clause of **J-04** ("suggestions are OOS-aware when walk-forward data
exists") has **never been independently asserted in any iteration** — every prior J-04
screenshot was a byte-identical duplicate of the walk-forward (J-03) panel
(lessons.md iter-2). The capability already exists in code
(`strategy/insights_generator.py:62,227-249` factors WFE/OOS into the prompt;
`POST /api/generate-insights` accepts `request.walk_forward_result`,
`backend/api.py:703`), so J-04 here is **verification-only — no code change** — but it
must finally get its own dedicated, distinct evidence.

**Lessons applied (from `lessons.md`):**
- *iter-0 (independence of green journey vs anti-goal):* J-02 has passed every iteration
  **with the eager-load present** — a green J-02 must NEVER be read as the eager-load
  anti-goal being satisfied. The anti-goal resolution must be proven by code inspection
  + a backend test asserting the response shape, not by J-02 passing.
- *iter-2 (J-04 evidence):* browser-QA MUST capture a **distinct, dedicated** screenshot
  of the **insights pane after a walk-forward run** showing OOS/walk-forward-referencing
  suggestions. A J-04 screenshot that duplicates the walk-forward (J-03) capture is
  invalid evidence and must be rejected.

## IN SCOPE

### Backend
- [ ] `apps/backend/backend/session_routes.py` `get_session` (lines 142-171): stop calling
      `read_iteration_full` per iteration. Return a **lightweight** iteration list
      (per-iteration metadata only — e.g. via `read_iteration_meta`), carrying the fields
      the frontend history tree/list needs to render and select (at minimum: iteration
      `id`, `status`, `timestamp`, `params`, strategy name/title, parent linkage,
      selection) but **excluding** the heavy `result` / `rating` / `equity_curve` /
      `trades` / per-bar payloads. Keep `meta`, `activityLog`, `backtestParams`, and
      `selectedIterationId` behavior unchanged. Keep the 404 condition behaviorally
      equivalent.
- [ ] Heavy iteration detail continues to be served **only** by the existing
      `GET /{session_id}/iterations/{iteration_id}` endpoint
      (`session_routes.py:229-237`) — do not add a second heavy path. No new endpoint
      unless strictly required; reuse what exists.
- [ ] If a list-critical field genuinely is not present in `meta.json`, surface that in
      the dev handoff as an explicit decision rather than silently re-introducing a heavy
      read; do not eagerly read `result.json`/`rating.json` to backfill list fields.

### Frontend
- [ ] `apps/frontend/src/lib/sessionApi.ts`: add a typed fetch for a single full
      iteration node via the existing `GET /api/sessions/{id}/iterations/{iterationId}`
      (a GET sibling to the existing DELETE `deleteIterationFromStore`).
- [ ] `apps/frontend/src/hooks/useBacktest.ts` hydration (~lines 492-570) and
      selection path: restore the lightweight iteration list, then **lazy-load the full
      node on selection** (and for the initially-resolved/selected iteration so the
      detail view and the `results` phase render on session open without a full eager
      payload). Merge fetched `result`/`rating`/`insights` into the in-memory node.
      Preserve the existing save-effect guards (`savedIterationVersionRef`,
      `savedActivityCountRef`) so lazy-loaded detail is NOT re-saved back to the store.
- [ ] `apps/frontend/src/components/SessionContainer.tsx`: ensure history list/tree
      rendering and selection still work against lightweight nodes (it must not assume
      `result`/`rating` are present until a node is selected and loaded).
- [ ] Loading + error states for the lazy detail fetch (the detail pane must show a
      clear loading state while fetching and a clear error state if the per-iteration
      fetch fails — no silent blank panel).

### J-04 verification (NO code change)
- [ ] Confirm via QA that after running a walk-forward on a completed run and then
      requesting/regenerating AI insights, at least one ranked suggestion references
      out-of-sample / walk-forward / WFE / robustness behavior.

### New user-facing capability
No new feature. Behavior preservation + performance correctness: opening a session with
many runs no longer forces the backend to parse every run's full result/rating; the
detail still appears when a run is selected.

### New information displayed
A brief loading indicator in the run-detail pane while heavy detail is lazily fetched
on selection (previously detail was always pre-inlined).

### New user actions
None. Selecting a run from history is unchanged from the user's point of view.

### UI surface changes
Run-history list/tree and the run-detail pane in the session view. No layout
restructure — the run detail pane gains a loading/error state for the lazy fetch.

### Product surface delta
The session-open path scales: a session with many heavy runs opens without the backend
deserializing every run's full payload. User-perceived behavior is unchanged except a
short detail-pane loading state on selection.

## OUT OF SCOPE

- Any backend change to AI-insights / OOS logic (the capability already exists;
  `insights_generator.py` and `/api/generate-insights` must NOT be modified — J-04 is
  verification-only this iteration).
- Touching `/api/symbols` or `/api/timeframes` or `BacktestConfigBar.tsx` (J-05 is
  closed; do not regress it).
- Touching `data/loader.py`, `session_store.py` storage layout, or the Parquet/durable-
  store anti-goals (already resolved iter-1 — do not reopen).
- Mutating `shared/contracts.py` frozen dataclasses.
- Pagination / infinite-scroll of run history, prefetching, caching layers, or any
  performance work beyond removing the eager `read_iteration_full` from `get_session`.
- Adding a new backend endpoint when the existing per-iteration endpoint suffices.
- Backend restart / persistence durability re-verification (resolved iter-1; not in
  scope here).

## DEFINITION OF DONE

- [ ] `GET /api/sessions/{id}` no longer calls `read_iteration_full` and its response
      contains NO per-iteration `result` / `rating` / `equity_curve` / `trades` payloads
      (proven by reading the final `get_session` source AND by a backend test asserting
      the response shape — NOT inferred from J-02 passing).
- [ ] `GET /api/sessions/{id}/iterations/{iteration_id}` still returns the full node
      (lazy detail path intact).
- [ ] **J-02** passes via browser-qa-agent: open a prior run from history → its strategy
      spec, metrics, and trades reload into the detail view (now via lazy fetch on
      selection). Highest regression watch this iteration.
- [ ] **J-04** passes via browser-qa-agent with **dedicated, distinct** evidence: after a
      walk-forward run, requesting/regenerating insights yields ≥1 ranked suggestion that
      is OOS/walk-forward-aware; the J-04 screenshot is the **insights pane**, not a
      duplicate of the J-03 walk-forward capture.
- [ ] Required-still-passing journeys remain green: J-01, J-03, J-05, J-06 (no regression
      from the session-open contract change; J-01/J-06 also confirm run creation still
      appends to history correctly).
- [ ] No anti-goal violation introduced; the eager-load anti-goal is resolved.
- [ ] Backend unit/integration tests pass; existing pre-existing baseline failures (e.g.
      `test_directions_cache.py`, byte-identical to HEAD) are documented as out-of-scope
      pre-existing, not introduced here.
- [ ] Dev handoff written at `docs/handoffs/goal-money-billions-iter-3-dev.md`.

## TESTING REQUIREMENTS

- **Browser (browser-qa-agent), required journeys to verify by ID:**
  - **J-02** — complete ≥1 backtest, open a *distinct prior* run from the history list;
    assert its strategy spec, metrics, and trades reload into the detail view. This is
    the primary regression target — exercise selecting more than one run and re-selecting.
  - **J-04** — on a completed run, run walk-forward, then request/regenerate insights;
    capture a **dedicated screenshot of the insights pane** showing ≥1 suggestion that
    references OOS / out-of-sample / walk-forward / WFE / robustness. **The J-04
    screenshot MUST be a distinct image of the insights pane — a capture that duplicates
    the J-03 walk-forward panel is invalid and fails J-04.**
  - **J-01, J-03, J-05, J-06** — no-regression smoke: J-01 run-from-NL still appends a
    new `run_id` to history; J-03 walk-forward still renders WFE badge + per-window table
    + combined OOS curve; J-05 symbol/timeframe controls still populate from endpoints;
    J-06 warm-cache re-run still deterministic and appears in history.
- **Unit/integration (backend):**
  - A test that calls `get_session` (or `GET /api/sessions/{id}`) for a session with ≥1
    completed iteration and asserts the returned iteration list entries contain NO
    `result`, `rating`, `equity_curve`, or `trades` keys (assert exact absence, not
    "something returned").
  - A test that `GET /{session_id}/iterations/{iteration_id}` still returns the full
    node *with* `result`/`rating` for the same iteration (lazy path intact).
  - A test that `get_session` still returns correct `meta`/`activityLog`/
    `backtestParams`/`selectedIterationId` and the lightweight iteration list preserves
    ordering and the fields the frontend tree/selection needs.
  - 404 behavior for a non-existent session remains equivalent.
- **Frontend:** the lazy-load-on-selection path must be exercised by the browser J-02
  test (open a run → detail populates). If a unit/component test harness exists for
  `useBacktest`/`sessionApi`, add a test that selection triggers the per-iteration fetch
  and merges detail; otherwise the browser J-02 flow is the binding evidence and the
  handoff must say so explicitly.
- **Error cases:**
  - Per-iteration lazy fetch failure → detail pane shows an explicit error state (not a
    silent blank); session list still renders.
  - Selecting an iteration that has no `result` yet (e.g. error/in-progress) does not
    crash the detail view.

## NOTES

- **Independence rule (lessons.md iter-0, applied):** J-02 passing does NOT prove the
  anti-goal resolved — J-02 has passed every prior iteration *with* the eager-load
  present. The evaluator should treat the anti-goal as resolved ONLY on (a) the final
  `get_session` source no longer calling `read_iteration_full` and (b) the backend
  response-shape test asserting absence of heavy payloads. Cross-layer corroboration
  (browser network inspection of the `GET /api/sessions/{id}` payload size/shape) is a
  welcome additional signal but not a substitute for the code+test proof.
- **J-04 evidence rule (lessons.md iter-2, applied):** the upcoming browser-QA MUST save
  a distinct insights-pane screenshot after a walk-forward run; a J-04 capture that is a
  byte-identical / visual duplicate of the J-03 walk-forward panel is invalid and the
  evaluator must reject it. This is the iteration that finally closes the long-open J-04
  OOS-aware soft gap.
- Frontend contract risk: `useBacktest.ts` hydration filters/derives state from
  `n.result`/`n.status`/`n.params` and seeds `savedIterationVersionRef` from
  `n.insights?.suggestions?.length`. The lightweight list must still carry enough for the
  history tree + selection; lazy-merged detail must NOT trip the save effects into
  re-persisting already-stored iterations (regression + write-amplification risk).
- GOAL_ACHIEVED becomes reachable after this iteration only if BOTH the eager-load
  anti-goal is code-proven resolved AND J-04 OOS-awareness has dedicated evidence AND no
  journey (esp. J-02) regresses. This is the last planned blocker.
- Reference: iter-2 `eval.md` Next-Step Recommendation; journey-history.json
  `anti_goal_violations[2]` (`resolved: false`).
