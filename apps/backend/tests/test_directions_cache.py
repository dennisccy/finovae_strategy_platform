"""Unit tests for backend/directions_cache.py — write/read/list round-trip."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

import backend.directions_cache as dc


@pytest.fixture(autouse=True)
def tmp_cache_dir(monkeypatch, tmp_path):
    """Redirect cache to a temporary directory for each test."""
    monkeypatch.setattr(dc, "BASE_DIR", tmp_path / "initial_directions")
    yield tmp_path / "initial_directions"


def _make_node(direction_id: str, total_return: float = 0.15) -> dict:
    return {
        "id": direction_id,
        "prompt": f"Test prompt for {direction_id}",
        "scriptCode": f"# Strategy: {direction_id}",
        "strategyName": f"Strategy {direction_id}",
        "changeSummary": "Test tagline",
        "status": "complete",
        "totalReturn": total_return,
        "winRate": 0.55,
        "numTrades": 42,
        "sharpe": 1.2,
        "maxDrawdown": 0.08,
        "insights": {"summary": "ok", "suggestions": []},
        "result": {
            "total_return": total_return,
            "win_rate": 0.55,
            "num_trades": 42,
            "sharpe_ratio": 1.2,
            "max_drawdown": 0.08,
            "equity_curve": [{"timestamp": i, "equity": 1000 + i, "drawdown": 0.0} for i in range(10)],
            "trades": [{"trade_id": str(i)} for i in range(5)],
        },
        "rating": None,
        "timeframeResults": [
            {
                "timeframe": "4h",
                "status": "complete",
                "result": {
                    "total_return": total_return,
                    "win_rate": 0.55,
                    "num_trades": 42,
                    "sharpe_ratio": 1.2,
                    "max_drawdown": 0.08,
                    "equity_curve": [],
                    "trades": [],
                },
                "rating": None,
            }
        ],
    }


def test_build_cache_key():
    key = dc.build_cache_key("BTC/USDT", "4h", "2024-01-01", "2024-12-31", "binance", False, 1)
    assert key == "BTC_USDT_4h_2024-01-01_2024-12-31_binance_false_1"


def test_build_cache_key_with_short():
    key = dc.build_cache_key("ETH/USDT", "1h", "2023-01-01", "2023-12-31", "bybit", True, 2)
    assert key == "ETH_USDT_1h_2023-01-01_2023-12-31_bybit_true_2"


def test_has_cache_returns_false_when_missing():
    assert not dc.has_cache("nonexistent_key")


def test_write_and_has_cache():
    cache_key = "BTC_USDT_4h_2024-01-01_2024-12-31_binance_false_1"
    node = _make_node("strategy-0")
    dc.write_direction_result(cache_key, 0, "strategy-0", node)
    assert dc.has_cache(cache_key)


def test_write_and_read_full_round_trip():
    cache_key = "test_round_trip"
    node = _make_node("strategy-5", total_return=0.42)

    dc.write_direction_result(cache_key, 5, "strategy-5", node)

    result = dc.read_direction_full(cache_key, "strategy-5")
    assert result is not None
    assert result["id"] == "strategy-5"
    assert result["prompt"] == "Test prompt for strategy-5"
    assert result["scriptCode"] == "# Strategy: strategy-5"
    assert result["strategyName"] == "Strategy strategy-5"
    assert result["status"] == "complete"
    assert result["result"]["total_return"] == pytest.approx(0.42)
    assert len(result["timeframeResults"]) == 1
    assert result["timeframeResults"][0]["timeframe"] == "4h"


def test_list_cached_directions_empty():
    assert dc.list_cached_directions("nonexistent") == []


def test_list_cached_directions_returns_summaries():
    cache_key = "test_list"
    for i in range(3):
        node = _make_node(f"strategy-{i}", total_return=i * 0.1)
        dc.write_direction_result(cache_key, i, f"strategy-{i}", node)

    summaries = dc.list_cached_directions(cache_key)
    assert len(summaries) == 3
    ids = [s["directionId"] for s in summaries]
    assert "strategy-0" in ids
    assert "strategy-1" in ids
    assert "strategy-2" in ids


def test_list_summaries_contain_lightweight_fields():
    cache_key = "test_summary_fields"
    node = _make_node("strategy-0", total_return=0.25)
    dc.write_direction_result(cache_key, 0, "strategy-0", node)

    summaries = dc.list_cached_directions(cache_key)
    s = summaries[0]
    assert s["directionId"] == "strategy-0"
    assert s["totalReturn"] == pytest.approx(0.25)
    assert s["winRate"] == pytest.approx(0.55)
    assert s["numTrades"] == 42
    assert s["status"] == "complete"


def test_read_returns_none_for_missing_direction():
    cache_key = "test_missing"
    dc.write_direction_result(cache_key, 0, "strategy-0", _make_node("strategy-0"))

    result = dc.read_direction_full(cache_key, "strategy-99")
    assert result is None


def test_write_overwrites_existing():
    cache_key = "test_overwrite"
    node1 = _make_node("strategy-0", total_return=0.10)
    node2 = _make_node("strategy-0", total_return=0.99)

    dc.write_direction_result(cache_key, 0, "strategy-0", node1)
    dc.write_direction_result(cache_key, 0, "strategy-0", node2)

    result = dc.read_direction_full(cache_key, "strategy-0")
    assert result["result"]["total_return"] == pytest.approx(0.99)


def test_equity_curve_downsampled_to_300():
    cache_key = "test_trim"
    node = _make_node("strategy-0")
    # Create a huge equity curve (600 points)
    node["result"]["equity_curve"] = [{"t": i, "equity": 1000 + i} for i in range(600)]

    dc.write_direction_result(cache_key, 0, "strategy-0", node)

    result = dc.read_direction_full(cache_key, "strategy-0")
    assert len(result["result"]["equity_curve"]) == 300


def test_trades_capped_at_200():
    cache_key = "test_trim_trades"
    node = _make_node("strategy-0")
    node["result"]["trades"] = [{"trade_id": str(i)} for i in range(500)]

    dc.write_direction_result(cache_key, 0, "strategy-0", node)

    result = dc.read_direction_full(cache_key, "strategy-0")
    assert len(result["result"]["trades"]) == 200


def test_multiple_directions_sorted_by_index():
    cache_key = "test_sort"
    # Write in reverse order
    for i in [4, 2, 0, 3, 1]:
        dc.write_direction_result(cache_key, i, f"strategy-{i}", _make_node(f"strategy-{i}"))

    summaries = dc.list_cached_directions(cache_key)
    # Should be sorted by directory name (index prefix)
    assert summaries[0]["directionId"] == "strategy-0"
    assert summaries[-1]["directionId"] == "strategy-4"
