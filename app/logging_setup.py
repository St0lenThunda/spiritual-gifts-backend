import structlog
import logging
import sys
from typing import Any, Dict
from datetime import datetime
from contextvars import ContextVar
from sqlalchemy.orm import Session
from . import database
from .models import LogEntry

user_id_ctx: ContextVar[int] = ContextVar("user_id", default=None)
user_email_ctx: ContextVar[str] = ContextVar("user_email", default=None)
path_ctx: ContextVar[str] = ContextVar("path", default=None)
method_ctx: ContextVar[str] = ContextVar("method", default=None)
request_id_ctx: ContextVar[str] = ContextVar("request_id", default=None)

def mask_email(email: str) -> str:
    """
    Mask an email address to protect PII.
    Example: 'johndoe@example.com' -> 'j***@example.com'
    """
    if not email or "@" not in email:
        return email
    
    try:
        local_part, domain = email.split("@", 1)
        if len(local_part) <= 1:
            masked_local = "*" * 3
        else:
            masked_local = local_part[0] + "***"
        return f"{masked_local}@{domain}"
    except Exception:
        return email

def pii_masking_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processor that masks PII fields (like user_email) in the event dict.
    Must run AFTER merge_contextvars so that it catches context-injected values too.
    """
    if "user_email" in event_dict and isinstance(event_dict["user_email"], str):
        event_dict["user_email"] = mask_email(event_dict["user_email"])
    
    return event_dict

def db_logger_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processor that writes log entries to the database.
    """
    # We use the current SessionLocal from database module (handles monkeypatching in tests)
    try:
        with database.SessionLocal() as db:
            # Extract fields from event_dict and context
            # Prioritize event_dict (where merge_contextvars puts things) then fall back to contextvars
            u_id = event_dict.get("user_id") or user_id_ctx.get()
            u_email = event_dict.get("user_email") or user_email_ctx.get()
            
            log_entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=method_name.upper(),
                event=event_dict.get("event"),
                user_id=u_id,
                user_email=u_email,
                path=path_ctx.get(),
                method=method_ctx.get(),
                status_code=event_dict.get("status_code"),
                request_id=event_dict.get("request_id") or request_id_ctx.get(),
                exception=event_dict.get("exception"),
                context={k: v for k, v in event_dict.items() if k not in ["event", "status_code", "exception", "user_id", "user_email", "request_id"]}
            )
            
            # SKIP ANONYMOUS INFO LOGS
            # We don't want to fill the DB with every public page view or health check
            is_anonymous = (u_id is None and u_email is None)
            is_info = (log_entry.level == "INFO")
            
            if is_anonymous and is_info:
                return event_dict

            db.add(log_entry)
            db.commit()
    except Exception as e:
        # Avoid infinite recursion if DB logging fails
        sys.stderr.write(f"Failed to write log to DB: {str(e)}\n")
        
    return event_dict

def setup_logging():
    """Configure structlog. Can be called manually if needed to reconfigure."""
    processors = [
        structlog.contextvars.merge_contextvars,
        pii_masking_processor, # Mask PII before any other processing
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        db_logger_processor,
    ]

    if sys.stderr.isatty():
        # In a terminal, use colorized output
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # In production/non-tty, use JSON
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

# Automatically configure on import to ensure any loggers created later recognize the config
setup_logging()

# Export a default logger for convenience
logger = structlog.get_logger()
