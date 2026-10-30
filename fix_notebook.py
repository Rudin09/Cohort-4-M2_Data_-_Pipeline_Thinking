import json

# Read the corrupted file as text
with open('lead_analyst_dashboard.ipynb', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the specific line - add missing quote
content = content.replace(
    '    print("\\n--- Qualified Leads ---")\\n",',
    '    "print(\\"\\\\n--- Qualified Leads ---\\")\\\\n",'
)

# Write fixed version
with open('lead_analyst_dashboard.ipynb', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed line 508')

# Validate
with open('lead_analyst_dashboard.ipynb', 'r', encoding='utf-8') as f:
    data = json.load(f)
print('Valid JSON!')
print('Cells:', len(data['cells']))