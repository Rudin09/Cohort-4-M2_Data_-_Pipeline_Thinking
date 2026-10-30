# Lead Intelligence System

Automated lead qualification that applies a deterministic, weighted rubric to lead data, surfaces records for human review, and prepares outreach drafts for salesperson review. The system does not send emails.

## Quick start (Windows PowerShell)

From the `lead-qualifier` directory:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Deterministic run; no API key or network request is needed.
python main.py --input ..\leads_training.csv --output output_training.json --reference-date 2024-01-20 --no-llm
```

For the full environment setup and phase-by-phase acceptance checks, see [TESTING_GUIDE.md](../TESTING_GUIDE.md).

## Qualification rubric

Five factors are scored from 1 to 10 and combined with weights totaling 100%. The weighted sum therefore remains on a 1-10 scale.

| Factor | Weight | Scoring summary |
|---|---:|---|
| Company size fit | 25% | 50-5,000 employees: 10; 11-49: 7; 5,001-10,000: 6; 1-10: 4; otherwise: 3 |
| Industry alignment | 25% | Core industries: 10; secondary industries: 7; tertiary industries: 5; otherwise: 3 |
| Engagement recency | 20% | 0-30 days: 10; 31-60: 7; 61-90: 5; otherwise or missing: 3 |
| Source quality | 15% | Inbound demo/referral: 10; sales call/webinar: 7; content/LinkedIn: 5; otherwise: 3 |
| Budget/buying signals | 15% | Composite company-size, industry, and source conditions, as defined in `config.yaml` |

Decision thresholds use the unrounded weighted score; reports display one decimal place:

- **QUALIFIED / HIGH:** score >= 7.5
- **REVIEW / MEDIUM:** score >= 5.0 and < 7.5, or a required name/company is missing
- **REJECTED / LOW:** score < 5.0

The REVIEW exception for missing required fields prevents incomplete records from being treated as qualified. Optional missing data is retained, flagged for review, and scored using the rubric defaults. This rubric is business logic, not a model trained on historical conversion outcomes.

## Data files

| File | Leads | Purpose |
|---|---:|---|
| `..\leads_training.csv` | 30 | Development and rubric review |
| `..\leads_testing.csv` | 20 | Missing-data and edge-case checks |
| `..\leads_full_scale_100.csv` | 100 | Production-size deterministic run |
| `leads.csv` | 30 | Packaged copy of the training sample |

## CLI

```powershell
python main.py --input ..\leads_testing.csv --output output_testing.json --reference-date 2024-01-20 --no-llm
python main.py --input ..\leads_full_scale_100.csv --output output_report.json --reference-date 2024-01-20 --no-llm
```

`--input` is required. `--output` defaults to `output_report.json`; `--config` defaults to `config.yaml`. `--reference-date` makes recency scores reproducible. `--no-llm` runs scoring and report generation without an LLM provider or API key. The configured Groq provider is installed by `requirements.txt`; LLM enrichment also requires `GROQ_API_KEY` in `.env` and network access. `--batch-size` overrides the configured batch size.

## Output report

The JSON report includes processing metadata, decision summary, per-lead scores and factor breakdowns, rejection reasons, a qualified-only priority queue, review flags, and processing errors. When LLM enrichment is enabled, it adds explanation and review notes only; deterministic scores, decisions, and priorities remain authoritative. Responses are matched by stable per-run lead IDs, and failed/partial enrichment is surfaced in `errors`.

Qualified leads receive a first-touch draft in `outreach_message`; REVIEW and REJECTED leads receive `null`. The report includes up to five varied examples in `sample_outreach_messages`. Drafts use the lead's supplied details and conditional industry wording, avoid invented customer references, and are for salesperson review—the application never sends them.

## Tests

From this directory, run the standard-library unit test suite:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover rubric scale and thresholds, input normalization, edge-case reporting, stable-ID batched LLM behavior using mocked providers, partial failures and strict-response retry, and qualified-only outreach drafts. Mocked tests do not verify live provider credentials, network availability, or model behavior; the manual acceptance guide includes the optional API smoke test and analyst review steps.

## Known limitations

- There is no ground truth; qualification rules are explicit business assumptions.
- Missing optional values use rubric defaults and should be checked by a person.
- Unrecognized industries and sources use default rubric tiers.
- Outreach content uses configured static templates, is conditional on industry relevance, and requires salesperson review.
- LLM explanations are optional and depend on provider availability and valid credentials. The model is not used to score or decide lead qualification.
- Aggregate counts and source/factor summaries are directional indicators, not proof of future conversion or revenue.

## Project structure

```text
lead-qualifier/
├── main.py
├── config.yaml
├── leads.csv
├── README.md
├── requirements.txt
├── .env.example
├── utils/
└── tests/
```
