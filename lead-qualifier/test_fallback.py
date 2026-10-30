from dotenv import load_dotenv
load_dotenv()

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
    reasoning = r.get('reasoning', 'NO REASONING')
    print(r['name'] + ': ' + reasoning[:80] + '...')