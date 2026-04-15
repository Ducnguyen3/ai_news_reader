from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.types import AIArticleInput, AIProvider
from app.utils.helpers import count_words, sha256_text


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float] = field(default_factory=list)
    dimensions: int = 0
    model_name: str = "stub-embedding-v1"


class ArticleEmbeddingGenerator:
    def generate_embedding(self, article: AIArticleInput) -> EmbeddingResult:
        seed_text = f"{article.title} {article.summary or ''} {article.content_text}"
        vector = self._stub_vector(seed_text)
        return EmbeddingResult(
            vector=vector,
            dimensions=len(vector),
            model_name="stub-embedding-v1",
        )

    def _stub_vector(self, value: str) -> list[float]:
        normalized = " ".join(value.split()).strip()
        if not normalized:
            return [0.0] * 8

        bucket_values = [0.0] * 8
        for index, character in enumerate(normalized):
            bucket = index % len(bucket_values)
            bucket_values[bucket] += (ord(character) % 97) / 100.0

        length = max(len(normalized), 1)
        return [round(item / length, 6) for item in bucket_values]

    # TODO: Replace stub vectors with real embedding generation from a model/API.
    # TODO: Add support for batching multiple articles for efficient embedding generation.


@dataclass(frozen=True)
class EmbeddingResult:
    chunk_scope: str
    vector: list[float] = field(default_factory=list)
    dimensions: int = 0
    model_name: str = "demo-embedding-v1"


@dataclass(frozen=True)
class ChunkResult:
    chunk_index: int
    chunk_text: str
    token_count: int
    embedding_vector: list[float] | None = None
    embedding_model: str | None = None
    content_hash: str | None = None


class ArticleEmbeddingGenerator:
    """Generate article-level embeddings and chunk content for retrieval."""

    def __init__(self, provider: AIProvider, chunk_size: int = 900) -> None:
        self.provider = provider
        self.chunk_size = chunk_size
        self.model_name = "demo-embedding-v1"

    def build_article_embedding(self, article: AIArticleInput) -> EmbeddingResult:
        seed_text = self._build_embedding_text(article)
        vector = self.provider.embed(seed_text)
        return EmbeddingResult(
            chunk_scope="title_summary",
            vector=vector,
            dimensions=len(vector),
            model_name=self.model_name,
        )

    def chunk_article(self, article: AIArticleInput) -> list[ChunkResult]:
        normalized = self._normalize(article.content_text)
        if not normalized:
            return []

        paragraphs = [item.strip() for item in normalized.split("\n") if item.strip()]
        if not paragraphs:
            paragraphs = [normalized]

        chunks: list[ChunkResult] = []
        current = ""
        chunk_index = 0
        for paragraph in paragraphs:
            candidate = paragraph if not current else f"{current}\n{paragraph}"
            if current and len(candidate) > self.chunk_size:
                chunks.append(self._build_chunk(chunk_index, current))
                chunk_index += 1
                current = paragraph
                continue
            current = candidate

        if current:
            chunks.append(self._build_chunk(chunk_index, current))
        return chunks

    def _build_chunk(self, chunk_index: int, text: str) -> ChunkResult:
        normalized = self._normalize(text)
        vector = self.provider.embed(normalized)
        return ChunkResult(
            chunk_index=chunk_index,
            chunk_text=normalized,
            token_count=count_words(normalized),
            embedding_vector=vector,
            embedding_model=self.model_name,
            content_hash=sha256_text(normalized.lower()),
        )

    def _build_embedding_text(self, article: AIArticleInput) -> str:
        return self._normalize(f"{article.title}\n{article.summary or ''}\n{article.content_text}")

    def _normalize(self, value: str) -> str:
        return value.replace("\r\n", "\n").strip()
