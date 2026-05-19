# Phase goal-auto-money-printer-iter-1 — What to Click (Operator Verification Guide)

**Phase:** goal-auto-money-printer-iter-1
**Time required:** ~5 minutes (plus ~1–2 min of unattended waiting for the
headless loop)
**Written by:** ui-test-designer

---

## Prerequisites

- Frontend running at `http://localhost:3691`, backend at
  `http://localhost:8691`.
- Backend env has a working `OPENAI_API_KEY` and outbound network (Binance +
  the LLM). The headless loop does a real generate→backtest→walk-forward→
  insights cycle on a tiny budget.
- A shell to run one `curl`. No login/auth in this app.
- This iteration has **no UI button** to start a headless run — the trigger is
  the API (rewiring a button is deferred to iter-2). That single curl is
  step 1.

---

## Verification Steps

<!-- 9 steps. Priority: 1) the new headless capability works end-to-end,
     2) it survives a reload (durable store), 3) J-02 + manual flow not broken. -->

1. **Start a headless run via the API.** Run:
   ```
   curl -sS -X POST http://localhost:8691/api/auto-sessions \
     -H 'Content-Type: application/json' \
     -d '{"natural_language":"Buy when RSI crosses below 30, sell when it crosses above 70","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-01-15","initial_capital":10000,"model":"gpt-5.4-mini","targets":{"min_wfe":0.0,"min_trades":0,"min_return":-1.0},"budget":{"max_iterations":2}}'
   ```
   - **Expect:** HTTP 200 and a JSON body like
     `{"sessionId":"<uuid>","status":"running"}`. Copy the `sessionId`.

2. Open `http://localhost:3691` in your browser.
   - **Expect:** Header reads "Finovae Strategy Platform" with a "Sessions"
     button top-right; no error page.

3. Click the **"Sessions"** button (clock icon, top-right). Look under the
   **"Live Sessions"** heading for a new row matching the run you just started.
   - **Expect:** A new session row with an **amber pulsing dot** is listed.
   - **If it is not there:** reload the page once (F5) and reopen "Sessions" —
     it must appear after a reload (it is persisted server-side). *Needing the
     reload here is a known weak spot of the "appears with no reload" claim —
     note it, then continue.*

4. Click that headless session row to open it. Look at the strip **directly
   below** the Symbol/Timeframe/Start/End/Capital config bar.
   - **Expect:** A blue strip with a spinning loader reading
     **"Automated run · iteration 1/2"** (or `2/2`).

5. **Do not reload.** Watch for ~30–120 seconds.
   - **Expect:** The iteration number advances (`1/2` → `2/2`), new iteration
     cards appear in the right-hand history list, and new lines appear in the
     left activity log — all **without any manual reload**.

6. Keep waiting until the strip stops spinning.
   - **Expect:** The strip turns **green**: **"Automated run complete · robust
     targets met · X/2 iterations"** (or **"… budget reached · X/2
     iterations"**). **Exactly one** iteration card shows a small amber
     **"★ Best"** pill.

7. Reload the page (F5), open **"Sessions"**, and reselect the same session.
   - **Expect:** The green terminal strip and the **"★ Best"** pill are still
     there — the run state survived a reload (durable file store, not browser
     memory).

8. In the right-hand history list, click a **different / older** iteration card
   than the one currently shown.
   - **Expect:** The RIGHT panel changes — the **"Trade History (N trades)"**
     count and/or first trade row differs from the previous run, the **Equity
     Curve** redraws, and the **"Walk-Forward Analysis"** section updates to
     the selected run (J-02 fix: the right panel re-binds, not just the left).

9. Open **"Sessions"** → click **"+ New Session"**. In the left chat box
   (placeholder **"Describe a trading strategy..."**) type
   `Buy when RSI crosses below 30, sell when it crosses above 70` and press
   **Enter**.
   - **Expect:** A normal manual run completes with metrics + equity curve +
     trades, **and there is NO "Automated run …" strip** below the config bar
     (manual sessions must not show the headless status strip).

---

## What "Working Correctly" Looks Like

- One curl with no browser open creates a session that shows up in the
  "Sessions" list and runs itself to completion.
- The blue "Automated run · iteration X/2" strip advances and turns green
  ("robust targets met" / "budget reached") **without you reloading**.
- Exactly one iteration card carries the amber **"★ Best"** pill, and it (plus
  the green terminal strip) is still there after a hard reload.
- Selecting an older run swaps the **right** panel's trades table + equity
  curve + walk-forward — not just the left conversation panel.
- A brand-new manual session behaves exactly as before and shows **no**
  "Automated run" strip.

## Common Issues

- **Blank page / error screen:** confirm the backend is up —
  `curl http://localhost:8691/api/sessions` should return JSON. (If 8691 is
  unreachable, the Vite proxy path `http://localhost:3691/api/...` is
  equivalent.)
- **Curl returns 4xx/5xx instead of a `sessionId`:** the headless endpoint
  rejected the body (missing pinned field) or the backend lacks
  `OPENAI_API_KEY` / network — fix the env and retry step 1.
- **New session never appears even after a reload:** the endpoint did not
  persist the session to the durable store — a J-07 backend failure, not a
  UI-discovery quirk.
- **Strip stuck on "iteration 1/2" with a spinner forever:** the server loop
  hung or the LLM/Binance call is failing — check backend logs; the loop must
  still reach a terminal state even when an iteration fails.
- **Right panel doesn't change when selecting an older run:** the J-02
  re-bind regressed — the right panel is still pinned to the latest run.
- **"Automated run …" strip appears on the manual session from step 9:** the
  AutoRunBar gating regressed (it must show only for headless `autoRun`
  sessions).
