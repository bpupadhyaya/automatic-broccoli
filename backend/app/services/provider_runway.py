from __future__ import annotations

from uuid import uuid4


class RunwayProvider:
    provider_name = "runway"

    def generate_shot(self, prompt: str, references: list[str], duration_sec: int) -> dict:
        return {
            "provider": self.provider_name,
            "job_id": f"runway-{uuid4().hex[:12]}",
            "status": "submitted",
            "estimated_duration_sec": 90 + duration_sec * 5,
        }
