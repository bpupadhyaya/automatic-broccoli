from __future__ import annotations

from app.models.pipeline import Character


class ConsistencyPromptInjectorService:
    """Inject character identity and wardrobe locks into shot prompts."""

    def inject(
        self,
        character: Character,
        base_prompt: str,
        scene_context: str,
        shot_language: str,
        outfit_description: str | None = None,
    ) -> str:
        identity = character.identity_json or {}
        identity_lock = (
            f"{character.name}, {identity.get('identity', character.identity_summary or 'fictional lead performer')}, "
            f"{identity.get('hair', 'consistent hair style')}, "
            f"{identity.get('eyes', 'consistent eye color')}, "
            f"{identity.get('build', 'consistent silhouette')}"
        )
        wardrobe_lock = outfit_description or identity.get("primary_outfit", "signature performance outfit")
        accessories = identity.get("accessories", [])
        if accessories:
            wardrobe_lock = f"{wardrobe_lock}, accessories: {', '.join(accessories)}"

        return (
            "[Identity Lock]\n"
            f"{identity_lock}\n\n"
            "[Wardrobe Lock]\n"
            f"{wardrobe_lock}\n\n"
            "[Scene Context]\n"
            f"{scene_context}\n\n"
            "[Shot Language]\n"
            f"{shot_language}\n\n"
            "[Base Prompt]\n"
            f"{base_prompt}"
        )


def inject_character_locks(
    character: Character,
    base_prompt: str,
    scene_context: str,
    shot_language: str,
    outfit_description: str | None = None,
) -> str:
    return ConsistencyPromptInjectorService().inject(
        character=character,
        base_prompt=base_prompt,
        scene_context=scene_context,
        shot_language=shot_language,
        outfit_description=outfit_description,
    )
