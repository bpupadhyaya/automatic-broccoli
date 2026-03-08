from __future__ import annotations

from hashlib import sha256

from app.models.project import Project

FIRST_NAMES = ["Aurelia", "Nova", "Lyra", "Selene", "Mira", "Kairo", "Riven", "Zara"]
LAST_NAMES = ["Voss", "Vale", "Noir", "Sloane", "Quill", "Raine", "Kade", "Skye"]
AGE_RANGES = ["early 20s", "mid 20s", "late 20s", "early 30s"]
FACE_SHAPES = ["soft oval face", "defined oval face", "heart-shaped face", "balanced angular face"]
SKIN_TONES = ["light warm tone", "medium warm tone", "medium neutral tone", "rich warm tone"]
HAIR_STYLES = [
    "platinum silver wavy hair, shoulder length",
    "dark chestnut layered hair, shoulder length",
    "midnight black straight hair, long bob",
    "honey-blonde textured waves, shoulder length",
]
EYE_STYLES = ["almond-shaped gray-blue eyes", "deep brown almond eyes", "hazel cat-eye shape", "green almond eyes"]
MAKEUP_STYLES = [
    "glossy stage makeup with metallic accents",
    "cinematic soft-glow makeup with bold liner",
    "high-contrast pop makeup with shimmer highlights",
]
BUILD_TYPES = ["slim athletic build", "lean dancer build", "athletic compact build"]
SIGNATURE_EXPRESSIONS = ["confident cinematic gaze", "playful performance grin", "focused stage intensity"]


def _index(seed: str, modulo: int) -> int:
    return int(sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % modulo


def _clip(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 3:
        return value[:limit]
    return value[: limit - 3].rstrip() + "..."


class CharacterDesignerService:
    """Generate fictional lead character identity cards for remix projects."""

    def generate_candidates(self, project: Project, candidate_count: int = 3) -> list[dict]:
        cards: list[dict] = []
        for idx in range(candidate_count):
            seed = f"{project.id}:{idx}:{project.character_style}:{project.visual_theme}"
            first = FIRST_NAMES[_index(seed + "f", len(FIRST_NAMES))]
            last = LAST_NAMES[_index(seed + "l", len(LAST_NAMES))]
            name = f"{first} {last}"
            identity = f"fictional {project.character_style.lower()}"

            age_range = AGE_RANGES[_index(seed + "age", len(AGE_RANGES))]
            face_shape = FACE_SHAPES[_index(seed + "face", len(FACE_SHAPES))]
            skin_tone = SKIN_TONES[_index(seed + "skin", len(SKIN_TONES))]
            hair = HAIR_STYLES[_index(seed + "hair", len(HAIR_STYLES))]
            eyes = EYE_STYLES[_index(seed + "eyes", len(EYE_STYLES))]
            makeup = MAKEUP_STYLES[_index(seed + "makeup", len(MAKEUP_STYLES))]
            build = BUILD_TYPES[_index(seed + "build", len(BUILD_TYPES))]
            signature_expression = SIGNATURE_EXPRESSIONS[_index(seed + "expr", len(SIGNATURE_EXPRESSIONS))]

            primary_outfit = f"{project.costume_style.lower()} with {project.visual_theme.lower()} accents"
            backup_outfit = f"alternate {project.costume_style.lower()} look for chorus peaks"
            accessories = ["single ear cuff", "fingerless gloves"]
            movement_style = f"{project.dance_style.lower()} performance gestures with controlled turns"

            consistency_rules = [
                f"maintain {hair}",
                "do not change eye color",
                "preserve signature face shape and silhouette",
                "keep primary outfit palette stable",
                "avoid heavy costume redesign between adjacent scenes",
            ]

            cards.append(
                {
                    "name": name,
                    "role": _clip("lead singer", 128),
                    "identity_summary": identity,
                    "age_range": _clip(age_range, 64),
                    "style_archetype": _clip(project.character_style, 128),
                    "movement_style": _clip(movement_style, 255),
                    "face_features_json": {
                        "face_shape": face_shape,
                        "skin_tone": skin_tone,
                        "hair": hair,
                        "eyes": eyes,
                        "makeup": makeup,
                        "signature_expression": signature_expression,
                    },
                    "body_features_json": {
                        "build": build,
                        "height_build": build,
                        "posture": "upright stage-ready posture",
                    },
                    "identity_json": {
                        "name": name,
                        "role": "lead singer",
                        "identity": identity,
                        "age_range": age_range,
                        "face_shape": face_shape,
                        "skin_tone": skin_tone,
                        "hair": hair,
                        "eyes": eyes,
                        "makeup": makeup,
                        "build": build,
                        "signature_expression": signature_expression,
                        "primary_outfit": primary_outfit,
                        "backup_outfit": backup_outfit,
                        "accessories": accessories,
                        "movement_style": movement_style,
                        "style_archetype": project.character_style,
                        "consistency_rules": consistency_rules,
                    },
                    "consistency_rules_json": consistency_rules,
                }
            )
        return cards
