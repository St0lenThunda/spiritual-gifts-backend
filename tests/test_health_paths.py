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
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def close(self):
            pass
    monkeypatch.setattr(database, "SessionLocal", MockDB)

    # Check root path
    resp_root = client.get("/health")
    assert resp_root.status_code == 200
    assert resp_root.json()["status"] == "ok"

    # Check v1 path
    resp_v1 = client.get("/api/v1/health")
    assert resp_v1.status_code == 200
    data = resp_v1.json()
    assert data["status"] == "ok"
    assert "database_latency_ms" in data
    # It might be 0.0 or small positive number in mock, but should be float or int
    assert isinstance(data["database_latency_ms"], (int, float))

@respx.mock
def test_health_check_external_via_v1(monkeypatch):
    """
    Test check_external via /api/v1/health.
    """
    from app import database
    class MockDB:
        def execute(self, query): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def close(self): pass
    monkeypatch.setattr(database, "SessionLocal", MockDB)

    respx.get("https://sga-v1.netlify.app/").mock(return_value=Response(200))
    
    resp = client.get("/api/v1/health?check_external=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["netlify"]["status"] == "ok"
    assert "latency_ms" in data["netlify"]
    assert isinstance(data["netlify"]["latency_ms"], (int, float))
