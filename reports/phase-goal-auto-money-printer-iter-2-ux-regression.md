# Phase goal-auto-money-printer-iter-2 — UX Regression Review

**Date:** 2026-05-19

**Verdict:** UX-REGRESSION-WARN

Frontend Present: yes. Functionally complete and non-regressing (all named +
required-still-passing journeys pass browser-QA). One **non-blocking
discoverability/label mismatch** is flagged: the in-app activity message
instructs the operator to look for an "Auto: …" session in the list, but that
name is transient (~12–15 s) before the backend overwrites it with the
strategy name. The running session stays reachable within 2 clicks via the
pulsing amber dot + "running" badge (browser-QA verified), so it is **not**
hidden/inaccessible — hence WARN, not FAIL.

---

## New Capability Discoverability

This iteration is a **rewire of existing affordances**, not a new surface — no
new pages, no new buttons, no navigation change (verified in the diff: only
`SessionContainer.tsx` +18 / `useBacktest.ts` ±550 / `sessionApi.ts` +45 on
the frontend). Every new capability rides a control that already existed.

| New capability | Navigation path | Clicks from home | Label clarity | Visual feedback |
|---|---|---|---|---|
| Launch a server-driven auto-session | Same config-bar **"Auto Run (N)"** button (or per-card zap action) — appears when a completed iteration has suggestions | 0 new nav (button already on the main session view) | Clear; gating unchanged from iter-1 (UT-02) | Verbatim activity-log info entry (UT-03/UT-08) + new running session in dropdown |
| Run survives tab close/reload | New **"Auto: …"** session in the `SessionPicker` dropdown | 2 (open Sessions dropdown → select the running session) | See WARN below — message says look for "Auto: …" | Pulsing amber dot + "running" badge; `AutoRunBar` "iteration X/N" (UT-04/UT-12) |
| Stop a running auto-session | Same config-bar **"Stop (x/N)"** button, now backend-wired | 0–1 | Clear (UT-05) | `AutoRunBar` flips to red `StopCircle` "Automated run stopped" (UT-05/UT-06) |
| Non-stale per-session status | Existing `AutoRunBar` strip + `SessionPicker` dot, re-derived authoritatively on mount/switch | 0 | Clear | Spinner/badge agree with bar (UT-13) |

Confirmed in source: the ownership-hardening effect re-derives this session's
durable `autoRun` from the backend on mount and on `isActive`/`sessionId`
change (`useBacktest.ts:823-835`), and the session-list spinner and
`AutoRunBar` derive from the **same** `autoRun.status` (`useBacktest.ts:872-886`)
— the iter-1 stale-terminal lesson is structurally addressed, not just
asserted. Discoverability is otherwise strong precisely because nothing moved.

---

## Regression Risk

| Shared component | Prior feature it served | Change this phase | Risk | Verified |
|---|---|---|---|---|
| `useBacktest.ts` | iter-1 live poll (J-08), iter-1 J-02 lazy-detail guard (`loadingDetailIdRef`), hydration, backend-owned save suppression | 550 lines changed (in-browser loop deleted; `startAutoSession`/`stopAutoSession` + ownership re-derive added) | **High exposure** | J-02 **UT-14 PASS** (bidirectional right-panel re-bind), J-08 **UT-13 PASS** (41 mounted containers, rapid switch, no stale terminal), J-01 **UT-15 PASS** | 
| `SessionContainer.tsx` | iter-1 `AutoRunBar`; host of all session journeys | hook signature → `useBacktest(sessionId, isActive)`; start/stop re-wired | Medium | UT-13/UT-14/UT-15 PASS; no manual-flow regression |
| `IterationCard`/`DetailView`/`IterationPanel` "★ Best" pill | iter-1 J-09 best marker | **Not modified** (not in diff); best-on-stop preserved backend-side | Low | UT-05/UT-16 PASS — exactly 1 Best pill preserved on stop, robust-objective not raw return |
| `App.tsx` discovery poll | iter-1 B2 fix (headless session appears ≤5 s) | **Not modified** (confirmed: not in diff) | Low | UT-12 PASS |
| `SessionPicker`/`SessionDot` | iter-1 running dot | Not directly modified; sources from backend `autoRun.status` | Low | UT-13 PASS — dot and bar agree |

**Navigation integrity:** no router / `App.tsx` / `Sidebar` / nav changes;
single-page app, no route change. All prior journeys reachable.

**Anti-goal "no second in-browser iterate loop":** verified at source-diff
level (per the spec's skeptical-evaluation requirement, not the report
headline): the legacy `startAutoRun` `while (attempt < maxAttempts &&
!autoRunStopRef.current)` iterate loop and its solely-owned state/refs
(`autoRunStopRef`, `autoRunIterationIdsRef`, `createSemaphore`,
`markSuggestionDisabled`) are gone. The only remaining `while` loops
(`useBacktest.ts:1208`, `:1996`) are pre-existing single-backtest exec /
walk-forward **retry** loops, not a generate→backtest→insights iterate loop.

Net: medium regression *exposure* on `useBacktest.ts`, but the two
lesson-protected journeys (J-02 iter-0 lesson, J-08 iter-1 lesson) and J-01
were re-verified PASS under realistic conditions. **No regression flag.**

---

## UI vs Backend Parity

| Backend capability (this phase) | UI exposure | Parity |
|---|---|---|
| `POST /api/auto-sessions/{id}/stop` | Config-bar Stop button (UT-05) + converges live on API-issued stop (UT-06) | ✅ Surfaced |
| In-process `_CANCEL_REGISTRY` (cancellation plumbing) | Internal; effect surfaces as `stopped` status | ✅ Effect visible (intentionally internal) |
| Durable worker-safe `stopRequested` signal | Internal durability; surfaces as eventual `stopped` status | ✅ Effect visible (intentionally internal) |

`user-visible-changes.md` "Not Visible Yet" = **None**, and that is accurate:
every user-facing backend capability is reachable via the existing Stop
control. Out-of-scope items (open-universe, hard cost tracker) are correctly
absent from the UI and still 4xx-rejected (UT-10: open-universe → 422). **No
UI/backend parity gap.**

---

## Flags

### Hidden Capabilities
- None. All new capabilities are surfaced through existing controls.

### Undiscoverable Capabilities
- None at the >2-click level. The running server session is reachable in 2
  clicks (open Sessions dropdown → select it) via the pulsing amber dot +
  "running" badge — browser-QA confirmed it appears without a manual reload
  (UT-12) and the indicator agrees with the in-session bar (UT-13).

### Label Confusion (WARN — non-blocking)
- **Transient `Auto:` session name vs the activity-log instruction.** The
  rewired Auto Run logs (verbatim, `useBacktest.ts:2255`): *"…a new 'Auto: …'
  session appears in the session list shortly."* Backend source sets
  `name = f"Auto: {nl[:40]}…"` at creation, but browser-QA's timed
  cross-check (skeptical evaluation per spec) found the `Auto:` prefix
  persists only ~12–15 s before the first iteration's generated strategy name
  overwrites it (e.g. "BTC 1h RSI Reversion") — every observed *terminal*
  auto-session is strategy-named with no `Auto:` prefix. An operator who opens
  the dropdown >15 s after clicking (common) will see **no** `Auto:`-prefixed
  row even though the in-app text told them to look for one; they must instead
  rely on the running dot/badge. The capability is **not** lost (the session
  is still discoverable by the running indicator, J-08 guarantee), so this is
  WARN, not FAIL — but the guidance text is misleading.

### Potential Regressions
- None confirmed. `useBacktest.ts` is the high-exposure shared file, but the
  J-02 right-panel re-bind (iter-0 lesson) and the J-08 no-stale-terminal
  ownership path (iter-1 lesson) were re-verified PASS by browser-QA
  (UT-14 bidirectional; UT-13 under 41 mounted containers with rapid
  switching), and the retry Fix Notes specifically hardened the J-08 live-poll
  convergence (Blocker #2 — poll now self-heals via `finally` re-arm) and
  confirmed the J-02 path is untouched (Blocker #5).

### Visual Consistency
- Consistent with prior phases. No new components, no new effects, no new
  pages — the iteration reuses the existing `AutoRunBar` strip,
  `BacktestConfigBar` Auto Run/Stop controls, `Loader2` spinner, red
  `StopCircle` terminal treatment, and the "★ Best" pill, on the unchanged
  two-panel analytical-workstation layout. UT-16 confirms the emerald/check
  "complete" treatment and `role="status"`; UT-05 confirms the red stopped
  treatment. No arbitrary values introduced; DESIGN-SYSTEM tokens
  (slate/primary/emerald/amber) preserved. No visual-inconsistency flag.

---

## Recommendation

The phase is functionally complete, non-regressing, and visually consistent —
J-10/J-11 pass and all required-still-passing journeys (J-01/J-02/J-08
explicitly re-verified) hold. Verdict is **WARN**, not PASS, solely for the
one label-confusion issue:

1. **(WARN — should fix, non-blocking) Resolve the transient `Auto:` name vs
   the activity-message mismatch.** Pick one: (a) preserve the `Auto:` prefix
   for the run's lifetime (do not let the first iteration's strategy name
   overwrite the session name while `autoRun` is non-terminal), or (b) reword
   the activity-log entry to point the operator at the **pulsing amber
   "running" indicator** in the Sessions dropdown rather than at an "Auto: …"
   name that disappears within ~15 s. Option (a) better matches the spec's
   "New information displayed" expectation. This does **not** block this
   iteration's named journeys and is appropriately deferred to the
   auditor/next iteration — it is a guidance-accuracy fix, not an
   accessibility defect.

2. **(No action — informational)** No regression remediation required; the
   high-exposure `useBacktest.ts` edit was verified clean against the two
   lesson-protected journeys. Keep J-02/J-08 in the required-still-passing
   set for any future edit to this file.
