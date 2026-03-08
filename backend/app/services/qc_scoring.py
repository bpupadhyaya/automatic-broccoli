from __future__ import annotations

from hashlib import sha256


def _metric(seed: str, floor: float = 0.55, ceiling: float = 0.96) -> float:
    raw = int(sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 1000
    return round(floor + (raw / 1000) * (ceiling - floor), 2)


class QCScoringService:
    """Create synthetic per-shot quality scores for acceptance decisions."""

    def score_render(self, shot_id: str, output_url: str) -> dict:
        overall = _metric(f"{shot_id}:{output_url}:overall", 0.58, 0.95)

        def around_overall(seed: str, spread: float = 0.12) -> float:
            offset = _metric(seed, -spread, spread)
            value = round(overall + offset, 2)
            return max(0.0, min(0.99, value))

        metrics = {
            "identity_score": around_overall(f"{shot_id}:identity", 0.08),
            "wardrobe_score": around_overall(f"{shot_id}:wardrobe", 0.08),
            "face_quality_score": around_overall(f"{shot_id}:face", 0.1),
            "hand_quality_score": around_overall(f"{shot_id}:hands", 0.14),
            "motion_score": around_overall(f"{shot_id}:motion", 0.11),
            "prompt_match_score": around_overall(f"{shot_id}:prompt", 0.08),
            "section_fit_score": around_overall(f"{shot_id}:section", 0.1),
            "visual_clarity_score": around_overall(f"{shot_id}:clarity", 0.1),
            "choreography_score": around_overall(f"{shot_id}:choreo", 0.12),
            "camera_motion_score": around_overall(f"{shot_id}:camera", 0.1),
        }
        metrics["overall_score"] = overall
        return metrics


def score_shot(shot_code: str) -> dict:
    return QCScoringService().score_render(shot_code, output_url=f"mock://{shot_code}.mp4")
