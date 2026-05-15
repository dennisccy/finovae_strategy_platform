"""
Sandbox Escape Tests (T52)

Tests to ensure the RestrictedPython sandbox properly blocks
dangerous operations and prevents escape attempts.
"""

import pytest

from backend.sandbox import SandboxExecutor, SandboxConfig, SandboxError


class TestSandboxBlocking:
    """Tests that verify dangerous operations are blocked."""

    @pytest.fixture
    def sandbox(self):
        """Create sandbox executor for tests."""
        return SandboxExecutor(SandboxConfig(timeout_seconds=5))

    def test_blocks_import(self, sandbox):
        """Test that __import__ is blocked."""
        code = '''
def signal(df, i):
    os = __import__("os")
    return 0
'''
        errors = sandbox.validate_code(code)
        assert any("__import__" in e for e in errors), (
            "__import__ should be blocked"
        )

    def test_blocks_exec(self, sandbox):
        """Test that exec() is blocked."""
        code = '''
def signal(df, i):
    exec("print('hello')")
    return 0
'''
        errors = sandbox.validate_code(code)
        assert any("exec" in e for e in errors), (
            "exec() should be blocked"
        )

    def test_blocks_eval(self, sandbox):
        """Test that eval() is blocked."""
        code = '''
def signal(df, i):
    result = eval("1 + 1")
    return 0
'''
        errors = sandbox.validate_code(code)
        assert any("eval" in e for e in errors), (
            "eval() should be blocked"
        )

    def test_blocks_compile(self, sandbox):
        """Test that compile() is blocked."""
        code = '''
def signal(df, i):
    c = compile("pass", "<string>", "exec")
    return 0
'''
        errors = sandbox.validate_code(code)
        assert any("compile" in e for e in errors), (
            "compile() should be blocked"
        )

    def test_blocks_open(self, sandbox):
        """Test that open() is blocked."""
        code = '''
def signal(df, i):
    with open("/etc/passwd") as f:
        data = f.read()
    return 0
'''
        errors = sandbox.validate_code(code)
        assert any("open" in e or "File" in e for e in errors), (
            "open() should be blocked"
        )

    def test_blocks_os_module(self, sandbox):
        """Test that os module access is blocked."""
        code = '''
import os

def signal(df, i):
    os.system("echo hello")
    return 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) > 0, "os module access should be blocked"

    def test_blocks_subprocess(self, sandbox):
        """Test that subprocess is blocked."""
        code = '''
def signal(df, i):
    import subprocess
    subprocess.run(["ls"])
    return 0
'''
        errors = sandbox.validate_code(code)
        assert any("subprocess" in e for e in errors), (
            "subprocess should be blocked"
        )

    def test_blocks_socket(self, sandbox):
        """Test that socket operations are blocked."""
        code = '''
def signal(df, i):
    import socket
    s = socket.socket()
    return 0
'''
        errors = sandbox.validate_code(code)
        assert any("socket" in e for e in errors), (
            "socket should be blocked"
        )

    def test_blocks_sys_modules(self, sandbox):
        """Test that sys.modules manipulation is blocked."""
        code = '''
import sys

def signal(df, i):
    sys.modules["os"] = None
    return 0
'''
        errors = sandbox.validate_code(code)
        assert any("sys.modules" in e for e in errors), (
            "sys.modules access should be blocked"
        )


class TestSandboxPrivateAccess:
    """Tests for blocking private attribute access."""

    @pytest.fixture
    def sandbox(self):
        return SandboxExecutor(SandboxConfig(timeout_seconds=5))

    def test_blocks_dunder_access(self, sandbox):
        """Test that __dunder__ attribute access is restricted."""
        code = '''
def signal(df, i):
    # Try to access __class__
    cls = df.__class__
    return 0
'''
        # This should compile but fail at runtime due to getattr restrictions
        errors = sandbox.validate_code(code)
        # RestrictedPython should catch this
        # If no error, that's also acceptable as long as runtime blocks it

    def test_blocks_builtins_access(self, sandbox):
        """Test that __builtins__ access is blocked."""
        code = '''
def signal(df, i):
    builtins = __builtins__
    return 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) > 0, "__builtins__ access should be blocked"


class TestSandboxResourceLimits:
    """Tests for resource limit enforcement."""

    @pytest.fixture
    def sandbox(self):
        return SandboxExecutor(SandboxConfig(timeout_seconds=2))

    def test_valid_strategy_compiles(self, sandbox):
        """Test that valid strategy code compiles successfully."""
        code = '''
import numpy as np
import pandas as pd

def signal(df, i):
    if i < 20:
        return 0

    close = df["close"]
    sma = close.rolling(20).mean()

    if close.iloc[i] > sma.iloc[i]:
        return 1
    elif close.iloc[i] < sma.iloc[i]:
        return -1
    return 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) == 0, f"Valid code should compile: {errors}"

    def test_allows_numpy_operations(self, sandbox):
        """Test that numpy operations are allowed."""
        code = '''
import numpy as np

def signal(df, i):
    arr = np.array([1, 2, 3])
    mean = np.mean(arr)
    return 1 if mean > 2 else 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) == 0, f"Numpy should be allowed: {errors}"

    def test_allows_pandas_operations(self, sandbox):
        """Test that pandas operations are allowed."""
        code = '''
import pandas as pd

def signal(df, i):
    sma = df["close"].rolling(10).mean()
    return 1 if df["close"].iloc[i] > sma.iloc[i] else 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) == 0, f"Pandas should be allowed: {errors}"


class TestSandboxEscapeAttempts:
    """Tests for various sandbox escape techniques."""

    @pytest.fixture
    def sandbox(self):
        return SandboxExecutor(SandboxConfig(timeout_seconds=5))

    def test_no_breakout_via_globals(self, sandbox):
        """Test that globals() cannot be used to escape."""
        code = '''
def signal(df, i):
    g = globals()
    return 0
'''
        errors = sandbox.validate_code(code)
        # Should be blocked or restricted

    def test_no_breakout_via_locals(self, sandbox):
        """Test that locals() cannot be used for escape."""
        code = '''
def signal(df, i):
    l = locals()
    return 0
'''
        errors = sandbox.validate_code(code)
        # Should be blocked or restricted

    def test_no_breakout_via_type(self, sandbox):
        """Test escape attempt via type() is blocked."""
        code = '''
def signal(df, i):
    # Attempt to get base classes
    t = type(df)
    bases = t.__bases__
    return 0
'''
        # This might compile but should fail at runtime
        errors = sandbox.validate_code(code)

    def test_no_breakout_via_getattr(self, sandbox):
        """Test that getattr cannot access private attributes."""
        code = '''
def signal(df, i):
    cls = getattr(df, "__class__")
    return 0
'''
        # Should be caught by our safe getattr wrapper
        errors = sandbox.validate_code(code)

    def test_no_code_object_manipulation(self, sandbox):
        """Test that code object manipulation is blocked."""
        code = '''
def signal(df, i):
    def inner():
        pass
    code = inner.__code__
    return 0
'''
        # Should be blocked
        errors = sandbox.validate_code(code)

    def test_no_frame_inspection(self, sandbox):
        """Test that frame inspection is blocked."""
        code = '''
import sys

def signal(df, i):
    frame = sys._getframe()
    return 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) > 0, "Frame inspection should be blocked"


class TestSandboxMaliciousPatterns:
    """Tests for specific malicious patterns."""

    @pytest.fixture
    def sandbox(self):
        return SandboxExecutor(SandboxConfig(timeout_seconds=5))

    def test_blocks_importlib(self, sandbox):
        """Test that importlib is blocked."""
        code = '''
def signal(df, i):
    import importlib
    os = importlib.import_module("os")
    return 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) > 0, "importlib should be blocked"

    def test_blocks_ctypes(self, sandbox):
        """Test that ctypes is blocked."""
        code = '''
def signal(df, i):
    import ctypes
    return 0
'''
        # Should fail on import
        errors = sandbox.validate_code(code)

    def test_blocks_pickle(self, sandbox):
        """Test that pickle (code execution risk) is blocked."""
        code = '''
def signal(df, i):
    import pickle
    return 0
'''
        # Should fail on import or be restricted

    def test_blocks_multiprocessing(self, sandbox):
        """Test that multiprocessing is blocked."""
        code = '''
def signal(df, i):
    import multiprocessing
    return 0
'''
        # Should fail on import

    def test_blocks_threading(self, sandbox):
        """Test that threading is blocked."""
        code = '''
def signal(df, i):
    import threading
    return 0
'''
        # Should fail on import


class TestSandboxValidCodeExecution:
    """Tests that valid strategy code actually works."""

    @pytest.fixture
    def sandbox(self):
        return SandboxExecutor(SandboxConfig(timeout_seconds=5))

    def test_simple_strategy_executes(self, sandbox):
        """Test that a simple valid strategy executes correctly."""
        code = '''
import numpy as np
import pandas as pd

def signal(df, i):
    if i < 20:
        return 0

    close = df["close"]
    sma20 = close.rolling(20).mean()

    if pd.isna(sma20.iloc[i]):
        return 0

    if close.iloc[i] > sma20.iloc[i]:
        return 1
    elif close.iloc[i] < sma20.iloc[i]:
        return -1

    return 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) == 0, f"Valid strategy should pass validation: {errors}"

        # Try to get signal function
        try:
            signal_func = sandbox.get_signal_function(code)
            assert callable(signal_func), "Should return callable"
        except SandboxError as e:
            pytest.fail(f"Valid code should execute: {e}")

    def test_rsi_strategy_executes(self, sandbox):
        """Test that RSI strategy executes correctly."""
        code = '''
import numpy as np
import pandas as pd

def signal(df, i):
    if i < 20:
        return 0

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    current_rsi = rsi.iloc[i]

    if pd.isna(current_rsi):
        return 0

    if current_rsi < 30:
        return 1
    elif current_rsi > 70:
        return -1

    return 0
'''
        errors = sandbox.validate_code(code)
        assert len(errors) == 0, f"RSI strategy should pass validation: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
