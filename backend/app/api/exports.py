from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_project_or_404
from app.database import get_db
from app.models.pipeline import Export, Manifest, Shot
from app.schemas.export import ExportRead, ExportRequest, ExportResponse
from app.services import job_state
from app.services.audio_analyzer import analyze_song
from app.services.exporter import build_export_variants
from app.services.timeline_editor import build_timeline

router = APIRouter()


@router.post("/{project_id}/export", response_model=ExportResponse)
def export_project(project_id: int, payload: ExportRequest, db: Session = Depends(get_db)) -> ExportResponse:
    project = get_project_or_404(project_id, db)

    approved_shots = (
        db.query(Shot)
        .filter(
            Shot.project_id == project.id,
            Shot.status.in_([job_state.APPROVED, job_state.QC_APPROVED]),
        )
        .order_by(Shot.start_time.asc())
        .all()
    )

    if not approved_shots:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No approved shots available for export")

    audio_analysis = analyze_song(project)
    timeline = build_timeline(approved_shots, audio_analysis["beat_map"])
    variants = build_export_variants(project.id, timeline, payload.formats)

    export_rows: list[Export] = []
    for variant in variants:
        row = Export(project_id=project.id, **variant)
        db.add(row)
        export_rows.append(row)

    version_num = (
        db.query(func.coalesce(func.count(Manifest.id), 0))
        .filter(Manifest.project_id == project.id)
        .scalar()
    ) + 1
    manifest_version = f"v{version_num}"
    manifest_json = {
        "project_id": project.id,
        "manifest_version": manifest_version,
        "timeline": timeline,
        "exports": variants,
    }

    db.add(Manifest(project_id=project.id, version=manifest_version, manifest_json=manifest_json))

    project.manifest = manifest_json
    project.status = "exporting"
    db.add(project)
    db.commit()

    for item in export_rows:
        db.refresh(item)

    return ExportResponse(
        project_id=project.id,
        exports=[
            ExportRead(
                id=item.id,
                project_id=item.project_id,
                format=item.format,
                status=item.status,
                output_url=item.output_url,
                duration_sec=item.duration_sec,
            )
            for item in export_rows
        ],
    )
