"""Retrieval pipeline — end-to-end procurement → recommendation engine.

Orchestrates:
  1. Query normalization
  2. Requirement extraction
  3. Lexical retrieval (FTS5)
  4. Semantic retrieval (pgvector, optional)
  5. Metadata retrieval
  6. Candidate fusion
  7. Reranking
  8. Evidence extraction
  9. Confidence assessment
  10. Recommendation assembly

All standards come from the actual 24,132-standard corpus.
No hallucinated standard IDs.
"""

import time
from typing import Optional
from dataclasses import dataclass, field

from .query import normalize as normalize_query, NormalizedQuery
from .requirements import extract_requirements, RequirementsResult, LLMProvider
from .lexical import lexical_search
from .semantic import semantic_search, get_embedding_provider, is_semantic_available, build_embedding_text
from .metadata import metadata_search
from .fusion import fuse_candidates, Candidate
from .reranker import get_reranker
from .evidence import extract_evidence, EvidenceItem
from .confidence import assess_confidence, ConfidenceAssessment
# Phase 6 modules are imported lazily inside run_pipeline to avoid circular imports


@dataclass
class PipelineResult:
    """Complete result from the retrieval pipeline."""
    # Query understanding
    raw_query: str
    normalized_query: NormalizedQuery
    requirements: RequirementsResult = field(default_factory=RequirementsResult)
    # Retrieval stats
    lexical_candidates: int = 0
    semantic_candidates: int = 0
    metadata_candidates: int = 0
    fused_candidates: int = 0
    # Timing
    timing_ms: dict = field(default_factory=dict)
    # Recommendations
    recommendations: list[dict] = field(default_factory=list)
    # Phase 6 enhanced intelligence (optional) — typed as Any to avoid circular import
    phase6_recommendations: list = field(default_factory=list)
    # Configuration
    phase6_enabled: bool = False
    phase6_intelligence: Optional[object] = None

    def to_dict(self) -> dict:
        return {
            "raw_query": self.raw_query,
            "normalized": self.normalized_query.to_dict(),
            "requirements": {
                "requirements": [r.model_dump() for r in self.requirements.requirements],
                "keywords": self.requirements.keywords,
                "categories": self.requirements.categories,
            },
            "retrieval": {
                "lexical_candidates": self.lexical_candidates,
                "semantic_candidates": self.semantic_candidates,
                "metadata_candidates": self.metadata_candidates,
                "fused_candidates": self.fused_candidates,
            },
            "timing_ms": {k: round(v, 1) for k, v in self.timing_ms.items()},
            "recommendations": self.recommendations,
            "phase6_enabled": self.phase6_enabled,
        }


def run_pipeline(
    query: str,
    top_k: int = 5,
    max_candidates: int = 40,
    llm: Optional[LLMProvider] = None,
    debug: bool = False,
    phase6: bool = True,
) -> PipelineResult:
    """Run the full retrieval pipeline.

    Returns a PipelineResult with recommendations, each containing:
      - standard fields
      - relevance_score
      - confidence assessment
      - evidence
      - Phase 6 enhanced intelligence (if enabled)
    """
    t0 = time.time()
    result = PipelineResult(raw_query=query, normalized_query=normalize_query(query))

    # Phase 6 setup — lazy import to avoid circular dependency
    phase6_engine = None
    if phase6:
        try:
            from .phase6_integration import Phase6IntelligenceEngine as _P6Engine
            phase6_engine = _P6Engine(llm)
            result.phase6_intelligence = phase6_engine
            result.phase6_enabled = True
        except Exception as e:
            if debug:
                print(f"Phase 6 disabled: {e}")

    # ── 1. Requirement extraction ──────────────────────────────────────────
    t1 = time.time()
    result.requirements = extract_requirements(query, llm)
    result.timing_ms["requirement_extraction"] = (time.time() - t1) * 1000

    # Use normalized query for retrieval
    nq = result.normalized_query

    # ── 2. Lexical retrieval ───────────────────────────────────────────────
    t2 = time.time()
    try:
        lexical_result = lexical_search(query, page=1, page_size=max_candidates)
        lexical_items = lexical_result.get("items", [])
    except Exception:
        lexical_items = []
    result.lexical_candidates = len(lexical_items)
    result.timing_ms["lexical_retrieval"] = (time.time() - t2) * 1000

    # ── 3. Semantic retrieval (optional) ─────────────────────────────────
    t3 = time.time()
    semantic_items = []
    if is_semantic_available():
        try:
            provider = get_embedding_provider()
            query_embedding = provider.embed([nq.normalized_query or query])[0]
            sem_results = semantic_search(query_embedding, top_k=max_candidates)
            # Map to dict format
            semantic_items = [
                {
                    "standard_id": r.standard_id,
                    "standard_number": r.standard_number,
                    "title": r.title,
                    "semantic_score": r.semantic_score,
                }
                for r in sem_results
            ]
        except Exception:
            semantic_items = []
    result.semantic_candidates = len(semantic_items)
    result.timing_ms["semantic_retrieval"] = (time.time() - t3) * 1000

    # ── 4. Metadata retrieval ──────────────────────────────────────────────
    t4 = time.time()
    try:
        metadata_result = metadata_search(nq, top_k=max_candidates)
        metadata_items = metadata_result.get("items", [])
    except Exception:
        metadata_items = []
    result.metadata_candidates = len(metadata_items)
    result.timing_ms["metadata_retrieval"] = (time.time() - t4) * 1000

    # ── 5. Candidate fusion ────────────────────────────────────────────────
    t5 = time.time()
    fused = fuse_candidates(lexical_items, semantic_items, metadata_items, top_k=max_candidates)
    result.fused_candidates = len(fused)
    result.timing_ms["candidate_fusion"] = (time.time() - t5) * 1000

    # ── 6. Reranking ──────────────────────────────────────────────────────
    t6 = time.time()
    reranker = get_reranker()
    try:
        reranked = reranker.rerank(query, fused)
    except Exception:
        reranked = fused
    result.timing_ms["reranking"] = (time.time() - t6) * 1000

    # Build basic recommendations
    recommendations = []
    for rank, candidate in enumerate(reranked[:top_k], start=1):
        # Extract evidence
        evidence = extract_evidence(
            query=query,
            standard=candidate.data,
            matching_terms=candidate.matching_terms,
            retrieval_methods=candidate.retrieval_methods,
        )

        # Assess confidence
        confidence = assess_confidence(
            relevance_score=candidate.fused_score,
            lexical_score=candidate.lexical_score,
            semantic_score=candidate.semantic_score,
            metadata_score=candidate.metadata_score,
            reranker_score=getattr(candidate, "reranker_score", None),
            evidence_count=len(evidence),
            retrieval_methods=candidate.retrieval_methods,
            title_match=any(e.type == "title_match" for e in evidence),
        )

        # Build recommendation
        rec = {
            "rank": rank,
            "standard": candidate.data,
            "relevance_score": candidate.fused_score,
            "confidence": confidence.to_dict(),
            "evidence": [e.to_dict() for e in evidence],
            "retrieval_methods": candidate.retrieval_methods,
        }

        # Add debug info if requested
        if debug:
            rec["_debug"] = {
                "lexical_score": candidate.lexical_score,
                "semantic_score": candidate.semantic_score,
                "metadata_score": candidate.metadata_score,
                "reranker_score": getattr(candidate, "reranker_score", None),
                "retrieval_methods": candidate.retrieval_methods,
            }

        recommendations.append(rec)

    result.recommendations = recommendations

    # Phase 6 enhancement
    if phase6 and phase6_engine:
        try:
            t7 = time.time()
            enhanced_recs = phase6_engine.process_retrieval(
                query=query,
                pipeline_result=result.to_dict(),
                debug=debug,
            )
            result.phase6_recommendations = enhanced_recs
            result.timing_ms["phase6_enhancement"] = (time.time() - t7) * 1000
        except Exception as e:
            if debug:
                print(f"Phase 6 enhancement failed: {e}")

    result.timing_ms["evidence_confidence"] = (time.time() - t7) * 1000 if 't7' in locals() else 0
    result.timing_ms["total"] = (time.time() - t0) * 1000

    return result


def run_search_pipeline(
    query: str,
    top_k: int = 10,
    page: int = 1,
    page_size: Optional[int] = None,
    mode: str = "hybrid",
    **kwargs,
) -> dict:
    """Run the pipeline and return the response shape used by the search API."""
    del mode  # Search mode is currently represented by the selected pipeline.
    requested_page_size = page_size or top_k
    requested_top_k = page * requested_page_size
    pipeline_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in {"max_candidates", "llm", "debug"}
    }
    pipeline_kwargs.setdefault("max_candidates", max(40, requested_top_k))
    pr = run_pipeline(
        query,
        top_k=requested_top_k,
        phase6=False,
        **pipeline_kwargs,
    )

    start = (page - 1) * requested_page_size
    recommendations = pr.recommendations[start:start + requested_page_size]
    items = []
    for recommendation in recommendations:
        standard = recommendation["standard"]
        items.append({
            **standard,
            "match_score": recommendation.get("relevance_score", 0.5),
            "match_type": "pipeline",
            "matching_terms": [],
            "rank": recommendation.get("rank", 0),
        })

    total = pr.fused_candidates
    total_pages = max(1, (total + requested_page_size - 1) // requested_page_size)
    return {
        "query": query,
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": requested_page_size,
            "total_pages": total_pages,
        },
        "timing_ms": pr.timing_ms,
    }


def run_enhanced_pipeline(
    query: str,
    top_k: int = 5,
    max_candidates: int = 40,
    llm: Optional[LLMProvider] = None,
    debug: bool = False,
) -> dict:
    """Delegate to Phase 6 integration — lazy import to avoid cycle."""
    from .phase6_integration import run_enhanced_pipeline as _enhanced

    return _enhanced(query, top_k=top_k, max_candidates=max_candidates, llm=llm, debug=debug)