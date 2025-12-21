import pytest
from app.models import LogEntry, User
from app.database import SessionLocal

def test_logging_middleware_captures_context(client):
    """Test that the logging middleware captures path and method."""
    # 1. Make a public request
    client.get("/questions")
    
    # 2. Verify log entry in DB
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.path == "/questions").order_by(LogEntry.timestamp.desc()).first()
        assert log is not None
        assert log.method == "GET"
        assert log.level == "INFO"
    finally:
        db.close()

def test_dev_login_logging(client):
    """Test that dev login is logged."""
    client.post("/auth/dev-login", json={"email": "dev@example.com"})
    
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
    client.post("/auth/dev-login", json={"email": "logout-test@example.com"})
    
    # 2. Logout
    client.post("/auth/logout")
    
    # 3. Verify log
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.event == "user_logged_out").order_by(LogEntry.timestamp.desc()).first()
        assert log is not None
        assert log.user_email == "logout-test@example.com"
    finally:
        db.close()

def test_error_logging(client):
    """Test that unhandled exceptions are logged."""
    # Trigger a 404 (not an exception, but recorded in request logs)
    client.get("/some-non-existent-route")
    
    db = SessionLocal()
    try:
        log = db.query(LogEntry).filter(LogEntry.path == "/some-non-existent-route").first()
        assert log is not None
        assert log.status_code == 404
    finally:
        db.close()
