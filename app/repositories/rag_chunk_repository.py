from __future__ import annotations

import json
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import RAGChunk


class RAGChunkStore(Protocol):
    """Storage contract for RAG chunks."""

    def list_by_article(self, article_id: int) -> list[RAGChunk]:
        ...

    def replace_chunks(self, *, article_id: int, chunks: list[dict[str, object]]) -> list[RAGChunk]:
        ...

    def list_all(self) -> list[RAGChunk]:
        ...


class SqlAlchemyRAGChunkRepository:
    """SQLAlchemy implementation for RAG chunks."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_article(self, article_id: int) -> list[RAGChunk]:
        stmt = select(RAGChunk).where(RAGChunk.article_id == article_id).order_by(RAGChunk.chunk_index.asc())
        return list(self.session.execute(stmt).scalars().all())

    def replace_chunks(self, *, article_id: int, chunks: list[dict[str, object]]) -> list[RAGChunk]:
        self.session.execute(delete(RAGChunk).where(RAGChunk.article_id == article_id))
        persisted: list[RAGChunk] = []
        for item in chunks:
            chunk = RAGChunk(
                article_id=article_id,
                chunk_index=int(item["chunk_index"]),
                chunk_text=str(item["chunk_text"]),
                token_count=int(item.get("token_count", 0)),
                embedding_vector=json.dumps(item["embedding_vector"], ensure_ascii=True)
                if item.get("embedding_vector") is not None
                else None,
                embedding_model=str(item["embedding_model"]) if item.get("embedding_model") else None,
                content_hash=str(item["content_hash"]) if item.get("content_hash") else None,
            )
            self.session.add(chunk)
            persisted.append(chunk)
        self.session.flush()
        return persisted

    def list_all(self) -> list[RAGChunk]:
        stmt = select(RAGChunk).order_by(RAGChunk.article_id.desc(), RAGChunk.chunk_index.asc())
        return list(self.session.execute(stmt).scalars().all())


class DeltaRAGChunkRepository:
    """Placeholder Delta implementation for Databricks integration."""

    def __init__(self, spark_session) -> None:
        self.spark = spark_session

    def list_by_article(self, article_id: int) -> list[RAGChunk]:
        raise NotImplementedError("TODO: implement Delta chunk lookup")

    def replace_chunks(self, *, article_id: int, chunks: list[dict[str, object]]) -> list[RAGChunk]:
        raise NotImplementedError("TODO: implement Delta chunk replace")

    def list_all(self) -> list[RAGChunk]:
        raise NotImplementedError("TODO: implement Delta chunk scan")
