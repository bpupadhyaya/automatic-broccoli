"""add qc results table

Revision ID: 20260308_0004
Revises: 20260308_0003
Create Date: 2026-03-08 02:40:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260308_0004"
down_revision: Optional[str] = "20260308_0003"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "qc_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shot_id", sa.Integer(), sa.ForeignKey("shots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("render_job_id", sa.Integer(), sa.ForeignKey("render_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scores_json", sa.JSON(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_qc_results_project_id", "qc_results", ["project_id"], unique=False)
    op.create_index("ix_qc_results_shot_id", "qc_results", ["shot_id"], unique=False)
    op.create_index("ix_qc_results_render_job_id", "qc_results", ["render_job_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_qc_results_render_job_id", table_name="qc_results")
    op.drop_index("ix_qc_results_shot_id", table_name="qc_results")
    op.drop_index("ix_qc_results_project_id", table_name="qc_results")
    op.drop_table("qc_results")
