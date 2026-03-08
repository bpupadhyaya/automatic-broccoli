from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.pipeline import Character, CharacterAsset, CharacterOutfit


class CharacterAssetManagerService:
    """Create and manage character reference assets and wardrobe records."""

    def _base_path(self, project_id: int, character_id: int) -> str:
        return f"s3://mock/remix/projects/{project_id}/characters/{character_id}"

    def build_minimum_assets(self, project_id: int, character_id: int, character_name: str) -> list[dict]:
        base = self._base_path(project_id, character_id)
        return [
            {
                "asset_type": "hero_portrait",
                "asset_url": f"{base}/hero_portrait.png",
                "prompt_used": f"{character_name} hero portrait",
                "metadata_json": {"required_v1": True},
            },
            {
                "asset_type": "full_body_reference",
                "asset_url": f"{base}/full_body_reference.png",
                "prompt_used": f"{character_name} full body studio reference",
                "metadata_json": {"required_v1": True},
            },
            {
                "asset_type": "costume_reference",
                "asset_url": f"{base}/costume_reference.png",
                "prompt_used": f"{character_name} costume reference sheet",
                "metadata_json": {"required_v1": True},
            },
            {
                "asset_type": "identity_card",
                "asset_url": f"{base}/identity_card.json",
                "prompt_used": "textual identity lock card",
                "metadata_json": {"required_v1": True},
            },
        ]

    def build_default_outfits(self, character: Character) -> list[dict]:
        outfit_primary = character.identity_json.get("primary_outfit", "signature performance outfit")
        outfit_backup = character.identity_json.get("backup_outfit", "alternate performance outfit")
        palette = character.identity_json.get("palette", ["silver", "blue", "black"])
        return [
            {
                "outfit_name": "primary_outfit",
                "palette_json": palette,
                "description": outfit_primary,
                "reference_asset_url": None,
            },
            {
                "outfit_name": "backup_outfit",
                "palette_json": palette,
                "description": outfit_backup,
                "reference_asset_url": None,
            },
        ]

    def create_assets(self, db: Session, character: Character) -> list[CharacterAsset]:
        rows = [
            CharacterAsset(character_id=character.id, **item)
            for item in self.build_minimum_assets(character.project_id, character.id, character.name)
        ]
        for row in rows:
            db.add(row)
        db.flush()
        return rows

    def create_outfits(self, db: Session, character: Character) -> list[CharacterOutfit]:
        rows = [CharacterOutfit(character_id=character.id, **item) for item in self.build_default_outfits(character)]
        for row in rows:
            db.add(row)
        db.flush()
        return rows

    def regenerate_assets(self, db: Session, character: Character) -> tuple[list[CharacterAsset], list[CharacterOutfit]]:
        db.query(CharacterAsset).filter(CharacterAsset.character_id == character.id).delete(synchronize_session=False)
        db.query(CharacterOutfit).filter(CharacterOutfit.character_id == character.id).delete(synchronize_session=False)
        assets = self.create_assets(db, character)
        outfits = self.create_outfits(db, character)
        return assets, outfits
