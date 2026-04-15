from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Article, ArticleCategory, Category, CrawlDailySummary, CrawlJob, Source


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_daily_summary(self, source_id: int, crawl_date: date) -> CrawlDailySummary | None:
        stmt = select(CrawlDailySummary).where(
            CrawlDailySummary.source_id == source_id,
            CrawlDailySummary.crawl_date == crawl_date,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create_daily_summary(self, source_id: int, crawl_date: date) -> CrawlDailySummary:
        summary = self.get_daily_summary(source_id, crawl_date)
        if summary is not None:
            return summary

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
        return summary

    def mark_daily_summary_started(
        self,
        *,
        source_id: int,
        crawl_job_id: int,
        started_at: datetime,
    ) -> CrawlDailySummary:
        summary = self.get_or_create_daily_summary(source_id, started_at.date())
        summary.run_count += 1
        summary.latest_crawl_job_id = crawl_job_id
        summary.latest_started_at = started_at
        summary.last_status = "running"
        summary.last_error_message = None
        self.session.flush()
        return summary

    def mark_daily_summary_finished(
        self,
        *,
        daily_summary: CrawlDailySummary,
        crawl_job_id: int,
        finished_at: datetime,
        status: str,
        total_found: int,
        total_inserted: int,
        total_failed: int,
        error_message: str | None,
    ) -> CrawlDailySummary:
        daily_summary.latest_crawl_job_id = crawl_job_id
        daily_summary.latest_finished_at = finished_at
        daily_summary.last_status = status
        daily_summary.total_found += total_found
        daily_summary.total_inserted += total_inserted
        daily_summary.total_failed += total_failed
        daily_summary.last_error_message = error_message
        self.session.flush()
        return daily_summary

    def get_latest_job_status_rows(self) -> list[tuple[int, str, str, datetime | None, int, int, int]]:
        latest_started_at_subquery = (
            select(
                CrawlJob.source_id.label("source_id"),
                func.max(CrawlJob.started_at).label("latest_started_at"),
            )
            .group_by(CrawlJob.source_id)
            .subquery()
        )

        stmt = (
            select(
                Source.id,
                Source.name,
                CrawlJob.status,
                CrawlJob.finished_at,
                CrawlJob.total_found,
                CrawlJob.total_inserted,
                CrawlJob.total_failed,
            )
            .join(CrawlJob, CrawlJob.source_id == Source.id)
            .join(
                latest_started_at_subquery,
                (latest_started_at_subquery.c.source_id == CrawlJob.source_id)
                & (latest_started_at_subquery.c.latest_started_at == CrawlJob.started_at),
            )
            .order_by(Source.name.asc())
        )
        return list(self.session.execute(stmt).all())

    def get_article_counts_by_source_rows(
        self,
        date_from: date,
        date_to: date,
    ) -> list[tuple[int, str, int]]:
        stmt = (
            select(
                Source.id,
                Source.name,
                func.count(Article.id),
            )
            .join(Article, Article.source_id == Source.id)
            .where(
                Article.scraped_time >= self._at_day_start(date_from),
                Article.scraped_time < self._at_next_day_start(date_to),
            )
            .group_by(Source.id, Source.name)
            .order_by(Source.name.asc())
        )
        return list(self.session.execute(stmt).all())

    def get_article_counts_by_day_rows(
        self,
        date_from: date,
        date_to: date,
    ) -> list[tuple[date, int]]:
        day_expr = func.date(Article.scraped_time)
        stmt = (
            select(
                day_expr.label("article_day"),
                func.count(Article.id),
            )
            .where(
                Article.scraped_time >= self._at_day_start(date_from),
                Article.scraped_time < self._at_next_day_start(date_to),
            )
            .group_by(day_expr)
            .order_by(day_expr.asc())
        )
        return list(self.session.execute(stmt).all())

    def get_top_categories_rows(self, limit: int) -> list[tuple[int, str, int]]:
        stmt = (
            select(
                Category.id,
                Category.name,
                func.count(ArticleCategory.article_id),
            )
            .join(ArticleCategory, ArticleCategory.category_id == Category.id)
            .group_by(Category.id, Category.name)
            .order_by(func.count(ArticleCategory.article_id).desc(), Category.name.asc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).all())

    def _at_day_start(self, value: date) -> datetime:
        return datetime.combine(value, time.min)

    def _at_next_day_start(self, value: date) -> datetime:
        return datetime.combine(value + timedelta(days=1), time.min)

    # TODO: If timezone-aware day bucketing becomes important for analytics,
    # replace current date-range filtering with explicit timezone conversion
    # aligned to APP_TIMEZONE or a caller-provided timezone.
