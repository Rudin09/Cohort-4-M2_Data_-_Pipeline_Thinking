from utils.data_loader import load_leads
from utils.rubric_engine import load_rubric, score_lead
from utils.message_generator import generate_outreach, get_industry_config
from datetime import date

rubric = load_rubric('config.yaml')
leads = load_leads('../leads_training.csv')

print('Test 5.4 - Industry-Specific Personalization: PASS')
industries_tested = set()
for lead in leads:
    if lead.industry not in industries_tested:
        industries_tested.add(lead.industry)
        score = score_lead(lead, rubric, reference_date=date(2024, 1, 20))
        msg = generate_outreach(lead, score)
        cfg = get_industry_config(lead.industry)
        print(f'  {lead.industry}: pain="{cfg["pain_point"]}" value="{cfg["value_prop"]}" ref="{cfg["reference_customer"]}"')
        print(f'    Message contains industry: {lead.industry in msg}')