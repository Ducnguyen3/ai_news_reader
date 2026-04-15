from __future__ import annotations

from dataclasses import dataclass

from app.ai.prompts import SUMMARY_PROMPT_VERSION, build_summary_prompt
from app.ai.types import AIArticleInput, AIProvider


@dataclass(frozen=True)
class SummaryResult:
    short_summary: str
    long_summary: str
    model_name: str


class ArticleSummarizer:
    def summarize_article(self, article: AIArticleInput) -> SummaryResult:
        base_summary = article.summary or article.content_text[:280].strip()
        short_summary = self._limit_text(base_summary or article.title, 160)
        long_summary = self._limit_text(
            f"{article.title}. {article.summary or article.content_text}",
            500,
        )
        return SummaryResult(
            short_summary=short_summary,
            long_summary=long_summary,
            model_name="stub-summarizer-v1",
        )

    def _limit_text(self, value: str, max_length: int) -> str:
        cleaned = " ".join(value.split()).strip()
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[: max_length - 3].rstrip() + "..."

    # TODO: Replace stub summarization with a real model-backed summarizer.
    # TODO: Add summarization style options such as headline, concise, and analyst modes.


@dataclass(frozen=True)
class SummaryResult:
    summary_text: str | None
    summary_type: str
    model_name: str
    model_version: str
    prompt_version: str
    status: str = "completed"
    error_message: str | None = None


class ArticleSummarizer:
    """Summarize persisted articles into a concise Vietnamese brief."""

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider
        self.model_name = "demo-summarizer"
        self.model_version = "v1"

    def summarize_article(self, article: AIArticleInput) -> SummaryResult:
        prompt = build_summary_prompt(
            title=article.title,
            summary=article.summary,
            content=self._limit_text(article.content_text, 4000),
        )
        try:
            summary_text = self.provider.summarize(prompt=prompt, article=article)
            return SummaryResult(
                summary_text=self._limit_text(summary_text, 600),
                summary_type="brief",
                model_name=self.model_name,
                model_version=self.model_version,
                prompt_version=SUMMARY_PROMPT_VERSION,
            )
        except Exception as exc:
            return SummaryResult(
                summary_text=None,
                summary_type="brief",
                model_name=self.model_name,
                model_version=self.model_version,
                prompt_version=SUMMARY_PROMPT_VERSION,
                status="failed",
                error_message=str(exc),
            )

    def _limit_text(self, value: str, max_length: int) -> str:
        cleaned = " ".join(value.split()).strip()
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[: max_length - 3].rstrip() + "..."
