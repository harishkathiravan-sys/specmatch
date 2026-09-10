"""Reranker abstraction — re-score fused candidates for final ranking.

Provides:
  - FallbackReranker: deterministic scoring without external APIs
  - CrossEncoderReranker: cross-encoder model (optional)
  - APIReranker: external reranking API (optional)

The reranker determines semantic relevance, NOT legal/compliance applicability.
"""

import os
import re
from typing import Optional
from dataclasses import dataclass, field

from .fusion import Candidate


class Reranker:
    """Abstract reranker interface."""

    def rerank(self, query: str, candidates: list[Candidate]) -> list[Candidate]:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return "base"


class FallbackReranker(Reranker):
    """Deterministic reranker — no external APIs needed.

    Uses term overlap, title match, phrase match, and position signals.
    This is the offline fallback that always works.
    """

    def __init__(self):
        self._stop = {
            "the", "a", "an", "and", "or", "of", "for", "in", "to", "is", "by",
            "on", "at", "with", "from", "that", "this", "which", "what", "have",
            "been", "will", "shall", "should", "would", "could", "must",
        }

    def _tokenize(self, text: str) -> list[str]:
        return [t for t in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", text.lower())
                if len(t) > 2 and t not in self._stop]

    def rerank(self, query: str, candidates: list[Candidate]) -> list[Candidate]:
        q_tokens = set(self._tokenize(query))
        q_lower = query.lower()

        for c in candidates:
            title_lower = (c.title or "").lower()
            title_tokens = set(self._tokenize(c.title or ""))
            kw_text = c.data.get("derived_keywords") or ""
            kw_tokens = set(self._tokenize(kw_text))
            all_tokens = title_tokens | kw_tokens

            # 1. Exact phrase match in title (strong signal)
            phrase_bonus = 0.0
            # Check if query appears as substring of title
            if len(q_lower) > 4 and q_lower in title_lower:
                phrase_bonus = 0.30
            else:
                # Check multi-word phrases from query
                q_phrases = [p for p in q_lower.split() if len(p) > 3]
                for qp in q_phrases:
                    if qp in title_lower:
                        phrase_bonus = max(phrase_bonus, 0.15)

            # 2. Token overlap with title (Jaccard-like)
            if q_tokens and title_tokens:
                overlap = q_tokens & title_tokens
                title_jaccard = len(overlap) / max(len(q_tokens | title_tokens), 1)
            else:
                title_jaccard = 0.0

            # 3. Token overlap with keywords
            if q_tokens and kw_tokens:
                kw_overlap = q_tokens & kw_tokens
                kw_jaccard = len(kw_overlap) / max(len(q_tokens | kw_tokens), 1)
            else:
                kw_jaccard = 0.0

            # 4. Matched terms bonus (from retrieval)
            matched_count = len(c.matching_terms) if c.matching_terms else 0
            matched_bonus = min(0.15, matched_count * 0.03)

            # 5. Retrieval method agreement bonus
            method_count = len(c.retrieval_methods)
            agreement_bonus = 0.05 * max(0, method_count - 1)

            # Combine signals
            reranker_score = (
                0.35 * phrase_bonus
                + 0.25 * title_jaccard
                + 0.15 * kw_jaccard
                + 0.15 * matched_bonus
                + 0.10 * agreement_bonus
            )

            c.reranker_score = round(min(1.0, reranker_score), 6)

        # Sort by reranker_score descending
        candidates.sort(key=lambda x: getattr(x, "reranker_score", 0.0), reverse=True)

        # Assign ranks
        for i, c in enumerate(candidates):
            c.rank = i + 1

        return candidates

    @property
    def name(self) -> str:
        return "fallback"


class APIReranker(Reranker):
    """External API-based reranker (e.g., Cohere Rerank, Jina)."""

    def __init__(self, api_key: str, model: str = "rerank-english-v3.0", base_url: Optional[str] = None):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def rerank(self, query: str, candidates: list[Candidate]) -> list[Candidate]:
        if not candidates:
            return candidates

        import httpx

        documents = [
            f"{c.standard_number} — {c.title}"
            for c in candidates
        ]

        url = (self._base_url or "https://api.cohere.ai/v1") + "/rerank"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "query": query,
            "documents": documents,
            "top_documents": len(documents),
        }

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            # Map results back to candidates
            results = data.get("results", [])
            id_to_idx = {c.standard_id: i for i, c in enumerate(candidates)}
            # Create ranked list
            for r in results:
                doc_idx = r.get("index", 0)
                score = r.get("relevance_score", 0.0)
                if 0 <= doc_idx < len(candidates):
                    candidates[doc_idx].reranker_score = round(score, 6)

        except Exception:
            # Fall back to no reranking
            pass

        # Sort by reranker_score (None gets 0.0)
        candidates.sort(key=lambda x: getattr(x, "reranker_score", 0.0) or 0.0, reverse=True)
        for i, c in enumerate(candidates):
            c.rank = i + 1

        return candidates

    @property
    def name(self) -> str:
        return f"api:{self._model}"


def get_reranker() -> Reranker:
    """Factory — returns configured reranker or FallbackReranker."""
    provider = os.getenv("RERANKER_PROVIDER", "").lower()
    api_key = os.getenv("RERANKER_API_KEY", "")

    if provider == "cohere" and api_key:
        return APIReranker(
            api_key=api_key,
            model=os.getenv("RERANKER_MODEL", "rerank-english-v3.0"),
        )

    return FallbackReranker()
