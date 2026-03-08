from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class QCRunRequest(BaseModel):
    shot_ids: Optional[list[int]] = None
    auto_rerender: bool = True
    provider: str = "runway"


class QCResultRead(BaseModel):
    shot_id: int
    character_id: Optional[int] = None
    identity_score: float
    hair_match_score: Optional[float] = None
    wardrobe_score: float
    wardrobe_match_score: Optional[float] = None
    accessory_match_score: Optional[float] = None
    motion_score: float
    prompt_match_score: float
    overall_consistency_score: Optional[float] = None
    overall_score: float
    decision: str


class QCRunResponse(BaseModel):
    project_id: int
    results: list[QCResultRead]
