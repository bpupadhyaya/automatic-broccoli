from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.schemas.project import ManifestResponse, ProjectCreate, ProjectDetail, ProjectListItem, ProjectPlanResponse
from app.services.project_generator import build_project_plan

router = APIRouter()


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")
    return project


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = Project(**payload.model_dump(mode="json"))
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectListItem])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    return _get_project_or_404(project_id, db)


@router.post("/{project_id}/generate-plan", response_model=ProjectPlanResponse)
def generate_project_plan(project_id: int, db: Session = Depends(get_db)) -> ProjectPlanResponse:
    project = _get_project_or_404(project_id, db)

    generated = build_project_plan(project)
    project.transformation_summary = generated["transformation_summary"]
    project.character_bible = generated["character_bible"]
    project.storyboard_scenes = generated["storyboard_scenes"]
    project.scene_prompts = generated["scene_prompts"]
    project.editing_plan = generated["editing_plan"]
    project.consistency_rules = generated["consistency_rules"]
    project.manifest = generated["manifest"]
    project.status = "generated"

    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectPlanResponse(**generated)


@router.get("/{project_id}/manifest", response_model=ManifestResponse)
def get_manifest(project_id: int, db: Session = Depends(get_db)) -> ManifestResponse:
    project = _get_project_or_404(project_id, db)
    if project.manifest is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manifest is not available yet. Run generate-plan first.",
        )

    return ManifestResponse(project_id=project.id, manifest=project.manifest)
