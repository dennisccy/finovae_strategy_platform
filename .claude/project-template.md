## PROJECT GOAL

All agents must read `docs/goal.md` before starting any phase.

---

## PROJECT

Name: Finovae Strategy Platform
Description: AI-assisted crypto strategy lab — natural language → `StrategySpec` → generated `signal()` code → RestrictedPython sandbox → Binance backtest → metrics/rating → optional walk-forward validation → AI insights. No database; Parquet OHLCV cache + file-based session/run store. See `docs/goal.md` for the full vision, must-have user journeys (J-01..J-05), and anti-goals.
Repository: https://github.com/dennisccy/finovae_strategy_platform

---

## STACK

Backend:
Language: Python 3.11+
Framework: FastAPI
ORM/DB lib: none (no database by design)
Migrations: N/A
Test runner: pytest
Package mgr: pip (`pip install -e .` from `pyproject.toml` + `requirements.txt`)
Venv/env: apps/backend/.venv

Frontend:
Enabled: yes
Framework: Vite + React 18 (NOT Next.js — the shared Aplhion scripts call `next`, satisfied by the local `next-vite-shim` at `apps/frontend/tools/next-shim`)
Language: TypeScript
Styling: Tailwind CSS
Package mgr: npm

Database:
Type: none — Parquet OHLCV cache (`apps/backend/.cache/ohlcv/`) + file-based session/run store
Location: filesystem; cache/store dirs are configurable via backend env vars

Services:
Backend URL: http://localhost:8000 (offset port in dev via ./scripts/dev.sh)
Frontend URL: http://localhost:5173 (offset port in dev; Vite proxies `/api` → backend)
Health check: http://localhost:8000/api/health (also GET / and /docs)

---

## DESIGN SYSTEM

Component library: lightweight internal React components; keep minimal
Icon library: lucide-react
Charts: recharts (equity curve, drawdown overlay)
Visual style: modern analytical workstation, not a consumer trading app
Color mode: dark default; clean contrast, restrained accents
Layout: two-panel — left = NL strategy chat + parameter controls; right = equity chart + metrics + trades
Typography: clean modern sans serif suited to dense dashboards; strong hierarchy for metric cards and tables

---

## TEST COMMANDS

Backend tests: cd apps/backend && .venv/bin/python -m pytest
Frontend tests: cd apps/frontend && npm run lint  (no `npm test` yet — frontend validation relies on lint + browser QA)
Migrations: N/A (no database)
Lint: cd apps/backend && .venv/bin/ruff check . && cd ../frontend && npm run lint

Notes:
- The frontend has no unit-test runner yet; record that validation relies on `npm run lint` plus browser QA.
- Browser workflow checks via Chrome MCP are part of the expected QA path for frontend-touching phases.

---

## SERVICE START COMMANDS

Used by qa-phase.sh to auto-start services during QA validation.

Start backend: ./scripts/start-backend.sh
Start frontend: ./scripts/start-frontend.sh
Start both: ./scripts/dev.sh

---

## PHASE SPECS

Phase spec directory: docs/phases/
Phase spec naming: phase-<n>-<name>.md
Example: phase-2-strategy-intake.md

---

## ROADMAP

| Phase | Name | Status |
|-------|------|--------|
| phase-1 | Monorepo merge + automation harness foundation | Complete |
| phase-2+ | Future capability work (TBD) | Future |

Important roadmap rule:
- Do not let backend capability outpace UI discoverability for multiple phases in a row.
- Every new capability should result in new navigation, controls, pages, or explainers where needed.

---

## ARCHITECTURE PRINCIPLES

- Keep API routes thin; business logic belongs in services / the pipeline orchestrator.
- Separate compilation, code generation, sandboxing, data, backtest, metrics, and walk-forward into distinct modules.
- Frontend orchestrates workflows and presents results; it does not embed core trading logic.
- RestrictedPython sandbox isolation is non-negotiable: no file I/O, network, `exec`/`eval`, `__import__`, `open`, or `os`.
- No lookahead: a signal at bar `i` fills at bar `i+1` open. Backtests are deterministic (seeded slippage).
- `apps/backend/shared/contracts.py` is a FROZEN interface; changes require architectural review.
- AI providers (OpenAI/Anthropic) must remain swappable; the selectable model list is the single source of truth in `apps/backend/shared/model_catalog.py` (default `gpt-5.4-mini`, served by `GET /api/models`) — never hardcode model ids or leak model/cost assumptions into core logic.
- No database by design — favor reproducible, file-backed, inspectable artifacts.
- Backtest results must be reproducible from the stored spec + config + cached market data.

---

## DATA MODEL RULES

- Domain identifiers are string `run_id` / session ids; preserve provenance (source NL, spec, generated code).
- All timestamps stored and serialized in UTC.
- Backtest results reproducible from stored `StrategySpec` + `BacktestRequest` + cached OHLCV.
- The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
- Prefer soft archival / status transitions over destructive deletes for sessions and runs.

---

## GIT WORKFLOW

Branch naming: phase/<phase-id>
PR title format: feat: <phase-id> — <phase-name>
Main branch: main

Never commit:
- .env / .env.local / .env.*
- node_modules/
- dist/ / build/ / .next/
- .venv/ / venv/
- __pycache__/ / .pytest_cache/ / .ruff_cache/ / .mypy_cache/ / .cache/
- *.db
- ANTHROPIC_API_KEY / OPENAI_API_KEY or any credentials in any form

---

## NOTES FOR AGENTS

- The backend boots without API keys, but `/api/generate-strategy`, `/api/run-backtest`, and `/api/generate-insights` require `OPENAI_API_KEY` (default model `gpt-5.4-mini`) in `apps/backend/.env`; `ANTHROPIC_API_KEY` is only needed if a Claude model is selected.
- The `.venv` is a setup artifact and must never be committed.
- The frontend is Vite; the shared scripts run `npx next dev` which resolves the local `next-vite-shim`. Do not "fix" this by installing real Next.js.
- The two `.claude/` layers coexist: this Everything-Claude-Code plugin `.claude/` and the framework's `incredible_auto_dev/CLAUDE.md` (root symlink). If automation generates/symlinks framework files into `.claude/`, surface the collision to the operator rather than silently overwriting.
- QA should include user-point-of-view functional testing (Chrome MCP) for real workflows, not just unit/API tests.
- Where repo reality differs from this template, update this file rather than hard-coding assumptions into agent prompts.

---

## INTERNAL-ONLY ENDPOINTS

Internal-only endpoints (no navigable UI surface) are allowed only when documented here, naming the endpoint, its purpose, and why no UI surface is appropriate.

_None as of phase-1._
