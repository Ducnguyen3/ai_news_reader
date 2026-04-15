from __future__ import annotations

import argparse
import sys
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.ai.jobs import AIEnrichmentJob
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


def run_ai_pending(limit: int) -> None:
    with get_db_session() as session:
        results = AIEnrichmentJob(session).run_ai_enrichment_for_pending_articles(limit=limit)
    get_logger(__name__).info("ai_enrichment_processed=%s", len(results))


def run_ai_article(article_id: int) -> None:
    with get_db_session() as session:
        result = AIEnrichmentJob(session).run_ai_enrichment_for_article(article_id)
    if result is None:
        get_logger(__name__).warning("article_id=%s not found", article_id)
        return
    get_logger(__name__).info("ai_enrichment_processed_article=%s", article_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-source news crawler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("crawl_all", help="Crawl all enabled sources")

    source_parser = subparsers.add_parser("crawl_source", help="Crawl one source")
    source_parser.add_argument("--source", required=True, help="Source name, e.g. vnexpress")

    subparsers.add_parser("run_scheduler", help="Start daily APScheduler job")

    ai_pending_parser = subparsers.add_parser("run_ai_pending", help="Run AI enrichment for pending articles")
    ai_pending_parser.add_argument("--limit", type=int, default=100, help="Max pending articles to process")

    ai_article_parser = subparsers.add_parser("run_ai_article", help="Run AI enrichment for one article")
    ai_article_parser.add_argument("--article-id", type=int, required=True, help="Article id to process")
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
    if args.command == "run_ai_pending":
        run_ai_pending(args.limit)
        return 0
    if args.command == "run_ai_article":
        run_ai_article(args.article_id)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
