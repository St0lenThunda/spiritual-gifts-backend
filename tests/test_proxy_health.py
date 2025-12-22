import pytest
from fastapi.testclient import TestClient
from app.main import app
import respx
from httpx import Response

client = TestClient(app)

@respx.mock
def test_health_check_with_external_success(monkeypatch):
    """
    Test that health check with check_external=True returns Netlify status.
    """
    # Mock database session to return success
    from app import database
    class MockDB:
        def execute(self, query):
            pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def close(self):
            pass
    monkeypatch.setattr(database, "SessionLocal", MockDB)

    # Mock Netlify response
    route = respx.get("https://sga-v1.netlify.app/").mock(return_value=Response(200))

    response = client.get("/health?check_external=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "netlify" in data
    assert data["netlify"]["status"] == "ok"
    assert data["netlify"]["code"] == 200
    assert route.called

@respx.mock
def test_health_check_with_external_failure(monkeypatch):
    """
    Test that health check handles external service failure gracefully.
    """
    # Mock database session
    from app import database
    class MockDB:
        def execute(self, query):
            pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def close(self):
            pass
    monkeypatch.setattr(database, "SessionLocal", MockDB)

    # Mock Netlify 404
    respx.get("https://sga-v1.netlify.app/").mock(return_value=Response(404))

    response = client.get("/health?check_external=true")
    assert response.status_code == 200  # Overall status is still 200 if DB is fine
    data = response.json()
    assert data["status"] == "ok"
    assert data["netlify"]["status"] == "error"
    assert data["netlify"]["code"] == 404

def test_health_check_without_external():
    """
    Test that health check defaults to internal only.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "netlify" not in data
