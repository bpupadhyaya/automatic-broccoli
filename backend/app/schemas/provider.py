from __future__ import annotations

from pydantic import BaseModel


class ProviderSubmitResponse(BaseModel):
    provider: str
    job_id: str
    status: str
    estimated_duration_sec: int


class ProviderJobStatusResponse(BaseModel):
    provider: str
    provider_job_id: str
    status: str


class ProviderCancelResponse(BaseModel):
    provider: str
    provider_job_id: str
    status: str
