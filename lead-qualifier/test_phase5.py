from datetime import date

from utils.data_loader import load_leads
from utils.message_generator import (
    OUTREACH_VARIANTS,
    generate_outreach,
    get_outreach_variant_id,
)
from utils.rubric_engine import load_rubric, score_lead


rubric = load_rubric("config.yaml")
leads = load_leads("../leads_training.csv")
qualified = None
for lead in leads:
    score = score_lead(lead, rubric, reference_date=date(2024, 1, 20))
    if score.decision == "QUALIFIED":
        qualified = lead, score
        break
if qualified is None:
    raise ValueError("Training data has no qualified leads for message testing.")
lead, score = qualified
messages = {}
for index in range(100):
    lead_id = f"lead-{index:06d}"
    variant_id = get_outreach_variant_id(lead, lead_id)
    messages.setdefault(
        variant_id, generate_outreach(lead, score, lead_id)
    )

assert set(messages) == {variant_id for variant_id, _ in OUTREACH_VARIANTS}
assert all(
    lead.name in message
    and lead.company in message
    and lead.industry in message
    and lead.source in message
    for message in messages.values()
)
print("All three deterministic, fact-grounded outreach variants passed.")
