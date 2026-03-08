from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pipeline import RenderJob
from app.schemas.pipeline import RenderJobResponse

router = APIRouter()


@router.get("/{job_id}", response_model=RenderJobResponse)
def get_render_job(job_id: int, db: Session = Depends(get_db)) -> RenderJob:
    job = db.get(RenderJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Render job {job_id} not found")
    return job
