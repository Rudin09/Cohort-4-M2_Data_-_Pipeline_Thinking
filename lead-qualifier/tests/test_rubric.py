import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

from utils.models import Lead
from utils.rubric_engine import load_rubric, score_lead


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RubricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubric = load_rubric(str(PROJECT_ROOT / "config.yaml"))

    def test_weights_and_thresholds_match_workflow_plan(self):
        self.assertEqual(len(self.rubric["rubric"]), 5)
        self.assertAlmostEqual(
            sum(factor["weight"] for factor in self.rubric["rubric"].values()),
            1.0,
        )
        self.assertEqual(self.rubric["thresholds"]["qualified"], 7.5)
        self.assertEqual(self.rubric["thresholds"]["review"], 5.0)

    def test_score_is_weighted_average_on_one_to_ten_scale(self):
        lead = Lead(
            name="Alex Example",
            company="Example Co",
            company_size=400,
            industry="SaaS",
            source="Inbound demo request",
            last_interaction_date=date(2024, 1, 19),
        )

        score = score_lead(lead, self.rubric, reference_date=date(2024, 1, 20))

        self.assertEqual(len(score.factor_scores), 5)
        self.assertGreaterEqual(score.total_score, 1)
        self.assertLessEqual(score.total_score, 10)
        self.assertEqual(score.decision, "QUALIFIED")
        self.assertEqual(score.priority, "HIGH")
        budget_score = next(
            factor.raw_score for factor in score.factor_scores
            if factor.name == "budget_signals"
        )
        self.assertEqual(budget_score, 10)

    def test_decision_uses_unrounded_score(self):
        lead = Lead(
            name="Alex Example",
            company="Example Co",
            company_size=50,
            industry="Finance",
            source="Content download",
            last_interaction_date=date(2023, 12, 20),
        )

        score = score_lead(lead, self.rubric, reference_date=date(2024, 1, 20))

        self.assertEqual(score.total_score, 7.5)
        self.assertEqual(score.decision, "REVIEW")
        self.assertEqual(score.priority, "MEDIUM")

    def test_missing_required_company_forces_review(self):
        lead = Lead(
            name="Alex Example",
            company="",
            company_size=400,
            industry="SaaS",
            source="Inbound demo request",
            last_interaction_date=date(2024, 1, 19),
        )

        score = score_lead(lead, self.rubric, reference_date=date(2024, 1, 20))

        self.assertEqual(score.decision, "REVIEW")
        self.assertEqual(score.priority, "MEDIUM")


if __name__ == "__main__":
    unittest.main()