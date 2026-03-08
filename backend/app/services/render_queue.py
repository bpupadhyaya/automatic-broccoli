from __future__ import annotations

from hashlib import sha256

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.pipeline import RenderJob, Shot
from app.models.project import Project
from app.schemas.render_job import RenderJobCreate, RenderJobRead
from app.services import job_state
from app.services.providers.luma import LumaProvider
from app.services.providers.runway import RunwayProvider
from app.services.providers.veo import VeoProvider

PROVIDERS = {
    "runway": RunwayProvider(),
    "veo": VeoProvider(),
    "luma": LumaProvider(),
}


def _should_fail(project_id: int, shot_code: str, attempt: int) -> bool:
    token = f"{project_id}:{shot_code}:{attempt}"
    return int(sha256(token.encode("utf-8")).hexdigest()[:2], 16) % 11 == 0


def _fallback_provider(primary_provider_name: str):
    for name, provider in PROVIDERS.items():
        if name != primary_provider_name:
            return provider
    return PROVIDERS["runway"]


def _to_render_job_read(job: RenderJob) -> RenderJobRead:
    return RenderJobRead(
        id=job.id,
        project_id=job.project_id,
        shot_id=job.shot_id,
        provider=job.provider,
        provider_job_id=job.provider_job_id,
        status=job.status,
        attempt_number=job.attempt_number,
        output_url=(job.output_url or job.raw_output_url),
        qc_status="pending",
        error_message=job.error_message,
    )


class RenderQueueService:
    """Queue, submit, and retry shot render jobs with provider fallbacks."""

    def __init__(self, db: Session):
        self.db = db

    def _next_attempt(self, shot_id: int) -> int:
        return (
            self.db.query(func.coalesce(func.max(RenderJob.attempt_number), 0))
            .filter(RenderJob.shot_id == shot_id)
            .scalar()
        ) + 1

    def _enqueue_model(self, payload: RenderJobCreate) -> RenderJob:
        shot = self.db.get(Shot, payload.shot_id)
        if not shot or shot.project_id != payload.project_id:
            raise ValueError(f"Shot {payload.shot_id} is not available for project {payload.project_id}")

        provider = PROVIDERS.get(payload.provider, PROVIDERS["runway"])
        attempt = self._next_attempt(shot.id)

        shot.status = job_state.RENDERING
        submission = provider.submit_generation(payload.prompt, payload.references, payload.duration_sec, payload.aspect_ratio)
        primary_job = RenderJob(
            project_id=payload.project_id,
            shot_id=payload.shot_id,
            provider=submission["provider"],
            provider_job_id=submission["job_id"],
            status=job_state.SUBMITTED,
            attempt_number=attempt,
            estimated_duration_sec=submission["estimated_duration_sec"],
        )
        self.db.add(primary_job)

        if _should_fail(payload.project_id, shot.shot_code, attempt):
            primary_job.status = job_state.FAILED
            primary_job.error_message = "Synthetic provider failure in MVP queue simulation"
            shot.status = job_state.FAILED
            self.db.add(shot)
            self.db.flush()

            fallback_provider = _fallback_provider(submission["provider"])
            fallback_submission = fallback_provider.submit_generation(
                payload.prompt,
                payload.references,
                payload.duration_sec,
                payload.aspect_ratio,
            )
            fallback_attempt = attempt + 1
            fallback_url = (
                f"s3://mock/remix/projects/{payload.project_id}/shots/{shot.shot_code}/attempt_{fallback_attempt}.mp4"
            )
            fallback_job = RenderJob(
                project_id=payload.project_id,
                shot_id=payload.shot_id,
                provider=fallback_submission["provider"],
                provider_job_id=fallback_submission["job_id"],
                status=job_state.SUCCEEDED,
                attempt_number=fallback_attempt,
                raw_output_url=fallback_url,
                output_url=fallback_url,
                estimated_duration_sec=fallback_submission["estimated_duration_sec"],
            )
            shot.status = job_state.SUCCEEDED
            shot.approved_clip_url = fallback_url
            self.db.add(fallback_job)
            self.db.add(shot)
            self.db.flush()
            return fallback_job

        clip_url = f"s3://mock/remix/projects/{payload.project_id}/shots/{shot.shot_code}/attempt_{attempt}.mp4"
        primary_job.status = job_state.SUCCEEDED
        primary_job.raw_output_url = clip_url
        primary_job.output_url = clip_url
        shot.status = job_state.SUCCEEDED
        shot.approved_clip_url = clip_url
        self.db.add(shot)
        self.db.flush()
        return primary_job

    def enqueue(self, payload: RenderJobCreate) -> RenderJobRead:
        return _to_render_job_read(self._enqueue_model(payload))

    def retry(self, render_job_id: str) -> RenderJobRead:
        previous_job = self.db.get(RenderJob, int(render_job_id))
        if not previous_job:
            raise ValueError(f"Render job {render_job_id} not found")

        shot = self.db.get(Shot, previous_job.shot_id)
        if not shot:
            raise ValueError(f"Shot {previous_job.shot_id} not found")

        return _to_render_job_read(
            self._enqueue_model(
                RenderJobCreate(
                    project_id=previous_job.project_id,
                    shot_id=shot.id,
                    provider=previous_job.provider,
                    prompt=shot.prompt,
                    references=shot.references_json,
                    duration_sec=shot.duration_sec,
                )
            )
        )


def render_project_shots(db: Session, project: Project, shots: list[Shot], provider_name: str) -> list[RenderJob]:
    queue = RenderQueueService(db)
    jobs: list[RenderJob] = []

    for shot in shots:
        job = queue._enqueue_model(
            RenderJobCreate(
                project_id=project.id,
                shot_id=shot.id,
                provider=provider_name,
                prompt=shot.prompt,
                references=shot.references_json,
                duration_sec=shot.duration_sec,
            )
        )
        jobs.append(job)

    db.commit()
    for job in jobs:
        db.refresh(job)
    return jobs
