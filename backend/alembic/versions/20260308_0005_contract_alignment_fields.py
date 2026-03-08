"""add contract-alignment fields

Revision ID: 20260308_0005
Revises: 20260308_0004
Create Date: 2026-03-08 03:10:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260308_0005"
down_revision: Optional[str] = "20260308_0004"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column("render_jobs", sa.Column("output_url", sa.String(length=1024), nullable=True))
    op.add_column("render_jobs", sa.Column("error_message", sa.Text(), nullable=True))

    op.add_column("exports", sa.Column("status", sa.String(length=32), nullable=False, server_default="processing"))
    op.add_column("exports", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    op.add_column("qc_results", sa.Column("identity_score", sa.Float(), nullable=True))
    op.add_column("qc_results", sa.Column("wardrobe_score", sa.Float(), nullable=True))
    op.add_column("qc_results", sa.Column("motion_score", sa.Float(), nullable=True))
    op.add_column("qc_results", sa.Column("prompt_match_score", sa.Float(), nullable=True))
    op.add_column("qc_results", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("qc_results", "notes")
    op.drop_column("qc_results", "prompt_match_score")
    op.drop_column("qc_results", "motion_score")
    op.drop_column("qc_results", "wardrobe_score")
    op.drop_column("qc_results", "identity_score")

    op.drop_column("exports", "updated_at")
    op.drop_column("exports", "status")

    op.drop_column("render_jobs", "error_message")
    op.drop_column("render_jobs", "output_url")
