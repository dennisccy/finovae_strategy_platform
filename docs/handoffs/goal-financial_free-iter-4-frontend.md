# goal-financial_free-iter-4 Frontend Handoff

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering (J-14)
**Date:** 2026-05-23
**Agent:** developer
**Status:** complete — **no frontend code change required**

## Decision: reuse the existing `auto-run` render branch (zero FE change)

The spec and plan offered two mechanisms for surfacing the SCREEN/PROMOTE stages and recommended the **lowest-risk** one: emit the stage entries as the existing `type:"auto-run"` activity records with explicit `SCREEN —` / `PROMOTE —` text labels. The backend does exactly that, so the existing `ActivityLogEntry` `auto-run` branch renders them with **no code change**.

Verified branch (`apps/frontend/src/components/ActivityLogEntry.tsx:27-34`):

```tsx
if (entry.type === 'auto-run') {
  return (
    <div className="flex items-center gap-2 mb-1.5 ml-1">
      <Zap className="w-3.5 h-3.5 text-violet-400 flex-shrink-0" />
      <span className="text-xs text-violet-600 font-medium">{entry.content}</span>
    </div>
  )
}
```

It renders `entry.content` verbatim (Zap icon + violet text), so every backend stage entry appears legibly in the Left Activity Log:

- **SCREEN stage header** — e.g. `SCREEN — screening 3 seed config(s) on gpt-5.4-mini, no walk-forward.`
- **per screened candidate** — e.g. `SCREEN — BTC/USDT 1h: score +0.0400`
- **PROMOTE stage header** — e.g. `PROMOTE — escalating top-1 of 3 to claude-haiku-4-5 + walk-forward.`
- **promote best** — e.g. `PROMOTE — ETH/USDT 1h is the new best (WFE-gated, score +0.2800).`

The two stages are **visually distinguishable** by their `SCREEN —` / `PROMOTE —` prefixes (sanctioned by the spec) and are **capturable by browser-qa** as plain text in the auto-run entries.

## What a user now sees

- An open-universe run's Activity Log shows a cheap **SCREEN** sweep over several seed configs, then a **PROMOTE** step that escalates only the best `k` (k < screened) to walk-forward + a stronger model.
- The **screen→promote lineage** shows in the existing iteration tree: a promoted node's `parentId` is the screened candidate it was promoted from, so the promoted card renders as a child of its screened candidate.
- **Promoted cards** display their own `modelUsed` (the stronger request model, e.g. Claude Haiku 4.5) **and** a walk-forward section. **Screened-only cards** display the cheap model (GPT-5.4 Mini) and **no** walk-forward section. Both are valid existing card shapes — no card change required.

## UI surface / navigation changes

- **None.** No new page, panel, route, or nav entry. No second data fetch — the Activity Log already streams from the canonical `GET /api/sessions/{id}`. No blueprint nav-skeleton change → no re-approval.

## Verification

- Read `ActivityLogEntry.tsx` and confirmed the `auto-run` branch renders arbitrary `content` (the SCREEN/PROMOTE labels) with the established Zap-icon / violet-text idiom.
- The backend live integration test (`test_live_open_universe_staged_screen_promote`) confirmed the persisted activity entries carry `SCREEN —` and `PROMOTE —` content and that promoted nodes carry `modelUsed = claude-haiku-4-5` + a walk-forward result while screened nodes carry the cheap model + none — i.e. the exact data the cards/tree read.
- Pixel-level capture of the live-updating status strip (J-08), reload-mid-run survival (J-10), and the SCREEN/PROMOTE entries (J-14) is the browser-qa agent's load-bearing task this iteration (see dev handoff "Known Issues").

## Files Changed

- None. (Display-only confirmation; the backend reuses the already-rendered `auto-run` entry type.)
