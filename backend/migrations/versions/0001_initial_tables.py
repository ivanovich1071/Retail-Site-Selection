"""Initial tables — all models

Revision ID: 0001
Revises:
Create Date: 2026-06-17

Schema matches the SQLAlchemy models exactly (verified against app/models/*).
Native PostgreSQL enums are used so `alembic check` reports no drift against
the ORM definitions.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

user_role = sa.Enum("admin", "manager", "viewer", name="userrole")
location_status = sa.Enum("draft", "in_review", "approved", "rejected", "opened", name="locationstatus")
batch_status = sa.Enum("pending", "running", "completed", "failed", "cancelled", name="batchjobstatus")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", user_role, nullable=True, server_default="manager"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
    )

    # ── locations ────────────────────────────────────────────────────────
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=True),
        sa.Column("building_polygon", Geometry("POLYGON", srid=4326), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("parking_spaces", sa.Integer(), nullable=True),
        sa.Column("floor_number", sa.Integer(), nullable=True),
        sa.Column("visibility_score", sa.Float(), nullable=True),
        sa.Column("status", location_status, nullable=True, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_path", sa.String(500), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
    )

    # ── competitors ───────────────────────────────────────────────────────
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("brand_name", sa.String(255), nullable=False, index=True),
        sa.Column("store_format", sa.String(100), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("source", sa.String(50), nullable=True, server_default="2gis"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
    )

    # ── our_stores ────────────────────────────────────────────────────────
    op.create_table(
        "our_stores",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("store_code", sa.String(50), nullable=True, unique=True),
        sa.Column("store_format", sa.String(100), nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("revenue_monthly", sa.Float(), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
    )

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
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("region_code", "data_year", name="uq_demographics_region_year"),
    )

    # ── scoring_results ───────────────────────────────────────────────────
    op.create_table(
        "scoring_results",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("huff_market_share", sa.Float(), nullable=True),
        sa.Column("cannibalization_risk", sa.Float(), nullable=True),
        sa.Column("revenue_forecast", sa.Float(), nullable=True),
        sa.Column("score_demographics", sa.Float(), nullable=True),
        sa.Column("score_competitors", sa.Float(), nullable=True),
        sa.Column("score_accessibility", sa.Float(), nullable=True),
        sa.Column("score_visibility", sa.Float(), nullable=True),
        sa.Column("score_location", sa.Float(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("version", sa.String(50), nullable=True, server_default="1.0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
    )

    # ── batch_jobs ────────────────────────────────────────────────────────
    op.create_table(
        "batch_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("status", batch_status, nullable=True, server_default="pending"),
        sa.Column("total_rows", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("processed_rows", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── batch_results ─────────────────────────────────────────────────────
    op.create_table(
        "batch_results",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("batch_job_id", sa.Integer(), sa.ForeignKey("batch_jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("huff_share", sa.Float(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("batch_results")
    op.drop_table("batch_jobs")
    op.drop_table("scoring_results")
    op.drop_table("demographics_zones")
    op.drop_table("our_stores")
    op.drop_table("competitors")
    op.drop_table("locations")
    op.drop_table("users")
    batch_status.drop(op.get_bind(), checkfirst=True)
    location_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
    op.execute("DROP EXTENSION IF EXISTS postgis")
