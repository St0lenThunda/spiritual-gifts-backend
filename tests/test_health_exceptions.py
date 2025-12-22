
from fastapi.testclient import TestClient
from app.main import app
import respx
from httpx import Response
import httpx

client = TestClient(app)

@respx.mock
def test_health_check_external_exception(monkeypatch):
    """
    Test that health check handles connection errors during external check.
    This covers lines 173-175 in main.py.
    """
    # Mock database to return success
    from app import database
    class MockDB:
        def execute(self, query): pass
        def close(self): pass
    monkeypatch.setattr(database, "SessionLocal", lambda: MockDB())

    # Mock Netlify to raise an exception (e.g. timeout)
    respx.get("https://sga-v1.netlify.app/").mock(side_effect=httpx.ConnectError("Connection failed"))

    response = client.get("/health?check_external=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["netlify"]["status"] == "unreachable"
    assert "Connection failed" in data["netlify"]["error"]
