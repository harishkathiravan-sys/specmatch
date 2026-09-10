"""Pydantic schemas for the SpecMatch API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# Pagination
# ============================================================

class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# Standards
# ============================================================

class StandardSummary(BaseModel):
    id: int
    standard_id: str
    standard_number: str
    title: str
    publication_year: Optional[int] = None
    type_of_standard: Optional[str] = None
    degree_of_equivalence: Optional[str] = None
    current_status: Optional[str] = None
    validation_status: Optional[str] = None
    record_type: Optional[str] = None
    synthetic_flag: bool = False
    sector: Optional[str] = None
    department: Optional[str] = None
    committee: Optional[str] = None
    product_category: Optional[str] = None
    standard_family_key: Optional[str] = None
    derived_keywords: Optional[str] = None
    enrichment_status: Optional[str] = None


class StandardDetail(StandardSummary):
    source: Optional[str] = None
    source_type: Optional[str] = None
    scope: Optional[str] = None
    scope_inferred: Optional[str] = None
    product_category_inferred: Optional[str] = None
    standard_number_raw: Optional[str] = None
    publication_prefix: Optional[str] = None
    base_standard_number: Optional[str] = None
    part: Optional[str] = None
    section: Optional[str] = None
    suffix: Optional[str] = None
    inventory_status: Optional[str] = None
    date_of_publish_raw: Optional[str] = None
    publication_date: Optional[str] = None
    identifier_parse_status: Optional[str] = None
    # Compliance
    qco_mandatory_status: Optional[str] = None
    qco_validation_status: Optional[str] = None
    certification_status: Optional[str] = None
    cert_validation_status: Optional[str] = None
    amendment_number: Optional[str] = None
    amendment_status: Optional[str] = None
    amendment_validation_status: Optional[str] = None


class StandardListResponse(BaseModel):
    items: list[StandardSummary]
    pagination: PaginationMeta


class StandardDetailResponse(BaseModel):
    standard: StandardDetail
    relationships: list[dict] = []
    related_standards: list[StandardSummary] = []


# ============================================================
# Search
# ============================================================

class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=500, description="Search query")
    sector: Optional[str] = None
    department: Optional[str] = None
    committee: Optional[str] = None
    type_of_standard: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    status: Optional[str] = None
    standard_family: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class SearchResultItem(BaseModel):
    standard: StandardSummary
    match_score: float = 0.0
    match_type: str = "fts"
    snippet: Optional[str] = None
    matching_terms: list[str] = []


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultItem]
    pagination: PaginationMeta


# ============================================================
# Filters
# ============================================================

class FilterOption(BaseModel):
    value: str
    count: int


class FilterOptions(BaseModel):
    sectors: list[FilterOption]
    departments: list[FilterOption]
    committees: list[FilterOption]
    types: list[FilterOption]
    years: list[FilterOption]
    statuses: list[FilterOption]
    families: list[FilterOption]


# ============================================================
# Compliance
# ============================================================

class ComplianceInfo(BaseModel):
    status: str  # VERIFIED_APPLICABLE, VERIFIED_NOT_APPLICABLE, NOT_VALIDATED, NEEDS_ENRICHMENT
    display_status: str
    details: Optional[dict] = None
    provenance: Optional[str] = None
    validation_status: Optional[str] = None


# ============================================================
# Relationships
# ============================================================

class StandardRelationship(BaseModel):
    relationship_type: str
    related_standard_id: str
    related_standard_number: Optional[str] = None
    related_standard_title: Optional[str] = None
    evidence: Optional[str] = None
    derivation_method: Optional[str] = None
    validation_status: str


# ============================================================
# Search History & Saved Items
# ============================================================

class SearchHistoryItem(BaseModel):
    id: int
    query: str
    search_type: str
    results_count: int
    created_at: str


class SavedItem(BaseModel):
    id: int
    item_type: str
    item_id: str
    item_data: Optional[str] = None
    label: Optional[str] = None
    created_at: str


class SaveItemRequest(BaseModel):
    item_type: str = Field(..., pattern="^(standard|recommendation|analysis)$")
    item_id: str
    item_data: Optional[str] = None
    label: Optional[str] = None


# ============================================================
# Analysis
# ============================================================

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000, description="Procurement specification text")


class AnalysisResult(BaseModel):
    requirements_extracted: list[str]
    keywords: list[str]
    categories: list[str]
    candidate_standards: list[StandardSummary]
    evidence: list[dict] = []


class EvidenceItemSchema(BaseModel):
    type: str
    text: str
    source: str
    strength: str = "moderate"


class ConfidenceSchema(BaseModel):
    relevance_score: float
    confidence: str  # "high", "medium", "low"
    confidence_reason: str = ""
    compliance_status: str = "not_validated"
    compliance_display: str = "Not validated"


class RecommendationItem(BaseModel):
    rank: int
    standard: StandardSummary
    relevance_score: float
    confidence: ConfidenceSchema
    evidence: list[EvidenceItemSchema] = []
    retrieval_methods: list[str] = []


class AnalysisResponse(BaseModel):
    # Backward-compatible fields (Phase 4 contract — never removed)
    query: str
    requirements: list[str | dict] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)
    # Phase 2 fields
    retrieval: Optional[dict] = None
    recommendations_enhanced: list[RecommendationItem] = Field(default_factory=list)
    # Phase 5 LLM intelligence (optional)
    llm_analysis: Optional[dict] = None
    # Phase 6 intelligence — all optional / null-safe for backwards compatibility
    phase6_enabled: bool = False
    phase6_recommendations: Optional[list[dict]] = None
    intelligence_summary: Optional[dict] = None
    dataset_version: Optional[str] = None
    structured_requirements: Optional[dict] = None
    confidence_summary: Optional[dict] = None
    compliance_summary: Optional[str] = None
    lifecycle_summary: Optional[str] = None
    injection_check: Optional[dict] = None
    ranking_analysis: Optional[dict] = None  # alias for intelligence_summary (SIH demo spec)
    timing_ms: Optional[dict] = None


# ============================================================
# Compare
# ============================================================

class CompareRequest(BaseModel):
    standard_ids: list[str] = Field(..., min_length=2, max_length=3)


class CompareResponse(BaseModel):
    standards: list[StandardDetail]
    differences: list[dict] = []


# ============================================================
# Stats
# ============================================================

class DatasetStats(BaseModel):
    total_standards: int
    unique_families: int
    unique_sectors: int
    unique_departments: int
    year_range: Optional[dict] = None
    types_distribution: list[FilterOption] = []
