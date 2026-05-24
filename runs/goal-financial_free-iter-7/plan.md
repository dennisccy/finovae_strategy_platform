# goal-financial_free-iter-7 Execution Plan

> **J-16 — the FINAL journey.** 15/16 must-have journeys pass; J-16 (overfit-gating
> leaderboard UI) is the only one failing. When it lands green, **persists** (DoD-0),
> and is **pixel-verified** in a real browser, all 16 journeys pass → evaluator should
> consider GOAL_ACHIEVED. The robust objective *already* gates overfit at the scorer
> level (hermetically proven since iter-4); what's missing is the **UI surface** that
> makes the gating visible. This is a read-only projection of values the loop already
> computes — **coherence (one scorer, one best, no FE recompute) is the central risk**,
> and **browser-QA pixel proof is load-bearing for the first time** (new render path).

## What to Build

**Backend (`apps/backend/backend/`)**
- **Serve a per-candidate `leaderboard` array on the `autoRun` block.** As `_run_open_universe`
  (`auto_session.py:1008`) scores candidates at the EXISTING `self.scorer.score(...)` /
  `self.scorer.is_eligible(...)` call sites (~`:1105`, `:1126/1134/1141`, `:1176`), accumulate
  a `leaderboard` list **in-memory** and persist it via the existing `_save_auto_run`
  (`:670`) path into `session.json`'s `autoRun` block (survives restart/reload). Each entry
  carries ONLY genuinely-new values:
  - `iterationId` (join key to the canonical `iterationHistory` node)
  - `stage`: `"screen" | "promote"`
  - `robustScore`: the ONE `RobustScorer.score(metrics)` output (`-inf` → `null` for JSON safety, with a clear ineligible/no-trades gating reason)
  - `eligible`: bool from the ONE `RobustScorer.is_eligible(metrics)`
  - `gatingReason`: short human string computed by the backend (`""`/`"best"`, `"WFE 0.21 < 0.30"`, `"over-leveraged (margin called)"`, `"0 trades"`, `"screened — not walk-forward validated"`, `"lower robust score"`)
  - **DO NOT** copy `totalReturn`/`sharpe`/`numTrades`/`maxDrawdown`/`wfe`/`symbol`/`timeframe` into the entry — the FE joins those from `iterationHistory` by `iterationId` (no duplicated metric).
  - **No new `best` field** — best is marked solely by `entry.iterationId === autoRun.bestIterationId` (the ONE canonical best marker).
  - **Dedup:** a promoted family appears as its **promote** node; screened-only families appear as their **screen** node — never both for the same family.
- **Bounded optional `promote_k`.** Add `promote_k: Optional[int]` to `CreateAutoSessionRequest`
  (`auto_session_routes.py:77`), validated to inclusive **1–3** (else **422** + clear message,
  mirroring the existing `history_scope` `field_validator` at `:114`); omitted → `DEFAULT_PROMOTE_K`
  (1). Thread through `_build_config` (`:189`/`:199`) → a new field on the frozen
  `AutoSessionConfig` (`auto_session.py:332`). In `_run_open_universe` replace
  `k = min(DEFAULT_PROMOTE_K, n_screened)` (`:1126`) with `k = min(config.promote_k or DEFAULT_PROMOTE_K, n_screened)`.
  Omitted ⇒ **byte-identical to today** (locks J-12/J-13/J-14). `k≥2` lets ≥2 candidates reach
  walk-forward so a real WFE-failing-but-higher-return candidate can sit in the leaderboard, not best.
  The pinned path (`_run_inner`) **ignores** `promote_k`.
- **No change** to `RobustScorer`/`BudgetTracker`/`select_best`/SCREEN-PROMOTE mechanics/seed
  bounds/`shared/contracts.py`. Leaderboard build adds **zero LLM tokens** and MUST NOT block the event loop.

**Frontend (`apps/frontend/src/`)**
- **New component `components/AutoSessionLeaderboard.tsx`**, rendered inside `IterationPanel.tsx`
  immediately after `<AutoSessionStatusStrip autoRun={autoRun} />` (`:281`, and the empty-state at `:259`)
  and before the iteration tree; shown only when `autoRun?.leaderboard` is non-empty. It:
  - reads `autoRun.leaderboard` and **joins** each entry to its matching `iterationHistory` node
    by `iterationId` for display metrics (`params.symbol/timeframe`, `totalReturn`, `sharpe`,
    `numTrades`, `maxDrawdown`, `walkForwardResult.wfe`) — **never recomputes `robustScore`** (reads `entry.robustScore` verbatim);
  - ranks rows by `robustScore` descending (sort/format only);
  - **highlights** the row where `entry.iterationId === autoRun.bestIterationId` with a clear "BEST" marker (consistent with the existing best-badge style);
  - per row shows: family (`SYMBOL TIMEFRAME`), stage badge (SCREEN/PROMOTE), robust score, total return, WFE chip (reuse the established emerald ≥0.5 / amber ≥0.3 / red <0.3 from `IterationCard.tsx:133-137`; `—` for screen rows), num-trades, max-drawdown, and `gatingReason`;
  - has empty/placeholder treatment (no leaderboard yet / run not started) and is responsive in the right panel (and under the mobile "Iterations" tab).
- **Additive type extensions** in `lib/sessionApi.ts`: add `leaderboard?: LeaderboardEntry[]` to
  `AutoRunStatus` (`:39`) and a new `LeaderboardEntry { iterationId: string; stage: 'screen' | 'promote'; robustScore: number | null; eligible: boolean; gatingReason: string }`. No change to the heavy/lazy fetch model — the leaderboard rides the existing `GET /api/sessions/{id}` poll (live updates without reload — J-08; survives reload — J-10).

## Agents Required
- developer: yes -- backend leaderboard accumulation + persist on `autoRun`, bounded `promote_k` (1–3, default 1) threaded request→config→loop, new `AutoSessionLeaderboard.tsx` + `sessionApi.ts` types + `IterationPanel.tsx` wiring, plus all hermetic tests below. (Single agent handles both backend and frontend.)

## Frontend Present
yes

> This iteration adds a genuinely **NEW front-end render path** (the leaderboard component) —
> the first since the auto-session UI. Per the iter-6 lesson, endpoint-layer proof CANNOT
> close a new render surface: **browser-QA pixel verification is mandatory and a 5th
> endpoint-only substitute is NOT acceptable.**

## Files to Create/Modify
- `apps/backend/backend/auto_session.py` -- accumulate+persist per-candidate `leaderboard` on `autoRun` from existing scorer call sites; add `AutoSessionConfig.promote_k`; `k = min(config.promote_k or DEFAULT_PROMOTE_K, n_screened)`; compute `gatingReason`.
- `apps/backend/backend/auto_session_routes.py` -- `promote_k: Optional[int]` on `CreateAutoSessionRequest` with 1–3 validator (422 otherwise); thread through `_build_config`.
- `apps/frontend/src/components/AutoSessionLeaderboard.tsx` -- **NEW** leaderboard component (ranked rows, best highlight, WFE chips, gating reason, empty state).
- `apps/frontend/src/components/IterationPanel.tsx` -- render `<AutoSessionLeaderboard>` after the status strip, before the iteration tree (both main and empty-state returns).
- `apps/frontend/src/lib/sessionApi.ts` -- add `LeaderboardEntry` interface + `leaderboard?` on `AutoRunStatus` (additive).
- `apps/backend/tests/test_*` -- NEW J-16 hermetic tests (canonical-score, overfit-gating, gating-reason correctness, best==bestIterationId, no-regression lock, promote_k validation, no-eager-parse + reload survival, no-secrets) via the existing `FakePipeline` in `tests/auto_session_helpers.py`.
- *(Out of product scope, separable/encouraged framework fix — commit separately if done)* `scripts/automation/browser-qa-phase.sh` -- correct the `:3000` FE/BE port probe to the offset ports (see Key Test Scenarios).

## UI Evolution
- **New user-facing capability:** After an automated run, the user sees a ranked **leaderboard** of evaluated candidates in the Iterations panel and can tell at a glance that the chosen best is the walk-forward-validated, WFE-passing strategy — and that a flashier higher-raw-return candidate was rejected (reason shown: WFE below threshold, over-leveraged, or screened-only/not validated).
- **New information displayed:** a multi-row leaderboard — per candidate: family, stage, **canonical robust score**, total return, color-graded WFE, trades, max-drawdown, and a **gating reason**; the marked best highlighted.
- **New user actions:** none beyond the new optional `promote_k` field on the existing `POST /api/auto-sessions` request. No new button/screen — the leaderboard is read-only display.
- **UI surface changes:** a new leaderboard panel inside the right-hand **Iterations** panel (its home already exists in the blueprint IA: "Best badge / leaderboard → Right — Iterations").
- **Navigation changes:** none. No new screen, no nav-skeleton change → **no blueprint re-approval required** (additive Data-Contract extension only, already pre-registered in `blueprint.md`).

## Visual Requirements
- **Component patterns:** match the existing Card/Badge patterns used by `AutoSessionStatusStrip.tsx` and `IterationCard.tsx`; rows as a compact table/stack within a Card; stage badge + WFE chip reuse existing chip styling.
- **Layout:** slots into the right-hand Iterations panel between the status strip and the iteration tree; responsive within the panel and under the mobile "Iterations" tab.
- **Key visual effects:** dark analytical-workstation styling; reuse the established WFE color semantics (**emerald ≥0.5 / amber ≥0.3 / red <0.3**, from `IterationCard.tsx:133-137`); best row highlighted consistently with the existing best-badge treatment; Lucide icons; Tailwind tokens only — **no raw hex outside the palette, no ad-hoc spacing**.
- **States to handle:** empty/placeholder (no leaderboard yet / run not started — no crash on a terminal run with zero completed candidates), populated/ranked, and the best-highlighted row; `—` for screen rows with no WFE.

## Key Test Scenarios

**0. PERSISTENCE GATE (LOAD-BEARING — run FIRST; the reason iter-5 failed; now FE-inclusive).**
- `git diff --stat HEAD -- apps/` is **non-empty** and includes the backend changes (`auto_session.py`, `auto_session_routes.py`), the **new FE component** (`AutoSessionLeaderboard.tsx`), the FE type/wiring edits (`sessionApi.ts`, `IterationPanel.tsx`), and the new J-16 test file(s).
- `runs/goal-financial_free-iter-7/status.json` has `changed_files` non-empty and `tests_run: true`; the dev handoff "Files Changed" matches `git diff --name-only HEAD -- apps/`.
- Any worktree work MUST be merged back into the pipeline tree before this gate. **A green pytest cache is NOT evidence.** An empty `apps/` diff or a missing FE component is an automatic FAIL downstream.

**1. Hermetic backend (no live LLM — inject the `FakePipeline`):**
- **canonical-score:** every `leaderboard[*].robustScore == RobustScorer.score(metrics)` for that candidate; a grep of the diff finds **no** new `RobustScorer(...)` or `BudgetTracker(...)` construction.
- **overfit-gating (the binding J-16 assertion):** with `promote_k=2`, build a promoted set where A = higher raw return + `wfe<0.3` and B = lower raw return + `wfe≥0.3`; assert `bestIterationId == B`, A is in `leaderboard` with `eligible:false` + a `gatingReason` citing WFE, and A (higher return) is **NOT** best. Add an over-leveraged variant: high-return `margin_called` candidate → `eligible:false`, gating cites over-leverage, not best.
- **gating-reason correctness:** each `gatingReason` matches the `is_eligible` outcome (WFE-fail / margin-called / below-trades-floor / screened-only / lower-score / best).
- **best == bestIterationId:** the entry the FE marks best (`iterationId == bestIterationId`) is the WFE-gated `select_best(promoted)` result — no separate best field served.
- **no-regression lock (J-12/J-13/J-14):** with `promote_k` omitted (default 1), SCREEN ordering, the `wfv` pattern, and the marked best are **byte-identical to HEAD**; J-13 token/USD tallies unchanged (leaderboard adds 0 tokens). The existing J-12/J-13/J-14 hermetic tests (which set no `promote_k`) MUST pass **unchanged**.
- **promote_k validation:** out of `[1,3]` → **422**; omitted → default 1; `k = min(promote_k, n_screened)`; a cost cap still halts mid-promote.
- **no eager parse + reload survival:** monkeypatch `read_iteration_full` to raise and assert `GET /api/sessions/{id}` still returns `autoRun.leaderboard` (built from in-memory metrics, persisted in `autoRun`); re-read after a simulated worker restart and assert it persists.
- **secrets:** leaderboard entries + gating strings contain no `api_key` / `sk-` material.
- **Full hermetic suite green** except the single known pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (out of scope). Frontend `npm run build` (`tsc && vite build`) and `npm run lint` clean.

**2. Endpoint/display:** `GET /api/sessions/{id}` → `autoRun.leaderboard` shape correct; the FE join (leaderboard ⨝ `iterationHistory` by `iterationId`, best via `bestIterationId`) yields a correct ranked view; best is WFE-gated and equals `bestIterationId`.

**3. Browser/pixel (LOAD-BEARING — must not be skipped or substituted):** with a seeded/triggered open-universe run, open the session in a **real foreground, uncontended** browser tab and verify the leaderboard **renders**: ranked rows display, the best row is highlighted, WFE chips are color-graded, and the higher-return non-best candidate visibly shows its gating reason. Capture evidence screenshots.
  - **Harness root cause (CONFIRMED, actionable):** `scripts/dev.sh` binds **FE on `:3691`** and **BE on `:8691`** (`port = base + sha1(repo_path)%1000`, offset = `0x451b % 1000 = 691`), but `browser-qa-phase.sh` defaults to probing `:3000`/`:8000`. **Fix:** export `CHAIN_FRONTEND_PORT=3691 CHAIN_BACKEND_PORT=8691 CHAIN_FRONTEND_URL=http://localhost:3691 CHAIN_BACKEND_HEALTH_URL=http://localhost:8691/health` (or recompute via dev.sh's formula), and **health-re-probe across the whole QA window** (iter-2/iter-3/iter-4 lesson: FE torn down mid-window). Keep the tab foreground (hidden-tab render throttle gives blank pixels — per MEMORY, that's not an app bug).
  - **Live-QA date range (iter-4 lesson):** if a live/keyed open-universe run is used to populate the leaderboard, use a date range **≥ 9 months** (≥ IS+OOS = 6+3 at defaults) with `promote_k: 2`, or PROMOTE forms 0 walk-forward windows → `wfe 0.0` → `best=None` and the gating demo is vacuous. The hermetic overfit scenario (Test 1) is the **binding** proof; the live run is optional/key-gated.

**4. No anti-goal violation:** exactly ONE `RobustScorer` + ONE `BudgetTracker` (no new construction in the diff); leaderboard score is `RobustScorer.score()` output (no FE recompute, no second scorer); best is the one `bestIterationId` (no second best definition); `shared/contracts.py` NOT in the diff; open path does NOT eagerly parse `result.json`/`rating.json`; bounded seed preserved (`promote_k` reprioritizes already-screened in-seed candidates, never adds symbols); budget honored; no new infra; no secrets; event loop non-blocking.

**5. Required-still-passing journeys remain green** — especially **J-09** (best == the one `bestIterationId`, WFE-gated), **J-12** (≥2 distinct configs from the bounded seed), **J-13** (token/USD/`max_configs` hard-enforced; leaderboard adds 0 tokens), **J-14** (SCREEN cheap-no-WF, PROMOTE k<n_screened on stronger model + WF, best from promoted only). Plus J-01–J-08, J-10, J-11, J-15 no-regression. Dev handoff written at `docs/handoffs/goal-financial_free-iter-7-dev.md`; the 6 UI-visibility artifacts produced; `git diff` reconciled with the handoff.

## Assumptions & Coherence Notes (no blocking questions — spec is complete and verified)
- **All spec anchors confirmed against the live tree** (line numbers ±, structure exact): `RobustScorer`/`score`/`is_eligible`/`select_best`, `DEFAULT_PROMOTE_K=1`, `_run_open_universe` scorer call sites, `AutoSessionConfig`, `_build_config`, the `history_scope` validator pattern (the model for `promote_k`), `session_routes.get_session` serving `autoRun`+`iterationHistory` lazily, and the FE files (`AutoSessionLeaderboard.tsx` does **not** exist yet → greenfield; `sessionApi.ts` has no `leaderboard`/`LeaderboardEntry` yet; `IterationCard.tsx` WFE thresholds at `:133-137`).
- **The FE `iterationHistory` node type already carries the join fields** the leaderboard needs (`IterationCard.tsx` already reads `iteration.walkForwardResult.wfe`, `.totalReturn`, `.maxDrawdown`, `.rating`). The developer locates the exact `IterationNode`-style type in `sessionApi.ts`/its detail type and joins by `id`; it must NOT duplicate metrics into the leaderboard entry.
- **Blueprint conformance:** the iter-7 J-16 extension is **already pre-registered** in `runs/goal-session-financial_free/state/blueprint.md` (the "Robust objective score + best marker" row was extended for `autoRun.leaderboard`, and the open-universe row notes the bounded `promote_k`). This is an **additive Data-Contract extension of an existing row** — same module (`RobustScorer`), same endpoint (`GET /api/sessions/{id}`), one best definition (`bestIterationId`) — so **no re-approval** is needed. Keeping the entry free of duplicated metrics (FE joins `iterationHistory`) is what keeps the coherence-auditor's "numbers don't match" gate green.
- **No scope creep / no goal drift detected.** `promote_k` is the minimal, bounded (1–3, default 1) enabler that makes WFE-gating demonstrable with real promoted candidates while keeping J-12/J-13/J-14 byte-identical; it does **not** fan out the seed (anti-goal safe). Everything in the spec traces to goal.md J-16 + its anti-goals.
- **Carry-forward non-blockers (out of scope, unchanged):** pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip`; flaky `test_post_returns_before_loop_completes_and_get_stays_responsive` (de-flake opportunistically); the out-of-scope `/health` probe still in the tree (release-manager reconciles handoff/changed_files at commit); `auto_session.py` size (~1.3k lines — future refactor, not this iteration).
