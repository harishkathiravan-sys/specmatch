"""Search service — FTS5-based full-text search for standards."""

import math
import re
import sqlite3
from typing import Optional

from app.config import SEARCH_MAX_PAGE_SIZE, SEARCH_PAGE_SIZE
from app.config import IS_POSTGRES
from app.database import get_db


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _paginate(total: int, page: int, page_size: int) -> dict:
    total_pages = max(1, math.ceil(total / page_size))
    return {"total": total, "page": page, "page_size": page_size, "total_pages": total_pages}


def _extract_search_terms(query: str) -> list[str]:
    """Extract individual search terms from a query."""
    terms = re.findall(r'[a-zA-Z0-9]+', query.lower())
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'of', 'for', 'in', 'to', 'is', 'by', 'on', 'at', 'with', 'from',
        'procurement', 'supply', 'installation', 'testing', 'suitable', 'shall', 'applicable', 'specification',
        'requirement', 'requirements', 'this', 'that', 'which', 'have', 'been',
    }
    return [t for t in terms if len(t) > 2 and t not in stop_words]


def _normalize_query(query: str) -> str:
    """Normalize a search query for FTS5 — returns OR-joined terms for recall."""
    q = query.strip()
    if re.search(r'\bIS\s*\d+', q, re.IGNORECASE):
        q = re.sub(r':\d{4}', '', q)
        return re.sub(r'\s+', ' ', q).strip()
    terms = _extract_search_terms(q)
    if not terms:
        return re.sub(r'\s+', ' ', re.sub(r'["*]', '', q)).strip()
    safe = [re.sub(r'["*]', '', t) for t in terms]
    return " OR ".join(safe) if len(safe) > 1 else safe[0]


def search_standards(
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
) -> dict:
    """Search standards using FTS5 with optional filters."""
    if IS_POSTGRES:
        from .lexical import lexical_search

        return lexical_search(
            query=query,
            page=page,
            page_size=page_size,
            sector=sector,
            department=department,
            committee=committee,
            type_of_standard=type_of_standard,
            year_from=year_from,
            year_to=year_to,
            status=status,
            standard_family=standard_family,
        )

    page_size = min(page_size, SEARCH_MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    # Build FTS query
    fts_query = _normalize_query(query)
    if not fts_query:
        fts_query = query

    # Build additional filter conditions
    filter_conditions = []
    filter_params = []

    if sector:
        filter_conditions.append("s.sector = ?")
        filter_params.append(sector)
    if department:
        filter_conditions.append("s.department = ?")
        filter_params.append(department)
    if committee:
        filter_conditions.append("s.committee = ?")
        filter_params.append(committee)
    if type_of_standard:
        filter_conditions.append("s.type_of_standard = ?")
        filter_params.append(type_of_standard)
    if year_from:
        filter_conditions.append("s.publication_year >= ?")
        filter_params.append(year_from)
    if year_to:
        filter_conditions.append("s.publication_year <= ?")
        filter_params.append(year_to)
    if status:
        filter_conditions.append("s.current_status = ?")
        filter_params.append(status)
    if standard_family:
        filter_conditions.append("s.standard_family_key = ?")
        filter_params.append(standard_family)

    filter_where = ""
    if filter_conditions:
        filter_where = "AND " + " AND ".join(filter_conditions)

    search_terms = _extract_search_terms(query)

    with get_db() as conn:
        # FTS search
        try:
            count_sql = f"""
                SELECT COUNT(*) as cnt
                FROM standards_fts fts
                JOIN standards s ON fts.rowid = s.rowid
                WHERE standards_fts MATCH ?
                {filter_where}
            """
            total = conn.execute(count_sql, [fts_query] + filter_params).fetchone()["cnt"]

            results_sql = f"""
                SELECT
                    s.id, s.standard_id, s.standard_number, s.title, s.title_normalized,
                    s.publication_year, s.type_of_standard, s.degree_of_equivalence,
                    s.current_status, s.validation_status, s.record_type, s.synthetic_flag,
                    s.sector, s.department, s.committee, s.product_category,
                    s.standard_family_key, s.derived_keywords, s.enrichment_status,
                    snippet(standards_fts, 1, '<mark>', '</mark>', '...', 40) as snippet,
                    rank
                FROM standards_fts fts
                JOIN standards s ON fts.rowid = s.rowid
                WHERE standards_fts MATCH ?
                {filter_where}
                ORDER BY rank
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(results_sql, [fts_query] + filter_params + [page_size, offset]).fetchall()

        except sqlite3.OperationalError:
            # If FTS query is malformed, fall back to LIKE search
            return _fallback_search(query, page, page_size, filter_conditions, filter_params)

    items = []
    for row in rows:
        item = _row_to_dict(row)
        # Calculate a simple match score based on rank
        rank = item.pop("rank", 0)
        # FTS5 rank is negative, convert to a 0-1 score
        match_score = max(0, min(1, 1.0 / (1.0 + abs(rank)))) if rank else 0.5
        item["match_score"] = round(match_score, 3)
        item["match_type"] = "fts"
        item["matching_terms"] = [t for t in search_terms if t in (item.get("title_normalized") or "").lower() or t in (item.get("derived_keywords") or "").lower()]
        items.append(item)

    pagination = _paginate(total, page, page_size)
    return {"query": query, "items": items, "pagination": pagination}


def _fallback_search(
    query: str, page: int, page_size: int,
    filter_conditions: list, filter_params: list,
) -> dict:
    """Fallback LIKE-based search when FTS fails."""
    offset = (page - 1) * page_size
    terms = _extract_search_terms(query)
    if not terms:
        terms = [query.lower()]

    # Build LIKE conditions
    like_conditions = []
    for term in terms:
        like_conditions.append(
            "(s.title_normalized LIKE ? OR s.derived_keywords LIKE ? OR s.standard_number LIKE ?)"
        )

    where = " AND ".join(like_conditions)
    filter_where = ""
    if filter_conditions:
        filter_where = "AND " + " AND ".join(filter_conditions)

    params = []
    for term in terms:
        pattern = f"%{term}%"
        params.extend([pattern, pattern, pattern])
    params.extend(filter_params)

    with get_db() as conn:
        count_sql = f"SELECT COUNT(*) as cnt FROM standards s WHERE {where} {filter_where}"
        total = conn.execute(count_sql, params).fetchone()["cnt"]

        query_sql = f"""
            SELECT s.id, s.standard_id, s.standard_number, s.title, s.title_normalized,
                   s.publication_year, s.type_of_standard, s.degree_of_equivalence,
                   s.current_status, s.validation_status, s.record_type, s.synthetic_flag,
                   s.sector, s.department, s.committee, s.product_category,
                   s.standard_family_key, s.derived_keywords, s.enrichment_status
            FROM standards s
            WHERE {where} {filter_where}
            ORDER BY s.standard_number
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query_sql, params + [page_size, offset]).fetchall()

    items = []
    for row in rows:
        item = _row_to_dict(row)
        item["match_score"] = 0.3
        item["match_type"] = "like"
        item["matching_terms"] = [t for t in terms if t in (item.get("title_normalized") or "").lower()]
        items.append(item)

    pagination = _paginate(total, page, page_size)
    return {"query": query, "items": items, "pagination": pagination}
