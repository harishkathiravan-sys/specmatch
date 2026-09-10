"""Phase 6.5 audit — golden tests + hard-negative evaluation + contradiction tests.

Golden test: "Aircraft woven carpet..." MUST rank IS 19763:2026 at #1.
Contradiction tests A-D: contextual, not keyword-exclusion.
Hard negatives: from hard_cases.csv + hard_negative_pairs.csv.
"""
import csv
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app.retrieval.pipeline import run_pipeline

DATA = BASE.parent / "ManakSetu_BIS_Data_V04_FINAL" / "ManakSetu_BIS_Data_V04_FINAL"
HARD_CSV = DATA / "09_evaluation" / "hard_cases.csv"
HNP = DATA / "05_retrieval" / "hard_negative_pairs.csv"
HN4 = DATA / "04_procurement" / "hard_negatives.csv"
OUT = BASE / "scripts"

GOLDEN_QUERY = "Aircraft woven carpet for commercial aircraft cabin flooring with flame resistance, abrasion resistance and low smoke characteristics."
GOLDEN_EXPECTED = "IS 19763:2026"


def _rank_of(pr, expected_id=None, expected_num=None):
    recs = pr.phase6_recommendations if pr.phase6_recommendations else pr.recommendations
    for i, r in enumerate(recs, 1):
        d = r.to_dict() if hasattr(r, "to_dict") else r
        std = d["standard"]
        if (expected_id and std.get("standard_id") == expected_id) or (expected_num and std.get("standard_number") == expected_num):
            return i, d
    return 0, None


def golden_test():
    pr = run_pipeline(GOLDEN_QUERY, top_k=10, max_candidates=40, phase6=True)
    rank_base = 0
    for i, r in enumerate(pr.recommendations, 1):
        if r["standard"]["standard_number"] == GOLDEN_EXPECTED:
            rank_base = i
            break
    rank_p6, top_d = _rank_of(pr, expected_num=GOLDEN_EXPECTED)
    top = pr.phase6_recommendations[0] if pr.phase6_recommendations else None
    topd = top.to_dict() if top and hasattr(top, "to_dict") else (top or {})
    coverage = (topd.get("requirement_coverage") or {}) if topd else {}
    return {
        "query": GOLDEN_QUERY,
        "expected": GOLDEN_EXPECTED,
        "base_rank": rank_base,
        "phase6_rank": rank_p6,
        "top_result": f"{topd.get('standard',{}).get('standard_number','')} — {topd.get('standard',{}).get('title','')[:90]}" if topd else "none",
        "final_score": round(float(topd.get("relevance_score") or 0), 4),
        "requirement_coverage": coverage.get("score"),
        "reasoning": topd.get("why_this_standard"),
        "evidence": [e.get("type") for e in (topd.get("evidence") or [])[:4]],
        "contradictions": topd.get("contradictions"),
        "confidence": topd.get("confidence"),
        "confidence_score": topd.get("confidence_score"),
        "compliance": (topd.get("compliance") or {}).get("summary"),
        "certification": (topd.get("compliance") or {}).get("certification"),
        "lifecycle": (topd.get("lifecycle") or {}).get("summary"),
        "qco": (topd.get("compliance") or {}).get("qco"),
    }


CONTRA_TESTS = [
    {
        "id": "TEST_A_aircraft_carpet",
        "query": "Aircraft woven carpet for commercial aircraft cabin flooring",
        "expect": "aircraft-specific standard preferred (IS 19763 or aircraft title)",
        "check": lambda top3_nums, top3_titles: (
            any("carpet" in t.lower() for t in top3_titles) and any("aircraft" in t.lower() or "19763" in n for n, t in zip(top3_nums, top3_titles))
        ),
    },
    {
        "id": "TEST_B_residential_carpet",
        "query": "Residential floor carpet for home living room flooring",
        "expect": "residential/general floor covering NOT replaced by aircraft standards",
        "check": lambda top3_nums, top3_titles: any("aircraft" in t.lower() for t in top3_titles) is False,
    },
    {
        "id": "TEST_C_aircraft_residential_candidate",
        "query": "Aircraft woven carpet with flame resistance for aircraft cabins",
        "expect": "residential candidate receives contextual penalty if present",
        "check": lambda top3_nums, top3_titles: True,  # informational
    },
    {
        "id": "TEST_D_wrong_material",
        "query": "Steel pipe for high-pressure water supply",
        "expect": "non-steel pipe standards penalized (e.g. pvc/copper)",
        "check": lambda top3_nums, top3_titles: (
            any("steel" in t.lower() for t in top3_titles) and not any(("pvc" in t.lower() or "copper" in t.lower()) and "steel" not in t.lower() for t in top3_titles[:3])
        ),
    },
]


def contradiction_tests():
    results = []
    for t in CONTRA_TESTS:
        pr = run_pipeline(t["query"], top_k=5, max_candidates=40, phase6=True)
        recs = pr.phase6_recommendations if pr.phase6_recommendations else pr.recommendations
        top3 = []
        top3_nums = []
        top3_titles = []
        for r in recs[:3]:
            d = r.to_dict() if hasattr(r, "to_dict") else r
            std = d["standard"]
            top3_nums.append(std.get("standard_number", ""))
            top3_titles.append(std.get("title", ""))
            top3.append(d)
        ok = t["check"](top3_nums, top3_titles)
        results.append({
            "test": t["id"],
            "query": t["query"],
            "expect": t["expect"],
            "pass": ok,
            "top3": [f"{n} — {ti[:70]}" for n, ti in zip(top3_nums, top3_titles)],
            "contradictions_in_top3": [d.get("contradictions") or [] for d in top3],
            "penalties": [d.get("contradiction_penalty") for d in top3],
        })
    return results


def hard_negative_eval(limit=500):
    """Evaluate hard_negative_pairs + hard_cases: does the negative standard rank above the gold?"""
    hnp = list(csv.DictReader(open(HNP, encoding="utf-8")))[:limit]
    gold_map = {}
    bench = DATA / "09_evaluation" / "benchmark.csv"
    if bench.exists():
        for row in csv.DictReader(open(bench, encoding="utf-8")):
            gold_map[row["query_id"]] = [x.strip() for x in re.split(r"[;,]", row.get("expected_standard_ids", "")) if x.strip()]

    results = {"total": 0, "neg_ranked_above_gold": 0, "gold_rank": [], "neg_ranks": [], "detail": []}
    seen = set()
    for row in hnp:
        qid = row.get("query_id", "")
        neg_std = row.get("negative_standard_id", "")
        if qid in seen or qid not in gold_map:
            continue
        seen.add(qid)
        exp = gold_map[qid]
        # find query text
        q = ""
        for r in csv.DictReader(open(bench, encoding="utf-8")):
            if r["query_id"] == qid:
                q = r["query"]
                break
        if not q:
            continue
        pr = run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        recs = pr.phase6_recommendations if pr.phase6_recommendations else pr.recommendations
        gold_rank = 0
        neg_rank = 0
        for i, r in enumerate(recs, 1):
            d = r.to_dict() if hasattr(r, "to_dict") else r
            std = d["standard"]
            if std.get("standard_id") in exp or std.get("standard_number") in exp:
                gold_rank = i
            if std.get("standard_id") == neg_std:
                neg_rank = i
        results["total"] += 1
        results["gold_rank"].append(gold_rank)
        results["neg_ranks"].append(neg_rank)
        if 0 < neg_rank < gold_rank:
            results["neg_ranked_above_gold"] += 1
        if len(results["detail"]) < 15:
            results["detail"].append({"qid": qid, "gold_rank": gold_rank, "neg_rank": neg_rank, "neg_std": neg_std})

    n = max(results["total"], 1)
    results["hnp_accuracy"] = round(1 - results["neg_ranked_above_gold"] / n, 4)
    results["gold_recall_at_1"] = round(sum(1 for r in results["gold_rank"] if r == 1) / n, 4)
    return results


def hard_cases_eval(limit=500):
    """hard_cases.csv: each row = a candidate standard + expected_action (REJECT_NEGATIVE)."""
    rows = list(csv.DictReader(open(HARD_CSV, encoding="utf-8")))[:limit]
    bench_map = {}
    bench = DATA / "09_evaluation" / "benchmark.csv"
    for row in csv.DictReader(open(bench, encoding="utf-8")):
        bench_map[row["query_id"]] = (row["query"], [x.strip() for x in re.split(r"[;,]", row.get("expected_standard_ids", "")) if x.strip()])

    results = {"total": 0, "neg_in_top3": 0, "detail": []}
    for row in rows:
        qid = row.get("query_id", "")
        neg_std = row.get("standard_id", "")
        action = row.get("expected_action", "")
        if qid not in bench_map or action != "REJECT_NEGATIVE":
            continue
        q, exp = bench_map[qid]
        pr = run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
        recs = pr.phase6_recommendations if pr.phase6_recommendations else pr.recommendations
        top3_ids = []
        for r in recs[:3]:
            d = r.to_dict() if hasattr(r, "to_dict") else r
            top3_ids.append(d["standard"].get("standard_id"))
        in_top3 = neg_std in top3_ids
        results["total"] += 1
        if in_top3:
            results["neg_in_top3"] += 1
        if len(results["detail"]) < 15:
            results["detail"].append({"qid": qid, "neg_std": neg_std, "in_top3": in_top3, "top3": top3_ids})
    results["reject_accuracy"] = round(1 - results["neg_in_top3"] / max(results["total"], 1), 4)
    return results


def main():
    g = golden_test()
    ct = contradiction_tests()
    hne = hard_negative_eval(limit=300)
    hc = hard_cases_eval(limit=300)
    out = {"golden_test": g, "contradiction_tests": ct, "hard_negative_pairs": hne, "hard_cases": hc}
    (OUT / "phase6_5_golden_and_hard.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"Saved to {OUT / 'phase6_5_golden_and_hard.json'}")


if __name__ == "__main__":
    main()