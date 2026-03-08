from __future__ import annotations


class SceneSegmenterService:
    """Map candidate source scenes and boundaries for remix construction."""

    def segment(self, video_url: str) -> list[dict]:
        return [
            {"scene_id": "scene_01", "section": "intro", "start": 0.0, "end": 8.0, "source_video_url": video_url},
            {"scene_id": "scene_02", "section": "verse", "start": 8.0, "end": 24.0, "source_video_url": video_url},
            {"scene_id": "scene_03", "section": "chorus", "start": 24.0, "end": 40.0, "source_video_url": video_url},
        ]


def _segment_with_audio(video_url: str, audio_analysis: dict | None = None) -> list[dict]:
    timing_map = (audio_analysis or {}).get("timing_map", [])
    if not timing_map:
        timing_map = [
            {"section": "intro", "start": 0.0, "end": 8.0},
            {"section": "verse", "start": 8.0, "end": 24.0},
            {"section": "chorus", "start": 24.0, "end": 40.0},
        ]

    boundaries = []
    for idx, section in enumerate(timing_map, start=1):
        boundaries.append(
            {
                "scene_id": f"scene_{idx:02d}",
                "section": section.get("section", section.get("label", "section")),
                "start": section["start"],
                "end": section["end"],
                "source_video_url": video_url,
            }
        )
    return boundaries


def segment_scenes(audio_analysis: dict) -> dict:
    boundaries = _segment_with_audio(video_url="mock://source-video", audio_analysis=audio_analysis)
    density: dict[str, int] = {}
    for item in boundaries:
        section = item["section"]
        density[section] = {
            "intro": 2,
            "verse": 3,
            "chorus": 4,
            "bridge": 2,
            "final_chorus": 5,
        }.get(section, 2)
    return {"scene_boundaries": boundaries, "shot_density_by_section": density}
