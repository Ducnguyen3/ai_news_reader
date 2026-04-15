from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.article_repository import ArticleRepository
from app.utils.helpers import normalize_whitespace, sha256_text
from app.ingestion.contracts import DedupDecision, ParsedArticlePayload


class IngestionDedupService:
    def __init__(self, session: Session) -> None:
        self.article_repository = ArticleRepository(session)

    def evaluate_url(self, url: str) -> DedupDecision:
        url_hash = sha256_text(url.strip().lower())
        if self.article_repository.get_article_by_url_hash(url_hash) is not None:
            return DedupDecision(
                is_duplicate=True,
                duplicate_by="url_hash",
                matched_value=url_hash,
            )
        return DedupDecision(is_duplicate=False)

    def evaluate_article(self, article: ParsedArticlePayload) -> DedupDecision:
        canonical_url = article.canonical_url or article.article_url
        url_decision = self.evaluate_url(canonical_url)
        if url_decision.is_duplicate:
            return url_decision

        content_hash = sha256_text(
            f"{normalize_whitespace(article.title)}|{normalize_whitespace(article.content_text)}".lower()
        )
        if self.article_repository.get_article_by_content_hash(content_hash) is not None:
            return DedupDecision(
                is_duplicate=True,
                duplicate_by="content_hash",
                matched_value=content_hash,
            )
        return DedupDecision(is_duplicate=False)

    # TODO: Add bulk-evaluation helpers once repository-based shared data access exists.
