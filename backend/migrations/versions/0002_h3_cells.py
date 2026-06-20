"""H3 spatial cells

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "h3_cells",
        sa.Column("h3_index", sa.String(16), primary_key=True),
        sa.Column("resolution", sa.Integer(), nullable=False, index=True),
        sa.Column("center_lat", sa.Float(), nullable=False),
        sa.Column("center_lon", sa.Float(), nullable=False),
        sa.Column("population", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("density_per_sqkm", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_income", sa.Float(), nullable=True),
        sa.Column("competitor_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("h3_cells")
