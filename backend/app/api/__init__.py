from fastapi import APIRouter

from app.api.projects import router as projects_router
from app.api.render_jobs import router as render_jobs_router

api_router = APIRouter()
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(render_jobs_router, prefix="/render-jobs", tags=["render-jobs"])
