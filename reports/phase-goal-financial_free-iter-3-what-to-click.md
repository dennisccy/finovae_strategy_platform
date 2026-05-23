# Phase goal-financial_free-iter-3 — What to Click (Operator Verification Guide)

**Phase:** goal-financial_free-iter-3
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## Prerequisites

- Frontend running at `http://localhost:3692`; backend running at `http://localhost:8000`
- A terminal (the open-universe search has **no in-UI start control** this iteration — you launch it once via `curl`, then watch it in the UI)
- Keep the browser tab **foregrounded** — a hidden tab throttles rendering and the counters may appear frozen

---

## Verification Steps

<!-- Maximum 10 steps. The core new feature is the live token/USD/configs counters streaming from a server-side open-universe run. -->

1. In a terminal, launch an open-universe run:
   ```bash
   curl -s -X POST http://localhost:8000/api/auto-sessions \
     -H 'Content-Type: application/json' \
     -d '{"objective":"robust","budget":{"max_configs":2,"max_tokens":50000,"max_usd":0.05,"max_wall_clock_seconds":120}}'
   ```
   - **Expect:** HTTP 200 and a JSON response containing a session id (copy it). It does **not** 400-reject for the missing symbol/timeframe.

2. Open `http://localhost:3692` in your browser and select the session you just created
   - **Expect:** The session opens; a bordered status strip sits at the top of the **Iterations** panel with a blue "Running" badge and a spinning icon.

3. Find the counter group on the right side of the strip (chips separated by `·`)
   - **Expect:** You see four chips: `1/2 configs` (or similar), `… tok`, `$0.0… / $0.0500`, and `…s`. There is **no** "rounds" chip.

4. Watch the `tok` chip and the `$` chip for ~5–10 seconds without refreshing
   - **Expect:** The token spend (e.g. `1.2k / 50k tok`) and the USD spend (e.g. `$0.0123 / $0.0500`) **increase** over the polls and never exceed their caps.

5. Watch the iteration list below the strip (still no manual refresh)
   - **Expect:** At least 2 config cards appear over time, each showing a **different** symbol/timeframe in its params.

6. Press F5 to reload the page mid-run, then re-open the same session
   - **Expect:** The strip and counters come back with the same (or higher) values — the run state is restored from the server, not lost.

7. Wait for the run to finish (configs reach `2/2`, or the cap trips)
   - **Expect:** A violet **"Best: <8-char id>"** badge appears in a second row, and the stop-reason label (e.g. "Budget exhausted" or "Robust targets met") is shown.

8. Regression check — start a **pinned** Auto Run from the in-UI "Auto Run" control (pick a symbol + timeframe), then open that session
   - **Expect:** Its strip shows a `…/… rounds` chip (NOT configs), alongside the `tok`, `$`, and `s` chips — the pinned display still works.

---

## What "Working Correctly" Looks Like

- The status strip shows live, rising `tok` and `$` counters during an open-universe run, each capped at the budget you set.
- Open-universe runs show a `configs` chip; pinned runs show a `rounds` chip — the strip picks the right one automatically.
- A single violet "Best:" badge lands when the run goes terminal, and config cards stream in without manual refresh.

## Common Issues

- **Counters look frozen / page looks blank:** the tab is probably backgrounded — bring it to the foreground (hidden-tab render throttle). Confirm the real values via `curl -s http://localhost:8000/api/sessions/<id>` → `autoRun.budget`.
- **`curl` in step 1 returns 400/422:** check the body is valid JSON and `objective` is `"robust"`; `422` means a budget field is missing or ≤ 0.
- **No config cards appear:** the run may have tripped a tiny cap before any config completed — relaunch with a larger `max_tokens` (e.g. `50000`).
- **Backend not responding:** verify it is up (`curl http://localhost:8000/api/sessions`).
