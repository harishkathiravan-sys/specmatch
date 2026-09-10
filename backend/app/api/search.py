"""Search API routes."""

import json
from fastapi import APIRouter, Query
from typing import Optional

from app.database import get_db
from app.retrieval.search_service import search_standards
from app.retrieval.pipeline import run_search_pipeline

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(..., min_length=1, max_length=500),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sector: Optional[str] = None,
    department: Optional[str] = None,
    committee: Optional[str] = None,
    type_of_standard: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    status: Optional[str] = None,
    standard_family: Optional[str] = None,
    mode: Optional[str] = Query("hybrid", description="Search mode: lexical, hybrid, semantic"),
):
    """Search standards by text query with optional filters.

    mode=hybrid (default): uses lexical + metadata fusion, falls back to lexical-only if vector backend unavailable.
    mode=lexical: FTS5 only.
    mode=semantic: vector search if available, falls back to hybrid.
    """
    # If filters are active, use traditional FTS search (filters aren't in pipeline yet)
    has_filters = any([sector, department, committee, type_of_standard, year_from, year_to, status, standard_family])

    if mode == "lexical" or has_filters:
        # Use the existing lexical search (supports filters)
        result = search_standards(
            query=q,
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

        # Log search history
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO search_history (query, search_type, results_count) VALUES (?, ?, ?)",
                    (q, "search", result["pagination"]["total"]),
                )
        except Exception:
            pass

        return result

    # Pipeline search (hybrid/semantic without filters)
    from app.config import DEBUG
    pipeline_result = run_search_pipeline(
        query=q,
        mode=mode,
        page=page,
        page_size=page_size,
        debug=DEBUG,
    )

    # Log search history
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO search_history (query, search_type, results_count) VALUES (?, ?, ?)",
                (q, f"search_{mode}", pipeline_result["pagination"]["total"]),
            )
    except Exception:
        pass

    return pipeline_result
