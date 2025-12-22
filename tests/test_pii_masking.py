import pytest
from app.logging_setup import mask_email, pii_masking_processor

def test_mask_email():
    assert mask_email("johndoe@example.com") == "j***@example.com"
    assert mask_email("long.name@company.co.uk") == "l***@company.co.uk"
    assert mask_email("a@b.com") == "***@b.com"
    assert mask_email("invalid-email") == "invalid-email"
    assert mask_email(None) is None

def test_pii_masking_processor_masks_user_email():
    logger = None
    method_name = "info"
    
    # Case 1: Email in event_dict
    event_dict = {"event": "login", "user_email": "test@example.com"}
    processed = pii_masking_processor(logger, method_name, event_dict)
    assert processed["user_email"] == "t***@example.com"
    
    # Case 2: No email
    event_dict = {"event": "logout"}
    processed = pii_masking_processor(logger, method_name, event_dict)
    assert "user_email" not in processed

    # Case 3: Invalid data type (just in case)
    event_dict = {"user_email": 123}
    processed = pii_masking_processor(logger, method_name, event_dict)
    assert processed["user_email"] == 123
