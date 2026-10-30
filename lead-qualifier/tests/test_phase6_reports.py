import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from utils.data_loader import load_leads
from utils.models import LeadResult
from utils.report_builder import build_report, write_report
from utils.rubric_engine import load_rubric, score_leads_batch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
REFERENCE_DATE = date(2024, 1, 20)
REQUIRED_REPORT_KEYS = {
    "metadata",
    "summary",
    "leads",
    "priority_queue",
    "sample_outreach_messages",
    "flagged_for_review",
    "errors",
}


class PhaseSixReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubric = load_rubric(str(PROJECT_ROOT / "config.yaml"))
        cls.leads = load_leads(str(REPOSITORY_ROOT / "leads_training.csv"))
        cls.scores = score_leads_batch(cls.leads, cls.rubric, REFERENCE_DATE)
        cls.metadata = {
            "processed_at": "2026-10-30T12:00:00Z",
            "total_leads": len(cls.leads),
            "rubric_version": "1.0",
            "llm_model": "deterministic-only",
        }

    def make_report(self, results=None):
        if results is None:
            results = [
                LeadResult(lead=score.lead, score=score)
                for score in self.scores
            ]
        return build_report(results, self.metadata)

    def test_report_contains_complete_summary_and_per_lead_explanations(self):
        report = self.make_report()

        self.assertTrue(REQUIRED_REPORT_KEYS.issubset(report))
        summary = report["summary"]
        self.assertEqual(summary["total_processed"], len(report["leads"]))
        self.assertEqual(
            summary["qualified_count"]
            + summary["review_count"]
            + summary["rejected_count"],
            summary["total_processed"],
        )
        self.assertAlmostEqual(
            summary["qualified_percentage"],
            round(
                summary["qualified_count"]
                / summary["total_processed"]
                * 100,
                1,
            ),
        )
        self.assertIsInstance(summary["common_rejection_reasons"], list)
        self.assertEqual(len(report["leads"]), 30)
        for lead in report["leads"]:
            self.assertIn("reasoning", lead)
            self.assertTrue(lead["reasoning"])
            self.assertIn("factor_breakdown", lead)
            self.assertIn("decision", lead)
            self.assertIn("priority", lead)
            self.assertGreaterEqual(lead["score"], 1)
            self.assertLessEqual(lead["score"], 10)

    def test_priority_queue_is_sorted_and_qualified_only(self):
        report = self.make_report()
        queue = report["priority_queue"]
        qualified_ids = {
            lead["lead_id"]
            for lead in report["leads"]
            if lead["decision"] == "QUALIFIED"
        }

        self.assertEqual({lead["lead_id"] for lead in queue}, qualified_ids)
        self.assertEqual(
            [lead["score"] for lead in queue],
            sorted((lead["score"] for lead in queue), reverse=True),
        )
        self.assertTrue(all(lead["priority"] == "HIGH" for lead in queue))

    def test_drafts_and_review_flags_follow_decisions(self):
        report = self.make_report()
        leads_by_id = {lead["lead_id"]: lead for lead in report["leads"]}
        flagged_ids = {
            lead["lead_id"] for lead in report["flagged_for_review"]
        }
        review_ids = {
            lead["lead_id"]
            for lead in report["leads"]
            if lead["decision"] == "REVIEW"
        }

        self.assertTrue(review_ids.issubset(flagged_ids))
        for lead in report["leads"]:
            self.assertEqual(
                lead["outreach_message"] is not None,
                lead["decision"] == "QUALIFIED",
            )
        messages = report["sample_outreach_messages"]
        self.assertLessEqual(len(messages), 5)
        self.assertGreaterEqual(
            len(messages),
            3 if report["summary"]["qualified_count"] >= 3 else 0,
        )
        self.assertTrue(
            all(
                leads_by_id[item["lead_id"]]["decision"] == "QUALIFIED"
                for item in messages
            )
        )
        available_segments = {
            (lead["industry"], lead["source"])
            for lead in report["leads"]
            if lead["decision"] == "QUALIFIED"
        }
        self.assertEqual(
            len({(item["industry"], item["source"]) for item in messages}),
            min(5, len(available_segments)),
        )

    def test_write_report_round_trips_json_and_metadata(self):
        report = self.make_report()
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.json"
            write_report(report, str(output_path))
            loaded = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(loaded, report)
        self.assertEqual(loaded["metadata"], self.metadata)

    def test_enrichment_failures_are_reported_and_flagged(self):
        results = [
            LeadResult(
                lead=self.scores[0].lead,
                score=self.scores[0],
                error="LLM request failed (TimeoutError)",
            )
        ]
        report = self.make_report(results)

        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(
            report["errors"][0]["lead_id"],
            report["flagged_for_review"][0]["lead_id"],
        )
        self.assertIn(
            "LLM enrichment failed",
            report["flagged_for_review"][0]["issue"],
        )


if __name__ == "__main__":
    unittest.main()
