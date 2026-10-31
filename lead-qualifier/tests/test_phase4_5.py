import json
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from utils.llm_client import (
    LLMProvider,
    PartialLLMResponse,
    _is_retryable_provider_error,
    enrich_leads_with_llm,
)
from utils.message_generator import (
    OUTREACH_VARIANTS,
    generate_outreach,
    get_outreach_variant_id,
)
from utils.models import Lead, LeadResult
from utils.report_builder import build_report
from utils.rubric_engine import load_rubric, score_leads_batch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MockProvider(LLMProvider):
    def __init__(self, response_factory):
        self.response_factory = response_factory
        self.calls = []

    def call_batch(
        self, leads, lead_scores, lead_ids, config, strict_prompt=False
    ):
        self.calls.append((list(lead_ids), strict_prompt))
        raw_results = self.response_factory(
            leads, lead_scores, lead_ids, strict_prompt
        )
        return self._validate_results(raw_results, lead_ids)


class PhaseFourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubric = load_rubric(str(PROJECT_ROOT / "config.yaml"))

    def make_leads(self):
        return [
            Lead(
                name="Alex Example",
                company="Example Co",
                company_size=250,
                industry="SaaS",
                source="Inbound demo request",
                last_interaction_date=date(2024, 1, 19),
            )
            for _ in range(3)
        ]

    @staticmethod
    def valid_result(lead_id, reasoning):
        return {
            "lead_id": lead_id,
            "reasoning": reasoning,
            "review_note": "",
        }

    def test_batch_size_and_duplicate_names_use_stable_ids(self):
        leads = self.make_leads()
        scores = score_leads_batch(leads, self.rubric, date(2024, 1, 20))

        def response(leads, scores, lead_ids, strict):
            return [
                self.valid_result(lead_id, f"Reason for {lead_id}")
                for lead_id in reversed(lead_ids)
            ]

        provider = MockProvider(response)
        with patch("utils.llm_client.get_provider", return_value=provider):
            enrichments = enrich_leads_with_llm(
                leads, self.rubric, scores, batch_size=2
            )

        self.assertEqual([len(call[0]) for call in provider.calls], [2, 1])
        self.assertEqual(
            [item["lead_id"] for item in enrichments],
            ["lead-000000", "lead-000001", "lead-000002"],
        )
        self.assertEqual(
            [item["reasoning"] for item in enrichments],
            [
                "Reason for lead-000000",
                "Reason for lead-000001",
                "Reason for lead-000002",
            ],
        )
        self.assertTrue(
            all(
                not {"score", "decision", "priority"}.intersection(item)
                for item in enrichments
            )
        )

    def test_strict_retry_preserves_successes_and_surfaces_partial_failures(self):
        leads = self.make_leads()
        scores = score_leads_batch(leads, self.rubric, date(2024, 1, 20))

        def response(leads, scores, lead_ids, strict):
            if not strict:
                return [
                    self.valid_result(lead_ids[0], "First lead was explained."),
                    {
                        **self.valid_result(lead_ids[1], "Invalid result."),
                        "score": 10,
                    },
                ]
            return [
                self.valid_result(lead_ids[0], "Second lead was explained.")
            ]

        provider = MockProvider(response)
        with patch("utils.llm_client.get_provider", return_value=provider):
            enrichments = enrich_leads_with_llm(
                leads, self.rubric, scores, batch_size=3
            )

        self.assertEqual(provider.calls, [
            (["lead-000000", "lead-000001", "lead-000002"], False),
            (["lead-000001", "lead-000002"], True),
        ])
        self.assertEqual(enrichments[0]["reasoning"], "First lead was explained.")
        self.assertEqual(enrichments[1]["reasoning"], "Second lead was explained.")
        self.assertIsNotNone(enrichments[2]["error"])

    def test_provider_initialization_failure_is_visible_per_lead(self):
        leads = self.make_leads()[:2]
        scores = score_leads_batch(leads, self.rubric, date(2024, 1, 20))
        with patch(
            "utils.llm_client.get_provider",
            side_effect=ValueError("API key not found in environment: GROQ_API_KEY"),
        ):
            enrichments = enrich_leads_with_llm(leads, self.rubric, scores)

        self.assertEqual(len(enrichments), 2)
        self.assertTrue(all(item["error"] for item in enrichments))
        self.assertTrue(
            all("GROQ_API_KEY" in item["error"] for item in enrichments)
        )

    def test_duplicate_or_scoring_fields_in_response_are_not_accepted(self):
        with self.assertRaises(PartialLLMResponse) as context:
            LLMProvider._validate_results(
                [
                    {
                        **self.valid_result("lead-000000", "Explanation."),
                        "decision": "QUALIFIED",
                    }
                ],
                ["lead-000000"],
            )

        self.assertEqual(context.exception.missing_ids, ["lead-000000"])
        self.assertEqual(context.exception.results, [])

    def test_provider_request_includes_rubric_and_parses_explanation(self):
        lead = self.make_leads()[0]
        score = score_leads_batch([lead], self.rubric, date(2024, 1, 20))[0]
        content = json.dumps(
            [self.valid_result("lead-000000", "The supplied factors support review.")]
        )
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=content))
            ]
        )

        class FakeCompletions:
            def create(self, **kwargs):
                self.request = kwargs
                return response

        completions = FakeCompletions()
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )
        provider = LLMProvider(client, "test-model", 10, 0)

        results = provider.call_batch(
            [lead], [score], ["lead-000000"], self.rubric
        )

        self.assertEqual(results[0]["reasoning"], "The supplied factors support review.")
        prompt = completions.request["messages"][0]["content"]
        self.assertIn('"deterministic_score":', prompt)
        self.assertIn('"qualified":7.5', prompt)
        self.assertIn('"results" array', prompt)
        self.assertNotIn("response_format", completions.request)
        self.assertEqual(completions.request["timeout"], 10)

    def test_partial_retry_keeps_valid_results_when_strict_retry_fails(self):
        leads = self.make_leads()
        scores = score_leads_batch(leads, self.rubric, date(2024, 1, 20))

        def response(leads, scores, lead_ids, strict):
            if strict:
                raise TimeoutError("provider timed out")
            return [self.valid_result(lead_ids[0], "First lead was explained.")]

        provider = MockProvider(response)
        with patch("utils.llm_client.get_provider", return_value=provider):
            with self.assertLogs("utils.llm_client", level="INFO") as captured:
                enrichments = enrich_leads_with_llm(
                    leads, self.rubric, scores, batch_size=3
                )

        self.assertEqual(len(provider.calls), 4)
        self.assertTrue(
            all(
                call[0] == ["lead-000001", "lead-000002"]
                for call in provider.calls[1:]
            )
        )
        self.assertEqual(enrichments[0]["reasoning"], "First lead was explained.")
        self.assertTrue(all(item["error"] for item in enrichments[1:]))
        diagnostics = "\n".join(captured.output)
        self.assertIn("request_attempts=4", diagnostics)
        self.assertIn("failure_category=partial_response+provider_TimeoutError_unrecovered", diagnostics)
        self.assertNotIn("provider timed out", diagnostics)

    def test_batch_diagnostics_report_elapsed_attempts_and_safe_finish_reason(self):
        leads = self.make_leads()
        scores = score_leads_batch(leads, self.rubric, date(2024, 1, 20))
        provider = MockProvider(
            lambda leads, scores, lead_ids, strict: [
                self.valid_result(lead_id, "The supplied factors support review.")
                for lead_id in lead_ids
            ]
        )
        with patch("utils.llm_client.get_provider", return_value=provider):
            with self.assertLogs("utils.llm_client", level="INFO") as captured:
                enrichments = enrich_leads_with_llm(
                    leads[:2], self.rubric, scores[:2], batch_size=2
                )

        self.assertEqual(len(enrichments), 2)
        diagnostic = "\n".join(captured.output)
        self.assertIn("elapsed_seconds=", diagnostic)
        self.assertIn("request_attempts=1", diagnostic)
        self.assertIn("valid_leads=2/2", diagnostic)
        self.assertIn("finish_reason=not_reported", diagnostic)
        self.assertIn("failure_category=none", diagnostic)

    def test_only_transient_provider_errors_are_retried(self):
        transient_error = type(
            "RateLimitError", (Exception,), {"__module__": "groq._exceptions"}
        )()
        auth_error = type(
            "AuthenticationError", (Exception,), {"__module__": "groq._exceptions"}
        )()

        self.assertTrue(_is_retryable_provider_error(transient_error))
        self.assertFalse(_is_retryable_provider_error(auth_error))
        self.assertTrue(_is_retryable_provider_error(TimeoutError()))


class PhaseFiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubric = load_rubric(str(PROJECT_ROOT / "config.yaml"))

    def test_only_qualified_leads_receive_grounded_drafts(self):
        industries_sources = [
            ("SaaS", "Inbound demo request"),
            ("SaaS", "Referral"),
            ("FinTech", "Inbound demo request"),
            ("HealthTech", "Referral"),
            ("Cybersecurity", "Webinar attendee"),
        ]
        leads = [
            Lead(
                name=f"Lead {index}",
                company=f"Company {index}",
                company_size=250,
                industry=industry,
                source=source,
                last_interaction_date=date(2024, 1, 19),
            )
            for index, (industry, source) in enumerate(industries_sources)
        ]
        scores = score_leads_batch(leads, self.rubric, date(2024, 1, 20))
        self.assertTrue(all(score.decision == "QUALIFIED" for score in scores))
        review_score = replace(scores[0], decision="REVIEW", priority="MEDIUM")
        rejected_score = replace(scores[1], decision="REJECTED", priority="LOW")
        report_results = [
            *(LeadResult(lead=score.lead, score=score) for score in scores),
            LeadResult(lead=leads[0], score=review_score),
            LeadResult(lead=leads[1], score=rejected_score),
        ]

        report = build_report(report_results, {"test": True})

        qualified_rows = [
            row for row in report["leads"] if row["decision"] == "QUALIFIED"
        ]
        other_rows = [
            row for row in report["leads"] if row["decision"] != "QUALIFIED"
        ]
        self.assertTrue(all(row["outreach_message"] for row in qualified_rows))
        self.assertTrue(all(row["outreach_message"] is None for row in other_rows))
        self.assertEqual(len(report["sample_outreach_messages"]), 5)
        sample_segments = {
            (item["industry"], item["source"])
            for item in report["sample_outreach_messages"]
        }
        self.assertEqual(len(sample_segments), 5)
        for item in report["sample_outreach_messages"]:
            self.assertIn(item["lead"], item["message"])
            self.assertIn(item["company"], item["message"])
            self.assertIn(item["industry"], item["message"])
            self.assertIn(item["source"], item["message"])
            self.assertIn(item["outreach_variant"], {
                variant_id for variant_id, _ in OUTREACH_VARIANTS
            })
            self.assertNotIn("budget", item["message"].lower())
            self.assertNotIn("interest", item["message"].lower())

    def test_three_distinct_variants_are_stable_and_use_supplied_facts(self):
        lead = Lead(
            name="Alex Example",
            company="Example Co",
            company_size=250,
            industry="SaaS",
            source="Inbound demo request",
            last_interaction_date=date(2024, 1, 19),
        )
        score = score_leads_batch([lead], self.rubric, date(2024, 1, 20))[0]
        self.assertEqual(score.decision, "QUALIFIED")

        messages_by_variant = {}
        for index in range(100):
            lead_id = f"lead-{index:06d}"
            variant_id = get_outreach_variant_id(lead, lead_id)
            message = generate_outreach(lead, score, lead_id)
            self.assertEqual(
                get_outreach_variant_id(lead, lead_id), variant_id
            )
            self.assertEqual(generate_outreach(lead, score, lead_id), message)
            self.assertIn(lead.name, message)
            self.assertIn(lead.company, message)
            self.assertIn(lead.industry, message)
            self.assertIn(str(lead.company_size), message)
            self.assertIn(lead.source, message)
            self.assertNotIn("budget", message.lower())
            self.assertNotIn("pain point", message.lower())
            messages_by_variant.setdefault(variant_id, message)

        self.assertEqual(
            set(messages_by_variant),
            {variant_id for variant_id, _ in OUTREACH_VARIANTS},
        )
        self.assertEqual(
            len({message.splitlines()[2] for message in messages_by_variant.values()}),
            len(OUTREACH_VARIANTS),
        )

    def test_nonqualified_outreach_returns_no_draft(self):
        lead = Lead(
            name="Alex Example",
            company="Example Co",
            company_size=250,
            industry="SaaS",
            source="Inbound demo request",
            last_interaction_date=date(2024, 1, 19),
        )
        score = score_leads_batch([lead], self.rubric, date(2024, 1, 20))[0]
        review_score = replace(score, decision="REVIEW", priority="MEDIUM")

        self.assertIsNone(generate_outreach(lead, review_score))


if __name__ == "__main__":
    unittest.main()
