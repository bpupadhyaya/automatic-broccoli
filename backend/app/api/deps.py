from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.pipeline import Manifest
from app.models.project import Project


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")
    return project


def get_latest_manifest(project_id: int, db: Session) -> Optional[Manifest]:
    return (
        db.query(Manifest)
        .filter(Manifest.project_id == project_id)
        .order_by(Manifest.created_at.desc())
        .first()
    )
