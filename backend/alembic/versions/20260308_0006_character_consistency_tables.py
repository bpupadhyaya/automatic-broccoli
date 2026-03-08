"""add character consistency tables and fields

Revision ID: 20260308_0006
Revises: 20260308_0005
Create Date: 2026-03-08 08:05:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260308_0006"
down_revision: Optional[str] = "20260308_0005"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("identity_summary", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("age_range", sa.String(length=64), nullable=True))
    op.add_column("characters", sa.Column("style_archetype", sa.String(length=128), nullable=True))
    op.add_column("characters", sa.Column("face_features_json", sa.JSON(), nullable=True))
    op.add_column("characters", sa.Column("body_features_json", sa.JSON(), nullable=True))
    op.add_column("characters", sa.Column("movement_style", sa.String(length=255), nullable=True))
    op.add_column(
        "characters",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "character_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("asset_url", sa.String(length=1024), nullable=False),
        sa.Column("prompt_used", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_character_assets_character_id", "character_assets", ["character_id"], unique=False)

    op.create_table(
        "character_outfits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outfit_name", sa.String(length=128), nullable=False),
        sa.Column("palette_json", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reference_asset_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_character_outfits_character_id", "character_outfits", ["character_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_character_outfits_character_id", table_name="character_outfits")
    op.drop_table("character_outfits")

    op.drop_index("ix_character_assets_character_id", table_name="character_assets")
    op.drop_table("character_assets")

    op.drop_column("characters", "is_locked")
    op.drop_column("characters", "movement_style")
    op.drop_column("characters", "body_features_json")
    op.drop_column("characters", "face_features_json")
    op.drop_column("characters", "style_archetype")
    op.drop_column("characters", "age_range")
    op.drop_column("characters", "identity_summary")
