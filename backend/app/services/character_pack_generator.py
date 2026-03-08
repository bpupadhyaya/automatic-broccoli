from __future__ import annotations

from app.models.project import Project
from app.schemas.project import CharacterProfile
from app.services.character_lock import build_character_identity


class CharacterPackGeneratorService:
    """Generate project cast metadata and reference asset plans."""

    def generate_character_pack(self, project_id: str) -> list[CharacterProfile]:
        base = f"s3://mock/remix/projects/{project_id}/character_pack"
        return [
            CharacterProfile(
                name=f"Lead Performer {project_id}",
                role="lead",
                identity={"summary": "Fictional lead performer profile"},
                references=[f"{base}/hero_portrait.png", f"{base}/full_body_reference.png"],
            )
        ]

    def build_project_pack(self, project: Project, cast_name: str) -> dict:
        identity = build_character_identity(project, cast_name)
        base = f"s3://mock/remix/projects/{project.id}/character_pack"
        references = {
            "hero_portrait": f"{base}/hero_portrait.png",
            "portrait_3_4": f"{base}/portrait_3_4.png",
            "full_body_reference": f"{base}/full_body_reference.png",
            "costume_sheet": f"{base}/costume_sheet.png",
            "hairstyle_reference": f"{base}/hairstyle_reference.png",
            "color_palette": f"{base}/color_palette.png",
            "silhouette_notes": f"{base}/silhouette_notes.png",
            "facial_structure_notes": f"{base}/facial_structure_notes.png",
            "accessories_reference": f"{base}/accessories_reference.png",
        }

        return {
            "name": cast_name,
            "role": "lead",
            "identity_json": {
                "summary": (
                    f"Fictional lead performer with {project.character_style.lower()} styling and "
                    f"{project.region_style_swap.lower()} fusion direction."
                ),
                **identity,
            },
            "reference_asset_urls": list(references.values()),
            "consistency_rules_json": identity["wardrobe_continuity_rules"],
        }


def generate_character_pack(project: Project, cast_name: str) -> dict:
    return CharacterPackGeneratorService().build_project_pack(project, cast_name)
