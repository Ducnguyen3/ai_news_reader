from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Article
from app.utils.helpers import normalize_whitespace, sha256_text


class DedupService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def url_hash(self, url: str) -> str:
        return sha256_text(url.strip().lower())

    def content_hash(self, title: str, content_text: str) -> str:
        normalized = f"{normalize_whitespace(title)}|{normalize_whitespace(content_text)}"
        return sha256_text(normalized.lower())

    def article_exists_by_url_hash(self, url_hash: str) -> bool:
        stmt = select(Article.id).where(Article.url_hash == url_hash).limit(1)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def article_exists_by_content_hash(self, content_hash: str) -> bool:
        stmt = select(Article.id).where(Article.content_hash == content_hash).limit(1)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def get_existing_url_hashes(self, urls: Iterable[str]) -> set[str]:
        url_hashes = [self.url_hash(url) for url in urls]
        if not url_hashes:
            return set()

        stmt = select(Article.url_hash).where(Article.url_hash.in_(url_hashes))
        return set(self.session.execute(stmt).scalars().all())

    def filter_new_urls(self, urls: Iterable[str]) -> list[str]:
        normalized_urls = [url for url in urls if url]
        if not normalized_urls:
            return []

        existing_hashes = self.get_existing_url_hashes(normalized_urls)
        return [
            url
            for url in normalized_urls
            if self.url_hash(url) not in existing_hashes
        ]
