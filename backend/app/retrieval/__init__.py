"""SpecMatch Retrieval Layer.

Provides:
  - Lexical retrieval (FTS5)
  - Semantic retrieval (pgvector, optional)
  - Metadata retrieval
  - Candidate fusion
  - Reranking
  - Evidence extraction
  - Confidence assessment
  - Full pipeline orchestration
"""

from .pipeline import run_pipeline, run_search_pipeline, PipelineResult
from .query import normalize as normalize_query, NormalizedQuery
from .lexical import lexical_search
from .semantic import get_embedding_provider, is_semantic_available
from .metadata import metadata_search
from .fusion import fuse_candidates
from .reranker import get_reranker
from .evidence import extract_evidence, EvidenceItem
from .confidence import assess_confidence, ConfidenceAssessment
from .requirements import extract_requirements, RequirementsResult, LLMProvider
