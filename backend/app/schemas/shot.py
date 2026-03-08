from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BuildShotsRequest(BaseModel):
    target_shot_count: int = Field(default=24, ge=1, le=80)
    min_duration_sec: int = Field(default=4, ge=1, le=20)
    max_duration_sec: int = Field(default=8, ge=1, le=20)
    aspect_ratio: str = "16:9"


class ShotBase(BaseModel):
    section: str
    start_time: float
    end_time: float
    duration_sec: int
    shot_type: str
    camera_move: str
    location: str
    cast: list[str]
    wardrobe: str
    lighting: str
    prompt: str
    references: list[str]


class ShotCreate(ShotBase):
    project_id: int
    shot_code: str


class ShotRead(ShotBase):
    id: int
    project_id: Optional[int] = None
    shot_code: Optional[str] = None
    status: str
    qc_score: Optional[float] = None


class BuildShotsResponse(BaseModel):
    project_id: int
    shot_count: int
    shots: list[ShotRead]


class ListShotsResponse(BaseModel):
    project_id: int
    shots: list[ShotRead]


class ManualShotOverrideRequest(BaseModel):
    decision: str
    note: Optional[str] = None
