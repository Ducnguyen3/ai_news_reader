from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.cafef_crawler import CafeFCrawler
from app.crawlers.diendandoanhnghiep_crawler import DienDanDoanhNghiepCrawler
from app.crawlers.genk_crawler import GenkCrawler
from app.crawlers.vnexpress_crawler import VnExpressCrawler
from app.db.models import CrawlDailySummary, CrawlJob
from app.services.dedup_service import DedupService
from app.utils.helpers import now_local
from app.utils.logger import get_logger


@dataclass
class CrawlSummary:
    source_name: str
    total_found: int
    total_inserted: int
    total_failed: int


class CrawlService:
    crawler_registry: Dict[str, Type[BaseCrawler]] = {
        "vnexpress": VnExpressCrawler,
        "cafef": CafeFCrawler,
        "genk": GenkCrawler,
        "diendandoanhnghiep": DienDanDoanhNghiepCrawler,
    }

    def __init__(self, session: Session) -> None:
        self.session = session
        self.logger = get_logger(self.__class__.__name__)
        self.dedup_service = DedupService(session)

    def crawl_all(self, source_names: Iterable[str]) -> list[CrawlSummary]:
        summaries: list[CrawlSummary] = []
        for source_name in source_names:
            summaries.append(self.crawl_source(source_name))
        return summaries

    def crawl_source(self, source_name: str) -> CrawlSummary:
        crawler_cls = self.crawler_registry.get(source_name.lower())
        if crawler_cls is None:
            raise ValueError(f"Unsupported source: {source_name}")

        crawler = crawler_cls(self.session)
        source = crawler.ensure_source()
        started_at = now_local()
        crawl_job = CrawlJob(source_id=source.id, status="running", started_at=started_at)
        self.session.add(crawl_job)
        self.session.flush()
        daily_summary = self._start_daily_summary(
            source_id=source.id,
            crawl_job_id=crawl_job.id,
            started_at=started_at,
        )

        total_found = 0
        total_inserted = 0
        total_failed = 0

        try:
            homepage = crawler.fetch_homepage()
            category_pages = crawler.fetch_category_pages()
            page_html_list = [homepage.html, *(page.html for page in category_pages)]
            article_links = crawler.extract_article_links_from_multiple_pages(page_html_list)
            total_found = len(article_links)
            new_article_links = self.dedup_service.filter_new_urls(article_links)
            skipped_existing = total_found - len(new_article_links)
            self.logger.info(
                "[%s] found=%s new=%s skipped_existing=%s",
                source_name,
                total_found,
                len(new_article_links),
                skipped_existing,
            )

            for url in new_article_links:
                try:
                    article_response = crawler.fetch_article(url)
                    parsed_article = crawler.parse_article(article_response.html, url)
                    if not parsed_article.title or not parsed_article.content_text:
                        self.logger.warning("[%s] skipped invalid article %s", source_name, url)
                        total_failed += 1
                        continue

                    raw_page = crawler.save_raw_page(
                        source=source,
                        crawl_job=crawl_job,
                        url=url,
                        page_type="article",
                        http_status=article_response.status_code,
                        html_content=article_response.html,
                        canonical_url=parsed_article.canonical_url,
                    )
                    article = crawler.save_article(
                        source=source,
                        raw_page=raw_page,
                        parsed_article=parsed_article,
                    )
                    if article is not None:
                        total_inserted += 1
                except Exception as exc:
                    total_failed += 1
                    self.logger.exception("[%s] failed processing article %s: %s", source_name, url, exc)

            finished_at = now_local()
            crawl_job.status = "success"
            crawl_job.total_found = total_found
            crawl_job.total_inserted = total_inserted
            crawl_job.total_failed = total_failed
            crawl_job.finished_at = finished_at
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
            self.session.flush()
            self.logger.info("[%s] inserted=%s failed=%s", source_name, total_inserted, total_failed)
            return CrawlSummary(source_name, total_found, total_inserted, total_failed)
        except Exception as exc:
            finished_at = now_local()
            crawl_job.status = "failed"
            crawl_job.total_found = total_found
            crawl_job.total_inserted = total_inserted
            crawl_job.total_failed = total_failed + 1
            crawl_job.error_message = str(exc)
            crawl_job.finished_at = finished_at
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
            self.session.flush()
            self.logger.exception("[%s] crawl job failed: %s", source_name, exc)
            raise
        finally:
            crawler.close()

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
