from __future__ import annotations

from uuid import uuid4


class VeoProvider:
    provider_name = "veo"

    def generate_shot(self, prompt: str, references: list[str], duration_sec: int) -> dict:
        return {
            "provider": self.provider_name,
            "job_id": f"veo-{uuid4().hex[:12]}",
            "status": "submitted",
            "estimated_duration_sec": 80 + duration_sec * 4,
        }
