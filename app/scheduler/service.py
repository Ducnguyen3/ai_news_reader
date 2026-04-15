from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import CrawlJob
from app.db.session import get_db_session
from app.ingestion.service import IngestionService
from app.repositories.article_repository import ArticleRepository
from app.utils.helpers import now_local
from app.utils.logger import get_logger


SessionFactory = Callable[[], AbstractContextManager[Session]]


@dataclass(frozen=True)
class SchedulerRunResult:
    source_name: str
    crawl_job_id: int
    status: str
    total_found: int
    total_selected: int
    total_failed: int


class SchedulerService:
    def __init__(
        self,
        session_factory: SessionFactory = get_db_session,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings or get_settings()
        self.logger = get_logger(self.__class__.__name__)

    def run_scheduler(self) -> None:
        scheduler = BlockingScheduler(timezone=ZoneInfo(self.settings.timezone))
        scheduler.add_job(
            self.run_all_sources,
            CronTrigger(
                hour=self.settings.scheduler_hour,
                minute=self.settings.scheduler_minute,
                timezone=self.settings.timezone,
            ),
            id="daily_news_ingestion",
            replace_existing=True,
        )
        self.logger.info(
            "scheduler started for ingestion at %02d:%02d (%s)",
            self.settings.scheduler_hour,
            self.settings.scheduler_minute,
            self.settings.timezone,
        )
        scheduler.start()

    def run_all_sources(self) -> list[SchedulerRunResult]:
        results: list[SchedulerRunResult] = []
        for source_name in self.settings.enabled_sources:
            results.append(self.run_single_source(source_name))
        return results

    def run_single_source(self, source_name: str) -> SchedulerRunResult:
        normalized_source = source_name.strip().lower()
        with self.session_factory() as session:
            ingestion_service = IngestionService(session)
            source = self._ensure_source(session, normalized_source)

            started_at = now_local()
            crawl_job = CrawlJob(
                source_id=source.id,
                status="running",
                started_at=started_at,
            )
            session.add(crawl_job)
            session.flush()

            try:
                ingestion_result = ingestion_service.ingest_source(normalized_source)

                crawl_job.status = "success"
                crawl_job.total_found = ingestion_result.total_found
                crawl_job.total_inserted = 0
                crawl_job.total_failed = ingestion_result.total_failed
                crawl_job.finished_at = now_local()
                session.flush()

                self.logger.info(
                    "[%s] crawl_job=%s found=%s selected=%s duplicates=%s failed=%s",
                    normalized_source,
                    crawl_job.id,
                    ingestion_result.total_found,
                    ingestion_result.total_selected,
                    ingestion_result.total_duplicates,
                    ingestion_result.total_failed,
                )

                return SchedulerRunResult(
                    source_name=normalized_source,
                    crawl_job_id=crawl_job.id,
                    status=crawl_job.status,
                    total_found=ingestion_result.total_found,
                    total_selected=ingestion_result.total_selected,
                    total_failed=ingestion_result.total_failed,
                )
            except Exception as exc:
                crawl_job.status = "failed"
                crawl_job.total_found = 0
                crawl_job.total_inserted = 0
                crawl_job.total_failed = 1
                crawl_job.error_message = str(exc)
                crawl_job.finished_at = now_local()
                session.flush()

                self.logger.exception(
                    "[%s] crawl_job=%s failed: %s",
                    normalized_source,
                    crawl_job.id,
                    exc,
                )
                raise

    def _ensure_source(self, session: Session, source_name: str):
        crawler_cls = IngestionService.crawler_registry.get(source_name)
        if crawler_cls is None:
            raise ValueError(f"Unsupported source: {source_name}")

        return ArticleRepository(session).get_or_create_source(
            crawler_cls.source_name,
            crawler_cls.domain,
        )

    # TODO: Hand off IngestionResult to repository-based persistence once the
    # shared data access layer is in place. At that point total_inserted should
    # reflect actual article/raw_page writes instead of remaining 0.
    # TODO: Add an execution backend abstraction so this scheduler can trigger
    # Databricks Jobs or another remote orchestrator without changing callers.
