from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class RawPagePayload:
    source_name: str
    url: str
    page_type: str
    http_status: Optional[int]
    html_content: Optional[str]
    canonical_url: Optional[str] = None


@dataclass(frozen=True)
class ParsedArticlePayload:
    source_name: str
    article_url: str
    canonical_url: Optional[str]
    title: str
    summary: Optional[str]
    content_text: str
    publish_time: Optional[datetime]
    updated_time: Optional[datetime] = None
    author_names: list[str] = field(default_factory=list)
    category_names: list[str] = field(default_factory=list)
    main_image_url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    language: str = "vi"


@dataclass(frozen=True)
class DedupDecision:
    is_duplicate: bool
    duplicate_by: Optional[str] = None
    matched_value: Optional[str] = None


@dataclass(frozen=True)
class IngestionArticleRecord:
    raw_page: RawPagePayload
    parsed_article: ParsedArticlePayload
    dedup_decision: DedupDecision


@dataclass(frozen=True)
class IngestionResult:
    source_name: str
    total_found: int
    total_selected: int
    total_duplicates: int
    total_failed: int
    records: list[IngestionArticleRecord] = field(default_factory=list)
