from __future__ import annotations

import random
from hashlib import sha256

from app.models.project import Project

NAME_POOL = [
    "Nova Vance",
    "Aria Flux",
    "Kai Sol",
    "Mira Pulse",
    "Jett Halo",
    "Zuri Vale",
    "Lio Ember",
    "Skye Riff",
]

SCENE_SETTINGS = [
    "Neon rooftop at twilight",
    "Rain-lit alley dance tunnel",
    "Mirror-lined rehearsal hall",
    "Retro-futurist subway platform",
    "Deserted theater with practical lights",
    "Industrial bridge under moving spotlights",
    "Open plaza with projection-mapped walls",
    "Moonlit beach with reflective water",
]


def _seed_for_project(project: Project) -> int:
    composite = "|".join(
        [
            project.target_original_video_url,
            project.example_original_video_url,
            project.example_remix_video_url,
            project.remix_genre,
            project.character_style,
        ]
    )
    return int(sha256(composite.encode("utf-8")).hexdigest()[:8], 16)


def build_project_plan(project: Project) -> dict:
    rng = random.Random(_seed_for_project(project))
    cast_name = rng.choice(NAME_POOL)
    alias_candidates = [name for name in NAME_POOL if name != cast_name]
    aliases = rng.sample(alias_candidates, k=2)

    transformation_summary = (
        f"Apply the energy arc and camera tempo from the example remix to the target song, "
        f"shifting toward a {project.visual_theme.lower()} visual world with {project.remix_genre.lower()} rhythm accents. "
        f"Prioritize {project.dance_style.lower()} movement phrasing and a {project.cinematic_mood.lower()} emotional tone."
    )

    character_bible = {
        "cast_name": cast_name,
        "aliases": aliases,
        "persona_summary": (
            f"A fictional performance lead designed for {project.region_style_swap} crossover aesthetics "
            f"with {project.gender_mix.lower()} expression and {project.energy_level.lower()} stage presence."
        ),
        "styling_notes": [
            f"Costume language: {project.costume_style}",
            f"Lighting intention: {project.lighting_style}",
            f"Camera behavior: {project.camera_style}",
        ],
        "movement_notes": [
            f"Dance base: {project.dance_style}",
            f"Beat intensity target: {project.beat_intensity}",
            f"Vocal handling direction: {project.vocal_handling}",
        ],
    }

    scene_count = rng.randint(5, 8)
    storyboard_scenes = []
    scene_prompts = []

    for idx in range(1, scene_count + 1):
        setting = rng.choice(SCENE_SETTINGS)
        visual_focus = rng.choice(
            [
                "wide lens movement with rhythmic whip pans",
                "slow push-ins synchronized to downbeats",
                "handheld orbit shots around key choreography moments",
                "high contrast silhouettes and rim light reveals",
            ]
        )

        scene = {
            "scene_number": idx,
            "title": f"Scene {idx}: {project.visual_theme} progression",
            "setting": setting,
            "visual_focus": visual_focus,
            "choreography_note": f"Blend {project.dance_style.lower()} patterns with {project.energy_level.lower()} escalation.",
        }
        storyboard_scenes.append(scene)

        scene_prompts.append(
            {
                "scene_number": idx,
                "prompt": (
                    f"Music video frame, fictional performer '{cast_name}', {setting}, {project.visual_theme.lower()} palette, "
                    f"{project.costume_style.lower()} wardrobe, {project.lighting_style.lower()} lighting, "
                    f"{visual_focus}, cinematic tone: {project.cinematic_mood.lower()}."
                ),
            }
        )

    editing_plan = [
        "Create a timing map from the target song structure (intro, verse, pre-chorus, chorus, bridge).",
        "Match cut density to example remix pacing while preserving narrative clarity.",
        "Use transition motif of light sweeps and impact cuts on major beat accents.",
        "Apply color grade profile consistent with selected visual theme.",
        "Finalize audio lane notes with preserve-melody flag considered in arrangement decisions.",
    ]

    consistency_rules = [
        "Use only fictional performers by default. Do not clone real celebrity likeness without explicit rights.",
        "Maintain wardrobe continuity across adjacent scenes unless transformation beat is intentional.",
        "Keep primary character silhouette readable in every wide shot.",
        "Camera motion should escalate with chorus energy and reset at bridge.",
        "Preserve the selected regional/style fusion in styling and set design choices.",
    ]

    manifest = {
        "project_version": "0.1.0-mvp",
        "project_id": project.id,
        "inputs": {
            "target_original_video_url": project.target_original_video_url,
            "example_original_video_url": project.example_original_video_url,
            "example_remix_video_url": project.example_remix_video_url,
            "celebrity_mode": project.celebrity_mode,
            "preserve_melody": project.preserve_melody,
        },
        "outputs": {
            "scene_count": scene_count,
            "character_name": cast_name,
            "storyboard": storyboard_scenes,
            "scene_prompts": scene_prompts,
            "editing_plan": editing_plan,
            "consistency_rules": consistency_rules,
        },
        "future_extensions": {
            "video_generation_engines": ["runway", "pika", "sora", "custom_pipeline"],
            "note": "MVP currently generates planning assets only.",
        },
    }

    return {
        "transformation_summary": transformation_summary,
        "character_bible": character_bible,
        "storyboard_scenes": storyboard_scenes,
        "scene_prompts": scene_prompts,
        "editing_plan": editing_plan,
        "consistency_rules": consistency_rules,
        "manifest": manifest,
    }
