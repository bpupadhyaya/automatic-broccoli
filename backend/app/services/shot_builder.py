from __future__ import annotations

from hashlib import sha256

from app.models.project import Project
from app.services.prompt_builder import build_shot_prompt

SHOT_TYPES = [
    "hero reveal",
    "medium performance",
    "wide dance performance",
    "close-up glam reaction",
    "cinematic walk",
]

CAMERA_FRAMINGS = ["wide", "medium", "close-up"]
CAMERA_MOVES = ["static with subtle sway", "slow dolly in", "orbit move", "handheld push", "crane lift"]
LOCATIONS = [
    "neon rooftop skyline",
    "mirror rehearsal stage",
    "rain-lit city alley",
    "industrial light tunnel",
    "moonlit boardwalk",
]


def _stable_index(seed: str, modulo: int) -> int:
    return int(sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % modulo


def build_shots(project: Project, scene_data: dict, character_pack: dict) -> list[dict]:
    shots = []
    lead_name = character_pack["name"]
    references = character_pack["reference_asset_urls"]

    for scene in scene_data["scene_boundaries"]:
        section = scene["section"]
        density = scene_data["shot_density_by_section"].get(section, 2)
        segment_duration = scene["end"] - scene["start"]
        slice_duration = max(4, int(segment_duration / max(1, density)))

        current = scene["start"]
        for index in range(density):
            start = round(current, 2)
            end = round(min(scene["end"], current + slice_duration), 2)
            duration = max(3, int(round(end - start)))
            shot_code = f"{section}_{index + 1:02d}_{int(start):03d}"

            seed = f"{project.id}:{shot_code}:{project.visual_theme}"
            shot = {
                "shot_code": shot_code,
                "section": section,
                "start_time": start,
                "end_time": end,
                "duration_sec": duration,
                "shot_type": SHOT_TYPES[_stable_index(seed + "type", len(SHOT_TYPES))],
                "camera_framing": CAMERA_FRAMINGS[_stable_index(seed + "frame", len(CAMERA_FRAMINGS))],
                "camera_move": CAMERA_MOVES[_stable_index(seed + "move", len(CAMERA_MOVES))],
                "location": LOCATIONS[_stable_index(seed + "loc", len(LOCATIONS))],
                "cast": [lead_name, "2 backup dancers"],
                "wardrobe": project.costume_style,
                "choreography_note": (
                    f"Blend {project.dance_style.lower()} with section-specific accents for {section.replace('_', ' ')}."
                ),
                "lighting_note": project.lighting_style,
                "references": references,
                "priority_score": round(0.65 + (_stable_index(seed + "prio", 30) / 100), 2),
            }
            shot["prompt"] = build_shot_prompt(project, shot, lead_name)

            shots.append(shot)
            current = end

    return shots
