import pytest
from app.models import LogEntry, User
from app.database import SessionLocal

def test_logging_middleware_captures_context(client):
    """Test that the logging middleware captures path and method."""
    # 1. Make a public request
    client.get("/api/v1/questions")
    
    # 2. Verify log entry in DB
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.path == "/api/v1/questions").order_by(LogEntry.timestamp.desc()).first()
        assert log is not None
        assert log.method == "GET"
        assert log.level == "INFO"
    finally:
        db.close()

def test_dev_login_logging(client):
    """Test that dev login is logged."""
    client.post("/api/v1/auth/dev-login", json={"email": "dev@example.com"})
    
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.event == "dev_login_successful").first()
        assert log is not None
        assert log.user_email == "dev@example.com"
    finally:
        db.close()

def test_logout_logging_with_context(client):
    """Test that logout is logged with user context."""
    # 1. Login
    client.post("/api/v1/auth/dev-login", json={"email": "logout-test@example.com"})
    
    # 2. Logout
    client.post("/api/v1/auth/logout")
    
    # 3. Verify log
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.event == "user_logged_out").order_by(LogEntry.timestamp.desc()).first()
        assert log is not None
        assert log.user_email == "logout-test@example.com"
    finally:
        db.close()

def test_request_id_correlation(client):
    """Test that X-Request-ID header is captured in logs."""
    request_id = "test-correlation-id-123"
    client.get("/api/v1/health", headers={"X-Request-ID": request_id})
    
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.request_id == request_id).first()
        assert log is not None
        assert log.path == "/api/v1/health"
        assert log.request_id == request_id
    finally:
        db.close()
def test_unauthorized_access_logging(client):
    """Test that unauthorized access attempts are logged."""
    # Try to access a protected route without a token
    client.get("/api/v1/auth/me")
    
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.event == "unauthorized_access").first()
        assert log is not None
        assert log.context.get("reason") == "missing_token"
        assert log.path == "/api/v1/auth/me"
    finally:
        db.close()

def test_rate_limit_logging(client):
    """Test that rate limit breaks are logged."""
    # The limit is 3/10min for /api/v1/auth/send-link
    for _ in range(3):
        client.post("/api/v1/auth/send-link", json={"email": "rate@test.com"})
    
    # This 4th one should trigger rate limit
    response = client.post("/api/v1/auth/send-link", json={"email": "rate@test.com"})
    assert response.status_code == 429
    
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.event == "rate_limit_exceeded").first()
        assert log is not None
        assert log.path == "/api/v1/auth/send-link"
        assert "limit" in log.context
    finally:
        db.close()
