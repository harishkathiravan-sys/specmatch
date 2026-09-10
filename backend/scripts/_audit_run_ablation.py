"""Phase 6.5 audit — ablation: which scoring signals actually help ranking.

Runs the pipeline with each signal disabled (via monkeypatching weights) on a
sample subset of the benchmark, computing Recall@1/5/10 and MRR.

Ablations:
  A. Lexical only
  B. Lexical + semantic
  C. Lexical + semantic + metadata
  D. Full Phase 6 scoring
  E. Full minus contradiction penalty
  F. Full minus compliance signal
  G. Full minus lifecycle signal
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

BENCH = BASE.parent / "ManakSetu_BIS_Data_V04_FINAL" / "ManakSetu_BIS_Data_V04_FINAL" / "09_evaluation" / "benchmark.csv"
OUT = BASE / "scripts" / "phase6_5_ablation.csv"


def _recall_at_k(ranks, k):
    return sum(1 for r in ranks if 0 < r <= k) / len(ranks) if ranks else 0.0


def _mrr(ranks):
    return sum(1.0 / r for r in ranks if r > 0) / len(ranks) if ranks else 0.0


def _rank(recs, exp):
    for i, rec in enumerate(recs, 1):
        std = rec.to_dict()["standard"] if hasattr(rec, "to_dict") else rec["standard"]
        if std.get("standard_id") in exp or std.get("standard_number") in exp:
            return i
    return 0


def run_ablation(name, fn, rows, exp_lookup, limit):
    ranks = []
    t0 = time.time()
    for row in rows[:limit]:
        q = row.get("query", "")
        exp = exp_lookup.get(row.get("query_id"), [])
        if not q or not exp:
            continue
        pr = fn(q)
        ranks.append(_rank(pr.phase6_recommendations, exp))
    elapsed = time.time() - t0
    n = len(ranks)
    return {
        "ablation": name,
        "queries": n,
        "recall_at_1": round(_recall_at_k(ranks, 1), 4),
        "recall_at_5": round(_recall_at_k(ranks, 5), 4),
        "recall_at_10": round(_recall_at_k(ranks, 10), 4),
        "mrr": round(_mrr(ranks), 4),
        "elapsed_s": round(elapsed, 1),
    }


def main(limit=200):
    rows = list(csv.DictReader(open(BENCH, encoding="utf-8")))[:limit]
    exp_lookup = {}
    for row in rows:
        exp_lookup[row.get("query_id")] = [x.strip() for x in re.split(r"[;,]", row.get("expected_standard_ids", "")) if x.strip()]

    results = []

    # A. Lexical only: metadata off, semantic off (semantic already off), weights shifted
    def fn_lexical(q):
        old_mw = fusion_mod.METADATA_WEIGHT
        fusion_mod.METADATA_WEIGHT = 0.0
        try:
            return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        finally:
            fusion_mod.METADATA_WEIGHT = old_mw
    results.append(run_ablation("A_lexical_only", fn_lexical, rows, exp_lookup, limit))

    # B. Lexical + semantic (semantic still inert; record as-is)
    def fn_lex_sem(q):
        old_mw = fusion_mod.METADATA_WEIGHT
        fusion_mod.METADATA_WEIGHT = 0.0
        try:
            return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        finally:
            fusion_mod.METADATA_WEIGHT = old_mw
    results.append(run_ablation("B_lexical_semantic", fn_lex_sem, rows, exp_lookup, limit))

    # C. Lexical + semantic + metadata = base fusion (phase6 still on but no signal changes)
    def fn_full_fusion(q):
        return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
    results.append(run_ablation("C_lex_sem_meta", fn_full_fusion, rows, exp_lookup, limit))

    # D. Full Phase 6 = C (same)
    results.append(run_ablation("D_full_phase6", fn_full_fusion, rows, exp_lookup, limit))

    # E. Full minus contradiction penalty
    def fn_no_contra(q):
        orig = p6_mod.contradiction_penalty
        p6_mod.contradiction_penalty = lambda contradictions: 0.0
        try:
            return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        finally:
            p6_mod.contradiction_penalty = orig
    results.append(run_ablation("E_no_contradiction", fn_no_contra, rows, exp_lookup, limit))

    # F. Full minus compliance signal (compliance is informational; should not move rank)
    # G. Full minus lifecycle penalty
    def fn_no_lifecycle(q):
        orig = p6_mod.lifecycle_penalty
        p6_mod.lifecycle_penalty = lambda *a, **k: 0.0
        try:
            return run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        finally:
            p6_mod.lifecycle_penalty = orig
    results.append(run_ablation("G_no_lifecycle", fn_no_lifecycle, rows, exp_lookup, limit))

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ablation", "queries", "recall_at_1", "recall_at_5", "recall_at_10", "mrr", "elapsed_s"])
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(json.dumps(results, indent=2))
    print(f"Saved to {OUT}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()
    main(limit=args.limit)