"""Pydantic schemas for LLM intelligence layer (Phase 5)."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class LLMAnalysisRequest(BaseModel):
    """Request to get LLM-enhanced analysis of procurement specification."""
    text: str = Field(..., min_length=1, max_length=50000, description="Procurement specification text")
    standard_ids: list[str] = Field(default_factory=list, description="Standard IDs from retrieval pipeline for context")
    query_keywords: list[str] = Field(default_factory=list, description="Extracted keywords for context")


class LLMStandardAssessment(BaseModel):
    """LLM assessment of a single standard against a requirement."""
    standard_id: str
    standard_number: str
    relevance_explanation: str = ""
    compliance_note: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    recommendation: str = ""  # "recommend", "consider", "not_relevant"
    confidence: str = "medium"  # high, medium, low


class LLMSummary(BaseModel):
    """Executive summary from LLM."""
    summary: str
    key_requirements: list[str] = Field(default_factory=list)
    compliance_overview: str = ""
    risk_assessment: str = ""
    recommended_actions: list[str] = Field(default_factory=list)


class LLMAnalysisResponse(BaseModel):
    """Response from LLM-enhanced analysis."""
    model_config = {"protected_namespaces": ()}

    model_used: str
    summary: LLMSummary
    standard_assessments: list[LLMStandardAssessment] = Field(default_factory=list)
    raw_response: str = ""
    tokens_used: int = 0
    latency_ms: int = 0
    cached: bool = False


class LLMBatchAssessRequest(BaseModel):
    """Batch assessment of multiple procurement texts."""
    items: list[LLMAnalysisRequest] = Field(..., min_length=1, max_length=10)


class LLMBatchAssessResponse(BaseModel):
    """Batch assessment response."""
    results: list[LLMAnalysisResponse]
    total_tokens: int = 0
    total_latency_ms: int = 0
