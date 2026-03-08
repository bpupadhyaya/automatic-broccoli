from __future__ import annotations

from app.schemas.project import ProjectCreate, QuickCastPreset, QuickHeritageMode, QuickRemixProfile


def _heritage_direction(remix_profile: QuickRemixProfile, heritage_mode: QuickHeritageMode) -> tuple[str, str]:
    if heritage_mode == "swap_to_english":
        return (
            "Original culture replaced with fictional English-heritage actors",
            "English-heritage cast replacement for all principal performers",
        )
    if heritage_mode == "swap_to_nepali":
        return (
            "Original culture replaced with fictional Nepali-heritage actors",
            "Nepali-heritage cast replacement for all principal performers",
        )
    if heritage_mode == "mix":
        return (
            "Mixed heritage cast blending English and Nepali fictional performers",
            "Blend English and Nepali heritage styling across leads and dancers",
        )

    if remix_profile == "english":
        return (
            "Primarily fictional English-heritage performers with optional global styling",
            "English-focused cast with global crossover styling",
        )
    return (
        "Primarily fictional Nepali-heritage performers with optional global styling",
        "Nepali-focused cast with global crossover styling",
    )


def _character_defaults(remix_profile: QuickRemixProfile, cast_preset: QuickCastPreset) -> tuple[str, str, str]:
    if remix_profile == "english":
        if cast_preset == "female":
            return (
                "Fictional extremely beautiful long-hair blonde blue-eyed female lead singer",
                "Female lead singer with supporting mixed dancers",
                "18-25",
            )
        if cast_preset == "male":
            return (
                "Fictional male actors age 18-30, both blonde and brunette, blue eyes",
                "Male lead singer with supporting mixed dancers",
                "18-30",
            )
        return (
            (
                "Fictional mixed cast: extremely beautiful long-hair blonde blue-eyed women age 18-25, "
                "plus male actors age 18-30 in blonde and brunette variants with blue eyes"
            ),
            "Mixed cast with female and male leads plus dancers",
            "18-30",
        )

    if cast_preset == "female":
        return (
            "Fictional Nepali-inspired female lead singer with cinematic performance styling",
            "Female lead singer with supporting mixed dancers",
            "18-25",
        )
    if cast_preset == "male":
        return (
            "Fictional Nepali-inspired male lead singer with cinematic performance styling",
            "Male lead singer with supporting mixed dancers",
            "18-30",
        )
    return (
        "Fictional Nepali-inspired mixed cast with female and male performers",
        "Mixed cast with female and male leads plus dancers",
        "18-30",
    )


def build_quick_project_payload(
    target_original_video_url: str,
    example_original_video_url: str,
    example_remix_video_url: str,
    remix_profile: QuickRemixProfile,
    cast_preset: QuickCastPreset,
    heritage_mode: QuickHeritageMode,
) -> ProjectCreate:
    character_style, gender_mix, age_group = _character_defaults(remix_profile, cast_preset)
    ethnic_cultural_direction, region_style_swap = _heritage_direction(remix_profile, heritage_mode)

    if remix_profile == "english":
        defaults = {
            "visual_theme": "Neon concert skyline with glossy night energy",
            "costume_style": "Modern pop stage couture with metallic accents",
            "lighting_style": "High-contrast glossy stage lights",
            "cinematic_mood": "Confident high-energy pop spectacle",
            "dance_style": "Precision pop choreography",
            "energy_level": "High",
            "camera_style": "Dynamic crane and dolly performance moves",
            "remix_genre": "Electronic dance pop",
            "beat_intensity": "Punchy",
            "vocal_handling": "Polished layered vocals",
        }
    else:
        defaults = {
            "visual_theme": "Himalayan cinematic romance with modern stage fusion",
            "costume_style": "Nepali-inspired contemporary performance styling",
            "lighting_style": "Warm cinematic sunset and stage glow",
            "cinematic_mood": "Emotional yet energetic performance journey",
            "dance_style": "Nepali folk-pop fusion choreography",
            "energy_level": "High",
            "camera_style": "Cinematic sweeping drone and dolly movement",
            "remix_genre": "Nepali pop fusion",
            "beat_intensity": "Driving",
            "vocal_handling": "Expressive melodic lead with layered harmonies",
        }

    return ProjectCreate(
        target_original_video_url=target_original_video_url,
        example_original_video_url=example_original_video_url,
        example_remix_video_url=example_remix_video_url,
        character_style=character_style,
        region_style_swap=region_style_swap,
        gender_mix=gender_mix,
        age_group=age_group,
        ethnic_cultural_direction=ethnic_cultural_direction,
        celebrity_mode="fictional_only",
        preserve_melody=True,
        **defaults,
    )
