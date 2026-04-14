from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    log_level: str
    timezone: str
    database_url: str
    scheduler_hour: int
    scheduler_minute: int
    crawl_timeout_seconds: int
    crawl_retry_count: int
    crawl_request_delay_seconds: float
    crawl_category_pages: int
    user_agent: str
    enabled_sources: List[str]
    parser_version: str
    article_status_default: str
    save_raw_html: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    enabled_sources = os.getenv(
        "ENABLED_SOURCES",
        "vnexpress,cafef,genk,diendandoanhnghiep",
    )
    return Settings(
        app_name=os.getenv("APP_NAME", "multi-source-news-crawler"),
        app_env=os.getenv("APP_ENV", "local"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        timezone=os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/news_crawler",
        ),
        scheduler_hour=_as_int(os.getenv("SCHEDULER_HOUR"), 7),
        scheduler_minute=_as_int(os.getenv("SCHEDULER_MINUTE"), 0),
        crawl_timeout_seconds=_as_int(os.getenv("CRAWL_TIMEOUT_SECONDS"), 20),
        crawl_retry_count=_as_int(os.getenv("CRAWL_RETRY_COUNT"), 3),
        crawl_request_delay_seconds=float(os.getenv("CRAWL_REQUEST_DELAY_SECONDS", "0.3")),
        crawl_category_pages=_as_int(os.getenv("CRAWL_CATEGORY_PAGES"), 10),
        user_agent=os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36 NewsCrawler/1.0",
        ),
        enabled_sources=[
            item.strip().lower()
            for item in enabled_sources.split(",")
            if item.strip()
        ],
        parser_version=os.getenv("PARSER_VERSION", "1.0.0"),
        article_status_default=os.getenv("ARTICLE_STATUS_DEFAULT", "published"),
        save_raw_html=_as_bool(os.getenv("SAVE_RAW_HTML"), True),
    )
