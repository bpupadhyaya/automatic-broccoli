from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_latest_manifest, get_project_or_404
from app.database import get_db
from app.models.project import Project
from app.schemas.project import (
    ManifestResponse,
    ProjectCreate,
    ProjectDetail,
    ProjectListItem,
    ProjectPlanResponse,
    QuickProjectCreateRequest,
)
from app.services.quick_conversion_defaults import build_quick_project_payload
from app.services.remix_planner import run_remix_planner

router = APIRouter()


def _create_project_record(payload: ProjectCreate, db: Session) -> Project:
    payload_dict = payload.model_dump(mode="json")
    project = Project(**payload_dict)
    project.status = "created"
    project.config_json = payload_dict
    return project


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = _create_project_record(payload, db)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/quick-convert", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def quick_convert_project(payload: QuickProjectCreateRequest, db: Session = Depends(get_db)) -> Project:
    project_payload = build_quick_project_payload(
        target_original_video_url=str(payload.target_original_video_url),
        example_original_video_url=str(payload.example_original_video_url),
        example_remix_video_url=str(payload.example_remix_video_url),
        remix_profile=payload.remix_profile,
        cast_preset=payload.cast_preset,
        heritage_mode=payload.heritage_mode,
    )
    project = _create_project_record(project_payload, db)
    project.config_json = {
        **project_payload.model_dump(mode="json"),
        "quick_conversion": {
            "enabled": True,
            "remix_profile": payload.remix_profile,
            "cast_preset": payload.cast_preset,
            "heritage_mode": payload.heritage_mode,
            "auto_generate_plan": payload.auto_generate_plan,
        },
    }

    if payload.auto_generate_plan:
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
    return project


@router.get("", response_model=list[ProjectListItem])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    return get_project_or_404(project_id, db)


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
