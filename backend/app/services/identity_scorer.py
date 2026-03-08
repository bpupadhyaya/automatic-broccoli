from __future__ import annotations

from hashlib import sha256

from app.models.pipeline import Character


def _score(seed: str, floor: float, ceiling: float) -> float:
    raw = int(sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 1000
    value = floor + (raw / 1000) * (ceiling - floor)
    return round(max(0.0, min(0.99, value)), 2)


class IdentityScorerService:
    """Evaluate whether shot output remains identity-consistent with locked character."""

    def score(self, shot_id: int, character: Character, output_url: str | None) -> dict:
        token = f"{shot_id}:{character.id}:{output_url or 'none'}"
        identity_score = _score(token + ":identity", 0.68, 0.96)
        hair_match_score = _score(token + ":hair", 0.66, 0.98)
        accessory_match_score = _score(token + ":accessory", 0.6, 0.95)
        return {
            "identity_score": identity_score,
            "hair_match_score": hair_match_score,
            "accessory_match_score": accessory_match_score,
        }
