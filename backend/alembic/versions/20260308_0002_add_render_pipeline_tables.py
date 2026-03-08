"""add render pipeline tables

Revision ID: 20260308_0002
Revises: 20260307_0001
Create Date: 2026-03-08 01:20:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260308_0002"
down_revision: Optional[str] = "20260307_0001"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("config_json", sa.JSON(), nullable=True))

    op.create_table(
        "characters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=128), nullable=False),
        sa.Column("identity_json", sa.JSON(), nullable=False),
        sa.Column("reference_asset_urls", sa.JSON(), nullable=False),
        sa.Column("consistency_rules_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_characters_project_id", "characters", ["project_id"], unique=False)

    op.create_table(
        "shots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shot_code", sa.String(length=64), nullable=False),
        sa.Column("section", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("shot_type", sa.String(length=255), nullable=False),
        sa.Column("camera_framing", sa.String(length=255), nullable=False),
        sa.Column("camera_move", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("cast_json", sa.JSON(), nullable=False),
        sa.Column("wardrobe", sa.String(length=255), nullable=False),
        sa.Column("choreography_note", sa.Text(), nullable=False),
        sa.Column("lighting_note", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("references_json", sa.JSON(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("qc_score", sa.Float(), nullable=True),
        sa.Column("approved_clip_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "shot_code", name="uq_shots_project_shot_code"),
    )
    op.create_index("ix_shots_project_id", "shots", ["project_id"], unique=False)
    op.create_index("ix_shots_shot_code", "shots", ["shot_code"], unique=False)

    op.create_table(
        "render_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shot_id", sa.Integer(), sa.ForeignKey("shots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_job_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("raw_output_url", sa.String(length=1024), nullable=True),
        sa.Column("estimated_duration_sec", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_render_jobs_project_id", "render_jobs", ["project_id"], unique=False)
    op.create_index("ix_render_jobs_shot_id", "render_jobs", ["shot_id"], unique=False)
    op.create_index("ix_render_jobs_provider_job_id", "render_jobs", ["provider_job_id"], unique=False)

    op.create_table(
        "manifests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_manifests_project_id", "manifests", ["project_id"], unique=False)

    op.create_table(
        "exports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(length=64), nullable=False),
        sa.Column("output_url", sa.String(length=1024), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_exports_project_id", "exports", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_exports_project_id", table_name="exports")
    op.drop_table("exports")

    op.drop_index("ix_manifests_project_id", table_name="manifests")
    op.drop_table("manifests")

    op.drop_index("ix_render_jobs_provider_job_id", table_name="render_jobs")
    op.drop_index("ix_render_jobs_shot_id", table_name="render_jobs")
    op.drop_index("ix_render_jobs_project_id", table_name="render_jobs")
    op.drop_table("render_jobs")

    op.drop_index("ix_shots_shot_code", table_name="shots")
    op.drop_index("ix_shots_project_id", table_name="shots")
    op.drop_table("shots")

    op.drop_index("ix_characters_project_id", table_name="characters")
    op.drop_table("characters")

    op.drop_column("projects", "config_json")
