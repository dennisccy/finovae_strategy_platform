"""API tests for backend/auto_session_routes.py + the autoRun field on
GET /api/sessions/{id}.

The pipeline is injected via ``app.state.auto_pipeline`` (a deterministic
FakePipeline) so no live LLM is hit.  The fake is GATED at its first
``generate_strategy`` call, so each launched background loop parks immediately —
these tests assert the synchronous ROUTE behavior (session created + listed +
status exposed, validation, stop semantics, non-blocking launch).  The loop's
own iteration behavior is covered exhaustively in test_auto_session.py.

Verification is API-grounded (HTTP status + parsed autoRun/session payloads),
the sanctioned substitute for pixel screenshots given the documented Chrome-MCP
headless render-throttle.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

import backend.session_store as ss
from backend.api import app
from backend.auto_session import is_terminal
from tests.auto_session_helpers import FakePipeline, FakeSpec


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "BASE_DIR", tmp_path / "store")
    ss.initialize()
    return ss


@pytest.fixture()
def fake_pipeline():
    # Gated: the launched loop parks at the first generate_strategy so route
    # tests stay deterministic (no iterations produced during the test).
    gate = asyncio.Event()
    return FakePipeline(sequence=[FakeSpec()] * 12, suggestions_per_round=1, gate=gate)


@pytest.fixture()
def client(store, fake_pipeline):
    app.state.auto_pipeline = fake_pipeline
    with TestClient(app) as c:
        yield c
    fake_pipeline.gate.set()
    try:
        delattr(app.state, "auto_pipeline")
    except AttributeError:
        pass


def _payload(**overrides):
    body = {
        "natural_language": "Buy when RSI crosses below 30, sell above 70",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "start_date": "2023-01-01",
        "end_date": "2023-06-01",
        "initial_capital": 10000,
        "budget": {"max_iterations": 2},
    }
    body.update(overrides)
    return body


# =============================================================================
# J-07 — start a headless session via the API
# =============================================================================

def test_create_returns_200_with_session_and_status(client):
    resp = client.post("/api/auto-sessions", json=_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["sessionId"]
    assert body["status"] in ("running", "queued")
    assert body["autoRun"]["status"] in ("running", "queued")
    assert body["autoRun"]["budget"]["maxIterations"] == 2
    assert body["autoRun"]["bestIterationId"] is None


def test_created_session_appears_immediately_in_sessions_list(client):
    sid = client.post("/api/auto-sessions", json=_payload()).json()["sessionId"]
    tabs = client.get("/api/sessions").json()["tabs"]
    assert any(t["id"] == sid for t in tabs)


def test_get_session_exposes_auto_run_block(client):
    sid = client.post("/api/auto-sessions", json=_payload()).json()["sessionId"]
    sess = client.get(f"/api/sessions/{sid}").json()
    assert sess["autoRun"] is not None
    assert sess["autoRun"]["status"] in ("running", "queued")
    assert sess["autoRun"]["budget"]["maxIterations"] == 2
    assert sess["backtestParams"]["symbol"] == "BTC/USDT"


def test_manual_session_has_null_auto_run(client):
    # A plain (non-auto) session: GET must return autoRun: null (additive field).
    ss.write_iteration("manual-x", 1, {"id": "it-1", "status": "complete",
                                        "params": {"symbol": "BTC/USDT"}})
    sess = client.get("/api/sessions/manual-x").json()
    assert sess["autoRun"] is None


# =============================================================================
# Non-blocking launch (anti-goal: must not block the event loop)
# =============================================================================

def test_post_returns_before_loop_completes_and_get_stays_responsive(client):
    resp = client.post("/api/auto-sessions", json=_payload(budget={"max_iterations": 3}))
    assert resp.status_code == 200
    sid = resp.json()["sessionId"]
    # The loop is parked at the gated first step → still active, not terminal.
    sess = client.get(f"/api/sessions/{sid}").json()
    assert sess["autoRun"]["status"] == "running"
    assert not is_terminal(sess["autoRun"]["status"])
    # The list endpoint stays responsive while a run is active.
    assert any(t["id"] == sid for t in client.get("/api/sessions").json()["tabs"])


# =============================================================================
# Error cases
# =============================================================================

def test_open_universe_rejected_4xx(client):
    resp = client.post("/api/auto-sessions", json=_payload(symbol=None, timeframe=None))
    assert resp.status_code == 400
    assert "symbol" in resp.json()["detail"].lower()


def test_missing_symbol_only_rejected_4xx(client):
    body = _payload()
    del body["symbol"]
    resp = client.post("/api/auto-sessions", json=body)
    assert resp.status_code == 400


def test_missing_budget_is_422(client):
    body = _payload()
    del body["budget"]
    resp = client.post("/api/auto-sessions", json=body)
    assert resp.status_code == 422


def test_missing_max_iterations_is_422(client):
    resp = client.post("/api/auto-sessions", json=_payload(budget={}))
    assert resp.status_code == 422


def test_invalid_timeframe_rejected_4xx(client):
    resp = client.post("/api/auto-sessions", json=_payload(timeframe="2h"))
    assert resp.status_code == 400


def test_end_before_start_is_422(client):
    resp = client.post("/api/auto-sessions",
                       json=_payload(start_date="2023-06-01", end_date="2023-01-01"))
    assert resp.status_code == 422


# =============================================================================
# Stop endpoint (cancellation infrastructure for J-11)
# =============================================================================

def test_stop_unknown_session_404(client):
    resp = client.post("/api/auto-sessions/does-not-exist/stop")
    assert resp.status_code == 404


def test_stop_running_flips_persisted_flag(client):
    created = client.post("/api/auto-sessions", json=_payload(budget={"max_iterations": 3}))
    sid = created.json()["sessionId"]
    resp = client.post(f"/api/auto-sessions/{sid}/stop")
    assert resp.status_code == 200
    assert resp.json()["autoRun"]["stopRequested"] is True
    # Durable: the flag is persisted on session.json (survives reload / restart).
    assert ss.read_session_meta(sid)["autoRun"]["stopRequested"] is True


def test_stop_already_terminal_is_idempotent_200(client):
    ss.write_session_meta("done-sess", {
        "name": "Done",
        "autoRun": {"status": "criteria-met", "stopReason": "criteria-met",
                    "stopRequested": False, "bestIterationId": "i1", "budget": {},
                    "startedAt": "t0", "endedAt": "t1"},
    })
    resp = client.post("/api/auto-sessions/done-sess/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "criteria-met"
    # No-op: the flag is NOT flipped on an already-terminal session.
    assert ss.read_session_meta("done-sess")["autoRun"]["stopRequested"] is False


def test_stop_on_manual_session_404(client):
    # A session with no autoRun block is not an auto-session.
    ss.write_iteration("manual-y", 1, {"id": "it-1", "status": "complete"})
    resp = client.post("/api/auto-sessions/manual-y/stop")
    assert resp.status_code == 404
