from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import sqrt

from app.ai.prompts import RAG_ANSWER_PROMPT_VERSION, build_rag_answer_prompt
from app.ai.types import AIProvider
from app.repositories.article_embedding_repository import ArticleEmbeddingStore
from app.repositories.article_repository import ArticleRepository
from app.repositories.rag_chunk_repository import RAGChunkStore


@dataclass(frozen=True)
class RelatedArticleRecommendation:
    article_id: int
    score: float
    reason: str


@dataclass(frozen=True)
class AIQueryAnswer:
    query: str
    answer_text: str
    related_article_ids: list[int] = field(default_factory=list)
    model_name: str = "demo-rag-v1"


class AIQueryService:
    """Query persisted embeddings and chunks for related articles and RAG-ready retrieval."""

    def __init__(
        self,
        *,
        article_repository: ArticleRepository,
        embedding_repository: ArticleEmbeddingStore,
        rag_chunk_repository: RAGChunkStore,
        provider: AIProvider,
    ) -> None:
        self.article_repository = article_repository
        self.embedding_repository = embedding_repository
        self.rag_chunk_repository = rag_chunk_repository
        self.provider = provider

    def recommend_related_articles(self, article_id: int, top_k: int = 5) -> list[RelatedArticleRecommendation]:
        current = self.embedding_repository.get_by_article(article_id=article_id, chunk_scope="title_summary")
        if current is None:
            return []

        current_vector = self._parse_vector(current.embedding_vector)
        recommendations: list[RelatedArticleRecommendation] = []
        for candidate in self.embedding_repository.list_all(chunk_scope="title_summary"):
            if candidate.article_id == article_id:
                continue
            score = self._cosine_similarity(current_vector, self._parse_vector(candidate.embedding_vector))
            recommendations.append(
                RelatedArticleRecommendation(
                    article_id=candidate.article_id,
                    score=score,
                    reason="cosine similarity on stored article embedding",
                )
            )

        recommendations.sort(key=lambda item: item.score, reverse=True)
        return recommendations[:top_k]

    def retrieve_chunks(self, query_text: str, top_k: int = 5) -> list[dict[str, object]]:
        query_vector = self.provider.embed(query_text)
        ranked: list[dict[str, object]] = []
        for chunk in self.rag_chunk_repository.list_all():
            if not chunk.embedding_vector:
                continue
            score = self._cosine_similarity(query_vector, self._parse_vector(chunk.embedding_vector))
            ranked.append(
                {
                    "article_id": chunk.article_id,
                    "chunk_id": chunk.id,
                    "chunk_text": chunk.chunk_text,
                    "score": score,
                }
            )

        ranked.sort(key=lambda item: float(item["score"]), reverse=True)
        return ranked[:top_k]

    def answer_question(self, query_text: str, top_k: int = 5) -> AIQueryAnswer:
        retrieved = self.retrieve_chunks(query_text=query_text, top_k=top_k)
        context_blocks = [str(item["chunk_text"]) for item in retrieved]
        prompt = build_rag_answer_prompt(query_text=query_text, context="\n\n".join(context_blocks))
        answer_text = self.provider.answer(prompt=prompt, query_text=query_text, context_blocks=context_blocks)
        related_article_ids = list(dict.fromkeys(int(item["article_id"]) for item in retrieved))
        return AIQueryAnswer(
            query=query_text.strip(),
            answer_text=answer_text,
            related_article_ids=related_article_ids,
            model_name=RAG_ANSWER_PROMPT_VERSION,
        )

    def _parse_vector(self, raw_value: str) -> list[float]:
        return [float(item) for item in json.loads(raw_value)]

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(l_item * r_item for l_item, r_item in zip(left, right))
        left_norm = sqrt(sum(item * item for item in left))
        right_norm = sqrt(sum(item * item for item in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return numerator / (left_norm * right_norm)
