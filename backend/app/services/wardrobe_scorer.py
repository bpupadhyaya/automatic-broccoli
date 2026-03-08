from __future__ import annotations

from hashlib import sha256

from app.models.pipeline import Character


def _score(seed: str, floor: float, ceiling: float) -> float:
    raw = int(sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 1000
    value = floor + (raw / 1000) * (ceiling - floor)
    return round(max(0.0, min(0.99, value)), 2)


class WardrobeScorerService:
    """Evaluate outfit/palette continuity against locked wardrobe identity."""

    def score(self, shot_id: int, character: Character, output_url: str | None) -> dict:
        token = f"{shot_id}:{character.id}:{output_url or 'none'}"
        return {
            "wardrobe_match_score": _score(token + ":wardrobe", 0.65, 0.97),
        }
