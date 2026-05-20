# Phase goal-auto-money-printer-iter-6 — What to Click (Operator Verification Guide)

**Phase:** goal-auto-money-printer-iter-6
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## What you are verifying

Every promoted candidate in an open-universe automated run now carries a
plain-English rationale beneath the existing green "complete" row in the
Activity Log: either `Best — WF-validated (…)` or `Not best — <named gate>`.
The `Best` badge in the iteration list sits on the same iteration whose
rationale begins with `Best —`. A multi-candidate run also closes with a
single violet `Robust-best: …` summary row.

---

## Prerequisites

- Frontend running at `http://localhost:3691` (open in Chrome)
- Backend running and healthy (check: `curl http://localhost:${CHAIN_BACKEND_PORT:-8000}/api/health` returns HTTP 200)
- No login required; this app does not use auth
- Backend store has its durable default path (not `/tmp`) so prior sessions are visible

---

## Verification Steps

1. Open `http://localhost:3691` in Chrome
   - **Expect:** Main session view renders with the chat input on the left, an empty (or prior-session) iteration list in the middle, and the Activity Log column on the right. No red error overlay.

2. In the chat input on the left panel, type `momentum breakout` (exactly), then click the "Send" (paper-airplane icon) button
   - **Expect:** A new auto-session starts. The AutoRunBar at the top of the page shows status `running` with a spinner. Within ~10 seconds, the Activity Log column starts populating with rows (prompt row, AI-step rows, SCREEN entries).

3. Wait up to 5 minutes for the AutoRunBar status to read `complete`, `idle`, `budget-exhausted`, or `stopped` (no spinner). Scroll the Activity Log column down as new rows appear
   - **Expect:** ≥ 2 emerald-bordered cards with a green checkmark icon appear in the Activity Log. The top line of each reads something like `return X.X% over N trades, robust Y.YY, walk-forward WFE Z.ZZ`.

4. Look BENEATH the top line of each emerald card for a smaller, muted-color second line
   - **Expect:** Each emerald card shows TWO lines: the existing numeric summary on top, and a smaller muted sub-line below. Exactly ONE sub-line starts with `Best —` (e.g., `Best — WF-validated (WFE 0.70, 25 trades)`). Every OTHER emerald card's sub-line starts with `Not best —` followed by a named gate (`Not best — WFE 0.00 below 0.30 gate`, `Not best — under min-trades floor (2 < 5)`, `Not best — no walk-forward windows`, `Not best — over-leveraged (1.5×)`, or `Not best — lower robust score (X.XX vs best Y.YY)`).

5. In the iteration list (middle column), find the iteration card that shows a `Best` badge. Note its position (e.g., the 3rd iteration). Then in the Activity Log column, find the emerald card that corresponds to that same iteration
   - **Expect:** The iteration carrying the `Best` badge has, in the Activity Log, a `complete` card whose muted sub-line begins with `Best —` (NOT `Not best —`). The badge and the rationale agree on which iteration is the round winner.

6. Scroll to the bottom of the Activity Log column
   - **Expect:** Just above the terminal/idle marker, ONE violet-text row with a small lightning-bolt icon reads `Robust-best: <iter-id> selected over N other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage` where `<iter-id>` matches the iteration with the `Best` badge.

7. Press `Ctrl+F` (or `Cmd+F` on macOS) inside the page and search for the literal text `NaN`, then `undefined`, then `null`, then `Infinity`, then `sk-`
   - **Expect:** Each search reports "phrase not found" (or 0 matches) inside the rendered Activity Log. No degenerate numbers and no secrets leak into the visible feed.

8. Open the session list (sidebar/top-bar control) and click any prior session whose status is `complete` from before this iteration (any earlier-dated session). Click any green-done iteration card in its iteration list
   - **Expect:** Detail panel loads strategy spec, metrics, trade list, and equity chart with no error. The Activity Log for this older session shows its prior `complete` rows as single-line emerald cards (no muted sub-line beneath them) — proving the renderer is byte-identical for pre-iter-6 entries.

---

## What "Working Correctly" Looks Like

- Two-line emerald `complete` cards in the open-universe session: bold numeric summary on top, smaller muted English rationale on the bottom
- `Best` badge in the iteration list aligns to the same iteration whose rationale starts `Best —`
- One concluding violet `Robust-best: …` row at the bottom of a multi-candidate run
- Old (pre-iter-6) sessions and pinned-strategy sessions render their `complete` cards as single-line emerald cards (no second muted line) — backward visual compatibility holds

## If Something Looks Wrong

- **All emerald cards show only one line, no muted sub-line:** Likely the backend did not emit `detail` (check `apps/backend/backend/auto_session.py` near line 1429-1441 and the rationale helper wiring). The frontend conditional `entry.detail &&` correctly hides the sub-line when absent — so the backend wire-in is the suspect.
- **An emerald card shows `null`, `undefined`, `NaN`, or `[object Object]` in the sub-line:** Backend rationale helper failed the error-case fallback contract. Check the corrupt-`RobustInputs` and non-finite-score branches in the helper.
- **`Best` badge and `Best —` rationale disagree (badge on iteration A, but A's rationale starts `Not best —`):** Likely a snapshot-vs-live mismatch — the rationale text is a write-time snapshot per the spec, but the round-current best should agree with the final `bestIterationId` at run termination. Confirm by reading the `autoRun.bestIterationId` field via `GET /api/sessions/<sid>` and comparing.
- **The violet `Robust-best:` row is missing on a run that produced ≥ 2 emerald complete cards:** Backend forgot to emit the terminal summary; check the `len(completed) >= 2` guard near the end of the open-universe loop.
- **A pinned-strategy run (manual single-strategy submission) shows a muted rationale sub-line beneath its emerald card:** Anti-goal violation — the rationale leaked into `_run_pinned`. Confirm `git diff HEAD -- apps/backend/backend/auto_session.py` shows zero edits inside `_run_pinned` (lines 1125-1234).
- **Blank page or red error overlay on `http://localhost:3691`:** Frontend build or runtime error; check DevTools Console and `cd apps/frontend && npm run build` for TypeScript errors.
