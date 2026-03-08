from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CharacterIdentityCard(BaseModel):
    name: str
    role: str
    identity: str
    age_range: str
    face_shape: str
    skin_tone: str
    hair: str
    eyes: str
    makeup: str
    build: str
    signature_expression: str
    primary_outfit: str
    accessories: list[str]
    movement_style: str
    consistency_rules: list[str]


class CharacterAssetRead(BaseModel):
    id: int
    asset_type: str
    asset_url: str
    prompt_used: Optional[str] = None
    metadata_json: Optional[dict] = None
    created_at: datetime


class CharacterOutfitRead(BaseModel):
    id: int
    outfit_name: str
    palette_json: list[str]
    description: str
    reference_asset_url: Optional[str] = None
    created_at: datetime


class CharacterRead(BaseModel):
    id: int
    project_id: int
    name: str
    role: str
    identity_summary: Optional[str] = None
    age_range: Optional[str] = None
    style_archetype: Optional[str] = None
    movement_style: Optional[str] = None
    is_locked: bool
    identity_json: dict
    reference_asset_urls: list[str]
    consistency_rules_json: list[str]
    created_at: datetime


class CharacterDetailResponse(BaseModel):
    character: CharacterRead
    assets: list[CharacterAssetRead]
    outfits: list[CharacterOutfitRead]


class CharacterGenerateRequest(BaseModel):
    candidate_count: int = Field(default=3, ge=1, le=6)


class CharacterGenerateResponse(BaseModel):
    project_id: int
    candidates: list[CharacterRead]


class CharacterListResponse(BaseModel):
    project_id: int
    characters: list[CharacterRead]


class CharacterLockResponse(BaseModel):
    character: CharacterRead


class ApplyCharacterToShotsRequest(BaseModel):
    character_id: Optional[int] = None


class ApplyCharacterToShotsResponse(BaseModel):
    project_id: int
    character_id: int
    updated_shot_count: int
