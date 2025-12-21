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
from fastapi import Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database initialization
    # In development, create_all() is convenient for rapid prototyping
    # In production, use Alembic migrations: `alembic upgrade head`
    if settings.ENV == "development":
        Base.metadata.create_all(bind=engine)
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
        
        # Log successful request
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration=duration
        )
        
        return response
    except (HTTPException, RequestValidationError):
        raise
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
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected server error occurred. Our team has been notified."}
        )
@app.exception_handler(RateLimitExceeded)
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

# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
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

app.include_router(router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

@app.get("/health")
def health():
    """
    Minimal health check endpoint to keep the server warm.
    Does not touch the database or load heavy dependencies.
    """
    return {"status": "ok"}
