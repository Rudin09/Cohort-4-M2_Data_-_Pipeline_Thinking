# Lead Intelligence System - Mini Project Workflow Plan

## Project Overview

**Objective:** Build an automated lead qualification system that processes 100+ leads, scores them using a custom rubric, generates personalized outreach messages, and produces an actionable report for a sales team.

**Business Problem:** A mid-market SaaS company processes ~1,200 inbound leads/month but only qualifies ~60 (95% loss rate). Manual qualification takes 8-12 minutes per lead. The company suspects missed opportunities and wasted effort on poor fits.

### Business Workflow and Intended Outcome

The business need is to help the sales team respond to promising inbound leads sooner and spend less time manually sorting every submission. The tool should take the lead information the team already collects, apply the same transparent qualification rules to every lead, and return a queue that makes the next action clear.

The workflow is: **lead intake → data checks → rubric-based fit score and decision → LLM-generated explanation → prioritized sales queue and outreach draft**. Sales should be able to see why a lead was ranked highly, identify records that need human judgment, and avoid spending first-touch effort on clear poor fits. In practice, a qualified lead gets a personalized draft for salesperson review; a review lead is checked by a person before outreach; and a rejected lead is not placed in the immediate outreach queue. Summary statistics and rejection reasons should also help the business see which lead sources and fit criteria are producing stronger prospects; they are directional insights, not proof of future revenue or conversion.

This mini-project delivers the qualification and first-touch step of the broader sales outreach sequence. Outreach is prepared for a person to review and send; the tool does not send emails, track replies, or schedule follow-ups. Sales owns any later follow-up timing and decisions. Leads with incomplete information or borderline scores should be surfaced for human review rather than treated as certain decisions.

**Key Deliverables:**
- Source code (Python recommended)
- LLM API integration (batched, not per-lead)
- Error handling for API failures, rate limits, missing data
- Sample data file (leads.csv) with 30+ diverse leads
- Output report (JSON/CSV) with scores, decisions, reasoning, priority rankings
- README with run instructions, rubric explanation, known limitations

---

## Phase 1: Project Setup & Environment (Day 1)

### 1.1 Initialize Project Structure
```
lead-qualifier/
├── main.py                 # Entry point with argparse (--input, --output)
├── config.yaml             # Rubric, thresholds, LLM settings
├── leads.csv               # Input data (copy/symlink from leads_training.csv)
├── output_report.json      # Generated output (from 100-lead run)
├── README.md               # Documentation
├── requirements.txt        # Dependencies
├── .env                    # API keys (from .env.example, not committed)
├── .env.example            # Template for API keys
├── .gitignore              # Excludes venv, .env, __pycache__, outputs
├── utils/
│   ├── __init__.py
│   ├── models.py           # Lead, LeadScore, LeadResult dataclasses
│   ├── data_loader.py      # CSV reading, validation, missing data handling
│   ├── rubric_engine.py    # Deterministic scoring logic
│   ├── llm_client.py       # Batched LLM calls with retry logic
│   ├── message_generator.py # Personalized outreach templates
│   └── report_builder.py   # Output report assembly
└── tests/
    ├── __init__.py
    ├── test_rubric.py
    ├── test_data_validation.py
    └── test_edge_cases.py
```

### 1.2 Set Up Python Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 1.3 Required Dependencies (requirements.txt)
```
pandas>=2.0
pyyaml>=6.0
requests>=2.31
tenacity>=8.2  # Retry logic
python-dotenv>=1.0  # Environment variables
```

---

## Phase 2: Design Qualification Rubric (Day 1-2)

### 2.1 Define 3-5 Scoring Factors (Weighted 1-10 each)

| Factor | Weight | Description |
|--------|--------|-------------|
| **Company Size Fit** | 25% | Target: 50-5000 employees (SMB to Mid-market) |
| **Industry Alignment** | 25% | Core verticals: SaaS, FinTech, HealthTech, Cybersecurity |
| **Engagement Recency** | 20% | Recent interaction (<30 days) = high intent |
| **Source Quality** | 15% | Inbound demo > Referral > Webinar > Content > LinkedIn > Cold |
| **Budget/Buying Signals** | 15% | Company size + industry + source combination |

### 2.2 Scoring Logic (config.yaml)
```yaml
rubric:
  company_size:
    weight: 0.25
    tiers:
      - range: [50, 5000]
        score: 10
      - range: [11, 49]
        score: 7
      - range: [5001, 10000]
        score: 6
      - range: [1, 10]
        score: 4
      - default: 3

  industry:
    weight: 0.25
    tiers:
      - industries: [SaaS, FinTech, HealthTech, Cybersecurity, AI/ML, Software]
        score: 10
      - industries: [Finance, Healthcare, Logistics, Manufacturing, EdTech]
        score: 7
      - industries: [Retail, Consulting, Marketing, Real Estate, Energy]
        score: 5
      - default: 3

  recency:
    weight: 0.20
    tiers:
      - days: [0, 30]
        score: 10
      - days: [31, 60]
        score: 7
      - days: [61, 90]
        score: 5
      - default: 3

  source_quality:
    weight: 0.15
    tiers:
      - sources: [Inbound demo request, Referral]
        score: 10
      - sources: [Sales call, Webinar attendee]
        score: 7
      - sources: [Content download, LinkedIn outreach]
        score: 5
      - default: 3

  budget_signals:
    weight: 0.15
    tiers:
      - score: 10
        condition: "company_size >= 50 and industry in [SaaS, FinTech, HealthTech, Cybersecurity] and source in [Inbound demo request, Referral]"
      - score: 7
        condition: "company_size >= 50 and industry in [Finance, Healthcare, Software]"
      - score: 5
        condition: "company_size >= 11"
      - default: 3

thresholds:
  qualified: 7.5
  review: 5.0
  rejected_below: 5.0

llm:
  provider: "groq"  # or openai, gemini, anthropic
  model: "llama-3.1-70b-versatile"
  batch_size: 15
  timeout: 30
  temperature: 0.3
```

**Key Notes:**
- **Scale: 1–10**, matching the project brief. Each factor is scored 1–10; multiply each raw factor score by its weight and sum to get the final score. Since the weights total 1.0, the result stays on a 1–10 scale.
- **Thresholds:** qualified ≥ 7.5, review ≥ 5.0 and < 7.5, rejected < 5.0. Make the decision using the unrounded score; display one decimal place in the report.
- **Priority:** HIGH for qualified leads, MEDIUM for review leads, LOW for rejected leads. The decision and priority must come from the deterministic rubric, not an LLM.
- **Recency:** Uses `days` (not `days_ago`), 3 tiers + default
- **Source:** Groups Inbound+Referral (10), Sales+Webinar (7), Content+LinkedIn (5)
- **Budget Signals:** Composite conditions evaluated in order

### 2.3 Document Rubric in README
- Explain each factor and weight
- Justify thresholds
- Note: No ground truth exists - you define "qualified"

---

## Phase 3: Data Pipeline Implementation (Day 2-3)

### 3.0 Data Models (utils/models.py)
```python
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class Lead:
    name: str
    company: str
    company_size: Optional[int]
    industry: str
    source: str
    last_interaction_date: Optional[date]

@dataclass
class FactorScore:
    name: str
    raw_score: int      # 1-10
    weight: float       # 0.25, 0.20, etc.
    weighted_score: float

@dataclass
class LeadScore:
    lead: Lead
    factor_scores: list[FactorScore]
    total_score: float  # 1-10 weighted average
    decision: str       # QUALIFIED / REVIEW / REJECTED
    priority: str       # HIGH / MEDIUM / LOW

@dataclass
class LeadResult:
    lead: Lead
    score: LeadScore
    llm_reasoning: Optional[str] = None
    outreach_message: Optional[str] = None
    error: Optional[str] = None
```

### 3.1 Data Loader (utils/data_loader.py)
```python
import pandas as pd
from datetime import datetime
from typing import List
from utils.models import Lead

def load_leads(csv_path: str) -> List[Lead]:
    """Load and validate leads from CSV."""
    df = pd.read_csv(csv_path)
    # Handle missing values
    # Normalize company_size (handle "NA", empty strings) → int or None
    # Parse dates, handle missing/invalid dates → date or None
    # Normalize industry, source strings
    # Return list of Lead dataclasses

def validate_lead(row: pd.Series) -> dict:
    """Validate single row, return dict of issues."""
    issues = {}
    # name: required
    # company: required
    # company_size: convert to int, handle "NA"/empty → None
    # industry: normalize case, handle unknown
    # source: normalize, handle missing
    # last_interaction_date: parse YYYY-MM-DD, handle missing → None
    return issues
```

**Validation Rules:**
- `name`: Required, flag if missing
- `company`: Required, flag if missing
- `company_size`: Convert to int, handle "NA"/empty → None
- `industry`: Normalize case, handle unknown
- `source`: Normalize, handle missing
- `last_interaction_date`: Parse YYYY-MM-DD, handle missing → None

### 3.2 Rubric Engine (utils/rubric_engine.py)
```python
import yaml
from typing import List
from utils.models import Lead, LeadScore, FactorScore

def load_rubric(config_path: str) -> dict:
    """Load rubric from config.yaml."""
    with open(config_path) as f:
        return yaml.safe_load(f)

def score_lead(lead: Lead, rubric: dict) -> LeadScore:
    """Apply rubric to single lead, return score breakdown."""
    # Calculate each factor score using tier matching
    # Apply weights
    # Sum weighted scores = total_score (1-10)
    # Determine decision from thresholds
    # Assign priority: HIGH (qualified), MEDIUM (review), LOW (rejected)
    # Return LeadScore with factor breakdown
```

### 3.3 Main Entry Point (main.py) — **With CLI Args**
```python
import argparse
import logging
from pathlib import Path

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def main():
    parser = argparse.ArgumentParser(description="Lead Intelligence System")
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument("--output", default="output_report.json", help="Output JSON file")
    parser.add_argument("--config", default="config.yaml", help="Rubric config file")
    parser.add_argument("--batch-size", type=int, default=15, help="LLM batch size")
    args = parser.parse_args()

    setup_logging()
    # Load config, leads, process, generate report
```

### 3.4 Batch Processing
```python
def process_batch(leads: List[Lead], batch_size: int = 15) -> List[LeadResult]:
    """Enrich rubric-scored leads in batches for LLM calls."""
    # Score each lead deterministically before calling the LLM
    # Send each batch of lead details and rubric results in one API call
    # Parse and validate explanations, matching each response to its lead
    # Return results without allowing LLM output to change score or decision
```

---

## Phase 4: LLM Integration (Day 3-4)

### 4.1 LLM Provider Factory (utils/llm_client.py)
```python
from abc import ABC, abstractmethod
from typing import List
from utils.models import LeadResult

class LLMProvider(ABC):
    @abstractmethod
    def call_batch(self, results: List[LeadResult]) -> List[dict]:
        pass

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout: int):
        # Initialize Groq client
        pass
    def call_batch(self, results: List[LeadResult]) -> List[dict]:
        # Groq-specific call
        pass

class OpenAIProvider(LLMProvider):
    # Similar structure
    pass

def get_provider(config: dict) -> LLMProvider:
    """Factory: return provider based on config.yaml 'provider' field."""
    provider_name = config['llm']['provider']
    # Load API key from .env (GROQ_API_KEY, OPENAI_API_KEY, etc.)
    # Return appropriate provider instance
```

### 4.2 Batched Prompt Design
```python
BATCH_PROMPT = """
You are a B2B sales qualification expert. Analyze these {n} leads and for each provide:
1. A concise explanation (2-3 sentences) for the score and decision already calculated by the rubric, referencing specific lead details
2. Any missing or ambiguous information a salesperson should verify

Rubric:
- Company size fit (25%): 50-5000 employees ideal
- Industry alignment (25%): SaaS, FinTech, HealthTech, Cybersecurity preferred
- Engagement recency (20%): <30 days = high intent
- Source quality (15%): Inbound demo > Referral > Webinar > Content > LinkedIn
- Buying signals (15%): Composite of above

The scores, decisions, and priorities below were calculated deterministically by the application. Do not recalculate or change them. Explain the existing result; if the lead data does not support a conclusion, say what should be reviewed by a person.

Leads and rubric results (each has a stable lead identifier):
{leads_json}

Output as a JSON array with fields: lead_id, reasoning, review_note. Do not return or invent scores, decisions, or priorities.
"""
```

### 4.3 LLM Client with Retry Logic (utils/llm_client.py)
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, TimeoutError, APIError, ConnectionError))
)
def call_llm_batch(results_batch: List[LeadResult], provider: LLMProvider, config: dict) -> List[dict]:
    """Call LLM with exponential backoff retry."""
    batch_size = config['llm']['batch_size']
    timeout = config['llm']['timeout']
    # Handle rate limits, timeouts, API errors
    # Log failures
    # Return parsed responses
```

### 4.4 Error Handling
- **Rate limits**: Exponential backoff (2s, 4s, 8s), queue requests
- **Timeouts**: 30s timeout (from config), retry 3x
- **Invalid responses**: Validate compact JSON schema, retry once with stricter instructions
- **Partial failures**: Preserve valid leads and retry only missing/invalid lead IDs once; surface remaining failures in report `errors`
- **Logging**: Per-batch duration, request-attempt count, valid/total count, safe finish reason, and sanitized failure category; never log API keys or raw response text

---

## Phase 5: Outreach Message Generation (Day 4)

### 5.1 Distinct, Fact-Grounded Message Structures
```python
OUTREACH_VARIANTS = ("fact_first", "question_first", "direct_context")
```

### 5.2 Message Generator (utils/message_generator.py)
```python
def generate_outreach(lead: Lead, score: LeadScore, lead_id: str) -> Optional[str]:
    """Draft a personalized first-touch message for qualified leads."""
    # Return no outreach draft for REVIEW or REJECTED leads
    # Select one of three different structures deterministically from lead_id
    # Use supplied company, industry, company_size, and source facts only
    # Do not infer customer needs, interests, budgets, or product capabilities
    # Return a draft for human review; do not send it
```

### 5.3 Sample Messages for Report
- Generate 3-5 examples for the output report
- Show variety across industries and lead sources
- Include the selected `outreach_variant` in each qualified lead and sample record
- Include in `sample_outreach_messages` array in report
- Generate drafts for qualified leads; do not send outreach automatically
- This project covers the first-touch draft only; sales owns reply tracking and any later follow-up sequence

---

## Phase 6: Report Generation (Day 4-5)

### 6.1 Output Report Structure (output_report.json) — **Exact Required Format**
```json
{
  "metadata": {
    "processed_at": "2024-01-20T10:30:00Z",
    "total_leads": 100,
    "rubric_version": "1.0",
    "llm_model": "llama-3.1-70b-versatile"
  },
  "summary": {
    "total_processed": 100,
    "qualified_count": 23,
    "review_count": 31,
    "rejected_count": 46,
    "qualified_percentage": 23.0,
    "common_rejection_reasons": [
      "Company size too small (32)",
      "Stale engagement >90 days (18)",
      "Industry outside core verticals (15)"
    ]
  },
  "leads": [
    {
      "name": "Alice Chen",
      "company": "CloudScale AI",
      "company_size": 50,
      "industry": "SaaS",
      "source": "Inbound demo request",
      "last_interaction_date": "2024-01-15",
      "score": 10.0,
      "decision": "QUALIFIED",
      "priority": "HIGH",
      "reasoning": "Strong fit: 50-person SaaS company with recent inbound demo request. Core vertical, ideal size range, high-intent signal.",
      "outreach_message": "Hi Alice, I noticed CloudScale AI recently requested a demo..."
    }
  ],
  "priority_queue": [
    {"name": "Alice Chen", "company": "CloudScale AI", "score": 10.0, "priority": "HIGH"},
    {"name": "Test_HighValueMatch", "company": "Perfect Fit Enterprise", "score": 9.2, "priority": "HIGH"}
  ],
  "sample_outreach_messages": [
    {"lead": "Alice Chen", "message": "Hi Alice, I noticed CloudScale AI recently requested a demo..."},
    {"lead": "Test_HighValueMatch", "message": "..."}
  ],
  "flagged_for_review": [
    {"name": "Test_MissingSize", "company": "Test Inc", "issue": "Missing company_size", "score": 5.2},
    {"name": "Test_Borderline", "company": "Example Co", "issue": "Borderline score; human qualification review required", "score": 7.2}
  ],
  "errors": [
    {"lead": "Test_NameOnly", "error": "Missing required fields: name, company_size, industry, source, last_interaction_date"}
  ]
}
```

**Key Format Notes:**
- `score` is 1-10, matching the project brief; show one decimal place
- `priority_queue` contains qualified leads sorted by score descending; review leads are presented separately for human follow-up
- `flagged_for_review`: includes all REVIEW decisions, plus other leads with missing or ambiguous data that can still be scored
- `errors`: leads that couldn't be processed (missing required fields)
- `decision` and `priority` are determined by the rubric engine. LLM-generated reasoning must not override them.

### 6.2 Report Builder (utils/report_builder.py)
```python
def build_report(results: List[LeadResult], metadata: dict) -> dict:
    """Build complete output report."""
    # Calculate summary stats
    # Sort leads by score descending for priority_queue
    # Select top 3-5 sample messages
    # Identify incomplete/ambiguous leads and borderline scores for human review
    # Collect errors (unprocessable leads)
    # Return structured report dict
```

### 6.3 Write Report
```python
import json
def write_report(report: dict, output_path: str):
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
```

---

## Phase 7: Testing & Validation (Day 5)

### 7.1 Test with Training Data (30 leads)
```bash
cd lead-qualifier
python main.py --input ../leads_training.csv --output output_training.json
```
- Verify all 30 leads processed
- Check scoring consistency
- Test the prompt on 5-10 leads first; check that explanations reference actual lead details and preserve the rubric's scores and decisions
- Review LLM reasoning quality and confirm malformed or mismatched responses are handled
- Adjust rubric if needed

### 7.2 Test with Edge Cases (20 leads)
```bash
python main.py --input ../leads_testing.csv --output output_testing.json
```
- Verify graceful handling of:
  - Missing company_size ("NA", empty)
  - Missing names
  - Unknown industries
  - Extreme sizes (1, 50000)
  - Stale dates (2022)
  - Missing dates/sources
- Check error logging in `errors` and `flagged_for_review`
- Confirm borderline scores and ambiguous records appear in `flagged_for_review`
- Ensure no crashes

### 7.3 Production Scale Test (100 leads) — **Final Submission Run**
```bash
python main.py --input ../leads_full_scale_100.csv --output output_report.json
```
- Verify 100 leads processed end-to-end
- Check batch processing efficiency
- Validate report completeness (all required fields)
- Measure runtime (< 5 minutes target)
- **This output_report.json is submitted**

---

## Phase 8: Documentation & Polish (Day 5-6)

### 8.1 README.md (1 page max)
```markdown
# Lead Intelligence System

## Quick Start
```bash
pip install -r requirements.txt
cp .env.example .env  # Add your API key
python main.py --input leads_training.csv --output report.json
```

## Qualification Rubric
[2-3 sentences explaining your rubric: 5 factors, weights, thresholds]

## Known Limitations
- [List edge cases, assumptions, constraints]
```

### 8.2 Code Quality
- Add type hints to all functions
- Docstrings for all public functions
- Consistent formatting (black/ruff)
- Comments for complex logic
- Logging throughout pipeline

### 8.3 Final Verification Checklist
- [x] Processes 100+ leads without crashes
- [x] Batched LLM calls (not per-lead) — batch_size from config
- [x] Error handling for API failures (retries, logging)
- [x] Handles missing/invalid data gracefully (flagged_for_review, errors)
- [x] Borderline or ambiguous leads are surfaced for human review
- [x] Scores use the 1-10 scale and thresholds consistently
- [x] LLM explains rubric results without changing scores, decisions, or priorities
- [x] Every lead has a unique report-wide `priority_rank` ordered by deterministic score (ties by lead ID); qualified queue entries retain that rank
- [x] Output report has all required fields (metadata, summary, per-lead ranks, priority_queue, sample_outreach_messages, flagged_for_review, errors)
- [x] Qualified leads receive one of three deterministic, fact-grounded first-touch structures (industry, size, source); sending and later follow-ups remain with sales
- [x] README explains how to run with CLI args and fits within one rendered page
- [x] Rubric documented and defensible
- [x] No API keys in repo (.env in .gitignore)

Verification update (2026-10-31): 27 unit tests pass; the 30/20/100 deterministic runs and notebook acceptance checks pass. The README renders to one Letter page. A prior 100-lead live attempt produced 85/100 explanations in 428.9s. The configured Groq model rejected `response_format={"type":"json_object"}` with HTTP 400, while a compact prompt-only JSON pilot passed. On the same ten leads, batch sizes 5/10/15 all achieved 10/10; size 5 was fastest (6.7s) with no retries and is the default. The new full live run produced 100/100 explanations, zero errors, and 20 batches with one request each and `finish_reason=stop`; deterministic scores/decisions/priorities matched exactly. Runtime was 299.8s, just under five minutes. The verified live report was promoted only after those checks. Outreach has three deterministic, fact-only structures selected by lead ID.

---

## Phase 9: Submission (Day 6-7)

### 9.1 Package Deliverables
```
lead-qualifier/
├── main.py
├── config.yaml
├── leads_training.csv (or your sample leads.csv)
├── output_report.json (from 100-lead run)
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
└── utils/
    ├── __init__.py
    ├── models.py
    ├── data_loader.py
    ├── rubric_engine.py
    ├── llm_client.py
    ├── message_generator.py
    └── report_builder.py
```
The submission archive also carries the analyst notebook, `TESTING_GUIDE.md`, `WORKFLOW_PLAN.md`, and the training, edge-case, and 100-lead CSVs at its root so the bundled guide links and analyst checks have their required inputs.

### 9.2 Create Submission Zip
Create `lead-qualifier-submission.zip` from the repository root with an explicit include list. The archive contains the application and tests under `lead-qualifier/`, plus the final report, analyst notebook, phase documentation, and training/testing/full-scale input CSVs. Exclude `.env`, `venv/`, `__pycache__/`, `*.pyc`, and temporary helper scripts. Verify the archive contains the required app/report/support files and none of the excluded paths before submission.

### 9.3 Submit
- Upload zip to submission portal
- Ensure `lead-qualifier/output_report.json` is from the 100-lead run

Phase 9 packaging verification (2026-10-31): the validated live 100-lead report contains reasoning for every lead, zero errors, unique ranks 1-100, and scores/decisions/priorities equal to deterministic baseline. The refreshed ZIP includes the final outreach variants, LLM diagnostics/retries, tests, README, notebook, guides, config, and live report. CRC, required-file/exclusion checks, extracted-package tests, and an extracted 100-lead deterministic CLI run pass; the archive report matches the workspace report. Uploading the verified ZIP to the external submission portal remains a user action.

---

## Data Files Reference

| File | Leads | Purpose | Quality |
|------|-------|---------|---------|
| `leads_training.csv` | 30 | Development, rubric tuning | 100% complete |
| `leads_full_scale_100.csv` | 100 | **Final submission run** | 100% complete |
| `leads_testing.csv` | 20 | Edge case validation | 60% complete (intentional) |

**Recommended Workflow:**
1. Develop with `leads_training.csv` (30 leads)
2. Validate robustness with `leads_testing.csv` (20 leads)
3. **Submit output from `leads_full_scale_100.csv` (100 leads)**

---

## Grading Criteria Mapping

| Criterion | Weight | How We Address It |
|-----------|--------|-------------------|
| **Correctness** | 25% | Zero crashes, defensible decisions, consistent scoring |
| **Usefulness** | 25% | Personalized messages, actionable priority queue, sales-ready report |
| **Robustness** | 20% | Retry logic, missing data handling, edge case flags |
| **Efficiency** | 15% | Batched LLM calls, <5 min for 100 leads |
| **Documentation** | 15% | Clear README, rubric explained, limitations noted |

---

## Timeline Summary

| Day | Focus | Key Output |
|-----|-------|------------|
| 1 | Setup, Rubric Design | Project structure, config.yaml |
| 2 | Data Pipeline, Rubric Engine | Working scoring on 30 leads |
| 3 | LLM Integration | Batched calls with retry logic |
| 4 | Messages, Report Builder | Complete output report |
| 5 | Testing (30 → 20 → 100) | Validated on all datasets |
| 6 | Documentation, Polish | README, code cleanup |
| 7 | Final Review, Submit | Zip package |

---

## Key Decisions to Make Early

1. **LLM Provider**: Choose one and stick with it (Groq recommended for speed/free tier)
2. **Batch Size**: 10-20 leads per API call (balance context window vs. calls)
3. **Rubric Weights**: Define before coding - hard to change later
4. **Decision Thresholds**: Use the configured 1-10 scale consistently: qualified ≥ 7.5, review ≥ 5.0 and < 7.5, rejected < 5.0
5. **Output Format**: JSON (structured) or CSV (spreadsheet-friendly)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM API rate limits | Exponential backoff, batch requests, local caching |
| Inconsistent LLM outputs | Strict JSON schema in prompt, validation, retry |
| Missing data crashes | Defensive coding, default values, flagging not crashing |
| Time overrun | Time-box each phase, prioritize core pipeline first |
| Rubric subjectivity | Document reasoning, test on samples, be consistent |

---

## Success Metrics

- ✅ **Minimum Bar**: Process 100 leads end-to-end, produce actionable report
- ✅ **Good**: Personalized messages, clear priority queue, handles edge cases
- ✅ **Excellent**: Consistent defensible scoring, robust error handling, sales-ready output

---

*Generated: 2026-10-30 | Based on Mini_Project_Brief.docx, DATA_README.md, DELIVERY_SUMMARY.md, EXPECTED_OUTCOMES_NOTE.md, and all CSV data files*