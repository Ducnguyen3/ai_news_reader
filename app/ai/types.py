from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.db.models import Article


@dataclass(frozen=True)
class AIArticleInput:
    article_id: int | None
    source_name: str
    title: str
    summary: str | None
    content_text: str
    category_names: list[str] = field(default_factory=list)
    tag_names: list[str] = field(default_factory=list)
    published_at: datetime | None = None

    @classmethod
    def from_article(cls, article: Article) -> "AIArticleInput":
        category_names = [
            item.category.name
            for item in article.article_categories
            if item.category is not None and item.category.name
        ]
        tag_names = [item.tag_name for item in article.ai_tags if item.tag_name]
        source_name = article.source.name if article.source is not None else "unknown"
        return cls(
            article_id=article.id,
            source_name=source_name,
            title=article.title,
            summary=article.summary,
            content_text=article.content_text,
            category_names=category_names,
            tag_names=tag_names,
            published_at=article.publish_time,
        )


class AIProvider(Protocol):
    """Minimal provider contract for summary, classification, embedding, and QA."""

    def summarize(self, *, prompt: str, article: AIArticleInput) -> str:
        ...

    def classify(self, *, prompt: str, article: AIArticleInput) -> dict[str, object]:
        ...

    def embed(self, text: str) -> list[float]:
        ...

    def answer(self, *, prompt: str, query_text: str, context_blocks: list[str]) -> str:
        ...
