import pytest
from unittest.mock import MagicMock
from app.services.audit_service import AuditService
from app.models import LogEntry, User

def test_log_action_creates_entry():
    """Test that log_action creates a LogEntry with correct data."""
    mock_db = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "admin@example.com"
    mock_user.org_id = "uuid-123"

    entry = AuditService.log_action(
        db=mock_db,
        user=mock_user,
        action="test_action",
        target_type="test_target",
        target_id="999",
        details={"foo": "bar"}
    )

    assert isinstance(entry, LogEntry)
    assert entry.event == "test_action"
    assert entry.user_id == 1
    assert entry.context == {"foo": "bar"}
    assert entry.path == "audit:test_target:999"
    
    mock_db.add.assert_called_once_with(entry)
