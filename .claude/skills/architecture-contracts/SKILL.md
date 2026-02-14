# Skill: Architecture Contracts

## Purpose

Define system architecture, module boundaries, frozen data contracts, and API schemas for the Finovae Strategy Platform. This skill is used by **A1 (Architecture Lead)** to maintain structural integrity across all modules.

The platform's data contracts live in `shared/contracts.py` and are marked **FROZEN**. They define the canonical data shapes that every module -- compiler, codegen, sandbox, backtest engine, API layer, and frontend -- depends on. Changing a contract is a high-impact operation that can break multiple subsystems simultaneously.

## Do

- Design contracts as Python `dataclasses` with explicit type annotations for every field.
- Use `frozen=True` on value-object dataclasses (`OHLCV`, `Trade`, `EquityPoint`) to enforce immutability.
- Define clear module boundaries: `data/` owns fetching and validation, `strategy/` owns compilation and codegen, `backtest/` owns execution and metrics, `backend/` owns API and orchestration, `shared/` owns contracts and schemas.
- Version contract changes explicitly. Every modification to `shared/contracts.py` must include an updated `Frozen Date` comment and a changelog entry in the PR description.
- Document all fields with docstrings that specify units (e.g., "USDT", "decimal percentage"), value ranges, and semantics.
- Use `str` enums (`class TradeType(str, Enum)`) so contracts serialize cleanly to JSON.
- Validate that new fields have sensible defaults to preserve backward compatibility with existing callers.
- Propose contract changes as a diff against the current frozen file, never as a full rewrite.
- Map every API endpoint response to a Pydantic schema in `shared/schemas.py` that mirrors the contract dataclasses.

## Don't

- Modify `shared/contracts.py` without explicit A0 (Orchestrator) or lead approval.
- Add fields that break backward compatibility -- existing consumers must continue to work without code changes.
- Create circular dependencies between modules. The dependency graph must remain: `shared` <- `data` <- `strategy` <- `backtest` <- `backend`.
- Introduce runtime imports between peer modules (e.g., `backtest/` must not import from `strategy/` directly; communication goes through contracts).
- Use `Any` or `dict` as field types in contracts -- every field must have a concrete type.
- Remove or rename existing contract fields (deprecate with a default value instead).
- Define contracts outside of `shared/contracts.py` -- all cross-module types live in one file.

## SOP (Standard Operating Procedure)

### 1. Review Existing Contracts

```bash
# Read the current frozen contracts
cat shared/contracts.py

# Check all modules that import from contracts
grep -r "from shared.contracts import" --include="*.py" .
grep -r "from shared import contracts" --include="*.py" .
```

### 2. Analyze Impact of Proposed Change

```bash
# Identify every file that uses the contract being modified
grep -rn "BacktestResult\|StrategySpec\|OHLCV\|Trade\|EquityPoint" --include="*.py" .

# Check API schemas that mirror contracts
cat shared/schemas.py

# Check frontend types that consume API responses
grep -rn "BacktestResult\|StrategySpec" --include="*.ts" --include="*.tsx" frontend/src/
```

### 3. Propose Change as Diff

```bash
# Create a branch for the contract change
git checkout -b contract/description-of-change

# Make the change in shared/contracts.py
# Update the Frozen Date comment
# Update shared/schemas.py if API-facing

# Verify no import errors
python -c "from shared.contracts import *; print('Contracts OK')"
```

### 4. Validate Backward Compatibility

```bash
# Run the full test suite to catch breakage
pytest -v

# Specifically run contract-sensitive tests
pytest tests/test_determinism.py -v
pytest tests/test_lookahead.py -v
pytest tests/test_sandbox.py -v

# Type check the entire codebase
mypy .
```

### 5. Submit for Approval

- Open a PR with the contract diff, an architecture decision record (ADR), and a dependency impact list.
- Tag A0 (Orchestrator) and all affected agent owners for review.
- Do not merge until all affected module owners acknowledge.

## Required Output Format

Every architecture-contracts task must produce:

### Contract Diff

```
File: shared/contracts.py
Frozen Date: YYYY-MM-DD (updated)

+ @dataclass
+ class NewContract:
+     """Description."""
+     field_name: type  # units, range, semantics
```

### Architecture Decision Record (ADR)

```
Title: ADR-NNN: <Short title>
Status: Proposed | Accepted | Rejected
Date: YYYY-MM-DD
Context: Why is this change needed?
Decision: What specific contract change is being made?
Consequences: Which modules are affected and how?
Migration: Steps for existing consumers to adapt (if any).
```

### Dependency Diagram

```
shared/contracts.py
  <- data/loader.py (uses OHLCV)
  <- data/validation.py (uses OHLCV)
  <- strategy/compiler.py (uses StrategySpec, CompileConstraints)
  <- strategy/codegen.py (uses StrategySpec, IndicatorConfig)
  <- backtest/engine.py (uses BacktestRequest, Trade, EquityPoint, BacktestResult)
  <- backtest/metrics.py (uses BacktestResult)
  <- backend/api.py (uses all request/response contracts)
  <- backend/pipeline.py (uses all contracts)
  <- frontend/src/ (consumes JSON serialized contracts via API)
```
