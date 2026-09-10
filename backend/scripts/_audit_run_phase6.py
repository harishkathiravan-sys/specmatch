"""Phase 6.5 audit — run Phase 6 pipeline against the same benchmark as Phase 4.

Captures full per-query detail (lexical/semantic/metadata/coverage/final scores)
for failure analysis. Writes:
  - phase6_5_metrics.csv  (aggregate metrics + dataset audit)
  - phase6_5_failures.csv (20+ failure examples, Phase4-vs-Phase6)
"""
import csv
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app.retrieval.pipeline import run_pipeline

DATA = BASE.parent / "ManakSetu_BIS_Data_V04_FINAL" / "ManakSetu_BIS_Data_V04_FINAL"
BENCH = DATA / "09_evaluation" / "benchmark.csv"
GOLD = DATA / "09_evaluation" / "gold_labels.csv"
HARD_CSV = DATA / "09_evaluation" / "hard_cases.csv"
HNP = DATA / "05_retrieval" / "hard_negative_pairs.csv"
SN_Q = DATA / "10_synthetic" / "synthetic_queries.csv"

OUT_ = BASE / "scripts"


def _recall_at_k(ranks, k):
    return sum(1 for r in ranks if 0 < r <= k) / len(ranks) if ranks else 0.0


def _mrr(ranks):
    return sum(1.0 / r for r in ranks if r > 0) / len(ranks) if ranks else 0.0


def _load(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _hit_rank(recs, exp_ids):
    for i, rec in enumerate(recs, 1):
        std = rec["standard"] if isinstance(rec, dict) else rec.to_dict()["standard"]
        sid = std.get("standard_id", "")
        sn = std.get("standard_number", "")
        if sid in exp_ids or sn in exp_ids:
            return i
    return 0


def main(limit=None, extra={"phase4_reranked": None}):
    bench = _load(BENCH)
    gold = _load(GOLD)
    hard_cases = _load(HARD_CSV)
    hnp = _load(HNP)

    if limit:
        bench = bench[:limit]

    # ---- Dataset audit section ----
    audit = {
        "dataset_version": "V0.4",
        "corpus_standards": 24132,
        "benchmark_rows": len(bench),
        "gold_rows": len(gold),
        "gold_per_query": Counter(g.get("label") for g in gold),
        "benchmark_validation": Counter(b.get("validation_status") for b in bench),
        "benchmark_difficulty": Counter(b.get("difficulty") for b in bench),
        "benchmark_source": Counter(b.get("source_type") for b in bench),
        "synthetic_flag": Counter(b.get("synthetic_flag") for b in bench),
        "multi_expected": sum(
            1 for b in bench
            if len([x for x in re.split(r"[;,]", b.get("expected_standard_ids", "")) if x.strip()]) > 1
        ),
        "gold_verification": Counter(g.get("annotator") for g in gold),
        "hard_cases_rows": len(hard_cases),
        "hard_negative_pairs_rows": len(hnp),
        "hard_case_expected_action": Counter(h.get("expected_action") for h in hard_cases),
    }

    ranks_p6 = []
    ranks_p6_final = []
    failures = []
    coverage_scores = []
    latency_p50_p95 = []
    t0 = time.time()
    first_50_times = []

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
        if len(first_50_times) < 200:
            first_50_times.append(dt)

        # Rank under base recommendations (reranker order — what Phase 6 eval measured)
        rank_base = _hit_rank(pr.recommendations, exp_ids)
        # Rank under Phase 6 final_score order
        rank_final = _hit_rank(pr.phase6_recommendations, exp_ids)
        ranks_p6.append(rank_base)
        ranks_p6_final.append(rank_final)

        if pr.phase6_recommendations:
            d = pr.phase6_recommendations[0].to_dict() if hasattr(pr.phase6_recommendations[0], "to_dict") else pr.phase6_recommendations[0]
            cov = (d.get("requirement_coverage") or {}).get("score", 0.0)
            coverage_scores.append(cov)

        # Failure capture: Phase 4 (reranked) hit at 1 but Phase 6 missed at 1
        p4_rank = (extra.get("phase4_reranked") or {}).get(row.get("query_id"), 0)
        if len(failures) < 40 and (p4_rank == 1 and rank_base != 1):
            recs = pr.phase6_recommendations
            top = recs[0].to_dict() if recs and hasattr(recs[0], "to_dict") else (recs[0] if recs else {})
            std = top.get("standard", {})
            failures.append({
                "query_id": row.get("query_id"),
                "query": q[:300],
                "expected_standard_ids": exp_raw,
                "phase4_rank": p4_rank,
                "phase6_base_rank": rank_base,
                "phase6_final_rank": rank_final,
                "phase6_top_result": f"{std.get('standard_number','')} — {std.get('title','')[:90]}",
                "lexical_score": round(float(top.get("lexical_score") or 0.0), 4),
                "semantic_score": round(float(top.get("semantic_score") or 0.0), 4),
                "metadata_score": round(float(top.get("metadata_score") or 0.0), 4),
                "coverage": round(float((top.get("requirement_coverage") or {}).get("score") or 0.0), 4),
                "contradictions": "|".join(c.get("reason", "")[:80] for c in top.get("contradictions") or []),
                "contradiction_penalty": round(float(top.get("contradiction_penalty") or 0.0), 4),
                "lifecycle_penalty": 0.0,
                "final_score": round(float(top.get("relevance_score") or 0.0), 4),
                "confidence": top.get("confidence"),
            })
        if idx % 500 == 0:
            print(f"  ... {idx} queries", flush=True)

    elapsed_ms = (time.time() - t0) * 1000

    p50 = sorted(first_50_times)[len(first_50_times) // 2] if first_50_times else 0
    p95_idx = min(len(first_50_times) - 1, int(len(first_50_times) * 0.95))
    p95 = sorted(first_50_times)[p95_idx] if first_50_times else 0

    metrics = {
        "benchmark_queries": len(ranks_p6),
        "recall_at_1_base": round(_recall_at_k(ranks_p6, 1), 4),
        "recall_at_5_base": round(_recall_at_k(ranks_p6, 5), 4),
        "recall_at_10_base": round(_recall_at_k(ranks_p6, 10), 4),
        "mrr_base": round(_mrr(ranks_p6), 4),
        "recall_at_1_final": round(_recall_at_k(ranks_p6_final, 1), 4),
        "recall_at_5_final": round(_recall_at_k(ranks_p6_final, 5), 4),
        "recall_at_10_final": round(_recall_at_k(ranks_p6_final, 10), 4),
        "mrr_final": round(_mrr(ranks_p6_final), 4),
        "avg_coverage": round(sum(coverage_scores) / len(coverage_scores), 4) if coverage_scores else 0.0,
        "total_ms": round(elapsed_ms, 1),
        "avg_ms_query": round(elapsed_ms / max(len(ranks_p6), 1), 1),
        "p50_ms_query": round(p50, 1),
        "p95_ms_query": round(p95, 1),
    }

    OUT_.mkdir(parents=True, exist_ok=True)
    (OUT_ / "phase6_5_dataset_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_ / "phase6_5_failures.json").write_text(json.dumps({"failures": failures, "metrics": metrics}, indent=2, ensure_ascii=False), encoding="utf-8")

    # metrics.csv
    with open(OUT_ / "phase6_5_metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "notes"])
        for k, v in metrics.items():
            w.writerow([k, v, ""])
        w.writerow(["dataset", "V0.4", "corpus=24132 standards"])
        w.writerow(["dataset_queries", len(bench), "all synthetic"])
        w.writerow(["dataset_gold_per_query", "1", "single gold label per query"])
        w.writerow(["phase4_recall_at_1", (extra.get("phase4_reranked_metrics") or {}).get("recall_at_1"), "from _audit_run_baseline.py (reranked mode)"])
        w.writerow(["phase4_recall_at_5", (extra.get("phase4_reranked_metrics") or {}).get("recall_at_5"), ""])
        w.writerow(["phase4_mrr", (extra.get("phase4_reranked_metrics") or {}).get("mrr"), ""])

    # failures.csv
    with open(OUT_ / "phase6_5_failures.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "query_id", "query", "expected_standard_ids", "phase4_rank", "phase6_base_rank",
            "phase6_final_rank", "phase6_top_result", "lexical_score", "semantic_score",
            "metadata_score", "coverage", "contradictions", "contradiction_penalty",
            "lifecycle_penalty", "final_score", "confidence",
        ])
        w.writeheader()
        for fr in failures:
            w.writerow(fr)

    print(json.dumps({"metrics": metrics, "audit": audit, "failures": len(failures)}, indent=2))
    print(f"Saved metrics csv + failures csv + dataset audit to {OUT_}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    main(limit=args.limit)