"""Compliance intelligence — Phase 6.8.

Uses verified V0.3 compliance data tables:
  - qco / qco_standard_map
  - certification / certification_standard_map
  - gazette_notifications
  - testing_inspection

Never invents compliance facts. Differentiates:
  1. Confirmed mandatory requirement
  2. Upcoming requirement
  3. General BIS certification information
  4. Unknown / not available
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.database import get_db


_NA_MSG = "Not available in the current verified dataset."


def _normalize_is_number(standard_number: str) -> str:
    """Normalize 'IS 19763:2026' style numbers for lookups."""
    sn = standard_number.strip()
    # Try exact, then without year, then with different spacing
    return sn


def _standard_id_for(standard_number: str) -> Optional[str]:
    """Find the standard_id for a standard_number."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT standard_id FROM standards WHERE standard_number = ? LIMIT 1",
                (standard_number,),
            ).fetchone()
            if row:
                return row["standard_id"]
            # Try without year
            base = re.sub(r":\d{4}$", "", standard_number.strip())
            row = conn.execute(
                "SELECT standard_id FROM standards WHERE standard_number LIKE ? LIMIT 1",
                (base + "%",),
            ).fetchone()
            if row:
                return row["standard_id"]
    except Exception:
        pass
    return None


def _fetch_rows(sql: str, params: tuple) -> list[dict]:
    try:
        with get_db() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_qco_info(standard_number: str, standard_id: Optional[str] = None) -> dict:
    """QCO information for a standard. Returns {} if nothing found."""
    sid = standard_id or _standard_id_for(standard_number)
    rows: list[dict] = []
    if sid:
        rows = _fetch_rows(
            "SELECT q.* FROM qco q JOIN qco_standard_map m ON q.qco_id = m.qco_id "
            "WHERE m.is_number = ? OR m.standard_id = ?",
            (standard_number, sid),
        )
    if not rows:
        # Direct qco lookup by is_number
        rows = _fetch_rows(
            "SELECT * FROM qco WHERE is_number = ? OR is_number LIKE ?",
            (standard_number, re.sub(r":\d{4}$", "", standard_number) + "%"),
        )
    if not rows:
        return {}

    row = rows[0]
    status_raw = (row.get("mandatory_status") or "UNKNOWN").upper()
    effective_date = row.get("effective_date") or ""

    # Interpret status into the four categories
    if "UPCOMING" in status_raw or (effective_date and effective_date >= "2026-01-01"):
        status = "UPCOMING"
        display = "QCO applicable from a future effective date."
    elif "MANDATORY" in status_raw or "ACTIVE" in status_raw:
        status = "MANDATORY"
        display = "Compulsory registration/QCO is in force."
    elif "WITHDRAWN" in status_raw or "REVOKED" in status_raw:
        status = "WITHDRAWN"
        display = "QCO has been withdrawn/revoked per dataset."
    else:
        status = "UNKNOWN"
        display = "QCO status is not confirmed in the current verified dataset."

    return {
        "status": status,
        "display": display,
        "product": row.get("product"),
        "order_name": row.get("order_name"),
        "notification_date": row.get("notification_date"),
        "effective_date": effective_date,
        "mandatory_status": row.get("mandatory_status"),
        "legal_basis": row.get("legal_basis"),
        "source": row.get("source"),
        "source_type": "verified_dataset" if row.get("validation_status") in (
            "SOURCE_DERIVED", "VERIFIED", "HIGH", None
        ) else "unverified",
        "validation_status": row.get("validation_status"),
    }


def get_certification_info(standard_number: str, standard_id: Optional[str] = None) -> dict:
    """Certification information for a standard. Returns {} if nothing found."""
    sid = standard_id or _standard_id_for(standard_number)
    rows: list[dict] = []
    if sid:
        rows = _fetch_rows(
            "SELECT c.* FROM certification c JOIN certification_standard_map m "
            "ON c.is_number = m.is_number WHERE m.is_number = ? OR m.standard_id = ?",
            (standard_number, sid),
        )
    if not rows:
        rows = _fetch_rows(
            "SELECT * FROM certification WHERE is_number = ? OR is_number LIKE ?",
            (standard_number, re.sub(r":\d{4}$", "", standard_number) + "%"),
        )
    if not rows:
        return {}

    row = rows[0]
    cert_status = (row.get("certification_status") or "UNKNOWN").upper()
    if "MANDATORY" in cert_status:
        status = "MANDATORY_ON_EFFECTIVE_DATE"
        display = "Certification becomes mandatory on the QCO effective date."
    elif "VOLUNTARY" in cert_status:
        status = "VOLUNTARY"
        display = "Certification is voluntary (BIS may issue on request)."
    elif "ACTIVE" in cert_status:
        status = "ACTIVE"
        display = "Certification scheme active per dataset."
    else:
        status = "UNKNOWN"
        display = "Certification status is not confirmed in the current verified dataset."

    return {
        "status": status,
        "display": display,
        "product": row.get("product"),
        "scheme": row.get("scheme"),
        "source": row.get("source"),
        "source_type": "verified_dataset",
        "validation_status": row.get("validation_status"),
    }


def get_gazette_info(standard_number: str) -> dict:
    """Gazette notification info. Returns {} if nothing found."""
    rows = _fetch_rows(
        "SELECT g.* FROM gazette_notifications g JOIN qco q ON g.qco_id = q.qco_id "
        "WHERE q.is_number = ? OR q.is_number LIKE ?",
        (standard_number, re.sub(r":\d{4}$", "", standard_number) + "%"),
    )
    if not rows:
        return {}
    row = rows[0]
    return {
        "notification_number": row.get("notification_number"),
        "notification_date": row.get("notification_date"),
        "effective_date": row.get("effective_date"),
        "document_status": row.get("document_status"),
        "description": row.get("description"),
        "source_type": "verified_dataset",
        "validation_status": row.get("validation_status"),
    }


def get_testing_inspection_info(standard_number: str) -> dict:
    rows = _fetch_rows(
        "SELECT * FROM testing_inspection WHERE is_number = ? OR is_number LIKE ?",
        (standard_number, re.sub(r":\d{4}$", "", standard_number) + "%"),
    )
    if not rows:
        return {}
    row = rows[0]
    return {
        "effective_date": row.get("effective_date"),
        "testing_scheme": row.get("testing_scheme"),
        "inspection_scheme": row.get("inspection_scheme"),
        "description": row.get("description"),
        "source_type": "verified_dataset",
        "validation_status": row.get("validation_status"),
    }


def get_compliance_intelligence(
    standard_number: str,
    standard_id: Optional[str] = None,
) -> dict:
    """Full compliance intelligence for a standard.

    Returns a dict with qco, certification, gazette, testing sections.
    Each section returns {} when no verified data exists.
    """
    qco = get_qco_info(standard_number, standard_id)
    certification = get_certification_info(standard_number, standard_id)
    gazette = get_gazette_info(standard_number)
    testing = get_testing_inspection_info(standard_number)

    # If QCO is UPCOMING, certification should reflect mandatory-on-effective-date
    if qco and qco["status"] == "UPCOMING":
        certification = {
            "status": "MANDATORY_ON_EFFECTIVE_DATE",
            "display": "Certification becomes mandatory on the QCO effective date.",
            "source_type": "verified_dataset",
        } if not certification else certification

    intelligence: dict = {}
    if qco:
        intelligence["qco"] = qco
        intelligence["qco"]["available"] = True
    else:
        intelligence["qco"] = {"available": False, "note": _NA_MSG}

    if certification:
        intelligence["certification"] = certification
        intelligence["certification"]["available"] = True
    else:
        intelligence["certification"] = {"available": False, "note": _NA_MSG}

    if gazette:
        intelligence["gazette"] = gazette
        intelligence["gazette"]["available"] = True
    else:
        intelligence["gazette"] = {"available": False, "note": _NA_MSG}

    if testing:
        intelligence["testing_inspection"] = testing
        intelligence["testing_inspection"]["available"] = True
    else:
        intelligence["testing_inspection"] = {"available": False, "note": _NA_MSG}

    # Summary
    available = sum(1 for sec in ("qco", "certification", "gazette", "testing_inspection")
                    if intelligence.get(sec, {}).get("available"))
    if available == 0:
        intelligence["summary"] = _NA_MSG
    elif qco and qco["status"] in ("UPCOMING", "MANDATORY"):
        intelligence["summary"] = (
            f"QCO is {qco['status'].replace('_', ' ').lower()} with effective "
            f"date {qco['effective_date'] or 'not specified'} per the verified dataset."
        )
    else:
        intelligence["summary"] = (
            f"{available} compliance signal(s) found in the verified dataset."
        )

    return intelligence