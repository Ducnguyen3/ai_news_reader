"""add crawl daily summaries

Revision ID: 20260410_0002
Revises: 20260410_0001
Create Date: 2026-04-10 22:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260410_0002"
down_revision = "20260410_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crawl_daily_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("crawl_date", sa.Date(), nullable=False),
        sa.Column("latest_crawl_job_id", sa.Integer(), sa.ForeignKey("crawl_jobs.id"), nullable=True),
        sa.Column("run_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latest_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("total_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "crawl_date", name="uq_crawl_daily_summaries_source_date"),
    )
    op.create_index("ix_crawl_daily_summaries_crawl_date", "crawl_daily_summaries", ["crawl_date"], unique=False)
    op.create_index("ix_crawl_daily_summaries_source_id", "crawl_daily_summaries", ["source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crawl_daily_summaries_source_id", table_name="crawl_daily_summaries")
    op.drop_index("ix_crawl_daily_summaries_crawl_date", table_name="crawl_daily_summaries")
    op.drop_table("crawl_daily_summaries")
