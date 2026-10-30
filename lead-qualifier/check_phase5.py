import json
with open('output_training_phase5.json') as f:
    r = json.load(f)
print('Summary:', r['summary'])
print()
print('Sample messages:')
for msg in r['sample_outreach_messages']:
    print(f"  {msg['lead']}: {msg['message'][:100]}...")
    print()