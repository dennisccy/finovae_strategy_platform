# Phase goal-auto-money-printer-iter-6 — UI Test Plan

**Phase:** goal-auto-money-printer-iter-6
**Date:** 2026-05-19
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3691

---

## Scope

This plan covers the only changed frontend surface in iter-6 — `ActivityLogEntry.tsx`'s
`complete` branch (additive muted sub-line under the emerald card) and the
unchanged `auto-run` row that now receives a new terminal-summary emission from
the backend. The `Best` badge on `IterationCard.tsx` is the touchstone for
co-location with the new rationale text. SCREEN entries and pinned-path
`complete` entries are anti-regression touchstones.

All tests run against an open-universe automated run produced by submitting an
auto-session via the chat panel (natural-language strategy → "objective: robust"
auto run). No new UI controls were added — every step uses existing buttons,
fields, and routes.

---

## Test Cases

<!-- Test IDs use UT-XX prefix to distinguish from functional test plan TC-XX IDs. -->
<!-- Each test MUST have exact steps and specific expected results. -->

---

### UT-01 — Main session view loads with Activity Log column (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (main session view, Activity Log column)

**Preconditions:**
- Frontend running at http://localhost:3691
- Backend running and reachable (verify `curl http://localhost:${CHAIN_BACKEND_PORT:-8000}/api/health` returns 200)
- No prior session required — empty session list is acceptable

**Steps:**
1. Open Chrome and navigate to `http://localhost:3691`
2. Wait for the page to finish loading (no spinner in the main content)
3. Open Chrome DevTools → Console tab

**Expected Result:**
- Main session view renders with three panels visible: chat/prompt on the left, iteration list in the middle column, and the Activity Log column on the right (or per current layout)
- No red error overlay appears
- DevTools Console shows zero `error` level entries originating from `ActivityLogEntry.tsx` or `useBacktest.ts`
- No `null`, `undefined`, `NaN`, or `Infinity` literal text appears in any rendered Activity Log row

---

### UT-02 — Open-universe run renders PROMOTE rationale sub-line under emerald `complete` card (happy path — primary J-16 demonstration)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (main session view, Activity Log column) — `ActivityLogEntry.tsx` `complete` branch

**Preconditions:**
- Frontend at http://localhost:3691, backend reachable
- `BACKTEST_STORE_DIR` is the durable default (NOT `/tmp`)
- No existing in-flight auto-run on the same session

**Steps:**
1. Navigate to `http://localhost:3691`
2. In the chat input on the left panel, type the natural-language strategy: `momentum breakout`
3. If a budget/iterations control is visible, set "max iterations" to `4` and "max configs" to `4`; otherwise rely on defaults sufficient for ≥ 2 PROMOTE candidates
4. If an explicit "Auto run" or "Robust objective" toggle is visible, enable it; otherwise submit the prompt — the open-universe robust auto-run is the default for this entry style
5. Click the "Send" (paper-airplane icon) button to submit
6. Wait up to 5 minutes, watching the Activity Log column on the right, until the AutoRunBar at the top of the page shows the run has reached a terminal state (status text reads `idle`, `complete`, `budget-exhausted`, or `stopped` — no spinner)
7. Scroll the Activity Log column to locate every emerald-bordered card with a green `CheckCircle2` icon whose top line reads `return X% over N trades, robust Y, walk-forward WFE Z` (these are the PROMOTE `complete` entries)
8. Count the emerald cards: confirm there are ≥ 2 of them

**Expected Result:**
- ≥ 2 emerald-bordered `complete` cards appear in the Activity Log
- **Every** emerald card shows TWO lines of text inside the card:
  - Top line: the existing numeric summary in `text-sm font-medium text-emerald-700` (e.g., `return 12.0% over 25 trades, robust 1.50, walk-forward WFE 0.70`)
  - Bottom line: a muted `text-xs text-emerald-700/70 mt-1` sub-line containing a rationale string
- Exactly **one** of the rationale sub-lines starts with `Best — ` (e.g., `Best — WF-validated (WFE 0.70, 25 trades)`) OR with `Best (sole survivor) — `
- Every **other** emerald card's rationale sub-line starts with `Not best — ` followed by a specific gate reason (one of: `no walk-forward windows`, `WFE X.XX below 0.30 gate`, `under min-trades floor (N < 5)`, `over-leveraged (X.X×)`, or `lower robust score (X.XX vs best Y.YY)`)
- The text contains no `null`, `undefined`, `NaN`, `Infinity`, `−∞` followed by `inf`, `nan`, or `[object Object]` substrings
- The text contains no `sk-`, `Bearer `, `API_KEY`, or other secret-shaped substring
- The emerald card dimensions and border styles are byte-identical to today (still `bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3`) — no new icon, badge, panel, or container appears

---

### UT-03 — `Best` badge co-locates with the `Best — …` rationale on the same iteration (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (main session view, Iteration list column) — `IterationCard.tsx` `Best` badge — touchstone for J-16

**Preconditions:**
- UT-02 has completed successfully on an open-universe session that produced ≥ 2 PROMOTE `complete` entries
- The session is still open in the browser

**Steps:**
1. Stay on `http://localhost:3691` with the UT-02 session open
2. In the iteration list column, locate the iteration card displaying a `Best` badge (small text badge — same one shown today)
3. Note the iteration id (or position) shown on that card (e.g., `iter-3`)
4. Scroll the Activity Log column to find the emerald `complete` card for that exact iteration (the one whose top-line numeric summary matches that iteration's metrics — or whose internal `iterId`/title corresponds; sequential PROMOTE entries are in the order they completed)
5. Read the muted sub-line under that emerald card

**Expected Result:**
- The iteration carrying the `Best` badge in the middle column has, in the Activity Log column, a `complete` card whose muted sub-line **begins** with `Best — ` (or `Best (sole survivor) — `)
- No `complete` card with a sub-line beginning `Not best — ` corresponds to the iteration carrying the `Best` badge
- The `Best` badge is visually unchanged from before iter-6 (no new color, icon, or position) — same component, same source-of-truth (`autoRun.bestIterationId`)

---

### UT-04 — Terminal-summary `auto-run` row appears at end of multi-PROMOTE run (happy path)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (main session view, Activity Log column) — `ActivityLogEntry.tsx` `auto-run` branch (violet `Zap` icon row)

**Preconditions:**
- UT-02 has completed (open-universe run with ≥ 2 PROMOTE `complete` cards)
- The session is still open in the browser

**Steps:**
1. Stay on `http://localhost:3691` with the UT-02 session open
2. Scroll the Activity Log column to its bottom
3. Locate the LAST entries in the feed (just before any terminal `idle`/`stopped` marker that may follow)
4. Look for a row with a violet `Zap` icon and violet `text-xs font-medium` text

**Expected Result:**
- Exactly ONE violet `Zap`-icon row appears near the bottom of the feed whose text begins with the literal substring `Robust-best: `
- The full text matches the shape: `Robust-best: <iter-id> selected over <N-1> other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage`
- `<N-1>` is an integer (the count of OTHER PROMOTE candidates; if 2 PROMOTEs completed, this is `1`)
- The iter-id referenced in the row matches the iteration carrying the `Best` badge from UT-03
- The text contains no `null`, `undefined`, `NaN`, `Infinity`, `nan`, or `inf` substrings

---

### UT-05 — Single-PROMOTE run does NOT emit the terminal `Robust-best: …` summary row (validation — emission gate)

**Type:** validation
**Priority:** P2
**Surface:** `/` (main session view, Activity Log column) — `ActivityLogEntry.tsx` `auto-run` branch

**Preconditions:**
- Frontend at http://localhost:3691, backend reachable
- Empty session list is acceptable; previous UT-02 session may co-exist

**Steps:**
1. Navigate to `http://localhost:3691`
2. In the chat input, type the natural-language strategy: `single conservative momentum`
3. If a budget control is visible, set "max configs" to `1` (the minimum); otherwise pick the tightest budget the UI exposes that still allows at least one PROMOTE
4. Click "Send"
5. Wait up to 3 minutes for the AutoRunBar to reach a terminal state
6. Scroll the Activity Log column for the new session and count the emerald `complete` cards
7. Inspect the violet-icon rows at the bottom of the feed

**Expected Result:**
- ≤ 1 emerald `complete` card appears (the one PROMOTE survivor, or zero if no PROMOTE completed)
- NO violet `Zap` row beginning with `Robust-best: ` appears anywhere in the feed for this session
- If exactly 1 PROMOTE complete card is present, its rationale sub-line begins with `Best — WF-validated (…)` or `Best (sole survivor) — gates not met: <reason>` (per its own gates); the rationale is still rendered for the single PROMOTE
- No regression in the rest of the activity feed: SCREEN entries, `ai-step` rows, prompt rows, and `auto-run` start/stop rows still render as today

---

### UT-06 — Activity log free of unsafe numeric/object literals (error / data-hygiene)

**Type:** error
**Priority:** P2
**Surface:** `/` (main session view, Activity Log column) — all `complete` and `auto-run` rows from iter-6 emissions

**Preconditions:**
- UT-02 and (if applicable) UT-04 sessions exist in the browser
- Browser DevTools open (F12) with Console tab visible

**Steps:**
1. Navigate to `http://localhost:3691` and open the UT-02 session
2. Press `Ctrl+F` (Cmd+F on macOS) inside the rendered page to invoke the browser in-page search
3. Search the visible page for the literal string `null`
4. Search for `undefined`
5. Search for `NaN`
6. Search for `Infinity`
7. Search for `[object Object]`
8. Search for `sk-` (would indicate an OpenAI-style key leak)
9. Search for `Bearer `
10. Switch to the DevTools Console tab and look for any red-level errors logged during the activity-feed render

**Expected Result:**
- The in-page search reports `Phrase not found` (or `0 of 0`) for each of `null`, `undefined`, `NaN`, `Infinity`, `[object Object]`, `sk-`, `Bearer `
- DevTools Console shows zero red-level errors emitted during the activity-feed render
- The rationale text is rendered in plain English with finite numeric formatting (e.g., `WFE 0.00`, `2 < 5`, `1.5×`) — never `nan`, never `inf`, never `null`

---

### UT-07 — Pinned-path `complete` rows render without a rationale sub-line (regression — J-07–J-11 invariance)

**Type:** regression
**Priority:** P1
**Surface:** `/` (main session view, Activity Log column) — `ActivityLogEntry.tsx` `complete` branch on a pinned-path run

**Preconditions:**
- Frontend at http://localhost:3691, backend reachable
- At least one pinned-path session exists (run a manual pinned strategy or open a prior session known to be pinned-only — J-07 fixture if available)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Open the session list (sidebar or top-bar control) and select an existing pinned-path session
3. (If none exists) In the chat input, type a manual single-strategy prompt like `buy when SMA(10) crosses above SMA(30) on BTC-USDT 1h` and click "Send"; wait for the single `complete` row to appear in the Activity Log
4. Locate any emerald `complete` card produced by the pinned-path run
5. Inspect the card's content carefully

**Expected Result:**
- The emerald card shows EXACTLY ONE line of text (the existing top-line summary) inside the `flex-1 min-w-0` div — NO muted `text-xs text-emerald-700/70` sub-line beneath it
- Card dimensions, border, padding, icon position, and elapsed-time formatting are byte-identical to pre-iter-6 behavior (visually indistinguishable from a screenshot taken before iter-6 of a pinned `complete` row)
- The card does NOT contain the substrings `Best — `, `Not best — `, or `Best (sole survivor) — ` anywhere
- No violet `Zap`-icon row beginning `Robust-best: ` appears in the feed for this pinned session

---

### UT-08 — SCREEN entries render without a rationale sub-line (regression — J-14 invariance)

**Type:** regression
**Priority:** P1
**Surface:** `/` (main session view, Activity Log column) — `ActivityLogEntry.tsx` SCREEN-stage entries

**Preconditions:**
- UT-02 session is open (open-universe run with both SCREEN and PROMOTE stages)

**Steps:**
1. Navigate to `http://localhost:3691` and open the UT-02 session
2. Scroll the Activity Log column to the earlier portion of the feed (before PROMOTE entries appear)
3. Locate SCREEN-stage entries — `ai-step` rows or completes whose top-line content references `SCREEN` (e.g., `SCREEN: BTC-USDT 1h …`) or whose stage marker indicates SCREEN
4. For each SCREEN entry that renders inside an emerald `complete`-style card (if any), inspect the inner content

**Expected Result:**
- NO SCREEN-stage entry (whether rendered as `ai-step`, `complete`, or `SCREEN done`) carries a muted `text-xs text-emerald-700/70` sub-line beneath its main content
- No SCREEN entry contains the substrings `Best — `, `Not best — `, or `Best (sole survivor) — ` anywhere
- SCREEN entries' visual layout is byte-identical to pre-iter-6 behavior

---

### UT-09 — Prior completed iteration's detail still loads when clicked (regression — J-02)

**Type:** regression
**Priority:** P1
**Surface:** `/` (main session view, Iteration list + detail panel)

**Preconditions:**
- At least one prior completed session/iteration exists in the durable store
- Frontend at http://localhost:3691

**Steps:**
1. Navigate to `http://localhost:3691`
2. Open the session list and select any prior session whose status reads `complete` (preferably from before iter-6, e.g., one of the previously-recorded sessions in the store)
3. In the iteration list column, click any iteration card whose status indicator is green/done
4. Wait for the detail panel to populate

**Expected Result:**
- The detail panel populates with: strategy spec text, metrics block (return / Sharpe / drawdown), trade list with ≥ 1 row, and an equity-curve chart with at least one visible line
- No red error overlay
- DevTools Console shows zero red-level errors during the load
- The Activity Log column re-loads its prior entries; if this was a pre-iter-6 session, NO `complete` row carries a rationale sub-line (the backend never emitted one for that run), confirming `entry.detail` absence renders identically to pre-iter-6

---

### UT-10 — AutoRunBar spend tokens / USD / configs render without NaN (regression — J-13)

**Type:** regression
**Priority:** P2
**Surface:** `/` (main session view, top AutoRunBar)

**Preconditions:**
- UT-02 session (terminal) is open in the browser

**Steps:**
1. Navigate to `http://localhost:3691` and open the UT-02 session
2. Locate the AutoRunBar at the top of the main content (status + spend + caps + stop button area)
3. Read each numeric span in the bar: tokens used, USD spent, configs explored

**Expected Result:**
- Each numeric span shows a finite integer or fixed-decimal number (e.g., `1,234`, `$0.05`, `4`)
- No span contains the substrings `NaN`, `undefined`, `null`, `Infinity`
- The terminal-state reason (e.g., `budget-exhausted`, `complete`) renders as plain English text
- The AutoRunBar's spend ≤ the configured caps (informational; not a strict pass criterion if the run completed naturally rather than via cap exhaustion)

---

### UT-11 — Rationale text is in plain operator language (UX)

**Type:** ux
**Priority:** P2
**Surface:** `/` (main session view, Activity Log column) — rationale sub-lines from UT-02

**Preconditions:**
- UT-02 session is open with ≥ 2 PROMOTE rationale sub-lines visible

**Steps:**
1. Open `http://localhost:3691` and select the UT-02 session
2. Read each rationale sub-line under each emerald `complete` card aloud (or to yourself as if you were a non-developer operator)
3. Note any term that requires developer knowledge to interpret

**Expected Result:**
- Each rationale sub-line uses operator-readable vocabulary:
  - Numeric gate names spelled in plain English: `WFE`, `min-trades floor`, `over-leveraged`, `walk-forward windows`, `lower robust score`
  - Concrete numeric values with units where applicable (e.g., `0.30 gate`, `5 trades`, `1.5×`)
  - No raw Python identifiers (`_GATE_FAIL_PENALTY`, `DEFAULT_MIN_WFE`, `RobustInputs`)
  - No `null`/`undefined` placeholders for missing fields (fallback reads `"Not best — gate evaluation unavailable"` instead)
- The terminal `Robust-best: …` row's gate list (`WFE ≥ 0.30, ≥ 5 trades, no over-leverage`) is human-readable

---

### UT-12 — Rationale sub-line is visually subordinate to the existing top line (UX)

**Type:** ux
**Priority:** P3
**Surface:** `/` (main session view, Activity Log column) — `ActivityLogEntry.tsx` `complete` branch

**Preconditions:**
- UT-02 session is open with ≥ 2 PROMOTE `complete` cards visible

**Steps:**
1. Open `http://localhost:3691` and select the UT-02 session
2. Compare the typography of the top line (existing numeric summary) vs the muted sub-line (rationale) on a single emerald card
3. Inspect with DevTools (F12 → Elements) — locate the rationale `<p>` element and check its computed CSS

**Expected Result:**
- Visually, the rationale sub-line is rendered at a smaller font size (`text-xs`, i.e., 12px) than the top line (`text-sm`, i.e., 14px)
- The rationale sub-line uses a muted color (computed color matches `text-emerald-700/70` — approximately `rgba(4, 120, 87, 0.7)`) rather than the bold emerald of the top line
- The rationale sub-line carries `mt-1` (4px top margin) — visually pinned beneath the top line without overlapping or doubling the card height
- The emerald card height has grown by approximately the height of one extra line of `text-xs` (~16-20px) vs a pre-iter-6 single-line `complete` card — not by two full lines or by visually-disruptive padding

---

## Test Summary

| ID    | Name                                                                     | Type        | Priority | Surface                                          |
|-------|--------------------------------------------------------------------------|-------------|----------|--------------------------------------------------|
| UT-01 | Main session view loads with Activity Log column                         | smoke       | P1       | `/`                                              |
| UT-02 | Open-universe PROMOTE rationale renders under emerald cards              | happy-path  | P1       | `/` Activity Log (`complete` branch)             |
| UT-03 | `Best` badge co-locates with `Best — …` rationale                        | happy-path  | P1       | `/` Iteration list (`IterationCard`) + feed      |
| UT-04 | Terminal `Robust-best:` summary row appears on multi-PROMOTE run         | happy-path  | P1       | `/` Activity Log (`auto-run` branch)             |
| UT-05 | Single-PROMOTE run does NOT emit terminal summary                        | validation  | P2       | `/` Activity Log (`auto-run` branch)             |
| UT-06 | No `null`/`undefined`/`NaN`/`Infinity`/secret literals in feed           | error       | P2       | `/` Activity Log (all rows)                      |
| UT-07 | Pinned-path `complete` rows have no rationale sub-line                   | regression  | P1       | `/` Activity Log (`complete` on pinned)          |
| UT-08 | SCREEN entries have no rationale sub-line                                | regression  | P1       | `/` Activity Log (SCREEN entries)                |
| UT-09 | Prior iteration detail still loads when clicked                          | regression  | P1       | `/` Iteration list + detail panel                |
| UT-10 | AutoRunBar spend renders without NaN                                     | regression  | P2       | `/` AutoRunBar                                   |
| UT-11 | Rationale text is in plain operator language                             | ux          | P2       | `/` Activity Log (rationale sub-lines)           |
| UT-12 | Rationale sub-line is visually subordinate to top line                   | ux          | P3       | `/` Activity Log (`complete` branch)             |

**P1 tests must all pass for browser QA verdict to be PASS.**

P1 tests: UT-01, UT-02, UT-03, UT-04, UT-07, UT-08, UT-09
P2 tests: UT-05, UT-06, UT-10, UT-11
P3 tests: UT-12

UT-02, UT-03, UT-04 are the J-16 primary acceptance proofs in the browser. UT-07
and UT-08 are the structural anti-regression proofs (pinned and SCREEN paths
visually unchanged). UT-09 is the J-02 history-browse regression proof.
