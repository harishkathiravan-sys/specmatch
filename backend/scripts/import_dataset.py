"""Import the ManakSetu BIS dataset into SQLite."""

import csv
import sqlite3
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR, DB_PATH
from app.database import init_fts


# Mapping of CSV file to (table name, has_header)
CSV_IMPORT_MAP = [
    # Core
    ("01_core/standards.csv", "standards", True),
    ("01_core/standard_families.csv", "standard_families", True),
    ("01_core/committees.csv", "committees", True),
    ("01_core/departments.csv", "departments", True),
    ("01_core/sectors.csv", "sectors", True),
    ("01_core/amendments.csv", "amendments", True),
    ("01_core/references.csv", "references_data", True),
    ("01_core/lifecycle_events.csv", "lifecycle_events", True),
    # Compliance
    ("02_compliance/qco.csv", "qco", True),
    ("02_compliance/certification.csv", "certification", True),
    ("02_compliance/compliance_sources.csv", "compliance_sources", True),
    ("02_compliance/qco_standard_map.csv", "qco_standard_map", True),
    ("02_compliance/certification_standard_map.csv", "certification_standard_map", True),
    ("02_compliance/testing_inspection.csv", "testing_inspection", True),
    ("02_compliance/gazette_notifications.csv", "gazette_notifications", True),
    # Knowledge graph
    ("03_knowledge_graph/entities.csv", "kg_entities", True),
    ("03_knowledge_graph/relationships.csv", "relationships", True),
    ("03_knowledge_graph/graph_paths.csv", "graph_paths", True),
    ("03_knowledge_graph/relationship_evidence.csv", "relationship_evidence", True),
    # Procurement
    ("04_procurement/tenders.csv", "tenders", True),
    ("04_procurement/requirements.csv", "requirements", True),
    ("04_procurement/requirement_standard_labels.csv", "requirement_standard_labels", True),
    ("04_procurement/hard_negatives.csv", "hard_negatives", True),
    ("04_procurement/expert_labels.csv", "expert_labels", True),
    # Retrieval
    ("05_retrieval/retrieval_corpus.csv", "retrieval_documents", True),
    ("05_retrieval/bm25_documents.csv", "bm25_documents", True),
    ("05_retrieval/reranker_pairs.csv", "reranker_pairs", True),
    ("05_retrieval/query_expansions.csv", "query_expansions", True),
    ("05_retrieval/hard_negative_pairs.csv", "hard_negative_pairs", True),
    ("05_retrieval/embedding_metadata.csv", "embedding_metadata", True),
    ("05_retrieval/retrieval_metadata.csv", "retrieval_metadata", True),
    # Explainability
    ("07_explainability/recommendation_evidence.csv", "recommendation_evidence", True),
    ("07_explainability/confidence.csv", "confidence_data", True),
    ("07_explainability/decision_traces.csv", "decision_traces", True),
    ("07_explainability/evidence_spans.csv", "evidence_spans", True),
    # Evaluation
    ("09_evaluation/benchmark.csv", "benchmarks", True),
    ("09_evaluation/gold_labels.csv", "gold_labels", True),
    ("09_evaluation/hard_cases.csv", "hard_cases", True),
    ("09_evaluation/multilingual_benchmark.csv", "multilingual_benchmark", True),
    ("09_evaluation/robustness_benchmark.csv", "robustness_benchmark", True),
    # Multilingual
    ("06_multilingual/multilingual_queries.csv", "multilingual_queries", True),
    ("06_multilingual/regional_variants.csv", "regional_variants", True),
    # Synthetic
    ("10_synthetic/synthetic_candidates.csv", "synthetic_candidates", True),
    ("10_synthetic/synthetic_pairs.csv", "synthetic_pairs", True),
    ("10_synthetic/synthetic_queries.csv", "synthetic_queries", True),
    ("10_synthetic/synthetic_tenders.csv", "synthetic_tenders", True),
    # Validation
    ("08_validation/validation_queue.csv", "validation_queue", True),
    ("08_validation/source_conflicts.csv", "source_conflicts", True),
    ("08_validation/expert_validation.csv", "expert_validation", True),
    ("08_validation/conflicts.csv", "conflicts", True),
    ("08_validation/validation_log.csv", "validation_log", True),
    # Quality
    ("11_quality/duplicate_report_v03.csv", "duplicate_report_v03", True),
    ("11_quality/qa_results_v03.csv", "qa_results_v03", True),
    ("11_quality/dataset_statistics_v03.csv", "dataset_statistics_v03", True),
    ("11_quality/enrichment_coverage.csv", "enrichment_coverage", True),
    ("11_quality/source_coverage.csv", "source_coverage", True),
    # Source manifest
    ("00_raw/source_manifest.csv", "source_manifest", True),
]


def create_schema(conn: sqlite3.Connection) -> None:
    """Execute the schema SQL."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    print("  Schema created successfully.")


def count_csv_rows(csv_path: Path) -> int:
    """Count rows in a CSV file (excluding header)."""
    if not csv_path.exists():
        return 0
    with open(csv_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # subtract header


def import_csv(conn: sqlite3.Connection, csv_rel_path: str, table_name: str) -> int:
    """Import a single CSV file into a table. Returns row count."""
    csv_path = DATA_DIR / csv_rel_path
    if not csv_path.exists():
        print(f"  SKIP: {csv_rel_path} not found")
        return 0

    row_count = 0
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print(f"  SKIP: {csv_rel_path} has no headers")
                return 0

            # Get column names from the table
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            db_columns = {row[1] for row in cursor.fetchall()}

            # Filter CSV columns to only those that exist in the table
            csv_columns = [col for col in reader.fieldnames if col in db_columns]
            if not csv_columns:
                print(f"  WARN: No matching columns for {csv_rel_path} -> {table_name}")
                return 0

            placeholders = ",".join(["?"] * len(csv_columns))
            col_names = ",".join(csv_columns)
            insert_sql = f"INSERT OR IGNORE INTO {table_name} ({col_names}) VALUES ({placeholders})"

            batch = []
            for row in reader:
                values = [row.get(col, None) for col in csv_columns]
                # Convert empty strings to None
                values = [None if v == "" or v == "NOT_AVAILABLE" else v for v in values]
                batch.append(values)
                row_count += 1

                if len(batch) >= 5000:
                    conn.executemany(insert_sql, batch)
                    batch = []

            if batch:
                conn.executemany(insert_sql, batch)

            conn.commit()
            print(f"  OK: {csv_rel_path} -> {table_name}: {row_count} rows")

    except Exception as e:
        print(f"  ERROR: {csv_rel_path}: {e}")
        conn.rollback()

    return row_count


def main():
    """Main import routine."""
    print("=" * 60)
    print("SpecMatch Dataset Import")
    print("=" * 60)
    print(f"Data directory: {DATA_DIR}")
    print(f"Database: {DB_PATH}")
    print()

    if not DATA_DIR.exists():
        print(f"ERROR: Data directory not found: {DATA_DIR}")
        sys.exit(1)

    # Remove existing database
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("Removed existing database.")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    print("Creating schema...")
    create_schema(conn)

    print("\nImporting CSV files...")
    total_rows = 0
    start = time.time()

    for csv_rel_path, table_name, _ in CSV_IMPORT_MAP:
        count = import_csv(conn, csv_rel_path, table_name)
        total_rows += count

    elapsed = time.time() - start

    # Build FTS index
    print("\nBuilding full-text search index...")
    try:
        init_fts(conn)
        print("  FTS5 index built successfully.")
    except Exception as e:
        print(f"  ERROR building FTS index: {e}")

    # Print summary
    print("\n" + "=" * 60)
    print("Import Complete")
    print("=" * 60)
    print(f"Total rows imported: {total_rows}")
    print(f"Time elapsed: {elapsed:.1f}s")
    print(f"Database size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    # Verify standards count
    cursor = conn.execute("SELECT COUNT(*) FROM standards")
    std_count = cursor.fetchone()[0]
    print(f"Standards in database: {std_count}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
