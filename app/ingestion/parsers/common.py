from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.ingestion.contracts import ParsedArticlePayload


@dataclass
class ParsedArticle:
    source_name: str
    article_url: str
    canonical_url: Optional[str]
    title: str
    summary: Optional[str]
    content_text: str
    publish_time: Optional[datetime]
    author_names: List[str] = field(default_factory=list)
    category_names: List[str] = field(default_factory=list)
    main_image_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    updated_time: Optional[datetime] = None
    language: str = "vi"


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def clean_text_list(values: Iterable[str | None]) -> List[str]:
    result: List[str] = []
    for item in values:
        cleaned = clean_text(item)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def get_meta_content(soup: BeautifulSoup, attr_name: str, attr_value: str) -> Optional[str]:
    tag = soup.find("meta", attrs={attr_name: attr_value})
    if tag and tag.get("content"):
        return clean_text(tag["content"])
    return None


def parse_datetime(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None


def join_url(base_url: str, href: str | None) -> Optional[str]:
    if not href:
        return None
    return urljoin(base_url, href)


def extract_json_ld_candidates(soup: BeautifulSoup) -> List[Any]:
    items: List[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.text
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            items.extend(data)
        else:
            items.append(data)
    return items


def find_news_article_json_ld(soup: BeautifulSoup) -> Optional[dict[str, Any]]:
    candidates = extract_json_ld_candidates(soup)
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("@type") in {"NewsArticle", "Article"}:
            return candidate
        graph = candidate.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict) and item.get("@type") in {"NewsArticle", "Article"}:
                    return item
    return None


def extract_breadcrumb_names(soup: BeautifulSoup) -> List[str]:
    names: List[str] = []
    candidates = extract_json_ld_candidates(soup)
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("@type") != "BreadcrumbList":
            continue
        elements = candidate.get("itemListElement", [])
        if not isinstance(elements, list):
            continue
        for element in elements:
            if not isinstance(element, dict):
                continue
            item = element.get("item", {})
            if isinstance(item, dict):
                name = clean_text(item.get("name"))
                if name and name.lower() != "trang chá»§" and name not in names:
                    names.append(name)
    return names


def to_parsed_article_payload(article: ParsedArticle) -> ParsedArticlePayload:
    return ParsedArticlePayload(
        source_name=article.source_name,
        article_url=article.article_url,
        canonical_url=article.canonical_url,
        title=article.title,
        summary=article.summary,
        content_text=article.content_text,
        publish_time=article.publish_time,
        updated_time=article.updated_time,
        author_names=list(article.author_names),
        category_names=list(article.category_names),
        main_image_url=article.main_image_url,
        tags=list(article.tags),
        language=article.language,
    )


def to_parsed_article(article: ParsedArticlePayload) -> ParsedArticle:
    return ParsedArticle(
        source_name=article.source_name,
        article_url=article.article_url,
        canonical_url=article.canonical_url,
        title=article.title,
        summary=article.summary,
        content_text=article.content_text,
        publish_time=article.publish_time,
        updated_time=article.updated_time,
        author_names=list(article.author_names),
        category_names=list(article.category_names),
        main_image_url=article.main_image_url,
        tags=list(article.tags),
        language=article.language,
    )


__all__ = [
    "ParsedArticle",
    "clean_text",
    "clean_text_list",
    "extract_breadcrumb_names",
    "find_news_article_json_ld",
    "get_meta_content",
    "join_url",
    "parse_datetime",
    "to_parsed_article_payload",
    "to_parsed_article",
]
