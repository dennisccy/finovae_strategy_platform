# Phase goal-financial_free-iter-4 — What to Click (Operator Verification Guide)

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering (J-14)
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## Prerequisites

- Backend running at `http://localhost:8000` (`curl -s http://localhost:8000/health` returns ok)
- Frontend running at `http://localhost:3692`
- No login required.
- This iteration adds **no button** — you start the run with one API call, then watch the UI. The UI shows
  the new SCREEN (cheap triage) and PROMOTE (expensive escalation) stages of an open-universe run.

---

## Verification Steps

1. Start one open-universe run by running this command in a terminal:
   ```bash
   curl -s -X POST http://localhost:8000/api/auto-sessions \
     -H "Content-Type: application/json" \
     -d '{"objective":"robust","natural_language":"EMA fast/slow crossover: go long when fast EMA crosses above slow EMA, flat otherwise","model":"claude-haiku-4-5","budget":{"max_iterations":2,"max_configs":3,"max_tokens":400000,"max_usd":5.0}}'
   ```
   - **Expect:** JSON response containing a session id. Copy it.

2. Open `http://localhost:3692/?session=<id>` in your browser (paste the id).
   - **Expect:** The session view loads with a Left **Activity Log** and a Right-panel iteration tree, no blank page or error overlay.

3. While the run is active, watch the status-strip chips (token / USD / configs) near the top for ~15 seconds **without reloading**.
   - **Expect:** At least one of the token / USD / configs values increases on its own. (This is the J-08 live-update check.)

4. In the Left Activity Log, find the entry beginning with `SCREEN —`.
   - **Expect:** A `SCREEN —` header naming the cheap model `gpt-5.4-mini`, "no walk-forward", and a candidate count; below it ≥3 per-candidate `SCREEN —` rows each with a symbol/timeframe and a score.

5. Below the SCREEN entries, find the entry beginning with `PROMOTE —`.
   - **Expect:** A `PROMOTE —` header reading "top-1 of 3" (1 < 3), naming the stronger model `claude-haiku-4-5` and "walk-forward"; exactly one promoted candidate row beneath it.

6. In the Right-panel iteration tree, click the iteration card that has a **walk-forward section** (the promoted one).
   - **Expect:** Its model field shows `claude-haiku-4-5` AND a walk-forward section is present. It is nested as a **child** under the screened candidate it came from.

7. Click a different card — one of the non-promoted (screened-only) candidates.
   - **Expect:** Its model field shows the cheap `gpt-5.4-mini` AND there is **no** walk-forward section.

8. Find the card carrying the **"best"** badge.
   - **Expect:** The best badge is on the promoted, walk-forward-bearing card — never on a cheap screened-only card. (If no candidate was promotable, no best badge appears at all — that is correct, not a bug.)

9. Press F5 to reload the page, then re-check the status and Activity Log.
   - **Expect:** Status, configs-done count, best badge, and the SCREEN/PROMOTE entries all survive the reload unchanged. (This is the J-10 reload-survival check.)

---

## What "Working Correctly" Looks Like

- The Activity Log reads as two clearly separated groups: a cheap `SCREEN —` sweep (gpt-5.4-mini, no WF, ≥3 candidates) followed by a `PROMOTE —` escalation ("top-1 of 3", claude-haiku-4-5, walk-forward).
- The expensive walk-forward + stronger model appear **only** on the single promoted card; screened cards stay cheap with no walk-forward.
- The "best" badge sits on the promoted, walk-forward-bearing node.
- Chips tick up live without reload, and everything survives an F5.

## Common Issues

- **Blank session view despite healthy services:** likely the documented Chrome-MCP hidden-tab render throttle, not an app bug. Verify the same outcome via `GET http://localhost:8000/api/sessions/<id>` — inspect `autoRun` (status, bestIterationId, budget counters) and the activity entries (the SCREEN/PROMOTE text) — and record that the frontend is still serving.
- **No PROMOTE entry / no best badge:** if the run was stopped or budget-exhausted before any promote, this is legitimate — screened nodes remain browsable and no best is marked. Re-run with the generous budget above to see the full SCREEN→PROMOTE flow.
- **No live chip movement:** confirm the run is still active (status "running") — a finished run won't tick further.
