# Phase goal-financial_free-iter-2 — What to Click (Operator Verification Guide)

**Phase:** goal-financial_free-iter-2
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## Prerequisites

- Frontend running at `http://localhost:3692`
- Backend running and reachable (the shell calls `GET /api/sessions` on load)
- Use a **tiny budget** for the run: short date range (e.g. `2024-01-01` → `2024-01-07`),
  cheapest model, **2 iterations**. This keeps the whole check under ~60 seconds.
- If the browser pixels look blank (headless render-throttle), verify the same steps via
  `GET /api/sessions/{id}` and watch the `autoRun` block instead.

---

## Verification Steps

1. Open `http://localhost:3692` in your browser
   - **Expect:** The two-panel shell loads — Left config/chat panel and Right Iterations panel. No error overlay.

2. In the Left config bar, type a strategy (e.g. `simple SMA crossover`), set the date range to `2024-01-01`→`2024-01-07`, pick the cheapest model, and set the Auto Run count input to `2`. Then click the violet **"Auto Run (2)"** button (lightning-bolt icon) at the right of the config bar.
   - **Expect:** A **new session tab appears in the Session picker and becomes active**. A status strip appears at the top of the Right panel with a blue **"Running"** badge, an animated spinner, and the label **"Optimizing server-side"**.

3. Without reloading, watch the status strip counters for ~10 seconds.
   - **Expect:** The `<n>/2 rounds` counter increments and the `<n>s / 60s` elapsed counter strictly increases on each ~2.5s poll.

4. Keep watching the Iterations panel (do NOT reload).
   - **Expect:** At least one **iteration card appears on its own** with a completed backtest result. Briefly before the first card, a **"Waiting for the first iteration…"** message may show under the strip.

5. While the run is still active, reload the page (press F5), then re-select the same session tab in the Session picker.
   - **Expect:** The Session picker shows the **spinner again with no extra action**, the strip still reads **"Running"**, and the elapsed counter keeps climbing past the reload — proving the run lives on the backend, not the tab.

6. (Optional — only if the run is still going) Click the amber **"Stop (n/2)"** button in the Left config bar.
   - **Expect:** Within one poll the badge turns slate **"Stopped"**, the spinner stops, the reason reads **"Stopped by user"**, no new cards appear, and any **"Best: <id>"** badge stays.

7. Let the run finish (or skip if you stopped it). Look at the status strip.
   - **Expect:** Badge becomes amber **"Budget exhausted"** (or emerald "Criteria met"), spinner stops, label becomes **"Automated session"**, and a violet **"Best: <8-char id>"** badge is shown.

8. Open or create a **manual** session (run a single backtest by typing a prompt and submitting it — not via Auto Run). Look at the top of the Right panel.
   - **Expect:** **No status strip at all** for the manual session, and the single result renders normally.

---

## What "Working Correctly" Looks Like

- Clicking **Auto Run** mints a new session tab and the backend-driven status strip drives itself — counters tick up and cards stream in **without you reloading**.
- After a mid-run reload, the run is **still running on its own** (spinner reappears, counters keep advancing) — it was never tied to the tab.
- **Stop** flips the badge to "Stopped" and freezes the iteration count; the strip is **absent** entirely on manual sessions.

## Common Issues

- **Blank page / error screen:** Confirm the backend is up (the shell needs `GET /api/sessions`); check the browser console for API errors.
- **Strip never appears after Auto Run:** Confirm a new session tab was actually added/selected — the strip only renders for backend auto-sessions (manual sessions have no strip by design).
- **Counters frozen / no new cards:** Headless tabs throttle rendering. Verify via `GET /api/sessions/{id}` that `autoRun.status` advances and `iterationsDone` grows — that confirms the backend loop is running even if pixels are stale.
