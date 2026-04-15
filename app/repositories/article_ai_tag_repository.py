from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import ArticleAITag


class ArticleAITagStore(Protocol):
    """Storage contract for AI-generated article tags."""

    def list_by_article(self, article_id: int) -> list[ArticleAITag]:
        ...

    def replace_tags(
        self,
        *,
        article_id: int,
        tags: list[dict[str, object]],
        model_name: str,
        model_version: str,
        prompt_version: str,
    ) -> list[ArticleAITag]:
        ...


class SqlAlchemyArticleAITagRepository:
    """SQLAlchemy implementation for AI tags."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_article(self, article_id: int) -> list[ArticleAITag]:
        stmt = select(ArticleAITag).where(ArticleAITag.article_id == article_id).order_by(
            ArticleAITag.is_primary.desc(),
            ArticleAITag.confidence.desc(),
            ArticleAITag.tag_name.asc(),
        )
        return list(self.session.execute(stmt).scalars().all())

    def replace_tags(
        self,
        *,
        article_id: int,
        tags: list[dict[str, object]],
        model_name: str,
        model_version: str,
        prompt_version: str,
    ) -> list[ArticleAITag]:
        self.session.execute(delete(ArticleAITag).where(ArticleAITag.article_id == article_id))
        persisted: list[ArticleAITag] = []
        for item in tags:
            tag = ArticleAITag(
                article_id=article_id,
                tag_type=str(item["tag_type"]),
                tag_name=str(item["tag_name"]),
                confidence=int(item.get("confidence", 0)),
                is_primary=bool(item.get("is_primary", False)),
                model_name=model_name,
                model_version=model_version,
                prompt_version=prompt_version,
            )
            self.session.add(tag)
            persisted.append(tag)
        self.session.flush()
        return persisted


class DeltaArticleAITagRepository:
    """Placeholder Delta implementation for Databricks integration."""

    def __init__(self, spark_session) -> None:
        self.spark = spark_session

    def list_by_article(self, article_id: int) -> list[ArticleAITag]:
        raise NotImplementedError("TODO: implement Delta tag lookup")

    def replace_tags(
        self,
        *,
        article_id: int,
        tags: list[dict[str, object]],
        model_name: str,
        model_version: str,
        prompt_version: str,
    ) -> list[ArticleAITag]:
        raise NotImplementedError("TODO: implement Delta tag replace")
