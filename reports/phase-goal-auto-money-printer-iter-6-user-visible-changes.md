# Phase goal-auto-money-printer-iter-6 — User-Visible Changes

**Phase:** goal-auto-money-printer-iter-6
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

- **Read a plain-English reason for every promoted candidate's gate decision** in the session Activity Log. Beneath each open-universe `complete` row (the green checkmark card), a muted sub-line names either why this candidate IS the round-current best ("Best — WF-validated (WFE 0.70, 25 trades)") or why it is NOT ("Not best — WFE 0.00 below 0.30 gate", "Not best — under min-trades floor (2 < 5)", "Not best — no walk-forward windows", "Not best — over-leveraged (2.5×)", or "Not best — lower robust score (0.50 vs best 1.50)").
- **See a durable terminal verdict line at the end of multi-candidate open-universe runs.** After all PROMOTE candidates complete, one final violet "auto-run" row (zap icon) reads: "Robust-best: &lt;iter id&gt; selected over N-1 other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage". This survives even if the per-candidate rationale rows scroll out of view.
- **Audit the robust-best invariant without decoding numeric sentinels.** Previously, a gate-failing candidate's `robust = -999.x` sentinel was the only signal that a high-raw-return candidate had been rejected; now the named gate (WFE / min-trades / over-leverage / lower-robust-score) is shown in operator vocabulary directly on the row.
- **Identify a "sole survivor" PROMOTE clearly.** When only one candidate completes PROMOTE in an open-universe round, its rationale reads "Best — WF-validated (...)" if its gates pass, or "Best (sole survivor) — gates not met: &lt;reason&gt;" if it fails its own gates. A best is always marked.

---

## What Changed in the Visible UI

- The **Activity Log feed's `complete` row** (the emerald-bordered card with a green `CheckCircle2` icon, rendered by `ActivityLogEntry.tsx`) now wraps its existing one-line content in a `flex-1 min-w-0` container and, when the entry carries a non-empty `detail` field, renders a single additional `<p>` sub-line below the main content using muted typography (`text-xs text-emerald-700/70 mt-1`).
- A **new "Robust-best: ... selected over N-1 other promoted candidate(s)" terminal row** appears in the activity feed at the end of open-universe runs that promoted ≥ 2 candidates. It uses the existing `auto-run` entry style (violet `Zap` icon, violet text) — not a new component.
- The **emerald `complete` card dimensions and rounded corners are byte-preserved** (`bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3`). Rows that do not carry a `detail` (e.g., pinned-path completes, SCREEN completes, all pre-iter-6 historic rows) render identically to before — there is no visual regression for runs without a rationale.

---

## What Old Behavior Changed

- **PROMOTE `complete` activity entries in open-universe runs**: previously rendered a single line (e.g., `"return 12.0% over 25 trades, robust 1.50, walk-forward WFE 0.70"`). Now: the same line still renders, plus a muted sub-line carrying the named gate decision. The cryptic `robust = -999.x` sentinel is still implicit in the existing top line but is now plainly explained in the sub-line.
- **Pinned-path `complete` entries and SCREEN entries are intentionally unchanged** — no rationale sub-line is rendered on those rows because the backend never emits `detail` for them. Operators who only run pinned (J-07–J-11) or SCREEN (J-14) flows see no change.
- **Manual (non-headless) runs**: visually unchanged. Manual runs do not traverse the PROMOTE branch, so the backend never emits a rationale `detail` on their `complete` rows — they look byte-identical to today.

---

## Not Visible Yet

- **Cross-round rationale recomputation.** When a later PROMOTE round changes the round-current `bestIterationId`, earlier rows' rationale text is NOT retroactively updated. The text is a write-time snapshot per the phase's explicit snapshot-semantics decision; the `Best` badge on `IterationCard` (driven by `bestIterationId`) remains the live source of truth. Operators reading an old row need to consult the terminal summary row (or the badge) to see the final chosen winner.
- **The "over-leveraged" rationale text exists but is not exercised by a real backtest** in this iteration. `RobustInputs.leverage` is hard-coded to `1.0` in `_robust_inputs` (`auto_session.py:1072`); plumbing a `leverage` request parameter through the API is explicitly out of scope. The reason string is defined for signature completeness and unit-tested but will not appear from a live engine run today.
- **No new leaderboard page, sortable grid, or top-N panel** was added. The rationale enrichment lives entirely on the existing Activity Log row — the goal explicitly chose the additive-feed approach over a parallel leaderboard surface.
