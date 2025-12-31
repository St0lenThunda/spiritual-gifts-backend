import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set dummy environment variables for settings initialization
# Must be set BEFORE importing app modules that use settings
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["NEON_API_KEY"] = "dummy"
os.environ["NEON_PROJECT_ID"] = "dummy"
os.environ["REDIS_ENABLED"] = "False"
os.environ["CSRF_SECRET_KEY"] = "test-csrf-secret-key-for-testing"

import app.database as db_app
from app.main import app
from app.database import Base, get_db

# Test database setup (using in-memory sqlite for speed and isolation)
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Monkeypatch database globally for tests
db_app.engine = engine
db_app.SessionLocal = TestingSessionLocal

@pytest.fixture(autouse=True)
def setup_db():
    """Create and drop database tables for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def clear_overrides():
    """Clear dependency overrides and reset limiter before and after each test."""
    app.dependency_overrides.clear()
    # Reset limiter to avoid cross-test interference
    from app.limiter import limiter
    limiter.reset()
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = True
        app.state.limiter.reset()
    yield
    # Also reset after test
    limiter.reset()
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def skip_csrf_validation(monkeypatch):
    """Skip CSRF validation in tests by mocking validate_csrf to be a no-op."""
    from fastapi_csrf_protect import CsrfProtect
    
    async def mock_validate_csrf(self, request):
        pass  # No-op: skip CSRF validation in tests
    
    monkeypatch.setattr(CsrfProtect, "validate_csrf", mock_validate_csrf)

@pytest.fixture
def db():
    """Provide a database session for tests."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    """Provide a test client with db override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

@pytest.fixture
def test_user(db):
    """Create a test user in the database."""
    from app.models import User
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture(autouse=True)
def init_cache():
    """Initialize fastapi-cache for tests."""
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    yield

@pytest.fixture
def admin_user(db):
    """Create a test admin user."""
    from app.models import User
    user = User(email="admin@example.com", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def admin_token_headers(admin_user):
    """Return auth headers for admin user."""
    from app.neon_auth import create_access_token
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}
