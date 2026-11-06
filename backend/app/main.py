from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import engine
from app.routes import bots, runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Browser Bot Platform API",
    description="Extensible browser automation and monitoring platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for local development and Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bots.router, prefix="/api")
app.include_router(runs.router, prefix="/api")


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for Docker and monitoring."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }
