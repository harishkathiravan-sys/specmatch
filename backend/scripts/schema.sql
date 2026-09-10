-- SpecMatch Database Schema
-- SQLite with FTS5 for search

-- ============================================================
-- CORE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS standards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_id TEXT UNIQUE NOT NULL,
    source_record_id TEXT,
    standard_number TEXT NOT NULL,
    standard_number_raw TEXT,
    publication_prefix TEXT,
    base_standard_number TEXT,
    part TEXT,
    section TEXT,
    publication_year INTEGER,
    suffix TEXT,
    standard_family_key TEXT,
    identifier_parse_status TEXT,
    title TEXT NOT NULL,
    title_raw TEXT,
    title_normalized TEXT,
    publication_date TEXT,
    date_of_publish_raw TEXT,
    type_of_standard TEXT,
    degree_of_equivalence TEXT,
    inventory_status TEXT,
    current_status TEXT,
    scope TEXT,
    department TEXT,
    committee TEXT,
    sector TEXT,
    product_category TEXT,
    validation_status TEXT,
    source TEXT,
    source_type TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0,
    derived_keywords TEXT,
    scope_inferred TEXT,
    product_category_inferred TEXT,
    enrichment_status TEXT,
    source_file TEXT,
    source_sheet TEXT,
    source_row_number TEXT,
    source_url TEXT,
    source_date TEXT,
    retrieval_date TEXT,
    last_verified TEXT,
    v03_authority_level TEXT,
    v03_scope_status TEXT,
    v03_enrichment_status TEXT,
    v03_last_verified TEXT,
    v03_provenance_id TEXT
);

CREATE TABLE IF NOT EXISTS standard_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_family_id TEXT UNIQUE NOT NULL,
    standard_family_key TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS committees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    committee_id TEXT UNIQUE NOT NULL,
    committee_name TEXT,
    source TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id TEXT UNIQUE NOT NULL,
    department_name TEXT,
    source TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_id TEXT UNIQUE NOT NULL,
    sector_name TEXT,
    source TEXT,
    validation_status TEXT
);

-- ============================================================
-- COMPLIANCE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS amendments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amendment_id TEXT UNIQUE NOT NULL,
    is_number TEXT,
    amendment_number TEXT,
    title TEXT,
    publication_date TEXT,
    effective_date TEXT,
    status TEXT,
    source TEXT,
    source_url TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS certification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certification_id TEXT UNIQUE NOT NULL,
    is_number TEXT,
    product TEXT,
    certification_status TEXT,
    scheme TEXT,
    source TEXT,
    source_url TEXT,
    validation_status TEXT,
    last_verified TEXT
);

CREATE TABLE IF NOT EXISTS qco (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qco_id TEXT UNIQUE NOT NULL,
    is_number TEXT,
    product TEXT,
    order_name TEXT,
    notification_date TEXT,
    effective_date TEXT,
    mandatory_status TEXT,
    legal_basis TEXT,
    source TEXT,
    source_url TEXT,
    validation_status TEXT,
    last_verified TEXT
);

CREATE TABLE IF NOT EXISTS compliance_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    source_name TEXT,
    source_type TEXT,
    source_url TEXT,
    source_date TEXT,
    retrieval_date TEXT,
    validation_status TEXT
);

-- ============================================================
-- RELATIONSHIPS
-- ============================================================

CREATE TABLE IF NOT EXISTS references_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_id TEXT UNIQUE NOT NULL,
    from_standard_id TEXT,
    to_standard_id TEXT,
    relationship_type TEXT,
    evidence TEXT,
    source TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relationship_id TEXT UNIQUE NOT NULL,
    from_entity_id TEXT,
    to_entity_id TEXT,
    relationship_type TEXT,
    evidence TEXT,
    source TEXT,
    derivation_method TEXT,
    validation_status TEXT
);

-- ============================================================
-- KNOWLEDGE GRAPH
-- ============================================================

CREATE TABLE IF NOT EXISTS kg_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    entity_name TEXT,
    source TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS graph_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_id TEXT UNIQUE NOT NULL,
    start_entity_id TEXT,
    end_entity_id TEXT,
    path_json TEXT,
    validation_status TEXT
);

-- ============================================================
-- PROCUREMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id TEXT UNIQUE NOT NULL,
    title TEXT,
    department TEXT,
    category TEXT,
    description TEXT,
    source TEXT,
    source_date TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id TEXT UNIQUE NOT NULL,
    tender_id TEXT,
    requirement_text TEXT,
    product TEXT,
    category TEXT,
    technical_attributes TEXT,
    mandatory_constraints TEXT,
    quantity TEXT,
    unit TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS requirement_standard_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id TEXT,
    standard_id TEXT,
    is_number TEXT,
    relevance TEXT,
    label_type TEXT,
    reason TEXT,
    annotator TEXT,
    validation_status TEXT
);

-- ============================================================
-- RETRIEVAL
-- ============================================================

CREATE TABLE IF NOT EXISTS retrieval_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT UNIQUE NOT NULL,
    standard_id TEXT,
    standard_number TEXT,
    title TEXT,
    type_of_standard TEXT,
    degree_of_equivalence TEXT,
    publication_date TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0,
    validation_status TEXT,
    scope TEXT,
    keywords TEXT,
    technical_terms TEXT,
    references_data TEXT,
    product_category TEXT,
    sector TEXT,
    search_text TEXT
);

CREATE TABLE IF NOT EXISTS bm25_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT UNIQUE NOT NULL,
    standard_id TEXT,
    standard_number TEXT,
    search_text TEXT
);

CREATE TABLE IF NOT EXISTS reranker_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_id TEXT UNIQUE NOT NULL,
    query TEXT,
    positive_standard_id TEXT,
    negative_standard_id TEXT,
    label TEXT,
    difficulty TEXT,
    reason TEXT,
    source TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0
);

-- ============================================================
-- EXPLAINABILITY
-- ============================================================

CREATE TABLE IF NOT EXISTS recommendation_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT,
    query_id TEXT,
    standard_id TEXT,
    rank INTEGER,
    evidence_type TEXT,
    evidence_text TEXT,
    source TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS confidence_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT,
    confidence_score REAL,
    confidence_level TEXT,
    evidence_count INTEGER,
    source_quality TEXT,
    retrieval_score REAL,
    validation_status TEXT,
    abstention_flag INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS decision_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT UNIQUE NOT NULL,
    query_id TEXT,
    stage TEXT,
    input_json TEXT,
    output_json TEXT,
    validation_status TEXT
);

-- ============================================================
-- EVALUATION
-- ============================================================

CREATE TABLE IF NOT EXISTS benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT UNIQUE NOT NULL,
    query TEXT,
    product TEXT,
    category TEXT,
    expected_standard_ids TEXT,
    acceptable_related_standard_ids TEXT,
    hard_negative_standard_ids TEXT,
    language TEXT,
    difficulty TEXT,
    source_type TEXT,
    validation_status TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0
);

-- ============================================================
-- MULTILINGUAL
-- ============================================================

CREATE TABLE IF NOT EXISTS multilingual_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT UNIQUE NOT NULL,
    query TEXT,
    language TEXT,
    script TEXT,
    standard_id TEXT,
    translation_type TEXT,
    validation_status TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS terminology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT,
    language TEXT,
    translation TEXT,
    standard_id TEXT,
    source TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_language TEXT,
    target_language TEXT,
    source_text TEXT,
    translated_text TEXT,
    standard_id TEXT,
    source TEXT,
    validation_status TEXT
);

-- ============================================================
-- V0.3 LIFECYCLE & PROVENANCE
-- ============================================================

CREATE TABLE IF NOT EXISTS lifecycle_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lifecycle_event_id TEXT UNIQUE NOT NULL,
    entity_id TEXT,
    entity_type TEXT,
    event_type TEXT,
    event_date TEXT,
    source TEXT,
    source_id TEXT,
    validation_status TEXT,
    authority_level TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS source_manifest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    source_name TEXT,
    source_type TEXT,
    publisher TEXT,
    locator TEXT,
    publication_date TEXT,
    retrieval_date TEXT,
    authority_level TEXT,
    source_url TEXT,
    coverage_role TEXT,
    content_hash TEXT,
    status TEXT
);

-- ============================================================
-- V0.3 COMPLIANCE MAPPINGS
-- ============================================================

CREATE TABLE IF NOT EXISTS qco_standard_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id TEXT UNIQUE NOT NULL,
    qco_id TEXT,
    is_number TEXT,
    standard_id TEXT,
    product TEXT,
    issuing_ministry_department TEXT,
    effective_date TEXT,
    qco_status TEXT,
    authority_level TEXT,
    source_id TEXT,
    mapping_method TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS certification_standard_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_number TEXT,
    standard_id TEXT,
    product TEXT,
    issuing_ministry_department TEXT,
    effective_date TEXT,
    authority_level TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS testing_inspection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    testing_id TEXT UNIQUE NOT NULL,
    is_number TEXT,
    effective_date TEXT,
    testing_scheme TEXT,
    inspection_scheme TEXT,
    description TEXT,
    source_url TEXT,
    source_type TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS gazette_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gazette_id TEXT UNIQUE NOT NULL,
    qco_id TEXT,
    notification_number TEXT,
    notification_date TEXT,
    effective_date TEXT,
    document_status TEXT,
    description TEXT,
    source TEXT,
    source_url TEXT,
    validation_status TEXT,
    document_capture_status TEXT
);

-- ============================================================
-- V0.3 KNOWLEDGE GRAPH EVIDENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS relationship_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relationship_id TEXT,
    from_entity_id TEXT,
    to_entity_id TEXT,
    relationship_type TEXT,
    evidence TEXT,
    source TEXT,
    derivation_method TEXT,
    validation_status TEXT
);

-- ============================================================
-- V0.3 PROCUREMENT (hard negatives & expert labels)
-- ============================================================

CREATE TABLE IF NOT EXISTS hard_negatives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hard_negative_id TEXT UNIQUE NOT NULL,
    requirement_id TEXT,
    tender_id TEXT,
    negative_standard_id TEXT,
    negative_standard_number TEXT,
    negative_title TEXT,
    similarity_score REAL,
    negative_reason TEXT,
    source TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS expert_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expert_label_id TEXT UNIQUE NOT NULL,
    requirement_id TEXT,
    standard_id TEXT,
    label TEXT,
    relevance TEXT,
    annotator TEXT,
    annotation_date TEXT,
    evidence_source TEXT,
    validation_status TEXT
);

-- ============================================================
-- V0.3 RETRIEVAL (query expansions, hard negatives, metadata)
-- ============================================================

CREATE TABLE IF NOT EXISTS query_expansions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expansion_id TEXT UNIQUE NOT NULL,
    standard_id TEXT,
    standard_number TEXT,
    expansion_type TEXT,
    expanded_query TEXT,
    language TEXT,
    generation_method TEXT,
    authority_status TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS hard_negative_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_id TEXT UNIQUE NOT NULL,
    query_id TEXT,
    negative_standard_id TEXT,
    pair_type TEXT,
    reason TEXT,
    similarity_score REAL,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS embedding_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vector_id TEXT UNIQUE NOT NULL,
    standard_id TEXT,
    model_name TEXT,
    dimension INTEGER,
    embedding_version TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS retrieval_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT UNIQUE NOT NULL,
    standard_id TEXT,
    standard_number TEXT,
    validation_status TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0,
    v03_query_expansion_available TEXT,
    v03_provenance_status TEXT
);

-- ============================================================
-- V0.3 MULTILINGUAL (regional variants)
-- ============================================================

CREATE TABLE IF NOT EXISTS regional_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regional_variant_id TEXT UNIQUE NOT NULL,
    standard_id TEXT,
    standard_number TEXT,
    source_title TEXT,
    target_language TEXT,
    variant_text TEXT,
    validation_status TEXT,
    authority_status TEXT
);

-- ============================================================
-- V0.3 EXPLAINABILITY (evidence spans)
-- ============================================================

CREATE TABLE IF NOT EXISTS evidence_spans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_span_id TEXT UNIQUE NOT NULL,
    standard_id TEXT,
    standard_number TEXT,
    field TEXT,
    evidence_text TEXT,
    char_start INTEGER,
    char_end INTEGER,
    evidence_source TEXT,
    validation_status TEXT
);

-- ============================================================
-- V0.3 VALIDATION (queue, conflicts, expert validation, log)
-- ============================================================

CREATE TABLE IF NOT EXISTS validation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    validation_task TEXT,
    status TEXT,
    priority TEXT,
    reason TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS source_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conflict_id TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    field_name TEXT,
    source_a TEXT,
    value_a TEXT,
    source_b TEXT,
    value_b TEXT,
    resolution_status TEXT,
    resolution_note TEXT
);

CREATE TABLE IF NOT EXISTS expert_validation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    validation_id TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    validator TEXT,
    decision TEXT,
    validation_date TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conflict_id TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    field_name TEXT,
    value_a TEXT,
    value_b TEXT,
    source_a TEXT,
    source_b TEXT,
    status TEXT,
    resolution TEXT
);

CREATE TABLE IF NOT EXISTS validation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    check_name TEXT,
    result TEXT,
    severity TEXT,
    message TEXT,
    checked_at TEXT
);

-- ============================================================
-- V0.3 EVALUATION (gold labels, hard cases, benchmarks)
-- ============================================================

CREATE TABLE IF NOT EXISTS gold_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT,
    standard_id TEXT,
    label TEXT,
    relevance TEXT,
    annotator TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS hard_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT UNIQUE NOT NULL,
    query_id TEXT,
    standard_id TEXT,
    candidate_title TEXT,
    case_type TEXT,
    expected_action TEXT,
    record_type TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS multilingual_benchmark (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark_id TEXT UNIQUE NOT NULL,
    query TEXT,
    target_standard_id TEXT,
    language TEXT,
    generation_note TEXT,
    validation_status TEXT,
    source_type TEXT,
    record_type TEXT
);

CREATE TABLE IF NOT EXISTS robustness_benchmark (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT UNIQUE NOT NULL,
    base_query TEXT,
    variant_query TEXT,
    variant_type TEXT,
    language TEXT,
    validation_status TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 0
);

-- ============================================================
-- V0.3 SYNTHETIC (candidates, pairs, queries, tenders)
-- ============================================================

CREATE TABLE IF NOT EXISTS synthetic_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT UNIQUE NOT NULL,
    query_id TEXT,
    standard_id TEXT,
    label TEXT,
    difficulty TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 1,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS synthetic_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_id TEXT UNIQUE NOT NULL,
    query TEXT,
    standard_id TEXT,
    label TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 1,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS synthetic_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT UNIQUE NOT NULL,
    query TEXT,
    target_standard_id TEXT,
    language TEXT,
    noise_type TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 1,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS synthetic_tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id TEXT UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    target_standard_id TEXT,
    record_type TEXT,
    synthetic_flag INTEGER DEFAULT 1,
    validation_status TEXT
);

-- ============================================================
-- V0.3 QUALITY REPORTS
-- ============================================================

CREATE TABLE IF NOT EXISTS duplicate_report_v03 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_id TEXT,
    standard_number TEXT,
    title TEXT,
    title_normalized TEXT,
    v03_duplicate_status TEXT
);

CREATE TABLE IF NOT EXISTS qa_results_v03 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qa_id TEXT,
    check_name TEXT,
    pass_flag TEXT,
    details TEXT
);

CREATE TABLE IF NOT EXISTS dataset_statistics_v03 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT,
    rows INTEGER,
    bytes INTEGER
);

CREATE TABLE IF NOT EXISTS enrichment_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT,
    description TEXT,
    value TEXT,
    target TEXT,
    interpretation TEXT,
    validation_status TEXT
);

CREATE TABLE IF NOT EXISTS source_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT,
    source_role TEXT,
    records_captured INTEGER,
    records_expected_or_applicable TEXT,
    coverage_note TEXT,
    authority_level TEXT
);

-- ============================================================
-- V0.3 LLM INTELLIGENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS llm_analysis_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,
    query_text TEXT,
    model_used TEXT,
    analysis_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- APPLICATION TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    search_type TEXT DEFAULT 'search',
    results_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS saved_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT NOT NULL,  -- 'standard', 'recommendation', 'analysis'
    item_id TEXT NOT NULL,
    item_data TEXT,  -- JSON blob for flexibility
    label TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT,
    file_name TEXT,
    requirements_json TEXT,
    recommendations_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_standards_number ON standards(standard_number);
CREATE INDEX IF NOT EXISTS idx_standards_family ON standards(standard_family_key);
CREATE INDEX IF NOT EXISTS idx_standards_year ON standards(publication_year);
CREATE INDEX IF NOT EXISTS idx_standards_type ON standards(type_of_standard);
CREATE INDEX IF NOT EXISTS idx_standards_sector ON standards(sector);
CREATE INDEX IF NOT EXISTS idx_standards_department ON standards(department);
CREATE INDEX IF NOT EXISTS idx_standards_status ON standards(current_status);
CREATE INDEX IF NOT EXISTS idx_standards_validation ON standards(validation_status);
CREATE INDEX IF NOT EXISTS idx_standards_title ON standards(title_normalized);

CREATE INDEX IF NOT EXISTS idx_amendments_is ON amendments(is_number);
CREATE INDEX IF NOT EXISTS idx_certification_is ON certification(is_number);
CREATE INDEX IF NOT EXISTS idx_qco_is ON qco(is_number);
CREATE INDEX IF NOT EXISTS idx_references_from ON references_data(from_standard_id);
CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);

CREATE INDEX IF NOT EXISTS idx_tenders_id ON tenders(tender_id);
CREATE INDEX IF NOT EXISTS idx_requirements_tender ON requirements(tender_id);
CREATE INDEX IF NOT EXISTS idx_requirements_product ON requirements(product);
CREATE INDEX IF NOT EXISTS idx_req_labels_req ON requirement_standard_labels(requirement_id);
CREATE INDEX IF NOT EXISTS idx_req_labels_std ON requirement_standard_labels(standard_id);

CREATE INDEX IF NOT EXISTS idx_bm25_std ON bm25_documents(standard_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_std ON retrieval_documents(standard_id);

CREATE INDEX IF NOT EXISTS idx_saved_type ON saved_items(item_type);
CREATE INDEX IF NOT EXISTS idx_saved_item ON saved_items(item_id);

-- ============================================================
-- VIEWS
-- ============================================================

CREATE VIEW IF NOT EXISTS v_standards_full AS
SELECT
    s.id,
    s.standard_id,
    s.standard_number,
    s.title,
    s.title_normalized,
    s.publication_year,
    s.type_of_standard,
    s.degree_of_equivalence,
    s.current_status,
    s.inventory_status,
    s.scope,
    s.department,
    s.committee,
    s.sector,
    s.product_category,
    s.standard_family_key,
    s.derived_keywords,
    s.validation_status,
    s.record_type,
    s.synthetic_flag,
    s.source,
    s.enrichment_status,
    q.mandatory_status AS qco_mandatory_status,
    q.validation_status AS qco_validation_status,
    c.certification_status,
    c.validation_status AS cert_validation_status,
    a.amendment_number,
    a.status AS amendment_status,
    a.validation_status AS amendment_validation_status
FROM standards s
LEFT JOIN qco q ON s.standard_number = q.is_number
LEFT JOIN certification c ON s.standard_number = c.is_number
LEFT JOIN amendments a ON s.standard_number = a.is_number;
