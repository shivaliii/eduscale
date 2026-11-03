"""API router — assembles all v1 route modules."""
from fastapi import APIRouter
from app.api.v1 import auth, students, teachers, experiments

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(teachers.router)
api_router.include_router(experiments.router)
