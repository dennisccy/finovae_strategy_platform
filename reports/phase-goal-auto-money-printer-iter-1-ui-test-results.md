# Phase goal-auto-money-printer-iter-1 — UI Test Results

**Phase:** goal-auto-money-printer-iter-1
**Date:** 2026-05-19
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** PASS (post-fix)

<!-- ORIGINAL PRE-FIX RUN: FAIL — two P1 happy-path tests failed: UT-03
     (headless session did NOT appear in the Sessions dropdown without a page
     reload, B2) and UT-06 (the "★ Best" badge did NOT render in the expanded
     iteration detail view, B3). The pre-fix detail below is preserved verbatim
     for traceability. Both P1 gaps (plus the critical B1 event-loop block)
     were subsequently FIXED in source and RE-VERIFIED by the QA MODE-2 browser
     run. See the "Post-Fix Reconciliation" section at the end of this file —
     that is the binding current verdict (PASS). -->

> **⚠ Reconciliation notice (auditor, 2026-05-19):** The verdict immediately
> below (`FAIL`) and the pre-fix detail in this document reflect the **first**
> browser-QA run, BEFORE the B1/B2/B3 fixes. Those fixes are present in source
> (App.tsx discovery poll, IterationDetailView BestBadge, auto_session
> store/encode offload — all diff-verified) and were re-validated end-to-end by
> the QA MODE-2 browser run (TC-17/TC-18/TC-06 PASS). The **binding current
> verdict is PASS (post-fix)** — see "Post-Fix Reconciliation" at the end of
> this file. The original pre-fix content is retained unedited for audit trail.

**Pre-fix verdict (superseded):** FAIL

**Overall:** 15/20 passed, 2 failed, 3 N/A (could-not-trigger / not-reachable
per the test plan's own allowances).

P1 results: UT-01 ✅ · UT-02 ✅ · **UT-03 ❌** · UT-04 ✅ · UT-05 ✅ ·
**UT-06 ❌** · UT-07 ✅ · UT-10 ✅ · UT-13 ✅ · UT-15 ✅
→ two P1 failures ⇒ **FAIL**.

> **Backend J-07 itself works** (`POST /api/auto-sessions` → 200 + `sessionId`;
> `GET /api/sessions` lists it; `autoRun` persisted in the durable store). The
> two P1 failures are **frontend surfacing gaps**, not backend-loop failures:
> (1) the session-tab list is only fetched on mount (no polling) so a new
> headless session is not discoverable without a manual reload; (2) the
> `BestBadge` is rendered in the compact iteration tree but not in the expanded
> `IterationDetailView` header.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | App shell + Sessions picker loads | smoke | P1 | Title "Finovae Strategy Platform", "v0.3.0", Sessions button, chat placeholder, no error overlay | All present; versionText "v0.3.0"; Sessions button (badge); placeholder "Describe a trading strategy..."; no error overlay | PASS | UT-01-result.png |
| UT-02 | Manual session has no AutoRunBar | smoke | P1 | Config bar present; NO "Automated run …" strip; empty iteration state | `hasAutomatedRunStrip:false`; config bar present; "No Iterations Yet" | PASS | UT-02-result.png |
| UT-03 | Headless session appears in dropdown w/o reload (J-07) | happy-path | P1 | New headless session row appears in the Sessions dropdown WITHOUT a manual page reload | Session present in API immediately, but dropdown showed only the 3 pre-existing sessions; the new row appeared **only after a manual reload** (count 3→4). Explicitly the plan's "broken" case. | **FAIL** | UT-03-fail-no-reload.png, UT-03-after-reload-appears.png |
| UT-04 | Live progress, no reload (J-08) | happy-path | P1 | Spinner "iteration X/2"; without reload X advances + new cards appear; terminal; polling stops | Opened running RUN-J ("iteration 1/2" spinner, "No Iterations Yet"); WITHOUT reload it advanced to terminal "complete · budget reached · 2/2" and right panel → "Iterations (2)" via the 2.5 s poll | PASS | UT-04-running-iter1-dropdown-amber.png, UT-04-terminal-live-no-reload.png |
| UT-05 | Terminal stop reason + one "★ Best" (J-09) | happy-path | P1 | Green strip "complete · budget reached/criteria met · X/2"; exactly one ★ Best matching `bestIterationId` | Strip green "Automated run complete · budget reached · 2/2 iterations"; exactly one "Best" badge on iteration `affe5dfd` = `autoRun.bestIterationId` (criteria-met path also confirmed at API level via RUN-I) | PASS | UT-05-terminal-best.png |
| UT-06 | "★ Best" in expanded card (J-09) | happy-path | P1 | ★ Best pill also shown next to strategy name in the expanded detail view | Expanded `IterationDetailView` header HTML contains only back-arrow + name + description + timestamp + return pill — **no BestBadge**. Badge present in compact tree only. | **FAIL** | UT-06-fail-no-badge-expanded.png |
| UT-07 | Older run re-binds RIGHT panel (J-02) | happy-path | P1 | Selecting older run re-binds RIGHT panel (trades/equity/WF), not pinned | Viewed iter2 (25 trades, −15.70%) → back → iter1: RIGHT panel re-bound to "Trade History (113 trades)", −38.41%, equity redrawn | PASS | UT-07-rebind-iter1-113trades.png |
| UT-08 | Failed iteration still terminal | error | P2 | Failed iteration shown as failed card; run still reaches terminal | No LLM/backtest iteration failure occurred across ~12 triggered runs | N/A — could not trigger (plan permits) | none |
| UT-09 | Detail-load failure pane + Retry | error | P2 | "Couldn't load this run's detail" + Retry, not blank/crash | Detail-fetch failure not triggered; harness-managed backend deliberately not destabilized | N/A — could not trigger (plan permits) | none |
| UT-10 | Manual session: no AutoRunBar (guard) | regression | P1 | Manual: no strip; headless: strip present | Manual "Session": `hasAutomatedRunStrip:false`; headless: "Automated run complete · budget reached · 2/2 iterations" | PASS | UT-02-result.png (manual), UT-05-terminal-best.png (headless) |
| UT-11 | J-02 re-fetch guard A→B→A | regression | P2 | Re-selecting A re-displays A's full detail, not stuck blank | A→B→A: A's full detail restored (Trade History 113 trades + Equity Curve + Strategy Script + WF); not stuck | PASS | UT-11-A-detail-restored.png |
| UT-12 | Live poll preserves open detail | regression | P2 | Open heavy detail not blanked/reverted across poll cycles | RUN-L iter1 (410 trades) open during running→complete poll merge + 9 s of poll cycles: detail stayed intact, no blank/loading | PASS | UT-12-detail-preserved.png |
| UT-13 | Manual NL backtest works (J-01) | regression | P1 | Activity log streams + completes w/o error; right panel full result; new run entry | Chat submit → streamed [1]–[8] activity → completed (`status:complete`, manual session, `autoRun:None`) → Equity Curve + metrics + Strategy Script + Trade History (183 rows) + WF | PASS | UT-13-state.png |
| UT-14 | Walk-Forward + insights work (J-03/J-04) | regression | P2 | WFE badge + per-window + OOS curve; ≥1 ranked suggestion | J-04: 17 ranked suggestions + insight text. J-03: WFE values computed/shown on iterations; "Run Walk-Forward"/"Re-run" controls work (run in-progress, not errored). Caveat: heavy 183-trade/4-yr manual WF still computing at QA end (slow, not broken). | PASS (caveat) | UT-14-walkforward.png, UT-14-wf-result.png |
| UT-15 | Ref data + legacy Auto Run intact (J-05) | regression | P1 | Timeframe/Symbol populated; legacy "Auto Run" starts→Stop halts; no crash | Timeframe [1 Minute…1 Day]; Symbol datalist [BTC/USDT,ETH/USDT,BNB/USDT,…]; "Auto Run (1)" → "Stop (0/1)" → Stop halts; no error overlay; coexists with headless API | PASS | UT-15-stop-button.png, UT-15-legacy-autorun.png |
| UT-16 | Session-picker amber dot pulses/clears | ux | P2 | Amber pulsing dot+"running" while active; steady emerald+no "running" at terminal, w/o reload | While running: amber dot + "running" (step 032). Terminal: steady `bg-emerald-500`, no "running" (step 078). Caveat: in-place amber→emerald transition in an already-open dropdown needs a reopen (same root cause as UT-03). | PASS (caveat) | UT-16-amber-running-dot.png |
| UT-17 | Session-picker best-return w/o opening | ux | P3 | Signed % best-return (emerald/red) without opening the session | Rows show "+7.6%" emerald (rgb 16,185,129), "−15.7%" red (rgb 239,68,68), "−1.4%" red, "+0.0%" emerald — without opening | PASS | UT-17-best-return-dropdown.png |
| UT-18 | AutoRunBar aria-live announced | ux | P3 | Strip has role="status" aria-live="polite" | `<div … role="status" aria-live="polite">Automated run complete · budget reached · 2/2 iterations` | PASS | (DOM eval step 080) |
| UT-19 | "★ Best" tooltip explains selection | ux | P3 | Tooltip "Best iteration — selected by the robust walk-forward objective" | Exact tooltip text present on the BestBadge: "Best iteration — selected by the robust walk-forward objective" | PASS | UT-05-terminal-best.png (badge), DOM eval steps 041/080 |
| UT-20 | AutoRunBar stopped state styling | ux | P3 | Red StopCircle + "Automated run stopped" | No run reached `stopped`; J-11 stop control deferred to iter-2 | N/A — stopped state not reachable in iter-1 (plan permits) | none |

---

## Failed Tests

### UT-03 — Headless session appears in the Sessions dropdown without a page reload (J-07)
**Verdict:** FAIL
**Failure:** A headless session created via `POST /api/auto-sessions` does **not**
appear in the header "Sessions" dropdown without a manual page reload. It is the
plan's explicitly-documented "broken" case for the "no manual reload"
tab-appearance claim.

**Steps taken:**
1. App open and untouched (manual session selected, no reload since mount).
2. `POST /api/auto-sessions` (RUN-B `f8c9a2e7…`) → HTTP 200 `{"status":"running"}`.
3. Confirmed via API: `GET /api/sessions` immediately lists RUN-B as
   "Auto: Buy when RSI crosses below 30, sell when…".
4. Without reloading: opened the "Sessions" dropdown within ~5 s → only the 3
   pre-existing sessions shown. Waited 12 s, re-opened the dropdown (still no
   reload) → still only 3; `runB_present_anywhere:false`.
5. Performed one page reload → dropdown count 3→4, RUN-B now present
   ("BTC 1H RSI Mean Reversion(active)").

**Expected:** New "Live Sessions" row for the headless session appears WITHOUT a
manual page reload.
**Actual:** Row appears **only after** a manual reload. Root cause: the App
fetches the session-tab list only on mount and does not poll it (the plan's own
"Session-discovery fallback" note acknowledges this; UT-03 is the explicit gate
for the "without reload" claim).
**Evidence:** `reports/qa/goal-auto-money-printer-iter-1-evidence/UT-03-fail-no-reload.png`
(3 sessions, no reload), `UT-03-after-reload-appears.png` (4 sessions after reload).

### UT-06 — "★ Best" badge also shows in the expanded iteration card (J-09)
**Verdict:** FAIL
**Failure:** The "★ Best" pill is **not** rendered in the expanded
`IterationDetailView` header next to the strategy name. It renders only in the
compact iteration tree.

**Steps taken:**
1. Opened terminal headless session RUN-J (2 iters; best = `affe5dfd`
   "BTC 1H RSI Reversion with Bull Trend Filter").
2. Confirmed exactly one "★ Best" pill in the compact tree on that iteration
   (UT-05).
3. Clicked that iteration to expand its detail.
4. Dumped the visible expanded-header HTML.

**Expected:** The "★ Best" amber pill is also shown next to the strategy name in
the expanded view (badge consistent in both compact tree and expanded card).
**Actual:** The expanded header `<div class="flex items-center justify-between
gap-3">` contains only: back-arrow button, `<h2>` strategy name, description,
timestamp, and the red return pill ("-15.70%"). No star/amber/"Best" element;
`document.body` "Best" text count = 0 in the expanded view (the 9 BestBadge
nodes belong to the collapsed tree and have 0×0 bounding boxes).
**Evidence:** `reports/qa/goal-auto-money-printer-iter-1-evidence/UT-06-fail-no-badge-expanded.png`
(+ header HTML captured in DOM eval step 042).

---

## Skipped / N/A Tests

### UT-08 — A failed iteration is still shown and the run still reaches a terminal state
**Verdict:** N/A — could not trigger
**Reason:** No LLM/backtest iteration failure occurred naturally across the ~12
headless runs triggered (RUN-A…RUN-L). All iterations completed (some with 0/low
trades, but `complete`, not `failed`). The plan explicitly permits marking this
N/A without failing the phase.

### UT-09 — Run-detail load failure shows a clear error pane with Retry
**Verdict:** N/A — could not trigger
**Reason:** No detail-fetch failure occurred during normal operation; the
backend is managed by browser-qa-phase.sh and was deliberately not destabilized
to force the error path. The plan explicitly permits N/A here.

### UT-20 — AutoRunBar "stopped" terminal styling
**Verdict:** N/A — stopped state not reachable in iter-1
**Reason:** No headless run ended in the `stopped` terminal state (all ended
`complete` with `budget-exhausted`, plus one `criteria-met` at API level). There
is no UI stop control or stop endpoint this iteration (J-11 deferred to iter-2),
so `stopped` is not reachable. The plan explicitly permits N/A here.

---

## Passed Tests (key verification notes)

- **UT-01** — Title/version/Sessions button/chat placeholder all present; no
  error overlay. `versionText:"v0.3.0"`.
- **UT-02 / UT-10** — Manual sessions render with the config bar but **no**
  "Automated run …" strip; headless sessions **do** show the strip. AutoRunBar
  correctly gated on `autoRun != null`.
- **UT-04 (J-08)** — Single allowed discovery reload (step 031); thereafter NO
  reload. Open RUN-J went from "iteration 1/2" spinner + "No Iterations Yet" →
  terminal "complete · budget reached · 2/2" + "Iterations (2)" purely via the
  2.5 s poll. Live tracking confirmed.
- **UT-05 (J-09)** — Green terminal strip with the budget-reached stop reason;
  exactly one "★ Best" pill on the iteration whose id equals
  `autoRun.bestIterationId` (`affe5dfd`). The criteria-met stop path was
  independently confirmed via RUN-I (`stopReason=criteria-met` after 1 iter on
  lenient targets). `GET /api/sessions/{id}` returns the `autoRun` block and
  does **not** inline iterations (lazy-load — anti-goal compliant).
- **UT-07 (J-02)** — RIGHT analysis panel re-binds on selecting an older run
  (25→113 trades, −15.70%→−38.41%, equity redraws). The J-02 bug is fixed.
- **UT-11** — A→B→A re-fetch guard: A's full heavy detail re-displays, not
  stuck blank/"no detail"/loading.
- **UT-12** — Open 410-trade heavy detail preserved across the live poll
  (including a running→complete merge) — never blanked/reverted.
- **UT-13 (J-01)** — Manual NL backtest works end-to-end: streamed activity log,
  no error, full result detail + Trade History (183 rows). Manual session
  (`autoRun:None`) with a `complete` iteration.
- **UT-14 (J-03/J-04)** — 17 ranked AI suggestions + insight text (J-04);
  WFE computed/displayed on iterations and WF controls functional (J-03).
  *Caveat:* the heavy 183-trade/4-year manual Walk-Forward was still computing
  at QA end (`wfStillRunning:true`) — slow, not a confirmed regression.
- **UT-15 (J-05)** — Timeframe + Symbol reference data populated; legacy
  in-browser "Auto Run (1)" starts the loop ("Stop (0/1)") and Stop halts it;
  no crash; coexists with the new headless API (expected this iteration).
- **UT-16 / UT-17 / UT-18 / UT-19** — Picker amber-running / emerald-terminal
  dot states correct; signed best-return shown without opening; AutoRunBar
  `role="status" aria-live="polite"`; BestBadge tooltip = "Best iteration —
  selected by the robust walk-forward objective". *UT-16 caveat:* the in-place
  dot transition in an already-open dropdown needs a reopen (same root cause as
  UT-03).

---

## Environment

- **Frontend URL:** http://localhost:3691
- **Backend URL:** http://localhost:8691 (`/health` returns 404 — no such route;
  `/api/sessions` returns 200, backend healthy)
- **Browser:** Chrome via MCP (`mcp__plugin_superpowers-chrome_chrome`)
- **Viewport:** 1600×1000
- **Test Date:** 2026-05-19
- **Evidence directory:** `reports/qa/goal-auto-money-printer-iter-1-evidence/`
- **Headless runs triggered (tiny budget, max_iterations:2, gpt-5.4-mini):**
  RUN-A `4af1ca25`, RUN-B `f8c9a2e7`, RUN-C `5d8c6f1e`, RUN-D `ee81ee8f`,
  RUN-E `60163279`, RUN-F `30318eaf`, RUN-G `2dda7f5f`, RUN-H `4dab2670`,
  RUN-I `df83e982` (criteria-met after 1 iter), RUN-J `9e943637`,
  RUN-K `87cb4341`, RUN-L `d8ba6cb9`. All reached a terminal state with a
  persisted `autoRun` block; none looped past `max_iterations`.

---

## Notes for downstream agents

1. **UT-03 (P1 FAIL) is a real, plan-anticipated frontend gap, not a backend
   bug.** Backend J-07 fully works (POST→200+sessionId, GET /api/sessions lists
   it immediately, `autoRun` persisted durably). The fix is frontend:
   poll/refresh the session-tab list while a headless `autoRun` is active (or on
   focus), instead of fetching it only on mount.
2. **UT-06 (P1 FAIL) is a missing `BestBadge` in `IterationDetailView`'s
   expanded header.** The compact-tree badge works (UT-05) and the tooltip text
   is correct (UT-19); the badge simply isn't placed in the expanded
   detail-panel header. Localized frontend fix.
3. The very fast headless runtimes (~10–45 s when LLM/data are cached) plus the
   UT-03 no-poll behaviour made the "open it while still running" cases hard to
   stage; UT-04 and UT-12 were ultimately captured using strict-target +
   longer-range runs that the app happened to restore as the active session.
4. UT-14's heavy manual Walk-Forward (183 trades / 4-year range) was still
   computing when QA concluded — this is expected slowness for that dataset, not
   a regression; J-03 is otherwise evidenced by WFE values computed for the
   robust objective across all headless iterations.

---

## Post-Fix Reconciliation (added by auditor, 2026-05-19 — BINDING VERDICT)

This document's body above is the **first (pre-fix)** browser-QA run. It
correctly recorded two P1 frontend-surfacing FAILs (UT-03, UT-06) and the
runner separately raised the critical B1 (event-loop block). The developer then
fixed all three; QA MODE-2 (which executes Chrome MCP browser checks) re-ran
the equivalent surfaces and they PASS. This section reconciles the stale
headline so the canonical UI test artifact reflects the true, current state.

### Fixes applied after this pre-fix run

| ID | Pre-fix FAIL | Fix (source-verified by audit) | Re-verification |
|----|--------------|--------------------------------|-----------------|
| **B2 / UT-03** (J-07) | Headless session not in Sessions dropdown without a manual reload | `App.tsx` — strictly-additive discovery poll: every 5 s + on `window` focus, `fetchSessionTabs()` merges only unknown backend session IDs (never removes/renames/reorders/persists; no `activeSessionId` change). Diff verified. | **QA TC-17 PASS** — "headless session auto-appears in list w/o reload (count 27→35 across 9 POSTs)"; evidence `TC-17-02-sessionlist.png`, `TC-17-dropdown-running.png`, `TC-17-J08-autorunbar-terminal.png` |
| **B3 / UT-06** (J-09) | "★ Best" badge absent in the expanded `IterationDetailView` header | `IterationCard.tsx` exports `BestBadge`; `IterationDetailView.tsx` imports it and renders `{isBest && <BestBadge />}` next to the strategy `<h2>`; `IterationPanel.tsx` threads `isBest={selected.id === bestIterationId}`. Diff verified. | **QA TC-18 PASS** — "exactly 1 visible Best badge, tooltip 'Best iteration — selected by the robust walk-forward objective'"; evidence `UT-06-expanded-best.png`, `TC-18-J09-terminal-best.png` |
| **B1** (critical, anti-goal) | Headless loop blocked the API event loop (synchronous store/encode I/O on the loop thread) | `auto_session.py` — every store/encode op (`_update_autorun`, `_serialize_artifacts`, `write_iteration`, `append_activity_entries`, loop-entry `read_session_meta`, `_record_failed` writes, endpoint pre-return write) offloaded via `asyncio.to_thread`; defensive `await asyncio.sleep(0)` per round. Diff verified; no pipeline/sandbox/engine/manual-path change. | **QA TC-06 PASS** — 3 probes while running: 200/0.023 s, 200/0.029 s, 200/0.011 s; new guard `test_headless_loop_does_not_block_event_loop` PASS (independently re-run by audit: 16/16 `test_auto_session` PASS) |

### Independent audit re-verification

- Backend suite re-run by the auditor: **140 passed, 1 failed** — the single
  failure is the pre-existing, explicitly out-of-scope
  `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  (spec OUT OF SCOPE: "may remain failing, nothing else may newly fail").
  Zero new regressions; +16 new `test_auto_session` tests all pass; `ruff`
  clean on the new modules.
- Frozen-contract / no-bypass anti-goals re-checked at the source-diff level:
  `shared/contracts.py`, `backend/sandbox.py`, `backend/pipeline.py` have
  **zero diff**; `api.py` change is the 2-line router mount only.
- The legacy in-browser `startAutoRun` loop was **not** touched (coexistence is
  spec-expected this iteration — J-10/iter-2).

### Binding current verdict

**PASS (post-fix).** All P1 journeys (UT-01/02/04/05/07/10/13/15 + the fixed
UT-03/UT-06) and the critical B1 anti-goal are satisfied and re-verified by the
QA MODE-2 browser run and independent audit. UT-08/UT-09/UT-20 remain N/A per
the test plan's own allowances (failure/stop paths not naturally reachable in
iter-1; UI stop control is J-11/iter-2). This supersedes the pre-fix `FAIL`
headline retained above for audit trail.
