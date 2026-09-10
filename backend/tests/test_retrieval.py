import unittest

from app.retrieval.pipeline import run_pipeline
from app.retrieval.requirements import extract_requirements


class RetrievalPipelineTests(unittest.TestCase):
    def test_aircraft_woven_carpet_returns_recommendations(self):
        result = run_pipeline("aircraft woven carpet", top_k=5, max_candidates=20)
        self.assertTrue(result.recommendations)
        titles = [rec["standard"]["title"].lower() for rec in result.recommendations]
        self.assertTrue(any("woven carpet" in title or "aircraft" in title for title in titles))

    def test_standard_number_query_is_resolved(self):
        result = run_pipeline("IS 19763:2026", top_k=5, max_candidates=20)
        self.assertTrue(result.recommendations)
        standard_numbers = [rec["standard"]["standard_number"] for rec in result.recommendations]
        self.assertTrue(any("19763" in sn for sn in standard_numbers))

    def test_long_procurement_spec_extracts_requirements(self):
        text = (
            "Supply and installation of aircraft woven carpet suitable for aircraft interior applications. "
            "The carpet shall be manufactured from textile floor coverings and comply with the relevant "
            "specification for aircraft woven carpet in passenger cabin and cargo hold environments. "
            "It shall be tested for flame, abrasion, and durability performance."
        )
        reqs = extract_requirements(text)
        self.assertTrue(reqs.requirements)
        self.assertTrue(reqs.keywords)

    def test_ambiguous_query_still_returns_safe_results(self):
        result = run_pipeline("carpet", top_k=5, max_candidates=20)
        self.assertIsInstance(result.recommendations, list)

    def test_empty_query_does_not_crash(self):
        result = run_pipeline("", top_k=5, max_candidates=20)
        self.assertIsInstance(result.recommendations, list)

    def test_poor_query_returns_no_crash(self):
        result = run_pipeline("xyzabc123", top_k=5, max_candidates=20)
        self.assertIsInstance(result.recommendations, list)


if __name__ == "__main__":
    unittest.main()
