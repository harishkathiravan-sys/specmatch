"""SQLite database connection and session management."""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from app.config import DB_PATH, FTS_TOKENIZER


def get_connection() -> sqlite3.Connection:
    """Get a new SQLite connection with recommended pragmas."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


# A long-lived read-only connection shared across the hot per-candidate
# compliance/lifecycle lookups. It avoids re-opening + re-PRAGMA-ing a
# connection for every single candidate (~40 per query), which otherwise
# dominates Phase 6 latency. SELECT-only usage is safe in WAL mode.
_shared_read_lock = threading.Lock()
_shared_read_conn: sqlite3.Connection | None = None


def get_shared_read_connection() -> sqlite3.Connection:
    """Return a shared long-lived read-only SQLite connection.

    The connection is created lazily on first use and reused thereafter.
    WAL mode permits concurrent readers, and the connection is only used
    for SELECT queries.
    """
    global _shared_read_conn
    if _shared_read_conn is None:
        with _shared_read_lock:
            if _shared_read_conn is None:
                conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA busy_timeout=5000")
                _shared_read_conn = conn
    return _shared_read_conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_fts(conn: sqlite3.Connection) -> None:
    """Create FTS5 virtual table for full-text search."""
    conn.execute("DROP TABLE IF EXISTS standards_fts")
    conn.execute(f"""
        CREATE VIRTUAL TABLE standards_fts USING fts5(
            standard_number,
            title,
            title_normalized,
            type_of_standard,
            derived_keywords,
            standard_family_key,
            department,
            committee,
            sector,
            product_category,
            scope,
            content='standards',
            content_rowid='rowid',
            tokenize='{FTS_TOKENIZER}'
        )
    """)
    # Populate FTS index from standards table
    conn.execute("""
        INSERT INTO standards_fts(rowid, standard_number, title, title_normalized,
            type_of_standard, derived_keywords, standard_family_key, department,
            committee, sector, product_category, scope)
        SELECT rowid, standard_number, title, title_normalized, type_of_standard,
            derived_keywords, standard_family_key, department, committee, sector,
            product_category, scope
        FROM standards
    """)
    conn.commit()


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Rebuild FTS index."""
    conn.execute("INSERT INTO standards_fts(standards_fts) VALUES('rebuild')")
    conn.commit()
