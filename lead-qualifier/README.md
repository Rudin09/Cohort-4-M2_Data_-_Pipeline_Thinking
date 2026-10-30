# Lead Intelligence System

Automated lead qualification system that scores leads using a custom rubric, generates personalized outreach messages, and produces an actionable report for sales teams.

## Quick Start

`ash
# Install dependencies
pip install -r requirements.txt

# Configure API key (choose one provider)
cp .env.example .env
# Edit .env and add your API key (GROQ_API_KEY, OPENAI_API_KEY, etc.)

# Run on training data (30 leads)
python main.py --input ../leads_training.csv --output output_training.json

# Run on testing data (20 edge cases)
python main.py --input ../leads_testing.csv --output output_testing.json

# Run on full scale (100 leads) - FINAL SUBMISSION
python main.py --input ../leads_full_scale_100.csv --output output_report.json
`

## Qualification Rubric

The system evaluates leads across **5 weighted factors** (total = 100%):

| Factor | Weight | Description |
|--------|--------|-------------|
| **Company Size Fit** | 25% | Target: 50-5000 employees (SMB to Mid-market). Scores: 50-5000?10, 11-49?7, 5001-10000?6, 1-10?4, default?3 |
| **Industry Alignment** | 25% | Core verticals: SaaS, FinTech, HealthTech, Cybersecurity, AI/ML, Software (10). Secondary: Finance, Healthcare, Logistics, Manufacturing, EdTech (7). Tertiary: Retail, Consulting, Marketing, Real Estate, Energy (5). Default: 3 |
| **Engagement Recency** | 20% | Recent interaction indicates intent. <30 days?10, 31-60 days?7, 61-90 days?5, default?3 |
| **Source Quality** | 15% | Inbound demo request + Referral (10), Sales call + Webinar attendee (7), Content download + LinkedIn outreach (5), default (3) |
| **Budget/Buying Signals** | 15% | Composite: size =50 + core industry + inbound/referral (10), size =50 + finance/healthcare/software (7), size =11 (5), default (3) |

**Scoring:** Each factor scored 1-10, weighted sum × 10 = final score (0-100 scale).

**Decision Thresholds:**
- **QUALIFIED** = 75
- **REVIEW** = 50
- **REJECTED** < 50

**Priority:** HIGH (=75), MEDIUM (=50), LOW (<50)

## Configuration

All rubric settings in config.yaml:
- Factor weights and tier definitions
- Decision thresholds
- LLM provider, model, batch size, timeout, temperature

## Data Files

| File | Leads | Purpose |
|------|-------|---------|
| leads_training.csv | 30 | Development, rubric tuning |
| leads_testing.csv | 20 | Edge case validation (missing data, stale dates, etc.) |
| leads_full_scale_100.csv | 100 | **Final submission run** |

## Output Report

Generates output_report.json with:
- metadata: processing timestamp, total leads, rubric version, LLM model
- summary: counts by decision, qualified %, common rejection reasons
- leads: detailed scoring for each lead with reasoning
- priority_queue: leads sorted by score (descending)
- sample_outreach_messages: 3-5 personalized message examples
- lagged_for_review: leads with missing data but scored
- errors: unprocessable leads

## Test Results (Phase 7 Validation)

| Dataset | Leads | Qualified | Review | Rejected | Edge Cases Handled |
|---------|-------|-----------|--------|----------|-------------------|
| Training | 29 | 10 (34.5%) | 18 | 1 | 0 flagged |
| Testing | 20 | 7 (35.0%) | 11 | 2 | 4 flagged, 0 errors |
| **Full Scale** | **100** | **45 (45.0%)** | **53** | **2** | 0 flagged, 0 errors |

## Known Limitations

1. **Recency calculation** uses current date — scores will vary over time. Use fixed reference date (--reference-date) for reproducibility.
2. **No ground truth** — rubric is based on business logic, not historical conversion data.
3. **LLM dependency** — requires API key and internet connectivity. Falls back to deterministic scoring if unavailable.
4. **Industry/source normalization** — unknown values default to lowest tier.
5. **Batch size** limited by LLM context window (default 15 leads per call).
6. **Budget signals** use simple conditional logic — could be enhanced with ML.
7. **LLM model availability** — Groq model availability varies; check console.groq.com for current models.

## Project Structure

`
lead-qualifier/
+-- main.py                 # CLI entry point
+-- config.yaml             # Rubric, thresholds, LLM settings
+-- leads.csv               # Sample input (30 training leads)
+-- output_report.json      # Generated output (from 100-lead run)
+-- README.md               # This file
+-- requirements.txt        # Dependencies
+-- .env                    # API keys (not committed)
+-- .env.example            # Template
+-- .gitignore              # Excludes venv, .env, cache, outputs
+-- utils/
¦   +-- __init__.py
¦   +-- models.py           # Lead, LeadScore, LeadResult dataclasses
¦   +-- data_loader.py      # CSV reading, validation
¦   +-- rubric_engine.py    # Deterministic scoring
¦   +-- llm_client.py       # Batched LLM calls with retry
¦   +-- message_generator.py # Personalized outreach
¦   +-- report_builder.py   # Output report assembly
+-- tests/
    +-- __init__.py
    +-- test_rubric.py
    +-- test_data_validation.py
    +-- test_edge_cases.py
`

## Development

`ash
# Run tests
pytest tests/

# Format code
black utils/ main.py

# Lint
ruff check utils/ main.py
`

## License

MIT
