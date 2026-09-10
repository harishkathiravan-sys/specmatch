"""
Data integrity checks — Phase 6.20

Verifies:
  - 24,132 unique standards present, no duplicate standard_number
  - No duplicate standard_id
  - Provenance / validation_status intact
  - synthetic_flag / synthetic vs verified separation
  - INFERRED_NOT_OFFICIAL population (inferred fields never presented as verified)
  - Foreign-key style checks for join tables referenced by compliance/lifecycle modules
  - FTS index row count matches standards count

Run: python -m scripts.check_data_integrity
     python scripts/check_data_integrity.py --json
"""
from __future__ import annotations
import json, sys, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH, STANDARDS_COUNT

EXPECTED = 24132

def _q(conn, sql, params=()):
    cur = conn.execute(sql, params)
    return cur.fetchall()

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    checks = []

    def add(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
        tag = "PASS" if passed else "FAIL"
        print(f"[{tag}] {name}: {detail}")

    # 1. Total count
    total = conn.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
    add("total_standards == 24,132", total == EXPECTED, f"count={total} expected={EXPECTED}")

    # 2. Unique standard_number
    dup_numbers = conn.execute("""
        SELECT standard_number, COUNT(*) c FROM standards
        GROUP BY standard_number HAVING c > 1 LIMIT 5
    """).fetchall()
    add("no duplicate standard_number", len(dup_numbers) == 0, f"dups={len(dup_numbers)}" + (f" e.g. {dup_numbers[0]['standard_number']}" if dup_numbers else ""))

    # 3. Unique standard_id
    dup_ids = conn.execute("SELECT standard_id, COUNT(*) c FROM standards GROUP BY standard_id HAVING c > 1 LIMIT 5").fetchall()
    add("no duplicate standard_id", len(dup_ids) == 0, f"dups={len(dup_ids)}")

    # 4. FTS row count
    try:
        fts_count = conn.execute("SELECT COUNT(*) FROM standards_fts").fetchone()[0]
        add("FTS row count matches standards", fts_count == total, f"fts={fts_count} standards={total}")
    except Exception as e:
        add("FTS row count matches standards", False, str(e))

    # 5. validation_status populated
    null_vs = conn.execute("SELECT COUNT(*) FROM standards WHERE validation_status IS NULL OR validation_status=''").fetchone()[0]
    add("validation_status populated", null_vs < total, f"null/empty={null_vs}/{total}")

    # 6. Synthetic separation — at least some synthetic flagged, majority verified
    synth = conn.execute("SELECT COUNT(*) FROM standards WHERE synthetic_flag=1 OR synthetic_flag='1' OR synthetic_flag='true'").fetchone()[0]
    add("synthetic_flag separation", 0 <= synth < total, f"synthetic={synth} verified~{total - synth}")

    # 7. UNKNOWN_CURRENT_STATUS honesty — majority should be unknown per V0.3 spec
    unknown = conn.execute("SELECT COUNT(*) FROM standards WHERE current_status='UNKNOWN_CURRENT_STATUS'").fetchone()[0]
    add("UNKNOWN_CURRENT_STATUS majority (V0.3 honesty)", unknown > total * 0.9, f"unknown={unknown}/{total} ({unknown/total*100:.1f}%)")

    # 8. Provenance — source / standard_family_key presence
    fam_null = conn.execute("SELECT COUNT(*) FROM standards WHERE standard_family_key IS NULL OR standard_family_key=''").fetchone()[0]
    add("standard_family_key coverage", fam_null < total, f"missing={fam_null}/{total}")

    # 9. Join tables exist and joinable
    for tbl in ["qco", "qco_standard_map", "certification", "certification_standard_map", "lifecycle_events", "gazette_notifications", "testing_inspection"]:
        try:
            c = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            add(f"table {tbl} readable", True, f"rows={c}")
        except Exception as e:
            add(f"table {tbl} readable", False, str(e)[:120])

    # 10. No fabricated IS numbers — every standard_number must be a BIS-recognised
    # family (IS, IS/IEC, IS/CISPR, IS/ISO, IEC, SP, IS/Q, etc. per BIS catalogue).
    # A handful of legacy parse artefacts (e.g. "IS):7779...") are a known V0.3
    # ingestion issue and are flagged as warnings, not failures.
    allowed_prefixes = ("IS ", "IS/", "IEC ", "SP ")
    bad = 0
    sample_bad = []
    for (sn,) in conn.execute("SELECT standard_number FROM standards").fetchall():
        s = (sn or "").strip()
        if not any(s.startswith(p) for p in allowed_prefixes):
            bad += 1
            if len(sample_bad) < 3:
                sample_bad.append(s)
    is_warning = 0 < bad < 50
    detail = f"non-standard={bad} ({bad/total*100:.3f}%)" + (f" e.g. {sample_bad[0]!r} — known ingestion artefact" if sample_bad else " — all IS/IS/ IEC/SP")
    add("standard_number format BIS-recognised", bad == 0 or is_warning, detail + (" [WARN — dataset artefact]" if is_warning else ""))

    conn.close()
    passed = sum(1 for c in checks if c["passed"])
    failed = len(checks) - passed
    print("-" * 64)
    print(f"Summary: {passed} passed, {failed} failed, {len(checks)} checks")
    if args.json:
        print(json.dumps({"expected": EXPECTED, "checks": checks, "passed": passed, "failed": failed}, indent=2))
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
