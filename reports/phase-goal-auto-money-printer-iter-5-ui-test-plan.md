# Phase goal-auto-money-printer-iter-5 — UI Test Plan

**Phase:** goal-auto-money-printer-iter-5
**Date:** 2026-05-19
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3691
**Backend URL:** http://localhost:8691

---

## Context (read before running)

No frontend code changed this phase. The only new user-visible artifact is a
single **warm-start planner-decision note** that flows through the **existing**
Activity feed. There is **no UI control** to start an open-universe headless run
with a `history_scope` — the scenario is created by `POST /api/auto-sessions`
calls (mirroring functional test plan TC-01/02/03), then verified in the browser.
These API calls are **one-time setup**, not the thing under test; the tests below
verify what an operator *sees* in the browser.

### Exact string under test (verbatim from `auto_session.py:718-720`)

```
Warm start (global history): prioritising <SYM> <TF> — prior best robust <S> across <N> prior <session|sessions>
```

- `<SYM>` is one of the bounded seed families: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`
- `<TF>` is `4h` or `1h`
- `<S>` is a 2-decimal score, e.g. `0.78`
- separator is an em-dash `—`
- trailing word is literally `session` when `<N>` is 1, else `sessions` (NOT the literal text "session(s)")
- Concrete example: `Warm start (global history): prioritising BTC/USDT 4h — prior best robust 0.78 across 1 prior session`

### How to tell the warm-start note apart from other violet ⚡ rows (critical)

Every open-universe run already emits other violet ⚡ `auto-run` rows
(`Automated iteration 1/2`, `SCREEN config 1: BTC/USDT 4h`,
`PROMOTE config: …`). These are **not** the warm-start note. The warm-start note
is uniquely identified by **BOTH**:
1. It is rendered **ungrouped at the very top of the Activity feed**, *above* every
   collapsible iteration card (all SCREEN/PROMOTE/iteration rows live *inside* the
   collapsible iteration accordions).
2. Its text starts with the literal prefix **`Warm start (global history): prioritising`**.

An "absence" test passes only when **no row begins with
`Warm start (global history):`** anywhere in the feed — not merely "no violet rows"
(violet SCREEN/PROMOTE rows still exist inside the iteration accordions).

---

## Shared Test Setup (run once; produces the sessions the UI tests open)

Use a tiny budget so each run reaches a terminal state in ~1–3 min. All runs
must hit the **same** backend store (the default durable store; do not isolate
between runs 1→2→3). Backend must have `OPENAI_API_KEY` set (auto-sessions invoke
the LLM compiler).

**S-1 — Run #1 (producer; no prior history; default scope):**
```bash
curl -s -X POST "http://localhost:8691/api/auto-sessions" \
  -H 'Content-Type: application/json' \
  -d '{"natural_language":"warmstart producer run1","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'
```
Wait until terminal: poll `GET http://localhost:8691/api/sessions/<sessionId>`
until `autoRun.status` is not `running`/`queued`, OR watch its AutoRunBar in the
UI turn amber "budget reached". Note which `(symbol, timeframe)` family it
promoted first — call it **F1**.

**S-2 — Run #2 (`history_scope:"global"`; mines Run #1):**
```bash
curl -s -X POST "http://localhost:8691/api/auto-sessions" \
  -H 'Content-Type: application/json' \
  -d '{"natural_language":"warmstart global run2","objective":"robust","history_scope":"global","budget":{"max_iterations":2,"max_configs":2}}'
```

**S-3 — Run #3 (`history_scope:"this-run"`; opt-out):**
```bash
curl -s -X POST "http://localhost:8691/api/auto-sessions" \
  -H 'Content-Type: application/json' \
  -d '{"natural_language":"warmstart optout run3","objective":"robust","history_scope":"this-run","budget":{"max_iterations":2,"max_configs":2}}'
```

**S-4 — Pinned run (manual-style; for the pinned-path regression UT-12):**
```bash
curl -s -X POST "http://localhost:8691/api/auto-sessions" \
  -H 'Content-Type: application/json' \
  -d '{"natural_language":"Buy when RSI<30, sell when RSI>70","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-02-01","initial_capital":10000,"model":"gpt-5.4-mini","budget":{"max_iterations":2}}'
```

**S-5 — Garbage scope run (for UT-13; prior history from S-1 present):**
```bash
curl -s -X POST "http://localhost:8691/api/auto-sessions" \
  -H 'Content-Type: application/json' \
  -d '{"natural_language":"warmstart garbage scope","objective":"robust","history_scope":"garbage-value","budget":{"max_iterations":2,"max_configs":2}}'
```

Each headless run appears in the UI Sessions dropdown as
`Auto: <first 40 chars of natural_language>` — e.g. `Auto: warmstart global run2`.

---

## Test Cases

<!-- UT-XX prefix distinguishes these from functional plan TC-XX IDs. -->

---

### UT-01 — App loads, Sessions control visible (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (header)

**Preconditions:**
- Frontend running at http://localhost:3691; backend running at http://localhost:8691

**Steps:**
1. Navigate to `http://localhost:3691`
2. Wait for the page to fully load (≤5 s)

**Expected Result:**
- The header shows the title text **"Finovae Strategy Platform"**
- A **"Sessions"** button (clock icon, grey pill) is visible in the top-right of the header, next to the version text **"v0.3.0"**
- No blank screen, no error overlay, no red error box
- Browser console shows no uncaught exceptions

---

### UT-02 — Headless auto-session auto-appears in Sessions dropdown within ~5 s, no reload (happy-path / discovery)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (header → Sessions dropdown / `SessionPicker`)

**Preconditions:**
- Frontend tab already open at `http://localhost:3691` and left untouched (no reload)
- About to issue Shared Setup **S-1**

**Steps:**
1. With the browser tab already open at `http://localhost:3691`, run Shared Setup **S-1** in a terminal
2. Do **not** reload the browser tab
3. Wait ~5–8 seconds
4. Click the **"Sessions"** button in the header
5. Read the **"Live Sessions"** section of the dropdown

**Expected Result:**
- A new live session row labelled **`Auto: warmstart producer run1`** appears in the "Live Sessions" list **without any page reload**
- While the run is active the row shows an amber pulsing dot and the text **"running"**
- Clicking that row closes the dropdown and selects the session (its row shows **"(active)"** when the dropdown is reopened)
- After selecting, the Activity feed (left panel on desktop) for that session is shown

---

### UT-03 — Warm-start citation visible on a `global` run with prior history (happy-path — PRIMARY J-15)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (selected session → Activity feed → `auto-run` violet ⚡ row)

**Preconditions:**
- Shared Setup **S-1** is terminal (Run #1 produced a promoted best in family **F1**)
- Shared Setup **S-2** has been issued

**Steps:**
1. Navigate to `http://localhost:3691`
2. Click the **"Sessions"** button in the header
3. In "Live Sessions", click the row **`Auto: warmstart global run2`**
4. Wait until that session's run is terminal (its AutoRunBar — the thin status strip directly under the header — stops showing the spinner; see UT-10)
5. In the Activity feed (left half of the screen on desktop; on a narrow window first click the **"Activity"** tab), **scroll to the very top of the feed**

**Expected Result:**
- At the **top** of the Activity feed, above every collapsible iteration card, there is one violet row: a small ⚡ (lightning) icon followed by violet text
- The text reads exactly, with real values substituted:
  `Warm start (global history): prioritising <SYM> <TF> — prior best robust <S> across <N> prior session` (or `… sessions` if `<N>` > 1)
  e.g. `Warm start (global history): prioritising BTC/USDT 4h — prior best robust 0.78 across 1 prior session`
- `<SYM> <TF>` matches Run #1's first promoted family **F1** (one of `BTC/USDT`/`ETH/USDT`/`SOL/USDT`/`BNB/USDT` and `4h`/`1h`)
- The full sentence is visible and **not truncated** (no `…`, the row wraps if needed, the prior robust score and session count are both readable)
- Save a screenshot to `reports/qa/goal-auto-money-printer-iter-5-evidence/UT-03-run2-warmstart-citation.png`

---

### UT-04 — Warm-start note renders at top of feed, above iteration accordions, visible without expanding (happy-path / placement)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (selected session → Activity feed → ungrouped region, above iteration accordions)

**Preconditions:**
- UT-03 set up (Run #2 `Auto: warmstart global run2` selected and terminal)

**Steps:**
1. With `Auto: warmstart global run2` selected, scroll to the very top of the Activity feed
2. Without clicking/expanding anything, look at the vertical order of items in the feed

**Expected Result:**
- The `Warm start (global history): prioritising …` violet ⚡ row is the **first** item in the feed
- It appears **above** the first collapsible iteration card (the rounded boxes with a chevron `›`/`⌄` and a status icon)
- It is fully readable **without expanding any iteration accordion** (no need to click any `›` chevron to reveal it)
- The SCREEN/PROMOTE/`Automated iteration` violet rows are *inside* the collapsible iteration cards, **below** the warm-start row — confirming the warm-start note is the only ungrouped (run-level) entry

---

### UT-05 — Default / omitted `history_scope` also warm-starts (citation present) (happy-path)

**Type:** happy-path
**Priority:** P2
**Surface:** `/` (selected session → Activity feed → `auto-run` violet ⚡ row)

**Preconditions:**
- Shared Setup **S-1** terminal (prior history present)
- Issue a default-scope run (NO `history_scope` key):
  ```bash
  curl -s -X POST "http://localhost:8691/api/auto-sessions" \
    -H 'Content-Type: application/json' \
    -d '{"natural_language":"warmstart default omitted","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'
  ```

**Steps:**
1. Navigate to `http://localhost:3691`
2. Open the **"Sessions"** dropdown, click **`Auto: warmstart default omitted`**
3. Wait until terminal; scroll to the top of the Activity feed

**Expected Result:**
- A `Warm start (global history): prioritising <SYM> <TF> — prior best robust <S> across <N> prior session(s)` violet ⚡ row IS present at the top of the feed (omitting `history_scope` behaves like `"global"` — the optimizer still learns from prior runs)
- The feed is visually identical in shape to UT-03 (no extra/missing UI; just the default behaving as global)

---

### UT-06 — `history_scope:"this-run"` shows NO warm-start citation (validation / opt-out absence)

**Type:** validation
**Priority:** P1
**Surface:** `/` (selected session → Activity feed → absence of the warm-start row)

**Preconditions:**
- Shared Setup **S-1** and **S-2** terminal (prior history definitely present in the store)
- Shared Setup **S-3** issued (`Auto: warmstart optout run3`)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Open the **"Sessions"** dropdown, click **`Auto: warmstart optout run3`**
3. Wait until terminal
4. In the Activity feed, scroll from the very top to the very bottom and read every row
5. (Optional, faster) Use the browser Find (Ctrl/Cmd+F) and search the page for the text `Warm start (global history)`

**Expected Result:**
- **No** row anywhere in the feed begins with `Warm start (global history):`
- The Find search for `Warm start (global history)` yields **0 matches**
- The run still completed normally: collapsible iteration cards are present and the AutoRunBar reached a terminal state (the opt-out only removes the warm-start note + reorder, it does not break the run)
- Note: violet ⚡ rows for `SCREEN config …` / `PROMOTE config …` / `Automated iteration …` *inside* the iteration cards are expected and are NOT the warm-start note
- Save a screenshot to `reports/qa/goal-auto-money-printer-iter-5-evidence/UT-06-run3-no-citation.png`

---

### UT-07 — Empty-history `global`/default run shows NO warm-start note, run still completes (validation / graceful absence)

**Type:** validation
**Priority:** P2
**Surface:** `/` (selected session → Activity feed → absence with empty history)

**Preconditions:**
- Run #1 from Shared Setup **S-1** is the FIRST open-universe run in the store (it ran against no prior promoted history) — this is the natural empty-history case and needs no extra infra. (If the store already had prior auto-sessions, instead point the backend at an empty `BACKTEST_STORE_DIR` and issue a fresh `"global"` run.)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Open the **"Sessions"** dropdown, click **`Auto: warmstart producer run1`**
3. Wait until terminal; scroll the entire Activity feed; (optional) Ctrl/Cmd+F search `Warm start (global history)`

**Expected Result:**
- **No** `Warm start (global history):` row appears anywhere (empty store → no usable prior evidence → no citation; byte-identical to pre-iter-5 behaviour)
- The run still completed: the feed shows ≥2 distinct SCREEN config rows (e.g. `SCREEN config 1: BTC/USDT 4h`, `SCREEN config 2: ETH/USDT 4h`) inside the iteration cards and the AutoRunBar reached a terminal state
- Find search for `Warm start (global history)` yields **0 matches**

---

### UT-08 — Warm-start note is visually identical to existing SCREEN/PROMOTE notes; no new component (ux)

**Type:** ux
**Priority:** P2
**Surface:** `/` (selected session → Activity feed → `ActivityLogEntry`)

**Preconditions:**
- UT-03 done (`Auto: warmstart global run2` selected, warm-start note visible)

**Steps:**
1. With the warm-start note visible at the top of the feed, expand one iteration card (click its `›` chevron) and locate a `SCREEN config …` violet row inside it
2. Visually compare the warm-start row to that `SCREEN config …` row

**Expected Result:**
- Both use the **same** small violet ⚡ (lightning) icon and the **same** violet text styling and the **same** compact single-line row layout
- The warm-start row introduces **no new panel, badge, button, modal, color, or section** — it is the same `auto-run` entry shape the feed already rendered before this phase (a headless warm-started run is UI-indistinguishable from a manual one in shape)
- The only difference is its position (top/ungrouped) and its wording (`Warm start (global history): …`)

---

### UT-09 — Operator can distinguish the warm-start note from other ⚡ rows by prefix + position (ux)

**Type:** ux
**Priority:** P2
**Surface:** `/` (selected session → Activity feed)

**Preconditions:**
- `Auto: warmstart global run2` (has the note) and `Auto: warmstart optout run3` (no note) both terminal

**Steps:**
1. Select `Auto: warmstart global run2`; at the top of the feed read the first row's leading words
2. Expand an iteration card; read a `SCREEN config …` and a `PROMOTE config …` row's leading words
3. Select `Auto: warmstart optout run3`; read the first row of its feed (top, ungrouped)

**Expected Result:**
- Only the run #2 top row begins with `Warm start (global history): prioritising` — the SCREEN/PROMOTE rows begin with `SCREEN config` / `PROMOTE config` / `Automated iteration` and are clearly different text
- For run #3 (opt-out) the first feed item is **not** a `Warm start (global history):` row (it is the first iteration card / a non-warm-start entry) — confirming an operator can reliably tell "warm-started" from "opted-out" by the presence of that exact prefix at the top of the feed

---

### UT-10 — AutoRunBar live status + spend still works for a warm-started run (regression — J-08 / J-13)

**Type:** regression
**Priority:** P1
**Surface:** `/` (selected session → AutoRunBar — thin status strip under the header)

**Preconditions:**
- A warm-started run is freshly issued (re-issue **S-2** with a fresh NL, e.g. `warmstart live status check`, and select it immediately so its run is observed live)

**Steps:**
1. Navigate to `http://localhost:3691`, open **"Sessions"**, select the freshly-issued warm-started session while it is still running
2. Observe the thin status strip directly **below the header and above the two-panel area** (the AutoRunBar)
3. Keep watching it (do NOT reload the page) until the run finishes

**Expected Result:**
- While running: the strip shows a spinning icon and text like **"Automated run · iteration 1/2"**; a spend readout (e.g. `1,234 tok · $0.0042 · 2 cfg`) appears on the right and increases as the run progresses
- The strip transitions **without a manual reload** from running → a terminal state
- On budget exhaustion the strip turns **amber** with a $-style icon and text **"Automated run complete · budget reached · 2/2 iterations"**
- No `NaN`, `undefined`, or empty value appears in the iteration counter or the spend readout

---

### UT-11 — Prior session iteration history/detail browse unaffected after the new run (regression — J-02, iter-0 lesson)

**Type:** regression
**Priority:** P1
**Surface:** `/` (prior session → right panel iteration detail / history)

**Preconditions:**
- Shared Setup **S-1** terminal, AND **S-2** (the global mining run) has since been issued and is terminal (the miner has read Run #1 read-only)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Open the **"Sessions"** dropdown, select the **prior** producer session **`Auto: warmstart producer run1`**
3. On desktop look at the right panel; on a narrow window click the **"Iterations"** tab
4. Click a completed iteration in that session's iteration list/tree
5. Inspect the loaded detail: strategy spec, metrics, trades, and equity curve

**Expected Result:**
- Run #1's iteration list is unchanged: same number of iterations, same order, none missing or renamed (the miner is read-only)
- Clicking an iteration loads its detail panel with a metrics summary, a trades list, and an equity chart that renders (no error box, no "failed to load", no empty/blank detail)
- The displayed values match Run #1's original results — the global mining run did not mutate, reorder, or corrupt Run #1's prior artifacts

---

### UT-12 — Pinned (manual-style) session shows NO warm-start note (regression — pinned path byte-unchanged)

**Type:** regression
**Priority:** P2
**Surface:** `/` (selected pinned session → Activity feed)

**Preconditions:**
- Prior history present (S-1/S-2 terminal) AND Shared Setup **S-4** issued (the pinned/manual-style run)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Open the **"Sessions"** dropdown, select **`Auto: Buy when RSI<30, sell when RSI>70`**
3. Wait until terminal; scroll the whole Activity feed; (optional) Ctrl/Cmd+F search `Warm start (global history)`

**Expected Result:**
- **No** `Warm start (global history):` row anywhere — warm-start is open-universe-only; the pinned path is untouched even though prior history exists
- The pinned run still produced its iteration(s) and reached a terminal state; the prompt-refinement chain renders as before this phase

---

### UT-13 — Garbage `history_scope` does not crash the UI; behaves as default global (error)

**Type:** error
**Priority:** P2
**Surface:** `/` (selected session → Activity feed + AutoRunBar)

**Preconditions:**
- Prior history present (S-1 terminal) AND Shared Setup **S-5** issued (`history_scope:"garbage-value"`)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Open the **"Sessions"** dropdown, select **`Auto: warmstart garbage scope`**
3. Wait until terminal; scroll to the top of the Activity feed

**Expected Result:**
- The session was created and is selectable (no error toast, no failed-to-create state — the garbage value did not cause a 4xx/5xx that breaks the UI)
- The run reached a terminal state in the AutoRunBar (no stuck spinner, no crash)
- Because a garbage value resolves to the safe default (`"global"`), a `Warm start (global history): prioritising …` violet ⚡ row IS present at the top of the feed (same as UT-03/UT-05) — garbage is treated as a clean default, not an error surfaced to the user

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | App loads, Sessions control visible | smoke | P1 | `/` header |
| UT-02 | Headless session auto-appears in dropdown ≤5s, no reload | happy-path | P1 | `/` Sessions dropdown |
| UT-03 | Warm-start citation visible on `global` run (PRIMARY J-15) | happy-path | P1 | `/` Activity feed ⚡ row |
| UT-04 | Citation at top of feed, above accordions, no expand needed | happy-path | P1 | `/` Activity feed ungrouped |
| UT-05 | Omitted `history_scope` also warm-starts (citation present) | happy-path | P2 | `/` Activity feed ⚡ row |
| UT-06 | `this-run` shows NO warm-start citation | validation | P1 | `/` Activity feed (absence) |
| UT-07 | Empty-history run: no note, run still completes | validation | P2 | `/` Activity feed (absence) |
| UT-08 | Note visually identical to SCREEN/PROMOTE; no new component | ux | P2 | `/` `ActivityLogEntry` |
| UT-09 | Distinguish warm-start by exact prefix + top position | ux | P2 | `/` Activity feed |
| UT-10 | AutoRunBar live status + spend still works (J-08/J-13) | regression | P1 | `/` AutoRunBar |
| UT-11 | Prior session history/detail browse unaffected (J-02) | regression | P1 | `/` right panel detail |
| UT-12 | Pinned session shows NO warm-start note | regression | P2 | `/` Activity feed (absence) |
| UT-13 | Garbage `history_scope` doesn't crash UI; behaves as default | error | P2 | `/` Activity feed + AutoRunBar |

**P1 tests (UT-01, UT-02, UT-03, UT-04, UT-06, UT-10, UT-11) must all pass for the browser QA verdict to be PASS.**

- **PRIMARY J-15 acceptance:** UT-03 + UT-04 (citation visible, correctly placed) and UT-06 (opt-out absence).
- **Most likely regression points:** UT-10 (live status/spend), UT-11 (prior-history read-only — iter-0 lesson).
- Screenshots required: UT-03 (`UT-03-run2-warmstart-citation.png`), UT-06 (`UT-06-run3-no-citation.png`), under `reports/qa/goal-auto-money-printer-iter-5-evidence/`.
- API-only assertions (raw `historyScope` persistence, `effectiveHistoryScope` key, before/after content-hash read-only proof, miner call-count==1, SCREEN-order permutation) are covered by the functional/unit test plan (TC-02/04/08/11/12) and are intentionally NOT re-tested here — they are not user-visible UI surfaces.
