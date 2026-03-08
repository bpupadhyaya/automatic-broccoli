from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class QCRunRequest(BaseModel):
    shot_ids: Optional[list[int]] = None
    auto_rerender: bool = True
    provider: str = "runway"


class QCResultRead(BaseModel):
    shot_id: int
    identity_score: float
    wardrobe_score: float
    motion_score: float
    prompt_match_score: float
    overall_score: float
    decision: str


class QCRunResponse(BaseModel):
    project_id: int
    results: list[QCResultRead]
