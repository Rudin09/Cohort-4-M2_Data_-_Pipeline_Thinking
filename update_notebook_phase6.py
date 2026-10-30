import json

with open('lead_analyst_dashboard.ipynb') as f:
    nb = json.load(f)

# Phase 6 cells to insert
phase6_cells = [
    {
        'cell_type': 'markdown',
        'metadata': {},
        'source': [
            '# ============================================================\n',
            '# 6. TESTING & VALIDATION - PHASE 6\n',
            '# ============================================================\n',
            '\n',
            'This phase validates the complete pipeline on all three datasets.\n',
            'Tests: Training (30), Testing (20 edge cases), Full Scale (100).\n',
            '\n',
            '---\n'
        ]
    },
    {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [
            '# ============================================================\n',
            '# 6. TESTING & VALIDATION - PHASE 6\n',
            '# ============================================================\n',
            '\n',
            'print("=== PHASE 6: TESTING & VALIDATION ===\\n")\n',
            '\n',
            '# Import subprocess to run CLI\n',
            'import subprocess\n',
            'import json\n',
            '\n',
            'def run_pipeline(input_file, output_file, no_llm=True):\n',
            '    \"\"\"Run the pipeline and return result.\"\"\"\n',
            '    cmd = [\n',
            '        str(LEAD_QUALIFIER / \"venv\" / \"Scripts\" / \"python.exe\"),\n',
            '        str(LEAD_QUALIFIER / \"main.py\"),\n',
            '        \"--input\", str(LEAD_QUALIFIER / \"..\" / input_file),\n',
            '        \"--output\", str(LEAD_QUALIFIER / output_file),\n',
            '        \"--reference-date\", \"2024-01-20\"\n',
            '    ]\n',
            '    if no_llm:\n',
            '        cmd.append(\"--no-llm\")\n',
            '    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(LEAD_QUALIFIER))\n',
            '    return result\n',
            '\n',
            '# Test 6.1: Training Data (30 leads)\n',
            'print(\"=== Test 6.1: Training Data (30 leads) ===\")\n',
            'result = run_pipeline(\"leads_training.csv\", \"output_training_final.json\")\n',
            'print(result.stdout[-500:])\n',
            'print(\"Return code:\", result.returncode)\n',
            '\n',
            '# Test 6.2: Testing Data (20 edge cases)\n',
            'print(\"\\n=== Test 6.2: Testing Data (20 edge cases) ===\")\n',
            'result = run_pipeline(\"leads_testing.csv\", \"output_testing_final.json\")\n',
            'print(result.stdout[-500:])\n',
            'print(\"Return code:\", result.returncode)\n',
            '\n',
            '# Test 6.3: Full Scale (100 leads) - FINAL SUBMISSION\n',
            'print(\"\\n=== Test 6.3: Full Scale (100 leads) ===\")\n',
            'result = run_pipeline(\"leads_full_scale_100.csv\", \"output_report.json\")\n',
            'print(result.stdout[-500:])\n',
            'print(\"Return code:\", result.returncode)'
        ]
    },
    {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [
            '# Validate all three outputs\n',
            'print(\"=== OUTPUT VALIDATION ===\\n\")\n',
            '\n',
            'for name, path in [\n',
            '    (\"Training\", \"output_training_final.json\"),\n',
            '    (\"Testing\", \"output_testing_final.json\"),\n',
            '    (\"Full Scale\", \"output_report.json\")\n',
            ']:\n',
            '    with open(LEAD_QUALIFIER / path) as f:\n',
            '        r = json.load(f)\n',
            '    \n',
            '    required = [\"metadata\", \"summary\", \"leads\", \"priority_queue\", \n',
            '                \"sample_outreach_messages\", \"flagged_for_review\", \"errors\"]\n',
            '    \n',
            '    print(f\"\\n=== {name} Report ===\")\n',
            '    for field in required:\n',
            '        status = \"OK\" if field in r else \"MISSING\"\n',
            '        print(f\"  {field}: {status}\")\n',
            '    \n',
            '    print(f\"  Leads: {len(r[\\\"leads\\\"])}\")\n',
            '    print(f\"  Qualified: {r[\\\"summary\\\"][\\\"qualified_count\\\"]} ({r[\\\"summary\\\"][\\\"qualified_percentage\\\"]}%)\")\n',
            '    print(f\"  Review: {r[\\\"summary\\\"][\\\"review_count\\\"]}\")\n',
            '    print(f\"  Rejected: {r[\\\"summary\\\"][\\\"rejected_count\\\"]}\")\n',
            '    print(f\"  Flagged: {len(r[\\\"flagged_for_review\\\"])}\")\n',
            '    print(f\"  Errors: {len(r[\\\"errors\\\"])}\")\n',
            '    \n',
            '    # Verify lead structure\n',
            '    lead = r[\"leads\"][0]\n',
            '    print(f\"  Lead keys: {list(lead.keys())}\")\n',
            '    print(f\"  Has factor_breakdown: {\\\"factor_breakdown\\\" in lead}\")'
        ]
    },
    {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [
            '# Edge case analysis\n',
            'print(\"\\n=== EDGE CASE ANALYSIS ===\")\n',
            '\n',
            'with open(LEAD_QUALIFIER / \"output_testing_final.json\") as f:\n',
            '    r = json.load(f)\n',
            '\n',
            'print(f\"Total: {r[\\\"summary\\\"][\\\"total_processed\\\"]}\")\n',
            'print(f\"Qualified: {r[\\\"summary\\\"][\\\"qualified_count\\\"]}\")\n',
            'print(f\"Review: {r[\\\"summary\\\"][\\\"review_count\\\"]}\")\n',
            'print(f\"Rejected: {r[\\\"summary\\\"][\\\"rejected_count\\\"]}\")\n',
            'print(f\"Flagged: {len(r[\\\"flagged_for_review\\\"])}\")\n',
            'print(f\"Errors: {len(r[\\\"errors\\\"])}\")\n',
            '\n',
            'print(\"\\nFlagged leads:\")\n',
            'for f in r[\"flagged_for_review\"]:\n',
            '    print(f\"  {f[\\\"name\\\"]} ({f[\\\"company\\\"]}): {f[\\\"issue\\\"]} - score={f[\\\"score\\\"]}\")'
        ]
    },
    {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [
            '# Final submission verification\n',
            'print(\"\\n=== FINAL SUBMISSION VERIFICATION ===\")\n',
            '\n',
            'with open(LEAD_QUALIFIER / \"output_report.json\") as f:\n',
            '    r = json.load(f)\n',
            '\n',
            'checks = {\n',
            '    \"All 7 required fields\": all(f in r for f in [\"metadata\", \"summary\", \"leads\", \"priority_queue\", \"sample_outreach_messages\", \"flagged_for_review\", \"errors\"]),\n',
            '    \"100 leads processed\": len(r[\"leads\"]) == 100,\n',
            '    \"Priority queue sorted\": all(r[\"priority_queue\"][i][\"score\"] >= r[\"priority_queue\"][i+1][\"score\"] for i in range(len(r[\"priority_queue\"])-1)),\n',
            '    \"Has factor_breakdown\": \"factor_breakdown\" in r[\"leads\"][0],\n',
            '    \"Has sample messages\": len(r[\"sample_outreach_messages\"]) >= 3,\n',
            '    \"No errors\": len(r[\"errors\"]) == 0,\n',
            '    \"Metadata complete\": all(k in r[\"metadata\"] for k in [\"processed_at\", \"total_leads\", \"rubric_version\", \"llm_model\", \"reference_date\"]),\n',
            '    \"Summary complete\": all(k in r[\"summary\"] for k in [\"total_processed\", \"qualified_count\", \"review_count\", \"rejected_count\", \"qualified_percentage\", \"common_rejection_reasons\"]),\n',
            '}\n',
            '\n',
            'all_passed = True\n',
            'for check, result in checks.items():\n',
            '    status = \"PASS\" if result else \"FAIL\"\n',
            '    if not result:\n',
            '        all_passed = False\n',
            '    print(f\"  {check}: {status}\")\n',
            '\n',
            'print(f\"\\nOverall: {\\\"ALL TESTS PASSED\\\" if all_passed else \\\"SOME TESTS FAILED\\\"}\")\n',
            '\n',
            'print(\"\\n=== Phase 6 Complete ===\")\n',
            'print(\"Pipeline validated on all three datasets!\")\n',
            'print(\"Ready for submission: output_report.json\")'
        ]
    }
]

# Find the index of Export & Sharing cell
insert_index = None
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'markdown' and 'EXPORT' in ''.join(cell['source']):
        insert_index = i
        break

if insert_index is None:
    insert_index = len(nb['cells']) - 1

print("Inserting Phase 6 at index " + str(insert_index))

for i, cell in enumerate(phase6_cells):
    nb['cells'].insert(insert_index + i, cell)

# Update header
nb['cells'][0]['source'][2] = '**Phase 1-6 Implementation Review**  \n'
nb['cells'][0]['source'][3] = 'Interactive exploration of data, rubric, scoring, LLM enrichment, messages, testing, and results.\n'

# Write updated notebook
with open('lead_analyst_dashboard.ipynb', 'w') as f:
    json.dump(nb, f, indent=2)

print('Notebook updated with Phase 6!')
print(f'Total cells: {len(nb[\"cells\"])}')