from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.ai.classifier import ArticleClassifier, ClassificationResult
from app.ai.embeddings import ArticleEmbeddingGenerator, ChunkResult, EmbeddingResult
from app.ai.query_service import AIQueryAnswer, AIQueryService, RelatedArticleRecommendation
from app.ai.summarizer import ArticleSummarizer, SummaryResult
from app.ai.types import AIArticleInput, AIProvider
from app.repositories.article_ai_summary_repository import (
    ArticleAISummaryStore,
    SqlAlchemyArticleAISummaryRepository,
)
from app.repositories.article_ai_tag_repository import ArticleAITagStore, SqlAlchemyArticleAITagRepository
from app.repositories.article_embedding_repository import ArticleEmbeddingStore, SqlAlchemyArticleEmbeddingRepository
from app.repositories.article_repository import ArticleRepository
from app.repositories.rag_chunk_repository import RAGChunkStore, SqlAlchemyRAGChunkRepository
from app.utils.helpers import sha256_text


@dataclass(frozen=True)
class AIEnrichmentResult:
    article_id: int
    summary: SummaryResult
    classification: ClassificationResult
    embedding: EmbeddingResult
    chunks: list[ChunkResult]


class DemoAIProvider:
    """Local deterministic fallback provider for demo and development."""

    def summarize(self, *, prompt: str, article: AIArticleInput) -> str:
        del prompt
        sentences = [item.strip() for item in article.content_text.replace("\n", " ").split(".") if item.strip()]
        picked = sentences[:3]
        if not picked:
            picked = [article.summary or article.title]
        return ". ".join(picked).strip()[:600]

    def classify(self, *, prompt: str, article: AIArticleInput) -> dict[str, object]:
        del prompt
        text = f"{article.title} {article.summary or ''} {article.content_text}".lower()
        topic_map = {
            "cong-nghe": ["ai", "tri tue nhan tao", "phan mem", "chip", "smartphone", "startup cong nghe"],
            "tai-chinh": ["chung khoan", "co phieu", "ngan hang", "lai suat", "trai phieu"],
            "bat-dong-san": ["bat dong san", "can ho", "du an", "nha o", "dat nen"],
            "kinh-doanh": ["doanh nghiep", "thi truong", "xuat khau", "doanh thu", "dau tu"],
            "chinh-sach": ["nghi dinh", "thong tu", "bo tai chinh", "quoc hoi", "chinh phu"],
        }
        primary_topic = next(
            (
                topic
                for topic, keywords in topic_map.items()
                if any(keyword in text for keyword in keywords)
            ),
            (article.category_names[0].strip().lower() if article.category_names else "general-news"),
        )
        tags = [primary_topic]
        for item in [*article.category_names, *article.tag_names]:
            cleaned = item.strip().lower()
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
        for keyword in ["ai", "startup", "doanh nghiep", "chung khoan", "thi truong", "dau tu"]:
            if keyword in text and keyword not in tags:
                tags.append(keyword)
        return {
            "primary_topic": primary_topic,
            "tags": tags[:6],
            "confidence": 0.72,
        }

    def embed(self, text: str) -> list[float]:
        normalized = " ".join(text.split()).strip().lower()
        if not normalized:
            return [0.0] * 16

        buckets = [0.0] * 16
        for index, char in enumerate(normalized):
            buckets[index % len(buckets)] += ((ord(char) % 97) + 1) / 100.0
        divisor = max(len(normalized), 1)
        return [round(item / divisor, 6) for item in buckets]

    def answer(self, *, prompt: str, query_text: str, context_blocks: list[str]) -> str:
        del prompt, query_text
        if not context_blocks:
            return "Khong du du lieu trong kho bai viet hien tai de tra loi cau hoi nay."
        answer_body = " ".join(context_blocks[:2]).strip()
        if not answer_body:
            return "Khong du du lieu trong kho bai viet hien tai de tra loi cau hoi nay."
        return f"Theo du lieu truy xuat duoc, {answer_body[:500]}"


class AIService:
    """Facade to enrich persisted articles with summary, tags, embeddings, and chunks."""

    def __init__(
        self,
        *,
        article_repository: ArticleRepository,
        summary_repository: ArticleAISummaryStore | None = None,
        tag_repository: ArticleAITagStore | None = None,
        embedding_repository: ArticleEmbeddingStore | None = None,
        rag_chunk_repository: RAGChunkStore | None = None,
        provider: AIProvider | None = None,
    ) -> None:
        self.article_repository = article_repository
        self.summary_repository = summary_repository or SqlAlchemyArticleAISummaryRepository(article_repository.session)
        self.tag_repository = tag_repository or SqlAlchemyArticleAITagRepository(article_repository.session)
        self.embedding_repository = embedding_repository or SqlAlchemyArticleEmbeddingRepository(article_repository.session)
        self.rag_chunk_repository = rag_chunk_repository or SqlAlchemyRAGChunkRepository(article_repository.session)
        self.provider = provider or DemoAIProvider()
        self.summarizer = ArticleSummarizer(self.provider)
        self.classifier = ArticleClassifier(self.provider)
        self.embedding_generator = ArticleEmbeddingGenerator(self.provider)
        self.query_service = AIQueryService(
            article_repository=article_repository,
            embedding_repository=self.embedding_repository,
            rag_chunk_repository=self.rag_chunk_repository,
            provider=self.provider,
        )

    def enrich_article(self, article: AIArticleInput) -> AIEnrichmentResult:
        summary = self.summarizer.summarize_article(article)
        classification = self.classifier.classify_article(article)
        embedding = self.embedding_generator.build_article_embedding(article)
        chunks = self.embedding_generator.chunk_article(article)
        return AIEnrichmentResult(
            article_id=article.article_id or 0,
            summary=summary,
            classification=classification,
            embedding=embedding,
            chunks=chunks,
        )

    def process_article(self, article_id: int) -> AIEnrichmentResult | None:
        article = self.article_repository.get_article_by_id(article_id)
        if article is None:
            return None

        article_input = AIArticleInput.from_article(article)
        result = self.enrich_article(article_input)
        self._persist_result(article_id=article_id, article_input=article_input, result=result)
        return result

    def process_articles(self, article_ids: Iterable[int]) -> list[AIEnrichmentResult]:
        results: list[AIEnrichmentResult] = []
        for article_id in article_ids:
            result = self.process_article(article_id)
            if result is not None:
                results.append(result)
        return results

    def process_pending_articles(self, limit: int = 100) -> list[AIEnrichmentResult]:
        articles = self.article_repository.list_articles_pending_ai_enrichment(limit=limit)
        return self.process_articles(article.id for article in articles)

    def recommend_related_articles(self, article_id: int) -> list[RelatedArticleRecommendation]:
        return self.query_service.recommend_related_articles(article_id)

    def retrieve_chunks(self, query_text: str, top_k: int = 5) -> list[dict[str, object]]:
        return self.query_service.retrieve_chunks(query_text=query_text, top_k=top_k)

    def answer_question(self, query_text: str) -> AIQueryAnswer:
        return self.query_service.answer_question(query_text)

    def _persist_result(
        self,
        *,
        article_id: int,
        article_input: AIArticleInput,
        result: AIEnrichmentResult,
    ) -> None:
        self.summary_repository.upsert_summary(
            article_id=article_id,
            summary_text=result.summary.summary_text,
            summary_type=result.summary.summary_type,
            model_name=result.summary.model_name,
            model_version=result.summary.model_version,
            prompt_version=result.summary.prompt_version,
            status=result.summary.status,
            error_message=result.summary.error_message,
        )
        self.tag_repository.replace_tags(
            article_id=article_id,
            tags=[
                {
                    "tag_type": tag.tag_type,
                    "tag_name": tag.tag_name,
                    "confidence": int(tag.confidence * 100),
                    "is_primary": tag.is_primary,
                }
                for tag in result.classification.tags
            ],
            model_name=result.classification.model_name,
            model_version=result.classification.model_version,
            prompt_version=result.classification.prompt_version,
        )
        self.embedding_repository.upsert_embedding(
            article_id=article_id,
            embedding_model=result.embedding.model_name,
            embedding_vector=result.embedding.vector,
            content_hash=sha256_text(
                f"{article_input.title}|{article_input.summary or ''}|{article_input.content_text}".lower()
            ),
            chunk_scope=result.embedding.chunk_scope,
        )
        self.rag_chunk_repository.replace_chunks(
            article_id=article_id,
            chunks=[
                {
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.chunk_text,
                    "token_count": chunk.token_count,
                    "embedding_vector": chunk.embedding_vector,
                    "embedding_model": chunk.embedding_model,
                    "content_hash": chunk.content_hash,
                }
                for chunk in result.chunks
            ],
        )

    # TODO: Inject a real provider backed by OpenAI or another vendor.
