from fastapi import APIRouter

from app.api.projects import router as projects_router

api_router = APIRouter()
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
