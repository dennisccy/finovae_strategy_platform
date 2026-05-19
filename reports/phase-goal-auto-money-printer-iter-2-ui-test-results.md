# Phase goal-auto-money-printer-iter-2 — UI Test Results

**Phase:** goal-auto-money-printer-iter-2
**Date:** 2026-05-19
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** PASS

<!-- PASS: All P1 tests pass -->

**Overall:** 17/17 tests passed (0 skipped)

All 10 P1 tests (UT-01, UT-02, UT-03, UT-04, UT-05, UT-06, UT-07, UT-13,
UT-14, UT-15) **passed**. All P2/P3 tests passed. One **non-blocking UX
observation** is recorded below (transient `Auto:` session naming) — it does
not fail any test because every asserted clause still holds, but it is flagged
per the spec's skeptical-evaluation requirement.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | App loads, two-panel workstation | smoke | P1 | Header/config bar/two panels, no error | Title "Finovae Strategy Platform", Sessions+v0.3.0, all config labels, left textarea + right "No Iterations Yet", no error overlay | PASS | UT-01-app-loaded.png, UT-01-fresh-session.png |
| UT-02 | Auto Run gated until completed+suggestions | ux | P1 | No Auto Run on fresh; "Auto Run (1)"+badge after a complete iter w/ suggestions | Fresh session: no Auto Run button/bar. After manual backtest+suggestions: violet "Auto Run (1)" + `5w` worker badge + count input (min1/max100), enabled | PASS | UT-02-before-no-autorun.png, UT-15-manual-backtest-complete.png |
| UT-03 | J-10 start server-driven from config bar | happy-path | P1 | Verbatim activity entry; no local iterations; new "Auto: …" session w/ running dot; AutoRunBar progresses | Activity entry **verbatim correct**; origin stayed 1 iter; new server session discovered w/ pulsing amber dot + "running"; AutoRunBar "Automated run · iteration 1→2→3/40" w/ spinner | PASS (see Observation) | UT-03-activity-entry.png, UT-03-step5-autorunbar-running.png |
| UT-04 | J-10 survives mid-run reload | happy-path | P1 | After hard reload, Y ≥ X, progresses to terminal + Best pill | Before reload 3/40 → after hard reload 8/40 (advanced); budget-8 run reached green "complete · 8/8" + 1 Best pill after a full reload | PASS | UT-04-after-reload-progress-advanced.png, UT-16-complete-budget-reached.png |
| UT-05 | J-11 Stop from UI button | happy-path | P1 | Red "Automated run stopped"; no post-stop iters; 1 Best; Stop btn gone | Bar→red "Automated run stopped" (stop-circle); iters frozen at 18; exactly 1 Best pill; Stop btn removed. Backend: status=stopped/stopped, bestId stable, no post-stop iters | PASS | UT-05-stopped-via-ui-best-preserved.png |
| UT-06 | J-11 API stop converges in UI live | happy-path | P1 | curl 2xx fast; UI flips to stopped w/o reload; iters frozen; 1 Best | `POST /stop` → HTTP 200 in 1.8ms `{"status":"stopping"}`; UI auto-converged to red "Automated run stopped" in ~17s with **no reload** (URL unchanged); iters frozen at 2; 1 Best pill | PASS | UT-06-api-stop-converged-no-reload.png |
| UT-07 | Per-card Auto Run starts backend session | happy-path | P1 | Same info entry; no local iterations; new "Auto: …" backend session pinned to card | Per-card zap "Auto Run" → verbatim info entry; origin stayed 2 iters; new backend session `f73e0bb2` created, server-driven, params pinned (BTC/USDT 1h 2024-01-01→02-01 $10000) | PASS | UT-07-08-percard-activity-entry.png |
| UT-08 | Activity log info entry text | ux | P2 | Verbatim text; singular "1 iteration" vs plural | Plural verified (UT-03: "up to 2 iterations"); singular verified (UT-07: "up to 1 iteration"); entry plainly visible at log bottom | PASS | UT-07-08-percard-activity-entry.png |
| UT-09 | Auto Run start failure error entry | error | P2 | Red "Auto Run failed to start: …"; no session; no crash | Error entry "Auto Run failed to start: Simulated network failure…" w/ red `alert-circle` icon (text-red-500); session count 44→44 (none created); app alive, button still usable | PASS (see Method) | UT-09-error-entry-failed-to-start.png |
| UT-10 | Stop already-terminal is silent no-op | error | P2 | No error/toast; bar doesn't regress; Best/iters unchanged | Redundant stop on terminal → HTTP 200 idempotent `{"status":"stopped"}`; UI bar stayed "Automated run stopped"; no error/toast; iters & 1 Best unchanged. (Also: unknown id → 404; open-universe → 422) | PASS | (covered by UT-06 evidence + backend) |
| UT-11 | Iteration-count clamps 1–100, drives budget | validation | P2 | 0→"Auto Run (1)"; 250→"Auto Run (100)"; denominator follows | input min=1/max=100; 0 → "Auto Run (1)"; 250 → "Auto Run (100)"; denominator proven across UT-03(/2) UT-04(/40) UT-06(/30) UT-08(/1) | PASS | UT-11-count-clamp.png |
| UT-12 | New "Auto: …" discoverable ≤5 s | ux | P2 | New row appears ≤ poll tick w/ pulsing amber dot + running badge; count badge increments | New session row appeared via discovery poll w/ `bg-amber-400 animate-pulse` dot + "running" badge, no manual reload; Sessions count badge incremented | PASS (see Observation) | UT-12-running-session-dropdown.png |
| UT-13 | J-08 no stale terminal under rapid switching | regression | P1 | Still-running session: AutoRunBar running (not stale terminal); dropdown dot agrees | After rapid running↔terminal switching across 41 mounted containers: AutoRunBar "Automated run · iteration 16/40" (running, spinner, NOT terminal); dropdown amber-pulse + "running" — **agree** | PASS | UT-13-no-stale-terminal-after-rapid-switch.png |
| UT-14 | J-02 right-panel re-bind on history select | regression | P1 | RIGHT pane (equity/trades/WF) re-binds to selected run; reversible | Card "Mean Reversion" (13 trades, +1.95%, α-0.93%) → card "50 Cross Trend Filter" (16 trades, -58.67%, α-87.01%): full rebind. Switch back restored exactly. | PASS | UT-14-right-panel-rebound-older-card.png |
| UT-15 | J-01 manual backtest still works | regression | P1 | Iteration → Complete w/ metrics, equity, trades, suggestions; no removed-loop errors | Generating→Executing→Complete; metrics (Return/Trades/DD/Win/Sharpe/Sortino/PF), equity chart, 13-trade table, suggestion chips ("Loosen RSI Entry Thresholds"…); no startAutoRun errors | PASS | UT-15-manual-backtest-complete.png |
| UT-16 | AutoRunBar complete state + reason | ux | P3 | Green, check icon, "Automated run complete · <reason> · X/N"; role=status; Best pill | Green `bg-emerald-50`, check-circle2 icon, "Automated run complete · budget reached · 8/8 iterations", `role="status"` preserved, 1 Best pill | PASS | UT-16-complete-budget-reached.png |
| UT-17 | No second in-browser loop in origin session | regression | P2 | Origin card count unchanged; no AutoRunBar/Stop; only the info entry | Origin a2e211a8 stayed exactly 1 iter / `autoRun=None` after 65s; no AutoRunBar, no Stop, only 1 info entry; separate server session `aa3d3181` created | PASS | UT-17-origin-no-loop.png |

---

## Passed Tests

### UT-01 — App loads, two-panel workstation renders
**Verdict:** PASS — Header "Finovae Strategy Platform" + "Sessions" + "v0.3.0";
config bar labels Symbol/Timeframe/Start/End/Capital/Exchange all present;
left Activity panel with "Describe a trading strategy..." textarea; right panel
"No Iterations Yet" on a fresh session. No blank screen, no error overlay, no
uncaught errors.

### UT-02 — Auto Run gated until completed iteration has suggestions
**Verdict:** PASS — A brand-new session (created via "+ New Session") showed
**no** "Auto Run" button and **no** AutoRunBar. After one manual backtest
completed and suggestion chips rendered, the violet **"Auto Run (1)"** button
appeared with a `5w` worker badge and a number input (min 1, max 100), enabled.
`canAutoRun` gating (`iterationHistory.some(complete && insights.suggestions>0)`)
behaves exactly as specified.

### UT-03 — J-10: config-bar Auto Run starts a server-driven session
**Verdict:** PASS — Activity entry rendered **verbatim**: *"Started a
server-driven Auto Run (up to 2 iterations). It runs on the backend and
continues even if you close or reload this tab — a new "Auto: …" session
appears in the session list shortly."* The originating session got **no** new
iteration cards (stayed 1 iteration, `autoRun=None`). A new backend
auto-session was created and discovered in the Sessions dropdown with a pulsing
amber dot + "running" badge; opening it showed `AutoRunBar` "Automated run ·
iteration X/40" with a spinner, X advancing 1→2→3 with no manual reload. See
Observation re: transient name.

### UT-04 — J-10: server-driven run survives a mid-run browser reload
**Verdict:** PASS — With the run at **iteration 3/40**, the browser tab was
hard-reloaded. After reload + reselecting the session, the AutoRunBar showed
**iteration 8/40** (Y=8 ≥ X=3) and was still advancing — progress continued
across a full reload, which is only possible if the loop is server-driven (the
in-browser loop is deleted). A separate budget-8 server run reached the terminal
green state **"Automated run complete · budget reached · 8/8 iterations"** with
exactly one **Best** pill after a full page reload.

### UT-05 — J-11: Stop a running auto-session from the UI Stop button
**Verdict:** PASS — Clicking the amber **"Stop (18/40)"** button: AutoRunBar
turned red with a stop-circle icon reading **"Automated run stopped"**;
iteration cards froze at 18 (no post-stop iterations); exactly **one Best pill**
retained; the Stop button was removed. Backend cross-check: `status=stopped`,
`stopReason=stopped`, `currentIteration` frozen at 18/40, `bestIterationId`
(`f4e7ceb7`) stable across 24 s, no iterations appended.

### UT-06 — J-11: an API-issued stop converges in the UI with no manual reload
**Verdict:** PASS — `POST /api/auto-sessions/<id>/stop` returned **HTTP 200 in
1.8 ms** with body `{"status":"stopping"}` (non-blocking, prompt return).
Without any browser reload or click (only read-only DOM polls), the AutoRunBar
auto-converged to red **"Automated run stopped"** ~17 s later via the app's
live poll; URL unchanged (`http://localhost:3691/`), iteration count frozen at
2, one Best pill remained.

### UT-07 — Per-iteration card "Auto Run" action starts a backend auto-session
**Verdict:** PASS — The per-card violet zap "Auto Run" action logged the same
verbatim info entry (singular "up to 1 iteration"); the originating session
stayed at 2 iterations (no in-browser loop). A new backend auto-session
`f73e0bb2` was created, server-driven (`autoRun.status=complete max=1`), with
pinned config correctly derived from the card (BTC/USDT · 1h ·
2024-01-01→2024-02-01 · $10000).

### UT-08 — Activity log info entry text is accurate
**Verdict:** PASS — Verified verbatim in both forms: plural "Started a
server-driven Auto Run (up to 2 iterations)…" (UT-03) and singular "(up to 1
iteration)…" (UT-07). Entry is plainly visible at the bottom of the Activity
log.

### UT-09 — Auto Run start failure surfaces an error entry
**Verdict:** PASS — **Method:** to avoid disrupting the harness-managed backend,
the `POST /api/auto-sessions` call was failed via a scoped `window.fetch`
override (restored immediately after); this exercises the exact UI error handler
under test. Result: a red `alert-circle` (`text-red-500`) error entry **"Auto
Run failed to start: Simulated network failure (QA UT-09: backend
unreachable)"** appeared; backend session count was unchanged (44 → 44, no
session created); the app did not crash and the Auto Run button remained usable.

### UT-10 — Stop on an already-terminal auto-session is a silent no-op
**Verdict:** PASS — A redundant `POST /stop` on an already-`stopped` session
returned **HTTP 200** idempotently (`{"status":"stopped","stopReason":"stopped"}`)
with no state change (still 2 iters, best `c0d68fe0`). The still-open session's
AutoRunBar did **not** regress (stayed "Automated run stopped"); no error toast
or red failure entry. Additional error-handling cross-checks: stop on unknown
session → **HTTP 404** (`{"detail":"Auto-session … not found."}`); open-universe
`POST /api/auto-sessions` (no symbol/timeframe) → **HTTP 422** (J-12 still
correctly rejected).

### UT-11 — Iteration-count input clamps to 1–100 and drives the budget
**Verdict:** PASS — Input has `min=1 max=100`. Typing `0` clamped to `1`
("Auto Run (1)"); typing `250` clamped to `100` ("Auto Run (100)"). The budget
denominator tracking the chosen value was independently proven across UT-03
(/2), UT-04 (/40), UT-06 (/30) and UT-08 (/1).

### UT-12 — New "Auto: …" session discoverable within ~5 s
**Verdict:** PASS — After clicking Auto Run, a new session row appeared in the
"Live Sessions" list via the App.tsx discovery poll with **no manual reload**,
showing a pulsing amber dot (`bg-amber-400 animate-pulse`) + "running" badge;
the Sessions count badge incremented. See Observation re: transient name.

### UT-13 — Regression J-08: no stale AutoRunBar terminal under rapid switching
**Verdict:** PASS — With 41 `SessionContainer`s mounted, sessions were rapidly
switched running↔terminal↔running multiple cycles. On landing back on the
still-running session, its AutoRunBar showed the **running** state ("Automated
run · iteration 16/40", spinner) — **never** a stale "complete"/"stopped".
The dropdown row showed the pulsing amber dot + "running" badge; the
SessionPicker indicator and the in-session AutoRunBar **agreed**. The mandatory
iter-1 ownership-hardening lesson is satisfied.

### UT-14 — Regression J-02: selecting a prior run re-binds the RIGHT panel
**Verdict:** PASS — On an 18-iteration session: opening card "BTC 1H RSI Mean
Reversion" showed Trade History (13 trades), Total Trades 13, Annual Return
+1.95%, Alpha -0.93%. After "back to history" and opening a different older
card "BTC 1H RSI 50 Cross Trend Filter", the **entire RIGHT pane re-bound**:
Trade History (16 trades), Total Trades 16, Annual Return -58.67%, Alpha
-87.01%. Switching back to the first card restored its exact values. The right
analysis panel (not just the left summary) re-binds bidirectionally — J-02 not
regressed.

### UT-15 — Regression J-01: manual natural-language backtest works end-to-end
**Verdict:** PASS — Submitting "Buy when RSI crosses below 30, sell when it
crosses above 70" (BTC/USDT 1h 2024-01-01→2024-02-01 $10000) produced an
iteration transitioning Generating → Executing → **Complete** with metrics
(Return/Trades/Drawdown/Win/Sharpe/Sortino/Profit Factor), a non-empty equity
curve, a 13-row trades table, and suggestion chips ("Loosen RSI Entry
Thresholds", "Add Trend Filter"). No console error referencing the removed
`startAutoRun`/in-browser loop; the manual flow is unaffected by the rewire.

### UT-16 — AutoRunBar terminal "complete" state renders with the correct reason
**Verdict:** PASS — A budget-reached server session rendered the green strip
(`bg-emerald-50`) with a check-circle icon reading **"Automated run complete ·
budget reached · 8/8 iterations"**, `role="status"` preserved, with exactly one
amber **Best** pill on an iteration card. (Format matches "Automated run
complete · <reason> · X/N iterations" with reason "budget reached".)

### UT-17 — Originating session does not run a second in-browser loop
**Verdict:** PASS — After clicking "Auto Run (2)" on the originating session and
staying on it for ~65 s, its iteration count remained **exactly 1**
(`autoRun=None`), it showed **no** AutoRunBar and **no** Stop button, and the
only change was the single info entry in the Activity log. The iterate work ran
in a separate new backend session (`aa3d3181`). Anti-goal "no second in-browser
iterate loop" holds at the user-visible level.

---

## Failed Tests

None.

---

## Skipped Tests

None.

---

## Notable Observation (non-blocking) — transient `Auto:` session name

**Skeptical cross-check performed per spec (source + backend timeline, not just
the UI headline).**

The in-app activity message and the test plan both state the new session
appears **named `Auto: <strategy>…`**. Backend source confirms
`auto_session.py:670` sets `name = f"Auto: {nl[:40]}…"` at creation. However, a
timed backend `/api/sessions` index poll showed the name is **`Auto: Buy when
RSI crosses below 30, sell when…` only for ~the first 12–15 s**, after which it
is **overwritten to the first iteration's generated strategy name** (e.g.,
"BTC 1h RSI Reversion") — every observed terminal auto-session in the store is
strategy-named with no `Auto:` prefix.

**Why this does not fail UT-03 / UT-12:**
- The new session **is** discovered within one ~5 s discovery-poll tick (the
  asserted timing), and during the ~5–15 s window it **does** carry the
  `Auto: …` name, so the literal assertion "within ~5 s a new `Auto: …` session
  appears" holds.
- The running session remains unambiguously discoverable via the **pulsing
  amber dot + "running" badge** (verified; the SessionPicker dot and AutoRunBar
  agree — the J-08 guarantee), so the operator can always find it.
- The core J-10/J-11 server-driven behavior is fully correct.

**User-visible impact (minor UX):** an operator who opens the Sessions dropdown
more than ~15 s after clicking — common in practice — will not see any
`Auto:`-prefixed row, even though the activity message tells them to look for
one; they must instead rely on the running dot/badge. Recommend either
preserving the `Auto:` prefix for the run's lifetime or rewording the activity
message to point at the running indicator. Filed as an observation for the
auditor/ux-regression reviewer; it does not block this phase's named journeys.

---

## Environment

- **Frontend URL:** http://localhost:3691
- **Backend URL:** http://localhost:8691 (`CHAIN_BACKEND_PORT=8691`; the test
  plan's `:8000` is the template default — actual port used was 8691)
- **Browser:** Chrome via `mcp__plugin_superpowers-chrome_chrome__use_browser`
- **Test Date:** 2026-05-19
- **Evidence directory:** `reports/qa/goal-auto-money-printer-iter-2-evidence/`
- **Notes:** Backend LLM strategy generation verified working empirically
  (manual + multiple server-driven runs produced real generated strategies,
  insights, and trades). The app keeps all sessions mounted simultaneously
  (≥44 `SessionContainer`s) — the exact multi-mount condition the iter-1
  lesson targets; UT-13 was executed under this real condition. Auto-runs
  here complete fast (~22 s/iteration, cached data), so larger budgets
  (8/30/40) were used to reliably observe running states for the
  reload/stop/switch tests; the asserted behaviors (not the example budget
  numbers) were verified.
