from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository


@dataclass(frozen=True)
class DailyCrawlSummaryView:
    source_id: int
    crawl_date: date
    run_count: int
    last_status: str
    total_found: int
    total_inserted: int
    total_failed: int
    latest_started_at: datetime | None
    latest_finished_at: datetime | None
    latest_crawl_job_id: int | None
    last_error_message: str | None


@dataclass(frozen=True)
class LatestJobStatusView:
    source_id: int
    source_name: str
    status: str
    finished_at: datetime | None
    total_found: int
    total_inserted: int
    total_failed: int


@dataclass(frozen=True)
class ArticleCountBySourceView:
    source_id: int
    source_name: str
    article_count: int


@dataclass(frozen=True)
class ArticleCountByDayView:
    article_day: date
    article_count: int


@dataclass(frozen=True)
class TopCategoryView:
    category_id: int
    category_name: str
    article_count: int


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AnalyticsRepository(session)

    def summarize_daily_crawl(self, source_id: int, crawl_date: date) -> DailyCrawlSummaryView | None:
        summary = self.repository.get_daily_summary(source_id, crawl_date)
        if summary is None:
            return None

        return DailyCrawlSummaryView(
            source_id=summary.source_id,
            crawl_date=summary.crawl_date,
            run_count=summary.run_count,
            last_status=summary.last_status,
            total_found=summary.total_found,
            total_inserted=summary.total_inserted,
            total_failed=summary.total_failed,
            latest_started_at=summary.latest_started_at,
            latest_finished_at=summary.latest_finished_at,
            latest_crawl_job_id=summary.latest_crawl_job_id,
            last_error_message=summary.last_error_message,
        )

    def get_latest_job_status_by_source(self) -> list[LatestJobStatusView]:
        rows = self.repository.get_latest_job_status_rows()
        return [
            LatestJobStatusView(
                source_id=source_id,
                source_name=source_name,
                status=status,
                finished_at=finished_at,
                total_found=total_found,
                total_inserted=total_inserted,
                total_failed=total_failed,
            )
            for source_id, source_name, status, finished_at, total_found, total_inserted, total_failed in rows
        ]

    def get_article_counts_by_source(
        self,
        date_from: date,
        date_to: date,
    ) -> list[ArticleCountBySourceView]:
        rows = self.repository.get_article_counts_by_source_rows(date_from, date_to)
        return [
            ArticleCountBySourceView(
                source_id=source_id,
                source_name=source_name,
                article_count=article_count,
            )
            for source_id, source_name, article_count in rows
        ]

    def get_article_counts_by_day(
        self,
        date_from: date,
        date_to: date,
    ) -> list[ArticleCountByDayView]:
        rows = self.repository.get_article_counts_by_day_rows(date_from, date_to)
        return [
            ArticleCountByDayView(
                article_day=article_day,
                article_count=article_count,
            )
            for article_day, article_count in rows
        ]

    def get_top_categories(self, limit: int = 10) -> list[TopCategoryView]:
        rows = self.repository.get_top_categories_rows(limit)
        return [
            TopCategoryView(
                category_id=category_id,
                category_name=category_name,
                article_count=article_count,
            )
            for category_id, category_name, article_count in rows
        ]

    # TODO: Add richer analytic views for article trends by category/source/time
    # once reporting requirements are fixed for dashboard or Databricks notebooks.
    # TODO: If needed later, add optional DataFrame export helpers in a separate
    # adapter module instead of mixing notebook concerns into this service.
