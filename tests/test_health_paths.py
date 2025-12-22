import pytest
from fastapi.testclient import TestClient
from app.main import app
import respx
from httpx import Response

client = TestClient(app)

def test_health_check_paths(monkeypatch):
    """
    Test that health check is accessible at both /health and /api/v1/health.
    """
    # Mock database to return success
    from app import database
    class MockDB:
        def execute(self, query):
            pass
        def close(self):
            pass
    monkeypatch.setattr(database, "SessionLocal", lambda: MockDB())

    # Check root path
    resp_root = client.get("/health")
    assert resp_root.status_code == 200
    assert resp_root.json()["status"] == "ok"

    # Check v1 path
    resp_v1 = client.get("/api/v1/health")
    assert resp_v1.status_code == 200
    assert resp_v1.json()["status"] == "ok"

@respx.mock
def test_health_check_external_via_v1(monkeypatch):
    """
    Test check_external via /api/v1/health.
    """
    from app import database
    monkeypatch.setattr(database, "SessionLocal", lambda: object())
    
    # Mock return
    class MockDB:
        def execute(self, query): pass
        def close(self): pass
    monkeypatch.setattr(database, "SessionLocal", lambda: MockDB())

    respx.get("https://sga-v1.netlify.app/").mock(return_value=Response(200))
    
    resp = client.get("/api/v1/health?check_external=true")
    assert resp.status_code == 200
    assert resp.json()["netlify"]["status"] == "ok"
