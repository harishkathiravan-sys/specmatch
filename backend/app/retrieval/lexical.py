"""Lexical retrieval — FTS5 wrapper (improves existing search_service).

Keeps SQLite + FTS5 as primary lexical signal.
Extracts meaningful terms rather than one enormous query.
"""

import re
import sqlite3
import math
from typing import Optional
from app.database import get_db
from app.config import IS_POSTGRES
from app.config import SEARCH_MAX_PAGE_SIZE, SEARCH_PAGE_SIZE
from .query import normalize as normalize_query, NormalizedQuery

def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert FTS5 search result row to candidate dict."""
    return {
        "standard_id": row["standard_id"],
        "standard_number": row["standard_number"],
        "title": row["title"],
        "data": dict(row),
        # FTS5 rank: more negative = better. Use negative rank so higher = better.
        "lexical_score": float(-row["rank"]),
        "match_score": float(-row["rank"]),  # kept for backward compatibility
    }

def _paginate(total: int, page: int, page_size: int) -> dict:
    total_pages = max(1, math.ceil(total / page_size))
    return {"total": total, "page": page, "page_size": page_size, "total_pages": total_pages}

def _safe_term(t: str) -> str:
    """Sanitize a term for FTS5 query syntax.

    Removes FTS5 metacharacters and quotes hyphenated multi-word terms so the
    hyphen does not break FTS5 (unquoted '-' is a NOT operator).
    """
    t = re.sub(r'["*():^]', "", t)
    if not t:
        return ""
    if "-" in t:
        return f'"{t}"'
    return t


def _build_fts_query(nq: NormalizedQuery) -> str:
    """Build FTS5 query from normalized terms.

    - If IS identifier present, search it verbatim AND with OR terms (boost).
    - For long queries, OR-join terms for recall.
    - Preserve quoted phrases where detected.
    """
    if nq.is_identifiers:
        # Keep IS number as anchor; append OR terms for recall
        base = nq.is_identifiers[0]
        if nq.query_terms:
            tail = " OR ".join(_safe_term(t) for t in nq.query_terms[:6] if _safe_term(t))
            return f'"{base}" OR {tail}' if tail else f'"{base}"'
        return f'"{base}"'
    if not nq.query_terms:
        return ""
    # Phrase-aware: promote known multi-word phrases as quoted
    phrases = [p for p in nq.technical_terms if " " in p][:2]
    singles = [t for t in nq.query_terms if t not in " ".join(phrases).split()]
    parts: list[str] = []
    for ph in phrases:
        safe_ph = re.sub(r'["*():^]', "", ph)
        parts.append(f'"{safe_ph}"')
    for t in singles[:8]:
        safe = _safe_term(t)
        if safe:
            parts.append(safe)
    if not parts:
        return ""
    # OR for recall; rank will handle precision
    return " OR ".join(parts)

def lexical_search(
    query: str,
    page: int = 1,
    page_size: int = SEARCH_PAGE_SIZE,
    sector: Optional[str] = None,
    department: Optional[str] = None,
    committee: Optional[str] = None,
    type_of_standard: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    status: Optional[str] = None,
    standard_family: Optional[str] = None,
    top_k: Optional[int] = None,
) -> dict:
    """Lexical candidate retrieval via FTS5.

    Returns dict with items, pagination, lexical_scores (rank-derived).
    """
    if top_k is not None:
        page_size = min(top_k, SEARCH_MAX_PAGE_SIZE)
    else:
        page_size = min(page_size, SEARCH_MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    nq = normalize_query(query)
    fts_query = _build_fts_query(nq)
    if not fts_query:
        fts_query = query.strip()[:500]

    filter_conditions: list[str] = []
    filter_params: list = []
    if sector:
        filter_conditions.append("s.sector = ?"); filter_params.append(sector)
    if department:
        filter_conditions.append("s.department = ?"); filter_params.append(department)
    if committee:
        filter_conditions.append("s.committee = ?"); filter_params.append(committee)
    if type_of_standard:
        filter_conditions.append("s.type_of_standard = ?"); filter_params.append(type_of_standard)
    if year_from:
        filter_conditions.append("s.publication_year >= ?"); filter_params.append(year_from)
    if year_to:
        filter_conditions.append("s.publication_year <= ?"); filter_params.append(year_to)
    if status:
        filter_conditions.append("s.current_status = ?"); filter_params.append(status)
    if standard_family:
        filter_conditions.append("s.standard_family_key = ?"); filter_params.append(standard_family)

    filter_where = ("AND " + " AND ".join(filter_conditions)) if filter_conditions else ""
    search_terms = nq.query_terms

    if IS_POSTGRES:
        return _postgres_search(
            query, page, page_size, offset, filter_conditions, filter_params, search_terms
        )

    with get_db() as conn:
        try:
            count_sql = f"SELECT COUNT(*) as cnt FROM standards_fts fts JOIN standards s ON fts.rowid=s.rowid WHERE standards_fts MATCH ? {filter_where}"
            total = conn.execute(count_sql, [fts_query] + filter_params).fetchone()["cnt"]
            results_sql = f"""
                SELECT s.id, s.standard_id, s.standard_number, s.title, s.title_normalized,
                       s.publication_year, s.type_of_standard, s.degree_of_equivalence,
                       s.current_status, s.validation_status, s.record_type, s.synthetic_flag,
                       s.sector, s.department, s.committee, s.product_category,
                       s.standard_family_key, s.derived_keywords, s.enrichment_status,
                       snippet(standards_fts, 1, '<mark>', '</mark>', '...', 40) as snippet,
                       rank
                FROM standards_fts fts JOIN standards s ON fts.rowid=s.rowid
                WHERE standards_fts MATCH ? {filter_where}
                ORDER BY rank LIMIT ? OFFSET ?
            """
            rows = conn.execute(results_sql, [fts_query] + filter_params + [page_size, offset]).fetchall()
        except sqlite3.OperationalError:
            return _fallback_like(query, nq, page, page_size, offset, filter_conditions, filter_params)

    items: list[dict] = []
    for row in rows:
        d = _row_to_dict(row)
        rank_val = d.pop("rank", 0)
        # FTS5 rank is negative; map to 0-1 (smaller absolute rank = better)
        score = max(0.0, min(1.0, 1.0 / (1.0 + abs(float(rank_val))))) if rank_val is not None else 0.5
        d["lexical_score"] = round(score, 4)
        d["match_score"] = round(score, 3)
        d["match_type"] = "fts"
        d["matching_terms"] = [t for t in search_terms if t in (d.get("title_normalized") or "").lower() or t in (d.get("derived_keywords") or "").lower() or t in (d.get("standard_number") or "").lower()]
        items.append(d)

    pagination = _paginate(total, page, page_size)
    return {"query": query, "normalized": nq.to_dict(), "fts_query": fts_query, "items": items, "pagination": pagination}

def _fallback_like(query: str, nq: NormalizedQuery, page: int, page_size: int, offset: int, filter_conditions: list, filter_params: list) -> dict:
    terms = nq.query_terms[:4] or [query.lower()[:30]]
    like_conditions = []
    for _ in terms:
        like_conditions.append("(s.title_normalized LIKE ? OR s.derived_keywords LIKE ? OR s.standard_number LIKE ?)")
    where = " AND ".join(like_conditions) if like_conditions else "1=1"
    filter_where = ("AND " + " AND ".join(filter_conditions)) if filter_conditions else ""
    params: list = []
    for t in terms:
        pat = f"%{t}%"
        params.extend([pat, pat, pat])
    params.extend(filter_params)
    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) as cnt FROM standards s WHERE {where} {filter_where}", params).fetchone()["cnt"]
        rows = conn.execute(f"""
            SELECT s.id, s.standard_id, s.standard_number, s.title, s.title_normalized,
                   s.publication_year, s.type_of_standard, s.degree_of_equivalence,
                   s.current_status, s.validation_status, s.record_type, s.synthetic_flag,
                   s.sector, s.department, s.committee, s.product_category,
                   s.standard_family_key, s.derived_keywords, s.enrichment_status
            FROM standards s WHERE {where} {filter_where} ORDER BY s.standard_number LIMIT ? OFFSET ?
        """, params + [page_size, offset]).fetchall()
    items=[]
    for r in rows:
        d=_row_to_dict(r); d["lexical_score"]=0.3; d["match_score"]=0.3; d["match_type"]="like"
        d["matching_terms"]=[t for t in terms if t in (d.get("title_normalized") or "").lower()]
        items.append(d)
    return {"query": query, "normalized": nq.to_dict(), "fts_query": "LIKE fallback", "items": items, "pagination": _paginate(total, page, page_size)}


def _postgres_search(query, page, page_size, offset, filter_conditions, filter_params, search_terms):
    """Search the Supabase tsvector index with PostgreSQL full-text search."""
    filter_where = ("AND " + " AND ".join(filter_conditions)) if filter_conditions else ""
    with get_db() as conn:
        count_sql = f"""
            SELECT COUNT(*) AS cnt FROM standards s
            WHERE s.search_vector @@ websearch_to_tsquery('simple', ?)
            {filter_where}
        """
        total = conn.execute(count_sql, [query] + filter_params).fetchone()["cnt"]
        results_sql = f"""
            SELECT s.id, s.standard_id, s.standard_number, s.title, s.title_normalized,
                   s.publication_year, s.type_of_standard, s.degree_of_equivalence,
                   s.current_status, s.validation_status, s.record_type, s.synthetic_flag,
                   s.sector, s.department, s.committee, s.product_category,
                   s.standard_family_key, s.derived_keywords, s.enrichment_status,
                   ts_headline('simple', COALESCE(s.title, ''),
                               websearch_to_tsquery('simple', ?)) AS snippet,
                   ts_rank_cd(s.search_vector, websearch_to_tsquery('simple', ?)) AS rank
            FROM standards s
            WHERE s.search_vector @@ websearch_to_tsquery('simple', ?)
            {filter_where}
            ORDER BY rank DESC
            LIMIT ? OFFSET ?
        """
        params = [query, query, query] + filter_params + [page_size, offset]
        rows = conn.execute(results_sql, params).fetchall()

    items = []
    for row in rows:
        d = _row_to_dict(row)
        score = max(0.0, min(1.0, float(d.pop("rank", 0) or 0)))
        d["lexical_score"] = round(score, 4)
        d["match_score"] = round(score, 3)
        d["match_type"] = "fts"
        d["matching_terms"] = [
            term for term in search_terms
            if term in (d.get("title_normalized") or "").lower()
            or term in (d.get("derived_keywords") or "").lower()
            or term in (d.get("standard_number") or "").lower()
        ]
        items.append(d)
    return {
        "query": query,
        "normalized": normalize_query(query).to_dict(),
        "fts_query": "PostgreSQL websearch_to_tsquery",
        "items": items,
        "pagination": _paginate(total, page, page_size),
    }

# Legacy alias for callers still importing from search_service
def search_standards(*args, **kwargs):
    return lexical_search(*args, **kwargs)
