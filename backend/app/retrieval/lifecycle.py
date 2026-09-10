"""Lifecycle intelligence — Phase 6.9.

Uses lifecycle_events.csv data plus standards.status to determine:
  - publication event
  - revision
  - withdrawal
  - supersession
  - current-status certainty

Never infers current status merely from inventory presence.
"""

from __future__ import annotations

import re
from typing import Optional

from app.database import get_db


_NA_MSG = "Current lifecycle status is not confirmed in the current verified dataset."


def _fetch_rows(sql: str, params: tuple) -> list[dict]:
    try:
        with get_db() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def _standard_id_for(standard_number: str) -> Optional[str]:
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT standard_id FROM standards WHERE standard_number = ? LIMIT 1",
                (standard_number,),
            ).fetchone()
            if row:
                return row["standard_id"]
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


def get_lifecycle_intelligence(
    standard_number: str,
    standard_id: Optional[str] = None,
) -> dict:
    """Lifecycle intelligence for a standard.

    Returns:
      {
        "current_status": ...,
        "status_certainty": "confirmed" | "unknown",
        "events": [...],
        "summary": "..."
      }
    """
    sid = standard_id or _standard_id_for(standard_number)

    # 1. Standards table current_status
    status = "UNKNOWN_CURRENT_STATUS"
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT current_status, publication_year, publication_date FROM standards "
                "WHERE standard_number = ? OR standard_id = ? LIMIT 1",
                (standard_number, sid or ""),
            ).fetchone()
            if row:
                status = row["current_status"] or "UNKNOWN_CURRENT_STATUS"
                pub_year = row["publication_year"]
                pub_date = row["publication_date"]
    except Exception:
        pub_year = pub_date = None

    status_certainty = "confirmed" if status not in ("UNKNOWN_CURRENT_STATUS", None, "") else "unknown"

    # 2. Lifecycle events
    events: list[dict] = []
    if sid:
        for r in _fetch_rows(
            "SELECT event_type, event_date, source, validation_status, notes "
            "FROM lifecycle_events WHERE entity_id = ? ORDER BY event_date",
            (sid,),
        ):
            events.append({
                "type": r["event_type"],
                "date": r["event_date"],
                "source": r["source"],
                "validation_status": r["validation_status"],
                "notes": r["notes"],
            })
    # Also try by standard_number match
    if not events:
        for r in _fetch_rows(
            "SELECT event_type, event_date, source, validation_status, notes "
            "FROM lifecycle_events WHERE entity_id LIKE ? ORDER BY event_date",
            ("%" + standard_number.replace(" ", "") + "%",),
        ):
            events.append({
                "type": r["event_type"],
                "date": r["event_date"],
                "source": r["source"],
                "validation_status": r["validation_status"],
                "notes": r["notes"],
            })

    # 3. Interpret
    interpretation: dict = {}
    event_types = {e["type"].upper() for e in events}

    if "WITHDRAWN" in event_types or "REVOKED" in event_types:
        interpretation["status"] = "WITHDRAWN"
        interpretation["certainty"] = "confirmed"
        interpretation["summary"] = "This standard has a withdrawal/revocation event in the verified dataset."
    elif "SUPERSEDED" in event_types:
        interpretation["status"] = "SUPERSEDED"
        interpretation["certainty"] = "confirmed"
        interpretation["summary"] = "This standard has a supersession event in the verified dataset."
    elif "REVISED" in event_types or "REVISION" in event_types:
        interpretation["status"] = "REVISED"
        interpretation["certainty"] = "confirmed"
        interpretation["summary"] = "This standard has a revision event in the verified dataset."
    elif "PUBLISHED" in event_types:
        interpretation["status"] = "PUBLISHED"
        interpretation["certainty"] = "confirmed"
        interpretation["summary"] = "Publication event recorded in the verified dataset."
    else:
        interpretation["status"] = "UNKNOWN_CURRENT_STATUS"
        interpretation["certainty"] = "unknown"
        interpretation["summary"] = _NA_MSG

    return {
        "current_status": status,
        "status_certainty": status_certainty,
        "interpretation": interpretation,
        "events": events[:10],
        "publication_year": pub_year,
        "publication_date": pub_date,
        "summary": interpretation["summary"],
    }


def lifecycle_penalty(standard_number: str, standard_id: Optional[str] = None) -> float:
    """Small penalty when status is UNKNOWN — recommendations prefer confirmed current."""
    try:
        li = get_lifecycle_intelligence(standard_number, standard_id)
        if li.get("interpretation", {}).get("status") in ("WITHDRAWN", "SUPERSEDED"):
            return 0.25
        if li["interpretation"]["status"] == "UNKNOWN_CURRENT_STATUS":
            return 0.05  # minor uncertainty penalty, do not silently remove
        return 0.0
    except Exception:
        return 0.0