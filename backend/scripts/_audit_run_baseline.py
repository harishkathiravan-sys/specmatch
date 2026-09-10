"""Phase 6.5 audit — reproduce Phase 4 baseline (FTS / Hybrid / Reranked) on the full benchmark.

Writes results to backend/scripts/phase6_5_phase4_baseline.json
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app.retrieval.fusion import fuse_candidates
from app.retrieval.lexical import lexical_search
from app.retrieval.metadata import metadata_search
from app.retrieval.query import normalize as normalize_query
from app.retrieval.reranker import get_reranker

CSV_PATH = BASE.parent / "ManakSetu_BIS_Data_V04_FINAL" / "ManakSetu_BIS_Data_V04_FINAL" / "09_evaluation" / "benchmark.csv"


def recall_at_k(ranks, k):
    return sum(1 for r in ranks if 0 < r <= k) / len(ranks) if ranks else 0.0


def mrr(ranks):
    return sum(1 / r for r in ranks if r > 0) / len(ranks) if ranks else 0.0


def _rank(hits, expected):
    for i, sid in enumerate(hits, 1):
        if sid in expected:
            return i
    return 0


def run_mode(mode, query, expected):
    if mode == "fts":
        res = lexical_search(query, page=1, page_size=20)
        hits = [i.get("standard_id") for i in res.get("items", []) if i.get("standard_id")]
        return _rank(hits, expected)
    nq = normalize_query(query)
    lex = lexical_search(query, page=1, page_size=40).get("items", [])
    try:
        meta = metadata_search(nq, top_k=40).get("items", [])
    except Exception:
        meta = []
    fused = fuse_candidates(lex, [], meta, top_k=40)
    if mode == "hybrid":
        return _rank([c.standard_id for c in fused], expected)
    reranked = get_reranker().rerank(query, fused)
    return _rank([c.standard_id for c in reranked], expected)


def main(limit=None):
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    if limit:
        rows = rows[:limit]
    stats = {"fts": [], "hybrid": [], "reranked": []}
    t0 = time.time()
    for row in rows:
        q = (row.get("query") or "").strip()
        expected = (row.get("expected_standard_ids") or "").strip()
        if not q or not expected:
            continue
        exp = [x.strip() for x in re.split(r"[;,]", expected) if x.strip()]
        if not exp:
            continue
        for mode in stats:
            stats[mode].append(run_mode(mode, q, exp))
    elapsed = time.time() - t0
    out = {"queries": len(rows), "elapsed_s": round(elapsed, 1), "modes": {}}
    for mode, ranks in stats.items():
        out["modes"][mode] = {
            "recall_at_1": round(recall_at_k(ranks, 1), 4),
            "recall_at_5": round(recall_at_k(ranks, 5), 4),
            "recall_at_10": round(recall_at_k(ranks, 10), 4),
            "mrr": round(mrr(ranks), 4),
            "hits": sum(1 for r in ranks if r > 0),
            "total": len(ranks),
        }
    dest = Path(__file__).resolve().parent / "phase6_5_phase4_baseline.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"Saved to {dest}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    main(limit=args.limit)