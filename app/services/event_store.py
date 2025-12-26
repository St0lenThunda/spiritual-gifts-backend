"""
Event Store service for webhook idempotency.
Uses Redis to track processed Stripe event IDs with 24-hour TTL.
"""
import redis
import logging
from ..config import settings

logger = logging.getLogger(__name__)

# TTL for processed events (24 hours)
EVENT_TTL_SECONDS = 24 * 60 * 60

# Redis key prefix for processed events
KEY_PREFIX = "stripe_event:"


def get_redis_client():
    """Get Redis client, returns None if unavailable."""
    if not settings.REDIS_ENABLED:
        return None
    
    try:
        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis unavailable for event store: {e}")
        return None


def is_event_processed(event_id: str) -> bool:
    """
    Check if a Stripe event has already been processed.
    Returns False if Redis is unavailable (fail-open).
    """
    client = get_redis_client()
    if not client:
        logger.warning("Event store unavailable - allowing event processing (fail-open)")
        return False
    
    try:
        key = f"{KEY_PREFIX}{event_id}"
        return client.exists(key) > 0
    except Exception as e:
        logger.error(f"Error checking event {event_id}: {e}")
        return False


def mark_event_processed(event_id: str) -> bool:
    """
    Mark a Stripe event as processed with 24-hour TTL.
    Returns True if successfully marked, False otherwise.
    """
    client = get_redis_client()
    if not client:
        logger.warning("Event store unavailable - event not marked")
        return False
    
    try:
        key = f"{KEY_PREFIX}{event_id}"
        client.setex(key, EVENT_TTL_SECONDS, "1")
        logger.info(f"Marked event {event_id} as processed (TTL: {EVENT_TTL_SECONDS}s)")
        return True
    except Exception as e:
        logger.error(f"Error marking event {event_id}: {e}")
        return False
