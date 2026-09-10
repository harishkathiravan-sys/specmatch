"""Standards service — database queries for standards."""

import json
import math
import sqlite3
from typing import Optional

from app.config import SEARCH_MAX_PAGE_SIZE, SEARCH_PAGE_SIZE
from app.database import get_db


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def _paginate(total: int, page: int, page_size: int) -> dict:
    """Calculate pagination metadata."""
    total_pages = max(1, math.ceil(total / page_size))
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_standards_list(
    page: int = 1,
    page_size: int = SEARCH_PAGE_SIZE,
    sector: Optional[str] = None,
    department: Optional[str] = None,
    committee: Optional[str] = None,
    type_of_standard: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    status: Optional[str] = None,
    family: Optional[str] = None,
    sort_by: str = "standard_number",
    sort_dir: str = "asc",
) -> dict:
    """Get paginated standards list with optional filters."""
    page_size = min(page_size, SEARCH_MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    conditions = []
    params = []

    if sector:
        conditions.append("sector = ?")
        params.append(sector)
    if department:
        conditions.append("department = ?")
        params.append(department)
    if committee:
        conditions.append("committee = ?")
        params.append(committee)
    if type_of_standard:
        conditions.append("type_of_standard = ?")
        params.append(type_of_standard)
    if year_from:
        conditions.append("publication_year >= ?")
        params.append(year_from)
    if year_to:
        conditions.append("publication_year <= ?")
        params.append(year_to)
    if status:
        conditions.append("current_status = ?")
        params.append(status)
    if family:
        conditions.append("standard_family_key = ?")
        params.append(family)

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    # Validate sort
    allowed_sorts = {
        "standard_number", "title", "publication_year", "type_of_standard", "sector"
    }
    if sort_by not in allowed_sorts:
        sort_by = "standard_number"
    sort_dir = "DESC" if sort_dir.lower() == "desc" else "ASC"

    with get_db() as conn:
        # Count total
        count_sql = f"SELECT COUNT(*) as cnt FROM standards {where}"
        total = conn.execute(count_sql, params).fetchone()["cnt"]

        # Fetch page
        query_sql = f"""
            SELECT id, standard_id, standard_number, title, title_normalized,
                   publication_year, type_of_standard, degree_of_equivalence,
                   current_status, validation_status, record_type, synthetic_flag,
                   sector, department, committee, product_category,
                   standard_family_key, derived_keywords, enrichment_status
            FROM standards
            {where}
            ORDER BY {sort_by} {sort_dir}
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query_sql, params + [page_size, offset]).fetchall()

    items = [_row_to_dict(r) for r in rows]
    pagination = _paginate(total, page, page_size)

    return {"items": items, "pagination": pagination}


def get_standard_detail(standard_number: str) -> Optional[dict]:
    """Get full standard detail with compliance and relationships."""
    with get_db() as conn:
        # Main standard record
        row = conn.execute(
            """
            SELECT s.*, q.mandatory_status AS qco_mandatory_status,
                   q.validation_status AS qco_validation_status,
                   q.order_name AS qco_order_name,
                   q.source AS qco_source,
                   c.certification_status,
                   c.validation_status AS cert_validation_status,
                   c.scheme AS cert_scheme,
                   c.source AS cert_source,
                   a.amendment_number,
                   a.status AS amendment_status,
                   a.validation_status AS amendment_validation_status,
                   a.effective_date AS amendment_effective_date,
                   a.source AS amendment_source
            FROM standards s
            LEFT JOIN qco q ON s.standard_number = q.is_number
            LEFT JOIN certification c ON s.standard_number = c.is_number
            LEFT JOIN amendments a ON s.standard_number = a.is_number
            WHERE s.standard_number = ?
            """,
            (standard_number,),
        ).fetchone()

        if not row:
            return None

        standard = _row_to_dict(row)

        # Get relationships
        rels = conn.execute(
            """
            SELECT r.relationship_type, r.evidence, r.derivation_method,
                   r.validation_status, r.to_entity_id,
                   s.standard_number AS related_number, s.title AS related_title
            FROM relationships r
            LEFT JOIN standards s ON r.to_entity_id = s.standard_id
            WHERE r.from_entity_id = ?
            """,
            (standard["standard_id"],),
        ).fetchall()
        standard["relationships"] = [_row_to_dict(r) for r in rels]

        # Get family members
        family = []
        if standard.get("standard_family_key"):
            family = conn.execute(
                """
                SELECT standard_id, standard_number, title, publication_year,
                       type_of_standard, current_status
                FROM standards
                WHERE standard_family_key = ? AND standard_number != ?
                LIMIT 20
                """,
                (standard["standard_family_key"], standard_number),
            ).fetchall()
        standard["family_members"] = [_row_to_dict(f) for f in family]

        # Get references
        refs = conn.execute(
            """
            SELECT * FROM references_data
            WHERE from_standard_id = ?
            """,
            (standard["standard_id"],),
        ).fetchall()
        standard["references"] = [_row_to_dict(r) for r in refs]

    return standard


def get_standard_by_id(standard_id: str) -> Optional[dict]:
    """Get standard by internal standard_id."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM standards WHERE standard_id = ?",
            (standard_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None


def get_filter_options() -> dict:
    """Get all available filter options with counts."""
    with get_db() as conn:
        sectors = conn.execute(
            "SELECT sector as value, COUNT(*) as count FROM standards WHERE sector IS NOT NULL AND sector != 'NOT_AVAILABLE' GROUP BY sector ORDER BY count DESC LIMIT 50"
        ).fetchall()

        departments = conn.execute(
            "SELECT department as value, COUNT(*) as count FROM standards WHERE department IS NOT NULL AND department != 'NOT_AVAILABLE' GROUP BY department ORDER BY count DESC LIMIT 50"
        ).fetchall()

        committees = conn.execute(
            "SELECT committee as value, COUNT(*) as count FROM standards WHERE committee IS NOT NULL AND committee != 'NOT_AVAILABLE' GROUP BY committee ORDER BY count DESC LIMIT 50"
        ).fetchall()

        types = conn.execute(
            "SELECT type_of_standard as value, COUNT(*) as count FROM standards WHERE type_of_standard IS NOT NULL GROUP BY type_of_standard ORDER BY count DESC"
        ).fetchall()

        years = conn.execute(
            "SELECT CAST(publication_year AS TEXT) as value, COUNT(*) as count FROM standards WHERE publication_year IS NOT NULL GROUP BY publication_year ORDER BY publication_year DESC LIMIT 30"
        ).fetchall()

        statuses = conn.execute(
            "SELECT current_status as value, COUNT(*) as count FROM standards WHERE current_status IS NOT NULL GROUP BY current_status ORDER BY count DESC"
        ).fetchall()

        families = conn.execute(
            "SELECT standard_family_key as value, COUNT(*) as count FROM standards WHERE standard_family_key IS NOT NULL GROUP BY standard_family_key ORDER BY count DESC LIMIT 50"
        ).fetchall()

    return {
        "sectors": [_row_to_dict(r) for r in sectors],
        "departments": [_row_to_dict(r) for r in departments],
        "committees": [_row_to_dict(r) for r in committees],
        "types": [_row_to_dict(r) for r in types],
        "years": [_row_to_dict(r) for r in years],
        "statuses": [_row_to_dict(r) for r in statuses],
        "families": [_row_to_dict(r) for r in families],
    }


def get_dataset_stats() -> dict:
    """Get dataset statistics."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
        families = conn.execute(
            "SELECT COUNT(DISTINCT standard_family_key) FROM standards WHERE standard_family_key IS NOT NULL"
        ).fetchone()[0]
        sectors = conn.execute(
            "SELECT COUNT(DISTINCT sector) FROM standards WHERE sector IS NOT NULL AND sector != 'NOT_AVAILABLE'"
        ).fetchone()[0]
        departments = conn.execute(
            "SELECT COUNT(DISTINCT department) FROM standards WHERE department IS NOT NULL AND department != 'NOT_AVAILABLE'"
        ).fetchone()[0]

        year_range = conn.execute(
            "SELECT MIN(publication_year) as min_year, MAX(publication_year) as max_year FROM standards WHERE publication_year IS NOT NULL"
        ).fetchone()

        types = conn.execute(
            "SELECT type_of_standard as value, COUNT(*) as count FROM standards WHERE type_of_standard IS NOT NULL GROUP BY type_of_standard ORDER BY count DESC"
        ).fetchall()

    return {
        "total_standards": total,
        "unique_families": families,
        "unique_sectors": sectors,
        "unique_departments": departments,
        "year_range": {
            "min": year_range["min_year"],
            "max": year_range["max_year"],
        } if year_range and year_range["min_year"] else None,
        "types_distribution": [_row_to_dict(t) for t in types],
    }


def get_standards_for_compare(standard_numbers: list[str]) -> list[dict]:
    """Get multiple standards for comparison."""
    with get_db() as conn:
        placeholders = ",".join(["?"] * len(standard_numbers))
        rows = conn.execute(
            f"""
            SELECT s.*, q.mandatory_status AS qco_mandatory_status,
                   q.validation_status AS qco_validation_status,
                   c.certification_status,
                   c.validation_status AS cert_validation_status,
                   a.amendment_number, a.status AS amendment_status,
                   a.validation_status AS amendment_validation_status
            FROM standards s
            LEFT JOIN qco q ON s.standard_number = q.is_number
            LEFT JOIN certification c ON s.standard_number = c.is_number
            LEFT JOIN amendments a ON s.standard_number = a.is_number
            WHERE s.standard_number IN ({placeholders})
            """,
            standard_numbers,
        ).fetchall()
    return [_row_to_dict(r) for r in rows]
