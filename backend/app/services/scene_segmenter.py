from __future__ import annotations


def segment_scenes(audio_analysis: dict) -> dict:
    timing_map = audio_analysis["timing_map"]
    boundaries = []
    density = {}

    for idx, section in enumerate(timing_map, start=1):
        boundaries.append(
            {
                "scene_id": f"scene_{idx:02d}",
                "section": section["section"],
                "start": section["start"],
                "end": section["end"],
            }
        )
        density[section["section"]] = {
            "intro": 2,
            "verse": 3,
            "chorus": 4,
            "bridge": 2,
            "final_chorus": 5,
        }.get(section["section"], 2)

    return {"scene_boundaries": boundaries, "shot_density_by_section": density}
