"""Semantic retrieval — optional vector search via embedding providers.

Supports:
  - LocalEmbeddingProvider (sentence-transformers or similar)
  - APIEmbeddingProvider (OpenAI, Cohere, etc.)
  - Falls back gracefully when no vector backend is available

SQLite mode: no vector retrieval (returns empty).
PostgreSQL+pgvector mode: cosine similarity search over embeddings.
"""

import os
import json
import hashlib
import sqlite3
from typing import Optional
from dataclasses import dataclass, field

from .query import NormalizedQuery


# ============================================================
# Embedding provider abstraction
# ============================================================

class EmbeddingProvider:
    """Abstract embedding provider."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @property
    def model_name(self) -> str:
        return "unknown"

    @property
    def dimension(self) -> int:
        return 0

    @property
    def version(self) -> str:
        return "0.0"


class NullEmbeddingProvider(EmbeddingProvider):
    """Sentinel — no embedding provider configured."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("No embedding provider configured")

    @property
    def model_name(self) -> str:
        return "none"


class APIEmbeddingProvider(EmbeddingProvider):
    """Embedding via external API (OpenAI, Cohere, etc.)."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
        dimension: int = 1536,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx
        url = (self._base_url or "https://api.openai.com/v1") + "/embeddings"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {"model": self._model, "input": texts}
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return [item["embedding"] for item in data["data"]]

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension


class LocalEmbeddingProvider(EmbeddingProvider):
    """Embedding via local sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        self._load()
        return self._model.get_sentence_embedding_dimension()


def get_embedding_provider() -> EmbeddingProvider:
    """Factory — returns configured provider or NullEmbeddingProvider."""
    provider_type = os.getenv("EMBEDDING_PROVIDER", "").lower()
    api_key = os.getenv("EMBEDDING_API_KEY", "")

    if provider_type == "openai" and api_key:
        return APIEmbeddingProvider(
            api_key=api_key,
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            dimension=int(os.getenv("VECTOR_DIMENSION", "1536")),
        )
    if provider_type == "local":
        return LocalEmbeddingProvider(
            model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        )

    return NullEmbeddingProvider()


# ============================================================
# Embedding document builder
# ============================================================

def build_embedding_text(standard: dict) -> str:
    """Create canonical text for embedding a standard.

    Includes standard number, title, and available metadata fields.
    Excludes NOT_AVAILABLE and empty fields.
    """
    parts = []

    # Standard number
    sn = standard.get("standard_number", "")
    if sn and sn.upper() != "NOT_AVAILABLE":
        parts.append(sn)

    # Title
    title = standard.get("title", "")
    if title and title.upper() != "NOT_AVAILABLE":
        parts.append(title)

    # Metadata fields (only if meaningful)
    for field_name, label in [
        ("type_of_standard", "Type"),
        ("sector", "Sector"),
        ("product_category", "Product category"),
        ("department", "Department"),
        ("committee", "Committee"),
        ("derived_keywords", "Keywords"),
        ("scope", "Scope"),
    ]:
        value = standard.get(field_name)
        if value and value.upper() not in ("NOT_AVAILABLE", "NONE", ""):
            parts.append(f"{label}: {value}")

    return "\n".join(parts)


def embedding_cache_key(standard_id: str, model_name: str, version: str) -> str:
    """Generate a cache key for an embedding."""
    raw = f"{standard_id}|{model_name}|{version}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ============================================================
# Semantic retrieval (pgvector)
# ============================================================

@dataclass
class SemanticResult:
    standard_id: str
    standard_number: str
    title: str
    semantic_score: float
    rank: int = 0


def semantic_search(
    query_embedding: list[float],
    top_k: int = 30,
) -> list[SemanticResult]:
    """Search via pgvector cosine similarity.

    Returns empty list if pgvector is not available.
    Never crashes the pipeline.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith("postgresql"):
        # SQLite — no vector search available
        return []

    try:
        import psycopg
        conn = psycopg.connect(db_url)
        # Cosine distance query
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        sql = """
            SELECT standard_id, standard_number, title,
                   1 - (embedding <=> %s::vector) AS cosine_similarity
            FROM standards
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        with conn.cursor() as cur:
            cur.execute(sql, [embedding_str, embedding_str, top_k])
            rows = cur.fetchall()
        conn.close()
        return [
            SemanticResult(
                standard_id=r[0],
                standard_number=r[1],
                title=r[2],
                semantic_score=float(r[3]),
                rank=i + 1,
            )
            for i, r in enumerate(rows)
        ]
    except Exception:
        # Never crash — semantic is optional
        return []


def is_semantic_available() -> bool:
    """Check if semantic retrieval is configured."""
    provider = get_embedding_provider()
    return not isinstance(provider, NullEmbeddingProvider)
