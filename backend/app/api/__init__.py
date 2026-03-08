from fastapi import APIRouter

from app.api.characters import router as characters_router
from app.api.exports import router as exports_router
from app.api.projects import router as projects_router
from app.api.render_jobs import router as render_jobs_router
from app.api.shots import router as shots_router

api_router = APIRouter()
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(shots_router, prefix="/projects", tags=["shots"])
api_router.include_router(exports_router, prefix="/projects", tags=["exports"])
api_router.include_router(render_jobs_router, prefix="/render-jobs", tags=["render-jobs"])
api_router.include_router(characters_router, prefix="", tags=["characters"])
