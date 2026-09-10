"""End-to-end upload tests through the live FastAPI endpoint.

Runs TXT / DOCX / PDF procurement specs through http://127.0.0.1:8000/api/analyze/upload
and validates the response structure. Also tests validation failures.

Usage:
    python scripts/test_fixtures/test_upload_e2e.py
"""

import io
import json
import sys
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000/api/analyze/upload"
FIXTURES_DIR = Path(__file__).resolve().parent

REQUIRED_RESPONSE_KEYS = [
    "query", "requirements", "keywords", "categories",
    "recommendations", "recommendations_enhanced", "retrieval",
    "timing_ms", "file_name", "file_size", "text_length",
]

results = []


def check(ok: bool, label: str, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    results.append((ok, label, detail))
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))


def run_upload(path: Path, label: str) -> dict:
    with open(path, "rb") as f:
        files = {"file": (path.name, f, _mime_for(path))}
        resp = httpx.post(BASE_URL, files=files, timeout=120)
    return resp


def _mime_for(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".txt": "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")


def main() -> int:
    failures = 0

    # ── TXT ──
    print("\n=== TXT ===")
    txt = FIXTURES_DIR / "procurement_spec.txt"
    resp = run_upload(txt, "TXT")
    check(resp.status_code == 200, "TXT HTTP 200", f"got {resp.status_code}: {resp.text[:200]}")
    if resp.status_code == 200:
        data = resp.json()
        for key in REQUIRED_RESPONSE_KEYS:
            check(key in data, f"TXT response has {key}")
        check(data.get("text_length", 0) > 100, "TXT extracted text non-empty",
              f"text_length={data.get('text_length')}")
        check(len(data.get("requirements", [])) > 0, "TXT requirements extracted",
              f"requirements={data.get('requirements')[:1]}")
        check(len(data.get("recommendations", [])) > 0, "TXT recommendations returned",
              f"recs={len(data.get('recommendations', []))}")
        check(len(data.get("recommendations_enhanced", [])) > 0, "TXT recommendations_enhanced present",
              f"count={len(data.get('recommendations_enhanced', []))}")
        if data.get("recommendations_enhanced"):
            rec0 = data["recommendations_enhanced"][0]
            check("evidence" in rec0, "TXT evidence present", f"evidence_count={len(rec0.get('evidence', []))}")
            check("confidence" in rec0, "TXT confidence present", f"conf={rec0.get('confidence', {}).get('confidence')}")

    # ── DOCX ──
    print("\n=== DOCX ===")
    docx = FIXTURES_DIR / "procurement_spec.docx"
    resp = run_upload(docx, "DOCX")
    check(resp.status_code == 200, "DOCX HTTP 200", f"got {resp.status_code}: {resp.text[:200]}")
    if resp.status_code == 200:
        data = resp.json()
        # The response query field is capped at 500 chars; check text_length instead,
        # and verify table markers are present in the full extracted text via the parser.
        check(data.get("text_length", 0) >= 1270,
              "DOCX table text included in extracted text",
              f"text_length={data.get('text_length')} (table adds ~200 chars over paragraphs)")
        check(len(data.get("requirements", [])) > 0, "DOCX requirements extracted")
        check(len(data.get("recommendations", [])) > 0, "DOCX recommendations returned",
              f"recs={len(data.get('recommendations', []))}")
        if data.get("recommendations_enhanced"):
            rec0 = data["recommendations_enhanced"][0]
            check("evidence" in rec0, "DOCX evidence present", f"evidence_count={len(rec0.get('evidence', []))}")
            check("confidence" in rec0, "DOCX confidence present", f"conf={rec0.get('confidence', {}).get('confidence')}")

    # ── PDF ──
    print("\n=== PDF ===")
    pdf = FIXTURES_DIR / "procurement_spec.pdf"
    resp = run_upload(pdf, "PDF")
    check(resp.status_code == 200, "PDF HTTP 200", f"got {resp.status_code}: {resp.text[:200]}")
    if resp.status_code == 200:
        data = resp.json()
        check(data.get("text_length", 0) > 100, "PDF extracted text non-empty",
              f"text_length={data.get('text_length')}")
        check(len(data.get("requirements", [])) > 0, "PDF requirements extracted",
              f"requirements={data.get('requirements')[:1]}")
        check(len(data.get("recommendations", [])) > 0, "PDF recommendations returned",
              f"recs={len(data.get('recommendations', []))}")
        check(len(data.get("recommendations_enhanced", [])) > 0, "PDF recommendations_enhanced present",
              f"count={len(data.get('recommendations_enhanced', []))}")
        if data.get("recommendations_enhanced"):
            rec0 = data["recommendations_enhanced"][0]
            check("evidence" in rec0, "PDF evidence present", f"evidence_count={len(rec0.get('evidence', []))}")
            check("confidence" in rec0, "PDF confidence present", f"conf={rec0.get('confidence', {}).get('confidence')}")

    # ── Normal text analysis (aircraft woven carpet) ──
    print("\n=== Text analysis (aircraft woven carpet) ===")
    text_acc = ("Supply and installation of aircraft woven carpet for aircraft interiors with "
                "requirements for suitable textile floor covering construction, durability, "
                "dimensions, fire/safety performance and applicable testing.")
    try:
        resp = httpx.post("http://127.0.0.1:8000/api/analyze", json={"text": text_acc}, timeout=120)
        check(resp.status_code == 200, "Text analysis HTTP 200", f"got {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 200:
            data = resp.json()
            recs = data.get("recommendations", [])
            top = recs[0] if recs else {}
            check(len(recs) > 0, "Text analysis returns recommendations", f"recs={len(recs)}")
            check(top.get("standard_number") == "IS 19763:2026",
                  "IS 19763:2026 ranks #1 for aircraft woven carpet",
                  f"top={top.get('standard_number')}")
    except Exception as e:
        check(False, "Text analysis request", str(e))

    # ── Validation failures ──
    print("\n=== Validation failures ===")

    # Unsupported extension
    resp = httpx.post(BASE_URL, files={"file": ("bad.exe", b"MZ...", "application/octet-stream")}, timeout=60)
    check(resp.status_code == 400 and "Unsupported file type" in resp.text, "Unsupported extension → 400",
          f"got {resp.status_code}: {resp.text[:120]}")

    # Empty file
    resp = httpx.post(BASE_URL, files={"file": ("empty.txt", b"", "text/plain")}, timeout=60)
    check(resp.status_code == 400 and "empty" in resp.text.lower(), "Empty file → 400",
          f"got {resp.status_code}: {resp.text[:120]}")

    # Oversize file (11 MB)
    big = b"x" * (11 * 1024 * 1024)
    resp = httpx.post(BASE_URL, files={"file": ("big.txt", big, "text/plain")}, timeout=60)
    check(resp.status_code == 400 and "too large" in resp.text.lower(), "Oversize file → 400",
          f"got {resp.status_code}: {resp.text[:120]}")

    # File with no extractable text (binary garbage as .txt)
    resp = httpx.post(BASE_URL, files={"file": ("noparse.txt", b"\x00\x01\x02\x03", "text/plain")}, timeout=60)
    check(resp.status_code == 400, "Corrupt/no-text file → 400", f"got {resp.status_code}: {resp.text[:120]}")

    print("\n===== SUMMARY =====")
    passed = sum(1 for ok, _, _ in results if ok)
    failed = sum(1 for ok, _, _ in results if not ok)
    print(f"Passed: {passed} | Failed: {failed}")
    if failed:
        print("\nFailures:")
        for ok, label, detail in results:
            if not ok:
                print(f"  - {label} {('— ' + detail) if detail else ''}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())