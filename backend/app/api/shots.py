from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_project_or_404
from app.database import get_db
from app.models.pipeline import Character, QcResultRecord, RenderJob, Shot
from app.schemas.qc import QCRunRequest, QCRunResponse, QCResultRead
from app.schemas.render_job import RenderJobBrief, StartRenderRequest, StartRenderResponse
from app.schemas.shot import BuildShotsRequest, BuildShotsResponse, ListShotsResponse, ManualShotOverrideRequest, ShotRead
from app.services import job_state
from app.services.audio_analyzer import analyze_song
from app.services.character_pack_generator import generate_character_pack
from app.services.qc_scoring import score_shot
from app.services.remix_planner import run_remix_planner
from app.services.render_queue import render_project_shots
from app.services.rerender_policy import decide_qc_action
from app.services.scene_segmenter import segment_scenes
from app.services.shot_builder import build_shots

router = APIRouter()


def _to_shot_read(shot: Shot) -> ShotRead:
    return ShotRead(
        id=shot.id,
        section=shot.section,
        start_time=shot.start_time,
        end_time=shot.end_time,
        duration_sec=shot.duration_sec,
        shot_type=shot.shot_type,
        camera_move=shot.camera_move,
        location=shot.location,
        cast=shot.cast_json,
        wardrobe=shot.wardrobe,
        lighting=shot.lighting_note,
        prompt=shot.prompt,
        references=shot.references_json,
        status=shot.status,
        qc_score=shot.qc_score,
    )


def _apply_contract_controls(shot_dicts: list[dict], payload: BuildShotsRequest) -> list[dict]:
    for shot in shot_dicts:
        duration = max(payload.min_duration_sec, min(payload.max_duration_sec, shot["duration_sec"]))
        shot["duration_sec"] = duration
        shot["end_time"] = round(shot["start_time"] + duration, 2)

    if len(shot_dicts) > payload.target_shot_count:
        shot_dicts = shot_dicts[: payload.target_shot_count]

    seed_len = len(shot_dicts)
    counter = 0
    while shot_dicts and len(shot_dicts) < payload.target_shot_count:
        base = dict(shot_dicts[counter % seed_len])
        counter += 1
        base["shot_code"] = f"{base['shot_code']}_alt{counter:02d}"
        base["start_time"] = round(base["start_time"] + counter * 0.1, 2)
        base["end_time"] = round(base["start_time"] + base["duration_sec"], 2)
        shot_dicts.append(base)

    return shot_dicts


@router.post("/{project_id}/build-shots", response_model=BuildShotsResponse)
def build_project_shots(project_id: int, payload: BuildShotsRequest, db: Session = Depends(get_db)) -> BuildShotsResponse:
    project = get_project_or_404(project_id, db)

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
    shot_dicts = _apply_contract_controls(shot_dicts, payload)

    shot_models: list[Shot] = []
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
            status=job_state.PLANNED,
        )
        db.add(shot)
        shot_models.append(shot)

    project.status = "shots_built"
    db.add(project)
    db.commit()

    for shot in shot_models:
        db.refresh(shot)

    return BuildShotsResponse(project_id=project.id, shot_count=len(shot_models), shots=[_to_shot_read(item) for item in shot_models])


@router.get("/{project_id}/shots", response_model=ListShotsResponse)
def list_project_shots(project_id: int, db: Session = Depends(get_db)) -> ListShotsResponse:
    get_project_or_404(project_id, db)
    shots = (
        db.query(Shot)
        .filter(Shot.project_id == project_id)
        .order_by(Shot.start_time.asc(), Shot.priority_score.desc())
        .all()
    )
    return ListShotsResponse(project_id=project_id, shots=[_to_shot_read(item) for item in shots])


@router.post("/{project_id}/render", response_model=StartRenderResponse)
def render_project(project_id: int, payload: StartRenderRequest, db: Session = Depends(get_db)) -> StartRenderResponse:
    project = get_project_or_404(project_id, db)

    query = db.query(Shot).filter(Shot.project_id == project.id)
    if payload.shot_ids:
        query = query.filter(Shot.id.in_(payload.shot_ids))
    else:
        query = query.filter(
            Shot.status.in_(
                [job_state.PLANNED, job_state.PENDING, job_state.REJECTED_QC, job_state.FAILED, job_state.RERENDERING]
            )
        )

    shots = query.order_by(Shot.priority_score.desc()).all()
    if not shots:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No shots available for rendering")

    jobs = render_project_shots(db, project, shots, payload.provider)
    project.status = "rendering"
    db.add(project)
    db.commit()

    brief = [RenderJobBrief(render_job_id=item.id, shot_id=item.shot_id, status=job_state.PENDING) for item in jobs]
    return StartRenderResponse(project_id=project.id, provider=payload.provider, jobs=brief)


@router.post("/{project_id}/qc", response_model=QCRunResponse)
def run_qc(project_id: int, payload: QCRunRequest, db: Session = Depends(get_db)) -> QCRunResponse:
    project = get_project_or_404(project_id, db)
    query = db.query(Shot).filter(
        Shot.project_id == project.id,
        Shot.status.in_(
            [
                job_state.SUCCEEDED,
                job_state.APPROVED,
                job_state.REJECTED_QC,
                job_state.RERENDERING,
                job_state.QC_PENDING,
            ]
        ),
    )
    if payload.shot_ids:
        query = query.filter(Shot.id.in_(payload.shot_ids))

    shots = query.order_by(Shot.priority_score.desc()).all()
    if not shots:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No rendered shots available for QC")

    results: list[QCResultRead] = []
    for shot in shots:
        metrics = score_shot(shot.shot_code)
        decision = decide_qc_action(metrics["overall_score"])

        if decision == "approved":
            shot.status = job_state.QC_APPROVED
        elif decision == "rerender":
            shot.status = job_state.RERENDERING
            if payload.auto_rerender:
                render_project_shots(db, project, [shot], payload.provider)
                db.refresh(shot)
        else:
            shot.status = job_state.QC_REJECTED

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
            latest_job.status = shot.status
            db.add(latest_job)

        db.add(
            QcResultRecord(
                project_id=project.id,
                shot_id=shot.id,
                render_job_id=(latest_job.id if latest_job else None),
                scores_json=metrics,
                identity_score=metrics["identity_score"],
                wardrobe_score=metrics["wardrobe_score"],
                motion_score=metrics["motion_score"],
                prompt_match_score=metrics["prompt_match_score"],
                overall_score=metrics["overall_score"],
                decision=decision,
            )
        )

        results.append(
            QCResultRead(
                shot_id=shot.id,
                identity_score=metrics["identity_score"],
                wardrobe_score=metrics["wardrobe_score"],
                motion_score=metrics["motion_score"],
                prompt_match_score=metrics["prompt_match_score"],
                overall_score=metrics["overall_score"],
                decision=decision,
            )
        )

    project.status = "qc_in_progress"
    db.add(project)
    db.commit()

    return QCRunResponse(project_id=project.id, results=results)


@router.post("/{project_id}/shots/{shot_id}/manual-override", response_model=ShotRead)
def manual_shot_override(
    project_id: int,
    shot_id: int,
    payload: ManualShotOverrideRequest,
    db: Session = Depends(get_db),
) -> ShotRead:
    get_project_or_404(project_id, db)
    shot = db.get(Shot, shot_id)
    if not shot or shot.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shot {shot_id} not found")

    decision = payload.decision.strip().lower()
    if decision in {"approved", job_state.QC_APPROVED, job_state.APPROVED}:
        shot.status = job_state.APPROVED
    elif decision in {"rejected_qc", "qc_rejected", "rejected"}:
        shot.status = job_state.QC_REJECTED
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid manual override decision")

    db.add(shot)
    db.add(
        QcResultRecord(
            project_id=project_id,
            shot_id=shot.id,
            render_job_id=None,
            scores_json={"manual_override": True, "note": payload.note or "", "decision": shot.status},
            overall_score=(shot.qc_score if shot.qc_score is not None else 0.0),
            decision=shot.status,
            notes=payload.note,
        )
    )

    db.commit()
    db.refresh(shot)
    return _to_shot_read(shot)
