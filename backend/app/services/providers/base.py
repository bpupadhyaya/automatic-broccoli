from __future__ import annotations

from typing import Protocol


class VideoProvider(Protocol):
    provider_name: str

    def submit_generation(
        self,
        prompt: str,
        references: list[str],
        duration_sec: int,
        aspect_ratio: str = "16:9",
    ) -> dict:
        ...

    def get_job_status(self, provider_job_id: str) -> dict:
        ...

    def cancel_job(self, provider_job_id: str) -> dict:
        ...
