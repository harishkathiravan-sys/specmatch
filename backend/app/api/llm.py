"""LLM Intelligence API routes — evidence-grounded procurement analysis (Phase 5)."""

import json
from fastapi import APIRouter, HTTPException

from app.schemas.llm import (
    LLMAnalysisRequest,
    LLMAnalysisResponse,
    LLMBatchAssessRequest,
    LLMBatchAssessResponse,
)
from app.services.llm_service import analyze_with_llm

router = APIRouter(prefix="/llm", tags=["llm-intelligence"])


@router.post("/analyze", response_model=LLMAnalysisResponse)
async def llm_analyze(request: LLMAnalysisRequest):
    """Get LLM-enhanced analysis of a procurement specification.

    This endpoint combines the retrieval pipeline results with LLM
    intelligence to provide evidence-grounded procurement recommendations.
    """
    result = await analyze_with_llm(
        text=request.text,
        standard_ids=request.standard_ids,
        query_keywords=request.query_keywords,
    )

    if "error" in result and result.get("tokens_used", 0) == 0:
        # Return the response anyway with a warning — it's not a crash,
        # just a configuration issue
        pass

    return result


@router.post("/analyze-integrated")
async def llm_analyze_integrated(request: LLMAnalysisRequest):
    """Full pipeline: retrieval + LLM intelligence in one call.

    Runs the retrieval pipeline first, then passes results to LLM
    for evidence-grounded analysis. This is the main integration point
    that transforms SpecMatch from search into intelligence.
    """
    # Step 1: Run retrieval pipeline
    from app.retrieval.pipeline import run_pipeline
    from app.config import DEBUG

    pipeline_result = run_pipeline(
        query=request.text,
        top_k=10,
        max_candidates=40,
        debug=DEBUG,
    )

    # Extract pipeline results for LLM context
    pipeline_recommendations = pipeline_result.recommendations
    keywords = pipeline_result.requirements.keywords

    # Step 2: Run LLM analysis with pipeline context
    llm_result = await analyze_with_llm(
        text=request.text,
        standard_ids=[r["standard"].get("standard_id", "") for r in pipeline_recommendations],
        query_keywords=keywords,
        pipeline_recommendations=pipeline_recommendations,
    )

    # Step 3: Merge pipeline results with LLM intelligence
    response = {
        "pipeline": {
            "requirements": [r.text for r in pipeline_result.requirements.requirements],
            "keywords": keywords,
            "categories": pipeline_result.requirements.categories,
            "retrieval_stats": {
                "lexical_candidates": pipeline_result.lexical_candidates,
                "semantic_candidates": pipeline_result.semantic_candidates,
                "fused_candidates": pipeline_result.fused_candidates,
            },
            "recommendations": [
                {
                    "rank": rec.get("rank"),
                    "standard_number": rec["standard"].get("standard_number"),
                    "title": rec["standard"].get("title"),
                    "relevance_score": rec.get("relevance_score"),
                    "confidence": rec.get("confidence", {}),
                    "evidence": rec.get("evidence", []),
                }
                for rec in pipeline_recommendations[:10]
            ],
        },
        "llm": llm_result,
    }

    return response


@router.post("/batch", response_model=LLMBatchAssessResponse)
async def llm_batch_assess(request: LLMBatchAssessRequest):
    """Batch LLM assessment for multiple procurement specifications."""
    import time

    total_start = int(time.time() * 1000)
    results = []
    total_tokens = 0

    for item in request.items:
        result = await analyze_with_llm(
            text=item.text,
            standard_ids=item.standard_ids,
            query_keywords=item.query_keywords,
        )
        results.append(LLMAnalysisResponse(**result))
        total_tokens += result.get("tokens_used", 0)

    total_latency = int(time.time() * 1000) - total_start

    return LLMBatchAssessResponse(
        results=results,
        total_tokens=total_tokens,
        total_latency_ms=total_latency,
    )


@router.get("/status")
async def llm_status():
    """Check LLM service status and configuration."""
    from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL

    return {
        "configured": bool(OPENROUTER_API_KEY),
        "model": OPENROUTER_MODEL,
        "base_url": OPENROUTER_BASE_URL,
        "api_key_set": bool(OPENROUTER_API_KEY),
        "api_key_preview": f"{OPENROUTER_API_KEY[:8]}...{OPENROUTER_API_KEY[-4:]}" if OPENROUTER_API_KEY and len(OPENROUTER_API_KEY) > 12 else "not set",
    }
