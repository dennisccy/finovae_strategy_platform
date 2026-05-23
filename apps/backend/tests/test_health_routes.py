"""Health-check route tests.

The dev-chain automation (qa-phase.sh, browser-qa-phase.sh, demo-phase.sh,
goal-iter-lean.sh, run-phase.sh) all default to polling GET /health to decide
whether the backend is up. The backend previously only exposed `/` and
`/api/health`, so every automated run wasted its full backend-readiness wait
budget on 404s. These tests pin the `/health` alias so that contract can't
silently regress.
"""

from fastapi.testclient import TestClient

from backend.api import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("ok", "healthy")


def test_api_health_still_works():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
