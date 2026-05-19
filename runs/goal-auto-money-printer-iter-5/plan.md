# goal-auto-money-printer-iter-5 Execution Plan

**Single slice: J-15 — read-only global-history warm start + `history_scope` opt-out.**
Depth=full (evaluator-mandated, iter-4 eval + journey history). Builds directly on
iter-4's staged SCREEN→PROMOTE controller (the `_SEED_UNIVERSE` enumeration consumed by
`_run_staged_open_universe` is the named injection point) and the iter-3 durable file
store (read-only mining, no schema fork). Aligned with `docs/goal.md` J-15 + Success
Criterion "a second automated run with global history scope demonstrably warm-starts
from prior sessions and is opt-out-able" + Key Capability 11 (history surrogate). **No
scope drift.** J-16 stays OUT (invariant only *preserved* here).

**Core design (from spec, not negotiable): a deterministic read-only history surrogate
— NO LLM planner.** The acceptance is satisfiable cheaply and deterministically; the
spec explicitly says do NOT add an LLM planner call the acceptance does not require.
The "MUST NOT be re-sent uncached every round" anti-goal is satisfied structurally by
the once-per-run guarantee (no per-round re-mining), so **no `cache_control` code is
needed** (no LLM call exists to cache).

## What to Build

**Backend — `apps/backend/backend/auto_session.py` (dominant surface)**

- **Read-only global-history surrogate** (new dependency-light helper, e.g.
  `_mine_history(...)`): for every prior session in the existing durable store EXCEPT
  the current `session_id`, read promoted iterations and aggregate the **best
  `robustScore` per `(symbol, timeframe)` family**.
  - Use existing `session_store` read helpers ONLY: enumerate prior sessions via
    `session_store.derive_session_tabs()` (or list `BASE_DIR/live`), then per session
    `read_session_meta` + `list_iteration_dirs` + **`read_iteration_meta`** (lean —
    `meta.json` already carries `params.symbol`, `params.timeframe`, `stage`,
    `walkForwardResult`, `robustScore`; `read_iteration_full` is NOT needed and would
    pull heavy `result/rating` — avoid it).
  - Filter to **promoted, walk-forward-bearing** iterations only:
    `stage == "promote"` AND non-null `walkForwardResult` AND a usable `robustScore`.
  - Read-only: **no** write/rename/delete/in-place mutation of any prior artifact.
    Best-effort: a missing/corrupt session or iteration dir is skipped (mirror the
    SCREEN/PROMOTE `except` discipline) — mining never raises out or hangs the run.
  - This is a one-time server-side read at run start — it MUST NOT make
    `GET /api/sessions/{id}` eager (separate path; the list/open path is untouched).
- **`history_scope` effective semantics** (replace iter-4 accept-&-persist-only,
  documented inline replacing the stale `auto_session.py:1565-1568` "J-15/OUT" comment):
  - `"global"` → warm-start ON.
  - `"this-run"` → opt-out: NO mining, NO citation, fixed `_SEED_UNIVERSE` order
    **byte-identical** to today's pre-iter-5 enumeration.
  - omitted / `null` (default) → treated as **effective `"global"`** warm-start. The
    raw supplied value still persists verbatim (`null` stays `null` in `historyScope`);
    the *effective* resolved scope is recorded as an **additive** key in the existing
    `autoRun` dict (e.g. `effectiveHistoryScope`) via the existing `_update_autorun`
    (no schema fork — mirrors iter-4's additive `stage`).
  - Unknown/garbage value → clean default (no 500); resolve to the safe default
    (treat like the default → effective `"global"`), do not raise.
- **Warm-start reorder** of the open-universe seed enumeration: when warm-start is
  active, return `_SEED_UNIVERSE` as a **stable permutation** ordered by mined family
  strength (strongest historical `(symbol, timeframe)` first; deterministic stable
  tie-break that preserves the existing fixed seed order for unseen/tied families).
  MUST remain a permutation of the **same bounded seed universe** —
  `set(order) == set(_SEED_UNIVERSE)`, no new symbols/timeframes, no fan-out.
- **Planner-decision activity entry** (only when warm-start active AND usable prior
  history exists): exactly one `_activity(...)` entry appended via the existing
  `session_store.append_activity_entries`, emitted **once, before the SCREEN loop** so
  it renders at the top of the existing feed. Plain operator language citing the
  concrete prior evidence, e.g. `"Warm start (global history): prioritising BTC/USDT
  4h — prior best robust 0.78 across 2 prior session(s)"`. **No API keys/secrets**;
  same entry shape the existing feed already renders (UI-indistinguishable from a
  manual run). When `"this-run"` or no usable prior history → **no** such entry.
- **Once-per-run, off-thread.** Mine + reorder + citation happen **exactly once** at
  run start via `asyncio.to_thread` (off the event-loop thread — iter-2 lesson; the
  same pattern `_update_autorun`/`append_activity_entries` use). Recommended site:
  `_run_auto_session_impl` immediately after `_config_plan` (line ~1293) and before
  the `if is_open:` branch (line ~1317) — open-universe ONLY. NOT recomputed per
  round/SCREEN/PROMOTE candidate. The reordered `configs` list is then passed into
  the unchanged `_run_staged_open_universe` exactly as today.
- **Invariants preserved (no behavioural change beyond ordering):**
  - No-prior-history / empty store / opt-out → enumeration **byte-identical** to
    today's fixed `_SEED_UNIVERSE`; J-12/J-13/J-14 paths unchanged.
  - Robust-best unchanged: `select_best`/`robust_score` over **promoted** iterations
    only; warm-start changes SCREEN *order*, never selection (J-09/J-16 intact).
  - Pinned path (J-07–J-11) byte-unchanged: no mining, no reorder, no citation
    (warm-start is open-universe-only; guard on `is_open`).
  - Cost tracker untouched: no LLM tokens added (surrogate-only); round-top
    `would_exceed()` gating and the `"max-configs"`-vs-spend-cap distinction
    (`_SPEND_CAPS`) unchanged; a surrogate-only run still must not start work past a
    reached cap.
  - `shared/contracts.py`, `sandbox.py`, `pipeline.py`, `backtest/` untouched.

**Frontend — conditional, verify-first**

- None expected: the existing activity feed renders arbitrary entries verbatim
  (`ActivityLogEntry.tsx`, proven iter-2/iter-4). Modify a frontend file **only if**
  the existing renderer flattens/truncates so an operator cannot read the
  planner-decision citation — then a *minimal additive* text-preserving tweak (no new
  component, no second in-browser loop). Do not add frontend the acceptance does not
  require.

## Agents Required

- developer: **yes** — backend read-only history surrogate + effective `history_scope`
  semantics + once-per-run off-thread warm-start reorder + planner-decision citation;
  new + consciously-updated tests; frontend ONLY the conditional minimal tweak if the
  feed flattens the citation (verify first). Single TDD pass; backend dominant.
- Full 11-step pipeline (UI impact → UI test design → browser-qa → ux-regression →
  audit → closure): depth=full — cross-run state touching the open-universe
  controller, durable file store (read-only), cost tracker, and activity feed, and
  activating three load-bearing cross-run anti-goals.

## Frontend Present
yes

> **Flagged spec/framework reconciliation (orchestrator surfaces, does not silently
> resolve):** the spec's machine line reads `Frontend Present: no (code)` but the
> *same line* states "browser-qa MUST verify the planner-decision entry renders", and
> DEFINITION OF DONE + TESTING REQUIREMENTS **mandate** browser-qa for J-15 (citation
> visible on a `"global"` run, absent on a `"this-run"` run, screenshots). This
> `Frontend Present:` line is machine-read by `qa-phase.sh` to decide whether browser
> checks run; `no` would **skip the very browser QA the spec requires**. Per the
> orchestrator rule ("if the phase adds any user-facing data, Frontend Present MUST be
> yes") and the unbroken iter-1→iter-4 precedent (all `yes` for this same
> additive-activity-feed situation), this is **`yes`**. "no (code)" means *no new
> frontend code is expected* — NOT that browser QA is skipped. The developer is not
> required to write frontend code (conditional clause above); browser-qa IS required.

## Files to Create/Modify

- `apps/backend/backend/auto_session.py` — read-only `_mine_history` surrogate;
  effective `history_scope` resolution (`"global"` / `"this-run"` / default→global /
  garbage→default) replacing the accept-&-persist-only comment at ~1565-1568; stable
  permutation reorder of `_SEED_UNIVERSE`; once-per-run off-thread mine+reorder+citation
  in `_run_auto_session_impl` (open-universe only, before SCREEN); additive
  `effectiveHistoryScope` key on the `autoRun` block. Pinned path / cost tracker /
  `select_best` untouched.
- `apps/backend/backend/session_store.py` — **read-only reference** (reuse existing
  helpers; do NOT add a parallel store, schema fork, or new write path).
- `apps/backend/tests/test_auto_session.py` — **extend, do not duplicate** (deterministic,
  tiny budgets, isolated `store` fixture + `FakePipeline`):
  - Warm-start reorder: seed a prior session whose promoted best family is F1 (write
    via the real store path); assert run #2's resolved SCREEN enumeration places F1
    first AND `set(order) == set(_SEED_UNIVERSE)`; assert the first **promoted**
    config's family == F1.
  - Opt-out: `"this-run"` → SCREEN order byte-identical to fixed `_SEED_UNIVERSE`;
    **no** planner-decision entry; no cross-run influence even with prior history.
  - Default→global: omitted `history_scope` + prior history → warm-start active
    (citation present, reorder applied); raw persisted `historyScope` still `null`,
    *effective* scope observable.
  - **Read-only proof:** snapshot a content hash (+ mtime) of every prior-session
    file before run #2; assert byte-identical after — no mutate/delete/rename.
  - **Once-per-run:** miner call-count == 1 per run (not per SCREEN/PROMOTE candidate).
  - No-history fallback: empty store → enumeration == today's fixed `_SEED_UNIVERSE`;
    keep `test_open_universe_*`, `test_max_configs_cap_*`,
    `test_pinned_path_unchanged_by_open_universe_addition` GREEN unchanged.
  - Robust-best: a historically-favoured family that promotes worse is NOT selected
    best (warm-start changes order, not selection).
  - Error cases: garbage `history_scope` → clean default, no 500; corrupt prior
    session dir skipped, run still reaches a terminal state.
  - **Consciously update (NOT loosen) to the new effective semantics; correct the
    stale "J-15/OUT" comments:** `test_open_universe_objective_and_history_scope_persisted`
    (persistence still asserted; `"this-run"` behaviour — no citation/no reorder — now
    asserted) and `test_history_scope_defaults_to_none_when_omitted` (raw `historyScope`
    still `null`; effective scope now `"global"` + warm-start observable).
- `apps/frontend/src/components/*` — **only if** the activity feed flattens the
  citation (verify first); minimal additive text preservation, no new component, zero
  in-browser loop change.

## UI Evolution
- New user-facing capability: a second open-universe run with `history_scope:
  "global"` (or default) visibly learns from prior runs — it prioritises the
  historically strongest `(symbol, timeframe)` families and shows *why* in the
  existing session activity feed; `"this-run"` opts out entirely.
- New information displayed: one planner-decision entry in the existing session
  activity feed citing the prior-session performance that drove the warm-start order
  (only on global-scope runs with usable history).
- New user actions: `POST /api/auto-sessions` with `history_scope: "global" |
  "this-run"` now changes behaviour (warm-start vs opt-out), not just persisted
  metadata. No new endpoint, no new control.
- UI surface changes: none structural — entry renders in the existing feed; a
  headless warm-started run stays UI-indistinguishable from a manual one.
- Navigation changes: none.

## Visual Requirements
- Component patterns: reuse the existing session activity feed list rendering; no new
  component. Any tweak preserves the citation text only.
- Layout: unchanged two-panel session view; no new region.
- Key visual effects: match the existing dense/dark/data-forward feed; no new effects.
- States to handle: global run with usable history (citation present) vs global
  with empty store (no citation, graceful) vs `"this-run"` (no citation); legacy /
  pinned / opt-out sessions show NO planner-decision entry (feed unchanged).

## Key Test Scenarios
- **J-15 (browser, primary):** three tiny-budget open-universe runs against ONE
  shared isolated store — Run #1 (default/global, no prior history) produces a
  promoted best in a known family F1; Run #2 (`history_scope: "global"`) → activity
  feed shows the planner-decision entry citing run #1's performance AND F1 is the
  first promoted family; Run #3 (`history_scope: "this-run"`) → NO
  planner-decision/warm-start entry, fixed seed order. Screenshot the run #2 citation
  and the run #3 absence.
- **Regression (browser, re-verify live — not carried headline):** J-02 (prior run
  history browse unaffected — iter-0 lesson), J-08 (live status), J-12 (≥2 distinct
  configs), J-13 (`budget-exhausted` + durable spend), J-14 (SCREEN→PROMOTE staging).
- **Unit/integration:** `cd apps/backend && .venv/bin/python -m pytest` — all new +
  updated tests GREEN, assert exact values, no skip/xfail. Baseline: iter-4 finished
  **188 passed / 1 failed**; the ONLY tolerated red remains the pre-existing
  out-of-scope `test_directions_cache.py::test_write_and_read_full_round_trip` —
  **zero new regressions**. Frontend `npm run build` EXIT 0 only if a frontend file
  is touched.
- **Anti-goal proofs:** before/after content-hash assertion (read-only); opt-out
  honored; bounded-seed permutation only; once-per-run (call-count==1); budget /
  robust-best / pinned invariants intact; no secrets in any entry/artifact.

## Out of Scope (exclude — flagged to prevent scope creep)
- **J-16** deep overfit-gating demonstration / leaderboard — next iteration; the
  robust-best invariant is only *preserved* here.
- Any bandit/Thompson/UCB/exploration policy beyond a deterministic best-family-first
  reorder of the bounded seed (single-robust-scalar Non-Goal; no fan-out).
- Any LLM planner call (spec design decision: deterministic surrogate only — do not
  add an LLM call the acceptance does not require; if one were added it would have to
  carry `cache_control` + drain `_drain_usage`, but it is NOT to be added).
- Any new datastore/index/vector store/queue/scheduler/broker, schema fork, or
  migration of prior artifacts; any mutation/compaction/back-fill of prior sessions.
- Mining or warm-starting on the **pinned** path.
- Any change to `shared/contracts.py`, `sandbox.py`, `pipeline.py`, the backtest
  engine/fills/metrics/determinism (`git diff HEAD --` of these MUST be empty).
- Re-tuning `select_best`/`robust_score`; multi-objective/Pareto.
- Reintroducing any in-browser iterate loop.

## Assumptions (documented per token policy — not blocking)
- The history surrogate is **deterministic, read-only, no LLM** (spec's explicit core
  design decision). No `cache_control` code is required because no LLM planning call
  exists; the prompt-caching anti-goal is satisfied structurally by the once-per-run
  guarantee. If the developer believes an LLM planner is unavoidable, STOP and flag —
  it is not, per the spec.
- Mining data source = each prior session's per-iteration `meta.json` via
  `read_iteration_meta` (carries `params.symbol/timeframe`, `stage`,
  `walkForwardResult`, `robustScore`) — the lean read; `read_iteration_full` is not
  needed and is avoided to keep mining cheap and the list/open path uneager.
- "Family" = `(symbol, timeframe)` tuple; "strength" = max persisted `robustScore`
  over that family's promoted, WF-bearing prior iterations. Tie / unseen family →
  preserve the existing fixed `_SEED_UNIVERSE` order (stable sort).
- Effective-scope key name (e.g. `effectiveHistoryScope`) and the precise
  planner-decision wording are the developer's choice within: additive `autoRun` key
  only (no schema fork), plain operator language, no secrets, renders in the existing
  feed.
- Recommended once-per-run site is `_run_auto_session_impl` post-`_config_plan` /
  pre-`if is_open:`; an equivalent once-at-top-of-`_run_staged_open_universe`
  placement is acceptable if the once-per-run + off-thread + open-universe-only +
  before-first-SCREEN constraints all hold.
- Definition of Done also requires: dev handoff at
  `docs/handoffs/goal-auto-money-printer-iter-5-dev.md`; all 6 UI visibility
  artifacts; phase-closure gate passes.
- **Reconciled-UI-test-headline caution (iter-1 lesson, for the evaluator):** if
  `ui-test-results.md` is QA-FAIL→fix→reconciled, do NOT trust the top headline —
  cross-check the post-fix source diff + QA full-mode re-verification (the read-only
  content-hash proof, the opt-out absence, and the citation-present assertions).
- **Outer-loop carryover (NOT iter-5 dev/source/test work):** per the iter-4
  evaluator, iter-4's transient closure trip needs the outer loop to run
  `./scripts/automation/ui-test-design-phase.sh goal-auto-money-printer-iter-4` then
  `./scripts/automation/phase-closure-check.sh goal-auto-money-printer-iter-4`.
  Recorded here so it is not lost; it implies **no** code/test/journey work in iter-5
  and MUST NOT flip any journey/anti-goal verdict.
