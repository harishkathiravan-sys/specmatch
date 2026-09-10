"""Candidate fusion — merge results from lexical, semantic, and metadata retrieval.

Normalizes scores from different retrieval strategies, combines them
with configurable weights, deduplicates, and returns top-N candidates.
"""

import os
from typing import Optional
from dataclasses import dataclass, field


# Configuration (engineering parameters, not scientifically tuned)
LEXICAL_WEIGHT = float(os.getenv("LEXICAL_WEIGHT", "0.50"))
SEMANTIC_WEIGHT = float(os.getenv("SEMANTIC_WEIGHT", "0.30"))
METADATA_WEIGHT = float(os.getenv("METADATA_WEIGHT", "0.20"))
FUSION_TOP_K = int(os.getenv("FUSION_TOP_K", "40"))


@dataclass
class Candidate:
    """A candidate standard from any retrieval strategy."""
    standard_id: str
    standard_number: str
    title: str
    # Per-strategy scores (None = not retrieved by that strategy)
    lexical_score: Optional[float] = None
    semantic_score: Optional[float] = None
    metadata_score: Optional[float] = None
    # Combined score after fusion
    fused_score: float = 0.0
    # Metadata
    snippet: Optional[str] = None
    matching_terms: list[str] = field(default_factory=list)
    metadata_matches: list[str] = field(default_factory=list)
    # All original standard fields
    data: dict = field(default_factory=dict)
    # Which strategies found this candidate
    retrieval_methods: list[str] = field(default_factory=list)
    rank: int = 0


def _normalize_score(score: Optional[float]) -> float:
    """Normalize a score to 0-1 range."""
    if score is None:
        return 0.0
    return max(0.0, min(1.0, float(score)))


def _normalize_scores(candidates: list[Candidate]) -> None:
    """Min-max normalize each score dimension across all candidates."""
    for attr in ("lexical_score", "semantic_score", "metadata_score"):
        scores = [getattr(c, attr) for c in candidates if getattr(c, attr) is not None]
        if not scores:
            continue
        min_s = min(scores)
        max_s = max(scores)
        range_s = max_s - min_s
        if range_s <= 0:
            # All scores identical — set to 1.0 for those with scores
            for c in candidates:
                if getattr(c, attr) is not None:
                    setattr(c, attr, 1.0)
        else:
            for c in candidates:
                val = getattr(c, attr)
                if val is not None:
                    setattr(c, attr, round((val - min_s) / range_s, 6))


def fuse_candidates(
    lexical_items: list[dict],
    semantic_items: list[dict],
    metadata_items: list[dict],
    top_k: int = FUSION_TOP_K,
    lexical_weight: float = LEXICAL_WEIGHT,
    semantic_weight: float = SEMANTIC_WEIGHT,
    metadata_weight: float = METADATA_WEIGHT,
) -> list[Candidate]:
    """Fuse candidates from multiple retrieval strategies.

    1. Convert all items to Candidate objects
    2. Deduplicate by standard_id
    3. Normalize scores within each dimension
    4. Combine with weighted sum
    5. Return top-K candidates
    """
    candidates: dict[str, Candidate] = {}

    # Index lexical results
    for item in lexical_items:
        sid = item.get("standard_id", "")
        if not sid:
            continue
        if sid not in candidates:
            candidates[sid] = Candidate(
                standard_id=sid,
                standard_number=item.get("standard_number", ""),
                title=item.get("title", ""),
                data=item,
            )
        c = candidates[sid]
        c.lexical_score = item.get("lexical_score") or item.get("match_score")
        c.snippet = item.get("snippet")
        c.matching_terms = item.get("matching_terms", [])
        if "lexical" not in c.retrieval_methods:
            c.retrieval_methods.append("lexical")

    # Index semantic results
    for item in semantic_items:
        sid = item.get("standard_id", "")
        if not sid:
            continue
        if sid not in candidates:
            candidates[sid] = Candidate(
                standard_id=sid,
                standard_number=item.get("standard_number", ""),
                title=item.get("title", ""),
                data=item,
            )
        c = candidates[sid]
        c.semantic_score = item.get("semantic_score")
        if "semantic" not in c.retrieval_methods:
            c.retrieval_methods.append("semantic")

    # Index metadata results
    for item in metadata_items:
        sid = item.get("standard_id", "")
        if not sid:
            continue
        if sid not in candidates:
            candidates[sid] = Candidate(
                standard_id=sid,
                standard_number=item.get("standard_number", ""),
                title=item.get("title", ""),
                data=item,
            )
        c = candidates[sid]
        c.metadata_score = item.get("metadata_score")
        c.metadata_matches = item.get("metadata_matches", [])
        # Merge matching terms
        existing = set(c.matching_terms)
        for mt in item.get("matching_terms", []):
            if mt not in existing:
                c.matching_terms.append(mt)
                existing.add(mt)
        if "metadata" not in c.retrieval_methods:
            c.retrieval_methods.append("metadata")

    candidate_list = list(candidates.values())
    if not candidate_list:
        return []

    # Normalize scores within each dimension
    _normalize_scores(candidate_list)

    # Calculate fused score
    for c in candidate_list:
        lex = _normalize_score(c.lexical_score) if c.lexical_score is not None else 0.0
        sem = _normalize_score(c.semantic_score) if c.semantic_score is not None else 0.0
        meta = _normalize_score(c.metadata_score) if c.metadata_score is not None else 0.0

        # Active strategy count bonus — candidates found by more strategies rank higher
        active_count = sum([
            c.lexical_score is not None,
            c.semantic_score is not None,
            c.metadata_score is not None,
        ])
        # Bonus: 0.05 per additional strategy beyond the first
        strategy_bonus = 0.05 * max(0, active_count - 1)

        # Weighted sum with strategy bonus
        raw = (lexical_weight * lex + semantic_weight * sem + metadata_weight * meta)
        c.fused_score = round(min(1.0, raw + strategy_bonus), 6)

    # Sort by fused_score descending
    candidate_list.sort(key=lambda x: x.fused_score, reverse=True)

    # Assign ranks and return top-K
    for i, c in enumerate(candidate_list[:top_k]):
        c.rank = i + 1

    return candidate_list[:top_k]
