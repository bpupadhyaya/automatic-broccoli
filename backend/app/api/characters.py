from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_project_or_404
from app.database import get_db
from app.models.pipeline import Character, CharacterAsset, CharacterOutfit, Shot
from app.schemas.character import (
    ApplyCharacterToShotsRequest,
    ApplyCharacterToShotsResponse,
    CharacterAssetRead,
    CharacterDetailResponse,
    CharacterGenerateRequest,
    CharacterGenerateResponse,
    CharacterListResponse,
    CharacterLockResponse,
    CharacterOutfitRead,
    CharacterRead,
)
from app.services.character_asset_manager import CharacterAssetManagerService
from app.services.character_designer import CharacterDesignerService
from app.services.consistency_prompt_injector import inject_character_locks

router = APIRouter()


def _character_to_read(row: Character) -> CharacterRead:
    return CharacterRead(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        role=row.role,
        identity_summary=row.identity_summary,
        age_range=row.age_range,
        style_archetype=row.style_archetype,
        movement_style=row.movement_style,
        is_locked=row.is_locked,
        identity_json=row.identity_json,
        reference_asset_urls=row.reference_asset_urls,
        consistency_rules_json=row.consistency_rules_json,
        created_at=row.created_at,
    )


def _build_character_detail(character: Character, db: Session) -> CharacterDetailResponse:
    assets = (
        db.query(CharacterAsset)
        .filter(CharacterAsset.character_id == character.id)
        .order_by(CharacterAsset.id.asc())
        .all()
    )
    outfits = (
        db.query(CharacterOutfit)
        .filter(CharacterOutfit.character_id == character.id)
        .order_by(CharacterOutfit.id.asc())
        .all()
    )
    return CharacterDetailResponse(
        character=_character_to_read(character),
        assets=[
            CharacterAssetRead(
                id=item.id,
                asset_type=item.asset_type,
                asset_url=item.asset_url,
                prompt_used=item.prompt_used,
                metadata_json=item.metadata_json,
                created_at=item.created_at,
            )
            for item in assets
        ],
        outfits=[
            CharacterOutfitRead(
                id=item.id,
                outfit_name=item.outfit_name,
                palette_json=item.palette_json,
                description=item.description,
                reference_asset_url=item.reference_asset_url,
                created_at=item.created_at,
            )
            for item in outfits
        ],
    )


@router.post("/projects/{project_id}/characters/generate", response_model=CharacterGenerateResponse)
def generate_project_characters(
    project_id: int,
    payload: CharacterGenerateRequest,
    db: Session = Depends(get_db),
) -> CharacterGenerateResponse:
    project = get_project_or_404(project_id, db)
    designer = CharacterDesignerService()
    manager = CharacterAssetManagerService()

    candidates: list[Character] = []
    for card in designer.generate_candidates(project, payload.candidate_count):
        row = Character(
            project_id=project.id,
            name=card["name"],
            role=card["role"],
            identity_json=card["identity_json"],
            reference_asset_urls=[],
            consistency_rules_json=card["consistency_rules_json"],
            identity_summary=card["identity_summary"],
            age_range=card["age_range"],
            style_archetype=card["style_archetype"],
            face_features_json=card["face_features_json"],
            body_features_json=card["body_features_json"],
            movement_style=card["movement_style"],
            is_locked=False,
        )
        db.add(row)
        db.flush()
        assets = manager.create_assets(db, row)
        manager.create_outfits(db, row)
        row.reference_asset_urls = [item.asset_url for item in assets]
        db.add(row)
        candidates.append(row)

    db.commit()
    for candidate in candidates:
        db.refresh(candidate)

    return CharacterGenerateResponse(
        project_id=project.id,
        candidates=[_character_to_read(item) for item in candidates],
    )


@router.get("/projects/{project_id}/characters", response_model=CharacterListResponse)
def list_project_characters(project_id: int, db: Session = Depends(get_db)) -> CharacterListResponse:
    get_project_or_404(project_id, db)
    rows = (
        db.query(Character)
        .filter(Character.project_id == project_id)
        .order_by(Character.is_locked.desc(), Character.id.asc())
        .all()
    )
    return CharacterListResponse(project_id=project_id, characters=[_character_to_read(item) for item in rows])


@router.get("/characters/{character_id}", response_model=CharacterDetailResponse)
def get_character(character_id: int, db: Session = Depends(get_db)) -> CharacterDetailResponse:
    character = db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character {character_id} not found")
    return _build_character_detail(character, db)


@router.post("/characters/{character_id}/lock", response_model=CharacterLockResponse)
def lock_character(character_id: int, db: Session = Depends(get_db)) -> CharacterLockResponse:
    character = db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character {character_id} not found")

    (
        db.query(Character)
        .filter(
            Character.project_id == character.project_id,
            Character.role == character.role,
            Character.id != character.id,
            Character.is_locked.is_(True),
        )
        .update({Character.is_locked: False}, synchronize_session=False)
    )
    character.is_locked = True
    db.add(character)
    db.commit()
    db.refresh(character)
    return CharacterLockResponse(character=_character_to_read(character))


@router.post("/characters/{character_id}/regenerate-assets", response_model=CharacterDetailResponse)
def regenerate_character_assets(character_id: int, db: Session = Depends(get_db)) -> CharacterDetailResponse:
    character = db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character {character_id} not found")

    manager = CharacterAssetManagerService()
    assets, _ = manager.regenerate_assets(db, character)
    character.reference_asset_urls = [item.asset_url for item in assets]
    db.add(character)
    db.commit()
    db.refresh(character)
    return _build_character_detail(character, db)


@router.post("/projects/{project_id}/characters/apply-to-shots", response_model=ApplyCharacterToShotsResponse)
def apply_character_to_shots(
    project_id: int,
    payload: ApplyCharacterToShotsRequest,
    db: Session = Depends(get_db),
) -> ApplyCharacterToShotsResponse:
    get_project_or_404(project_id, db)

    character_query = db.query(Character).filter(Character.project_id == project_id)
    if payload.character_id is not None:
        character_query = character_query.filter(Character.id == payload.character_id)
    else:
        character_query = character_query.filter(Character.is_locked.is_(True), Character.role.in_(["lead singer", "lead"]))
    character = character_query.order_by(Character.id.asc()).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No target character found. Generate and lock a character first.",
        )

    shots = db.query(Shot).filter(Shot.project_id == project_id).order_by(Shot.start_time.asc()).all()
    updated = 0
    for shot in shots:
        shot.prompt = inject_character_locks(
            character=character,
            base_prompt=shot.prompt,
            scene_context=f"{shot.section} at {shot.location}",
            shot_language=f"{shot.shot_type}, {shot.camera_move}, {shot.lighting_note}",
            outfit_description=shot.wardrobe,
        )
        shot.references_json = character.reference_asset_urls
        if shot.cast_json:
            shot.cast_json = [character.name] + [member for member in shot.cast_json if member != character.name]
        else:
            shot.cast_json = [character.name]
        db.add(shot)
        updated += 1

    db.commit()
    return ApplyCharacterToShotsResponse(project_id=project_id, character_id=character.id, updated_shot_count=updated)
