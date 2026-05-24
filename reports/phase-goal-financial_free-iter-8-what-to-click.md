# Phase goal-financial_free-iter-8 — What to Click (Operator Verification Guide)

**Phase:** goal-financial_free-iter-8
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## Prerequisites

- Frontend running at `http://localhost:3692`
- Session store contains both a **current-schema** auto-session
  (`j16-leaderboard-proof` is the reference one) and at least one **legacy**
  auto-session (any of the ~70 pre-`budget` records).
- No login required.

---

## Verification Steps

<!-- This iteration is a crash-fix + render-proof. There is nothing to "create".
     The point is: legacy sessions no longer blank the app, current-schema sessions
     still show their status strip, and the leaderboard paints. -->

1. Open DevTools console (F12), clear it, then open `http://localhost:3692/`
   - **Expect:** The backtest workspace loads — NOT a blank white screen. No
     uncaught console error mentioning `iterationsDone`.

2. Select the **current-schema** session `j16-leaderboard-proof` from the session
   selector.
   - **Expect:** The right "Iterations" panel opens and a budget / spend /
     iteration-progress **status strip** appears at the top of it.

3. Scroll to the candidate leaderboard inside the "Iterations" panel.
   - **Expect:** ≥2 ranked candidate rows; exactly one row highlighted as **BEST**
     with a violet badge/tint.

4. Look at the WFE chip on each leaderboard row.
   - **Expect:** Color-graded chips — emerald (WFE ≥0.5), amber (0.3–0.5), red
     (<0.3); a screen-stage row shows `—` instead.

5. Find the non-best candidate that still has a strong score.
   - **Expect:** It shows a visible **gating reason** text (e.g. a WFE-failing
     rejection) and is NOT highlighted as BEST.

6. Now switch to a **legacy** auto-session (any session other than
   `j16-leaderboard-proof`).
   - **Expect:** The app does NOT blank. The session opens — iteration tree and
     charts render. The status strip is **absent** (correct: no budget data).

7. Switch back to `j16-leaderboard-proof`.
   - **Expect:** The status strip reappears; the app never blanked during the switch.

---

## What "Working Correctly" Looks Like

- Legacy sessions open to a normal workspace (tree + charts), just without the
  budget status strip — and the app never goes blank-white.
- Current-schema sessions still show the budget/spend/iteration status strip exactly
  as in iter-7.
- The leaderboard paints real rows: a violet BEST row, color-graded WFE chips, and a
  gating reason on a rejected high-scorer.

## Common Issues

- **Blank white screen when selecting a legacy session:** the crash fix has
  regressed — this is the exact bug this iteration fixed. Check the console for
  `Cannot read properties of undefined (reading 'iterationsDone')`.
- **Status strip missing on `j16-leaderboard-proof`:** the budget gate is too
  aggressive — a current-schema session must still show the strip.
- **Headless/hidden-tab blank page:** if running Chrome headless, a blank panel can
  be the hidden-tab render throttle, not an app bug — bring the tab to the
  foreground or verify the session data via the backend endpoint the panel calls.
