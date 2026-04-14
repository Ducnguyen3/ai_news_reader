from __future__ import annotations

import argparse
import sys
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.db.session import get_db_session
from app.services.crawl_service import CrawlService
from app.utils.logger import configure_logging, get_logger


def run_crawl_all() -> None:
    settings = get_settings()
    with get_db_session() as session:
        summaries = CrawlService(session).crawl_all(settings.enabled_sources)
    logger = get_logger(__name__)
    for summary in summaries:
        logger.info(
            "source=%s found=%s inserted=%s failed=%s",
            summary.source_name,
            summary.total_found,
            summary.total_inserted,
            summary.total_failed,
        )


def run_crawl_source(source_name: str) -> None:
    with get_db_session() as session:
        summary = CrawlService(session).crawl_source(source_name)
    get_logger(__name__).info(
        "source=%s found=%s inserted=%s failed=%s",
        summary.source_name,
        summary.total_found,
        summary.total_inserted,
        summary.total_failed,
    )


def run_scheduler() -> None:
    settings = get_settings()
    logger = get_logger(__name__)
    scheduler = BlockingScheduler(timezone=ZoneInfo(settings.timezone))
    scheduler.add_job(
        run_crawl_all,
        CronTrigger(hour=settings.scheduler_hour, minute=settings.scheduler_minute, timezone=settings.timezone),
        id="daily_news_crawl",
        replace_existing=True,
    )
    logger.info(
        "scheduler started for daily crawl at %02d:%02d (%s)",
        settings.scheduler_hour,
        settings.scheduler_minute,
        settings.timezone,
    )
    scheduler.start()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-source news crawler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("crawl_all", help="Crawl all enabled sources")

    source_parser = subparsers.add_parser("crawl_source", help="Crawl one source")
    source_parser.add_argument("--source", required=True, help="Source name, e.g. vnexpress")

    subparsers.add_parser("run_scheduler", help="Start daily APScheduler job")
    return parser


def main() -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "crawl_all":
        run_crawl_all()
        return 0
    if args.command == "crawl_source":
        run_crawl_source(args.source)
        return 0
    if args.command == "run_scheduler":
        run_scheduler()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
