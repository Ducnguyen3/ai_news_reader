from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import RawPage


class RawPageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()

    def get_by_id(self, raw_page_id: int) -> RawPage | None:
        return self.session.get(RawPage, raw_page_id)

    def get_by_url_hash(self, url_hash: str) -> RawPage | None:
        stmt = select(RawPage).where(RawPage.url_hash == url_hash).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_raw_page(
        self,
        *,
        source_id: int,
        crawl_job_id: int,
        url: str,
        url_hash: str,
        page_type: str,
        http_status: int | None,
        html_content: str | None,
        text_content: str | None,
        canonical_url: str | None,
        checksum: str | None,
        parser_version: str | None,
    ) -> RawPage:
        raw_page = RawPage(
            source_id=source_id,
            crawl_job_id=crawl_job_id,
            url=url,
            url_hash=url_hash,
            page_type=page_type,
            http_status=http_status,
            html_content=html_content if self.settings.save_raw_html else None,
            text_content=text_content,
            canonical_url=canonical_url,
            checksum=checksum,
            parser_version=parser_version,
        )
        self.session.add(raw_page)
        self.session.flush()
        return raw_page

    def list_by_crawl_job(self, crawl_job_id: int) -> list[RawPage]:
        stmt = (
            select(RawPage)
            .where(RawPage.crawl_job_id == crawl_job_id)
            .order_by(RawPage.id.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    # TODO: Add bulk insert helpers if ingestion later persists many raw pages
    # in batches for higher throughput.
