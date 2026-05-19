# goal-auto-money-printer-iter-2 Frontend Handoff

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built (UI)

All changes ride the existing two-panel analytical-workstation layout — no
new page, no navigation change, no new components.

- **"Auto Run" is now server-driven (J-10).** Both entrypoints — the
  `BacktestConfigBar` "Auto Run" button and the per-iteration-card auto-run
  action (`handleStartAutoRunFromCard`) — call `POST /api/auto-sessions`,
  pinning the config from the chosen completed iteration (its
  natural-language strategy, `symbol`/`timeframe`/`start_date`/`end_date`/
  `initial_capital`, the selected model, and `budget.max_iterations` from the
  existing Auto Run count control). The run executes entirely on the backend
  and **survives closing/reloading the tab**. The new "Auto: …" session
  surfaces in the Sessions dropdown via App.tsx's existing discovery poll
  (~5 s); an activity entry in the originating session tells the operator a
  new session is coming.
- **Stop control wired to the backend (J-11).** The existing config-bar Stop
  button now calls `POST /api/auto-sessions/{id}/stop` for the open
  server-driven session. The durable status flips to `stopped` and the
  `AutoRunBar` shows the red `StopCircle` + "Automated run stopped"; the
  best-so-far iteration keeps its "★ Best" pill; no iterations appear after
  the stop. An immediate authoritative refresh is nudged so the bar reacts
  without waiting for the next 2.5 s poll tick.
- **Legacy in-browser Auto Run loop deleted.** The old `startAutoRun`
  while-loop and `stopAutoRun` (and the UI state they owned —
  `isAutoRunning`, `autoRunProgress`, plus internal refs) are gone. There is
  no second iterate loop in the browser; the browser is a viewer/controller.
- **AutoRunBar / SessionContainer ownership hardened (mandatory iter-1
  lesson).** Each session's `autoRun` status is authoritatively re-derived
  from the backend **on mount and every time the session becomes active**
  (`isActive` is now passed into `useBacktest`). With every `SessionContainer`
  mounted and rapid session switching, a freshly-opened *still-running*
  session can no longer show a stale terminal status. The session-list
  spinner (`SessionPicker`) and the in-session `AutoRunBar` now derive from
  the **same** durable `autoRun.status`, so they cannot disagree.

## Changed Behavior

- **"Auto Run" button** — Previously ran an in-browser generate→backtest→
  insights loop that died if the tab closed. Now starts a backend
  auto-session that keeps running independently; the originating session
  logs an info entry and the new "Auto: …" session appears in the list.
- **Stop button** — Previously aborted the in-browser loop and deleted its
  partial iterations. Now cooperatively stops the *server* run; the backend
  preserves completed iterations and the robust "★ Best" marker.
- **Per-session running/terminal status** — Now always reflects backend
  truth on switch (no stale terminal under rapid multi-session switching).
- **Manual run, history browsing, the J-02 right-panel re-bind, `runAll`,
  and the live poll are unchanged** — those code paths were not modified.

## Files Changed

- `apps/frontend/src/lib/sessionApi.ts` — `startAutoSession` /
  `stopAutoSession` clients + `AutoSessionStartConfig`.
- `apps/frontend/src/hooks/useBacktest.ts` — delete in-browser loop + its
  solely-owned state/refs/helpers (`createSemaphore`, `workerCountRef`,
  `markSuggestionDisabled`); add `startAutoSession`/`stopAutoSession`;
  authoritative `autoRun` re-derive on mount/switch; derived
  `headlessRunning`/`autoRunProgress`; signature `useBacktest(sessionId,
  isActive)`.
- `apps/frontend/src/components/SessionContainer.tsx` — pass `isActive` to
  the hook; route both start paths and the Stop control to the backend.

## Tests Run

`cd apps/frontend && npm run build` (tsc + vite) → **EXIT 0, clean** (the
pre-existing >500 kB chunk warning is unrelated). `npx tsc --noEmit` is part
of `npm run build` and passed (`noUnusedLocals`/`noUnusedParameters` are on,
so all loop-orphaned symbols were removed). `npm run lint` remains
non-functional repo-wide (no ESLint config — pre-existing, unrelated).

## Known Issues

- In-browser J-10/J-11/J-02/J-08 user-flow verification is delegated to
  browser-qa (tiny budgets) per the spec. The status block consumed by the
  UI (`autoRun` durable, lightweight list path, `stopped` + reason) is
  validated by the backend `test_auto_session` suite (26 passing).
- Visual styling reuses existing slate/primary/emerald/amber tokens, the
  `Loader2` spinner and the red `StopCircle` terminal treatment, and the
  `IterationCard`/`IterationDetailView` "★ Best" pill — no new effects, no
  `AutoRunBar` redesign (cosmetic redesign was out of scope).
- The new auto-session appears via App.tsx's existing 5 s discovery poll
  (App.tsx intentionally not modified — spec confines changes to
  `SessionContainer.tsx`/`useBacktest.ts`). Browser-QA must wait for and
  select the new "Auto: …" tab when verifying J-10.

---

# Fix Notes — QA FAIL retry (2026-05-19)

Frontend changes are confined to `apps/frontend/src/hooks/useBacktest.ts`
(no SessionContainer/App changes this retry). Full reasoning in the dev
handoff's Fix Notes; UI-relevant summary:

- **Live AutoRunBar now converges without a manual reload (QA Blocker #2 /
  J-08 / iter-1 lesson).** The live poll's `tick` re-armed its next run only
  on the fully-successful path; a single failed/slow `apiLoadSession` (which
  returns `null` on any network error — exactly what the backend GIL stall
  caused) silently killed the poll forever, freezing the bar at "running
  5/8" until a hard reload. `tick` now re-arms in a `finally`, so the poll
  self-heals and the bar reliably advances running → terminal (`complete` /
  `stopped` + reason) on its own. `role="status" aria-live="polite"` and the
  heavy-detail-preserving merge are unchanged (J-02 not regressed).
- **Stop button is steadier (QA Blocker #4).** `autoRunProgress` is now a
  `useMemo`-stable object (was rebuilt every 2.5 s poll tick, recreating the
  Stop button subtree each tick); combined with the no-flicker poll fix the
  Stop/Auto-Run button identity stays stable so the first click fires
  reliably. Exact MCP click-timing to be re-verified by browser-qa (TC-17).
- No new components, no new effects, no layout/token changes — the
  AutoRunBar/BacktestConfigBar visual treatment is untouched (cosmetic
  redesign remains out of scope).
