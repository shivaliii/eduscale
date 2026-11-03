"""EduScale FastAPI Application Entry Point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.config import get_settings
from app.database import engine, Base
from app.api.router import api_router
# Import all models so they are registered with SQLAlchemy
from app.models import *  # noqa: F401, F403

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup if they don't exist."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="EduScale API",
    description="AI-Based Personalized Learning and Predictive Cloud Resource Optimization",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

# Serve avatar images
avatars_dir = os.path.join(os.path.dirname(__file__), "..", "static", "avatars")
if os.path.isdir(avatars_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static")), name="static")


@app.get("/health")
def health_check():
    from sqlalchemy import text
    from app.database import SessionLocal
    db_status = "connected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "database": db_status,
        "model_status": "demo_mode" if settings.DEMO_MODE else "available",
        "demo_mode": settings.DEMO_MODE,
        "version": settings.APP_VERSION,
    }
