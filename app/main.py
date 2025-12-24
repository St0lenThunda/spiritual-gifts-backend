from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database import Base, engine
from .routers import router
from .limiter import limiter
from .routers import admin
from .services import load_questions, load_gifts
from .config import settings
from .logging_setup import setup_logging, logger, path_ctx, method_ctx, user_id_ctx, user_email_ctx, request_id_ctx
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response, Depends
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # HSTS - 1 year, includes subdomains
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy (Basic restrictive)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://www.gravatar.com; "
            "connect-src 'self' http://localhost:5173 http://localhost:5174 http://127.0.0.1:5173 http://127.0.0.1:5174 "
            "https://spiritual-gifts-backend-d82f.onrender.com https://sga-v1.netlify.app;"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

from pydantic_settings import BaseSettings
class CsrfSettings(BaseSettings):
    csrf_secret_key: str = settings.CSRF_SECRET_KEY
    csrf_cookie_samesite: str = "lax"
    csrf_cookie_secure: bool = False if settings.ENV == "development" else True
    csrf_cookie_httponly: bool = False  # Allow frontend to read for header inclusion

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database initialization
    # In development, create_all() is convenient for rapid prototyping
    # In production, use Alembic migrations: `alembic upgrade head`
    if settings.ENV == "development":
        Base.metadata.create_all(bind=engine)
    
    # Initialize Redis Cache with Memory Fallback
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend
    
    cache_initialized = False
    if settings.REDIS_ENABLED:
        try:
            import redis
            from fastapi_cache.backends.redis import RedisBackend
            # use a sync connection to check ping
            r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
            if r.ping():
                import redis.asyncio as aioredis
                redis_instance = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
                FastAPICache.init(RedisBackend(redis_instance), prefix="fastapi-cache")
                logger.info("Redis cache initialized successfully")
                cache_initialized = True
        except Exception as e:
            logger.info(f"Redis unreachable at {settings.REDIS_URL}, falling back to in-memory caching: {e}")
    
    if not cache_initialized:
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
        if not settings.REDIS_ENABLED:
            logger.info("Memory cache initialized (Redis explicitly disabled)")
        else:
            logger.info("Memory cache initialized (Redis unreachable)")
    
    yield

# Initialize structured logging
# setup_logging() is automatically called on import from app.logging_setup

app = FastAPI(
    title="Spiritual Gifts Assessment API",
    description="Backend service for user authentication (Magic Links) and spiritual gifts assessment processing.",
    version="1.1.0",
    lifespan=lifespan
)
app.state.limiter = limiter


# CSRF configuration is done above via get_csrf_config

@app.middleware("http")
async def logging_middleware(request, call_next):
    """
    Middleware to set request context for logging and catch/log exceptions.
    """
    path_ctx.set(request.url.path)
    method_ctx.set(request.method)
    
    # Handle Correlation ID
    import uuid
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_ctx.set(request_id)
    
    # Set ID for structlog in all subsequent logs for this request
    import structlog
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    # user_id and user_email are set in the auth dependency (neon_auth.py)
    
    import time
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Add Request-ID to headers
        response.headers["X-Request-ID"] = request_id
        
        # Log successful request
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration=duration
        )
        
        return response
    except Exception as e:
        duration = time.time() - start_time
        import traceback
        error_msg = traceback.format_exc()
        logger.error(
            "unhandled_exception",
            exception=error_msg,
            error=str(e),
            duration=duration,
            status_code=500
        )
        # We return a generic 500 response here to ensure the middleware
        # doesn't let the exception crawl up to Starlette's default text handler
        from fastapi.responses import JSONResponse
        content = {
            "detail": "An unexpected server error occurred. Our team has been notified.",
            "request_id": request_id
        }
        return JSONResponse(
            status_code=500,
            content=content,
            headers={"X-Request-ID": request_id}
        )
@app.exception_handler(CsrfProtectError)
async def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    """
    Handle CSRF violations by returning 403 Forbidden.
    """
    logger.warning(
        "csrf_violation",
        client_ip=request.client.host if request.client else "unknown",
        path=request.url.path,
        error=exc.message
    )
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": "CSRF validation failed. Please refresh and try again."}
    )

# CSRF token endpoint moved to routers/__init__.py

async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Log rate limit breaches before returning the 429 response.
    """
    logger.warning(
        "rate_limit_exceeded",
        client_ip=request.client.host if request.client else "unknown",
        path=request.url.path,
        limit=str(exc.detail)
    )
    return _rate_limit_exceeded_handler(request, exc)

app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "https://sga-v1.netlify.app",
    "https://spiritual-gifts-backend-d82f.onrender.com"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Security Headers Middleware LAST to ensure it wraps everything
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

# Multi-tenancy routes
from .routers import organizations
app.include_router(organizations.router, prefix="/api/v1")

@app.get("/health")
@app.get("/api/v1/health")
async def health(check_external: bool = False):
    """
    Health check endpoint that verifies server and database status.
    Returns 503 if database is unavailable to ensure load balancers take us out of rotation.
    Optionally checks external services (Netlify) if check_external=True.
    """
    from app import __version__
    
    status = {
        "status": "ok",
        "version": __version__,
        "database": "unknown",
        "timestamp": None
    }
    
    import time
    from sqlalchemy import text
    from .database import SessionLocal

    status["timestamp"] = time.time()
    
    # 1. Check Database
    try:
        # Check database connectivity
        with SessionLocal() as db:
            db_start = time.time()
            db.execute(text("SELECT 1"))
            db_latency = (time.time() - db_start) * 1000  # Convert to ms
            status["database"] = "connected"
            status["database_latency_ms"] = round(db_latency, 2)
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        status["status"] = "degraded"
        status["database"] = "disconnected"
        status["database_latency_ms"] = None
        status["error"] = str(e)
        
    # 2. Check External Services (Optional)
    if check_external:
        import httpx
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("https://sga-v1.netlify.app/")
                duration = (time.time() - start_time) * 1000
                status["netlify"] = {
                    "status": "ok" if resp.status_code == 200 else "error",
                    "code": resp.status_code,
                    "latency_ms": round(duration, 2)
                }
        except Exception as e:
            logger.error("external_health_check_failed", service="netlify", error=str(e))
            status["netlify"] = {
                "status": "unreachable",
                "error": str(e),
                "latency_ms": None
            }
            # Only downgrade overall status if DB is fine but external is down?
            # For now, let's keep overall status focused on BACKEND health.
            # But frontend can use the specific 'netlify' field to show red/green.

    if status["database"] != "connected":
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=status)
        
    return status
