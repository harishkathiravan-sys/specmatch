"""Debug golden test rankings."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.retrieval.pipeline import run_pipeline

tests = [
    ("Aircraft carpet", "Carpet for aircraft use standard", "IS 19763"),
    ("Steel pipe", "Steel pipe specification IS 5822", "IS 5822"),
    ("Cement", "Portland cement specification", "IS 1077"),
    ("Fire safety", "Fire extinguisher for commercial buildings", "IS 12795"),
]

for name, q, exp in tests:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    print(f"Expected: {exp}")
    print()
    pr = run_pipeline(q, top_k=10, max_candidates=40, phase6=True)
    recs = pr.phase6_recommendations or pr.recommendations
    for i, rec in enumerate(recs[:5], 1):
        if hasattr(rec, "to_dict"):
            d = rec.to_dict()
        else:
            d = rec
        std = d.get("standard", {})
        sn = std.get("standard_number", "")
        title = std.get("title", "")[:80]
        rel = d.get("relevance_score", 0)
        contra_pen = d.get("contradiction_penalty", 0)
        conf = d.get("confidence", "?")
        marker = " <<<" if exp in sn else ""
        print(f"  #{i}: {sn} — {title}")
        print(f"      rel={rel:.3f} contra_pen={contra_pen:.3f} conf={conf}{marker}")
