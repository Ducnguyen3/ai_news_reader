from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    crawl_jobs: Mapped[List["CrawlJob"]] = relationship(back_populates="source")
    raw_pages: Mapped[List["RawPage"]] = relationship(back_populates="source")
    articles: Mapped[List["Article"]] = relationship(back_populates="source")
    categories: Mapped[List["Category"]] = relationship(back_populates="source")
    crawl_daily_summaries: Mapped[List["CrawlDailySummary"]] = relationship(back_populates="source")


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    total_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source: Mapped["Source"] = relationship(back_populates="crawl_jobs")
    raw_pages: Mapped[List["RawPage"]] = relationship(back_populates="crawl_job")
    daily_summaries: Mapped[List["CrawlDailySummary"]] = relationship(back_populates="latest_crawl_job")


class CrawlDailySummary(Base):
    __tablename__ = "crawl_daily_summaries"
    __table_args__ = (
        UniqueConstraint("source_id", "crawl_date", name="uq_crawl_daily_summaries_source_date"),
        Index("ix_crawl_daily_summaries_crawl_date", "crawl_date"),
        Index("ix_crawl_daily_summaries_source_id", "source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    crawl_date: Mapped[date] = mapped_column(nullable=False)
    latest_crawl_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("crawl_jobs.id"))
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    latest_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    latest_finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", server_default="pending")
    total_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source: Mapped["Source"] = relationship(back_populates="crawl_daily_summaries")
    latest_crawl_job: Mapped[Optional["CrawlJob"]] = relationship(back_populates="daily_summaries")


class RawPage(Base):
    __tablename__ = "raw_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    crawl_job_id: Mapped[int] = mapped_column(ForeignKey("crawl_jobs.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_type: Mapped[str] = mapped_column(String(50), nullable=False, default="article", server_default="article")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    html_content: Mapped[Optional[str]] = mapped_column(Text)
    text_content: Mapped[Optional[str]] = mapped_column(Text)
    canonical_url: Mapped[Optional[str]] = mapped_column(Text)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    parser_version: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source: Mapped["Source"] = relationship(back_populates="raw_pages")
    crawl_job: Mapped["CrawlJob"] = relationship(back_populates="raw_pages")
    article: Mapped[Optional["Article"]] = relationship(back_populates="raw_page")


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_articles_url_hash"),
        Index("ix_articles_publish_time", "publish_time"),
        Index("ix_articles_source_id", "source_id"),
        Index("ix_articles_article_url", "article_url"),
        Index("ix_articles_canonical_url", "canonical_url"),
        Index("ix_articles_content_hash", "content_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    raw_page_id: Mapped[Optional[int]] = mapped_column(ForeignKey("raw_pages.id"))
    article_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[Optional[str]] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    publish_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scraped_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="vi", server_default="vi")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="published", server_default="published")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reading_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    main_image_url: Mapped[Optional[str]] = mapped_column(Text)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source: Mapped["Source"] = relationship(back_populates="articles")
    raw_page: Mapped[Optional["RawPage"]] = relationship(back_populates="article")
    article_categories: Mapped[List["ArticleCategory"]] = relationship(back_populates="article")
    article_authors: Mapped[List["ArticleAuthor"]] = relationship(back_populates="article")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("source_id", "slug", name="uq_categories_source_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    category_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source: Mapped["Source"] = relationship(back_populates="categories")
    parent: Mapped[Optional["Category"]] = relationship(remote_side="Category.id")
    article_categories: Mapped[List["ArticleCategory"]] = relationship(back_populates="category")


class ArticleCategory(Base):
    __tablename__ = "article_categories"
    __table_args__ = (
        UniqueConstraint("article_id", "category_id", name="uq_article_categories_article_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    article: Mapped["Article"] = relationship(back_populates="article_categories")
    category: Mapped["Category"] = relationship(back_populates="article_categories")


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    profile_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    article_authors: Mapped[List["ArticleAuthor"]] = relationship(back_populates="author")


class ArticleAuthor(Base):
    __tablename__ = "article_authors"
    __table_args__ = (
        UniqueConstraint("article_id", "author_id", name="uq_article_authors_article_author"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), nullable=False, index=True)
    author_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    article: Mapped["Article"] = relationship(back_populates="article_authors")
    author: Mapped["Author"] = relationship(back_populates="article_authors")
