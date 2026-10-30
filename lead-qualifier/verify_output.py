import json
with open('output_report.json') as f:
    r = json.load(f)

required = ['metadata', 'summary', 'leads', 'priority_queue', 'sample_outreach_messages', 'flagged_for_review', 'errors']
print('=== OUTPUT REPORT VALIDATION ===')
for field in required:
    status = 'OK' if field in r else 'MISSING'
    print('  ' + field + ': ' + status)

print()
print('Metadata keys:', list(r['metadata'].keys()))
print('Summary keys:', list(r['summary'].keys()))
print('Leads count:', len(r['leads']))
print('Priority queue count:', len(r['priority_queue']))
print('Sample messages count:', len(r['sample_outreach_messages']))
print('Flagged count:', len(r['flagged_for_review']))
print('Errors count:', len(r['errors']))

lead = r['leads'][0]
print()
print('Sample lead keys:', list(lead.keys()))
print('Has factor_breakdown:', 'factor_breakdown' in lead)
print('Has llm_reasoning:', 'llm_reasoning' in lead)

# Check priority queue is sorted
pq = r['priority_queue']
sorted_check = all(pq[i]['score'] >= pq[i+1]['score'] for i in range(len(pq)-1))
print('Priority queue sorted:', sorted_check)