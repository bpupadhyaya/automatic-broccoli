from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pipeline import RenderJob
from app.schemas.render_job import RenderJobRead
from app.services import job_state

router = APIRouter()


@router.get("/{job_id}", response_model=RenderJobRead)
def get_render_job(job_id: int, db: Session = Depends(get_db)) -> RenderJobRead:
    job = db.get(RenderJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Render job {job_id} not found")
    if job.status in {job_state.QC_APPROVED, job_state.APPROVED}:
        qc_status = "approved"
    elif job.status in {job_state.QC_REJECTED, job_state.REJECTED_QC}:
        qc_status = "rejected"
    else:
        qc_status = "pending"

    return RenderJobRead(
        id=job.id,
        project_id=job.project_id,
        shot_id=job.shot_id,
        provider=job.provider,
        provider_job_id=job.provider_job_id,
        status=job.status,
        attempt_number=job.attempt_number,
        output_url=(job.output_url or job.raw_output_url),
        qc_status=qc_status,
        error_message=job.error_message,
    )
