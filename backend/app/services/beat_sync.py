from __future__ import annotations


class BeatSyncService:
    """Utilities for snapping timeline segments to beat boundaries."""

    def snap_shot_boundaries(self, timeline_data: dict, beat_map: dict) -> dict:
        beats = beat_map.get("beat_map", []) if isinstance(beat_map, dict) else beat_map
        if not beats:
            return timeline_data

        snapped = dict(timeline_data)
        segments = []
        for segment in timeline_data.get("segments", []):
            updated = dict(segment)
            updated["timeline_start"] = align_to_nearest_beat(float(segment["timeline_start"]), beats)
            updated["timeline_end"] = align_to_nearest_beat(float(segment["timeline_end"]), beats)
            if updated["timeline_end"] <= updated["timeline_start"]:
                updated["timeline_end"] = round(updated["timeline_start"] + 1.0, 2)
            segments.append(updated)
        snapped["segments"] = segments
        snapped["duration_sec"] = round(max((s["timeline_end"] for s in segments), default=0.0), 2)
        return snapped


def align_to_nearest_beat(time_sec: float, beat_map: list[dict]) -> float:
    if not beat_map:
        return time_sec
    nearest = min(beat_map, key=lambda beat: abs(beat["time"] - time_sec))
    return float(nearest["time"])
