# ManakSetu BIS Data V0.2 — Expanded Development Dataset

## What changed from V1
V0.2 aggressively populates the dataset with **source-derived, deterministic inferred, and synthetic training data** while preserving the 24,132-record official inventory.

### Integrity
- Official inventory records are never replaced.
- Inferred fields are marked `INFERRED_NOT_OFFICIAL`.
- Synthetic training/evaluation data is marked `SYNTHETIC`.
- QCO/certification/amendment/reference facts were **not invented**. Per-standard records explicitly state that authoritative enrichment is still required.

## Dataset scale
- Base standards: 24,132
- Procurement synthetic examples: 5,000
- Multilingual schema/query examples: 9,000
- Reranker pairs: 3,000
- Benchmark cases: 2,000
- Synthetic queries: 5,000

This package is ready for development, retrieval experimentation, BM25, vector indexing, reranking, graph work, and human/authoritative enrichment.
