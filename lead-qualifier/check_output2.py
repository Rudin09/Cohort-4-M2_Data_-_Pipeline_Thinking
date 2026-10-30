import json
with open('output_training_llm.json') as f:
    r = json.load(f)
print('Last 5 leads with LLM reasoning:')
for lead in r['leads'][-5:]:
    print(f"  {lead['name']} ({lead['company']}): score={lead['score']}, decision={lead['decision']}")
    if 'llm_reasoning' in lead and lead['llm_reasoning']:
        print(f"    LLM: {lead['llm_reasoning'][:200]}...")
    print()