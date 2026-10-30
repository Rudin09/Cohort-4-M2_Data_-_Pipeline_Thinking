# Lead Intelligence System - Mini Project Workflow Plan

## Project Overview

**Objective:** Build an automated lead qualification system that processes 100+ leads, scores them using a custom rubric, generates personalized outreach messages, and produces an actionable report for a sales team.

**Business Problem:** A mid-market SaaS company processes ~1,200 inbound leads/month but only qualifies ~60 (95% loss rate). Manual qualification takes 8-12 minutes per lead. The company suspects missed opportunities and wasted effort on poor fits.

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
├── main.py                 # Entry point
├── config.yaml             # Rubric, API keys, settings
├── leads.csv               # Input data (use leads_training.csv initially)
├── output_report.json      # Generated output
├── README.md               # Documentation
├── requirements.txt        # Dependencies
├── utils/
│   ├── __init__.py
│   ├── data_loader.py      # CSV reading, validation
│   ├── rubric_engine.py    # Scoring logic
│   ├── llm_client.py       # Batched LLM calls
│   ├── message_generator.py # Outreach message creation
│   └── report_builder.py   # Output formatting
└── tests/
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
      - days_ago: [0, 30]
        score: 10
      - days_ago: [31, 90]
        score: 7
      - days_ago: [91, 180]
        score: 5
      - days_ago: [181, 365]
        score: 3
      - default: 1

  source:
    weight: 0.15
    tiers:
      - sources: [Inbound demo request]
        score: 10
      - sources: [Referral]
        score: 8
      - sources: [Sales call, Webinar attendee]
        score: 6
      - sources: [Content download]
        score: 5
      - sources: [LinkedIn outreach]
        score: 4
      - default: 3

  buying_signals:
    weight: 0.15
    # Composite: size + industry + source alignment
    rules:
      - condition: "size >= 50 AND industry in core_verticals AND source == 'Inbound demo request'"
        score: 10
      - condition: "size >= 100 AND source in ['Referral', 'Sales call']"
        score: 7
      - default: 4

decision_thresholds:
  qualified: 7.0
  review: 5.0
  rejected: 0.0
```

### 2.3 Document Rubric in README
- Explain each factor and weight
- Justify thresholds
- Note: No ground truth exists - you define "qualified"

---

## Phase 3: Data Pipeline Implementation (Day 2-3)

### 3.1 Data Loader (utils/data_loader.py)
```python
def load_leads(csv_path: str) -> List[Lead]:
    """Load and validate leads from CSV."""
    df = pd.read_csv(csv_path)
    # Handle missing values
    # Normalize company_size (handle "NA", empty strings)
    # Parse dates, handle missing/invalid dates
    # Return list of Lead dataclasses
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
def score_lead(lead: Lead, rubric: RubricConfig) -> LeadScore:
    """Apply rubric to single lead, return score breakdown."""
    # Calculate each factor score
    # Apply weights
    # Return total + breakdown + decision
```

### 3.3 Batch Processing
```python
def process_batch(leads: List[Lead], batch_size: int = 20) -> List[LeadResult]:
    """Process leads in batches for LLM calls."""
    # Group leads by similarity for batched prompts
    # Call LLM once per batch
    # Parse responses
    # Return enriched results
```

---

## Phase 4: LLM Integration (Day 3-4)

### 4.1 Choose LLM Provider (Free Tier)
- **Groq** (fast, free): `llama-3.1-70b-versatile`
- **OpenAI**: `gpt-3.5-turbo` (free tier)
- **Gemini**: `gemini-1.5-flash` (free)
- **Claude**: Free tier available

### 4.2 Batched Prompt Design
```python
BATCH_PROMPT = """
You are a B2B sales qualification expert. Analyze these {n} leads and for each provide:
1. Qualification score (1-10) based on the rubric
2. Decision: QUALIFIED / REVIEW / REJECTED
3. Reasoning (2-3 sentences referencing specific lead details)
4. Priority rank (HIGH/MEDIUM/LOW)

Rubric:
- Company size fit (25%): 50-5000 employees ideal
- Industry alignment (25%): SaaS, FinTech, HealthTech, Cybersecurity preferred
- Engagement recency (20%): <30 days = high intent
- Source quality (15%): Inbound demo > Referral > Webinar > Content > LinkedIn
- Buying signals (15%): Composite of above

Leads:
{leads_json}

Output as JSON array with fields: name, company, score, decision, reasoning, priority
"""
```

### 4.3 LLM Client with Retry Logic (utils/llm_client.py)
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, TimeoutError, APIError))
)
def call_llm_batch(leads_batch: List[Lead]) -> List[LLMResponse]:
    """Call LLM with exponential backoff retry."""
    # Handle rate limits, timeouts, API errors
    # Log failures
    # Return parsed responses
```

### 4.4 Error Handling
- **Rate limits**: Exponential backoff, queue requests
- **Timeouts**: 30s timeout, retry 3x
- **Invalid responses**: Validate JSON, retry with stricter prompt
- **Partial failures**: Process successful leads, flag failed for retry

---

## Phase 5: Outreach Message Generation (Day 4)

### 5.1 Message Templates (Personalized)
```python
TEMPLATES = {
    "high_priority": """
Hi {name},

I noticed {company} ({industry}, {size} employees) recently {source_detail}.
Given your focus on {industry_specific_pain_point}, I thought you'd find 
our {product_value_prop} relevant.

Would you be open to a brief call this week to explore how we've helped 
similar {industry} companies like {reference_customer}?

Best,
[Your Name]
""",
    "medium_priority": "...",
    "low_priority": "..."
}
```

### 5.2 Message Generator (utils/message_generator.py)
```python
def generate_outreach(lead: Lead, score: LeadScore) -> str:
    """Generate personalized message for qualified leads."""
    # Select template based on priority
    # Fill in lead-specific details
    # Reference industry, size, source, recent activity
    # Return message string
```

### 5.3 Sample Messages for Report
- Generate 3-5 examples for the output report
- Show variety across industries/priorities

---

## Phase 6: Report Generation (Day 4-5)

### 6.1 Output Report Structure (output_report.json)
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
      "Stale engagement >180 days (18)",
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
      "score": 8.5,
      "decision": "QUALIFIED",
      "priority": "HIGH",
      "reasoning": "Strong fit: 50-person SaaS company with recent inbound demo request. Core vertical, ideal size range, high-intent signal.",
      "outreach_message": "Hi Alice, I noticed CloudScale AI recently requested a demo..."
    }
  ],
  "priority_queue": [
    {"name": "Alice Chen", "company": "CloudScale AI", "score": 8.5, "priority": "HIGH"},
    {"name": "Test_HighValueMatch", "company": "Perfect Fit Enterprise", "score": 9.2, "priority": "HIGH"}
  ],
  "sample_outreach_messages": [
    {"lead": "Alice Chen", "message": "..."},
    {"lead": "Test_HighValueMatch", "message": "..."}
  ],
  "flagged_for_review": [
    {"name": "Test_MissingSize", "company": "Test Inc", "issue": "Missing company_size", "score": 5.2}
  ],
  "errors": [
    {"lead": "Test_NameOnly", "error": "Missing required fields: name, company_size, industry, source, last_interaction_date"}
  ]
}
```

### 6.2 Report Builder (utils/report_builder.py)
```python
def build_report(results: List[LeadResult], metadata: dict) -> dict:
    """Build complete output report."""
    # Calculate summary stats
    # Sort by priority/score
    # Generate priority queue
    # Select sample messages
    # Identify flagged leads
    # Return structured report
```

---

## Phase 7: Testing & Validation (Day 5)

### 7.1 Test with Training Data (30 leads)
```bash
python main.py --input leads_training.csv --output output_training.json
```
- Verify all 30 leads processed
- Check scoring consistency
- Review LLM reasoning quality
- Adjust rubric if needed

### 7.2 Test with Edge Cases (20 leads)
```bash
python main.py --input leads_testing.csv --output output_testing.json
```
- Verify graceful handling of:
  - Missing company_size ("NA", empty)
  - Missing names
  - Unknown industries
  - Extreme sizes (1, 50000)
  - Stale dates (2022)
  - Missing dates/sources
- Check error logging
- Ensure no crashes

### 7.3 Production Scale Test (100 leads)
```bash
python main.py --input leads_full_scale_100.csv --output output_full_scale.json
```
- Verify 100 leads processed end-to-end
- Check batch processing efficiency
- Validate report completeness
- Measure runtime (< 5 minutes target)

---

## Phase 8: Documentation & Polish (Day 5-6)

### 8.1 README.md (1 page max)
```markdown
# Lead Intelligence System

## Quick Start
```bash
pip install -r requirements.txt
cp .env.example .env  # Add API key
python main.py --input leads.csv --output report.json
```

## Qualification Rubric
[2-3 sentences explaining your rubric]

## Known Limitations
- [List edge cases, assumptions, constraints]
```

### 8.2 Code Quality
- Add type hints
- Docstrings for all public functions
- Consistent formatting (black/ruff)
- Comments for complex logic

### 8.3 Final Verification Checklist
- [ ] Processes 100+ leads without crashes
- [ ] Batched LLM calls (not per-lead)
- [ ] Error handling for API failures
- [ ] Handles missing/invalid data gracefully
- [ ] Output report has all required fields
- [ ] Messages are personalized (not generic)
- [ ] README explains how to run
- [ ] Rubric documented and defensible
- [ ] No API keys in repo

---

## Phase 9: Submission (Day 6-7)

### 9.1 Package Deliverables
```
lead-qualifier/
├── main.py
├── config.yaml
├── leads_training.csv (or your sample)
├── output_report.json (from 100-lead run)
├── README.md
├── requirements.txt
└── utils/
```

### 9.2 Create Submission Zip
```bash
zip -r lead-qualifier-submission.zip lead-qualifier/
# Exclude: venv/, __pycache__/, .env, *.pyc
```

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
4. **Decision Thresholds**: Set qualified ≥ 7, review 5-7, rejected < 5
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