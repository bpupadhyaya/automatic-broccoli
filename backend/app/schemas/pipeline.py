from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ProviderName = Literal["runway", "veo", "luma"]


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CharacterPack(ORMBaseModel):
    id: int
    project_id: int
    name: str
    role: str
    identity_json: dict
    reference_asset_urls: list[str]
    consistency_rules_json: list[str]


class ShotResponse(ORMBaseModel):
    id: int
    project_id: int
    shot_code: str
    section: str
    start_time: float
    end_time: float
    duration_sec: int
    shot_type: str
    camera_framing: str
    camera_move: str
    location: str
    cast_json: list[str]
    wardrobe: str
    choreography_note: str
    lighting_note: str
    prompt: str
    references_json: list[str]
    priority_score: float
    status: str
    qc_score: Optional[float]
    approved_clip_url: Optional[str]


class BuildShotsResponse(ORMBaseModel):
    project_id: int
    timing_map: list[dict]
    beat_map: list[dict]
    scene_boundaries: list[dict]
    shot_density_by_section: dict[str, int]
    character_pack: list[CharacterPack]
    shots: list[ShotResponse]


class RenderRequest(BaseModel):
    provider: ProviderName = "runway"
    shot_ids: Optional[list[int]] = None


class RenderJobResponse(ORMBaseModel):
    id: int
    project_id: int
    shot_id: int
    provider: str
    provider_job_id: str
    status: str
    attempt_number: int
    raw_output_url: Optional[str]
    estimated_duration_sec: Optional[int]
    qc_result_json: Optional[dict]
    created_at: datetime
    updated_at: datetime


class RenderResponse(ORMBaseModel):
    project_id: int
    jobs: list[RenderJobResponse]


class QcResult(ORMBaseModel):
    shot_id: int
    identity_score: float
    wardrobe_score: float
    face_quality_score: float
    hand_quality_score: float
    motion_score: float
    prompt_match_score: float
    section_fit_score: float
    visual_clarity_score: float
    choreography_score: float
    camera_motion_score: float
    overall_score: float
    decision: str


class QcResponse(ORMBaseModel):
    project_id: int
    approved: int
    rerender: int
    manual_review: int
    results: list[QcResult]


class QcRequest(BaseModel):
    auto_rerender: bool = True
    provider: ProviderName = "runway"


class ExportRequest(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["16:9_youtube", "9:16_shorts", "thumbnail_stills", "teaser_trailer"]) 


class ExportVariant(ORMBaseModel):
    id: int
    format: str
    output_url: str
    duration_sec: int
    created_at: datetime


class ExportResponse(ORMBaseModel):
    project_id: int
    manifest_version: str
    timeline: dict
    exports: list[ExportVariant]
