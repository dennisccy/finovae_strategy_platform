**Verdict:** COHERENCE-PASS

# Coherence Audit — goal-financial_free-iter-7 (J-16: overfit-gating leaderboard UI)

- **Session:** financial_free · **Iteration:** 7 · **Auditor:** coherence-auditor
- **Snapshot SHA:** `a4f9c1b92254f140b1dc5200d0429e9150b49036` (resolved; diff inspected via `git diff HEAD` + untracked new files)
- **Blueprint:** `runs/goal-session-financial_free/state/blueprint.md`
- **UI surface map:** present (`reports/phase-goal-financial_free-iter-7-ui-surface-map.md`)

## Summary

This iteration surfaces the optimizer's per-candidate robust-score competition as a new right-panel
**leaderboard** and adds a bounded optional `promote_k` (1–3, default 1) knob. It is a textbook
additive, single-source-of-truth change: the leaderboard reads canonical served values verbatim and
joins display metrics from the canonical iteration nodes. **No objective Data-Contract or
Information-Architecture violation found.** No advisory issues material enough to flag.

## Step 1 — Data Contract check (the "numbers don't match" gate) → PASS

**New values introduced (all registered in the blueprint extension, all from the ONE scorer):**

- `robustScore` — computed by `self.scorer.score(m)` at `apps/backend/backend/auto_session.py:807`
  (the single `RobustScorer` instance; same call site family as `select_best` at `:1271` and the
  activity-log score text at `:1191`). Served on `autoRun.leaderboard` via the existing
  `GET /api/sessions/{id}` (no new endpoint). FE reads it **verbatim** —
  `AutoSessionLeaderboard.tsx:107` `formatScore(entry.robustScore)` only formats; the sort at
  `:58-63` orders by the served value, never recomputes it.
- `eligible` — `self.scorer.is_eligible(m)` at `auto_session.py:808` (the one scorer).
- `gatingReason` — backend-narrated at `auto_session.py:_gating_reason` (`:777`), derived entirely
  from the one scorer's thresholds (`self.scorer.min_trades_floor`, `self.scorer.wf_accept_threshold`)
  + the candidate's `m.margin_called` / `m.wfe`. FE reads it **verbatim**
  (`AutoSessionLeaderboard.tsx:137`), never re-derives it.

**No duplicate computation.** Grep of the diff for new `RobustScorer(` / `BudgetTracker(`
construction → **none**. Every `score`/`is_eligible`/`select_best` call in the post-change file goes
through the single `self.scorer` instance. `_json_safe_score` (`auto_session.py:398`) maps the
scorer's `-inf` → JSON `null` and rounds — serialization/formatting, not a second computation.

**No non-canonical source / no duplicated display metric.** The backend stores **only** the
genuinely-new fields on each entry (`iterationId/stage/robustScore/eligible/gatingReason`,
`auto_session.py:803-809`) — it deliberately does **not** copy `totalReturn`/`wfe`/`numTrades`/
`maxDrawdown`/`symbol`/`timeframe`. The FE joins those from the canonical `iterationHistory` node by
`iterationId` (`AutoSessionLeaderboard.tsx:55,78-86`): `totalReturn`/`numTrades`/`maxDrawdown` are the
canonical `IterationNode` fields (`useBacktest.ts:381/383/385`), and `wfe` is read from
`node.walkForwardResult?.wfe` gated on `walkForwardStatus === 'complete'` (`:83`) — the canonical
walk-forward value (`POST /api/execute-walk-forward` → carried on the node). No metric is recomputed
client-side; the activity-log score and the leaderboard score are the *same* `RobustScorer.score(m)`
on the *same* in-memory `m`, merely formatted to different precision (allowed re-format).

**No eager-parse violation.** The leaderboard is built from in-memory metrics during the run
(`_record_leaderboard` at the existing `_run_open_universe` SCREEN/PROMOTE call sites,
`auto_session.py:1194,1284`) and persisted into the `autoRun` block via the existing `_save_auto_run`
(`:725`); it does **not** re-parse `result.json`/`rating.json` on the open path.

**No unregistered value.** The new values are explicitly added to the blueprint's existing "Robust
objective score + best marker" row and the open-universe row (blueprint diff is an additive extension
only — no new value family, no new endpoint, no schema fork).

## Step 2 — Information Architecture check → PASS

- **Canonical home exists.** The blueprint IA pre-registered this slot: Right panel → Iterations →
  "Automated-session status strip (… best badge / **leaderboard**)" and journey row "J-16 … Best
  badge / leaderboard → Right — Iterations". The new `AutoSessionLeaderboard` lives in exactly that
  home — mounted inside `IterationPanel.tsx` after `AutoSessionStatusStrip` and before the iteration
  tree, in **both** the populated (`:284`) and empty-state (`:261`) returns.
- **Reachable in ≤2 clicks.** It renders inline in the always-visible persistent right panel (0 extra
  clicks on desktop; 1 click via the mobile "Iterations" tab). It is shown only when
  `autoRun.leaderboard` is non-empty (`AutoSessionLeaderboard.tsx:51-52`) — manual/zero-candidate
  sessions render nothing (no empty card, no crash). No new route; router/nav unchanged.
- **No duplicate home.** Confirmed greenfield — there is no other leaderboard/ranking view. It does
  not duplicate the iteration history tree (chronological/parent-child list) nor the status strip's
  single best badge; it is a distinct ranked-by-robust-score projection, and "best" is marked solely
  by `entry.iterationId === autoRun.bestIterationId` (`:79`) — the one canonical best definition, no
  second best field.
- **No parallel shell.** Built with the established Card/Badge/Tailwind tokens (slate/emerald/amber/
  red/violet), Lucide icons (`Trophy`/`Award`), and the established WFE color thresholds (emerald
  ≥0.5 / amber ≥0.3 / red <0.3, `:16-20`) consistent with `IterationCard`. No new layout/nav skeleton.

The `promote_k` API field (`auto_session_routes.py:101`, validated 1–3 → 422 otherwise, `:126-131`)
is a request-contract enabler, not a UI surface; it adds no screen and no nav.

## Step 3 — Advisory (WARN-only) observations

None material. WFE is shown to 2 decimals with the established color semantics, and total-return is
sign-prefixed percent — both consistent with the existing panels. The blueprint was updated in-place
as the spec's stated additive extension (no new screen / nav change → no re-approval needed).

## Conclusion

One scorer, one best definition, one serving endpoint, one canonical home — all preserved. The
leaderboard is a read-only projection of values the loop already computes, and the FE reads them
verbatim while joining the rest from the canonical iteration nodes. **COHERENCE-PASS.**
