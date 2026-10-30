import json
with open('output_testing_final.json') as f:
    r = json.load(f)

print('=== TESTING OUTPUT VALIDATION ===')
print('Summary:', r['summary'])
print()
print('Flagged for review:')
for f in r['flagged_for_review']:
    print('  ' + f['name'] + ' (' + f['company'] + '): ' + f['issue'] + ' - score=' + str(f['score']))
print()
print('Errors:', len(r['errors']))