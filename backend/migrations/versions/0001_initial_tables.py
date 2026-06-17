"""Initial tables — all models

Revision ID: 0001
Revises:
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")),
    )

    # ── locations ────────────────────────────────────────────────────────
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("address", sa.String(512), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("parking_spaces", sa.Integer(), nullable=True),
        sa.Column("floor_number", sa.Integer(), nullable=True),
        sa.Column("visibility_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_path", sa.String(512), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=True),
        sa.Column("building_geom", Geometry("POLYGON", srid=4326), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_locations_geom", "locations", ["geom"], postgresql_using="gist")

    # ── competitors ───────────────────────────────────────────────────────
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("brand_name", sa.String(255), nullable=False),
        sa.Column("store_format", sa.String(100), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("source", sa.String(100), nullable=True, server_default="2gis"),
        sa.Column("external_id", sa.String(255), nullable=True, unique=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_competitors_geom", "competitors", ["geom"], postgresql_using="gist")

    # ── our_stores ────────────────────────────────────────────────────────
    op.create_table(
        "our_stores",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("address", sa.String(512), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_our_stores_geom", "our_stores", ["geom"], postgresql_using="gist")

    # ── demographics_zones ────────────────────────────────────────────────
    op.create_table(
        "demographics_zones",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("region_code", sa.String(20), nullable=True, index=True),
        sa.Column("region_name", sa.String(255), nullable=False),
        sa.Column("district", sa.String(255), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("population_density", sa.Float(), nullable=True),
        sa.Column("avg_salary", sa.Float(), nullable=True),
        sa.Column("median_age", sa.Float(), nullable=True),
        sa.Column("geom", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("data_year", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("region_code", "data_year", name="uq_demographics_region_year"),
    )

    # ── scoring_results ───────────────────────────────────────────────────
    op.create_table(
        "scoring_results",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("score_demographics", sa.Float(), nullable=True),
        sa.Column("score_competitors", sa.Float(), nullable=True),
        sa.Column("score_accessibility", sa.Float(), nullable=True),
        sa.Column("score_visibility", sa.Float(), nullable=True),
        sa.Column("score_location", sa.Float(), nullable=True),
        sa.Column("huff_market_share", sa.Float(), nullable=True),
        sa.Column("cannibalization_risk", sa.Float(), nullable=True),
        sa.Column("revenue_forecast", sa.Float(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")),
    )

    # ── batch_jobs ────────────────────────────────────────────────────────
    op.create_table(
        "batch_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    # ── batch_results ─────────────────────────────────────────────────────
    op.create_table(
        "batch_results",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("batch_jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(512), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("batch_results")
    op.drop_table("batch_jobs")
    op.drop_table("scoring_results")
    op.drop_table("demographics_zones")
    op.drop_index("ix_our_stores_geom", table_name="our_stores", postgresql_using="gist")
    op.drop_table("our_stores")
    op.drop_index("ix_competitors_geom", table_name="competitors", postgresql_using="gist")
    op.drop_table("competitors")
    op.drop_index("ix_locations_geom", table_name="locations", postgresql_using="gist")
    op.drop_table("locations")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS postgis")
