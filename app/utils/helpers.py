from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_whitespace(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def count_words(value: str | None) -> int:
    text = normalize_whitespace(value)
    if not text:
        return 0
    return len(text.split(" "))


def estimate_reading_time_minutes(word_count: int) -> int:
    if word_count <= 0:
        return 0
    return max(1, math.ceil(word_count / 220))


def now_local() -> datetime:
    settings = get_settings()
    return datetime.now(tz=ZoneInfo(settings.timezone))


def slugify(value: str) -> str:
    value = normalize_whitespace(value).lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    return re.sub(r"[-\s]+", "-", value).strip("-")
