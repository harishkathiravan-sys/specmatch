def recall_at_k(ranks, k): return sum(1 for r in ranks if r <= k) / len(ranks) if ranks else 0.0
def mrr(ranks): return sum(1/r for r in ranks if r > 0) / len(ranks) if ranks else 0.0
