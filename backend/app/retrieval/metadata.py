"""Metadata-based retrieval — sector, department, committee, type matching.

Provides a complementary signal to lexical/semantic retrieval.
Standards in the same sector or of the same type may be relevant.
"""

import sqlite3
from typing import Optional
from app.database import get_db
from .query import NormalizedQuery


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def metadata_search(
    nq: NormalizedQuery,
    page: int = 1,
    page_size: int = 20,
    top_k: int = 20,
) -> dict:
    """Retrieve standards based on metadata similarity.

    Uses the extracted product/application terms to find standards
    with matching sector, product_category, or department.
    Returns metadata-enriched candidates with a metadata_score.
    """
    if not nq.query_terms and not nq.product_terms and not nq.application_terms:
        return {"items": [], "method": "metadata", "count": 0}

    # Build search terms from product + application + technical terms
    search_terms = list(set(
        nq.product_terms + nq.application_terms + nq.technical_terms[:5]
    ))
    if not search_terms:
        return {"items": [], "method": "metadata", "count": 0}

    # We search the standards table for metadata matches
    # Build LIKE conditions against sector, product_category, department
    limit = min(top_k, page_size)
    
    # Score each term's match against metadata columns
    # We use a UNION ALL approach to score multiple columns
    conditions = []
    params = []
    for term in search_terms[:8]:
        like = f"%{term}%"
        conditions.append(
            "(LOWER(s.product_category) LIKE LOWER(?) OR "
            "LOWER(s.sector) LIKE LOWER(?) OR "
            "LOWER(s.title_normalized) LIKE LOWER(?))"
        )
        params.extend([like, like, like])

    where = " OR ".join(conditions)

    with get_db() as conn:
        # Count total
        count_sql = f"SELECT COUNT(*) as cnt FROM standards s WHERE ({where})"
        total = conn.execute(count_sql, params).fetchone()["cnt"]

        # Fetch candidates
        results_sql = f"""
            SELECT s.id, s.standard_id, s.standard_number, s.title, s.title_normalized,
                   s.publication_year, s.type_of_standard, s.degree_of_equivalence,
                   s.current_status, s.validation_status, s.record_type, s.synthetic_flag,
                   s.sector, s.department, s.committee, s.product_category,
                   s.standard_family_key, s.derived_keywords, s.enrichment_status
            FROM standards s
            WHERE ({where})
            LIMIT ?
        """
        rows = conn.execute(results_sql, params + [limit]).fetchall()

    items = []
    for row in rows:
        d = _row_to_dict(row)
        # Calculate metadata relevance score
        title_lower = (d.get("title_normalized") or "").lower()
        sector_lower = (d.get("sector") or "").lower()
        pc_lower = (d.get("product_category") or "").lower()
        kw_lower = (d.get("derived_keywords") or "").lower()

        matches = 0
        total_terms = len(search_terms) if search_terms else 1
        matched_detail = []

        for term in search_terms[:8]:
            term_lower = term.lower()
            if term_lower in title_lower:
                matches += 1.0
                matched_detail.append(f"title:{term}")
            elif term_lower in kw_lower:
                matches += 0.8
                matched_detail.append(f"keyword:{term}")
            elif term_lower in sector_lower:
                matches += 0.6
                matched_detail.append(f"sector:{term}")
            elif term_lower in pc_lower:
                matches += 0.7
                matched_detail.append(f"product_category:{term}")

        score = min(1.0, matches / max(total_terms, 1))
        d["metadata_score"] = round(score, 4)
        d["match_score"] = round(score, 3)
        d["match_type"] = "metadata"
        d["matching_terms"] = [t for t in search_terms if t in title_lower or t in kw_lower]
        d["metadata_matches"] = matched_detail
        items.append(d)

    # Sort by metadata_score descending
    items.sort(key=lambda x: x["metadata_score"], reverse=True)

    return {
        "items": items[:limit],
        "method": "metadata",
        "count": len(items),
        "total_matched": total,
    }
