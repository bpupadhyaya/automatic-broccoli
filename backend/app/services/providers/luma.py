from __future__ import annotations

from uuid import uuid4


class LumaProvider:
    provider_name = "luma"

    def submit_generation(self, prompt: str, references: list[str], duration_sec: int, aspect_ratio: str = "16:9") -> dict:
        return {
            "provider": self.provider_name,
            "job_id": f"luma-{uuid4().hex[:12]}",
            "status": "submitted",
            "estimated_duration_sec": 70 + duration_sec * 6,
        }

    def get_job_status(self, provider_job_id: str) -> dict:
        return {"provider": self.provider_name, "provider_job_id": provider_job_id, "status": "rendering"}

    def cancel_job(self, provider_job_id: str) -> dict:
        return {"provider": self.provider_name, "provider_job_id": provider_job_id, "status": "cancelled"}
