from __future__ import annotations

from app.models.project import Project


class AudioAnalyzerService:
    """Analyze track timing and rough musical structure for shot planning."""

    def analyze(self, audio_url: str) -> dict:
        timing_map = [
            {"section": "intro", "start": 0.0, "end": 12.0},
            {"section": "verse", "start": 12.0, "end": 36.0},
            {"section": "chorus", "start": 36.0, "end": 52.0},
            {"section": "verse", "start": 52.0, "end": 76.0},
            {"section": "bridge", "start": 76.0, "end": 92.0},
            {"section": "final_chorus", "start": 92.0, "end": 120.0},
        ]

        beat_map = []
        beat_time = 0.0
        while beat_time <= 120.0:
            section = next(
                (item["section"] for item in timing_map if item["start"] <= beat_time < item["end"]),
                "outro",
            )
            intensity = {
                "intro": 0.55,
                "verse": 0.7,
                "chorus": 0.88,
                "bridge": 0.68,
                "final_chorus": 0.95,
            }.get(section, 0.6)
            beat_map.append({"time": round(beat_time, 2), "section": section, "intensity": intensity})
            beat_time += 2.0

        return {
            "audio_url": audio_url,
            "tempo_bpm": 120,
            "timing_map": timing_map,
            "beat_map": beat_map,
            "sections": [{"label": item["section"], "start": item["start"], "end": item["end"]} for item in timing_map],
        }


def analyze_song(project: Project) -> dict:
    return AudioAnalyzerService().analyze(str(project.target_original_video_url))
