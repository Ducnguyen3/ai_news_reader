from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Type

from sqlalchemy.orm import Session

from app.ingestion.contracts import (
    DedupDecision,
    IngestionArticleRecord,
    IngestionResult,
    ParsedArticlePayload,
    RawPagePayload,
)
from app.ingestion.crawlers.base_crawler import BaseCrawler
from app.ingestion.crawlers.cafef_crawler import CafeFCrawler
from app.ingestion.crawlers.diendandoanhnghiep_crawler import DienDanDoanhNghiepCrawler
from app.ingestion.crawlers.genk_crawler import GenkCrawler
from app.ingestion.crawlers.vnexpress_crawler import VnExpressCrawler
from app.ingestion.dedup.service import IngestionDedupService
from app.ingestion.parsers.common import to_parsed_article_payload
from app.utils.logger import get_logger


@dataclass(frozen=True)
class IngestionSelection:
    raw_page: RawPagePayload
    parsed_article: ParsedArticlePayload
    dedup_decision: DedupDecision


class IngestionService:
    crawler_registry: Dict[str, Type[BaseCrawler]] = {
        "vnexpress": VnExpressCrawler,
        "cafef": CafeFCrawler,
        "genk": GenkCrawler,
        "diendandoanhnghiep": DienDanDoanhNghiepCrawler,
    }

    def __init__(self, session: Session) -> None:
        self.session = session
        self.logger = get_logger(self.__class__.__name__)
        self.dedup_service = IngestionDedupService(session)

    def ingest_source(self, source_name: str) -> IngestionResult:
        crawler_cls = self.crawler_registry.get(source_name.lower())
        if crawler_cls is None:
            raise ValueError(f"Unsupported source: {source_name}")

        crawler = crawler_cls(self.session)
        records: list[IngestionArticleRecord] = []
        total_found = 0
        total_failed = 0
        total_duplicates = 0

        try:
            homepage = crawler.fetch_homepage()
            category_pages = crawler.fetch_category_pages()
            page_html_list = [homepage.html, *(page.html for page in category_pages)]
            article_links = crawler.extract_article_links_from_multiple_pages(page_html_list)
            total_found = len(article_links)

            for url in article_links:
                try:
                    article_response = crawler.fetch_article(url)
                    raw_page = RawPagePayload(
                        source_name=source_name.lower(),
                        url=url,
                        page_type="article",
                        http_status=article_response.status_code,
                        html_content=article_response.html,
                    )

                    parsed_article = to_parsed_article_payload(
                        crawler.parse_article(article_response.html, url)
                    )
                    dedup_decision = self.dedup_service.evaluate_article(parsed_article)

                    if dedup_decision.is_duplicate:
                        total_duplicates += 1
                        continue

                    records.append(
                        IngestionArticleRecord(
                            raw_page=RawPagePayload(
                                source_name=raw_page.source_name,
                                url=raw_page.url,
                                page_type=raw_page.page_type,
                                http_status=raw_page.http_status,
                                html_content=raw_page.html_content,
                                canonical_url=parsed_article.canonical_url,
                            ),
                            parsed_article=parsed_article,
                            dedup_decision=dedup_decision,
                        )
                    )
                except Exception as exc:
                    total_failed += 1
                    self.logger.exception("[%s] failed during ingestion for %s: %s", source_name, url, exc)

            return IngestionResult(
                source_name=source_name.lower(),
                total_found=total_found,
                total_selected=len(records),
                total_duplicates=total_duplicates,
                total_failed=total_failed,
                records=records,
            )
        finally:
            crawler.close()

    def ingest_many(self, source_names: Iterable[str]) -> list[IngestionResult]:
        return [self.ingest_source(source_name) for source_name in source_names]

    # TODO: Add a persistence handoff method that maps IngestionResult into repository writes.
    # TODO: Replace direct legacy crawler usage once app/ingestion/crawlers contains full implementations.
