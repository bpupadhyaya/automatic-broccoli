from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_latest_manifest, get_project_or_404
from app.config import settings
from app.database import SessionLocal, get_db
from app.models.project import Project
from app.schemas.project import (
    ManifestResponse,
    ProjectCreate,
    ProjectDetail,
    ProjectListItem,
    ProjectPlanResponse,
    QuickDownloadItem,
    QuickConversionProgressResponse,
    QuickConversionOutputResponse,
    QuickProjectCreateRequest,
)
from app.services.local_quick_remixer import LocalQuickRemixService
from app.services.quick_conversion_defaults import build_quick_project_payload
from app.services.remix_planner import run_remix_planner
from app.services.youtube_uploader import YouTubeUploaderService

router = APIRouter()


def _create_project_record(payload: ProjectCreate, db: Session) -> Project:
    payload_dict = payload.model_dump(mode="json")
    project = Project(**payload_dict)
    project.status = "created"
    project.config_json = payload_dict
    return project


def _get_quick_output_meta(project: Project) -> dict:
    config = project.config_json or {}
    quick = config.get("quick_conversion")
    if not isinstance(quick, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quick conversion output is not available for this project.",
        )
    output_video_path = quick.get("output_video_path")
    output_dir = quick.get("output_dir")
    if not output_video_path or not output_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quick conversion output has not been generated yet.",
        )
    return quick


def _build_quick_download_item(project: Project, quick_meta: dict) -> QuickDownloadItem | None:
    output_video_path = quick_meta.get("output_video_path")
    if not isinstance(output_video_path, str) or not output_video_path.strip():
        return None

    output_path = Path(output_video_path).expanduser()
    if not output_path.exists() or not output_path.is_file():
        return None

    title_candidate = quick_meta.get("youtube_title") or quick_meta.get("download_filename")
    if isinstance(title_candidate, str) and title_candidate.strip():
        video_title = title_candidate.strip()
    else:
        video_title = f"Project {project.id} Quick Remix"

    remix_profile = str(quick_meta.get("remix_profile") or "unknown").replace("_", " ").title()
    cast_preset = str(quick_meta.get("cast_preset") or "mixed").replace("_", " ").title()
    heritage_mode = str(quick_meta.get("heritage_mode") or "preserve").replace("_", " ").title()

    remix_details = (
        f"{remix_profile} profile | Genre: {project.remix_genre} | "
        f"Cast: {cast_preset} | Heritage: {heritage_mode}"
    )
    download_url = str(quick_meta.get("download_url") or f"{settings.api_prefix}/projects/{project.id}/quick-convert/download")

    return QuickDownloadItem(
        project_id=project.id,
        video_title=video_title,
        remix_details=remix_details,
        download_url=download_url,
        created_at=project.created_at,
    )


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _quick_progress_step(stage: str, detail: str, progress: float) -> dict[str, Any]:
    clamped = max(0.0, min(1.0, float(progress)))
    return {
        "timestamp": _utc_iso_now(),
        "stage": stage,
        "detail": detail,
        "progress": round(clamped, 4),
    }


def _persist_quick_runtime_state(
    db: Session,
    project: Project,
    quick_meta: dict[str, Any],
    *,
    status_value: str,
) -> None:
    project.status = status_value
    project.config_json = {**(project.config_json or {}), "quick_conversion": quick_meta}
    flag_modified(project, "config_json")
    db.add(project)
    db.commit()


def _run_quick_convert_job(project_id: int, payload_data: dict[str, Any]) -> None:
    payload = QuickProjectCreateRequest.model_validate(payload_data)

    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            return

        config = project.config_json or {}
        quick_meta_raw = config.get("quick_conversion")
        quick_meta: dict[str, Any] = quick_meta_raw if isinstance(quick_meta_raw, dict) else {}
        existing_steps = quick_meta.get("processing_steps")
        processing_steps: list[dict[str, Any]] = existing_steps if isinstance(existing_steps, list) else []
        quick_meta["processing_steps"] = processing_steps

        def persist_progress_step(step: dict[str, Any]) -> None:
            processing_steps.append(step)
            quick_meta["processing_steps"] = processing_steps[-240:]
            quick_meta["execution"] = "running"
            quick_meta["current_stage"] = str(step.get("stage") or "Running")
            step_progress = step.get("progress")
            if isinstance(step_progress, (float, int)):
                quick_meta["progress"] = round(max(0.0, min(1.0, float(step_progress))), 4)
            quick_meta.pop("execution_error", None)
            _persist_quick_runtime_state(db, project, quick_meta, status_value="processing")

        persist_progress_step(
            _quick_progress_step(
                "Queued",
                "Quick conversion worker started.",
                quick_meta.get("progress", 0.02),
            )
        )

        try:
            output_artifacts = LocalQuickRemixService().run(
                project=project,
                local_output_dir=payload.local_output_dir,
                remix_profile=payload.remix_profile,
                cast_preset=payload.cast_preset,
                heritage_mode=payload.heritage_mode,
                progress_callback=persist_progress_step,
            )
            quick_meta.update(
                {
                    "execution": "completed",
                    **output_artifacts,
                    "download_url": f"{settings.api_prefix}/projects/{project.id}/quick-convert/download",
                    "progress": 1.0,
                    "current_stage": "Completed",
                }
            )
            project.status = "exported"

            if payload.allow_youtube_upload:
                upload_title = payload.youtube_title or f"AI Remix Project {project.id}"
                upload_description = payload.youtube_description or (
                    f"Auto-generated quick remix export for project {project.id}."
                )
                quick_meta["youtube_upload"] = YouTubeUploaderService().upload(
                    video_path=output_artifacts["output_video_path"],
                    title=upload_title,
                    description=upload_description,
                    privacy_status=payload.youtube_privacy_status,
                )
        except Exception as exc:
            quick_meta["execution"] = "failed"
            quick_meta["execution_error"] = str(exc)
            quick_meta["progress"] = max(float(quick_meta.get("progress") or 0.0), 0.01)
            quick_meta["current_stage"] = "Failed"
            processing_steps.append(
                _quick_progress_step(
                    "Failed",
                    f"Quick conversion failed: {exc}",
                    quick_meta["progress"],
                )
            )
            quick_meta["processing_steps"] = processing_steps[-240:]
            project.status = "failed"

        project.config_json = {**(project.config_json or {}), "quick_conversion": quick_meta}
        flag_modified(project, "config_json")
        db.add(project)
        db.commit()


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = _create_project_record(payload, db)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/quick-convert", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def quick_convert_project(
    payload: QuickProjectCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Project:
    project_payload = build_quick_project_payload(
        target_original_video_url=str(payload.target_original_video_url),
        example_original_video_url=str(payload.example_original_video_url),
        example_remix_video_url=str(payload.example_remix_video_url),
        remix_profile=payload.remix_profile,
        cast_preset=payload.cast_preset,
        heritage_mode=payload.heritage_mode,
    )
    project = _create_project_record(project_payload, db)
    quick_meta = {
        "enabled": True,
        "remix_profile": payload.remix_profile,
        "cast_preset": payload.cast_preset,
        "heritage_mode": payload.heritage_mode,
        "auto_generate_plan": payload.auto_generate_plan,
        "run_end_to_end": payload.run_end_to_end,
        "local_output_dir": payload.local_output_dir,
        "allow_youtube_upload": payload.allow_youtube_upload,
        "youtube_title": payload.youtube_title,
        "youtube_privacy_status": payload.youtube_privacy_status,
        "execution": "queued" if payload.run_end_to_end else "not_started",
        "progress": 0.01 if payload.run_end_to_end else 0.0,
        "current_stage": "Queued" if payload.run_end_to_end else None,
        "processing_steps": [],
    }
    project.config_json = {**project_payload.model_dump(mode="json"), "quick_conversion": quick_meta}
    flag_modified(project, "config_json")
    db.add(project)
    db.flush()

    if payload.auto_generate_plan:
        if payload.run_end_to_end:
            quick_meta["processing_steps"].append(
                _quick_progress_step("Plan Generation", "Generating planning assets and manifest.", 0.03)
            )
            quick_meta["progress"] = 0.03
            quick_meta["current_stage"] = "Plan Generation"
        generated = run_remix_planner(project)
        project.transformation_summary = generated["transformation_summary"]
        project.character_bible = generated["character_bible"]
        project.storyboard_scenes = generated["storyboard_scenes"]
        project.scene_prompts = generated["scene_prompts"]
        project.editing_plan = generated["editing_plan"]
        project.consistency_rules = generated["consistency_rules"]
        project.manifest = generated["manifest"]
        project.status = "processing" if payload.run_end_to_end else "planned"

    if payload.run_end_to_end:
        project.status = "processing"
        project.config_json = {**(project.config_json or {}), "quick_conversion": quick_meta}
        flag_modified(project, "config_json")
        background_tasks.add_task(_run_quick_convert_job, project.id, payload.model_dump(mode="json"))

    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectListItem])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/downloads", response_model=list[QuickDownloadItem])
def list_quick_convert_downloads(db: Session = Depends(get_db)) -> list[QuickDownloadItem]:
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    downloads: list[QuickDownloadItem] = []
    for project in projects:
        config = project.config_json or {}
        quick_meta = config.get("quick_conversion")
        if not isinstance(quick_meta, dict):
            continue

        item = _build_quick_download_item(project, quick_meta)
        if item is not None:
            downloads.append(item)

    return downloads


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    return get_project_or_404(project_id, db)


@router.get("/{project_id}/quick-convert/progress", response_model=QuickConversionProgressResponse)
def get_quick_convert_progress(project_id: int, db: Session = Depends(get_db)) -> QuickConversionProgressResponse:
    project = get_project_or_404(project_id, db)
    config = project.config_json or {}
    quick_meta = config.get("quick_conversion")
    if not isinstance(quick_meta, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quick conversion metadata is not available for this project.",
        )

    steps_raw = quick_meta.get("processing_steps")
    steps = [item for item in steps_raw if isinstance(item, dict)] if isinstance(steps_raw, list) else []
    progress = quick_meta.get("progress")
    if isinstance(progress, (float, int)):
        progress_value = max(0.0, min(1.0, float(progress)))
    elif steps:
        last_progress = steps[-1].get("progress")
        progress_value = max(0.0, min(1.0, float(last_progress))) if isinstance(last_progress, (float, int)) else 0.0
    elif str(quick_meta.get("execution")) == "completed":
        progress_value = 1.0
    else:
        progress_value = 0.0

    output_video_path = quick_meta.get("output_video_path")
    download_url = quick_meta.get("download_url")
    if isinstance(output_video_path, str) and output_video_path and not isinstance(download_url, str):
        download_url = f"{settings.api_prefix}/projects/{project.id}/quick-convert/download"

    return QuickConversionProgressResponse(
        project_id=project.id,
        status=project.status,
        execution=str(quick_meta.get("execution") or "unknown"),
        progress=round(progress_value, 4),
        current_stage=str(quick_meta.get("current_stage")) if quick_meta.get("current_stage") is not None else None,
        processing_steps=steps,
        output_video_path=output_video_path if isinstance(output_video_path, str) else None,
        download_url=download_url if isinstance(download_url, str) else None,
        execution_error=str(quick_meta.get("execution_error")) if quick_meta.get("execution_error") else None,
        youtube_upload=quick_meta.get("youtube_upload") if isinstance(quick_meta.get("youtube_upload"), dict) else None,
    )


@router.get("/{project_id}/quick-convert/output", response_model=QuickConversionOutputResponse)
def get_quick_convert_output(project_id: int, db: Session = Depends(get_db)) -> QuickConversionOutputResponse:
    project = get_project_or_404(project_id, db)
    quick = _get_quick_output_meta(project)
    return QuickConversionOutputResponse(
        project_id=project.id,
        output_video_path=quick["output_video_path"],
        output_dir=quick["output_dir"],
        download_url=quick.get("download_url", f"{settings.api_prefix}/projects/{project.id}/quick-convert/download"),
        youtube_upload=quick.get("youtube_upload"),
    )


@router.get("/{project_id}/quick-convert/download")
def download_quick_convert_output(project_id: int, db: Session = Depends(get_db)) -> FileResponse:
    project = get_project_or_404(project_id, db)
    quick = _get_quick_output_meta(project)
    output_video_path = Path(str(quick["output_video_path"])).expanduser()
    if not output_video_path.exists() or not output_video_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quick conversion output file not found.")
    return FileResponse(
        path=output_video_path,
        media_type="video/mp4",
        filename=output_video_path.name,
    )


@router.post("/{project_id}/generate-plan", response_model=ProjectPlanResponse)
def generate_project_plan(project_id: int, db: Session = Depends(get_db)) -> ProjectPlanResponse:
    project = get_project_or_404(project_id, db)

    generated = run_remix_planner(project)
    project.transformation_summary = generated["transformation_summary"]
    project.character_bible = generated["character_bible"]
    project.storyboard_scenes = generated["storyboard_scenes"]
    project.scene_prompts = generated["scene_prompts"]
    project.editing_plan = generated["editing_plan"]
    project.consistency_rules = generated["consistency_rules"]
    project.manifest = generated["manifest"]
    project.status = "planned"

    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectPlanResponse(**generated)


@router.get("/{project_id}/manifest", response_model=ManifestResponse)
def get_manifest(project_id: int, db: Session = Depends(get_db)) -> ManifestResponse:
    project = get_project_or_404(project_id, db)
    latest = get_latest_manifest(project.id, db)

    if latest:
        return ManifestResponse(project_id=project.id, manifest=latest.manifest_json)

    if project.manifest is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manifest is not available yet. Run generate-plan or export first.",
        )

    return ManifestResponse(project_id=project.id, manifest=project.manifest)
