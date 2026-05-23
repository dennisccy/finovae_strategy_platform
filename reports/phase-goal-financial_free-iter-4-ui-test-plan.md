# Phase goal-financial_free-iter-4 — UI Test Plan

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering for the open-universe search (J-14)
**Date:** 2026-05-23
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3692

---

## Context for the operator

This iteration changed **no frontend code**. The UI surfaces below already exist; what changes is the
*content* they display because the backend now emits two new stages — **SCREEN** (cheap triage) and
**PROMOTE** (expensive escalation) — during an open-universe automated run.

There is **no new button or control**. An open-universe run is started the same way as before, by issuing
an API request with **no** `symbol`/`timeframe`. The setup step (UT-00) does this once; all other tests
observe the resulting UI.

**Standard run setup (shared precondition for most tests below).** Start one open-universe run and keep its
session open:

```bash
curl -s -X POST http://localhost:8000/api/auto-sessions \
  -H "Content-Type: application/json" \
  -d '{
        "objective": "robust",
        "natural_language": "EMA fast/slow crossover: go long when the fast EMA crosses above the slow EMA, flat otherwise",
        "model": "claude-haiku-4-5",
        "budget": { "max_iterations": 2, "max_configs": 3, "max_tokens": 400000, "max_usd": 5.0 }
      }'
```

The response contains a session id. Open the session in the UI at
`http://localhost:3692/?session=<id>` (or click the session from the session list on `http://localhost:3692/`).
`model: "claude-haiku-4-5"` is intentionally **not** the cheapest model — that is what makes "stronger model
only on promoted" observable against the cheap `gpt-5.4-mini` used for SCREEN.

---

## Test Cases

<!-- UT-XX IDs distinguish these UI tests from the functional plan's TC-XX IDs. -->

---

### UT-00 — Trigger an open-universe run (setup / smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (session view)

**Preconditions:**
- Backend running at http://localhost:8000 (`curl -s http://localhost:8000/health` returns ok)
- Frontend running at http://localhost:3692

**Steps:**
1. Run the **Standard run setup** curl command above; note the returned session id.
2. Navigate to `http://localhost:3692/` and click the session whose id matches (or open `http://localhost:3692/?session=<id>` directly).
3. Wait for the session view to load.

**Expected Result:**
- The session view renders with no blank screen and no error overlay.
- A Left **Activity Log** panel and a Right-panel iteration tree are both visible.
- A status strip showing token / USD / configs chips is visible near the top of the session view.

---

### UT-01 — Session view loads without errors (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (session view)

**Preconditions:**
- A session from UT-00 is open at `http://localhost:3692/?session=<id>`.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. Open the browser DevTools console (F12 → Console).
3. Wait for the page to fully load.

**Expected Result:**
- The session view renders with the Activity Log (left) and iteration tree (right) both visible.
- No red error overlay, no blank page.
- No uncaught console errors are logged on load.

---

### UT-02 — Activity Log shows the SCREEN stage (happy path, part 1)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (session view) — Left Activity Log

**Preconditions:**
- A run from UT-00 has started and is progressing (or has completed).

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. In the Left **Activity Log**, locate the entry whose text begins with `SCREEN —`.
3. Read the `SCREEN —` header entry and the per-candidate `SCREEN —` rows beneath it.

**Expected Result:**
- A `SCREEN —` **header** entry is present that names the cheap model `gpt-5.4-mini`, mentions "no walk-forward", and states a candidate count (e.g. "3 candidates").
- At least **3** per-candidate `SCREEN —` rows appear, each naming a candidate's symbol/timeframe and a numeric robust score.
- SCREEN entries render as `auto-run`-style rows (Zap icon, violet text), not as raw JSON or an error string.

---

### UT-03 — Activity Log shows the PROMOTE stage with top-k of N (happy path, part 2)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (session view) — Left Activity Log

**Preconditions:**
- The run from UT-00 has progressed past SCREEN into PROMOTE (a promoted candidate was produced).

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. In the Left **Activity Log**, locate the entry whose text begins with `PROMOTE —`, below the SCREEN entries.
3. Read the `PROMOTE —` header and any per-candidate `PROMOTE —` row.

**Expected Result:**
- A `PROMOTE —` **header** entry is present reading "top-1 of 3" (k < N, i.e. 1 < 3), naming the stronger model `claude-haiku-4-5`, and mentioning "walk-forward".
- Exactly **one** `PROMOTE —` per-candidate row appears (DEFAULT_PROMOTE_K = 1), naming the promoted candidate's symbol/timeframe.
- The PROMOTE entries appear **after** the SCREEN entries in the log ordering.

---

### UT-04 — SCREEN and PROMOTE stages are visually distinguishable (ux)

**Type:** ux
**Priority:** P2
**Surface:** `/` (session view) — Left Activity Log

**Preconditions:**
- A completed (or in-progress) run from UT-00 with both SCREEN and PROMOTE entries.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. Visually scan the Left Activity Log for the `SCREEN —` group and the `PROMOTE —` group.

**Expected Result:**
- The `SCREEN —`-prefixed entries and the `PROMOTE —`-prefixed entries are both present and clearly separable by their text prefix.
- The two stages read as two distinct groups (SCREEN group above, PROMOTE group below), not interleaved or merged into one ambiguous block.
- An operator who has never seen this UI can tell which entries are the cheap triage and which are the escalation from the text alone.

---

### UT-05 — Promoted node nests as a child of its screened parent (happy path — lineage)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (session view) — Right-panel iteration tree

**Preconditions:**
- The run from UT-00 produced a promoted candidate.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. In the Right-panel **iteration tree**, locate the promoted iteration card (the one with a walk-forward section — see UT-06).
3. Inspect its position in the tree relative to the screened candidate it came from.

**Expected Result:**
- The promoted iteration card is rendered **nested as a child** of the screened candidate it was promoted from (indented / connected under its parent), not as a sibling or top-level node.
- The screened candidate that was promoted is the visible parent of that promoted node.

---

### UT-06 — Promoted card shows stronger model + walk-forward section (happy path — card data)

**Type:** happy-path
**Priority:** P1
**Surface:** `/` (session view) — Iteration card (promoted)

**Preconditions:**
- The run from UT-00 produced a promoted candidate.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. In the Right-panel iteration tree, click the promoted iteration card to open/expand it.
3. Read the model name field and look for a walk-forward section.

**Expected Result:**
- The card's `modelUsed` field shows the stronger model `claude-haiku-4-5`.
- A **walk-forward** section is present on the card, showing a walk-forward (WFE) result.

---

### UT-07 — Screened-only card shows cheap model + no walk-forward section (validation — card data)

**Type:** validation
**Priority:** P2
**Surface:** `/` (session view) — Iteration card (screened-only)

**Preconditions:**
- The run from UT-00 screened ≥3 candidates; at least 2 were NOT promoted.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. In the Right-panel iteration tree, click a screened-only card (one of the non-promoted candidates, i.e. NOT the one opened in UT-06) to open/expand it.
3. Read the model name field and look for a walk-forward section.

**Expected Result:**
- The card's `modelUsed` field shows the cheap model `gpt-5.4-mini`.
- There is **no** walk-forward section on the card.

---

### UT-08 — "Best" badge is on a promoted, walk-forward-bearing node only (validation)

**Type:** validation
**Priority:** P1
**Surface:** `/` (session view) — "Best" badge / `bestIterationId` marker

**Preconditions:**
- The run from UT-00 completed with at least one eligible promoted candidate.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. In the Right-panel iteration tree, locate the iteration card carrying the "best" badge.
3. Open that card and confirm it has a walk-forward section (it is a promoted node).
4. Identify the highest raw-return screened-only card and confirm it does NOT carry the best badge.

**Expected Result:**
- The card carrying the "best" badge is a **promoted** node that has a walk-forward section and `modelUsed = claude-haiku-4-5`.
- No screened-only card (cheap model, no WF) carries the best badge — even if its raw return looks higher.
- (Edge case — not a failure) If no promoted candidate was eligible, **no** best badge appears anywhere; all screened nodes remain browsable. This is a correct gated outcome, not an error.

---

### UT-09 — Status-strip token/USD/configs chips update live without reload (regression — J-08)

**Type:** regression
**Priority:** P1
**Surface:** `/` (session view) — Status strip chips

**Preconditions:**
- Start a **fresh** open-universe run (repeat the Standard run setup) and open its session immediately, while it is still active.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>` while the run is active.
2. Note the current values of the token, USD, and configs chips in the status strip.
3. Wait ~10–20 seconds **without** reloading the page.
4. Re-read the same three chips.

**Expected Result:**
- At least one of the token / USD / configs chip values **increases** during the wait without any page reload.
- The increase happens via the UI's own polling — the operator did not press F5 or navigate.

---

### UT-10 — Run state survives a browser reload mid-run (regression — J-10)

**Type:** regression
**Priority:** P1
**Surface:** `/` (session view) — `autoRun` status + chips

**Preconditions:**
- An open-universe run is active or recently completed and its session is open.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>` with an active/just-finished run.
2. Note the current `autoRun` status text (e.g. "running" / "completed" / "stopped"), the configs-done chip value, and whether a best badge is shown.
3. Press F5 (or Cmd+R) to reload the page.
4. Wait for the session view to reload, then re-read status, configs-done chip, and best badge.

**Expected Result:**
- After reload, the `autoRun` status, configs-done count, and best-badge state match what was shown before reload (no reset to empty, no loss of progress).
- The Activity Log SCREEN/PROMOTE entries are still present after reload.

---

### UT-11 — Distinct configs still appear as iteration cards (regression — J-12)

**Type:** regression
**Priority:** P1
**Surface:** `/` (session view) — Right-panel iteration tree

**Preconditions:**
- A completed run from UT-00.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. In the Right-panel iteration tree, count the iteration cards and read each card's symbol/timeframe.

**Expected Result:**
- At least **2** iteration cards with **differing** symbol/timeframe are present (most as cheap/no-WF screened nodes, at least one promoted).
- The run reached a terminal state (status is "completed", "stopped", or "budget-exhausted") — it did not loop unbounded.

---

### UT-12 — No API key or secret appears in any Activity Log entry (validation — security)

**Type:** validation
**Priority:** P1
**Surface:** `/` (session view) — Left Activity Log

**Preconditions:**
- A completed run from UT-00 with SCREEN and PROMOTE entries.

**Steps:**
1. Navigate to `http://localhost:3692/?session=<id>`.
2. Read through every SCREEN and PROMOTE Activity Log entry's visible text.

**Expected Result:**
- No entry contains an API key, bearer token, `sk-`-style secret, or any credential-looking string.
- Entries name only model identifiers (`gpt-5.4-mini`, `claude-haiku-4-5`), symbols/timeframes, scores, and stage labels.

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-00 | Trigger open-universe run (setup) | smoke | P1 | `/` session view |
| UT-01 | Session view loads without errors | smoke | P1 | `/` session view |
| UT-02 | SCREEN stage shown in Activity Log | happy-path | P1 | Left Activity Log |
| UT-03 | PROMOTE stage top-k of N shown | happy-path | P1 | Left Activity Log |
| UT-04 | SCREEN vs PROMOTE distinguishable | ux | P2 | Left Activity Log |
| UT-05 | Promoted node nests under screened parent | happy-path | P1 | Iteration tree |
| UT-06 | Promoted card: stronger model + WF | happy-path | P1 | Iteration card |
| UT-07 | Screened card: cheap model, no WF | validation | P2 | Iteration card |
| UT-08 | Best badge on promoted WFE node only | validation | P1 | Best badge |
| UT-09 | Chips update live without reload (J-08) | regression | P1 | Status strip |
| UT-10 | Run state survives reload (J-10) | regression | P1 | `autoRun` status |
| UT-11 | Distinct configs as cards (J-12) | regression | P1 | Iteration tree |
| UT-12 | No secrets in Activity Log | validation | P1 | Left Activity Log |

**P1 tests must all pass for browser QA verdict to be PASS.**

**Throttle fallback (per phase TESTING REQUIREMENTS):** If pixels render blank despite a healthy frontend
(documented Chrome-MCP hidden-tab throttle), verify the same outcomes via the backend endpoint the UI polls —
`GET http://localhost:8000/api/sessions/<id>` → inspect `autoRun` (status, bestIterationId, budget counters)
and the activity entries (SCREEN/PROMOTE text) — and record the live-frontend health-check alongside.
"Services down / could not run" is NOT an acceptable result this iteration.
