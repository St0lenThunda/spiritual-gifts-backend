from slowapi import Limiter
from slowapi.util import get_remote_address
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Shared rate limiting state via Redis with memory fallback
def get_limiter():
    if not settings.REDIS_ENABLED:
        logger.info("Rate limiter using memory storage (Redis explicitly disabled)")
        return Limiter(key_func=get_remote_address)
    
    try:
        # Try to ping Redis to see if it's actually alive
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        r.ping()
        
        logger.info("Rate limiter using Redis storage")
        return Limiter(
            key_func=get_remote_address,
            storage_uri=settings.REDIS_URL
        )
    except Exception as e:
        logger.warning(f"Redis unreachable for rate limiting ({e}). Falling back to memory storage.")
        return Limiter(key_func=get_remote_address)

limiter = get_limiter()
