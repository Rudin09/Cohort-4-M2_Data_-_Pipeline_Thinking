import json
with open('lead_analyst_dashboard.ipynb') as f:
    nb = json.load(f)
print('Total cells: ' + str(len(nb['cells'])))
print()
for i, cell in enumerate(nb['cells']):
    cell_type = cell['cell_type']
    if cell_type == 'markdown':
        source = ''.join(cell['source'])[:100]
    else:
        source = ''.join(cell['source'])[:100]
    print('Cell ' + str(i) + ': ' + cell_type + ' - ' + source + '...')