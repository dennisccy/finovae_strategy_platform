# Phase goal-auto-money-printer-iter-2 — What to Click (Operator Verification Guide)

**Phase:** goal-auto-money-printer-iter-2
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## Prerequisites

- Frontend running at `http://localhost:3691`
- Backend running with `OPENAI_API_KEY` set (auto-run generates strategies via the LLM)
- No login required. A "Session 1" exists by default on first load.

---

## Verification Steps

1. Open `http://localhost:3691` in your browser.
   - **Expect:** App loads — header "Finovae Strategy Platform", a "Sessions" button top-right, a config bar (Symbol / Timeframe / Start / End / Capital), a left "Describe a trading strategy..." box, and a right panel saying "No Iterations Yet". No error screen.

2. In the config bar set Symbol `BTC/USDT`, Timeframe `1 Hour`, Start `2024-01-01`, End `2024-02-01`, Capital `10000`. In the left box type `Buy when RSI crosses below 30, sell when it crosses above 70` and press **Enter** (or click the blue paper-plane Send button).
   - **Expect:** An iteration card appears in the right panel and runs to **"Complete"** (≤ ~90 s) with metrics. Shortly after, suggestion chips appear in the left Activity panel. A violet **"Auto Run (1)"** button now appears at the far right of the config bar.

3. Set the small number box right of the Auto Run button to `2`, then click the violet **"Auto Run (2)"** button.
   - **Expect:** A new entry appears at the bottom of the left Activity panel reading exactly: *"Started a server-driven Auto Run (up to 2 iterations). It runs on the backend and continues even if you close or reload this tab — a new "Auto: …" session appears in the session list shortly."* No new iteration cards are added to **this** session.

4. Click the **Sessions** button (top-right); within ~5 seconds a new **"Auto: …"** row appears with a pulsing amber dot and a `running` badge. Click that row.
   - **Expect:** That session opens and a slim strip directly below the config bar shows a spinner and **"Automated run · iteration X/2"**, with X advancing on its own (no manual reload).

5. While it still reads **"Automated run · iteration X/2"**, hard-reload the page (Ctrl+Shift+R). Then click **Sessions** and re-open the same **"Auto: …"** session.
   - **Expect:** The strip still shows the run; iteration count is the **same or higher** than before the reload and keeps advancing — the run survived the reload (it is server-driven). It ends green: **"Automated run complete · budget reached · 2/2 iterations"**, and one iteration card in the right panel shows an amber **"Best"** star pill.

6. Set the number box to `8`, click **"Auto Run (8)"**, open the new **"Auto: …"** session, and once the strip shows **"Automated run · iteration X/8"** with ≥1 completed card, click the amber **"Stop (x/8)"** button at the far right of the config bar.
   - **Expect:** Within a few seconds the strip turns red and reads **"Automated run stopped"**. No new iteration cards are added after the click. Exactly one card keeps the amber **"Best"** star pill.

7. (Regression check) Open a session with ≥2 completed iteration cards. In the right panel click an **older** completed card.
   - **Expect:** The right pane re-binds to that older run — its own equity curve, trades table, and walk-forward — not the previously shown run's data.

---

## What "Working Correctly" Looks Like

- Clicking "Auto Run" creates a **separate** `Auto: …` session in the Sessions dropdown; the originating session only gets the one info log entry (it does **not** start iterating locally).
- The `Auto: …` session's status strip advances running → terminal **on its own**, survives a full page reload, and the iteration count never goes backwards.
- The amber **"Stop (x/N)"** button stops the run within seconds (red "Automated run stopped"); no iterations appear after the stop and the **"Best"** star pill stays on exactly one card.
- A still-running session always shows "running" — in the dropdown (pulsing amber dot + `running` badge) and in its status strip — even after rapidly switching sessions.

## Common Issues

- **Blank page / error screen:** confirm the backend is up — `curl http://localhost:8000/health` (or the port from `./scripts/dev.sh`).
- **No "Auto Run" button:** the session has no completed iteration with suggestions yet. Run step 2 and wait until suggestion chips appear in the left panel.
- **No "Auto: …" session after clicking Auto Run:** wait ~5 s (discovery poll) or close/reopen the Sessions dropdown; if an error entry "Auto Run failed to start: …" shows instead, the backend rejected the request — check it is running.
- **Status strip never appears:** the AutoRunBar shows only for server-driven `Auto: …` sessions — make sure you opened the new `Auto: …` row, not the originating session.
- **Strip stuck on a terminal state while still running:** that is the J-08 regression this phase fixes — re-open the session from the Sessions dropdown; if it persists, FAIL.
