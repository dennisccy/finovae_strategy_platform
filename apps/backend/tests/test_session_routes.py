"""API/response-shape tests for backend/session_routes.py.

Covers the iter-3 anti-goal: GET /api/sessions/{id} (the list/open path) MUST NOT
eagerly parse full per-iteration result/rating payloads. Iteration detail is
lazy-loaded via the existing per-iteration endpoint.

These tests are the *primary* proof the anti-goal is resolved — they assert the
actual HTTP response shape (heavy-payload key absence) and inspect the final
get_session source. They do NOT infer resolution from a passing browser journey
(J-02 has passed every prior iteration *with* the eager-load present).

No store mocking: a real on-disk temp store is seeded via session_store helpers,
matching the style of test_session_store.py. session_routes imported the store
functions by name; those functions resolve BASE_DIR from the session_store module
global at call time, so monkeypatching session_store.BASE_DIR redirects both the
helpers and the route handlers to the temp dir (no importlib.reload needed, which
would break session_routes' already-bound function references).
"""

import inspect

import pytest
from fastapi.testclient import TestClient

import backend.session_store as ss
from backend import session_routes
from backend.api import app


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "BASE_DIR", tmp_path / "store")
    ss.initialize()
    return ss


@pytest.fixture()
def client():
    # No context manager → no lifespan/startup; the routes under test do not
    # depend on startup events.
    return TestClient(app)


def _completed_node(iter_id: str = "iter-001", parent: str | None = None) -> dict:
    return {
        "id": iter_id,
        "prompt": "buy when rsi < 30, sell when rsi > 70",
        "scriptCode": "def signal(df, i):\n    return 0\n",
        "scriptId": f"scr-{iter_id}",
        "strategyName": "RSI Reversion",
        "status": "complete",
        "timestamp": "2024-01-02T03:04:05.000Z",
        "params": {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "start_date": "2024-01-01",
            "end_date": "2024-06-01",
            "initial_capital": 10000,
            "exchange": "binance",
        },
        "parentId": parent,
        "totalReturn": 0.37,
        "winRate": 0.55,
        "numTrades": 42,
        "sharpe": 1.8,
        "maxDrawdown": 0.12,
        "result": {
            "run_id": "run-xyz",
            "total_return": 0.37,
            "max_drawdown": 0.12,
            "num_trades": 42,
            "win_rate": 0.55,
            "sharpe_ratio": 1.8,
            "profit_factor": 1.6,
            "equity_curve": [
                {"timestamp": "2024-01-01T00:00:00Z", "equity": 10000, "drawdown": 0.0}
            ],
            "trades": [
                {
                    "trade_id": "t1",
                    "entry_time": "2024-01-02T00:00:00Z",
                    "exit_time": "2024-01-03T00:00:00Z",
                    "entry_price": 100.0,
                    "exit_price": 110.0,
                    "quantity": 1.0,
                    "pnl": 10.0,
                    "pnl_percent": 0.1,
                    "commission_paid": 0.1,
                }
            ],
        },
        "rating": {
            "benchmark_total_return": 0.2,
            "profitability": {
                "name": "profitability",
                "label": "Good",
                "stars": 4,
                "key_metrics": {},
                "analyses": {},
            },
        },
        "insights": {"summary": "ok", "suggestions": [{"title": "Add a stop loss"}]},
    }


_HEAVY_KEYS = (
    "result",
    "rating",
    "insights",
    "prompt",
    "scriptCode",
    "timeframeResults",
    "equity_curve",
    "trades",
)


def test_get_session_iteration_list_is_lightweight_no_heavy_payloads(store, client):
    """The list/open path must not inline per-iteration result/rating payloads."""
    store.write_iteration("sess-1", 1, _completed_node("iter-001"))
    store.write_session_meta(
        "sess-1",
        {
            "backtestParams": {"symbol": "BTCUSDT", "timeframe": "1h"},
            "selectedIterationId": "iter-001",
        },
    )
    store.append_activity_entries(
        "sess-1", [{"id": "a1", "type": "user-prompt", "content": "hi"}]
    )

    resp = client.get("/api/sessions/sess-1")
    assert resp.status_code == 200
    body = resp.json()

    assert body["sessionId"] == "sess-1"
    assert body["backtestParams"] == {"symbol": "BTCUSDT", "timeframe": "1h"}
    assert body["selectedIterationId"] == "iter-001"
    assert body["activityLog"] == [
        {"id": "a1", "type": "user-prompt", "content": "hi"}
    ]

    history = body["iterationHistory"]
    assert len(history) == 1
    entry = history[0]

    # Anti-goal: NO heavy payload keys present (assert exact absence, not null).
    for key in _HEAVY_KEYS:
        assert key not in entry, f"heavy key {key!r} leaked into the list path"

    # Lightweight fields the frontend tree/selection needs MUST be present.
    assert entry["id"] == "iter-001"
    assert entry["status"] == "complete"
    assert entry["timestamp"] == "2024-01-02T03:04:05.000Z"
    assert entry["strategyName"] == "RSI Reversion"
    assert entry["parentId"] is None
    assert entry["params"]["symbol"] == "BTCUSDT"
    assert entry["params"]["timeframe"] == "1h"
    assert entry["totalReturn"] == pytest.approx(0.37)


def test_get_session_does_not_call_read_iteration_full(store):
    """Code-inspection proof of the anti-goal, independent of any browser journey.

    get_session must lazy-list via read_iteration_meta and must NOT eager-load
    via read_iteration_full.
    """
    src = inspect.getsource(session_routes.get_session)
    assert "read_iteration_full" not in src
    assert "read_iteration_meta" in src


def test_per_iteration_endpoint_still_returns_full_node(store, client):
    """The lazy-detail path must remain intact: full result/rating on demand."""
    store.write_iteration("sess-1", 1, _completed_node("iter-001"))

    resp = client.get("/api/sessions/sess-1/iterations/iter-001")
    assert resp.status_code == 200
    node = resp.json()

    assert node["id"] == "iter-001"
    assert "result" in node and node["result"] is not None
    assert node["result"]["total_return"] == pytest.approx(0.37)
    assert len(node["result"]["equity_curve"]) == 1
    assert len(node["result"]["trades"]) == 1
    assert "rating" in node and node["rating"] is not None
    assert node["rating"]["benchmark_total_return"] == pytest.approx(0.2)
    assert node["prompt"] == "buy when rsi < 30, sell when rsi > 70"
    assert node["scriptCode"] == "def signal(df, i):\n    return 0\n"
    assert node["insights"]["suggestions"][0]["title"] == "Add a stop loss"


def test_get_session_preserves_order_and_meta(store, client):
    """Lightweight list preserves disk ordering; meta/activity unchanged."""
    store.write_iteration("sess-2", 1, _completed_node("iter-001"))
    store.write_iteration("sess-2", 2, _completed_node("iter-002", parent="iter-001"))

    resp = client.get("/api/sessions/sess-2")
    assert resp.status_code == 200
    history = resp.json()["iterationHistory"]

    assert [e["id"] for e in history] == ["iter-001", "iter-002"]
    assert history[1]["parentId"] == "iter-001"
    for entry in history:
        for key in _HEAVY_KEYS:
            assert key not in entry


def test_get_session_404_for_unknown_session(store, client):
    resp = client.get("/api/sessions/does-not-exist")
    assert resp.status_code == 404
    assert "does-not-exist" in resp.json()["detail"]
