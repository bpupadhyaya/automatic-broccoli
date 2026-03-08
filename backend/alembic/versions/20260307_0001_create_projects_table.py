"""create projects table

Revision ID: 20260307_0001
Revises: 
Create Date: 2026-03-07 15:20:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260307_0001"
down_revision: Optional[str] = None
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("target_original_video_url", sa.String(length=1024), nullable=False),
        sa.Column("example_original_video_url", sa.String(length=1024), nullable=False),
        sa.Column("example_remix_video_url", sa.String(length=1024), nullable=False),
        sa.Column("character_style", sa.String(length=255), nullable=False),
        sa.Column("region_style_swap", sa.String(length=255), nullable=False),
        sa.Column("gender_mix", sa.String(length=255), nullable=False),
        sa.Column("age_group", sa.String(length=255), nullable=False),
        sa.Column("ethnic_cultural_direction", sa.String(length=255), nullable=False),
        sa.Column("celebrity_mode", sa.String(length=64), nullable=False, server_default="fictional_only"),
        sa.Column("visual_theme", sa.String(length=255), nullable=False),
        sa.Column("costume_style", sa.String(length=255), nullable=False),
        sa.Column("lighting_style", sa.String(length=255), nullable=False),
        sa.Column("cinematic_mood", sa.String(length=255), nullable=False),
        sa.Column("dance_style", sa.String(length=255), nullable=False),
        sa.Column("energy_level", sa.String(length=255), nullable=False),
        sa.Column("camera_style", sa.String(length=255), nullable=False),
        sa.Column("preserve_melody", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remix_genre", sa.String(length=255), nullable=False),
        sa.Column("beat_intensity", sa.String(length=255), nullable=False),
        sa.Column("vocal_handling", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("transformation_summary", sa.Text(), nullable=True),
        sa.Column("character_bible", sa.JSON(), nullable=True),
        sa.Column("storyboard_scenes", sa.JSON(), nullable=True),
        sa.Column("scene_prompts", sa.JSON(), nullable=True),
        sa.Column("editing_plan", sa.JSON(), nullable=True),
        sa.Column("consistency_rules", sa.JSON(), nullable=True),
        sa.Column("manifest", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("projects")
