from __future__ import annotations


def align_to_nearest_beat(time_sec: float, beat_map: list[dict]) -> float:
    if not beat_map:
        return time_sec
    nearest = min(beat_map, key=lambda beat: abs(beat["time"] - time_sec))
    return float(nearest["time"])
