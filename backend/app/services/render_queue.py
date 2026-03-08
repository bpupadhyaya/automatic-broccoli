from __future__ import annotations

from hashlib import sha256

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.pipeline import RenderJob, Shot
from app.models.project import Project
from app.services import job_state
from app.services.provider_luma import LumaProvider
from app.services.provider_runway import RunwayProvider
from app.services.provider_veo import VeoProvider

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


def render_project_shots(db: Session, project: Project, shots: list[Shot], provider_name: str) -> list[RenderJob]:
    provider = PROVIDERS.get(provider_name, PROVIDERS["runway"])
    jobs: list[RenderJob] = []

    for shot in shots:
        attempt = (
            db.query(func.coalesce(func.max(RenderJob.attempt_number), 0))
            .filter(RenderJob.shot_id == shot.id)
            .scalar()
        ) + 1

        shot.status = job_state.RENDERING
        submission = provider.generate_shot(shot.prompt, shot.references_json, shot.duration_sec)

        job = RenderJob(
            project_id=project.id,
            shot_id=shot.id,
            provider=submission["provider"],
            provider_job_id=submission["job_id"],
            status=job_state.RENDERING,
            attempt_number=attempt,
            estimated_duration_sec=submission["estimated_duration_sec"],
        )

        if _should_fail(project.id, shot.shot_code, attempt):
            job.status = job_state.FAILED
            shot.status = job_state.FAILED
            db.add(job)
            jobs.append(job)

            fallback_provider = _fallback_provider(submission["provider"])
            fallback_submission = fallback_provider.generate_shot(shot.prompt, shot.references_json, shot.duration_sec)
            fallback_attempt = attempt + 1
            fallback_url = (
                f"s3://mock/remix/projects/{project.id}/shots/{shot.shot_code}/attempt_{fallback_attempt}.mp4"
            )
            fallback_job = RenderJob(
                project_id=project.id,
                shot_id=shot.id,
                provider=fallback_submission["provider"],
                provider_job_id=fallback_submission["job_id"],
                status=job_state.SUCCEEDED,
                attempt_number=fallback_attempt,
                raw_output_url=fallback_url,
                estimated_duration_sec=fallback_submission["estimated_duration_sec"],
            )
            shot.status = job_state.SUCCEEDED
            shot.approved_clip_url = fallback_url
            db.add(fallback_job)
            jobs.append(fallback_job)
        else:
            clip_url = f"s3://mock/remix/projects/{project.id}/shots/{shot.shot_code}/attempt_{attempt}.mp4"
            job.status = job_state.SUCCEEDED
            job.raw_output_url = clip_url
            shot.status = job_state.SUCCEEDED
            shot.approved_clip_url = clip_url
            db.add(job)
            jobs.append(job)

        db.add(shot)

    db.commit()
    for job in jobs:
        db.refresh(job)
    return jobs
