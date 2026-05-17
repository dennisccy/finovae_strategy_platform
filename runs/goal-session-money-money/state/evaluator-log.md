## Iteration 0 — goal-money-money-iter-0

**Verdict:** CONTINUE
**Date:** 2026-05-17T23:10:05Z
**Depth dispatched:** lean
**Journey deltas:**
- Newly passing: none (fresh baseline — J-01, J-02, J-03, J-04, J-06 seeded `already_passing`)
- Newly failing: J-05 (frontend never calls `/api/symbols` & `/api/timeframes`; Symbol free-text, Timeframe static buttons)
- Regressed: none (journey-history was empty — nothing to regress from)
- Anti-goal violations: 3, all PRE-EXISTING, severity `minor` (halt-sense), not introduced this iter — (a) per-day CSV OHLCV fan-out `loader.py:63`; (b) `/tmp` code defaults `session_store.py:26` & `directions_cache.py:23` (runtime-masked by `.env`); (c) eager 51 MB session open-path `session_routes.py:150-156`

**Reasoning:** Verify-only baseline, zero source diff (independently confirmed under `apps/`/`scripts/`/`incredible_auto_dev/`). 5/6 Must-have journeys pass end-to-end against the unmodified codebase, corroborated by screenshots + cross-checked (incl. md5 — J-03/J-04 share one byte-identical capture that legitimately shows both panels). J-05 is a real, tractable frontend wiring gap. All 3 anti-goal postures corroborated at cited file:line + runtime byte evidence; pre-existing, not iteration-introduced, and not in the REGRESSION critical set — so CONTINUE, not REGRESSION (an empty baseline cannot regress; halting it would block the remediation it exists to enable).

**Next-step recommendation:** Next iter at **full** depth (anti-goal remediations are data-layout/open-path changes, regression-prone to the 5 passing journeys → pin J-01/J-02/J-03/J-04/J-06 required-still-passing). Priority: (1) single-file Parquet OHLCV cache replacing per-day CSV fan-out; (2) flip `BACKTEST_STORE_DIR`/`DIRECTIONS_CACHE_DIR` code defaults off `/tmp` (do not rely on `.env`); (3) make `GET /api/sessions/{id}` lazy; (4) wire J-05 Symbol/Timeframe controls to the reference endpoints (lowest risk).
