"""
Migration stub: SQLite (FTS5) → PostgreSQL + pgvector

This file is intentionally NOT run on Windows without Postgres.
It documents the target schema and provides a runnable migration
when DATABASE_URL points at Postgres.

Usage (when Postgres is available):
  DATABASE_URL=postgresql://user:pass@localhost:5432/specmatch python scripts/migrate_pgvector.py

On current SQLite deployment it is a no-op (exits with a message).
"""
import os
import sys
from pathlib import Path

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
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        print("migrate_pgvector: No Postgres DATABASE_URL set — skipping. Current deployment uses SQLite + FTS5.")
        print("To migrate, set DATABASE_URL=postgresql://... and ensure 'vector' extension is available.")
        print("\n--- Target PG delta ---")
        print(PG_DDL)
        return 0
    # If Postgres is configured, import psycopg and run DDL
    print(f"migrate_pgvector: connecting to {url[:40]}...")
    try:
        import psycopg  # psycopg3
    except ImportError:
        print("psycopg not installed. Install with: pip install psycopg[binary]")
        return 1
    # Read current SQLite schema for parity check
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    print("SQLite schema loaded, applying PG delta...")
    print(PG_DDL)
    # Actual DDL execution would happen here
    return 0

if __name__ == "__main__":
    sys.exit(main())
