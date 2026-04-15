from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CrawlJob
from app.utils.helpers import now_local


class CrawlJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, crawl_job_id: int) -> CrawlJob | None:
        return self.session.get(CrawlJob, crawl_job_id)

    def create_job(
        self,
        *,
        source_id: int,
        status: str = "running",
        started_at: datetime | None = None,
    ) -> CrawlJob:
        crawl_job = CrawlJob(
            source_id=source_id,
            status=status,
            started_at=started_at or now_local(),
        )
        self.session.add(crawl_job)
        self.session.flush()
        return crawl_job

    def update_job_status(
        self,
        *,
        crawl_job: CrawlJob,
        status: str,
        total_found: int,
        total_inserted: int,
        total_failed: int,
        finished_at: datetime | None = None,
        error_message: str | None = None,
    ) -> CrawlJob:
        crawl_job.status = status
        crawl_job.total_found = total_found
        crawl_job.total_inserted = total_inserted
        crawl_job.total_failed = total_failed
        crawl_job.finished_at = finished_at or now_local()
        crawl_job.error_message = error_message
        self.session.flush()
        return crawl_job

    def get_latest_by_source(self, source_id: int) -> CrawlJob | None:
        stmt = (
            select(CrawlJob)
            .where(CrawlJob.source_id == source_id)
            .order_by(CrawlJob.started_at.desc(), CrawlJob.id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_source(self, source_id: int, limit: int = 20) -> list[CrawlJob]:
        stmt = (
            select(CrawlJob)
            .where(CrawlJob.source_id == source_id)
            .order_by(CrawlJob.started_at.desc(), CrawlJob.id.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    # TODO: If remote execution is added later, extend this repository with
    # external job identifiers such as Databricks run ids without changing callers.
