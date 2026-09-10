"""Phase 6 ablation study — which scoring signals actually help ranking?

Tests 6 configurations on a 200-query sample:
  A. Lexical only (metadata weight = 0, Phase 6 off)
  B. Lexical + metadata (no Phase 6)
  C. Full Phase 6 (baseline)
  D. Full minus contradiction penalty
  E. Full minus lifecycle penalty
  F. Full minus both penalties

Reports Recall@1/5/10, MRR, and avg latency for each.
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import app.retrieval.fusion as fusion_mod
import app.retrieval.phase6_integration as p6_mod
from app.retrieval.pipeline import run_pipeline

DATA = BASE.parent / "ManakSetu_BIS_Data_V04_FINAL" / "ManakSetu_BIS_Data_V04_FINAL"
BENCH = DATA / "09_evaluation" / "benchmark.csv"
OUT_ = BASE / "scripts" / "phase6_5_ablation.json"


def _recall_at_k(ranks, k):
    return sum(1 for r in ranks if 0 < r <= k) / len(ranks) if ranks else 0.0


def _mrr(ranks):
    return sum(1.0 / r for r in ranks if r > 0) / len(ranks) if ranks else 0.0


def _rank(recs, exp_ids):
    for i, rec in enumerate(recs, 1):
        std = rec["standard"] if isinstance(rec, dict) else rec.to_dict()["standard"]
        if std.get("standard_id") in exp_ids or std.get("standard_number") in exp_ids:
            return i
    return 0


def _run_variant(name, bench_rows, exp_lookup, run_fn):
    """Run a variant and compute metrics."""
    ranks = []
    latencies = []
    t0 = time.time()
    for row in bench_rows:
        q = row.get("query", "")
        exp_raw = row.get("expected_standard_ids", "")
        if not q or not exp_raw:
            continue
        exp_ids = exp_lookup.get(row.get("query_id"), [])
        if not exp_ids:
            continue

        tq = time.time()
        pr = run_fn(q)
        dt = (time.time() - tq) * 1000
        latencies.append(dt)

        # Get rank from phase6_recommendations if available, else recommendations
        recs = getattr(pr, "phase6_recommendations", None) or pr.recommendations
        r = _rank(recs, exp_ids)
        ranks.append(r)

    elapsed = time.time() - t0
    n = len(ranks)
    sorted_lat = sorted(latencies)
    p50 = sorted_lat[n // 2] if n else 0
    p95 = sorted_lat[min(n - 1, int(n * 0.95))] if n else 0

    return {
        "name": name,
        "queries": n,
        "recall_at_1": round(_recall_at_k(ranks, 1), 4),
        "recall_at_5": round(_recall_at_k(ranks, 5), 4),
        "recall_at_10": round(_recall_at_k(ranks, 10), 4),
        "mrr": round(_mrr(ranks), 4),
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 1),
        "p50_latency_ms": round(p50, 1),
        "p95_latency_ms": round(p95, 1),
        "total_s": round(elapsed, 1),
    }


def main(limit=200):
    rows = list(csv.DictReader(open(BENCH, encoding="utf-8")))[:limit]
    exp_lookup = {}
    for row in rows:
        exp_ids = [x.strip() for x in re.split(r"[;,]", row.get("expected_standard_ids", "")) if x.strip()]
        if exp_ids:
            exp_lookup[row.get("query_id")] = exp_ids

    print(f"Ablation study: {limit} queries\n")

    # A. Lexical only (Phase 6 OFF, metadata weight = 0)
    def run_lexical_only(q):
        old_mw = fusion_mod.METADATA_WEIGHT
        fusion_mod.METADATA_WEIGHT = 0.0
        try:
            return run_pipeline(q, top_k=10, max_candidates=40, phase6=False)
        finally:
            fusion_mod.METADATA_WEIGHT = old_mw

    # B. Lexical + metadata (Phase 6 OFF)
    def run_lex_meta(q):
        return run_pipeline(q, top_k=10, max_candidates=40, phase6=False)

    # C. Full Phase 6 (baseline)
    def run_full(q):
        return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)

    # D. Full minus contradiction penalty
    def run_no_contra(q):
        orig = p6_mod.contradiction_penalty
        p6_mod.contradiction_penalty = lambda *a, **k: 0.0
        try:
            return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        finally:
            p6_mod.contradiction_penalty = orig

    # E. Full minus lifecycle penalty
    def run_no_lifecycle(q):
        orig = p6_mod.lifecycle_penalty
        p6_mod.lifecycle_penalty = lambda *a, **k: 0.0
        try:
            return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        finally:
            p6_mod.lifecycle_penalty = orig

    # F. Full minus both penalties
    def run_no_penalties(q):
        orig_contra = p6_mod.contradiction_penalty
        orig_life = p6_mod.lifecycle_penalty
        p6_mod.contradiction_penalty = lambda *a, **k: 0.0
        p6_mod.lifecycle_penalty = lambda *a, **k: 0.0
        try:
            return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        finally:
            p6_mod.contradiction_penalty = orig_contra
            p6_mod.lifecycle_penalty = orig_life

    variants = [
        ("A_lexical_only", run_lexical_only),
        ("B_lexical_metadata", run_lex_meta),
        ("C_full_phase6", run_full),
        ("D_no_contradiction", run_no_contra),
        ("E_no_lifecycle", run_no_lifecycle),
        ("F_no_penalties", run_no_penalties),
    ]

    results = []
    for name, fn in variants:
        print(f"  Running {name}...", end="", flush=True)
        r = _run_variant(name, rows, exp_lookup, fn)
        results.append(r)
        print(f" R@1={r['recall_at_1']}, MRR={r['mrr']}, avg={r['avg_latency_ms']}ms")

    # Summary table
    print(f"\n{'='*80}")
    print(f"{'Variant':<25} {'Queries':>7} {'R@1':>7} {'R@5':>7} {'R@10':>7} {'MRR':>7} {'Avg(ms)':>8} {'P95(ms)':>8}")
    print(f"{'-'*80}")
    for r in results:
        print(f"{r['name']:<25} {r['queries']:>7} {r['recall_at_1']:>7.4f} {r['recall_at_5']:>7.4f} "
              f"{r['recall_at_10']:>7.4f} {r['mrr']:>7.4f} {r['avg_latency_ms']:>8.1f} {r['p95_latency_ms']:>8.1f}")

    # Key deltas
    baseline = next(r for r in results if r["name"] == "C_full_phase6")
    print(f"\n{'='*80}")
    print("KEY COMPARISONS vs Full Phase 6 baseline:")
    for r in results:
        if r["name"] == "C_full_phase6":
            continue
        delta_r1 = r["recall_at_1"] - baseline["recall_at_1"]
        delta_mrr = r["mrr"] - baseline["mrr"]
        sign_r1 = "+" if delta_r1 >= 0 else ""
        sign_mrr = "+" if delta_mrr >= 0 else ""
        print(f"  {r['name']:<25} R@1 {sign_r1}{delta_r1:.4f}  MRR {sign_mrr}{delta_mrr:.4f}")

    OUT_.write_text(json.dumps({
        "config": {"limit": limit, "benchmark": str(BENCH)},
        "results": results,
        "baseline_variant": "C_full_phase6",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to {OUT_}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()
    main(limit=args.limit)
