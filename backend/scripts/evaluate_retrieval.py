"""
Offline evaluation — runs the FTS retrieval against 09_evaluation/benchmark.csv
using metrics.py semantics. Does NOT fabricate scores; reports measured values.

Computes: Recall@1, Recall@5, Recall@10, MRR against expected_standard_ids.
Uses _extract_search_terms / _normalize_query logic mirrored from search_service.
"""
import csv
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "specmatch.db"
CSV_PATH = BASE.parent / "SpecMatch_Data_V03_FINAL" / "ManakSetu_BIS_Data_V03" / "09_evaluation" / "benchmark.csv"

import re

STOP = {'the','a','an','and','or','of','for','in','to','is','by','on','at','with','from',
        'procurement','supply','installation','testing','suitable','shall','applicable','specification',
        'requirement','requirements','this','that','which','have','been'}

def extract(q):
    terms = re.findall(r'[a-zA-Z0-9]+', q.lower())
    return [t for t in terms if len(t)>2 and t not in STOP]

def normalize(q):
    if re.search(r'\bIS\s*\d+', q, re.IGNORECASE):
        q = re.sub(r':\d{4}', '', q)
        return re.sub(r'\s+',' ', q).strip()
    terms = extract(q)
    if not terms: return re.sub(r'\s+',' ', re.sub(r'["*]','', q)).strip()
    safe=[re.sub(r'["*]','',t) for t in terms]
    return " OR ".join(safe) if len(safe)>1 else safe[0]

def recall_at_k(ranks, k): return sum(1 for r in ranks if r <= k)/len(ranks) if ranks else 0.0
def mrr(ranks): return sum(1/r for r in ranks if r>0)/len(ranks) if ranks else 0.0

def search_once(conn, query, k=10):
    fts = normalize(query)
    try:
        rows = conn.execute(
            "SELECT s.standard_id FROM standards_fts fts JOIN standards s ON fts.rowid=s.rowid WHERE standards_fts MATCH ? ORDER BY rank LIMIT ?",
            [fts, k]
        ).fetchall()
        return [r[0] for r in rows]
    except sqlite3.OperationalError:
        # fallback LIKE
        terms = extract(query)[:4]
        if not terms: return []
        cond = " OR ".join(["s.title_normalized LIKE ?"]*len(terms))
        params=[f"%{t}%" for t in terms]
        rows = conn.execute(f"SELECT standard_id FROM standards s WHERE {cond} LIMIT ?", params+[k]).fetchall()
        return [r[0] for r in rows]

def main(limit=None, k_list=(1,5,10)):
    conn=sqlite3.connect(str(DB_PATH))
    conn.row_factory=sqlite3.Row
    rows=list(csv.DictReader(open(CSV_PATH,encoding='utf-8')))
    if limit: rows=rows[:limit]
    ranks=[]
    total=0
    for r in rows:
        q=r['query']
        expected=(r['expected_standard_ids'] or '').strip()
        if not expected: continue
        exp_ids=[x.strip() for x in re.split(r'[;,]', expected) if x.strip()]
        if not exp_ids: continue
        total+=1
        hits=search_once(conn, q, max(k_list))
        rank=0
        for i,sid in enumerate(hits, start=1):
            if sid in exp_ids:
                rank=i; break
        ranks.append(rank if rank>0 else 0)
    print(f"Evaluated: {total} queries")
    for k in k_list:
        print(f"Recall@{k}: {recall_at_k(ranks,k):.4f}")
    print(f"MRR: {mrr([r for r in ranks if r>0] or ranks):.4f}  (over {len([r for r in ranks if r>0])} hits / {len(ranks)})")
    # also print raw histogram
    from collections import Counter
    c=Counter(ranks)
    print("Rank histogram (rank:count):", dict(sorted(c.items())[:15]))

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args=ap.parse_args()
    main(limit=args.limit)
