"""Analyze ALL Recall@1 failure cases — queries where gold standard is NOT at rank 1.

Unlike the main audit script, this captures every query where Phase 6 missed rank #1.
Outputs failures_analysis.json with per-query details.
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app.retrieval.pipeline import run_pipeline

DATA = BASE.parent / "ManakSetu_BIS_Data_V04_FINAL" / "ManakSetu_BIS_Data_V04_FINAL"
BENCH = DATA / "09_evaluation" / "benchmark.csv"
OUT_ = BASE / "scripts" / "recall1_failures.json"


def _hit_rank(recs, exp_ids):
    for i, rec in enumerate(recs, 1):
        std = rec["standard"] if isinstance(rec, dict) else rec.to_dict()["standard"]
        sid = std.get("standard_id", "")
        sn = std.get("standard_number", "")
        if sid in exp_ids or sn in exp_ids:
            return i
    return 0


def main(limit=2000):
    bench = list(csv.DictReader(open(BENCH, encoding="utf-8")))

    if limit:
        bench = bench[:limit]

    all_ranks = []
    failures = []
    t0 = time.time()

    for idx, row in enumerate(bench):
        q = row.get("query", "")
        exp_raw = row.get("expected_standard_ids", "")
        if not q or not exp_raw:
            continue
        exp_ids = [x.strip() for x in re.split(r"[;,]", exp_raw) if x.strip()]
        if not exp_ids:
            continue

        tq = time.time()
        pr = run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        dt = (time.time() - tq) * 1000

        rank_base = _hit_rank(pr.recommendations, exp_ids)
        rank_final = _hit_rank(pr.phase6_recommendations, exp_ids)
        all_ranks.append(rank_base)

        if rank_base != 1:
            # Capture top-3 detail for analysis
            top3 = []
            for rec in (pr.phase6_recommendations or pr.recommendations)[:3]:
                std = rec["standard"] if isinstance(rec, dict) else rec.to_dict().get("standard", {})
                top3.append({
                    "standard_number": std.get("standard_number", ""),
                    "title": std.get("title", "")[:100],
                    "relevance_score": round(float(rec.get("relevance_score", 0) if isinstance(rec, dict) else rec.to_dict().get("relevance_score", 0)), 4),
                })
            
            failures.append({
                "query_id": row.get("query_id", str(idx)),
                "query": q[:300],
                "expected_ids": exp_raw,
                "rank_base": rank_base,
                "rank_final": rank_final,
                "latency_ms": round(dt, 1),
                "top3": top3,
            })

        if idx % 500 == 0:
            print(f"  ... {idx} queries ({len(failures)} failures so far)", flush=True)

    elapsed = time.time() - t0

    # Summary
    n = len(all_ranks)
    recall1 = sum(1 for r in all_ranks if r == 1) / n if n else 0
    recall5 = sum(1 for r in all_ranks if 0 < r <= 5) / n if n else 0
    recall10 = sum(1 for r in all_ranks if 0 < r <= 10) / n if n else 0

    # Failure breakdown
    not_in_top10 = [f for f in failures if f["rank_base"] == 0]
    in_top5_not_1 = [f for f in failures if 1 < f["rank_base"] <= 5]
    in_top10_not_1 = [f for f in failures if 5 < f["rank_base"] <= 10]

    result = {
        "summary": {
            "total_queries": n,
            "recall_at_1": round(recall1, 4),
            "recall_at_5": round(recall5, 4),
            "recall_at_10": round(recall10, 4),
            "total_failures": len(failures),
            "not_in_top10": len(not_in_top10),
            "in_top5_not_1": len(in_top5_not_1),
            "in_top10_not_1": len(in_top10_not_1),
            "elapsed_s": round(elapsed, 1),
        },
        "failure_cause_analysis": {
            "not_in_top10_root_cause": "Gold standard not retrieved by FTS — likely corpus gap (standard exists but FTS keyword mismatch)",
            "in_top10_not_1_root_cause": "Phase 6 re-ranking moved gold from top position — scoring or penalty issue",
        },
        "failures": failures,
    }

    OUT_.parent.mkdir(parents=True, exist_ok=True)
    OUT_.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*80}")
    print(f"RECALL@1 FAILURE ANALYSIS: {len(failures)} / {n} queries missed rank #1")
    print(f"{'='*80}")
    print(f"  Not in top 10 (FTS gap):    {len(not_in_top10)}")
    print(f"  In top 5 but not #1:         {len(in_top5_not_1)}")
    print(f"  In top 10 but not #1 (6-10): {len(in_top10_not_1)}")
    print()
    for f in failures[:30]:
        marker = "OUT_OF_T10" if f["rank_base"] == 0 else f"rank={f['rank_base']}"
        print(f"  [{marker}] {f['query'][:100]}")
        print(f"    Expected: {f['expected_ids']}")
        if f["top3"]:
            print(f"    Top result: {f['top3'][0]['standard_number']} — {f['top3'][0]['title']}")
        print()
    print(f"\nFull results saved to {OUT_}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2000)
    args = ap.parse_args()
    main(limit=args.limit)
