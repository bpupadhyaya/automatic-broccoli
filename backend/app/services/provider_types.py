from __future__ import annotations

from typing import Protocol


class VideoProvider(Protocol):
    def generate_shot(self, prompt: str, references: list[str], duration_sec: int) -> dict:
        ...
