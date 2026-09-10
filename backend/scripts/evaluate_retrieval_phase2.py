import csv
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from app.retrieval.fusion import fuse_candidates
from app.retrieval.lexical import lexical_search
from app.retrieval.metadata import metadata_search
from app.retrieval.query import normalize as normalize_query
from app.retrieval.reranker import get_reranker
from app.retrieval.semantic import get_embedding_provider, is_semantic_available, semantic_search

CSV_PATH = BASE.parent / "SpecMatch_Data_V03_FINAL" / "ManakSetu_BIS_Data_V03" / "09_evaluation" / "benchmark.csv"


def recall_at_k(ranks, k):
    return sum(1 for r in ranks if r <= k) / len(ranks) if ranks else 0.0


def mrr(ranks):
    return sum(1 / r for r in ranks if r > 0) / len(ranks) if ranks else 0.0


def ndcg_at_k(ranks, k):
    if not ranks:
        return 0.0
    dcg = 0.0
    for i, rank in enumerate(ranks[:k], start=1):
        if rank <= k:
            dcg += 1.0 / i
    ideal = sum(1.0 / i for i in range(1, min(k, len(ranks)) + 1))
    return dcg / ideal if ideal else 0.0


def _rank_for_hits(hits: list[str], expected_ids: list[str]):
    for i, sid in enumerate(hits, start=1):
        if sid in expected_ids:
            return i
    return 0


def evaluate_fts(query: str, expected_ids: list[str]):
    result = lexical_search(query, page=1, page_size=20)
    hits = [item.get("standard_id") for item in result.get("items", []) if item.get("standard_id")]
    rank = _rank_for_hits(hits, expected_ids)
    return rank, recall_at_k([rank] if rank else [0], 1), recall_at_k([rank] if rank else [0], 5), mrr([rank] if rank else [0]), ndcg_at_k([rank] if rank else [0], 5)


def evaluate_hybrid(query: str, expected_ids: list[str]):
    nq = normalize_query(query)
    lexical_result = lexical_search(query, page=1, page_size=40)
    lexical_items = lexical_result.get("items", [])

    semantic_items = []
    if is_semantic_available():
        try:
            provider = get_embedding_provider()
            emb = provider.embed([nq.normalized_query or query])[0]
            semantic_results = semantic_search(emb, top_k=40)
            semantic_items = [{
                "standard_id": r.standard_id,
                "standard_number": r.standard_number,
                "title": r.title,
                "semantic_score": r.semantic_score,
            } for r in semantic_results]
        except Exception:
            semantic_items = []

    try:
        metadata_result = metadata_search(nq, top_k=40)
        metadata_items = metadata_result.get("items", [])
    except Exception:
        metadata_items = []

    fused = fuse_candidates(lexical_items, semantic_items, metadata_items, top_k=40)
    hits = [c.standard_id for c in fused]
    rank = _rank_for_hits(hits, expected_ids)
    return rank, recall_at_k([rank] if rank else [0], 1), recall_at_k([rank] if rank else [0], 5), mrr([rank] if rank else [0]), ndcg_at_k([rank] if rank else [0], 5)


def evaluate_reranked(query: str, expected_ids: list[str]):
    nq = normalize_query(query)
    lexical_result = lexical_search(query, page=1, page_size=40)
    lexical_items = lexical_result.get("items", [])

    semantic_items = []
    if is_semantic_available():
        try:
            provider = get_embedding_provider()
            emb = provider.embed([nq.normalized_query or query])[0]
            semantic_results = semantic_search(emb, top_k=40)
            semantic_items = [{
                "standard_id": r.standard_id,
                "standard_number": r.standard_number,
                "title": r.title,
                "semantic_score": r.semantic_score,
            } for r in semantic_results]
        except Exception:
            semantic_items = []

    try:
        metadata_result = metadata_search(nq, top_k=40)
        metadata_items = metadata_result.get("items", [])
    except Exception:
        metadata_items = []

    fused = fuse_candidates(lexical_items, semantic_items, metadata_items, top_k=40)
    reranker = get_reranker()
    reranked = reranker.rerank(query, fused)
    hits = [c.standard_id for c in reranked]
    rank = _rank_for_hits(hits, expected_ids)
    return rank, recall_at_k([rank] if rank else [0], 1), recall_at_k([rank] if rank else [0], 5), mrr([rank] if rank else [0]), ndcg_at_k([rank] if rank else [0], 5)


def main(limit=None):
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    if limit:
        rows = rows[:limit]

    modes = {
        "fts": {"rec1": 0.0, "rec5": 0.0, "mrr": 0.0, "ndcg5": 0.0, "count": 0},
        "hybrid": {"rec1": 0.0, "rec5": 0.0, "mrr": 0.0, "ndcg5": 0.0, "count": 0},
        "reranked": {"rec1": 0.0, "rec5": 0.0, "mrr": 0.0, "ndcg5": 0.0, "count": 0},
    }

    for row in rows:
        q = (row.get("query") or "").strip()
        expected = (row.get("expected_standard_ids") or "").strip()
        if not q or not expected:
            continue
        expected_ids = [x.strip() for x in re.split(r"[;,]", expected) if x.strip()]
        if not expected_ids:
            continue

        for mode, evaluator in {
            "fts": evaluate_fts,
            "hybrid": evaluate_hybrid,
            "reranked": evaluate_reranked,
        }.items():
            rank, rec1, rec5, mrr_val, ndcg_val = evaluator(q, expected_ids)
            stats = modes[mode]
            stats["count"] += 1
            stats["rec1"] += rec1
            stats["rec5"] += rec5
            stats["mrr"] += mrr_val
            stats["ndcg5"] += ndcg_val

    print("Benchmark comparison: FTS vs Hybrid vs Hybrid + Reranker")
    print("-" * 90)
    for mode in ["fts", "hybrid", "reranked"]:
        stats = modes[mode]
        count = max(1, stats["count"])
        print(
            f"{mode:>9} | "
            f"Recall@1={stats['rec1']/count:.4f} | "
            f"Recall@5={stats['rec5']/count:.4f} | "
            f"MRR={stats['mrr']/count:.4f} | "
            f"NDCG@5={stats['ndcg5']/count:.4f}"
        )


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    main(limit=args.limit)
