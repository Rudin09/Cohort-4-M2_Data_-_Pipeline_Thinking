"""Generate fact-grounded first-touch drafts for qualified leads."""

import hashlib
from typing import Dict, Optional, Sequence, Tuple

from utils.models import Lead, LeadScore


OUTREACH_VARIANTS = (
    (
        "fact_first",
        """Hi {name},

I noticed {company} in our lead records ({record_details}).
Would you be open to a short introductory conversation to see if there may be a fit?

Best,
[Your Name]""",
    ),
    (
        "question_first",
        """Hi {name},

Would a short introductory conversation be useful? The lead record lists {company} ({record_details}).
If so, could you share a suitable time?

Best,
[Your Name]""",
    ),
    (
        "direct_context",
        """Hi {name},

I'm reaching out about {company}. Our record includes: {record_details}.
If you're open to an introduction, could we set up a brief call to explore whether there may be a fit?

Best,
[Your Name]""",
    ),
)


def get_outreach_variant_id(lead: Lead, lead_id: Optional[str] = None) -> str:
    """Choose a reproducible message structure for a stable lead identifier."""
    variant_key = lead_id
    if variant_key is None:
        variant_key = "\x1f".join(
            (
                lead.name,
                lead.company,
                str(lead.company_size),
                lead.industry,
                lead.source,
                (
                    lead.last_interaction_date.isoformat()
                    if lead.last_interaction_date
                    else ""
                ),
            )
        )
    digest = hashlib.sha256(variant_key.encode("utf-8")).digest()
    variant_index = int.from_bytes(digest[:4], "big") % len(OUTREACH_VARIANTS)
    return OUTREACH_VARIANTS[variant_index][0]


def generate_outreach(
    lead: Lead,
    score: LeadScore,
    lead_id: Optional[str] = None,
) -> Optional[str]:
    """Return a qualified-lead draft grounded only in supplied lead details."""
    if score.decision != "QUALIFIED":
        return None

    record_details = []
    if lead.industry:
        record_details.append(f"{lead.industry} industry")
    if lead.company_size is not None:
        record_details.append(
            f"approximately {lead.company_size} employees"
        )
    details = "; ".join(record_details) or "the details provided"
    if lead.source:
        details = f"{details}; source: {lead.source}"

    variant_id = get_outreach_variant_id(lead, lead_id)
    template = next(
        template
        for candidate_id, template in OUTREACH_VARIANTS
        if candidate_id == variant_id
    )
    return template.format(
        name=lead.name or "there",
        company=lead.company or "your company",
        record_details=details,
    )


def generate_all_outreach(
    leads_with_scores: Sequence[Tuple[Lead, LeadScore]],
) -> Dict[Tuple[str, str], str]:
    """Generate qualified drafts keyed by name and company."""
    messages = {}
    for index, (lead, score) in enumerate(leads_with_scores):
        message = generate_outreach(lead, score, f"lead-{index:06d}")
        if message is not None:
            messages[(lead.name, lead.company)] = message
    return messages
