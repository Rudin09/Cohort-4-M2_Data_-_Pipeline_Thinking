import json
with open('lead_analyst_dashboard.ipynb') as f:
    data = json.load(f)
print('Notebook valid!')
print('Cells:', len(data['cells']))
for i, cell in enumerate(data['cells']):
    src_len = len(cell.get('source', []))
    print('  Cell {}: {} ({} lines)'.format(i+1, cell['cell_type'], src_len))