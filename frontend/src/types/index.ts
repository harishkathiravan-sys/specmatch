// Type definitions for the SpecMatch API

export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface StandardSummary {
  id: number;
  standard_id: string;
  standard_number: string;
  title: string;
  title_normalized?: string;
  publication_year: number | null;
  type_of_standard: string | null;
  degree_of_equivalence: string | null;
  current_status: string | null;
  validation_status: string | null;
  record_type: string | null;
  synthetic_flag: boolean | string;
  sector: string | null;
  department: string | null;
  committee: string | null;
  product_category: string | null;
  standard_family_key: string | null;
  derived_keywords: string | null;
  enrichment_status?: string | null;
}

export interface StandardDetail extends StandardSummary {
  source?: string | null;
  source_type?: string | null;
  scope?: string | null;
  scope_inferred?: string | null;
  product_category_inferred?: string | null;
  standard_number_raw?: string | null;
  publication_prefix?: string | null;
  base_standard_number?: string | null;
  part?: string | null;
  section?: string | null;
  suffix?: string | null;
  inventory_status?: string | null;
  date_of_publish_raw?: string | null;
  publication_date?: string | null;
  identifier_parse_status?: string | null;
  qco_mandatory_status?: string | null;
  qco_validation_status?: string | null;
  certification_status?: string | null;
  cert_validation_status?: string | null;
  amendment_number?: string | null;
  amendment_status?: string | null;
  amendment_validation_status?: string | null;
  relationships?: Relationship[];
  family_members?: StandardSummary[];
  references?: Reference[];
}

export interface Relationship {
  relationship_type: string;
  evidence?: string;
  derivation_method?: string;
  validation_status: string;
  to_entity_id: string;
  related_number?: string | null;
  related_title?: string | null;
}

export interface Reference {
  reference_id?: string;
  from_standard_id?: string;
  to_standard_id?: string | null;
  relationship_type?: string;
  evidence?: string;
  source?: string;
  validation_status?: string;
}

export interface StandardListResponse {
  items: StandardSummary[];
  pagination: PaginationMeta;
}

export interface SearchResultItem {
  id: number;
  standard_id: string;
  standard_number: string;
  title: string;
  title_normalized?: string;
  publication_year: number | null;
  type_of_standard: string | null;
  degree_of_equivalence: string | null;
  current_status: string | null;
  validation_status: string | null;
  record_type: string | null;
  synthetic_flag: boolean | string;
  sector: string | null;
  department: string | null;
  committee: string | null;
  product_category: string | null;
  standard_family_key: string | null;
  derived_keywords: string | null;
  enrichment_status?: string | null;
  match_score: number;
  match_type: string;
  snippet?: string;
  matching_terms: string[];
  rank?: number;
}

export interface SearchResponse {
  query: string;
  items: SearchResultItem[];
  pagination: PaginationMeta;
}

export interface FilterOption {
  value: string;
  count: number;
}

export interface FilterOptions {
  sectors: FilterOption[];
  departments: FilterOption[];
  committees: FilterOption[];
  types: FilterOption[];
  years: FilterOption[];
  statuses: FilterOption[];
  families: FilterOption[];
}

export interface DatasetStats {
  total_standards: number;
  unique_families: number;
  unique_sectors: number;
  unique_departments: number;
  year_range: { min: number; max: number } | null;
  types_distribution: FilterOption[];
}

export interface AnalysisResponse {
  query: string;
  requirements: string[];
  keywords: string[];
  categories: string[];
  recommendations: SearchResultItem[];
  // Phase 2 enhanced fields
  retrieval?: {
    lexical_candidates: number;
    semantic_candidates: number;
    fused_candidates: number;
  };
  recommendations_enhanced?: RecommendationItem[];
  // Phase 6 — all optional for backwards compatibility
  dataset_version?: string;
  timing_ms?: Record<string, number>;
  phase6_enabled?: boolean;
  phase6_recommendations?: Phase6Recommendation[];
  structured_requirements?: StructuredRequirements | null;
  confidence_summary?: { top_confidence: string | null; top_confidence_score: number | null; top_reasons: string[] } | null;
  compliance_summary?: string | null;
  lifecycle_summary?: string | null;
  injection_check?: { injection_detected: boolean; threat_type: string | null; cleaned: boolean } | null;
  intelligence_summary?: Record<string, unknown> | null;
  ranking_analysis?: Record<string, unknown> | null;
  llm_analysis?: Record<string, unknown> | null;
}

export interface StructuredRequirements {
  product: string;
  application: string;
  materials: string[];
  performance_requirements: string[];
  safety_requirements: string[];
  testing_requirements: string[];
  certification_requirements: string[];
  environmental_conditions: string[];
  domain: string;
  constraints: string[];
  dimensions: string[];
  industry: string;
  intended_use: string;
  confidence: number;
}

export interface Phase6Recommendation {
  standard: { standard_id: string; standard_number: string; title: string; data: Record<string, unknown> };
  rank: number;
  relevance_score: number;
  retrieval_methods: string[];
  lexical_score?: number;
  semantic_score?: number;
  metadata_score?: number;
  evidence: EvidenceItem[];
  evidence_strength: string;
  requirement_coverage: { score: number; matched: string[]; unmatched: string[]; details: Record<string, string> };
  contradictions: Array<{ type: string; reason: string; severity: string; penalty: number }>;
  compliance: Record<string, unknown>;
  lifecycle: Record<string, unknown>;
  confidence: string;
  confidence_score: number;
  confidence_reasons: string[];
  why_this_standard: string[];
  why_not_others: string[][];
  llm_analysis?: unknown;
  llm_explanation?: string | null;
}

// Phase 2 types

export interface EvidenceItem {
  type: string;
  text: string;
  source: string;
  strength: 'strong' | 'moderate' | 'weak';
}

export interface ConfidenceInfo {
  relevance_score: number;
  confidence: 'high' | 'medium' | 'low';
  confidence_reason: string;
  compliance_status: string;
  compliance_display: string;
}

export interface RecommendationItem {
  rank: number;
  standard: StandardSummary;
  relevance_score: number;
  confidence: ConfidenceInfo;
  evidence: EvidenceItem[];
  retrieval_methods: string[];
}

export interface SavedItem {
  id: number;
  item_type: string;
  item_id: string;
  item_data: string | null;
  label: string | null;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  database: string;
  database_size_mb: number;
  version: string;
}
