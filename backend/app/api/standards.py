"""Standards API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.schemas.api import (
    StandardListResponse,
    StandardDetailResponse,
    StandardSummary,
    StandardDetail,
    FilterOptions,
    DatasetStats,
    CompareRequest,
    CompareResponse,
    SaveItemRequest,
    SavedItem,
    SearchHistoryItem,
)
from app.services import standards_service
from app.database import get_db

router = APIRouter(prefix="/standards", tags=["standards"])


@router.get("", response_model=StandardListResponse)
def list_standards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sector: Optional[str] = None,
    department: Optional[str] = None,
    committee: Optional[str] = None,
    type_of_standard: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    status: Optional[str] = None,
    family: Optional[str] = None,
    sort_by: str = Query("standard_number"),
    sort_dir: str = Query("asc"),
):
    """List standards with pagination and filters."""
    result = standards_service.get_standards_list(
        page=page,
        page_size=page_size,
        sector=sector,
        department=department,
        committee=committee,
        type_of_standard=type_of_standard,
        year_from=year_from,
        year_to=year_to,
        status=status,
        family=family,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return result


@router.get("/filters", response_model=FilterOptions)
def get_filters():
    """Get available filter options."""
    return standards_service.get_filter_options()


@router.get("/stats", response_model=DatasetStats)
def get_stats():
    """Get dataset statistics."""
    return standards_service.get_dataset_stats()


@router.get("/{standard_number}")
def get_standard(standard_number: str):
    """Get detailed standard information."""
    result = standards_service.get_standard_detail(standard_number)
    if not result:
        raise HTTPException(status_code=404, detail=f"Standard '{standard_number}' not found")
    return result


@router.post("/compare", response_model=CompareResponse)
def compare_standards(request: CompareRequest):
    """Compare 2-3 standards side by side."""
    standards = standards_service.get_standards_for_compare(request.standard_ids)
    if len(standards) == 0:
        raise HTTPException(status_code=404, detail="No standards found for comparison")

    # Identify meaningful differences
    if len(standards) >= 2:
        diff_fields = [
            "type_of_standard", "degree_of_equivalence", "current_status",
            "sector", "department", "committee", "product_category",
            "certification_status", "qco_mandatory_status", "amendment_status",
        ]
        differences = []
        for field in diff_fields:
            values = {s.get("standard_number"): s.get(field) for s in standards}
            unique_values = set(v for v in values.values() if v and v != "NOT_AVAILABLE")
            if len(unique_values) > 1:
                differences.append({"field": field, "values": values})
    else:
        differences = []

    return {"standards": standards, "differences": differences}


@router.post("/saved")
def save_item(request: SaveItemRequest):
    """Save a standard, recommendation, or analysis."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO saved_items (item_type, item_id, item_data, label) VALUES (?, ?, ?, ?)",
            (request.item_type, request.item_id, request.item_data, request.label),
        )
        return {"id": cursor.lastrowid, "message": "Item saved"}


@router.get("/saved/list")
def list_saved():
    """List all saved items."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM saved_items ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@router.delete("/saved/{item_id}")
def delete_saved(item_id: int):
    """Delete a saved item."""
    with get_db() as conn:
        conn.execute("DELETE FROM saved_items WHERE id = ?", (item_id,))
    return {"message": "Item deleted"}


@router.get("/history/list")
def list_history(limit: int = Query(50, ge=1, le=200)):
    """List search history."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM search_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
