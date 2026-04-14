from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    Article,
    ArticleAuthor,
    ArticleCategory,
    Author,
    Category,
    RawPage,
    Source,
)
from app.parsers.common import ParsedArticle
from app.services.dedup_service import DedupService
from app.utils.helpers import count_words, estimate_reading_time_minutes, slugify


class ArticleService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.dedup_service = DedupService(session)

    def get_or_create_source(self, name: str, domain: str) -> Source:
        stmt = select(Source).where(Source.name == name)
        source = self.session.execute(stmt).scalar_one_or_none()
        if source:
            return source

        source = Source(name=name, domain=domain, is_active=True)
        self.session.add(source)
        self.session.flush()
        return source

    def save_raw_page(
        self,
        *,
        source_id: int,
        crawl_job_id: int,
        url: str,
        url_hash: str,
        page_type: str,
        http_status: int | None,
        html_content: str | None,
        text_content: str | None,
        canonical_url: str | None,
        checksum: str | None,
        parser_version: str | None,
    ) -> RawPage:
        raw_page = RawPage(
            source_id=source_id,
            crawl_job_id=crawl_job_id,
            url=url,
            url_hash=url_hash,
            page_type=page_type,
            http_status=http_status,
            html_content=html_content if self.settings.save_raw_html else None,
            text_content=text_content,
            canonical_url=canonical_url,
            checksum=checksum,
            parser_version=parser_version,
        )
        self.session.add(raw_page)
        self.session.flush()
        return raw_page

    def save_article(
        self,
        *,
        source: Source,
        raw_page: RawPage,
        parsed_article: ParsedArticle,
    ) -> Optional[Article]:
        article_url = parsed_article.article_url
        canonical_url = parsed_article.canonical_url or article_url
        url_hash = self.dedup_service.url_hash(canonical_url)
        content_hash = self.dedup_service.content_hash(
            parsed_article.title,
            parsed_article.content_text,
        )

        if self.dedup_service.article_exists_by_url_hash(url_hash):
            return None
        if self.dedup_service.article_exists_by_content_hash(content_hash):
            return None

        word_count = count_words(parsed_article.content_text)
        article = Article(
            source_id=source.id,
            raw_page_id=raw_page.id,
            article_url=article_url,
            canonical_url=canonical_url,
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

        self._attach_categories(article, source.id, parsed_article.category_names)
        self._attach_authors(article, parsed_article.author_names)
        return article

    def _attach_categories(self, article: Article, source_id: int, names: Iterable[str]) -> None:
        for index, name in enumerate(names):
            slug = slugify(name)
            if not slug:
                continue
            stmt = select(Category).where(Category.source_id == source_id, Category.slug == slug)
            category = self.session.execute(stmt).scalar_one_or_none()
            if category is None:
                category = Category(
                    source_id=source_id,
                    name=name,
                    slug=slug,
                )
                self.session.add(category)
                self.session.flush()

            mapping_stmt = select(ArticleCategory).where(
                ArticleCategory.article_id == article.id,
                ArticleCategory.category_id == category.id,
            )
            exists = self.session.execute(mapping_stmt).scalar_one_or_none()
            if exists is None:
                self.session.add(
                    ArticleCategory(
                        article_id=article.id,
                        category_id=category.id,
                        is_primary=index == 0,
                    )
                )

    def _attach_authors(self, article: Article, names: Iterable[str]) -> None:
        for index, name in enumerate(names):
            cleaned = name.strip()
            if not cleaned:
                continue
            stmt = select(Author).where(Author.name == cleaned)
            author = self.session.execute(stmt).scalar_one_or_none()
            if author is None:
                author = Author(name=cleaned)
                self.session.add(author)
                self.session.flush()

            mapping_stmt = select(ArticleAuthor).where(
                ArticleAuthor.article_id == article.id,
                ArticleAuthor.author_id == author.id,
            )
            exists = self.session.execute(mapping_stmt).scalar_one_or_none()
            if exists is None:
                self.session.add(
                    ArticleAuthor(
                        article_id=article.id,
                        author_id=author.id,
                        author_order=index + 1,
                    )
                )
