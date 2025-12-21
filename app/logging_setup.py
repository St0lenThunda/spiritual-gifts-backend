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

def db_logger_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processor that writes log entries to the database.
    """
    # We use the current SessionLocal from database module (handles monkeypatching in tests)
    db = database.SessionLocal()
    try:
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
        db.add(log_entry)
        db.commit()
    except Exception as e:
        # Avoid infinite recursion if DB logging fails
        sys.stderr.write(f"Failed to write log to DB: {str(e)}\n")
    finally:
        db.close()
        
    return event_dict

def setup_logging():
    """Configure structlog. Can be called manually if needed to reconfigure."""
    processors = [
        structlog.contextvars.merge_contextvars,
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
