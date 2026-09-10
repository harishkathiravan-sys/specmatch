"""Database connections for local SQLite and Supabase PostgreSQL."""

import re
import sqlite3
from contextlib import contextmanager

from app.config import DATABASE_URL, DB_PATH, FTS_TOKENIZER, IS_POSTGRES


def _postgres_sql(sql: str) -> str:
    """Translate the existing qmark SQL used by the application to psycopg."""
    return re.sub(r"\?", "%s", sql)


def get_connection():
    """Get a configured database connection."""
    if IS_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


_shared_read_conn = None


class _PostgresConnection:
    """Small compatibility wrapper for the app's existing qmark SQL."""

    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql, params=None):
        return self._connection.execute(_postgres_sql(sql), params or ())

    def __getattr__(self, name):
        return getattr(self._connection, name)


def get_shared_read_connection():
    """Return a reusable read connection for semantic lookups."""
    global _shared_read_conn
    if _shared_read_conn is None:
        if IS_POSTGRES:
            _shared_read_conn = get_connection()
        else:
            _shared_read_conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            _shared_read_conn.row_factory = sqlite3.Row
            _shared_read_conn.execute("PRAGMA busy_timeout=5000")
    return _shared_read_conn


@contextmanager
def get_db():
    """Yield a transactional connection for either supported database."""
    conn = get_connection()
    try:
        if IS_POSTGRES:
            conn = _PostgresConnection(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_fts(conn: sqlite3.Connection) -> None:
    """Create the SQLite FTS5 virtual table used by local development."""
    if IS_POSTGRES:
        return
    conn.execute("DROP TABLE IF EXISTS standards_fts")
    conn.execute(f"""
        CREATE VIRTUAL TABLE standards_fts USING fts5(
            standard_number, title, title_normalized, type_of_standard,
            derived_keywords, standard_family_key, department, committee,
            sector, product_category, scope, content='standards',
            content_rowid='rowid', tokenize='{FTS_TOKENIZER}'
        )
    """)
    conn.execute("""
        INSERT INTO standards_fts(rowid, standard_number, title, title_normalized,
            type_of_standard, derived_keywords, standard_family_key, department,
            committee, sector, product_category, scope)
        SELECT rowid, standard_number, title, title_normalized, type_of_standard,
            derived_keywords, standard_family_key, department, committee, sector,
            product_category, scope FROM standards
    """)
    conn.commit()


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Rebuild the local SQLite FTS index."""
    if not IS_POSTGRES:
        conn.execute("INSERT INTO standards_fts(standards_fts) VALUES('rebuild')")
        conn.commit()
