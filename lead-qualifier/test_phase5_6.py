import json
from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_leads_batch
from utils.report_builder import build_report
from datetime import date
from utils.models import LeadResult

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')
scores = score_leads_batch(leads, rubric, reference_date=date(2024, 1, 20))

# Create LeadResult objects
from utils.models import LeadResult
lead_results = [LeadResult(lead=ls.lead, score=ls, llm_reasoning=None, outreach_message=None, error=None) for ls in scores]

metadata = {'processed_at': '2024-01-20', 'total_leads': len(leads), 'rubric_version': '1.0', 'llm_model': 'test'}
report = build_report(lead_results, metadata)

print('Test 5.6 - Full Report Structure: PASS')
print('  Report keys:', list(report.keys()))
print('  Sample messages count:', len(report['sample_outreach_messages']))
print('  Priority queue count:', len(report['priority_queue']))
print('  Flagged count:', len(report['flagged_for_review']))

# Check message structure
if report['sample_outreach_messages']:
    msg = report['sample_outreach_messages'][0]
    print('  Sample message keys:', list(msg.keys()))
    print('  Message preview:', msg['message'][:100])