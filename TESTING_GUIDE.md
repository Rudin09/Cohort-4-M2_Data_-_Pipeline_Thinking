# Lead Intelligence System - Testing Guide

This document provides step-by-step verification tests for each phase of the implementation. Run these tests after completing each phase to verify success criteria.

---

## Prerequisites

```bash
# Activate virtual environment
cd lead-qualifier
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Verify dependencies
pip list | grep -E "pandas|pyyaml|requests|tenacity|python-dotenv"
```

Expected: All 5 packages installed.

---

## Phase 1: Project Setup & Environment

### Test 1.1: Project Structure
```bash
# From Mini Project root
ls -la lead-qualifier/
```
**Verify:**
- [ ] `main.py` exists
- [ ] `config.yaml` exists
- [ ] `requirements.txt` exists
- [ ] `README.md` exists
- [ ] `.env.example` exists
- [ ] `.gitignore` exists
- [ ] `leads.csv` exists (30 training leads)
- [ ] `utils/` directory with `__init__.py`, `models.py`, `data_loader.py`, `rubric_engine.py`, `llm_client.py`, `message_generator.py`, `report_builder.py`
- [ ] `tests/` directory with `__init__.py`, `test_rubric.py`, `test_data_validation.py`, `test_edge_cases.py`
- [ ] `venv/` directory exists

### Test 1.2: Virtual Environment & Dependencies
```bash
cd lead-qualifier
.\venv\Scripts\python.exe -c "import pandas, yaml, requests, tenacity, dotenv; print('All imports OK')"
```
**Verify:** No import errors.

### Test 1.3: Git Repository
```bash
cd lead-qualifier
git status
```
**Verify:** Clean working tree, on main branch.

### Test 1.4: Config File Loads
```bash
.\venv\Scripts\python.exe -c "
import yaml
with open('config.yaml') as f:
    c = yaml.safe_load(f)
print('Rubric factors:', list(c['rubric'].keys()))
print('Weights sum:', sum(v['weight'] for v in c['rubric'].values()))
print('Thresholds:', c['thresholds'])
print('LLM config:', c['llm'])
"
```
**Verify:**
- [ ] 5 rubric factors: `company_size`, `industry`, `recency`, `source_quality`, `budget_signals`
- [ ] Weights sum to 1.0
- [ ] Thresholds: qualified=75, review=50, rejected=0
- [ ] LLM config has provider, model, batch_size, timeout, temperature

### Test 1.5: Environment Template
```bash
cat .env.example
```
**Verify:** Contains placeholders for GROQ_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, LLM_MODEL, BATCH_SIZE, REQUEST_TIMEOUT.

---

## Phase 2: Rubric Design

### Test 2.1: Rubric Documentation in README
```bash
grep -A 30 "## Qualification Rubric" README.md
```
**Verify:** Table with 5 factors, weights, and tier descriptions.

### Test 2.2: Manual Rubric Test (5 Training Leads)
```bash
.\venv\Scripts\python.exe -c "
import pandas as pd, yaml
from datetime import datetime, date

with open('config.yaml') as f:
    config = yaml.safe_load(f)

rubric = config['rubric']
thresholds = config['thresholds']
df = pd.read_csv('leads.csv')

def score_factor(value, tiers, default):
    for tier in tiers:
        if 'range' in tier:
            lo, hi = tier['range']
            if lo <= value <= hi: return tier['score']
        elif 'days' in tier:
            lo, hi = tier['days']
            if lo <= value <= hi: return tier['score']
        elif 'industries' in tier:
            if value in tier['industries']: return tier['score']
        elif 'sources' in tier:
            if value in tier['sources']: return tier['score']
    return default

def days_since(date_str):
    if pd.isna(date_str) or date_str == '': return None
    try:
        d = datetime.strptime(str(date_str), '%Y-%m-%d').date()
        return (date.today() - d).days
    except: return None

weights = {k: v['weight'] for k, v in rubric.items()}

for i, row in df.head().iterrows():
    size = row['company_size']
    industry = row['industry']
    source = row['source']
    last_date = row['last_interaction_date']
    
    size_score = score_factor(size, rubric['company_size']['tiers'], rubric['company_size']['tiers'][-1]['default'])
    industry_score = score_factor(industry, rubric['industry']['tiers'], rubric['industry']['tiers'][-1]['default'])
    recency_days = days_since(last_date)
    recency_score = score_factor(recency_days, rubric['recency']['tiers'], rubric['recency']['tiers'][-1]['default']) if recency_days is not None else rubric['recency']['tiers'][-1]['default']
    source_score = score_factor(source, rubric['source_quality']['tiers'], rubric['source_quality']['tiers'][-1]['default'])
    
    budget_score = 3
    for tier in rubric['budget_signals']['tiers']:
        if 'condition' in tier:
            try:
                if eval(tier['condition'].replace('company_size', str(size)).replace('industry', repr(industry)).replace('source', repr(source))):
                    budget_score = tier['score']
                    break
            except: pass
    
    total = (size_score * weights['company_size'] + industry_score * weights['industry'] + recency_score * weights['recency'] + source_score * weights['source_quality'] + budget_score * weights['budget_signals']) * 10
    
    decision = 'QUALIFIED' if total >= thresholds['qualified'] else ('REVIEW' if total >= thresholds['review'] else 'REJECTED')
    print(f'{row[\"name\"]} ({row[\"company\"]}): Total={total:.1f} -> {decision}')
"
```
**Verify:** Scores match expected logic (see Phase 2 results in chat).

---

## Phase 3: Core Pipeline Implementation

### Test 3.1: Models Import
```bash
.\venv\Scripts\python.exe -c "
from utils.models import Lead, FactorScore, LeadScore, LeadResult
from datetime import date
l = Lead('Test', 'Co', 100, 'SaaS', 'Inbound demo request', date(2024,1,15))
print('Lead:', l.name, l.company)
fs = FactorScore('test', 10, 0.25, 2.5)
print('FactorScore:', fs.name, fs.raw_score)
ls = LeadScore(l, [fs], 85.0, 'QUALIFIED', 'HIGH')
print('LeadScore:', ls.total_score, ls.decision)
lr = LeadResult(l, ls, 'reasoning', 'message')
print('LeadResult:', lr.llm_reasoning)
print('All models OK')
"
```
**Verify:** No import errors, all dataclasses work.

### Test 3.2: Data Loader
```bash
.\venv\Scripts\python.exe -c "
from utils.data_loader import load_leads, get_validation_summary
leads = load_leads('../leads_training.csv')
print(f'Loaded {len(leads)} leads')
print(f'First: {leads[0].name}, {leads[0].company}, size={leads[0].company_size}')
summary = get_validation_summary(leads)
print('Validation:', summary)
"
```
**Verify:**
- [ ] Loads 29 leads (training data)
- [ ] First lead: Alice Chen, CloudScale AI, size=50
- [ ] Validation shows 29/29 complete records

### Test 3.3: Data Loader - Edge Cases (Testing Data)
```bash
.\venv\Scripts\python.exe -c "
from utils.data_loader import load_leads, get_validation_summary
leads = load_leads('../leads_testing.csv')
print(f'Loaded {len(leads)} leads')
summary = get_validation_summary(leads)
print('Validation:', summary)
# Check specific edge cases
for l in leads:
    if 'Missing' in l.name or 'Partial' in l.name or 'NameOnly' in l.name:
        print(f'  {l.name}: size={l.company_size}, industry={l.industry}, source={l.source}, date={l.last_interaction_date}')
"
```
**Verify:**
- [ ] Loads 20 leads
- [ ] Validation shows ~15 complete, 3 missing size, 2 missing date
- [ ] Edge case leads parsed without crashing

### Test 3.4: Rubric Engine
```bash
.\venv\Scripts\python.exe -c "
from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_lead
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')

# Test first 3 leads
for lead in leads[:3]:
    score = score_lead(lead, rubric, reference_date=date(2024, 1, 20))
    print(f'{lead.name} ({lead.company}): {score.total_score} -> {score.decision} ({score.priority})')
    for fs in score.factor_scores:
        print(f'  {fs.name}: raw={fs.raw_score}, weight={fs.weight}, weighted={fs.weighted_score:.2f}')
"
```
**Verify:**
- [ ] Scores match manual calculation
- [ ] Factor breakdown shows all 5 factors
- [ ] Decision and priority assigned correctly

### Test 3.5: Batch Scoring
```bash
.\venv\Scripts\python.exe -c "
from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_leads_batch
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')
scores = score_leads_batch(leads, rubric, reference_date=date(2024, 1, 20))

qualified = sum(1 for s in scores if s.decision == 'QUALIFIED')
review = sum(1 for s in scores if s.decision == 'REVIEW')
rejected = sum(1 for s in scores if s.decision == 'REJECTED')
print(f'Total: {len(scores)}, Qualified: {qualified}, Review: {review}, Rejected: {rejected}')
"
```
**Verify:** Batch processes all leads, correct counts.

### Test 3.6: Main CLI - Training Data
```bash
.\venv\Scripts\python.exe main.py --input ../leads_training.csv --output output_training.json --verbose
```
**Verify:**
- [ ] Runs without errors
- [ ] Output file created: `output_training.json`
- [ ] Console shows summary with counts

### Test 3.7: Main CLI - Testing Data (Edge Cases)
```bash
.\venv\Scripts\python.exe main.py --input ../leads_testing.csv --output output_testing.json --verbose
```
**Verify:**
- [ ] Runs without errors (no crashes on missing data)
- [ ] Output file created: `output_testing.json`
- [ ] `flagged_for_review` array populated
- [ ] `errors` array empty

### Test 3.8: Main CLI - Full Scale (100 Leads)
```bash
.\venv\Scripts\python.exe main.py --input ../leads_full_scale_100.csv --output output_report.json --verbose
```
**Verify:**
- [ ] Runs without errors
- [ ] Output file created: `output_report.json`
- [ ] Processes 100 leads

### Test 3.9: Output Report Structure Validation
```bash
.\venv\Scripts\python.exe -c "
import json
with open('output_report.json') as f:
    r = json.load(f)

required = ['metadata', 'summary', 'leads', 'priority_queue', 'sample_outreach_messages', 'flagged_for_review', 'errors']
for field in required:
    status = 'OK' if field in r else 'MISSING'
    print(f'  {field}: {status}')

print()
print('Metadata keys:', list(r['metadata'].keys()))
print('Summary keys:', list(r['summary'].keys()))
print('Leads count:', len(r['leads']))
print('Priority queue count:', len(r['priority_queue']))
print('Sample messages count:', len(r['sample_outreach_messages']))
print('Flagged count:', len(r['flagged_for_review']))
print('Errors count:', len(r['errors']))

# Check lead structure
lead = r['leads'][0]
print()
print('Sample lead keys:', list(lead.keys()))
print('Has factor_breakdown:', 'factor_breakdown' in lead)
"
```
**Verify:** All 7 required fields present, correct structure.

### Test 3.10: CLI Arguments
```bash
# Test help
.\venv\Scripts\python.exe main.py --help

# Test required input
.\venv\Scripts\python.exe main.py 2>&1 | head -5

# Test custom config
.\venv\Scripts\python.exe main.py --input ../leads_training.csv --output test.json --config config.yaml --batch-size 10 --reference-date 2024-01-20 --verbose
```
**Verify:**
- [ ] Help shows all arguments
- [ ] Missing `--input` shows error
- [ ] Custom arguments work

---

## Phase 4: LLM Integration (Requires API Key)

### Test 4.1: LLM Client Import
```bash
.\venv\Scripts\python.exe -c "
from utils.llm_client import get_provider, enrich_leads_with_llm, BATCH_PROMPT
print('LLM client imports OK')
"
```
**Verify:** No import errors.

### Test 4.2: Provider Factory (with API Key)
```bash
.\venv\Scripts\python.exe -c "
from dotenv import load_dotenv
load_dotenv()

import yaml
from utils.llm_client import get_provider

with open('config.yaml') as f:
    config = yaml.safe_load(f)

provider = get_provider(config)
print('Provider:', type(provider).__name__)
print('Model:', config['llm']['model'])
"
```
**Verify:** Factory returns GroqProvider with correct model.

### Test 4.3: Batched Prompt Generation
```bash
.\venv\Scripts\python.exe -c "
from utils.llm_client import BATCH_PROMPT
from utils.data_loader import load_leads

leads = load_leads('../leads_training.csv')[:3]
prompt = BATCH_PROMPT.format(n=len(leads), leads_json='[...]')
print('Prompt length:', len(prompt))
print('Contains rubric:', 'Company size fit' in prompt)
print('Contains JSON output instruction:', 'JSON array' in prompt)
"
```
**Verify:** Prompt template includes rubric, requests JSON output.

### Test 4.4: Retry Logic & Rate Limit Handling
```bash
.\venv\Scripts\python.exe -c "
from tenacity import retry, stop_after_attempt, wait_exponential
print('Tenacity retry decorators available')
"
```
**Verify:** Tenacity imported correctly.

### Test 4.5: LLM Enrichment End-to-End (Training Data)
```bash
.\venv\Scripts\python.exe main.py --input ../leads_training.csv --output output_training_llm.json --reference-date 2024-01-20
```
**Verify:**
- [ ] Runs without errors
- [ ] Output file created: `output_training_llm.json`
- [ ] All 29 leads have `llm_reasoning` field populated
- [ ] Rate limits handled with retries (429 responses)

### Test 4.6: Verify LLM Reasoning Quality
```bash
.\venv\Scripts\python.exe -c "
import json
with open('output_training_llm.json') as f:
    r = json.load(f)

print('Summary:', r['summary'])
print()
print('Sample LLM Reasoning:')
for lead in r['leads'][:3]:
    print(f\"  {lead['name']} ({lead['company']}):\")
    print(f\"    Score: {lead['score']} | {lead['decision']} | {lead['priority']}\")
    if 'llm_reasoning' in lead and lead['llm_reasoning']:
        print(f\"    LLM: {lead['llm_reasoning'][:100]}...\")
    print()
"
```
**Verify:**
- [ ] All leads have `llm_reasoning` field
- [ ] Reasoning references specific lead details (industry, size, source)
- [ ] Reasoning is 2-3 sentences
- [ ] No "fallback" messages for successful calls

### Test 4.7: LLM Enrichment with Rate Limit Retries
```bash
.\venv\Scripts\python.exe main.py --input ../leads_training.csv --output output_training_llm2.json --reference-date 2024-01-20 --verbose 2>&1 | grep -E "(429|Retrying|Groq API returned)"
```
**Verify:**
- [ ] 429 rate limit responses handled
- [ ] Retries with exponential backoff (8s, 28s, etc.)
- [ ] Eventually succeeds with "Groq API returned X results"

### Test 4.8: Fallback on LLM Failure
```bash
.\venv\Scripts\python.exe -c "
from utils.llm_client import enrich_leads_with_llm
from utils.data_loader import load_leads
import yaml

with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Temporarily break config to test fallback
config['llm']['model'] = 'invalid-model'
leads = load_leads('../leads_training.csv')[:3]
results = enrich_leads_with_llm(leads, config)

for r in results:
    print(f\"{r['name']}: {r.get('reasoning', 'NO REASONING')[:80]}...\")
"
```
**Verify:**
- [ ] Returns fallback reasoning ("LLM enrichment failed - using fallback")
- [ ] Doesn't crash
- [ ] Returns results for all leads

---

## Phase 5: Outreach Message Generation

### Test 5.1: Message Generator Import
```bash
.\venv\Scripts\python.exe -c "
from utils.message_generator import generate_outreach, TEMPLATES
print('Templates:', list(TEMPLATES.keys()))
print('Message generator imports OK')
"
```
**Verify:** Templates for high/medium/low priority exist.

### Test 5.2: Message Generation (Deterministic)
```bash
.\venv\Scripts\python.exe -c "
from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_lead
from utils.message_generator import generate_outreach
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')
lead = leads[0]
score = score_lead(lead, rubric, reference_date=date(2024, 1, 20))
message = generate_outreach(lead, score)
print('Message for', lead.name)
print(message[:200])
print('...')
print('Contains name:', lead.name in message)
print('Contains company:', lead.company in message)
print('Contains industry:', lead.industry in message)
"
```
**Verify:** Message personalized with lead details (name, company, industry, size, source).

### Test 5.3: All Priority Templates
```bash
.\venv\Scripts\python.exe -c "
from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_leads_batch
from utils.message_generator import generate_outreach
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')
scores = score_leads_batch(leads, rubric, reference_date=date(2024, 1, 20))

for priority in ['HIGH', 'MEDIUM', 'LOW']:
    matching = [s for s in scores if s.priority == priority]
    if matching:
        lead = matching[0].lead
        score = matching[0]
        msg = generate_outreach(lead, score)
        print(f'=== {priority} PRIORITY ===')
        print(f'{lead.name} ({lead.company}):')
        print(msg[:200])
        print('...')
        print()
"
```
**Verify:** Each priority uses different template with appropriate tone.

### Test 5.4: Industry-Specific Personalization
```bash
.\venv\Scripts\python.exe -c "
from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_lead
from utils.message_generator import generate_outreach, get_industry_config
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')

# Test different industries
industries_tested = set()
for lead in leads:
    if lead.industry not in industries_tested:
        industries_tested.add(lead.industry)
        score = score_lead(lead, rubric, reference_date=date(2024, 1, 20))
        msg = generate_outreach(lead, score)
        cfg = get_industry_config(lead.industry)
        print(f'{lead.industry}: pain_point="{cfg[\"pain_point\"]}" value_prop="{cfg[\"value_prop\"]}"')
        print(f'  Message contains industry: {lead.industry in msg}')
        print()
"
```
**Verify:** Messages reference industry-specific pain points and value propositions.

### Test 5.5: Report Builder Import
```bash
.\venv\Scripts\python.exe -c "
from utils.report_builder import build_report, write_report, build_summary_report
print('Report builder imports OK')
"
```
**Verify:** No import errors.

### Test 5.6: Full Report Structure with Messages
```bash
.\venv\Scripts\python.exe -c "
import json
from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_leads_batch
from utils.report_builder import build_report
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')
scores = score_leads_batch(leads, rubric, reference_date=date(2024, 1, 20))

# Create LeadResult objects
from utils.models import LeadResult
lead_results = [LeadResult(lead=ls.lead, score=ls, llm_reasoning=None, outreach_message=None, error=None) for ls in scores]

metadata = {'processed_at': '2024-01-20', 'total_leads': len(leads), 'rubric_version': '1.0', 'llm_model': 'test'}
report = build_report(lead_results, metadata)

print('Report keys:', list(report.keys()))
print('Sample messages count:', len(report['sample_outreach_messages']))
print('Priority queue count:', len(report['priority_queue']))
print('Flagged count:', len(report['flagged_for_review']))

# Check message structure
if report['sample_outreach_messages']:
    msg = report['sample_outreach_messages'][0]
    print('Sample message keys:', list(msg.keys()))
    print('Message preview:', msg['message'][:100])
"
```
**Verify:** Report includes all required fields with personalized messages.

### Test 5.7: Full Pipeline with Messages (Deterministic)
```bash
.\venv\Scripts\python.exe main.py --input ../leads_training.csv --output output_training_phase5.json --reference-date 2024-01-20 --no-llm
```
**Verify:**
- [ ] Runs without errors
- [ ] Output file created: `output_training_phase5.json`
- [ ] `sample_outreach_messages` contains 5 personalized messages
- [ ] Messages reference specific lead details (name, company, industry, size, source)
- [ ] Priority queue sorted by score descending

### Test 5.8: Full Pipeline with LLM + Messages
```bash
.\venv\Scripts\python.exe main.py --input ../leads_training.csv --output output_training_phase5_llm.json --reference-date 2024-01-20
```
**Verify:**
- [ ] Runs without errors
- [ ] Output file created: `output_training_phase5_llm.json`
- [ ] `sample_outreach_messages` contains personalized messages
- [ ] `leads` array includes `llm_reasoning` field
- [ ] All 7 required report fields present

### Test 5.9: Message Quality Verification
```bash
.\venv\Scripts\python.exe -c "
import json
with open('output_training_phase5.json') as f:
    r = json.load(f)

print('Sample messages:')
for msg in r['sample_outreach_messages']:
    print(f\"  {msg['lead']}:\")
    print(f\"    {msg['message'][:150]}...\")
    print()
"
```
**Verify:**
- [ ] Messages are personalized (not generic)
- [ ] Reference specific lead details (name, company, industry, size, source)
- [ ] Industry-specific pain points and value propositions
- [ ] Appropriate tone for priority level (HIGH=direct, MEDIUM=informative, LOW=resource)

---

## Phase 6: Report Generation

### Test 6.1: Report Builder Import
```bash
.\venv\Scripts\python.exe -c "
from utils.report_builder import build_report, write_report
print('Report builder imports OK')
"
```
**Verify:** No import errors.

### Test 6.2: Full Report Structure
```bash
.\venv\Scripts\python.exe -c "
import json
from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_leads_batch
from utils.report_builder import build_report
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')
scores = score_leads_batch(leads, rubric, reference_date=date(2024, 1, 20))

metadata = {'processed_at': '2024-01-20', 'total_leads': len(leads), 'rubric_version': '1.0', 'llm_model': 'test'}
report = build_report(scores, metadata)

print('Report keys:', list(report.keys()))
print('Summary:', report['summary'])
print('Priority queue sorted:', all(report['priority_queue'][i]['score'] >= report['priority_queue'][i+1]['score'] for i in range(len(report['priority_queue'])-1)))
"
```
**Verify:** Report has all sections, priority queue sorted descending.

---

## Phase 7: End-to-End Testing

### Test 7.1: Complete Pipeline - Training
```bash
.\venv\Scripts\python.exe main.py --input ../leads_training.csv --output output_training.json --reference-date 2024-01-20
.\venv\Scripts\python.exe -c "
import json
with open('output_training.json') as f: r = json.load(f)
print('Training:', r['summary'])
"
```

### Test 7.2: Complete Pipeline - Testing (Edge Cases)
```bash
.\venv\Scripts\python.exe main.py --input ../leads_testing.csv --output output_testing.json --reference-date 2024-01-20
.\venv\Scripts\python.exe -c "
import json
with open('output_testing.json') as f: r = json.load(f)
print('Testing:', r['summary'])
print('Flagged:', len(r['flagged_for_review']))
for f in r['flagged_for_review']: print('  ', f['name'], f['issue'], f['score'])
"
```

### Test 7.3: Complete Pipeline - Full Scale (Submission)
```bash
.\venv\Scripts\python.exe main.py --input ../leads_full_scale_100.csv --output output_report.json --reference-date 2024-01-20
.\venv\Scripts\python.exe -c "
import json
with open('output_report.json') as f: r = json.load(f)
print('Full Scale:', r['summary'])
print('Top 5:', [(l['name'], l['score']) for l in r['priority_queue'][:5]])
"
```

---

## Phase 8: Documentation & Polish

### Test 8.1: README Completeness
```bash
grep -E "## (Quick Start|Qualification Rubric|Configuration|Data Files|Output Report|Known Limitations|Project Structure)" README.md
```
**Verify:** All sections present.

### Test 8.2: Code Quality
```bash
# Check type hints
grep -r "def " utils/ | grep -v "__pycache__" | head -10

# Check docstrings
grep -A 2 "^def " utils/data_loader.py | head -20
```
**Verify:** Functions have type hints and docstrings.

### Test 8.3: No Secrets in Repo
```bash
git status
grep -r "API_KEY" . --exclude-dir=venv --exclude="*.example" 2>/dev/null || echo "No API keys found"
```
**Verify:** No API keys committed.

---

## Phase 9: Submission Package

### Test 9.1: Create Submission Zip
```bash
cd lead-qualifier
zip -r ../lead-qualifier-submission.zip . \
  -x "venv/*" "__pycache__/*" ".env" "*.pyc" "*.log" ".pytest_cache/*" ".coverage" "output_*.json"
```

### Test 9.2: Verify Zip Contents
```bash
unzip -l ../lead-qualifier-submission.zip | grep -E "(main\.py|config\.yaml|README\.md|requirements\.txt|utils/|output_report\.json)"
```
**Verify:** Contains source, config, README, requirements, utils/, and output_report.json.

---

## Quick Reference: All Test Commands

```bash
# Phase 1
cd lead-qualifier && .\venv\Scripts\python.exe -c "import pandas, yaml, requests, tenacity, dotenv; print('OK')"

# Phase 2
.\venv\Scripts\python.exe -c "import yaml; c=yaml.safe_load(open('config.yaml')); print('Factors:', list(c['rubric'].keys()), 'Weights:', sum(v['weight'] for v in c['rubric'].values()))"

# Phase 3
.\venv\Scripts\python.exe main.py --input ../leads_training.csv --output output_training.json --reference-date 2024-01-20
.\venv\Scripts\python.exe main.py --input ../leads_testing.csv --output output_testing.json --reference-date 2024-01-20
.\venv\Scripts\python.exe main.py --input ../leads_full_scale_100.csv --output output_report.json --reference-date 2024-01-20

# Phase 4-6 (after implementation)
.\venv\Scripts\python.exe -c "from utils.llm_client import get_provider; from utils.message_generator import generate_outreach; from utils.report_builder import build_report; print('All Phase 4-6 modules OK')"

# Final verification
.\venv\Scripts\python.exe -c "
import json
with open('output_report.json') as f: r = json.load(f)
required = ['metadata', 'summary', 'leads', 'priority_queue', 'sample_outreach_messages', 'flagged_for_review', 'errors']
print('All fields present:', all(f in r for f in required))
print('Leads:', len(r['leads']), '| Qualified:', r['summary']['qualified_count'], '| Review:', r['summary']['review_count'], '| Rejected:', r['summary']['rejected_count'])
"
```

---

## Success Criteria Checklist

| Phase | Criteria | Test Command | Pass? |
|-------|----------|--------------|-------|
| 1 | Project structure complete | `ls lead-qualifier/` | ☐ |
| 1 | Dependencies installed | `pip list \| grep -E "pandas\|pyyaml\|requests\|tenacity\|python-dotenv"` | ☐ |
| 1 | Config loads correctly | Test 1.4 | ☐ |
| 2 | Rubric documented in README | `grep "## Qualification Rubric" README.md` | ☐ |
| 2 | Rubric weights sum to 100% | Test 1.4 | ☐ |
| 3 | Models work | Test 3.1 | ☐ |
| 3 | Data loader handles CSV | Test 3.2 | ☐ |
| 3 | Data loader handles edge cases | Test 3.3 | ☐ |
| 3 | Rubric engine scores correctly | Test 3.4 | ☐ |
| 3 | Batch scoring works | Test 3.5 | ☐ |
| 3 | CLI works on training data | Test 3.6 | ☐ |
| 3 | CLI handles edge cases | Test 3.7 | ☐ |
| 3 | CLI works on 100 leads | Test 3.8 | ☐ |
| 3 | Output report has all fields | Test 3.9 | ☐ |
| 3 | CLI args work | Test 3.10 | ☐ |
| 4 | LLM client imports | Test 4.1 | ☐ |
| 4 | Provider factory works | Test 4.2 | ☐ |
| 4 | Batched prompt correct | Test 4.3 | ☐ |
| 5 | Message generator works | Test 5.2 | ☐ |
| 6 | Report builder works | Test 6.2 | ☐ |
| 7 | Full pipeline training | Test 7.1 | ☐ |
| 7 | Full pipeline testing | Test 7.2 | ☐ |
| 7 | Full pipeline 100 leads | Test 7.3 | ☐ |
| 8 | README complete | Test 8.1 | ☐ |
| 8 | Code has type hints/docstrings | Test 8.2 | ☐ |
| 8 | No secrets in repo | Test 8.3 | ☐ |
| 9 | Submission zip created | Test 9.1 | ☐ |
| 9 | Zip has required files | Test 9.2 | ☐ |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in venv |
| `config.yaml` not found | Run from `lead-qualifier/` directory |
| `leads.csv` not found | Use `../leads_training.csv` from `lead-qualifier/` |
| Recency scores seem wrong | Use `--reference-date 2024-01-20` for consistent results |
| LLM errors | Add API key to `.env`, check provider in `config.yaml` |
| Permission denied on zip | Run from `lead-qualifier/` directory |

---

## Reference Dates for Consistent Testing

| Dataset | Recommended Reference Date |
|---------|---------------------------|
| `leads_training.csv` | `2024-01-20` (max date in file) |
| `leads_testing.csv` | `2024-01-20` |
| `leads_full_scale_100.csv` | `2024-01-20` |

Use `--reference-date 2024-01-20` for reproducible results across runs.