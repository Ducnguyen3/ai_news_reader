from __future__ import annotations

import json
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ArticleEmbedding


class ArticleEmbeddingStore(Protocol):
    """Storage contract for article-level embeddings."""

    def get_by_article(self, article_id: int, chunk_scope: str = "title_summary") -> ArticleEmbedding | None:
        ...

    def upsert_embedding(
        self,
        *,
        article_id: int,
        embedding_model: str,
        embedding_vector: list[float],
        content_hash: str | None,
        chunk_scope: str,
    ) -> ArticleEmbedding:
        ...

    def list_all(self, chunk_scope: str = "title_summary") -> list[ArticleEmbedding]:
        ...


class SqlAlchemyArticleEmbeddingRepository:
    """SQLAlchemy implementation for article embeddings."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_article(self, article_id: int, chunk_scope: str = "title_summary") -> ArticleEmbedding | None:
        stmt = select(ArticleEmbedding).where(
            ArticleEmbedding.article_id == article_id,
            ArticleEmbedding.chunk_scope == chunk_scope,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_embedding(
        self,
        *,
        article_id: int,
        embedding_model: str,
        embedding_vector: list[float],
        content_hash: str | None,
        chunk_scope: str,
    ) -> ArticleEmbedding:
        embedding = self.get_by_article(article_id=article_id, chunk_scope=chunk_scope)
        if embedding is None:
            embedding = ArticleEmbedding(article_id=article_id, chunk_scope=chunk_scope, embedding_vector="[]")
            self.session.add(embedding)

        embedding.embedding_model = embedding_model
        embedding.embedding_vector = json.dumps(embedding_vector, ensure_ascii=True)
        embedding.content_hash = content_hash
        self.session.flush()
        return embedding

    def list_all(self, chunk_scope: str = "title_summary") -> list[ArticleEmbedding]:
        stmt = select(ArticleEmbedding).where(ArticleEmbedding.chunk_scope == chunk_scope)
        return list(self.session.execute(stmt).scalars().all())


class DeltaArticleEmbeddingRepository:
    """Placeholder Delta implementation for Databricks integration."""

    def __init__(self, spark_session) -> None:
        self.spark = spark_session

    def get_by_article(self, article_id: int, chunk_scope: str = "title_summary") -> ArticleEmbedding | None:
        raise NotImplementedError("TODO: implement Delta embedding lookup")

    def upsert_embedding(
        self,
        *,
        article_id: int,
        embedding_model: str,
        embedding_vector: list[float],
        content_hash: str | None,
        chunk_scope: str,
    ) -> ArticleEmbedding:
        raise NotImplementedError("TODO: implement Delta embedding upsert")

    def list_all(self, chunk_scope: str = "title_summary") -> list[ArticleEmbedding]:
        raise NotImplementedError("TODO: implement Delta embedding scan")
