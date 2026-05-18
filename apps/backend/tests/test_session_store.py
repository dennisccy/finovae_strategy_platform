"""Unit tests for backend/session_store.py — durable-by-default store.

Covers the iter-1 BACKTEST_STORE_DIR anti-goal:
  * with BACKTEST_STORE_DIR unset, BASE_DIR is absolute, not under /tmp, and
    resolves to <repo>/.data/backtests (so existing on-disk sessions written
    there via the runtime .env are not orphaned)
  * a session/iteration written, then re-resolved from a fresh module import
    (simulated process restart), reads back intact
  * missing session/iteration reads return None (no crash)
"""

import importlib
import os
from pathlib import Path

import pytest

import backend.session_store as ss


@pytest.fixture(autouse=True)
def _restore_session_store():
    """Reload the module after each test so a test's BASE_DIR cannot leak."""
    yield
    os.environ.pop("BACKTEST_STORE_DIR", None)
    importlib.reload(ss)


def _node() -> dict:
    return {
        "id": "iter-abc",
        "prompt": "buy when rsi < 30, sell when rsi > 70",
        "scriptCode": "def signal(df, i): return 0",
        "strategyName": "RSI Reversion",
        "status": "complete",
        "params": {"timeframe": "1h"},
        "result": {"total_return": 0.37, "trades": [], "equity_curve": []},
        "rating": None,
        "insights": None,
    }


def test_default_store_dir_is_durable_not_tmp(monkeypatch):
    monkeypatch.delenv("BACKTEST_STORE_DIR", raising=False)
    importlib.reload(ss)

    repo_root = Path(ss.__file__).resolve().parents[3]
    assert ss.BASE_DIR.is_absolute()
    assert not str(ss.BASE_DIR).startswith("/tmp")
    assert ss.BASE_DIR == repo_root / ".data" / "backtests"


def test_write_then_simulated_restart_round_trip(monkeypatch, tmp_path):
    store = tmp_path / "store"
    monkeypatch.setenv("BACKTEST_STORE_DIR", str(store))
    importlib.reload(ss)
    assert ss.BASE_DIR == store

    ss.initialize()
    ss.write_session_meta("sess-1", {"name": "RSI Reversion"})
    ss.write_iteration("sess-1", 1, _node())

    # Simulated process restart: re-import the module fresh; BASE_DIR is
    # re-resolved from the (still-set) env and must point at the same dir.
    importlib.reload(ss)
    assert ss.BASE_DIR == store

    meta = ss.read_session_meta("sess-1")
    assert meta is not None
    assert meta["name"] == "RSI Reversion"

    full = ss.read_iteration_full("sess-1", "iter-abc")
    assert full is not None
    assert full["id"] == "iter-abc"
    assert full["prompt"] == "buy when rsi < 30, sell when rsi > 70"
    assert full["scriptCode"] == "def signal(df, i): return 0"
    assert full["result"]["total_return"] == pytest.approx(0.37)

    tabs = ss.derive_session_tabs()
    assert any(t["id"] == "sess-1" and t["name"] == "RSI Reversion" for t in tabs)


def test_missing_session_and_iteration_return_none(monkeypatch, tmp_path):
    monkeypatch.setenv("BACKTEST_STORE_DIR", str(tmp_path / "store"))
    importlib.reload(ss)
    ss.initialize()

    assert ss.read_session_meta("does-not-exist") is None
    assert ss.read_iteration_full("does-not-exist", "nope") is None
    assert ss.derive_session_tabs() == []
