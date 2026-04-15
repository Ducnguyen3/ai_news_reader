from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import CrawlDailySummary, Source
from app.ingestion.parsers.common import to_parsed_article
from app.ingestion.service import IngestionResult, IngestionService
from app.repositories.article_repository import ArticleRepository
from app.repositories.crawl_job_repository import CrawlJobRepository
from app.repositories.raw_page_repository import RawPageRepository
from app.utils.helpers import normalize_whitespace, now_local, sha256_text
from app.utils.logger import get_logger


@dataclass
class CrawlSummary:
    source_name: str
    total_found: int
    total_inserted: int
    total_failed: int
    article_ids: list[int]


class CrawlService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.logger = get_logger(self.__class__.__name__)
        self.ingestion_service = IngestionService(session)
        self.article_repository = ArticleRepository(session)
        self.raw_page_repository = RawPageRepository(session)
        self.crawl_job_repository = CrawlJobRepository(session)

    def crawl_all(self, source_names: Iterable[str]) -> list[CrawlSummary]:
        summaries: list[CrawlSummary] = []
        for source_name in source_names:
            summaries.append(self.crawl_source(source_name))
        return summaries

    def crawl_source(self, source_name: str) -> CrawlSummary:
        normalized_source = source_name.strip().lower()
        crawler_cls = IngestionService.crawler_registry.get(normalized_source)
        if crawler_cls is None:
            raise ValueError(f"Unsupported source: {source_name}")

        source = self.article_repository.get_or_create_source(crawler_cls.source_name, crawler_cls.domain)
        started_at = now_local()
        crawl_job = self.crawl_job_repository.create_job(
            source_id=source.id,
            status="running",
            started_at=started_at,
        )
        daily_summary = self._start_daily_summary(
            source_id=source.id,
            crawl_job_id=crawl_job.id,
            started_at=started_at,
        )

        total_found = 0
        total_inserted = 0
        total_failed = 0

        try:
            ingestion_result = self.ingestion_service.ingest_source(normalized_source)
            total_found = ingestion_result.total_found
            total_inserted, persistence_failed, article_ids = self._persist_ingestion_result(
                source=source,
                crawl_job_id=crawl_job.id,
                ingestion_result=ingestion_result,
            )
            total_failed = ingestion_result.total_failed + persistence_failed

            self.logger.info(
                "[%s] found=%s selected=%s duplicates=%s inserted=%s failed=%s",
                normalized_source,
                ingestion_result.total_found,
                ingestion_result.total_selected,
                ingestion_result.total_duplicates,
                total_inserted,
                total_failed,
            )

            finished_at = now_local()
            self.crawl_job_repository.update_job_status(
                crawl_job=crawl_job,
                status="success",
                total_found=total_found,
                total_inserted=total_inserted,
                total_failed=total_failed,
                finished_at=finished_at,
                error_message=None,
            )
            self._finish_daily_summary(
                daily_summary=daily_summary,
                crawl_job_id=crawl_job.id,
                finished_at=finished_at,
                status="success",
                total_found=total_found,
                total_inserted=total_inserted,
                total_failed=total_failed,
                error_message=None,
            )
            self.logger.info("[%s] inserted=%s failed=%s", normalized_source, total_inserted, total_failed)
            return CrawlSummary(normalized_source, total_found, total_inserted, total_failed, article_ids)
        except Exception as exc:
            finished_at = now_local()
            self.crawl_job_repository.update_job_status(
                crawl_job=crawl_job,
                status="failed",
                total_found=total_found,
                total_inserted=total_inserted,
                total_failed=total_failed + 1,
                finished_at=finished_at,
                error_message=str(exc),
            )
            self._finish_daily_summary(
                daily_summary=daily_summary,
                crawl_job_id=crawl_job.id,
                finished_at=finished_at,
                status="failed",
                total_found=total_found,
                total_inserted=total_inserted,
                total_failed=total_failed + 1,
                error_message=str(exc),
            )
            self.logger.exception("[%s] crawl job failed: %s", normalized_source, exc)
            raise

    def _persist_ingestion_result(
        self,
        *,
        source: Source,
        crawl_job_id: int,
        ingestion_result: IngestionResult,
    ) -> tuple[int, int, list[int]]:
        total_inserted = 0
        total_failed = 0
        article_ids: list[int] = []

        for record in ingestion_result.records:
            try:
                raw_page = self.raw_page_repository.create_raw_page(
                    source_id=source.id,
                    crawl_job_id=crawl_job_id,
                    url=record.raw_page.url,
                    url_hash=sha256_text(record.raw_page.url.strip().lower()),
                    page_type=record.raw_page.page_type,
                    http_status=record.raw_page.http_status,
                    html_content=record.raw_page.html_content,
                    text_content=normalize_whitespace(
                        BeautifulSoup(record.raw_page.html_content or "", "lxml").get_text(" ")
                    ),
                    canonical_url=record.raw_page.canonical_url,
                    checksum=sha256_text(record.raw_page.html_content or ""),
                    parser_version=self.settings.parser_version,
                )

                parsed_article = to_parsed_article(record.parsed_article)
                canonical_url = parsed_article.canonical_url or parsed_article.article_url
                url_hash = sha256_text(canonical_url.strip().lower())
                content_hash = sha256_text(
                    f"{normalize_whitespace(parsed_article.title)}|{normalize_whitespace(parsed_article.content_text)}".lower()
                )

                if self.article_repository.get_article_by_url_hash(url_hash) is not None:
                    continue
                if self.article_repository.get_article_by_content_hash(content_hash) is not None:
                    continue

                article = self.article_repository.create_article(
                    source=source,
                    raw_page=raw_page,
                    parsed_article=parsed_article,
                    url_hash=url_hash,
                    content_hash=content_hash,
                )
                self.article_repository.attach_categories(article, source.id, parsed_article.category_names)
                self.article_repository.attach_authors(article, parsed_article.author_names)
                total_inserted += 1
                article_ids.append(article.id)
            except Exception as exc:
                total_failed += 1
                self.logger.exception(
                    "[%s] failed persisting article %s: %s",
                    ingestion_result.source_name,
                    record.parsed_article.article_url,
                    exc,
                )

        return total_inserted, total_failed, article_ids

    def _start_daily_summary(
        self,
        *,
        source_id: int,
        crawl_job_id: int,
        started_at,
    ) -> CrawlDailySummary:
        crawl_date = started_at.date()
        stmt = select(CrawlDailySummary).where(
            CrawlDailySummary.source_id == source_id,
            CrawlDailySummary.crawl_date == crawl_date,
        )
        summary = self.session.execute(stmt).scalar_one_or_none()
        if summary is None:
            summary = CrawlDailySummary(
                source_id=source_id,
                crawl_date=crawl_date,
                run_count=0,
                total_found=0,
                total_inserted=0,
                total_failed=0,
            )
            self.session.add(summary)
            self.session.flush()

        summary.run_count += 1
        summary.latest_crawl_job_id = crawl_job_id
        summary.latest_started_at = started_at
        summary.last_status = "running"
        summary.last_error_message = None
        return summary

    def _finish_daily_summary(
        self,
        *,
        daily_summary: CrawlDailySummary,
        crawl_job_id: int,
        finished_at,
        status: str,
        total_found: int,
        total_inserted: int,
        total_failed: int,
        error_message: str | None,
    ) -> None:
        daily_summary.latest_crawl_job_id = crawl_job_id
        daily_summary.latest_finished_at = finished_at
        daily_summary.last_status = status
        daily_summary.total_found += total_found
        daily_summary.total_inserted += total_inserted
        daily_summary.total_failed += total_failed
        daily_summary.last_error_message = error_message
