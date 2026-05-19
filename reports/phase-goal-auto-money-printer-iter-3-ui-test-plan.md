# Phase goal-auto-money-printer-iter-3 — UI Test Plan

**Phase:** goal-auto-money-printer-iter-3
**Date:** 2026-05-19
**Written by:** ui-test-designer
**Frontend URL:** http://localhost:3691
**Backend URL:** http://localhost:8691

---

## Conventions used by every test below

- The app is a **single-page React workspace** — there is no client-side router.
  Everything lives at `http://localhost:3691`. A "surface" is reached by opening
  the **Sessions** dropdown (top of the page, button labeled **"Sessions"** with
  a clock icon) and clicking a session row; that renders the two-panel session
  view with the `AutoRunBar` strip at the top.
- Open-universe runs have **no UI trigger by design** (per spec). They are
  started with one API call:
  ```
  curl -s -X POST "http://localhost:8691/api/auto-sessions" \
    -H 'Content-Type: application/json' \
    -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'
  ```
  The created session appears in the **Sessions** dropdown under **"Live
  Sessions"** named exactly **`Auto: momentum breakout`** (format:
  `Auto: <first 40 chars of natural_language>`).
- "The `AutoRunBar`" = the thin colored strip directly **below the dark config
  bar and above the two-panel content**. It only renders for server-driven
  auto-sessions (manual sessions have no such strip).
- Exact `AutoRunBar` states (verbatim from `SessionContainer.tsx`):
  - **running/queued** → blue strip (`bg-primary-50`), spinning loader icon,
    text `Automated run · iteration <N>/<M>` (queued adds ` (queued)`).
  - **stopped** → red strip, stop-circle icon, text `Automated run stopped`.
  - **budget-exhausted** → **amber** strip (`bg-amber-50`/amber text),
    dollar-in-circle icon, text
    `Automated run complete · budget reached · <N>/<M> iterations`.
  - **criteria-met** → emerald strip, check-circle icon, text
    `Automated run complete · robust targets met · <N>/<M> iterations`.
  - **spend readout** (new) → right-aligned, dimmed, monospaced-digit span at
    the far right of the strip, format `<tok> tok · $<usd> · <n> cfg`
    (e.g. `12,480 tok · $0.0193 · 3 cfg`; USD always 4 decimals, tokens with
    thousands separators), tooltip on hover:
    `AI tokens / USD / configs spent under the hard budget`. Absent entirely
    when no spend recorded.
- Iteration card config line (verbatim from `IterationCard.tsx`):
  `<symbol> · <timeframe> · <start>–<end> · $<capital>`
  (e.g. `BTCUSDT · 1h · 2024-01-01–2024-02-01 · $10,000`).
- `BestBadge` = small amber pill with a filled star and the text **`Best`**,
  tooltip `Best iteration — selected by the robust walk-forward objective`.

---

## Test Cases

<!-- Test IDs use UT-XX prefix to distinguish from functional test plan TC-XX IDs. -->

---

### UT-01 — Session workspace loads without errors (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** `/` (single-page session workspace)

**Preconditions:**
- Frontend running at `http://localhost:3691`
- Backend running at `http://localhost:8691` (`curl http://localhost:8691/api/health` → 200)

**Steps:**
1. Navigate to `http://localhost:3691`
2. Wait for the page to fully load (≤10 s)
3. Open the browser devtools Console tab (F12 → Console)

**Expected Result:**
- The two-panel workspace renders: a dark config bar at the top, a left
  Activity-log panel, and a right results panel — no blank white screen, no
  red error overlay
- A **"Sessions"** button with a clock icon is visible at the top of the page
- The Console shows **no uncaught errors** (a failed `/api/...` request is
  acceptable only if the backend is intentionally down; for this test it must
  be up)

---

### UT-02 — Open-universe "Auto:" session appears in the list and opens (smoke)

**Type:** smoke
**Priority:** P1
**Surface:** Sessions dropdown (`SessionPicker`) + `AutoRunBar` mount

**Preconditions:**
- UT-01 passed
- `OPENAI_API_KEY` set in the backend environment

**Steps:**
1. In a terminal run:
   ```
   curl -s -w "\nHTTP:%{http_code}\n" -X POST "http://localhost:8691/api/auto-sessions" \
     -H 'Content-Type: application/json' \
     -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'
   ```
2. Confirm the terminal prints `HTTP:200` and a JSON body containing a
   non-empty `sessionId`
3. In the browser at `http://localhost:3691`, click the **"Sessions"** button
   (top of page)
4. In the dropdown, look under the **"Live Sessions"** section header
5. Click the row named **`Auto: momentum breakout`**

**Expected Result:**
- Step 2: `HTTP:200`, body has `"sessionId":"<uuid>"` and
  `"status":"running"` or `"status":"queued"`
- Step 4: a row named exactly **`Auto: momentum breakout`** is present, with a
  small amber pulsing dot to its left and an amber **`running`** label in its
  sub-line (it is actively running)
- Step 5: the dropdown closes, the session opens, and a colored `AutoRunBar`
  strip appears directly below the dark config bar (blue "running" state with a
  spinning icon, text begins `Automated run · iteration`)

---

### UT-03 — Headless open-universe explores ≥2 distinct configs, robust Best marked (happy path · J-12)

**Type:** happy-path
**Priority:** P1
**Surface:** Iteration tree / `IterationCard` / `BestBadge`

**Preconditions:**
- The `Auto: momentum breakout` session from UT-02 exists and is open

**Steps:**
1. With `Auto: momentum breakout` open, watch the **left Activity-log /
   iteration list** for ≤180 s (do **not** reload the page — it live-polls)
2. As iteration cards appear, read each card's config line
   (`<symbol> · <timeframe> · <start>–<end> · $<capital>`)
3. Record the symbol/timeframe of each iteration card
4. Wait until no card shows status **`Generating`** or **`Executing`** (all
   show **`Complete`** or the `AutoRunBar` reached a terminal state)
5. Scan all iteration cards for the amber **`Best`** badge (filled star)

**Expected Result:**
- **At least 2** iteration cards appear, and at least two of them have a
  **different symbol and/or different timeframe** in the config line (e.g. one
  `BTCUSDT · 1h · …`, another `ETHUSDT · 4h · …`) — not the same config twice
- The run reaches a terminal state **without a manual reload** (the
  `AutoRunBar` leaves the blue "running" state on its own)
- **Exactly one** iteration card shows the amber **`Best`** badge; hovering it
  shows the tooltip `Best iteration — selected by the robust walk-forward
  objective`

---

### UT-04 — Live recorded spend readout in AutoRunBar (happy path · J-13)

**Type:** happy-path
**Priority:** P1
**Surface:** `AutoRunBar` → spend `<span>` (right-aligned, dimmed)

**Preconditions:**
- An open-universe session is **actively running** (start a fresh one as in
  UT-02 step 1 if the previous one already finished; open it immediately)

**Steps:**
1. Open the running `Auto: momentum breakout` session
2. Look at the **far right end** of the `AutoRunBar` strip
3. Note the displayed text (format `<tok> tok · $<usd> · <n> cfg`)
4. Wait ~6 s (two ~2.5 s poll cycles) without reloading the page
5. Re-read the right-end text
6. Hover the mouse over the right-end spend text and read the tooltip

**Expected Result:**
- Step 2–3: a right-aligned dimmed span shows e.g. `1,240 tok · $0.0021 · 1 cfg`
  — the USD value has exactly 4 decimals, the token count is comma-grouped, and
  there is **no** `NaN`, `$undefined`, or `undefined tok`
- Step 5: the **token count and/or `cfg` count has increased** (or the run
  reached terminal and the value froze at its final figure) — the readout is
  live, not stuck at 0
- Step 6: the tooltip reads exactly
  `AI tokens / USD / configs spent under the hard budget`

---

### UT-05 — Budget-exhausted run is amber and visually distinct (happy path · J-13)

**Type:** happy-path
**Priority:** P1
**Surface:** `AutoRunBar` → `budget-exhausted` terminal branch

**Preconditions:**
- Backend running with `OPENAI_API_KEY` set

**Steps:**
1. In a terminal run (tiny token/USD budget to force exhaustion):
   ```
   curl -s -w "\nHTTP:%{http_code}\n" -X POST "http://localhost:8691/api/auto-sessions" \
     -H 'Content-Type: application/json' \
     -d '{"natural_language":"budget probe","objective":"robust","budget":{"max_ai_tokens":1,"max_usd":0.0001,"max_configs":2,"max_iterations":2}}'
   ```
2. Confirm `HTTP:200` in the terminal
3. In the browser, open the **Sessions** dropdown and click the row
   **`Auto: budget probe`**
4. Wait (no reload) until the `AutoRunBar` leaves the blue "running" state
5. Read the `AutoRunBar` strip color, icon, and text
6. Count the iteration cards in the left panel and note whether any new card
   appears after the bar turns terminal

**Expected Result:**
- Step 5: the `AutoRunBar` strip is **amber** (pale amber background, amber
  text), shows a **dollar-sign-in-a-circle** icon (not a green check, not a
  red stop), and the text reads exactly
  `Automated run complete · budget reached · <N>/<M> iterations`
- This is clearly different from the emerald `… · robust targets met · …`
  finish and the red `Automated run stopped`
- Step 6: **no new iteration card is added** after the bar turns amber (the run
  did not take "one more round" past the cap)
- The right-end spend readout shows a final non-zero `… tok · $… · … cfg`
  figure ≤ the requested caps (no `NaN`/`undefined`)

---

### UT-06 — Spend + budget-exhausted state survive a browser reload (regression/durability · J-13)

**Type:** regression
**Priority:** P1
**Surface:** `AutoRunBar` persistence after reload

**Preconditions:**
- The terminal `Auto: budget probe` session from UT-05 (already
  `budget-exhausted`)

**Steps:**
1. With `Auto: budget probe` open and showing the amber budget-reached state,
   note the exact spend text at the right of the `AutoRunBar`
2. Hard-reload the browser (press **F5** / **Ctrl-R**)
3. After reload, click **"Sessions"** and re-open the **`Auto: budget probe`**
   row
4. Re-read the `AutoRunBar` strip and its right-end spend text

**Expected Result:**
- After reload the `AutoRunBar` is **still amber** with the dollar-circle icon
  and the text `Automated run complete · budget reached · <N>/<M> iterations`
- The right-end spend text is **byte-identical** to what was noted in step 1
  (tokens / USD / cfg unchanged — the value came from the durable store, not
  browser memory)
- No `NaN`/`$undefined`; the bar did **not** revert to a blue "running" state
  or a generic green finish

---

### UT-07 — Legacy / manual session renders gracefully with no spend artifacts (regression)

**Type:** regression
**Priority:** P2
**Surface:** `AutoRunBar` absent-spend path / manual session (no `autoRun`)

**Preconditions:**
- Frontend + backend running

**Steps:**
1. Click the **"Sessions"** button → click **"+ New Session"** at the top of
   the dropdown
2. Observe the new (manual) session view from the dark config bar downward
3. Open the browser Console (F12) and scan visible text for `NaN`,
   `undefined`, or `$undefined`
4. If any **non-`Auto:`** session (a pre-iter-3 / manual session) already
   exists in the Sessions list, open it and inspect the area below the config
   bar as well

**Expected Result:**
- For the fresh manual session: there is **no `AutoRunBar` strip at all**
  (no blue/amber/green/red strip below the config bar) — manual sessions never
  render it
- Nowhere on screen does the text `NaN`, `undefined`, `$undefined`, or
  `undefined tok` appear
- Step 4 (if applicable): a pre-iter-3 auto-session shows the `AutoRunBar` in
  its normal state **without** the right-aligned spend span — the bar looks
  exactly as it did before this iteration (additive-only, no regression)

---

### UT-08 — Running open-universe session is not a stale terminal after rapid switching (regression · J-08)

**Type:** regression
**Priority:** P1
**Surface:** Session list `SessionDot` + `AutoRunBar` mount-status re-derivation

**Preconditions:**
- A freshly started, **still-running** open-universe session (use a larger
  budget so it stays running long enough):
  ```
  curl -s -X POST "http://localhost:8691/api/auto-sessions" \
    -H 'Content-Type: application/json' \
    -d '{"natural_language":"switch probe","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'
  ```
- At least one **other** session exists in the Sessions list (create one via
  "+ New Session" if needed)

**Steps:**
1. Open `Auto: switch probe` while it is still running; confirm the
   `AutoRunBar` is blue and reads `Automated run · iteration <N>/<M>`
2. Click **"Sessions"**, select the other session, wait ~2 s
3. Click **"Sessions"** again, re-select **`Auto: switch probe`**
4. Repeat steps 2–3 twice more (rapid back-and-forth), each time waiting ~2 s
5. After the last switch back, wait one poll cycle (~3 s) and read the
   `AutoRunBar` state, then open the **"Sessions"** dropdown and read the
   `Auto: switch probe` row's dot/label

**Expected Result:**
- After every switch back, the `AutoRunBar` shows the **blue "running"** state
  (spinning icon, `Automated run · iteration <N>/<M>`) — **never** a stale
  amber `budget reached`, green `complete`, or red `stopped` while the run is
  in fact still running
- In the Sessions dropdown the `Auto: switch probe` row shows the **amber
  pulsing dot** and the amber **`running`** sub-label — i.e. the list spinner
  and the bar **agree**
- The iteration count in the bar continues to advance without any manual
  reload (the live poll self-heals)

---

### UT-09 — Selecting a prior iteration re-binds the RIGHT analysis panel (regression · J-02)

**Type:** regression
**Priority:** P1
**Surface:** Right analysis panel (trades table / equity curve / walk-forward)

**Preconditions:**
- A session with **≥2 completed iterations** — reuse the terminal
  `Auto: momentum breakout` session from UT-03 (it has ≥2 distinct completed
  configs)

**Steps:**
1. Open `Auto: momentum breakout` (terminal, ≥2 completed iterations)
2. Note the equity curve and trades currently shown in the **right** panel
3. In the left iteration list, click a **prior, non-selected** completed
   iteration card (one that is not the latest/highlighted one)
4. Observe the **right** panel: equity curve, the trades table, and the
   walk-forward view
5. Click a different prior iteration card and observe the right panel again

**Expected Result:**
- After step 3 the **right** panel re-binds to the clicked run: the equity
  curve redraws, the trades table reloads with that run's trades, and the
  walk-forward section updates — not only the left-side summary
- After step 5 the right panel changes **again** to the second clicked run's
  data (each selection re-binds the full right panel, not just the header)
- No console error; the right panel never goes blank or keeps showing the
  previous run's trades after a different card is selected

---

### UT-10 — Invalid open-universe requests create no session in the UI (validation / error)

**Type:** validation
**Priority:** P2
**Surface:** Sessions list (negative — no entry added) + `POST /api/auto-sessions`

**Preconditions:**
- Backend running; note the current number of `Auto: …` rows in the Sessions
  dropdown before starting (deep API-only assertions live in the functional
  test plan TC-04/05/06 — this case only verifies the UI-visible outcome)

**Steps:**
1. Open the **"Sessions"** dropdown, count and remember the existing
   `Auto: …` rows under "Live Sessions", then close the dropdown
2. Run each of these and note the printed HTTP code:
   - a) Unsupported objective:
     ```
     curl -s -w "\nHTTP:%{http_code}\n" -X POST "http://localhost:8691/api/auto-sessions" \
       -H 'Content-Type: application/json' \
       -d '{"natural_language":"x","objective":"sharpe","budget":{"max_iterations":1}}'
     ```
   - b) Half-specified (timeframe but no symbol):
     ```
     curl -s -w "\nHTTP:%{http_code}\n" -X POST "http://localhost:8691/api/auto-sessions" \
       -H 'Content-Type: application/json' \
       -d '{"natural_language":"x","timeframe":"1h","budget":{"max_iterations":1}}'
     ```
   - c) Malformed budget:
     ```
     curl -s -w "\nHTTP:%{http_code}\n" -X POST "http://localhost:8691/api/auto-sessions" \
       -H 'Content-Type: application/json' \
       -d '{"natural_language":"x","objective":"robust","budget":{"max_ai_tokens":"lots"}}'
     ```
3. In the browser, click **"Sessions"** again and re-count the `Auto: …` rows

**Expected Result:**
- Each of (a), (b), (c) prints `HTTP:422` (never `HTTP:500`, never `HTTP:200`)
  and a JSON body with a readable `detail` message (e.g. naming the unsupported
  objective or the missing field)
- Step 3: the number of `Auto: …` rows in the Sessions dropdown is **unchanged**
  from step 1 — no broken/blank/"Auto: x" session was added for any rejected
  request

---

### UT-11 — Open-universe results are discoverable & spend states are legible (UX)

**Type:** ux
**Priority:** P3
**Surface:** Overall UX — discoverability + readability of new pixels

**Preconditions:**
- The terminal `Auto: momentum breakout` (UT-03) and `Auto: budget probe`
  (UT-05) sessions exist

**Steps:**
1. Starting from `http://localhost:3691` with no session preselected, click
   **"Sessions"** and confirm the open-universe runs are reachable in **≤2
   clicks** (open dropdown → click the `Auto: …` row)
2. Confirm there is **no** new button, menu item, form, leaderboard, or
   "open-universe" / "new search" control anywhere in the UI (open-universe is
   API-only by design)
3. Open `Auto: momentum breakout`; visually compare the right-aligned spend
   readout against the rest of the `AutoRunBar` text
4. Open `Auto: budget probe`; compare its amber strip against a green
   `criteria-met` finish (UT-03's bar, if it ended green) and the blue
   "running" state

**Expected Result:**
- The headless run's iterations, robust `Best` badge, and spend are all
  visible through the **existing** iteration tree + `AutoRunBar` with no new
  page/panel/route — a user finds the results within 2 clicks
- There is intentionally **no** new UI affordance to *start* an open-universe
  run (this is expected, not a defect)
- The spend readout is right-aligned, dimmed (lower contrast than the status
  text), and uses fixed-width digits — it reads as a secondary metric, not
  noise; no overlap/clipping with the status text
- The amber `budget reached` strip is **immediately distinguishable** at a
  glance from the emerald `robust targets met` strip and the blue "running"
  strip (distinct color + distinct icon)

---

## Test Summary

| ID | Name | Type | Priority | Surface |
|----|------|------|----------|---------|
| UT-01 | Session workspace loads | smoke | P1 | `/` |
| UT-02 | "Auto:" session listed & opens | smoke | P1 | Sessions dropdown + `AutoRunBar` mount |
| UT-03 | ≥2 distinct configs + robust Best (J-12) | happy-path | P1 | Iteration tree / `IterationCard` / `BestBadge` |
| UT-04 | Live spend readout (J-13) | happy-path | P1 | `AutoRunBar` spend span |
| UT-05 | Budget-exhausted amber state (J-13) | happy-path | P1 | `AutoRunBar` budget-exhausted branch |
| UT-06 | Spend + amber survive reload (J-13) | regression | P1 | `AutoRunBar` reload durability |
| UT-07 | Legacy/manual graceful, no NaN | regression | P2 | `AutoRunBar` absent-spend path |
| UT-08 | No stale terminal on rapid switch (J-08) | regression | P1 | Session list dot + `AutoRunBar` mount |
| UT-09 | Prior-run RIGHT panel re-bind (J-02) | regression | P1 | Right analysis panel |
| UT-10 | Invalid requests add no session | validation | P2 | Sessions list (negative) + API gate |
| UT-11 | Discoverable & legible spend states | ux | P3 | Overall UX |

**P1 tests (UT-01 — UT-06, UT-08, UT-09) must all pass for the browser QA
verdict to be PASS.** P1 here includes the two required-still-passing
regression journeys J-08 (UT-08) and J-02 (UT-09), which the spec explicitly
flags as high-risk and must not regress.
