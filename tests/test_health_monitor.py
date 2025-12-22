import pytest
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_success():
    """
    Test that the health check returns 200 and 'connected' when DB is reachable.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "timestamp" in data

def test_health_check_failure(monkeypatch):
    """
    Test that the health check returns 503 and 'disconnected' when DB raises an exception.
    """
    from app import main
    
    # Mock SessionLocal to raise an exception
    def mock_session_local():
        raise Exception("Database Connection Error")
        
    monkeypatch.setattr("app.database.SessionLocal", mock_session_local)
    
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "disconnected"
    assert data["error"] == "Database Connection Error"
