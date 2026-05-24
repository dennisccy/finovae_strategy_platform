# Goal Iteration 7 — J-16: robust-objective overfit-gating leaderboard UI (the FINAL journey)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** financial_free
- **Iteration:** 7
- **Mode:** next
- **Depth:** full
- **Frontend Present:** yes (this iteration adds a genuinely NEW front-end render path — a leaderboard component — for the first time since the auto-session UI; browser-QA pixel proof is LOAD-BEARING)
- **Target journeys:** J-16
- **Required-still-passing journeys:** J-09 (best-marking — MOST-AT-RISK: the leaderboard's "best" MUST be the one `bestIterationId`), J-12, J-13, J-14 (MOST-AT-RISK — this iteration edits `_run_open_universe` and adds `promote_k`), J-07, J-08, J-10, J-11 (auto-session mechanics), plus J-01, J-02, J-03, J-04, J-05, J-06 (no-regression)
- **Anti-goal reminders (verbatim from `docs/goal.md`):**
  - "The automated 'best' MUST be selected by the robust objective (walk-forward OOS, WFE-gated, drawdown-penalized, min-trades floor); a higher raw-return but WFE-failing or over-leveraged candidate MUST NOT be marked best."
  - "The automated chain MUST write the same session/iteration/activity/insights artifacts the UI renders (the existing file store) — no parallel store, no schema fork; a headless run MUST be indistinguishable in the UI from a manual one."
  - "`GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint."
  - "The frozen dataclasses in `shared/contracts.py` must not be mutated in place."
  - "Cheap `SCREEN` evaluation MUST NOT run walk-forward or the strongest model; those are reserved for promoted candidates."
  - "Open-universe exploration MUST start from a bounded seed universe and MUST NOT blindly fan out across the entire exchange symbol list; expansion only as budget/history justify."
  - "Every automated run MUST honor a hard budget (AI tokens/USD AND max-configs AND wall-clock), enforced by an immutable cost tracker; it MUST NOT loop unbounded or take 'one more round' past the cap."
  - "No new external infrastructure (no Celery/Redis/database/broker/vector-store) for the automated session; optimizer state persists in the existing file store."
  - "API keys/secrets MUST NOT be written into the activity log or persisted in session artifacts."
  - "The automated background job MUST NOT block the API event loop; the UI poll and other requests MUST stay responsive while a run is active."
  - Coherence gate (re-confirmed iter-2 / iter-4 / iter-6): there is exactly ONE `RobustScorer` and ONE `BudgetTracker`. The leaderboard MUST read the canonical `RobustScorer` values; it MUST NOT recompute scores in the front-end or introduce a second best-definition path.

## GOAL

After an open-universe automated run, the right-hand **Iterations** panel shows a **leaderboard** of the candidates the optimizer evaluated, ranked by the canonical robust score, with the marked **best** highlighted — and the best is the WFE-gated, walk-forward-validated candidate, while a **higher-raw-return but WFE-failing or over-leveraged candidate is visibly NOT selected as best** (its gating reason shown). This is the FINAL journey: when J-16 lands green, persists, and is pixel-verified, **all 16 must-have journeys pass** and the evaluator should consider GOAL_ACHIEVED.

## BACKGROUND

15 of 16 journeys pass; **J-16 is the only failing journey** and the last before GOAL_ACHIEVED (iter-6 evaluator recommendation: "J-16 at full depth — the final journey"). The robust objective *already* gates overfit at the scorer level (proven hermetically since iter-4 via `test_open_universe_best_is_wfe_gated_not_highest_return`); what is missing is the **UI surface** that makes the gating visible — a multi-candidate leaderboard. J-16's acceptance is "the marked best satisfies WFE ≥ threshold + min-trades floor and derives from walk-forward OOS; a higher raw-return but WFE-failing or over-leveraged candidate is not selected as best (visible in the leaderboard / activity log)."

**Critical state verified in code before planning (do not re-derive — but do confirm against the live tree):**
- `RobustScorer.score()` (`apps/backend/backend/auto_session.py:262`) returns a **transient scalar**; it is only embedded as text in `auto-run` activity entries and used to pick `bestIterationId`. **It is NOT persisted or served per-candidate.** `RobustScorer.is_eligible()` (`:270`) holds the WFE gate (`wfe is None or wfe >= WF_ACCEPT_THRESHOLD=0.3`), the min-trades floor (`DEFAULT_MIN_TRADES_FLOOR=1`), and `not margin_called` (over-leverage). `select_best()` (`:279`) returns the highest-scoring **eligible** candidate over the **promoted** set only.
- `autoRun` (served by `GET /api/sessions/{id}`, `session_routes.py:142`) carries `status / stopReason / stopRequested / bestIterationId / budget / startedAt / endedAt` — **no per-candidate scores, no leaderboard.**
- `iterationHistory` nodes already serve the display metrics the leaderboard needs (`totalReturn`, `sharpe`, `numTrades`, `maxDrawdown`, `walkForwardResult.wfe`, `params.symbol/timeframe`, `parentId`) — these are canonical and lightweight (no eager full-payload parse).
- `DEFAULT_PROMOTE_K = 1` (`auto_session.py:95`) is a module constant and **not configurable**, so a typical run promotes exactly one candidate to walk-forward → only one WFE-bearing candidate exists, which makes the literal "higher-raw-return **WFE-failing** candidate not best" hard to demonstrate with real promoted candidates.
- Frontend: `AutoSessionStatusStrip.tsx` renders the run-state/best badge/budget counters; `IterationPanel.tsx` (~line 279) is where a leaderboard slots in (after the status strip, before the iteration tree); `AutoRunStatus`/`AutoRunBudget` types live in `apps/frontend/src/lib/sessionApi.ts:39`; the WFE color thresholds (emerald ≥0.5 / amber ≥0.3 / red <0.3) are already established in `IterationCard.tsx`. **No existing leaderboard/ranking view** — this is greenfield FE.

**Therefore J-16 needs two coherent pieces:** (1) the backend must **serve** the canonical per-candidate robust score + eligibility + gating reason (computed by the ONE existing `RobustScorer`/`is_eligible` at their existing call sites, persisted into the `autoRun` block, served by the existing endpoint — no second scorer, no new endpoint, no frozen-contract change); and (2) a new FE leaderboard component that reads those values **verbatim** and ranks/highlights them. A small, bounded, optional `promote_k` enabler lets a run promote ≥2 candidates so the overfit gate is genuinely demonstrable with real walk-forward-validated candidates (default 1 keeps J-12/J-13/J-14 byte-identical).

Lessons carried into this spec (from `lessons.md`, **Applies to** matched):
- **iter-6 (LOAD-BEARING for J-16 specifically):** "J-16 is the FIRST journey since the auto-session UI to add a genuinely NEW front-end render path … endpoint-layer proof cannot close a new render surface, and the `browser-qa-phase.sh` `:3000`-vs-offset-`:3692` health-probe root cause must be fixed (or a real foreground browser-QA window budgeted)." Browser-QA of the leaderboard is a HARD DoD item — **a 5th endpoint-only substitute is NOT acceptable.**
- **iter-5 (LOAD-BEARING — lost work):** "A green pytest cache is NOT evidence the work persisted." The DoD-0 persistence gate is re-applied (now FE-inclusive). Worktree-only work that isn't merged back is an automatic FAIL.
- **iter-4 (live-QA recipe):** any walk-forward-dependent live QA MUST use a date range ≥ `IS_months + OOS_months` (≥ 9 months at the 6/3 defaults), or PROMOTE walk-forward forms 0 windows → `wfe 0.0` → `best=None` and the leaderboard's gating is vacuous.
- **iter-4 (harness, not effort):** the recurring pixel miss is the `browser-qa-phase.sh` frontend-lifecycle/port root cause (FE binds an offset port e.g. `:3692`, harness probes `:3000`), not agent effort — fix the probe or run a real uncontended foreground window with health re-probing.
- **MEMORY (headless render throttle):** a blank Chrome-MCP page is the hidden-tab render throttle, NOT an app bug — keep the QA tab **foreground and uncontended** when capturing leaderboard pixels; do not let a concurrent QA run steal the foreground tab.
- **iter-0 (no eager parse):** building the leaderboard MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` on the open path — accumulate it from in-memory metrics during the run and persist it in the `autoRun` block.

## IN SCOPE

### Backend

- [ ] **Serve a per-candidate leaderboard in the `autoRun` block.** As the open-universe loop scores candidates (the existing `self.scorer.score(...)` / `self.scorer.is_eligible(...)` call sites in `_run_open_universe`, `auto_session.py:~1102/1134/1176`), accumulate a `leaderboard` array onto the `autoRun` block and persist it via the existing `_save_auto_run` path (same file store, survives restart/reload — J-08/J-10). Each entry carries ONLY the genuinely-new values (everything else the FE joins from `iterationHistory`):
  - `iterationId` (key — joins to the canonical `iterationHistory` node for display metrics)
  - `stage`: `"screen" | "promote"`
  - `robustScore`: the canonical `RobustScorer.score(metrics)` output for that candidate (the ONE scorer — do NOT add a second scoring path; `-inf` may be represented as `null` for JSON safety with a clear "ineligible (no trades)" gating reason)
  - `eligible`: bool, from the ONE `RobustScorer.is_eligible(metrics)`
  - `gatingReason`: a short human string computed by the backend from the eligibility/best outcome — e.g. `""`/`"best"`, `"WFE 0.21 < 0.30"`, `"over-leveraged (margin called)"`, `"0 trades"`, `"screened — not walk-forward validated"`, `"lower robust score"`. This is the only place the gate is narrated; the FE does NOT re-derive it.
  - **Do NOT** copy `totalReturn`/`sharpe`/`numTrades`/`maxDrawdown`/`wfe`/`symbol`/`timeframe` into the leaderboard entry — those are canonical values already served on the `iterationHistory` node; the FE reads them from there by `iterationId` (single fetch path, no duplication).
  - The leaderboard's **best is NOT a new field** — the FE marks "best" by `entry.iterationId === autoRun.bestIterationId` (the ONE canonical best marker). Do not introduce a second best definition.
  - Dedup: a family promoted to PROMOTE appears as its **promote** node (its validated evaluation); screened-only families (never promoted) appear as their **screen** node. Do not list both the screen node and its promoted child for the same family.
- [ ] **Bounded optional `promote_k` enabler.** Add `promote_k: Optional[int]` to `CreateAutoSessionRequest` (`auto_session_routes.py:77`), validated to the inclusive range **1–3** (reject otherwise with **422** + clear message), default → `DEFAULT_PROMOTE_K` (1) when omitted. Thread it through `_build_config` (`auto_session_routes.py:178`) → a new field on `AutoSessionConfig` (`auto_session.py:332`). In `_run_open_universe`, `k = min(config.promote_k or DEFAULT_PROMOTE_K, n_screened)` (the `k < n_screened` / budget-gated-per-promote invariants are PRESERVED). When omitted, behavior is **byte-identical to today** (J-12/J-13/J-14 hermetic tests set no `promote_k`). This lets a J-16 run promote ≥2 candidates so a real WFE-failing-but-higher-return candidate can sit in the leaderboard, not be best. The pinned path (`_run_inner`) ignores `promote_k`.
- [ ] **No change to** the `RobustScorer`, `BudgetTracker`, the SCREEN/PROMOTE staging mechanics (cheap-no-WF SCREEN, stronger-model+WF PROMOTE), the best-marking definition (`select_best(promoted)`, WFE-gated), the seed bounds (`SEED_SYMBOLS`/`SEED_TIMEFRAMES`/`SEED_UNIVERSE_MAX`), or `shared/contracts.py`. The leaderboard is a read-only projection of values the loop already computes; building/persisting it adds **zero** LLM tokens (J-13 budget unaffected) and MUST NOT block the event loop.

### Frontend

- [ ] **New leaderboard component** (e.g. `apps/frontend/src/components/AutoSessionLeaderboard.tsx`), rendered inside `IterationPanel.tsx` after `AutoSessionStatusStrip` and before the iteration tree, shown only when `autoRun?.leaderboard` is non-empty. It:
  - reads `autoRun.leaderboard` and, per entry, **joins** to the matching `iterationHistory` node (by `iterationId`) for the display metrics (`symbol`/`timeframe` from `params`, `totalReturn`, `sharpe`, `numTrades`, `maxDrawdown`, `walkForwardResult.wfe`) — **never recomputes the robust score** (reads `entry.robustScore` verbatim);
  - ranks rows by `robustScore` descending (sorting/formatting only — not recomputation);
  - **highlights the best** row where `entry.iterationId === autoRun.bestIterationId` (a clear "BEST" marker, consistent with the existing best badge styling);
  - shows per row: family (`SYMBOL TIMEFRAME`), stage badge (SCREEN/PROMOTE), robust score, total return, WFE (using the established emerald ≥0.5 / amber ≥0.3 / red <0.3 chip; `—` for screen rows with no WFE), num-trades, max-drawdown, and the `gatingReason` (so a higher-return non-best candidate visibly shows WHY it isn't best);
  - has appropriate empty/placeholder treatment (no leaderboard yet / run not started) and is responsive within the right panel (and under the mobile "Iterations" tab).
- [ ] **Type extensions only** (additive): add `leaderboard?: LeaderboardEntry[]` to `AutoRunStatus` and a `LeaderboardEntry { iterationId: string; stage: 'screen' | 'promote'; robustScore: number | null; eligible: boolean; gatingReason: string }` interface in `apps/frontend/src/lib/sessionApi.ts`. No change to the heavy/lazy fetch model; the leaderboard rides the existing `GET /api/sessions/{id}` poll the UI already does (live updates without reload — J-08; survives reload — J-10).
- [ ] Use the established dark analytical-workstation styling (Tailwind tokens, the existing Card/Badge patterns, Lucide icons, emerald/red/amber semantics) — match the existing panels; no raw hex outside the palette, no ad-hoc spacing.

### New user-facing capability
After an automated run, the user sees a ranked **leaderboard** of evaluated candidates in the Iterations panel and can tell at a glance that the chosen best is the walk-forward-validated, WFE-passing strategy — and that a flashier higher-raw-return candidate was rejected (with the reason: WFE below threshold, over-leveraged, or screened-only/not validated).

### New information displayed
A multi-row leaderboard: per candidate — family, stage, **canonical robust score**, total return, WFE (color-graded), trades, max-drawdown, and a **gating reason**; the marked best highlighted.

### New user actions
None beyond the new optional `promote_k` field on the existing `POST /api/auto-sessions` request. No new button/screen; the leaderboard is read-only display under the existing Iterations panel.

### UI surface changes
A new leaderboard panel inside the right-hand **Iterations** panel (its home already exists in the blueprint IA: "J-16 … Best badge / leaderboard → Right — Iterations"). No nav-skeleton change.

### Product surface delta
The optimizer's overfit-gating decision becomes **transparent**: the robust objective is no longer just a hidden best-marker — the user sees the full candidate competition and why the robust (not the highest-raw-return) strategy won. This realizes the goal's "skeptical, evidence-driven" mood and the J-16 "robust objective gates overfit" capability.

### Blueprint conformance
No new screen and no nav-skeleton change → **no re-approval required**. Additive Data-Contract edit only: the existing "Robust objective score + best marker" row (`blueprint.md`) is EXTENDED to register that the per-candidate robust score + eligibility + gating reason are now served in `autoRun.leaderboard` by the **same** `RobustScorer` via the **same** `GET /api/sessions/{id}`, read verbatim by the FE leaderboard, with the best entry identified by the **one** `bestIterationId` (no second best definition). The open-universe row gets a one-clause note that the bounded optional `promote_k` (1–3, default 1) governs how many candidates are promoted/walk-forward-validated for the leaderboard.

### Data-contract additions
**One extension to an existing row (not a new value family):** per-candidate `robustScore` + `eligible` + `gatingReason`, served in `autoRun.leaderboard`. Computed ONLY by the registered single `RobustScorer`/`is_eligible` (`apps/backend/backend/auto_session.py`), served ONLY by the registered `GET /api/sessions/{id}`. The FE reads them verbatim and joins to the already-registered `iterationHistory` metrics by `iterationId` — it introduces **no** second computation, no second endpoint, no duplicated metric, and no second best definition.

## OUT OF SCOPE

- Any change to `shared/contracts.py` (frozen), the `RobustScorer` formula/thresholds, the `BudgetTracker`, the SCREEN/PROMOTE staging mechanics, or the `select_best` best-definition.
- A second/parallel store, a new endpoint, or a new activity type for the leaderboard (it rides `autoRun` on the existing `GET /api/sessions/{id}`; the SCREEN/PROMOTE/WARM-START activity entries from J-14/J-15 are unchanged).
- Recomputing or re-deriving the robust score (or the gating reason) in the front-end — the FE reads canonical served values only.
- Expanding the seed universe or fanning out exchange-wide — `promote_k` reprioritizes how many *already-screened, in-seed* candidates are promoted (bounded ≤3), never adds new symbols.
- Multi-objective / Pareto optimization (single robust scalar objective remains).
- The pinned path (`_run_inner`) — J-16 is open-universe only; pinned runs ignore `promote_k` and need no leaderboard change.
- A `browser-qa-phase.sh` harness rewrite as product scope — fixing its port detection is a **separable, encouraged** framework fix (see NOTES); commit it separately if a maintainer does it. But browser-QA of the leaderboard is NOT optional this iteration (see DoD).

## DEFINITION OF DONE

- [ ] **0. PERSISTENCE GATE (LOAD-BEARING — the reason iter-5 failed; verify BEFORE writing the handoff; now FE-inclusive).** The J-16 code MUST exist in *this* working tree, not only in a worktree or a green test cache:
  - `git diff --stat HEAD -- apps/` is **non-empty** and includes the backend changes (`apps/backend/backend/auto_session.py`, `apps/backend/backend/auto_session_routes.py`), the **new FE leaderboard component** (`apps/frontend/src/components/AutoSessionLeaderboard.tsx` or equivalent), the FE type/data-layer edits (`apps/frontend/src/lib/sessionApi.ts`, and `IterationPanel.tsx` wiring), and the new J-16 test file(s).
  - `runs/goal-financial_free-iter-7/status.json` has `changed_files` **non-empty** and `tests_run: true`.
  - The dev handoff at `docs/handoffs/goal-financial_free-iter-7-dev.md` exists and its "Files Changed" list matches `git diff --name-only HEAD -- apps/`.
  - If any work was done in an isolated worktree, it MUST be merged back into the pipeline's working tree before this gate is checked. **A green pytest cache is NOT evidence the code landed.** Downstream review/QA/audit MUST treat an empty `apps/` diff (or a missing FE component) as an automatic FAIL.
- [ ] **1. J-16 passes — BOTH layers required (endpoint-only does NOT close a new render path):**
  - **Endpoint/data:** `GET /api/sessions/{id}` → `autoRun.leaderboard` contains per-candidate `{iterationId, stage, robustScore, eligible, gatingReason}`; the marked best (`bestIterationId`) is WFE-gated and derives from walk-forward OOS; a higher-raw-return candidate that is WFE-failing (or over-leveraged / screened-only) is present in the leaderboard with `eligible:false` (or screened stage) and is **NOT** `bestIterationId`.
  - **Browser/pixel (LOAD-BEARING):** the leaderboard component is verified **rendering in a real browser** (foreground, uncontended tab; FE health-probed on its actual offset port): the ranked rows display, the best row is highlighted, WFE chips are color-graded, and the higher-return non-best candidate visibly shows its gating reason. Capture evidence screenshots. This MUST be a genuine render verification — not an endpoint substitute.
- [ ] **2. Required-still-passing journeys remain green** — especially **J-09** (best == the one `bestIterationId`, WFE-gated), **J-12** (≥2 distinct configs from the bounded seed), **J-13** (token/USD/`max_configs` hard-enforced; leaderboard adds 0 tokens), **J-14** (SCREEN cheap-no-WF, PROMOTE k<n_screened on stronger model + WF, best from promoted only). Their existing hermetic tests (which set no `promote_k`) MUST pass **unchanged** under the default.
- [ ] **3. No anti-goal violation:** exactly ONE `RobustScorer` + ONE `BudgetTracker` (no new construction in the diff); the leaderboard score is `RobustScorer.score()` output (no FE recompute, no second scorer); best is the one `bestIterationId` (no second best definition); `shared/contracts.py` NOT in the diff; the open path does NOT eagerly parse `result.json`/`rating.json` (leaderboard built from in-memory metrics + persisted in `autoRun`); bounded seed preserved; budget honored; no new infra; no secrets in the leaderboard/gating strings; event loop non-blocking.
- [ ] **4.** Unit/integration tests pass; the full hermetic backend suite is green except the single known pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip`. Frontend builds/lints clean.
- [ ] **5.** Dev handoff written at `docs/handoffs/goal-financial_free-iter-7-dev.md`; the 6 UI-visibility artifacts are produced (this is a user-facing frontend change); `git diff` reconciled with the handoff.

## TESTING REQUIREMENTS

- **Persistence (run FIRST, gates everything):** record the DoD-0 checks against the live tree (`git diff --stat HEAD -- apps/` non-empty with the backend + FE component + FE types + tests; `status.json.changed_files` non-empty + `tests_run:true`). QA/audit re-run them.
- **Browser (LOAD-BEARING — must not be skipped; J-16 is a NEW render path):** with a seeded/triggered open-universe run, open the session in a real foreground browser (FE on its actual offset port — fix `browser-qa-phase.sh`'s `:3000`-vs-offset-port probe, or run a manual uncontended window with health re-probing). Verify the leaderboard renders: ranked candidate rows, the best highlighted, color-graded WFE chips, and a higher-return non-best candidate showing its gating reason. Keep the tab foreground (avoid the documented hidden-tab render throttle). Save evidence screenshots. **A 5th endpoint-only substitute is NOT acceptable for this journey.**
- **Endpoint/display:** assert the served `autoRun.leaderboard` shape + that the FE join (leaderboard ⨝ iterationHistory by `iterationId`, best via `bestIterationId`) yields a correct ranked view; the best is WFE-gated and equals `bestIterationId`.
- **Unit/integration (hermetic, no live LLM — inject a fake pipeline):**
  - **canonical-score:** every `leaderboard[*].robustScore` equals `RobustScorer.score(metrics)` for that candidate (assert against the one scorer); a grep of the diff finds **no** new `RobustScorer(...)` or `BudgetTracker(...)` construction.
  - **overfit-gating (the binding J-16 assertion):** construct (via the fake pipeline + `promote_k=2`) a promoted set with candidate A = higher raw return + `wfe < 0.3` and candidate B = lower raw return + `wfe ≥ 0.3`; assert `bestIterationId == B`, A is in `leaderboard` with `eligible:false` + a `gatingReason` citing WFE, and A (higher return) is NOT best. Add an over-leveraged variant: a high-return `margin_called` candidate → `eligible:false`, `gatingReason` cites over-leverage, not best.
  - **gating-reason correctness:** each `gatingReason` string matches the `is_eligible` outcome (WFE-fail / margin-called / below-trades-floor / screened-only / lower-score / best).
  - **best == bestIterationId:** the leaderboard entry the FE would mark best (`iterationId == bestIterationId`) is the WFE-gated `select_best(promoted)` result — no separate best field is served.
  - **no-regression (lock J-12/J-14):** with `promote_k` omitted (default 1), SCREEN ordering, the `wfv` pattern (`[F,F,…,T]`), and the marked best are **byte-identical to HEAD**; J-13 budget tallies unchanged (leaderboard adds 0 tokens).
  - **promote_k validation:** out of `[1,3]` → **422**; omitted → default 1; `k = min(promote_k, n_screened)` and budget-gated per promote (a cost cap still halts mid-promote).
  - **no eager parse + reload survival:** monkeypatch `read_iteration_full` to raise and assert `GET /api/sessions/{id}` still returns `autoRun.leaderboard` (built from in-memory metrics, persisted in the `autoRun` block of `session.json`); re-read after a simulated worker restart and assert the leaderboard persists.
  - **secrets:** leaderboard entries + gating strings contain no `api_key` / `sk-` material.
  - **FE (if component-test infra exists):** the leaderboard renders rows from a fixture `autoRun.leaderboard` + `iterationHistory`, ranks by `robustScore`, highlights `bestIterationId`, shows gating reasons, and reads `robustScore` from props (does NOT compute it). If FE unit infra is thin, the browser-QA step covers rendering — note which path was used.
- **Live (key-gated, optional — one cheap run):** open-universe run with `promote_k: 2` and a date range **≥ 9 months** (so PROMOTE walk-forward forms ≥1 window — iter-4 lesson) → the leaderboard shows ≥2 promoted candidates with the best WFE-gated. Non-blocking if no key; the hermetic overfit scenario is the binding proof.
- **Error cases:** `promote_k` outside `[1,3]` → 422; a run that reaches a terminal state with zero completed candidates (e.g. budget exhausted before SCREEN) → the FE shows an empty/placeholder leaderboard, no crash.

## NOTES

- **This is the FINAL journey.** When J-16 lands green, persists (DoD-0), and is pixel-verified, all 16 must-have journeys pass → the evaluator should consider **GOAL_ACHIEVED**.
- **Coherence is the central risk.** The single load-bearing rule: the leaderboard reads canonical `RobustScorer` values served by the one endpoint and marks best by the one `bestIterationId` — never a FE recompute, never a second best definition. The blueprint edit is an **additive extension** of the existing "Robust objective score + best marker" row (per-candidate granularity, same module, same endpoint), so it needs no re-approval. Keeping the leaderboard entry free of duplicated metrics (FE joins to `iterationHistory`) is what keeps the coherence-auditor's Step-1 "numbers don't match" gate green.
- **`promote_k` rationale.** A bounded (1–3), optional, default-1 knob is the minimal enabler that makes the WFE-gating demonstrable with real promoted candidates while keeping J-12/J-13/J-14 byte-identical (they omit it). It does not fan out the seed (anti-goal safe) and stays budget-gated per promote.
- **Pixel/browser-QA is load-bearing for the first time since the auto-session UI** (iter-6 lesson). Do NOT carry a 6th "pixel debt" deferral. The root cause is the harness FE port probe (`browser-qa-phase.sh` probes `:3000`; `./scripts/dev.sh` binds a deterministic offset port, e.g. `:3692`) — fix the probe (preferred, separable) or run a real uncontended foreground window. Per the headless-throttle memory: a blank Chrome-MCP page is the hidden-tab throttle, not an app bug — keep the QA tab foreground and uncontended.
- **Do NOT re-litigate** settled items: the eager-load anti-goal (resolved iter-1), the in-browser scorer/loop removal (done iter-2), and the single-`RobustScorer`/single-`BudgetTracker` coherence gate (re-confirmed iter-4/iter-6).
- **Carry-forward non-blockers (unchanged, out of scope):** pre-existing red `tests/test_directions_cache.py::test_write_and_read_full_round_trip`; flaky `test_post_returns_before_loop_completes_and_get_stays_responsive` (de-flake opportunistically); the out-of-scope `/health` probe still in the tree (release-manager to reconcile handoff/changed_files when the branch is committed); `auto_session.py` size (~1.3k lines — future refactor, not this iteration).
