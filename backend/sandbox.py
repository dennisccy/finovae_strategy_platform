"""
Sandboxed Strategy Executor

Uses RestrictedPython to safely execute user-generated strategy code.
Enforces resource limits and blocks dangerous operations.
"""

import signal
import sys
from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    safer_getattr,
)


class SandboxError(Exception):
    """Exception raised for sandbox violations or execution errors."""
    pass


class TimeoutError(SandboxError):
    """Exception raised when execution exceeds time limit."""
    pass


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    allow_numpy: bool = True
    allow_pandas: bool = True


class SandboxExecutor:
    """
    Executes strategy code in a restricted Python sandbox.

    Security measures:
    - RestrictedPython compilation
    - Limited imports (numpy, pandas only)
    - No network access
    - No file I/O
    - No exec(), eval(), __import__()
    - Time limit enforcement
    - Memory limit (advisory)
    """

    # Whitelisted imports
    ALLOWED_MODULES = {
        "numpy": np,
        "pandas": pd,
        "np": np,
        "pd": pd,
    }

    # Blocked builtins
    BLOCKED_BUILTINS = {
        "exec", "eval", "compile", "__import__",
        "open", "input", "breakpoint",
        "globals", "locals", "vars",
        "getattr", "setattr", "delattr",
        "memoryview", "bytearray",
    }

    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Initialize sandbox executor.

        Args:
            config: Sandbox configuration (uses defaults if None)
        """
        self.config = config or SandboxConfig()
        self._compiled_cache: dict[str, Any] = {}

    def _create_safe_builtins(self) -> dict:
        """Create dictionary of safe builtin functions."""
        import builtins

        safe_builtins = {}

        # Copy safe builtins
        for name in dir(builtins):
            if name not in self.BLOCKED_BUILTINS and not name.startswith("_"):
                safe_builtins[name] = getattr(builtins, name)

        # Add RestrictedPython guards
        safe_builtins["_getiter_"] = default_guarded_getiter
        safe_builtins["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence

        # Safe getattr that blocks access to dunder methods
        def _safe_getattr(obj, name, default=None):
            if name.startswith("_"):
                raise SandboxError(f"Access to private attribute '{name}' is not allowed")
            return safer_getattr(obj, name, default)

        safe_builtins["_getattr_"] = _safe_getattr
        safe_builtins["getattr"] = _safe_getattr

        # Block dangerous builtins explicitly
        for blocked in self.BLOCKED_BUILTINS:
            if blocked in safe_builtins:
                del safe_builtins[blocked]

        return safe_builtins

    def _create_safe_globals(self) -> dict:
        """Create safe global namespace for execution."""
        globals_dict = {
            "__builtins__": self._create_safe_builtins(),
            "__name__": "__strategy__",
            "__doc__": None,
        }

        # Add allowed modules
        if self.config.allow_numpy:
            globals_dict["numpy"] = np
            globals_dict["np"] = np

        if self.config.allow_pandas:
            globals_dict["pandas"] = pd
            globals_dict["pd"] = pd

        return globals_dict

    def compile_strategy(self, code: str) -> dict:
        """
        Compile strategy code in restricted mode.

        Args:
            code: Python source code

        Returns:
            Compiled code object

        Raises:
            SandboxError: If compilation fails or code is unsafe
        """
        # Check for obviously dangerous patterns
        dangerous_patterns = [
            "__import__", "exec(", "eval(", "compile(",
            "open(", "socket", "subprocess", "os.",
            "sys.modules", "importlib", "__builtins__",
        ]

        for pattern in dangerous_patterns:
            if pattern in code:
                raise SandboxError(f"Dangerous pattern detected: {pattern}")

        # Compile with RestrictedPython
        try:
            compiled = compile_restricted(
                code,
                filename="<strategy>",
                mode="exec",
            )

            if compiled.errors:
                raise SandboxError(
                    f"Compilation errors: {'; '.join(compiled.errors)}"
                )

            return compiled.code

        except SyntaxError as e:
            raise SandboxError(f"Syntax error in strategy code: {e}")

    def _timeout_handler(self, signum, frame):
        """Signal handler for timeout."""
        raise TimeoutError(
            f"Strategy execution exceeded {self.config.timeout_seconds}s timeout"
        )

    def execute(
        self,
        code: str,
        df: pd.DataFrame,
        bar_index: int,
    ) -> int:
        """
        Execute strategy code and get signal for a single bar.

        Args:
            code: Strategy Python code
            df: DataFrame with OHLCV data
            bar_index: Current bar index

        Returns:
            Signal: 1 (buy), -1 (sell), or 0 (hold)

        Raises:
            SandboxError: If execution fails or violates sandbox
        """
        # Compile code (or use cache)
        code_hash = hash(code)
        if code_hash not in self._compiled_cache:
            self._compiled_cache[code_hash] = self.compile_strategy(code)

        compiled_code = self._compiled_cache[code_hash]

        # Create safe execution environment
        safe_globals = self._create_safe_globals()
        safe_locals: dict[str, Any] = {}

        # Set timeout (Unix only)
        if sys.platform != "win32":
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.config.timeout_seconds)

        try:
            # Execute the strategy code to define functions
            exec(compiled_code, safe_globals, safe_locals)

            # Get the signal function
            signal_func = safe_locals.get("signal")
            if signal_func is None:
                raise SandboxError("Strategy code must define a 'signal' function")

            # Call signal function
            result = signal_func(df.copy(), bar_index)

            # Validate result
            if result not in (-1, 0, 1):
                return 0

            return int(result)

        except TimeoutError:
            raise
        except SandboxError:
            raise
        except Exception as e:
            raise SandboxError(f"Strategy execution error: {e}")
        finally:
            # Cancel timeout
            if sys.platform != "win32":
                signal.alarm(0)

    def get_signal_function(self, code: str) -> Callable[[pd.DataFrame, int], int]:
        """
        Get a callable signal function from strategy code.

        This allows the backtest engine to call the signal function
        repeatedly without re-compiling.

        Args:
            code: Strategy Python code

        Returns:
            Callable that takes (df, bar_index) and returns signal

        Raises:
            SandboxError: If compilation or setup fails
        """
        # Compile code
        compiled_code = self.compile_strategy(code)

        # Create safe execution environment
        safe_globals = self._create_safe_globals()
        safe_locals: dict[str, Any] = {}

        try:
            # Execute to define functions
            exec(compiled_code, safe_globals, safe_locals)

            signal_func = safe_locals.get("signal")
            if signal_func is None:
                raise SandboxError("Strategy code must define a 'signal' function")

            # Wrap with timeout (on Unix)
            def wrapped_signal(df: pd.DataFrame, i: int) -> int:
                if sys.platform != "win32":
                    signal.signal(signal.SIGALRM, self._timeout_handler)
                    signal.alarm(self.config.timeout_seconds)

                try:
                    result = signal_func(df.copy(), i)
                    if result not in (-1, 0, 1):
                        return 0
                    return int(result)
                except Exception:
                    return 0
                finally:
                    if sys.platform != "win32":
                        signal.alarm(0)

            return wrapped_signal

        except SandboxError:
            raise
        except Exception as e:
            raise SandboxError(f"Failed to create signal function: {e}")

    def validate_code(self, code: str) -> list[str]:
        """
        Validate strategy code without executing it.

        Args:
            code: Strategy Python code

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check for dangerous patterns
        dangerous_patterns = [
            ("__import__", "Dynamic imports not allowed"),
            ("exec(", "exec() not allowed"),
            ("eval(", "eval() not allowed"),
            ("compile(", "compile() not allowed"),
            ("open(", "File operations not allowed"),
            ("socket", "Network operations not allowed"),
            ("subprocess", "Process spawning not allowed"),
            ("os.", "os module not allowed"),
            ("sys.modules", "Module manipulation not allowed"),
        ]

        for pattern, message in dangerous_patterns:
            if pattern in code:
                errors.append(message)

        # Try to compile
        if not errors:
            try:
                self.compile_strategy(code)
            except SandboxError as e:
                errors.append(str(e))

        return errors
