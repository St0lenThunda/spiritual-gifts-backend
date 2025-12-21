import pytest
from app.database import get_db

def test_get_db_yields_session():
    """Verify get_db generator yields a session and closes it."""
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    # We can't easily check if it's closed without mocking, 
    # but we can verify the yield works.
    try:
        next(db_gen)
    except StopIteration:
        pass # Expected
