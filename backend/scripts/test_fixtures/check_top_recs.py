"""Check which standard each upload format recommends at rank #1."""

import httpx
from pathlib import Path

BASE = "http://127.0.0.1:8000/api/analyze/upload"
FIXTURES = Path(r"D:\testing2\backend\scripts\test_fixtures")

for name in ["procurement_spec.txt", "procurement_spec.docx", "procurement_spec.pdf"]:
    p = FIXTURES / name
    resp = httpx.post(BASE, files={"file": (name, p.read_bytes())}, timeout=120)
    if resp.status_code != 200:
        print(f"{name}: HTTP {resp.status_code} {resp.text[:150]}")
        continue
    data = resp.json()
    recs = data.get("recommendations", [])
    top = recs[0] if recs else {}
    top_enh = data.get("recommendations_enhanced", [])
    te = top_enh[0] if top_enh else {}
    print(f"{name}:")
    print(f"  top rec: {top.get('standard_number')} — {str(top.get('title', ''))[:60]}")
    print(f"  match_score: {top.get('match_score')}")
    print(
        f"  enhanced rank1: {te.get('standard', {}).get('standard_number')} "
        f"conf={te.get('confidence', {}).get('confidence')} "
        f"evidence={len(te.get('evidence', []))}"
    )
    print(f"  top5: {[r.get('standard_number') for r in recs[:5]]}")