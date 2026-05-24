# Phase goal-financial_free-iter-7 — What to Click (Operator Verification Guide)

**Phase:** goal-financial_free-iter-7 — J-16: overfit-gating leaderboard UI
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## Prerequisites

- Frontend running at `http://localhost:3692`, backend at `http://localhost:8692`
  (if you started the offset stack instead, use `:3691` / `:8691`)
- Populated open-universe session fixture exists at
  `.data/backtests/live/2a829f6e-9762-467e-b32d-d2336724b2df` — this is the session you open below.
  If absent, start a `promote_k: 2` open-universe auto-session over a ≥9-month date range and let it finish first.

---

## Verification Steps

1. Open `http://localhost:3692/?session=2a829f6e-9762-467e-b32d-d2336724b2df`
   - **Expect:** Page loads, no error overlay; the right-hand **Iterations** panel is visible

2. Find the "Candidate leaderboard" card in the Iterations panel (between the status strip and the iteration tree)
   - **Expect:** Trophy-icon header "Candidate leaderboard · ranked by robust score" with an "N candidates" count (N ≥ 2) on the right
   - **Broken looks like:** no card at all, or a card showing "0 candidates"

3. Read the robust score (right-aligned value on each row's top line) from `#1` downward
   - **Expect:** `#1` has the highest score; each row below is ≤ the one above; any "—" score rows sit at the very bottom

4. Locate the violet "BEST" badge
   - **Expect:** Exactly ONE row is highlighted violet with a "BEST" badge + award icon, and that row also has a blue "PROMOTE" badge
   - **Broken looks like:** zero or two-plus BEST rows, or a BEST row tagged "SCREEN"

5. Read the small text line under a NON-best row's metrics
   - **Expect:** A plain-language gating reason — e.g. "WFE 0.21 < 0.30", "over-leveraged (margin called)", "0 trades", "screened — not walk-forward validated", or "lower robust score". Gated-out reasons are red; eligible-but-not-best reasons are gray

6. Check the WFE chips across rows
   - **Expect:** WFE ≥ 0.50 green, ≥ 0.30 amber, < 0.30 red; a SCREEN row shows gray "WFE —" (no colored chip)

7. Confirm one row per family
   - **Expect:** No two rows share the same `SYMBOL TIMEFRAME` label; every row carries a SCREEN or PROMOTE badge

8. Open a manual (non-auto) backtest session via `http://localhost:3692/`
   - **Expect:** NO "Candidate leaderboard" card appears — no empty card, no error

9. Resize the browser to ~375 px wide and click the "Iterations" tab
   - **Expect:** Rows wrap cleanly and stay readable; no horizontal scrollbar or clipped text

---

## What "Working Correctly" Looks Like

- A ranked list of candidates, `#1` on top with the highest robust score, exactly one violet "BEST" row tagged PROMOTE
- Every non-best row explains itself with a short gating reason (red = gated out, gray = eligible but not best)
- A manual session shows no leaderboard card whatsoever

## Common Issues

- **No leaderboard card on an auto-session:** confirm it was an *open-universe* run with ≥2 candidates — pinned-path runs intentionally render no leaderboard
- **Blank page / error screen:** check the backend is up (`curl http://localhost:8692/health`)
- **Headless Chrome shows a blank page:** that is the hidden-tab render throttle, not an app bug — bring the tab to the foreground, or verify the served `leaderboard` / `bestIterationId` via `GET /api/sessions/{id}`
- **"WFE —" on every row:** the run never reached walk-forward — use a ≥9-month date range with `promote_k ≥ 1`
</parameter>
