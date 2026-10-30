import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from utils.data_loader import load_leads, validate_lead


class DataValidationTests(unittest.TestCase):
    def test_blank_required_fields_are_reported(self):
        lead = load_leads_from_rows(
            ["name", "company", "company_size", "industry", "source", "last_interaction_date"],
            [["", "", "NA", "", "", "not-a-date"]],
        )[0]

        issues = validate_lead(lead)

        self.assertIn("name", issues)
        self.assertIn("company", issues)
        self.assertIsNone(lead.company_size)
        self.assertIsNone(lead.last_interaction_date)

    def test_optional_missing_values_are_normalized(self):
        lead = load_leads_from_rows(
            ["name", "company", "company_size", "industry", "source", "last_interaction_date"],
            [["Jamie Example", "Example Co", "", "", "", ""]],
        )[0]

        issues = validate_lead(lead)

        self.assertEqual(lead.name, "Jamie Example")
        self.assertEqual(lead.company, "Example Co")
        self.assertIsNone(lead.company_size)
        self.assertIsNone(lead.last_interaction_date)
        self.assertIn("company_size", issues)
        self.assertIn("industry", issues)
        self.assertIn("source", issues)

    def test_valid_date_and_company_size_are_parsed(self):
        lead = load_leads_from_rows(
            ["name", "company", "company_size", "industry", "source", "last_interaction_date"],
            [["Jamie Example", "Example Co", "250", "SaaS", "Referral", "2024-01-20"]],
        )[0]

        self.assertEqual(lead.company_size, 250)
        self.assertEqual(lead.last_interaction_date, date(2024, 1, 20))
        self.assertEqual(validate_lead(lead), {})


def load_leads_from_rows(headers, rows):
    with tempfile.TemporaryDirectory() as directory:
        csv_path = Path(directory) / "leads.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)
        return load_leads(str(csv_path))


if __name__ == "__main__":
    unittest.main()