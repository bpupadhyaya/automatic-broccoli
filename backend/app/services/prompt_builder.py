from __future__ import annotations

from app.models.project import Project


def build_shot_prompt(project: Project, shot: dict, lead_name: str) -> str:
    cast_descriptor = ", ".join(shot["cast"]) if shot["cast"] else lead_name
    return (
        f"fictional music video shot, {cast_descriptor}, section {shot['section']}, "
        f"{shot['shot_type']}, {shot['location']}, {project.visual_theme.lower()} palette, "
        f"wardrobe {shot['wardrobe'].lower()}, {project.lighting_style.lower()} lighting, "
        f"camera {shot['camera_framing'].lower()} with {shot['camera_move'].lower()}, "
        f"choreography {shot['choreography_note'].lower()}, cinematic quality"
    )
