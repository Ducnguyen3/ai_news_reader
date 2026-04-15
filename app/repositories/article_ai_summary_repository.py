from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ArticleAISummary


class ArticleAISummaryStore(Protocol):
    """Storage contract for article summaries across SQLAlchemy/Delta backends."""

    def get_by_article(self, article_id: int, summary_type: str = "brief") -> ArticleAISummary | None:
        ...

    def upsert_summary(
        self,
        *,
        article_id: int,
        summary_text: str | None,
        summary_type: str,
        model_name: str,
        model_version: str,
        prompt_version: str,
        status: str,
        error_message: str | None = None,
    ) -> ArticleAISummary:
        ...


class SqlAlchemyArticleAISummaryRepository:
    """SQLAlchemy implementation for persisted article summaries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_article(self, article_id: int, summary_type: str = "brief") -> ArticleAISummary | None:
        stmt = select(ArticleAISummary).where(
            ArticleAISummary.article_id == article_id,
            ArticleAISummary.summary_type == summary_type,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_summary(
        self,
        *,
        article_id: int,
        summary_text: str | None,
        summary_type: str,
        model_name: str,
        model_version: str,
        prompt_version: str,
        status: str,
        error_message: str | None = None,
    ) -> ArticleAISummary:
        summary = self.get_by_article(article_id=article_id, summary_type=summary_type)
        if summary is None:
            summary = ArticleAISummary(article_id=article_id, summary_type=summary_type)
            self.session.add(summary)

        summary.summary_text = summary_text
        summary.model_name = model_name
        summary.model_version = model_version
        summary.prompt_version = prompt_version
        summary.status = status
        summary.error_message = error_message
        self.session.flush()
        return summary


class DeltaArticleAISummaryRepository:
    """Placeholder Delta implementation for Databricks integration."""

    def __init__(self, spark_session) -> None:
        self.spark = spark_session

    def get_by_article(self, article_id: int, summary_type: str = "brief") -> ArticleAISummary | None:
        raise NotImplementedError("TODO: implement Delta summary lookup")

    def upsert_summary(
        self,
        *,
        article_id: int,
        summary_text: str | None,
        summary_type: str,
        model_name: str,
        model_version: str,
        prompt_version: str,
        status: str,
        error_message: str | None = None,
    ) -> ArticleAISummary:
        raise NotImplementedError("TODO: implement Delta summary upsert")
