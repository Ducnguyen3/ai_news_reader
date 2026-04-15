from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import (
    Article,
    ArticleAISummary,
    ArticleAuthor,
    ArticleCategory,
    Author,
    Category,
    RawPage,
    Source,
)
from app.ingestion.contracts import ParsedArticlePayload
from app.ingestion.parsers.common import ParsedArticle
from app.utils.helpers import count_words, estimate_reading_time_minutes, slugify


class ArticleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()

    def get_source_by_name(self, name: str) -> Source | None:
        stmt = select(Source).where(Source.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_sources(self) -> list[Source]:
        stmt = select(Source).where(Source.is_active.is_(True)).order_by(Source.name.asc())
        return list(self.session.execute(stmt).scalars().all())

    def get_or_create_source(self, name: str, domain: str) -> Source:
        source = self.get_source_by_name(name)
        if source is not None:
            return source

        source = Source(name=name, domain=domain, is_active=True)
        self.session.add(source)
        self.session.flush()
        return source

    def get_article_by_url_hash(self, url_hash: str) -> Article | None:
        stmt = select(Article).where(Article.url_hash == url_hash).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_article_by_content_hash(self, content_hash: str) -> Article | None:
        stmt = select(Article).where(Article.content_hash == content_hash).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_article_by_id(self, article_id: int) -> Article | None:
        stmt = (
            select(Article)
            .options(
                selectinload(Article.source),
                selectinload(Article.article_categories).selectinload(ArticleCategory.category),
                selectinload(Article.ai_tags),
            )
            .where(Article.id == article_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_articles_by_ids(self, article_ids: Iterable[int]) -> list[Article]:
        ids = [item for item in article_ids if item is not None]
        if not ids:
            return []

        stmt = (
            select(Article)
            .options(
                selectinload(Article.source),
                selectinload(Article.article_categories).selectinload(ArticleCategory.category),
                selectinload(Article.ai_tags),
            )
            .where(Article.id.in_(ids))
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_articles_pending_ai_enrichment(self, limit: int = 100) -> list[Article]:
        stmt = (
            select(Article)
            .options(
                selectinload(Article.source),
                selectinload(Article.article_categories).selectinload(ArticleCategory.category),
                selectinload(Article.ai_tags),
            )
            .outerjoin(
                ArticleAISummary,
                (ArticleAISummary.article_id == Article.id) & (ArticleAISummary.summary_type == "brief"),
            )
            .where((ArticleAISummary.id.is_(None)) | (ArticleAISummary.status != "completed"))
            .order_by(Article.id.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_articles(
        self,
        *,
        source_name: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
    ) -> list[Article]:
        stmt = (
            select(Article)
            .options(
                selectinload(Article.source),
                selectinload(Article.article_categories).selectinload(ArticleCategory.category),
            )
            .join(Source, Source.id == Article.source_id)
            .order_by(Article.publish_time.desc().nullslast(), Article.id.desc())
            .limit(limit)
        )

        if source_name:
            stmt = stmt.where(Source.name == source_name)
        if keyword:
            normalized_keyword = f"%{keyword.strip()}%"
            stmt = stmt.where(Article.title.ilike(normalized_keyword))

        return list(self.session.execute(stmt).scalars().all())

    def create_article(
        self,
        *,
        source: Source,
        raw_page: RawPage,
        parsed_article: ParsedArticle | ParsedArticlePayload,
        url_hash: str,
        content_hash: str,
    ) -> Article:
        word_count = count_words(parsed_article.content_text)
        article = Article(
            source_id=source.id,
            raw_page_id=raw_page.id,
            article_url=parsed_article.article_url,
            canonical_url=parsed_article.canonical_url or parsed_article.article_url,
            url_hash=url_hash,
            title=parsed_article.title,
            summary=parsed_article.summary,
            content_text=parsed_article.content_text,
            publish_time=parsed_article.publish_time,
            updated_time=parsed_article.updated_time,
            language=parsed_article.language,
            status=self.settings.article_status_default,
            word_count=word_count,
            reading_time_minutes=estimate_reading_time_minutes(word_count),
            main_image_url=parsed_article.main_image_url,
            content_hash=content_hash,
        )
        self.session.add(article)
        self.session.flush()
        return article

    def attach_categories(self, article: Article, source_id: int, names: Iterable[str]) -> None:
        for index, name in enumerate(names):
            category = self.get_or_create_category(source_id=source_id, name=name)
            if category is None:
                continue
            self.attach_category(article_id=article.id, category_id=category.id, is_primary=index == 0)

    def attach_authors(self, article: Article, names: Iterable[str]) -> None:
        for index, name in enumerate(names):
            author = self.get_or_create_author(name)
            if author is None:
                continue
            self.attach_author(article_id=article.id, author_id=author.id, author_order=index + 1)

    def get_or_create_category(self, *, source_id: int, name: str) -> Category | None:
        slug = slugify(name)
        if not slug:
            return None

        stmt = select(Category).where(Category.source_id == source_id, Category.slug == slug)
        category = self.session.execute(stmt).scalar_one_or_none()
        if category is not None:
            return category

        category = Category(source_id=source_id, name=name, slug=slug)
        self.session.add(category)
        self.session.flush()
        return category

    def attach_category(self, *, article_id: int, category_id: int, is_primary: bool) -> ArticleCategory:
        stmt = select(ArticleCategory).where(
            ArticleCategory.article_id == article_id,
            ArticleCategory.category_id == category_id,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        mapping = ArticleCategory(
            article_id=article_id,
            category_id=category_id,
            is_primary=is_primary,
        )
        self.session.add(mapping)
        self.session.flush()
        return mapping

    def get_or_create_author(self, name: str) -> Author | None:
        cleaned = name.strip()
        if not cleaned:
            return None

        stmt = select(Author).where(Author.name == cleaned)
        author = self.session.execute(stmt).scalar_one_or_none()
        if author is not None:
            return author

        author = Author(name=cleaned)
        self.session.add(author)
        self.session.flush()
        return author

    def attach_author(self, *, article_id: int, author_id: int, author_order: int) -> ArticleAuthor:
        stmt = select(ArticleAuthor).where(
            ArticleAuthor.article_id == article_id,
            ArticleAuthor.author_id == author_id,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        mapping = ArticleAuthor(
            article_id=article_id,
            author_id=author_id,
            author_order=author_order,
        )
        self.session.add(mapping)
        self.session.flush()
        return mapping

    # TODO: Add methods for AI metadata persistence if summary/topic/embedding
    # columns or side tables are introduced later.
