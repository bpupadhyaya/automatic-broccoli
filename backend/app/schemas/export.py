from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["youtube_16_9", "vertical_9_16", "teaser_15s", "thumbnails"])


class ExportRead(BaseModel):
    id: int
    project_id: int
    format: str
    status: str
    output_url: Optional[str] = None
    duration_sec: int


class ExportResponse(BaseModel):
    project_id: int
    exports: list[ExportRead]
