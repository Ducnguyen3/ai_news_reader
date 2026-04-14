"""initial schema

Revision ID: 20260410_0001
Revises: None
Create Date: 2026-04-10 20:05:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260410_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sources_name", "sources", ["name"], unique=True)
    op.create_unique_constraint("uq_sources_domain", "sources", ["domain"])

    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_authors_name", "authors", ["name"], unique=True)

    op.create_table(
        "crawl_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("total_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_crawl_jobs_source_id", "crawl_jobs", ["source_id"], unique=False)
    op.create_index("ix_crawl_jobs_status", "crawl_jobs", ["status"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("category_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "slug", name="uq_categories_source_slug"),
    )
    op.create_index("ix_categories_source_id", "categories", ["source_id"], unique=False)

    op.create_table(
        "raw_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("crawl_job_id", sa.Integer(), sa.ForeignKey("crawl_jobs.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("page_type", sa.String(length=50), server_default="article", nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("html_content", sa.Text(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_raw_pages_source_id", "raw_pages", ["source_id"], unique=False)
    op.create_index("ix_raw_pages_crawl_job_id", "raw_pages", ["crawl_job_id"], unique=False)
    op.create_index("ix_raw_pages_url_hash", "raw_pages", ["url_hash"], unique=False)
    op.create_index("ix_raw_pages_checksum", "raw_pages", ["checksum"], unique=False)

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("raw_page_id", sa.Integer(), sa.ForeignKey("raw_pages.id"), nullable=True),
        sa.Column("article_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("publish_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="vi", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="published", nullable=False),
        sa.Column("word_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reading_time_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("main_image_url", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("url_hash", name="uq_articles_url_hash"),
    )
    op.create_index("ix_articles_publish_time", "articles", ["publish_time"], unique=False)
    op.create_index("ix_articles_source_id", "articles", ["source_id"], unique=False)
    op.create_index("ix_articles_article_url", "articles", ["article_url"], unique=False)
    op.create_index("ix_articles_canonical_url", "articles", ["canonical_url"], unique=False)
    op.create_index("ix_articles_content_hash", "articles", ["content_hash"], unique=False)

    op.create_table(
        "article_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("article_id", "category_id", name="uq_article_categories_article_category"),
    )
    op.create_index("ix_article_categories_article_id", "article_categories", ["article_id"], unique=False)
    op.create_index("ix_article_categories_category_id", "article_categories", ["category_id"], unique=False)

    op.create_table(
        "article_authors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("authors.id"), nullable=False),
        sa.Column("author_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("article_id", "author_id", name="uq_article_authors_article_author"),
    )
    op.create_index("ix_article_authors_article_id", "article_authors", ["article_id"], unique=False)
    op.create_index("ix_article_authors_author_id", "article_authors", ["author_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_article_authors_author_id", table_name="article_authors")
    op.drop_index("ix_article_authors_article_id", table_name="article_authors")
    op.drop_table("article_authors")
    op.drop_index("ix_article_categories_category_id", table_name="article_categories")
    op.drop_index("ix_article_categories_article_id", table_name="article_categories")
    op.drop_table("article_categories")
    op.drop_index("ix_articles_content_hash", table_name="articles")
    op.drop_index("ix_articles_canonical_url", table_name="articles")
    op.drop_index("ix_articles_article_url", table_name="articles")
    op.drop_index("ix_articles_source_id", table_name="articles")
    op.drop_index("ix_articles_publish_time", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_raw_pages_checksum", table_name="raw_pages")
    op.drop_index("ix_raw_pages_url_hash", table_name="raw_pages")
    op.drop_index("ix_raw_pages_crawl_job_id", table_name="raw_pages")
    op.drop_index("ix_raw_pages_source_id", table_name="raw_pages")
    op.drop_table("raw_pages")
    op.drop_index("ix_categories_source_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_crawl_jobs_status", table_name="crawl_jobs")
    op.drop_index("ix_crawl_jobs_source_id", table_name="crawl_jobs")
    op.drop_table("crawl_jobs")
    op.drop_index("ix_authors_name", table_name="authors")
    op.drop_table("authors")
    op.drop_constraint("uq_sources_domain", "sources", type_="unique")
    op.drop_index("ix_sources_name", table_name="sources")
    op.drop_table("sources")
