import json

with open('lead_analyst_dashboard.ipynb') as f:
    nb = json.load(f)

# Phase 4 cells to insert
phase4_cells = [
    {
        'cell_type': 'markdown',
        'metadata': {},
        'source': [
            '# ============================================================\n',
            '# 4. LLM INTEGRATION - PHASE 4\n',
            '# ============================================================\n',
            '\n',
            'This phase adds LLM enrichment to the deterministic scoring.\n',
            'Requires GROQ_API_KEY in .env file.\n',
            '\n',
            'Key Learning: Batched API calls with retry logic, JSON parsing,\n',
            'rate limit handling, and graceful fallback to deterministic scores.\n',
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
            '# 4. LLM INTEGRATION - PHASE 4\n',
            '# ============================================================\n',
            '\n',
            'print("=== PHASE 4: LLM INTEGRATION ===\\n")\n',
            '\n',
            '# Import LLM client\n',
            'from utils.llm_client import get_provider, enrich_leads_with_llm, BATCH_PROMPT\n',
            '\n',
            '# Load configuration\n',
            'with open(LEAD_QUALIFIER / "config.yaml") as f:\n',
            '    config = yaml.safe_load(f)\n',
            '\n',
            '# Get LLM provider\n',
            'provider = get_provider(config)\n',
            'print(f"LLM Provider: {type(provider).__name__}")\n',
            'print(f"   Model: {config[\"llm\"][\"model\"]}")\n',
            'print(f"   Batch Size: {config[\"llm\"][\"batch_size\"]}\\n")\n',
            '\n',
            '# Load leads and rubric\n',
            'leads = load_leads(str(LEAD_QUALIFIER / ".." / "leads_training.csv"))\n',
            'rubric = load_rubric(str(LEAD_QUALIFIER / "config.yaml"))\n',
            '\n',
            'print(f"Loading {len(leads)} leads for LLM enrichment...\\n")\n',
            '\n',
            '# Enrich leads with LLM reasoning\n',
            'enrichments = enrich_leads_with_llm(leads, config)\n',
            '\n',
            'print(f"LLM Enrichment Complete: {len(enrichments)} leads enriched\\n")\n',
            '\n',
            '# Convert to DataFrame for analysis\n',
            'results = []\n',
            'for s in enrichments:\n',
            '    if isinstance(s, dict):\n',
            '        results.append({\n',
            '            "name": s.get("name", ""),\n',
            '            "company": s.get("company", ""),\n',
            '            "total_score": s.get("total_score", 0),\n',
            '            "decision": s.get("decision", "REVIEW"),\n',
            '            "priority": s.get("priority", "MEDIUM"),\n',
            '            "llm_reasoning": s.get("reasoning", ""),\n',
            '        })\n',
            '    else:\n',
            '        results.append({\n',
            '            "name": s.lead.name,\n',
            '            "company": s.lead.company,\n',
            '            "total_score": s.total_score,\n',
            '            "decision": s.decision,\n',
            '            "priority": s.priority,\n',
            '            "llm_reasoning": s.llm_reasoning or "LLM enrichment failed - using fallback",\n',
            '        })\n',
            '\n',
            'results_df = pd.DataFrame(results)\n',
            '\n',
            'print("=== LLM Results Summary ===")\n',
            'print(f"Total enriched: {len(results_df)}")\n',
            'print(f"Qualified: {sum(results_df[\"decision\"] == \"QUALIFIED\")}")\n',
            'print(f"Review: {sum(results_df[\"decision\"] == \"REVIEW\")}")\n',
            'print(f"Rejected: {sum(results_df[\"decision\"] == \"REJECTED\")}\\n")\n',
            '\n',
            '# Show first 5 leads with LLM reasoning\n',
            'print("=== Sample LLM Reasoning ===")\n',
            'for _, row in results_df.head(5).iterrows():\n',
            '    print(f"  {row[\"name\"]} ({row[\"company\"]}):")\n',
            '    print(f"    Score: {row[\"total_score\"]} | {row[\"decision\"]} | {row[\"priority\"]}")\n',
            '    reason = row["llm_reasoning"][:150] if row["llm_reasoning"] else "No reasoning"\n',
            '    print(f"    LLM: {reason}...")\n',
            '    print()'
        ]
    },
    {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [
            '# Visualize LLM-enriched results\n',
            'import matplotlib.pyplot as plt\n',
            'import seaborn as sns\n',
            '\n',
            'fig, axes = plt.subplots(1, 2, figsize=(12, 5))\n',
            '\n',
            '# Decision distribution\n',
            'decision_counts = results_df["decision"].value_counts()\n',
            'axes[0].pie(decision_counts.values, labels=decision_counts.index, autopct="%1.1f%%",\n',
            '            colors=["#2ecc71", "#f39c12", "#e74c3c"])\n',
            'axes[0].set_title("Decision Distribution (LLM-Enriched)")\n',
            '\n',
            '# Score distribution\n',
            'axes[1].hist(results_df["total_score"], bins=20, edgecolor="black", alpha=0.7)\n',
            'axes[1].axvline(x=75, color="green", linestyle="--", label="Qualified (>=75)")\n',
            'axes[1].axvline(x=50, color="orange", linestyle="--", label="Review (>=50)")\n',
            'axes[1].set_xlabel("Total Score")\n',
            'axes[1].set_ylabel("Count")\n',
            'axes[1].set_title("Score Distribution (LLM-Enriched)")\n',
            'axes[1].legend()\n',
            '\n',
            'plt.tight_layout()\n',
            'plt.show()\n',
            '\n',
            'print("=== Phase 4 Complete ===")\n',
            'print("LLM enrichment integrated successfully!")\n',
            'print("Next: Phase 5 - Message Generation & Report Builder")'
        ]
    }
]

# Insert Phase 4 cells after Cell 22 (Edge Case Analysis) and before Cell 23 (Export & Sharing)
# Cell 22 is index 22, Cell 23 is index 23
# We want to insert at index 23 (before Export & Sharing)
insert_index = 23

for i, cell in enumerate(phase4_cells):
    nb['cells'].insert(insert_index + i, cell)

# Update markdown header to reflect Phase 1-4
nb['cells'][0]['source'][0] = '# Lead Intelligence System - Business Analyst Dashboard\n'
nb['cells'][0]['source'][1] = '\n'
nb['cells'][0]['source'][2] = '**Phase 1-4 Implementation Review**  \n'
nb['cells'][0]['source'][3] = 'Interactive exploration of data, rubric, scoring, LLM enrichment, and results.\n'
nb['cells'][0]['source'][4] = '\n'
nb['cells'][0]['source'][4] = '---\n'
nb['cells'][0]['source'][5] = '\n'
nb['cells'][0]['source'][6] = '## Quick Start\n'
nb['cells'][0]['source'][7] = '1. Run each cell in order (Shift+Enter)\n'
nb['cells'][0]['source'][8] = '2. Modify parameters in **Configuration** cells to explore\n'
nb['cells'][0]['source'][9] = '3. All visualizations update automatically\n'
nb['cells'][0]['source'][10] = '\n'
nb['cells'][0]['source'][11] = '**Prerequisites:** Run from `lead-qualifier` directory with venv activated\n'
nb['cells'][0]['source'][12] = '**Note:** Phase 4 requires GROQ_API_KEY in .env file\n'

# Write updated notebook
with open('lead_analyst_dashboard.ipynb', 'w') as f:
    json.dump(nb, f, indent=2)

print('Notebook updated with Phase 4!')
print(f'Total cells: {len(nb["cells"])}')