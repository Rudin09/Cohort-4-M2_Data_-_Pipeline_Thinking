import json

with open('lead_analyst_dashboard.ipynb') as f:
    nb = json.load(f)

# Phase 5 cells to insert
phase5_cells = [
    {
        'cell_type': 'markdown',
        'metadata': {},
        'source': [
            '# ============================================================\n',
            '# 5. MESSAGE GENERATION & REPORT BUILDER - PHASE 5\n',
            '# ============================================================\n',
            '\n',
            'This phase adds personalized outreach messages and enhanced reporting.\n',
            'Messages are tailored by priority level and industry.\n',
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
            '# 5. MESSAGE GENERATION & REPORT BUILDER - PHASE 5\n',
            '# ============================================================\n',
            '\n',
            'print("=== PHASE 5: MESSAGE GENERATION & REPORT BUILDER ===\\n")\n',
            '\n',
            '# Import message generator and report builder\n',
            'from utils.message_generator import generate_outreach, TEMPLATES, get_industry_config\n',
            'from utils.report_builder import build_report, build_summary_report\n',
            'from utils.models import LeadResult\n',
            '\n',
            'print("Available templates:", list(TEMPLATES.keys()))\n',
            '\n',
            '# Load leads and scores\n',
            'leads = load_leads(str(LEAD_QUALIFIER / ".." / "leads_training.csv"))\n',
            'rubric = load_rubric(str(LEAD_QUALIFIER / "config.yaml"))\n',
            'scores = score_leads_batch(leads, rubric, reference_date=date(2024, 1, 20))\n',
            '\n',
            '# Create LeadResult objects\n',
            'lead_results = [LeadResult(lead=ls.lead, score=ls, llm_reasoning=None, outreach_message=None, error=None) for ls in scores]\n',
            '\n',
            '# Build report with messages\n',
            'metadata = {\"processed_at\": "2024-01-20", \"total_leads\": len(leads), \"rubric_version\": "1.0", \"llm_model\": "test"}\n',
            'report = build_report(lead_results, metadata)\n',
            '\n',
            'print(f"Report built with {len(report[\"sample_outreach_messages\"])} sample messages")\n',
            'print(f"Priority queue: {len(report[\"priority_queue\"])} leads")\n',
            'print(f"Flagged for review: {len(report[\"flagged_for_review\"])}")\n',
            '\n',
            '# Show sample messages by priority\n',
            'print("\\n=== SAMPLE OUTREACH MESSAGES ===")\n',
            'for msg in report["sample_outreach_messages"]:\n',
            '    print(f"  {msg[\"lead\"]}:")\n',
            '    print(f"    {msg[\"message\"][:150]}...")\n',
            '    print()'
        ]
    },
    {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [
            '# Message templates by priority\n',
            'print("=== MESSAGE TEMPLATES BY PRIORITY ===")\n',
            'for priority, template in TEMPLATES.items():\n',
            '    print(f"\\n--- {priority} PRIORITY ---")\n',
            '    print(template[:300] + "...")\n',
            '\n',
            '# Industry-specific configurations\n',
            'print("\\n=== INDUSTRY-SPECIFIC CONFIGURATIONS ===")\n',
            'test_industries = ["SaaS", "FinTech", "HealthTech", "Cybersecurity", "Finance", "Healthcare", "Manufacturing", "Retail"]\n',
            'for industry in test_industries:\n',
            '    cfg = get_industry_config(industry)\n',
            '    print(f"{industry}: pain=\"{cfg[\"pain_point\"]}\", value=\"{cfg[\"value_prop\"]}\", ref=\"{cfg[\"reference_customer\"]}\")'
        ]
    },
    {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [
            '# Full report visualization\n',
            'import matplotlib.pyplot as plt\n',
            'import seaborn as sns\n',
            '\n',
            'fig, axes = plt.subplots(2, 2, figsize=(14, 10))\n',
            '\n',
            '# 1. Decision distribution\n',
            'decision_counts = pd.DataFrame(report["leads"])["decision"].value_counts()\n',
            'axes[0, 0].pie(decision_counts.values, labels=decision_counts.index, autopct="%1.1f%%",\n',
            '             colors=["#2ecc71", "#f39c12", "#e74c3c"])\n',
            'axes[0, 0].set_title("Decision Distribution")\n',
            '\n',
            '# 2. Priority distribution\n',
            'priority_counts = pd.DataFrame(report["leads"])["priority"].value_counts()\n',
            'axes[0, 1].pie(priority_counts.values, labels=priority_counts.index, autopct="%1.1f%%",\n',
            '             colors=["#e74c3c", "#f39c12", "#2ecc71"])\n',
            'axes[0, 1].set_title("Priority Distribution")\n',
            '\n',
            '# 3. Score distribution with messages\n',
            'leads_df = pd.DataFrame(report["leads"])\n',
            'axes[1, 0].hist(leads_df["score"], bins=20, edgecolor="black", alpha=0.7)\n',
            'axes[1, 0].axvline(x=75, color="green", linestyle="--", label="Qualified (>=75)")\n',
            'axes[1, 0].axvline(x=50, color="orange", linestyle="--", label="Review (>=50)")\n',
            'axes[1, 0].set_xlabel("Total Score")\n',
            'axes[1, 0].set_ylabel("Count")\n',
            'axes[1, 0].set_title("Score Distribution")\n',
            'axes[1, 0].legend()\n',
            '\n',
            '# 4. Messages by priority\n',
            'msg_priority = pd.DataFrame(report["sample_outreach_messages"])\n',
            'if len(msg_priority) > 0:\n',
            '    # Merge with leads to get priority\n',
            '    leads_df = pd.DataFrame(report["leads"])[["name", "priority"]]\n',
            '    msg_priority = msg_priority.merge(leads_df, left_on="lead", right_on="name")\n',
            '    msg_priority_counts = msg_priority["priority"].value_counts()\n',
            '    msg_priority_counts.plot(kind="bar", ax=axes[1, 1], color=["#e74c3c", "#f39c12", "#2ecc71"])\n',
            '    axes[1, 1].set_title("Sample Messages by Priority")\n',
            '    axes[1, 1].set_ylabel("Count")\n',
            '    axes[1, 1].tick_params(axis="x", rotation=0)\n',
            '\n',
            'plt.tight_layout()\n',
            'plt.show()\n',
            '\n',
            'print("=== Phase 5 Complete ===")\n',
            'print("Message generation and report builder integrated successfully!")\n',
            'print("Next: Phase 6 - Testing & Validation")'
        ]
    }
]

# Find the index of Phase 4 cells and insert Phase 5 after them
# Phase 4 cells are at indices 23, 24, 25
# Phase 5 should go after Phase 4 (after index 25) and before Export & Sharing
# Export & Sharing is now at index 26 (was 23 before Phase 4 insertion)

# Find "EXPORT & SHARING" cell
insert_index = None
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'markdown' and 'EXPORT' in ''.join(cell['source']):
        insert_index = i
        break

if insert_index is None:
    insert_index = len(nb['cells']) - 1  # Before last cell

print(f"Inserting Phase 5 at index {insert_index}")

for i, cell in enumerate(phase5_cells):
    nb['cells'].insert(insert_index + i, cell)

# Update header
nb['cells'][0]['source'][2] = '**Phase 1-5 Implementation Review**  \n'
nb['cells'][0]['source'][3] = 'Interactive exploration of data, rubric, scoring, LLM enrichment, messages, and results.\n'

# Write updated notebook
with open('lead_analyst_dashboard.ipynb', 'w') as f:
    json.dump(nb, f, indent=2)

print('Notebook updated with Phase 5!')
print(f'Total cells: {len(nb["cells"])}')