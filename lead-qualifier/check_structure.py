import os
print('=== PROJECT STRUCTURE CHECK ===')
files = [
    'main.py', 'config.yaml', 'requirements.txt', 'README.md', 
    '.env', '.env.example', '.gitignore', 'leads.csv',
    'utils/__init__.py', 'utils/models.py', 'utils/data_loader.py',
    'utils/rubric_engine.py', 'utils/llm_client.py', 
    'utils/message_generator.py', 'utils/report_builder.py',
    'tests/__init__.py', 'tests/test_rubric.py', 
    'tests/test_data_validation.py', 'tests/test_edge_cases.py'
]
for f in files:
    path = os.path.join('.', f)
    status = 'OK' if os.path.exists(path) else 'MISSING'
    print('  ' + status + ' ' + f)