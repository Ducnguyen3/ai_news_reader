from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import time
from typing import Iterable

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import CrawlJob, RawPage, Source
from app.parsers.common import ParsedArticle
from app.services.article_service import ArticleService
from app.utils.helpers import normalize_whitespace, sha256_text
from app.utils.logger import get_logger


@dataclass
class FetchResult:
    url: str
    status_code: int
    html: str


class BaseCrawler(ABC):
    source_name: str
    domain: str
    homepage_url: str
    parser_version: str = "1.0.0"
    category_paths: list[str] = []

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.article_service = ArticleService(session)
        self.logger = get_logger(self.__class__.__name__)
        self.client = httpx.Client(
            timeout=self.settings.crawl_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self.settings.user_agent},
        )

    @abstractmethod
    def fetch_homepage(self) -> FetchResult:
        raise NotImplementedError

    @abstractmethod
    def extract_article_links(self, homepage_html: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def parse_article(self, html: str, url: str) -> ParsedArticle:
        raise NotImplementedError

    def fetch_article(self, url: str) -> FetchResult:
        return self._request(url)

    def fetch_category_pages(self) -> list[FetchResult]:
        pages: list[FetchResult] = []
        for category_path in self.category_paths:
            consecutive_misses = 0
            for page_number in range(1, self.settings.crawl_category_pages + 1):
                page_result = self._fetch_first_available_category_page(category_path, page_number)
                if page_result is None:
                    consecutive_misses += 1
                    if page_number > 1 and consecutive_misses >= 2:
                        break
                    continue

                consecutive_misses = 0
                if not self.extract_article_links(page_result.html):
                    if page_number > 1:
                        break
                    continue
                pages.append(page_result)
        return pages

    def extract_article_links_from_multiple_pages(self, page_html_list: Iterable[str]) -> list[str]:
        links: list[str] = []
        seen_hashes: set[str] = set()
        for page_html in page_html_list:
            for link in self.extract_article_links(page_html):
                url_hash = sha256_text(link.strip().lower())
                if url_hash in seen_hashes:
                    continue
                seen_hashes.add(url_hash)
                links.append(link)
        return links

    @abstractmethod
    def build_category_page_urls(self, category_path: str, page_number: int) -> list[str]:
        raise NotImplementedError

    def _fetch_first_available_category_page(
        self,
        category_path: str,
        page_number: int,
    ) -> FetchResult | None:
        for page_url in self.build_category_page_urls(category_path, page_number):
            try:
                return self._request(page_url)
            except Exception as exc:
                self.logger.debug(
                    "Failed candidate category page %s for %s page=%s: %s",
                    page_url,
                    self.source_name,
                    page_number,
                    exc,
                )
        self.logger.warning(
            "No working pagination URL for %s category=%s page=%s",
            self.source_name,
            category_path,
            page_number,
        )
        return None

    def save_raw_page(
        self,
        *,
        source: Source,
        crawl_job: CrawlJob,
        url: str,
        page_type: str,
        http_status: int | None,
        html_content: str | None,
        canonical_url: str | None,
    ) -> RawPage:
        text_content = normalize_whitespace(BeautifulSoup(html_content or "", "lxml").get_text(" "))
        return self.article_service.save_raw_page(
            source_id=source.id,
            crawl_job_id=crawl_job.id,
            url=url,
            url_hash=sha256_text(url.strip().lower()),
            page_type=page_type,
            http_status=http_status,
            html_content=html_content,
            text_content=text_content,
            canonical_url=canonical_url,
            checksum=sha256_text(html_content or ""),
            parser_version=self.settings.parser_version,
        )

    def save_article(
        self,
        *,
        source: Source,
        raw_page: RawPage,
        parsed_article: ParsedArticle,
    ):
        return self.article_service.save_article(
            source=source,
            raw_page=raw_page,
            parsed_article=parsed_article,
        )

    def ensure_source(self) -> Source:
        return self.article_service.get_or_create_source(self.source_name, self.domain)

    def close(self) -> None:
        self.client.close()

    def normalize_links(self, links: Iterable[str | None]) -> list[str]:
        normalized: list[str] = []
        for link in links:
            if not link:
                continue
            value = link.strip()
            if value and value not in normalized and self.is_article_url(value):
                normalized.append(value)
        return normalized

    def is_article_url(self, url: str) -> bool:
        return self.domain in url and url.startswith(("http://", "https://"))

    def _request(self, url: str) -> FetchResult:
        last_error: Exception | None = None
        for attempt in range(1, self.settings.crawl_retry_count + 1):
            try:
                if self.settings.crawl_request_delay_seconds > 0:
                    time.sleep(self.settings.crawl_request_delay_seconds)
                response = self.client.get(url)
                response.raise_for_status()
                return FetchResult(url=str(response.url), status_code=response.status_code, html=response.text)
            except httpx.HTTPError as exc:
                last_error = exc
                self.logger.warning("Request failed for %s on attempt %s/%s: %s", url, attempt, self.settings.crawl_retry_count, exc)
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Could not fetch url: {url}")
