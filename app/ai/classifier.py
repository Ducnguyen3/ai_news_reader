from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.prompts import CLASSIFICATION_PROMPT_VERSION, build_classification_prompt
from app.ai.types import AIArticleInput, AIProvider


@dataclass(frozen=True)
class TagResult:
    tag_type: str
    tag_name: str
    confidence: float = 0.0
    is_primary: bool = False


@dataclass(frozen=True)
class ClassificationResult:
    primary_topic: str
    tags: list[TagResult] = field(default_factory=list)
    confidence: float = 0.0
    model_name: str = "demo-classifier"
    model_version: str = "v1"
    prompt_version: str = CLASSIFICATION_PROMPT_VERSION


class ArticleClassifier:
    def classify_article(self, article: AIArticleInput) -> ClassificationResult:
        normalized_text = f"{article.title} {article.content_text}".lower()
        if "ai" in normalized_text or "trí tuệ nhân tạo" in normalized_text:
            primary_topic = "artificial-intelligence"
        elif "chứng khoán" in normalized_text or "cổ phiếu" in normalized_text:
            primary_topic = "finance"
        elif "điện thoại" in normalized_text or "smartphone" in normalized_text:
            primary_topic = "consumer-tech"
        elif article.category_names:
            primary_topic = article.category_names[0]
        else:
            primary_topic = "general-news"

        inferred_tags = self._build_stub_tags(article, primary_topic)
        return ClassificationResult(
            primary_topic=primary_topic,
            tags=inferred_tags,
            confidence=0.55,
            model_name="stub-classifier-v1",
        )

    def _build_stub_tags(self, article: AIArticleInput, primary_topic: str) -> list[str]:
        tags: list[str] = []
        for value in [primary_topic, *article.category_names, *article.tag_names]:
            cleaned = value.strip().lower()
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
        return tags[:5]

    # TODO: Replace keyword-based stub logic with a proper multi-label classifier.
    # TODO: Add hierarchical topic mapping for source-specific category names.


class ArticleClassifier:
    """Classify a persisted article into one primary topic and practical tags."""

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def classify_article(self, article: AIArticleInput) -> ClassificationResult:
        prompt = build_classification_prompt(
            title=article.title,
            summary=article.summary,
            content=self._limit_text(article.content_text, 4000),
        )
        payload = self.provider.classify(prompt=prompt, article=article)
        primary_topic = str(payload.get("primary_topic") or "general-news").strip().lower()
        confidence = float(payload.get("confidence") or 0.5)

        tags: list[TagResult] = [
            TagResult(
                tag_type="topic",
                tag_name=primary_topic,
                confidence=confidence,
                is_primary=True,
            )
        ]

        seen = {primary_topic}
        for raw_tag in payload.get("tags", []):
            cleaned = str(raw_tag).strip().lower()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            tags.append(TagResult(tag_type="keyword", tag_name=cleaned, confidence=confidence * 0.95))

        return ClassificationResult(
            primary_topic=primary_topic,
            tags=tags[:8],
            confidence=confidence,
        )

    def _limit_text(self, value: str, max_length: int) -> str:
        cleaned = " ".join(value.split()).strip()
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[: max_length - 3].rstrip() + "..."
