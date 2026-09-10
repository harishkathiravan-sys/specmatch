"""Final golden test validation — using actual benchmark queries."""
import csv
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.retrieval.pipeline import run_pipeline

BENCH = Path(__file__).resolve().parent.parent.parent / "ManakSetu_BIS_Data_V04_FINAL" / "ManakSetu_BIS_Data_V04_FINAL" / "09_evaluation" / "benchmark.csv"
bench = list(csv.DictReader(open(BENCH, encoding="utf-8")))

# Pick 5 diverse queries from the actual benchmark
indices = [0, 100, 500, 1000, 1500]
tests = [(bench[i], bench[i].get("query", "")) for i in indices if i < len(bench)]

print("Final Validation — Actual Benchmark Queries")
print("=" * 60)
passed = 0
total = 0
for row, q in tests:
    exp_raw = row.get("expected_standard_ids", "")
    exp_ids = [x.strip() for x in re.split(r"[;,]", exp_raw) if x.strip()]
    if not q or not exp_ids:
        continue
    total += 1
    pr = run_pipeline(q, top_k=5, max_candidates=40, phase6=True)
    recs = pr.phase6_recommendations or pr.recommendations
    rank = 0
    top_sn = ""
    for i, r in enumerate(recs, 1):
        s = r["standard"] if isinstance(r, dict) else r.to_dict()["standard"]
        sn = s.get("standard_number", "")
        sid = s.get("standard_id", "")
        top_sn = sn
        if sid in exp_ids or sn in exp_ids:
            rank = i
            break
    hit = rank == 1
    if hit:
        passed += 1
    status = "PASS" if hit else "FAIL"
    print("  [%s] rank=%d top=%s" % (status, rank, top_sn[:50]))
    print("        query=%s" % q[:70])
    print("        expected=%s" % exp_raw[:40])

print("\n%d/%d validation queries hit rank #1" % (passed, total))
