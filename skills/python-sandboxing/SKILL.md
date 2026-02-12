# Skill: Python Sandboxing

## Purpose

Execute untrusted strategy code safely using RestrictedPython within the Finovae Strategy Platform. This skill is used by **A4 (Sandbox/Security Agent)** to maintain the sandbox execution environment (`backend/sandbox.py`) and ensure no user-generated or LLM-generated code can escape the security boundary.

The sandbox is the last line of defense. Even if the compiler or codegen produces unexpected output, the sandbox must prevent any harmful operations. It compiles code using `RestrictedPython.compile_restricted`, injects a controlled set of safe globals, and enforces execution timeouts.

## Do

- Use `RestrictedPython.compile_restricted` to compile all strategy code before execution. Never use the built-in `compile()` or `exec()` on untrusted code.
- Whitelist only these modules/objects in the sandbox globals: `numpy` (as `np`), `pandas` (as `pd`), `math` (standard library), `int`, `float`, `bool`, `str`, `list`, `range`, `len`, `abs`, `min`, `max`, `round`, `sum`, `enumerate`, `zip`.
- Enforce a 30-second timeout on every `signal()` call. On Unix, use `signal.SIGALRM`. On Windows, use a polling/thread-based fallback.
- Enforce memory limits where the platform supports it (e.g., `resource.setrlimit` on Linux).
- Log all execution attempts with: timestamp, run_id, code hash, success/failure, execution time, and any security violations.
- Return clear, actionable error messages when code is rejected. Indicate which specific construct was blocked (e.g., "Import statement blocked: os").
- Test the sandbox against a comprehensive escape test suite on every change.
- Keep the sandbox policy declarative and centralized in one file (`backend/sandbox.py`). Do not scatter security checks across modules.
- Validate that the `signal` function signature is `signal(df: pd.DataFrame, i: int) -> int` before execution.

## Don't

- Allow `__import__` or any form of dynamic importing. This includes `importlib`, `__builtins__.__import__`, and attribute access to `__import__`.
- Allow `open()`, file I/O of any kind, or any path-based operations.
- Allow `exec()`, `eval()`, or `compile()` within sandboxed code.
- Allow access to `os`, `sys`, `subprocess`, `socket`, `http`, `urllib`, `requests`, or any module that provides system or network access.
- Allow access to `__builtins__`, `__subclasses__`, `__bases__`, `__globals__`, `__code__`, or other dunder attributes that enable sandbox escape.
- Allow `getattr()`, `setattr()`, or `delattr()` with dynamic string arguments on non-whitelisted objects.
- Skip timeout enforcement. An infinite loop in user code must not hang the server.
- Allow the sandbox to silently fail. Every blocked operation must raise a `SecurityError` or equivalent that is logged and returned to the caller.
- Trust the codegen output. Even though we control the code generator, the sandbox must validate as if the code is fully untrusted.

## SOP (Standard Operating Procedure)

### 1. Review Current Sandbox Policy

```bash
# Read the sandbox implementation
cat backend/sandbox.py

# Check what globals are injected
grep -n "safe_globals\|_SAFE\|allowed\|whitelist" backend/sandbox.py

# Check timeout implementation
grep -n "timeout\|SIGALRM\|signal\." backend/sandbox.py
```

### 2. Run Sandbox Escape Test Suite

```bash
# Run all sandbox security tests
pytest tests/test_sandbox.py -v

# Expected: ALL escape attempts must be blocked
# If any escape test passes (i.e., malicious code executes), this is a critical security bug
```

### 3. Verify Blocked Operations

Test each of these operations individually and confirm they raise errors:

| Operation | Test Code | Expected |
|---|---|---|
| Import os | `import os` | SecurityError / CompileError |
| Import subprocess | `import subprocess` | SecurityError / CompileError |
| Dynamic import | `__import__('os')` | SecurityError |
| File read | `open('/etc/passwd')` | SecurityError |
| File write | `open('/tmp/x', 'w')` | SecurityError |
| Exec | `exec('print(1)')` | SecurityError |
| Eval | `eval('1+1')` | SecurityError |
| Network | `import socket` | SecurityError / CompileError |
| Dunder access | `().__class__.__bases__` | SecurityError |
| Getattr escape | `getattr(__builtins__, '__import__')` | SecurityError |
| Infinite loop | `while True: pass` | TimeoutError (30s) |
| Memory bomb | `x = [0] * (10**9)` | MemoryError or ResourceLimit |

```bash
# Run blocked operation tests
pytest tests/test_sandbox.py -v -k "blocked or security or escape"
```

### 4. Test Timeout Enforcement

```bash
# Verify timeout works on current platform
python -c "
import platform
print(f'Platform: {platform.system()}')
# Unix: SIGALRM-based timeout
# Windows: Thread-based polling timeout
"

# Run timeout-specific tests
pytest tests/test_sandbox.py -v -k "timeout"
```

### 5. Validate Legitimate Code Passes

```bash
# Ensure valid signal functions still execute correctly
pytest tests/test_sandbox.py -v -k "valid or legitimate or signal"

# Run a full pipeline test to verify sandbox doesn't block valid strategies
pytest tests/ -k "pipeline" -v
```

### 6. Full Regression

```bash
pytest -v
mypy backend/sandbox.py
ruff check backend/sandbox.py
```

## Required Output Format

Every python-sandboxing task must produce:

### Sandbox Policy Config

```
Sandbox Version: X.Y
RestrictedPython Version: X.Y.Z

Whitelisted Modules: numpy, pandas, math
Whitelisted Builtins: int, float, bool, str, list, range, len, abs, min, max, round, sum, enumerate, zip
Blocked Dunders: __import__, __builtins__, __subclasses__, __bases__, __globals__, __code__
Timeout: 30 seconds (Unix: SIGALRM, Windows: threading)
Memory Limit: [configured value or "platform default"]
```

### Security Test Results

```
Sandbox Escape Tests:
  [PASS] import os -> blocked (SecurityError)
  [PASS] import subprocess -> blocked (SecurityError)
  [PASS] __import__('os') -> blocked (SecurityError)
  [PASS] open('/etc/passwd') -> blocked (SecurityError)
  [PASS] exec('print(1)') -> blocked (SecurityError)
  [PASS] eval('1+1') -> blocked (SecurityError)
  [PASS] infinite loop -> blocked (TimeoutError, 30s)
  ...

Legitimate Code Tests:
  [PASS] simple RSI signal function -> executed, returned 0
  [PASS] multi-indicator signal function -> executed, returned 1
  ...

Result: ALL escape attempts blocked, ALL valid code executed successfully
```

### Blocked Operation List

```
Category: Imports
  - import <any_module> (except numpy, pandas, math via sandbox globals)
  - __import__()
  - importlib.*

Category: File I/O
  - open()
  - pathlib.*
  - os.path.*

Category: Code Execution
  - exec()
  - eval()
  - compile()

Category: System Access
  - os.*
  - sys.*
  - subprocess.*

Category: Network
  - socket.*
  - http.*
  - urllib.*
  - requests.*

Category: Sandbox Escape
  - __builtins__
  - __subclasses__()
  - __bases__
  - __globals__
  - __code__
  - getattr() on non-whitelisted objects
  - setattr() / delattr()
```
