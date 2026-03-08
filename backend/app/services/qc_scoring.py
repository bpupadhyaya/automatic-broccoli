from __future__ import annotations

from hashlib import sha256


def _metric(seed: str, floor: float = 0.55, ceiling: float = 0.96) -> float:
    raw = int(sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 1000
    return round(floor + (raw / 1000) * (ceiling - floor), 2)


def score_shot(shot_code: str) -> dict:
    overall = _metric(shot_code + "overall", 0.58, 0.95)

    def around_overall(seed: str, spread: float = 0.12) -> float:
        offset = _metric(seed, -spread, spread)
        value = round(overall + offset, 2)
        return max(0.0, min(0.99, value))

    metrics = {
        "identity_score": around_overall(shot_code + "identity", 0.08),
        "wardrobe_score": around_overall(shot_code + "wardrobe", 0.08),
        "face_quality_score": around_overall(shot_code + "face", 0.1),
        "hand_quality_score": around_overall(shot_code + "hands", 0.14),
        "motion_score": around_overall(shot_code + "motion", 0.11),
        "prompt_match_score": around_overall(shot_code + "prompt", 0.08),
        "section_fit_score": around_overall(shot_code + "section", 0.1),
        "visual_clarity_score": around_overall(shot_code + "clarity", 0.1),
        "choreography_score": around_overall(shot_code + "choreo", 0.12),
        "camera_motion_score": around_overall(shot_code + "camera", 0.1),
    }
    metrics["overall_score"] = overall
    return metrics
