from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database import Base, engine
from .routers import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
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

app.include_router(router)

@app.get("/health")
def health():
    """
    Minimal health check endpoint to keep the server warm.
    Does not touch the database or load heavy dependencies.
    """
    return {"status": "ok"}
