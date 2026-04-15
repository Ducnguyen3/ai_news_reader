from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai.service import AIEnrichmentResult, AIService
from app.repositories.article_repository import ArticleRepository


class AIEnrichmentJob:
    """Background/batch entrypoints for AI enrichment after persistence."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.ai_service = AIService(article_repository=ArticleRepository(session))

    def run_ai_enrichment_for_article(self, article_id: int) -> AIEnrichmentResult | None:
        return self.ai_service.process_article(article_id)

    def run_ai_enrichment_for_articles(self, article_ids: list[int]) -> list[AIEnrichmentResult]:
        return self.ai_service.process_articles(article_ids)

    def run_ai_enrichment_for_pending_articles(self, limit: int = 100) -> list[AIEnrichmentResult]:
        return self.ai_service.process_pending_articles(limit=limit)
