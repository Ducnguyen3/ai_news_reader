from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ArticleListItem:
    article_id: int
    title: str
    source_name: str
    publish_time: datetime | None
    primary_category: str | None


@dataclass(frozen=True)
class RelatedArticleItem:
    article_id: int
    title: str
    source_name: str
    similarity_score: float
    article_url: str


@dataclass(frozen=True)
class RagContextItem:
    article_id: int
    article_title: str
    source_name: str
    score: float
    chunk_text: str


@dataclass(frozen=True)
class RagAnswerView:
    query_text: str
    answer_text: str
    related_article_ids: list[int] = field(default_factory=list)
    contexts: list[RagContextItem] = field(default_factory=list)


@dataclass(frozen=True)
class ArticleDetailView:
    article_id: int
    title: str
    source_name: str
    publish_time: datetime | None
    article_url: str
    content_text: str
    summary_text: str | None
    summary_status: str
    primary_topic: str | None
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
