import unittest
from datetime import date
from pathlib import Path

from utils.data_loader import load_leads
from utils.models import LeadResult
from utils.report_builder import build_report
from utils.rubric_engine import load_rubric, score_leads_batch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


class PipelineEdgeCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubric = load_rubric(str(PROJECT_ROOT / "config.yaml"))
        cls.reference_date = date(2024, 1, 20)
        leads = load_leads(str(REPOSITORY_ROOT / "leads_testing.csv"))
        scores = score_leads_batch(leads, cls.rubric, cls.reference_date)
        cls.report = build_report(
            [LeadResult(lead=score.lead, score=score) for score in scores],
            {"reference_date": cls.reference_date.isoformat()},
        )

    def test_missing_required_company_is_reviewed_not_qualified(self):
        lead = next(
            item for item in self.report["leads"]
            if item["name"] == "Test_MissingCompany"
        )

        self.assertEqual(lead["decision"], "REVIEW")
        self.assertEqual(lead["priority"], "MEDIUM")
        self.assertTrue(
            any(item["name"] == lead["name"] for item in self.report["flagged_for_review"])
        )
        self.assertNotIn(
            lead["name"],
            {item["name"] for item in self.report["priority_queue"]},
        )

    def test_all_review_decisions_are_flagged(self):
        flagged_names = {item["name"] for item in self.report["flagged_for_review"]}
        review_names = {
            item["name"] for item in self.report["leads"]
            if item["decision"] == "REVIEW"
        }

        self.assertTrue(review_names.issubset(flagged_names))

    def test_priority_queue_contains_only_qualified_leads(self):
        qualified_names = {
            item["name"] for item in self.report["leads"]
            if item["decision"] == "QUALIFIED"
        }

        self.assertEqual(
            {item["name"] for item in self.report["priority_queue"]},
            qualified_names,
        )


if __name__ == "__main__":
    unittest.main()