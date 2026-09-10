"""Identify the Recall@1 failure cases from the Phase 6 audit."""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.retrieval.pipeline import run_pipeline

DATA = Path(r"D:\testing2\ManakSetu_BIS_Data_V04_FINAL\ManakSetu_BIS_Data_V04_FINAL")
BENCH = DATA / "09_evaluation" / "benchmark.csv"

with open(BENCH, encoding="utf-8") as f:
    bench = list(csv.DictReader(f))

failures = []
for idx, row in enumerate(bench):
    q = row.get("query", "")
    exp_raw = row.get("expected_standard_ids", "")
    if not q or not exp_raw:
        continue
    exp_ids = [x.strip() for x in re.split(r"[;,]", exp_raw) if x.strip()]
    if not exp_ids:
        continue

    pr = run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
    
    # Check base rank
    rank_base = 0
    for i, rec in enumerate(pr.recommendations, 1):
        std = rec["standard"]
        if std.get("standard_id") in exp_ids or std.get("standard_number") in exp_ids:
            rank_base = i
            break

    if rank_base != 1:
        top3_base = [(r["standard"]["standard_number"], r["standard"]["title"][:80]) for r in pr.recommendations[:3]]
        failures.append({
            "idx": idx,
            "query": q[:200],
            "expected": exp_raw,
            "rank_base": rank_base,
            "top3_base": top3_base,
        })

print(f"\n{'='*80}")
print(f"RECALL@1 FAILURE ANALYSIS: {len(failures)} / {len(bench)} queries missed gold at rank #1")
print(f"{'='*80}\n")

for f in failures:
    print(f"Query #{f['idx']}: {f['query'][:150]}")
    print(f"  Expected: {f['expected']} | Rank: {f['rank_base']}")
    print(f"  Top 3 base:")
    for rank, (sn, title) in enumerate(f["top3_base"], 1):
        marker = " <<<" if f['expected'] in sn else ""
        print(f"    #{rank}: {sn} — {title}{marker}")
    print()
