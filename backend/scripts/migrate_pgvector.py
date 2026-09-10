"""Backward-compatible entry point for the Supabase migration."""

import sys

PG_DDL = """
-- pgvector must be installed: CREATE EXTENSION IF NOT EXISTS vector;

CREATE EXTENSION IF NOT EXISTS vector;

-- Standards table mirrors SQLite schema; adds embedding column
-- The SQLite schema.sql remains the source of truth for columns.
-- This block only shows the delta for vector search:

ALTER TABLE standards ADD COLUMN IF NOT EXISTS embedding vector(384);
-- or for OpenAI text-embedding-3-small: vector(1536)

-- HNSW index (pgvector ≥ 0.5)
CREATE INDEX IF NOT EXISTS idx_standards_embedding_hnsw
  ON standards USING hnsw (embedding vector_cosine_ops);

-- FTS: replace FTS5 with tsvector + GIN
ALTER TABLE standards ADD COLUMN IF NOT EXISTS tsv tsvector;
CREATE INDEX IF NOT EXISTS idx_standards_tsv ON standards USING gin(tsv);

-- Trigger to keep tsv current:
-- CREATE TRIGGER trg_standards_tsv ...
-- Hybrid query template:
--   WITH fts AS (... ts_rank ...), vec AS (... cosine ...),
--   fused AS (SELECT ... FROM fts FULL JOIN vec USING (id) ...)
--   SELECT * FROM fused ORDER BY 0.6*fts_rank + 0.4*(1 - cosine_distance) ...

-- Embedding population (offline, call embedding provider):
--   UPDATE standards SET embedding = :vec WHERE standard_id = :id;

-- Reranker pairs / benchmarks tables are unchanged.
"""


def main():
    from migrate_supabase import main as migrate_supabase

    return migrate_supabase()

if __name__ == "__main__":
    sys.exit(main())
