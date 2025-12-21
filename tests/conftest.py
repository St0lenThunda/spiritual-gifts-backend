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
    yield
    app.dependency_overrides.clear()

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
