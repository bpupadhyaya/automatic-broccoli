from __future__ import annotations

from app.models.project import Project
from app.schemas.project import RemixProjectRead


class CharacterLockService:
    """Create stable identity and continuity rules for generated cast."""

    def build_consistency_rules(self, project: RemixProjectRead) -> dict:
        name = f"Lead Performer {project.id}"
        return {
            "name": name,
            "facial_structure_notes": [
                "Defined jawline with soft cheek highlights",
                "Expressive eyes and consistent eyebrow shape",
            ],
            "silhouette_notes": [
                "Readable silhouette in wide shots",
                "Signature shoulder line preserved across looks",
            ],
            "hairstyle_reference": f"{project.visual_theme} textured style",
            "color_palette": ["teal", "magenta", "midnight blue", "silver"],
            "accessories_reference": ["statement earrings", "metal cuffs", "performance boots"],
            "wardrobe_continuity_rules": [
                "Keep hero color palette consistent per song section.",
                "Only change costume between major structural boundaries (verse/chorus/bridge).",
                "Maintain recurring accessory motif for character recognition.",
            ],
        }


def build_character_identity(project: Project, cast_name: str) -> dict:
    result = CharacterLockService().build_consistency_rules(project)
    result["name"] = cast_name
    return result
