# ============================================================
# 4. LLM INTEGRATION - PHASE 4
# ============================================================
#
# This phase adds LLM enrichment to the deterministic scoring.
# Requires GROQ_API_KEY in .env file.
#
# Key Learning: Batched API calls with retry logic, JSON parsing,
# rate limit handling, and graceful fallback to deterministic scores.
#
# ============================================================

print("=== PHASE 4: LLM INTEGRATION ===\n")

# Import LLM client
from utils.llm_client import get_provider, enrich_leads_with_llm, BATCH_PROMPT

# Load configuration
with open(LEAD_QUALIFIER / "config.yaml") as f:
    config = yaml.safe_load(f)

# Get LLM provider
provider = get_provider(config)
print(f"✅ LLM Provider: {type(provider).__name__}")
print(f"   Model: {config['llm']['model']}")
print(f"   Batch Size: {config['llm']['batch_size']}\n")

# Load leads and rubric
leads = load_leads(str(LEAD_QUALIFIER / ".." / "leads_training.csv"))
rubric = load_rubric(str(LEAD_QUALIFIER / "config.yaml"))

print(f"📊 Loading {len(leads)} leads for LLM enrichment...\n")

# Enrich leads with LLM reasoning
enrichments = enrich_leads_with_llm(leads, config)

print(f"📈 LLM Enrichment Complete: {len(enrichments)} leads enriched\n")

# Convert to DataFrame for analysis
results = []
for s in enrichments:  # Note: enrichments returns LeadScore objects or dicts
    # Handle both LeadScore and dict formats
    if isinstance(s, dict):
        results.append({
            "name": s.get("name", ""),
            "company": s.get("company", ""),
            "total_score": s.get("total_score", 0),
            "decision": s.get("decision", "REVIEW"),
            "priority": s.get("priority", "MEDIUM"),
            "llm_reasoning": s.get("reasoning", ""),
        })
    else:
        results.append({
            "name": s.lead.name,
            "company": s.lead.company,
            "total_score": s.total_score,
            "decision": s.decision,
            "priority": s.priority,
            "llm_reasoning": s.llm_reasoning or "LLM enrichment failed - using fallback",
        })

results_df = pd.DataFrame(results)

print("=== LLM Results Summary ===")
print(f"Total enriched: {len(results_df)}")
print(f"Qualified: {sum(results_df['decision'] == 'QUALIFIED')}")
print(f"Review: {sum(results_df['decision'] == 'REVIEW')}")
print(f"Rejected: {sum(results_df['decision'] == 'REJECTED')}\n")

# Show first 5 leads with LLM reasoning
print("=== Sample LLM Reasoning ===")
for _, row in results_df.head(5).iterrows():
    print(f"  {row['name']} ({row['company']}):")
    print(f"    Score: {row['total_score']} | {row['decision']} | {row['priority']}")
    reason = row['llm_reasoning'][:150] if row['llm_reasoning'] else "No reasoning"
    print(f"    LLM: {reason}...")
    print()

# Visualize decision distribution
import matplotlib.pyplot as plt
import seaborn as sns

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Decision distribution
decision_counts = results_df['decision'].value_counts()
axes[0].pie(decision_counts.values, labels=decision_counts.index, autopct='%1.1f%%',
            colors=['#2ecc71', '#f39c12', '#e74c3c'])
axes[0].set_title('Decision Distribution (LLM-Enriched)')

# Score distribution
axes[1].hist(results_df['total_score'], bins=20, edgecolor='black', alpha=0.7)
axes[1].axvline(x=75, color='green', linestyle='--', label='Qualified (≥75)')
axes[1].axvline(x=50, color='orange', linestyle='--', label='Review (≥50)')
axes[1].set_xlabel('Total Score')
axes[1].set_ylabel('Count')
axes[1].set_title('Score Distribution (LLM-Enriched)')
axes[1].legend()

plt.tight_layout()
plt.show()

print("=== Phase 4 Complete ===")
print("LLM enrichment integrated successfully!")
print("Next: Phase 5 - Message Generation & Report Builder")
"