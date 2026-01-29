# app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import redis_client
from app.api import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print(f"Starting {settings.APP_NAME}...")

    # Connect to Redis
    await redis_client.connect()
    print("Redis connected")

    # Initialize database (optional: create tables if not using Alembic)
    # await init_db()
    # print("Database initialized")

    yield

    # Shutdown
    print("Shutting down...")
    await redis_client.disconnect()
    await close_db()
    print("Cleanup completed")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered business automation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
    }
