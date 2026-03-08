from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pipeline import Character, Export, Manifest, RenderJob, Shot
from app.models.project import Project
from app.schemas.pipeline import (
    BuildShotsResponse,
    ExportRequest,
    ExportResponse,
    QcRequest,
    QcResponse,
    QcResult,
    RenderRequest,
    RenderResponse,
    ShotResponse,
)
from app.schemas.project import ManifestResponse, ProjectCreate, ProjectDetail, ProjectListItem, ProjectPlanResponse
from app.services import job_state
from app.services.audio_analyzer import analyze_song
from app.services.character_pack_generator import generate_character_pack
from app.services.exporter import build_export_variants
from app.services.qc_scoring import score_shot
from app.services.remix_planner import run_remix_planner
from app.services.render_queue import render_project_shots
from app.services.rerender_policy import decide_qc_action
from app.services.scene_segmenter import segment_scenes
from app.services.shot_builder import build_shots
from app.services.timeline_editor import build_timeline

router = APIRouter()


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")
    return project


def _latest_manifest(project_id: int, db: Session) -> Optional[Manifest]:
    return (
        db.query(Manifest)
        .filter(Manifest.project_id == project_id)
        .order_by(Manifest.created_at.desc())
        .first()
    )


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    payload_dict = payload.model_dump(mode="json")
    project = Project(**payload_dict)
    project.config_json = payload_dict
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


@router.post("/{project_id}/build-shots", response_model=BuildShotsResponse)
def build_project_shots(project_id: int, db: Session = Depends(get_db)) -> BuildShotsResponse:
    project = _get_project_or_404(project_id, db)

    if not project.transformation_summary:
        generated = run_remix_planner(project)
        project.transformation_summary = generated["transformation_summary"]
        project.character_bible = generated["character_bible"]
        project.storyboard_scenes = generated["storyboard_scenes"]
        project.scene_prompts = generated["scene_prompts"]
        project.editing_plan = generated["editing_plan"]
        project.consistency_rules = generated["consistency_rules"]
        project.manifest = generated["manifest"]

    db.query(RenderJob).filter(RenderJob.project_id == project.id).delete(synchronize_session=False)
    db.query(Shot).filter(Shot.project_id == project.id).delete(synchronize_session=False)
    db.query(Character).filter(Character.project_id == project.id).delete(synchronize_session=False)

    cast_name = (
        (project.character_bible or {}).get("cast_name")
        if isinstance(project.character_bible, dict)
        else None
    ) or f"Lead Performer {project.id}"

    character_pack_data = generate_character_pack(project, cast_name)
    character = Character(project_id=project.id, **character_pack_data)
    db.add(character)
    db.flush()

    audio_analysis = analyze_song(project)
    scene_data = segment_scenes(audio_analysis)
    shot_dicts = build_shots(project, scene_data, character_pack_data)

    shot_models = []
    for item in shot_dicts:
        shot = Shot(
            project_id=project.id,
            shot_code=item["shot_code"],
            section=item["section"],
            start_time=item["start_time"],
            end_time=item["end_time"],
            duration_sec=item["duration_sec"],
            shot_type=item["shot_type"],
            camera_framing=item["camera_framing"],
            camera_move=item["camera_move"],
            location=item["location"],
            cast_json=item["cast"],
            wardrobe=item["wardrobe"],
            choreography_note=item["choreography_note"],
            lighting_note=item["lighting_note"],
            prompt=item["prompt"],
            references_json=item["references"],
            priority_score=item["priority_score"],
            status=job_state.PENDING,
        )
        db.add(shot)
        shot_models.append(shot)

    project.status = "shots_built"
    db.add(project)
    db.commit()

    for shot in shot_models:
        db.refresh(shot)
    db.refresh(character)

    return BuildShotsResponse(
        project_id=project.id,
        timing_map=audio_analysis["timing_map"],
        beat_map=audio_analysis["beat_map"],
        scene_boundaries=scene_data["scene_boundaries"],
        shot_density_by_section=scene_data["shot_density_by_section"],
        character_pack=[character],
        shots=shot_models,
    )


@router.get("/{project_id}/shots", response_model=list[ShotResponse])
def list_project_shots(project_id: int, db: Session = Depends(get_db)) -> list[Shot]:
    _get_project_or_404(project_id, db)
    return (
        db.query(Shot)
        .filter(Shot.project_id == project_id)
        .order_by(Shot.start_time.asc(), Shot.priority_score.desc())
        .all()
    )


@router.post("/{project_id}/render", response_model=RenderResponse)
def render_project(project_id: int, payload: RenderRequest, db: Session = Depends(get_db)) -> RenderResponse:
    project = _get_project_or_404(project_id, db)

    query = db.query(Shot).filter(Shot.project_id == project.id)
    if payload.shot_ids:
        query = query.filter(Shot.id.in_(payload.shot_ids))
    else:
        query = query.filter(
            Shot.status.in_(
                [job_state.PENDING, job_state.REJECTED_QC, job_state.FAILED, job_state.RERENDERING]
            )
        )

    shots = query.order_by(Shot.priority_score.desc()).all()
    if not shots:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No shots available for rendering")

    jobs = render_project_shots(db, project, shots, payload.provider)
    project.status = "rendered"
    db.add(project)
    db.commit()

    return RenderResponse(project_id=project.id, jobs=jobs)


@router.post("/{project_id}/qc", response_model=QcResponse)
def run_qc(project_id: int, payload: QcRequest, db: Session = Depends(get_db)) -> QcResponse:
    project = _get_project_or_404(project_id, db)
    shots = (
        db.query(Shot)
        .filter(
            Shot.project_id == project.id,
            Shot.status.in_([job_state.SUCCEEDED, job_state.APPROVED, job_state.REJECTED_QC, job_state.RERENDERING]),
        )
        .order_by(Shot.priority_score.desc())
        .all()
    )

    if not shots:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No rendered shots available for QC")

    approved = 0
    rerender = 0
    manual_review = 0
    results: list[QcResult] = []

    for shot in shots:
        metrics = score_shot(shot.shot_code)
        decision = decide_qc_action(metrics["overall_score"])

        if decision == "approved":
            shot.status = job_state.APPROVED
            approved += 1
        elif decision == "rerender":
            shot.status = job_state.RERENDERING
            rerender += 1
            if payload.auto_rerender:
                render_project_shots(db, project, [shot], payload.provider)
                db.refresh(shot)
        else:
            shot.status = job_state.REJECTED_QC
            manual_review += 1

        shot.qc_score = metrics["overall_score"]
        db.add(shot)
        latest_job = (
            db.query(RenderJob)
            .filter(RenderJob.shot_id == shot.id)
            .order_by(RenderJob.updated_at.desc(), RenderJob.id.desc())
            .first()
        )
        if latest_job:
            latest_job.qc_result_json = metrics
            if decision == "approved":
                latest_job.status = job_state.APPROVED
            elif decision == "manual_review":
                latest_job.status = job_state.REJECTED_QC
            db.add(latest_job)

        results.append(
            QcResult(
                shot_id=shot.id,
                identity_score=metrics["identity_score"],
                wardrobe_score=metrics["wardrobe_score"],
                face_quality_score=metrics["face_quality_score"],
                hand_quality_score=metrics["hand_quality_score"],
                motion_score=metrics["motion_score"],
                prompt_match_score=metrics["prompt_match_score"],
                section_fit_score=metrics["section_fit_score"],
                visual_clarity_score=metrics["visual_clarity_score"],
                choreography_score=metrics["choreography_score"],
                camera_motion_score=metrics["camera_motion_score"],
                overall_score=metrics["overall_score"],
                decision=decision,
            )
        )

    project.status = "qc_reviewed"
    db.add(project)
    db.commit()

    return QcResponse(
        project_id=project.id,
        approved=approved,
        rerender=rerender,
        manual_review=manual_review,
        results=results,
    )


@router.post("/{project_id}/export", response_model=ExportResponse)
def export_project(project_id: int, payload: ExportRequest, db: Session = Depends(get_db)) -> ExportResponse:
    project = _get_project_or_404(project_id, db)

    approved_shots = (
        db.query(Shot)
        .filter(Shot.project_id == project.id, Shot.status == job_state.APPROVED)
        .order_by(Shot.start_time.asc())
        .all()
    )

    if not approved_shots:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No approved shots available for export")

    audio_analysis = analyze_song(project)
    timeline = build_timeline(approved_shots, audio_analysis["beat_map"])

    variants = build_export_variants(project.id, timeline, payload.formats)
    export_rows = []
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

    db.add(
        Manifest(
            project_id=project.id,
            version=manifest_version,
            manifest_json=manifest_json,
        )
    )

    project.manifest = manifest_json
    project.status = "exported"
    db.add(project)
    db.commit()

    for item in export_rows:
        db.refresh(item)

    return ExportResponse(
        project_id=project.id,
        manifest_version=manifest_version,
        timeline=timeline,
        exports=export_rows,
    )


@router.get("/{project_id}/manifest", response_model=ManifestResponse)
def get_manifest(project_id: int, db: Session = Depends(get_db)) -> ManifestResponse:
    project = _get_project_or_404(project_id, db)
    latest = _latest_manifest(project.id, db)

    if latest:
        return ManifestResponse(project_id=project.id, manifest=latest.manifest_json)

    if project.manifest is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manifest is not available yet. Run generate-plan or export first.",
        )

    return ManifestResponse(project_id=project.id, manifest=project.manifest)
