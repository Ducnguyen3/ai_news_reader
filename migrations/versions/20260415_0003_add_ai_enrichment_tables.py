"""add ai enrichment tables

Revision ID: 20260415_0003
Revises: 20260410_0002
Create Date: 2026-04-15 10:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260415_0003"
down_revision = "20260410_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_ai_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("summary_type", sa.String(length=50), server_default="brief", nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("article_id", "summary_type", name="uq_article_ai_summaries_article_type"),
    )
    op.create_index("ix_article_ai_summaries_article_id", "article_ai_summaries", ["article_id"], unique=False)
    op.create_index("ix_article_ai_summaries_status", "article_ai_summaries", ["status"], unique=False)

    op.create_table(
        "article_ai_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("tag_type", sa.String(length=30), nullable=False),
        sa.Column("tag_name", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("article_id", "tag_type", "tag_name", name="uq_article_ai_tags_article_type_name"),
    )
    op.create_index("ix_article_ai_tags_article_id", "article_ai_tags", ["article_id"], unique=False)
    op.create_index("ix_article_ai_tags_tag_type", "article_ai_tags", ["tag_type"], unique=False)
    op.create_index("ix_article_ai_tags_tag_name", "article_ai_tags", ["tag_name"], unique=False)

    op.create_table(
        "article_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_vector", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("chunk_scope", sa.String(length=50), server_default="title_summary", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("article_id", "chunk_scope", name="uq_article_embeddings_article_scope"),
    )
    op.create_index("ix_article_embeddings_article_id", "article_embeddings", ["article_id"], unique=False)
    op.create_index("ix_article_embeddings_chunk_scope", "article_embeddings", ["chunk_scope"], unique=False)

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("embedding_vector", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("article_id", "chunk_index", name="uq_rag_chunks_article_index"),
    )
    op.create_index("ix_rag_chunks_article_id", "rag_chunks", ["article_id"], unique=False)
    op.create_index("ix_rag_chunks_chunk_index", "rag_chunks", ["chunk_index"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rag_chunks_chunk_index", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_article_id", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_index("ix_article_embeddings_chunk_scope", table_name="article_embeddings")
    op.drop_index("ix_article_embeddings_article_id", table_name="article_embeddings")
    op.drop_table("article_embeddings")
    op.drop_index("ix_article_ai_tags_tag_name", table_name="article_ai_tags")
    op.drop_index("ix_article_ai_tags_tag_type", table_name="article_ai_tags")
    op.drop_index("ix_article_ai_tags_article_id", table_name="article_ai_tags")
    op.drop_table("article_ai_tags")
    op.drop_index("ix_article_ai_summaries_status", table_name="article_ai_summaries")
    op.drop_index("ix_article_ai_summaries_article_id", table_name="article_ai_summaries")
    op.drop_table("article_ai_summaries")
