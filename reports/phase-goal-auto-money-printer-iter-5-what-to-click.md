# Phase goal-auto-money-printer-iter-5 — What to Click (Operator Verification Guide)

**Phase:** goal-auto-money-printer-iter-5
**Time required:** ~5 minutes (after the 3 setup runs have finished)
**Written by:** ui-test-designer

---

## Prerequisites

- Frontend running at **http://localhost:3691**
- Backend running at **http://localhost:8691** with `OPENAI_API_KEY` set
- **One-time setup (do this first; not part of the 5 minutes — each run takes ~1–3 min):**
  There is no UI button to start a headless run with a history scope, so create the
  three sessions via the API against the **same** store, in order:

  ```bash
  # 1. Producer (no prior history). WAIT until this one finishes before step 2.
  curl -s -X POST "http://localhost:8691/api/auto-sessions" -H 'Content-Type: application/json' \
    -d '{"natural_language":"warmstart producer run1","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'

  # 2. Global warm-start (learns from run 1).
  curl -s -X POST "http://localhost:8691/api/auto-sessions" -H 'Content-Type: application/json' \
    -d '{"natural_language":"warmstart global run2","objective":"robust","history_scope":"global","budget":{"max_iterations":2,"max_configs":2}}'

  # 3. Opt-out (no cross-run learning).
  curl -s -X POST "http://localhost:8691/api/auto-sessions" -H 'Content-Type: application/json' \
    -d '{"natural_language":"warmstart optout run3","objective":"robust","history_scope":"this-run","budget":{"max_iterations":2,"max_configs":2}}'
  ```
  Wait until all three reach a terminal state (their AutoRunBar turns amber
  "budget reached") before doing the verification steps below.

---

## Verification Steps

1. Open **http://localhost:3691** in your browser
   - **Expect:** Header reads "Finovae Strategy Platform"; a grey **"Sessions"** button is top-right. No error page.

2. Click the **"Sessions"** button in the header
   - **Expect:** A dropdown opens with a **"Live Sessions"** list containing the rows `Auto: warmstart producer run1`, `Auto: warmstart global run2`, and `Auto: warmstart optout run3` (they auto-discovered with no page reload).

3. Click the row **`Auto: warmstart global run2`**
   - **Expect:** The dropdown closes and that session opens. The left half of the screen is its Activity feed. (On a narrow window, click the **"Activity"** tab first.)

4. Scroll to the **very top** of the Activity feed and read the first row
   - **Expect:** A violet row with a small ⚡ icon reading exactly:
     `Warm start (global history): prioritising <SYM> <TF> — prior best robust <S> across <N> prior session`
     e.g. `Warm start (global history): prioritising BTC/USDT 4h — prior best robust 0.78 across 1 prior session`.
     The whole sentence is readable (not cut off), and it sits **above** all the
     collapsible iteration cards (you do **not** need to expand anything to see it).
   - **Broken looks like:** no violet row at the top; the text is truncated with `…`;
     or it shows raw placeholders / `undefined` / a secret-looking string.

5. Open the **"Sessions"** dropdown again and click **`Auto: warmstart optout run3`**
   - **Expect:** That session's Activity feed opens.

6. Press **Ctrl+F** (Cmd+F on Mac) and search the page for `Warm start (global history)`
   - **Expect:** **0 matches.** The opt-out run has **no** warm-start note anywhere.
     (Violet `SCREEN config …` / `PROMOTE config …` rows *inside* the iteration cards
     are normal and are NOT the warm-start note.)
   - **Broken looks like:** a `Warm start (global history): …` row appears on the
     opt-out run — opt-out was not honored.

7. Open the **"Sessions"** dropdown and click the prior **`Auto: warmstart producer run1`**; in the right panel (or the **"Iterations"** tab on a narrow window) click one completed iteration
   - **Expect:** Its metrics, trades, and equity chart load normally — Run #1's
     history is intact and unchanged after the global mining run (read-only).
   - **Broken looks like:** missing/reordered iterations, "failed to load", or an
     empty detail panel.

8. While viewing any auto session, look at the thin status strip directly under the header (the AutoRunBar)
   - **Expect:** It shows a terminal state — amber **"Automated run complete · budget reached · 2/2 iterations"** with a spend readout like `1,234 tok · $0.0042 · 2 cfg` on the right. No `NaN`/`undefined`.

---

## What "Working Correctly" Looks Like

- **`Auto: warmstart global run2`**: a single violet ⚡ row
  `Warm start (global history): prioritising <SYM> <TF> — prior best robust <S> across <N> prior session(s)`
  at the **top** of the Activity feed, fully readable, above the iteration cards.
- **`Auto: warmstart optout run3`**: searching `Warm start (global history)` finds
  **0 matches** — no warm-start note.
- **`Auto: warmstart producer run1`**: its iteration history still opens with
  metrics/trades/equity intact (the new run did not touch it).
- The warm-start note looks exactly like the existing SCREEN/PROMOTE ⚡ rows
  (same icon, same violet style) — no new panel/button/page was added.

## Common Issues

- **No sessions in the dropdown / "running" forever**: backend not running or
  `OPENAI_API_KEY` not set. Check `curl http://localhost:8691/api/health`.
- **No warm-start note on `run2`**: Run #1 must have *finished* (produced a promoted
  best) **before** Run #2 was started, and both must hit the same store. Re-run the
  setup in order.
- **Warm-start note appears on `run3` (opt-out)**: opt-out regression — fail J-15.
- **Note is truncated with `…`**: the feed flattened the citation — fail (the entry
  must render its full text, like the existing auto-run rows).
- **Can't see the note**: it is at the **top** of the feed (the feed auto-scrolls to
  the bottom on a live run) — scroll all the way up.
