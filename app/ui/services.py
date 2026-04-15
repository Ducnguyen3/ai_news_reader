from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from app.ai.query_service import AIQueryService
from app.ai.service import DemoAIProvider
from app.db.session import get_db_session
from app.repositories.article_ai_summary_repository import SqlAlchemyArticleAISummaryRepository
from app.repositories.article_ai_tag_repository import SqlAlchemyArticleAITagRepository
from app.repositories.article_embedding_repository import SqlAlchemyArticleEmbeddingRepository
from app.repositories.article_repository import ArticleRepository
from app.repositories.rag_chunk_repository import SqlAlchemyRAGChunkRepository
from app.ui.view_models import (
    ArticleDetailView,
    ArticleListItem,
    RagAnswerView,
    RagContextItem,
    RelatedArticleItem,
)


SessionFactory = Callable[[], AbstractContextManager]


class NewsUIService:
    """Facade used by Streamlit to read news and AI enrichment data."""

    def __init__(self, session_factory: SessionFactory = get_db_session) -> None:
        self.session_factory = session_factory

    def list_sources(self) -> list[str]:
        with self.session_factory() as session:
            article_repository = ArticleRepository(session)
            return [source.name for source in article_repository.list_sources()]

    def list_articles(
        self,
        source: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
    ) -> list[ArticleListItem]:
        with self.session_factory() as session:
            article_repository = ArticleRepository(session)
            articles = article_repository.list_articles(source_name=source, keyword=keyword, limit=limit)
            return [
                ArticleListItem(
                    article_id=article.id,
                    title=article.title,
                    source_name=article.source.name if article.source else "unknown",
                    publish_time=article.publish_time,
                    primary_category=self._primary_category(article),
                )
                for article in articles
            ]

    def get_article_detail(self, article_id: int) -> ArticleDetailView | None:
        with self.session_factory() as session:
            article_repository = ArticleRepository(session)
            summary_repository = SqlAlchemyArticleAISummaryRepository(session)
            tag_repository = SqlAlchemyArticleAITagRepository(session)

            article = article_repository.get_article_by_id(article_id)
            if article is None:
                return None

            summary = summary_repository.get_by_article(article_id, summary_type="brief")
            tags = tag_repository.list_by_article(article_id)
            primary_topic = next((tag.tag_name for tag in tags if tag.tag_type == "topic" and tag.is_primary), None)
            return ArticleDetailView(
                article_id=article.id,
                title=article.title,
                source_name=article.source.name if article.source else "unknown",
                publish_time=article.publish_time,
                article_url=article.article_url,
                content_text=article.content_text,
                summary_text=summary.summary_text if summary is not None else None,
                summary_status=summary.status if summary is not None else "not_enriched",
                primary_topic=primary_topic,
                tags=[tag.tag_name for tag in tags],
                categories=[
                    item.category.name
                    for item in article.article_categories
                    if item.category is not None and item.category.name
                ],
            )

    def get_article_summary(self, article_id: int) -> str | None:
        detail = self.get_article_detail(article_id)
        return detail.summary_text if detail is not None else None

    def get_article_tags(self, article_id: int) -> list[str]:
        detail = self.get_article_detail(article_id)
        return detail.tags if detail is not None else []

    def get_related_articles(self, article_id: int, top_k: int = 5) -> list[RelatedArticleItem]:
        with self.session_factory() as session:
            article_repository = ArticleRepository(session)
            query_service = self._build_query_service(session)
            recommendations = query_service.recommend_related_articles(article_id=article_id, top_k=top_k)
            article_map = {article.id: article for article in article_repository.list_articles_by_ids(
                item.article_id for item in recommendations
            )}
            related_items: list[RelatedArticleItem] = []
            for recommendation in recommendations:
                article = article_map.get(recommendation.article_id)
                if article is None:
                    continue
                related_items.append(
                    RelatedArticleItem(
                        article_id=article.id,
                        title=article.title,
                        source_name=article.source.name if article.source else "unknown",
                        similarity_score=recommendation.score,
                        article_url=article.article_url,
                    )
                )
            return related_items

    def ask_question(self, query_text: str, top_k: int = 5) -> RagAnswerView:
        with self.session_factory() as session:
            article_repository = ArticleRepository(session)
            query_service = self._build_query_service(session)
            answer = query_service.answer_question(query_text=query_text, top_k=top_k)
            contexts = query_service.retrieve_chunks(query_text=query_text, top_k=top_k)
            article_map = {article.id: article for article in article_repository.list_articles_by_ids(
                item["article_id"] for item in contexts
            )}
            context_items = [
                RagContextItem(
                    article_id=int(item["article_id"]),
                    article_title=article_map[int(item["article_id"])].title if int(item["article_id"]) in article_map else "unknown",
                    source_name=article_map[int(item["article_id"])].source.name
                    if int(item["article_id"]) in article_map and article_map[int(item["article_id"])].source
                    else "unknown",
                    score=float(item["score"]),
                    chunk_text=str(item["chunk_text"]),
                )
                for item in contexts
            ]
            return RagAnswerView(
                query_text=query_text,
                answer_text=answer.answer_text,
                related_article_ids=answer.related_article_ids,
                contexts=context_items,
            )

    def _build_query_service(self, session) -> AIQueryService:
        article_repository = ArticleRepository(session)
        return AIQueryService(
            article_repository=article_repository,
            embedding_repository=SqlAlchemyArticleEmbeddingRepository(session),
            rag_chunk_repository=SqlAlchemyRAGChunkRepository(session),
            provider=DemoAIProvider(),
        )

    def _primary_category(self, article) -> str | None:
        for item in article.article_categories:
            if item.is_primary and item.category is not None and item.category.name:
                return item.category.name
        for item in article.article_categories:
            if item.category is not None and item.category.name:
                return item.category.name
        return None
