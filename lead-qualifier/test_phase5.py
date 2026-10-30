# Phase 5 tests
from utils.message_generator import generate_outreach, TEMPLATES
print('Phase 5.1 - Message Generator Import: OK (templates: ' + str(list(TEMPLATES.keys())) + ')')

from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_lead
from utils.message_generator import generate_outreach
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')
lead = leads[0]
score = score_lead(lead, rubric, reference_date=date(2024, 1, 20))
message = generate_outreach(lead, score)
print('Phase 5.2 - Message Generation: OK')
print('  Contains name:', lead.name in message)
print('  Contains company:', lead.company in message)
print('  Contains industry:', lead.industry in message)

from utils.report_builder import build_report, write_report, build_summary_report
print('Phase 5.5 - Report Builder Import: OK')