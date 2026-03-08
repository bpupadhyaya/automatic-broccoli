"""add qc_result_json to render jobs

Revision ID: 20260308_0003
Revises: 20260308_0002
Create Date: 2026-03-08 01:40:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260308_0003"
down_revision: Optional[str] = "20260308_0002"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column("render_jobs", sa.Column("qc_result_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("render_jobs", "qc_result_json")
