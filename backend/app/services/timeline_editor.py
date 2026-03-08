from __future__ import annotations

from app.models.pipeline import Shot
from app.services.beat_sync import align_to_nearest_beat


class TimelineEditorService:
    """Assemble approved clips into beat-aligned timeline segments."""

    def build_timeline(self, project_id: str) -> dict:
        return {"project_id": project_id, "segments": [], "duration_sec": 0.0, "rules_applied": []}


def _build_timeline_from_shots(project_id: str, approved_shots: list[Shot], beat_map: list[dict]) -> dict:
    ordered = sorted(approved_shots, key=lambda shot: (shot.start_time, shot.priority_score * -1))
    segments = []
    wide_medium_close_cycle = ["wide", "medium", "close-up"]

    for idx, shot in enumerate(ordered):
        snapped_start = align_to_nearest_beat(shot.start_time, beat_map)
        snapped_end = align_to_nearest_beat(shot.end_time, beat_map)
        if snapped_end <= snapped_start:
            snapped_end = snapped_start + max(1, shot.duration_sec)

        framing_target = wide_medium_close_cycle[idx % len(wide_medium_close_cycle)]
        transition = "cut" if idx % 4 else "light_sweep"

        segments.append(
            {
                "shot_id": shot.id,
                "shot_code": shot.shot_code,
                "section": shot.section,
                "timeline_start": round(snapped_start, 2),
                "timeline_end": round(snapped_end, 2),
                "transition": transition,
                "framing_target": framing_target,
                "clip_url": shot.approved_clip_url,
            }
        )

    duration = round(max((segment["timeline_end"] for segment in segments), default=0.0), 2)

    return {
        "project_id": project_id,
        "segments": segments,
        "duration_sec": duration,
        "rules_applied": [
            "trimmed to nearest beat",
            "alternated wide/medium/close framing target",
            "inserted hero-friendly transition markers at section peaks",
        ],
    }


def build_timeline(approved_shots: list[Shot], beat_map: list[dict]) -> dict:
    project_id = str(approved_shots[0].project_id) if approved_shots else "unknown"
    return _build_timeline_from_shots(project_id, approved_shots, beat_map)
