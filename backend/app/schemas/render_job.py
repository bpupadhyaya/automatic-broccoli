from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RenderJobCreate(BaseModel):
    project_id: int
    shot_id: int
    provider: str
    prompt: str
    references: list[str]
    duration_sec: int
    aspect_ratio: str = "16:9"


class StartRenderRequest(BaseModel):
    provider: str = "runway"
    shot_ids: Optional[list[int]] = None
    priority: str = "normal"
    aspect_ratio: str = "16:9"


class RenderJobBrief(BaseModel):
    render_job_id: int
    shot_id: int
    status: str


class StartRenderResponse(BaseModel):
    project_id: int
    provider: str
    jobs: list[RenderJobBrief]


class RenderJobRead(BaseModel):
    id: int
    project_id: int
    shot_id: int
    provider: str
    provider_job_id: Optional[str] = None
    status: str
    attempt_number: int
    output_url: Optional[str] = None
    qc_status: str = "pending"
    error_message: Optional[str] = None
