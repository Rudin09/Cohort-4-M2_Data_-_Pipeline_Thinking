"""Generate human-reviewable first-touch drafts for qualified leads."""

from typing import Dict, Optional, Sequence, Tuple

from utils.models import Lead, LeadScore


TEMPLATES = {
    "qualified_first_touch": """Hi {name},

I noticed {company_context}.{source_sentence}
If {pain_point} is a priority for your team, our {value_prop} may be relevant.
Would you be open to a brief conversation to see whether it could be a fit?

Best,
[Your Name]"""
}


INDUSTRY_CONFIG = {
    "SaaS": {
        "pain_point": "scaling customer acquisition efficiently",
        "value_prop": "automated lead qualification platform",
    },
    "FinTech": {
        "pain_point": "compliance and fraud detection",
        "value_prop": "real-time transaction monitoring",
    },
    "HealthTech": {
        "pain_point": "patient data security and interoperability",
        "value_prop": "healthcare data platform",
    },
    "Cybersecurity": {
        "pain_point": "threat detection and response time",
        "value_prop": "security analytics",
    },
    "Finance": {
        "pain_point": "risk assessment and portfolio optimization",
        "value_prop": "predictive analytics for financial services",
    },
    "Healthcare": {
        "pain_point": "operational efficiency and patient outcomes",
        "value_prop": "healthcare analytics platform",
    },
    "Manufacturing": {
        "pain_point": "supply chain optimization and quality control",
        "value_prop": "manufacturing intelligence",
    },
    "Retail": {
        "pain_point": "customer personalization and inventory management",
        "value_prop": "retail analytics and demand forecasting",
    },
    "Logistics": {
        "pain_point": "route optimization and delivery tracking",
        "value_prop": "logistics optimization platform",
    },
    "EdTech": {
        "pain_point": "student engagement and learning outcomes",
        "value_prop": "adaptive learning platform",
    },
    "Marketing": {
        "pain_point": "campaign attribution and ROI optimization",
        "value_prop": "marketing analytics dashboard",
    },
    "Consulting": {
        "pain_point": "client delivery efficiency and knowledge management",
        "value_prop": "consulting project intelligence",
    },
    "Real Estate": {
        "pain_point": "property valuation and market analysis",
        "value_prop": "real estate analytics platform",
    },
    "Energy": {
        "pain_point": "grid optimization and renewable integration",
        "value_prop": "energy analytics platform",
    },
    "default": {
        "pain_point": "business growth and efficiency",
        "value_prop": "business intelligence platform",
    },
}


SOURCE_DETAILS = {
    "Inbound demo request": "requested a demo",
    "Referral": "was referred to us",
    "Sales call": "spoke with our team",
    "Webinar attendee": "attended our webinar",
    "Content download": "downloaded our content",
    "LinkedIn outreach": "connected on LinkedIn",
}


def get_industry_config(industry: str) -> Dict[str, str]:
    """Get the configured industry-specific pain point and value proposition."""
    return INDUSTRY_CONFIG.get(industry, INDUSTRY_CONFIG["default"])


def get_source_detail(source: str) -> Optional[str]:
    """Return a known source description without inventing engagement details."""
    return SOURCE_DETAILS.get(source)


def generate_outreach(lead: Lead, score: LeadScore) -> Optional[str]:
    """Return a qualified-lead draft, or None when outreach is not appropriate."""
    if score.decision != "QUALIFIED":
        return None

    company_context = lead.company
    details = []
    if lead.industry:
        details.append(lead.industry)
    if lead.company_size is not None:
        details.append(f"approximately {lead.company_size} employees")
    if details:
        company_context = f"{company_context} ({', '.join(details)})"

    source_detail = get_source_detail(lead.source)
    source_sentence = (
        f" I saw that your team {source_detail}." if source_detail else ""
    )
    industry_config = get_industry_config(lead.industry)
    return TEMPLATES["qualified_first_touch"].format(
        name=lead.name or "there",
        company_context=company_context,
        source_sentence=source_sentence,
        pain_point=industry_config["pain_point"],
        value_prop=industry_config["value_prop"],
    )


def generate_all_outreach(
    leads_with_scores: Sequence[Tuple[Lead, LeadScore]],
) -> Dict[Tuple[str, str], str]:
    """Generate drafts only for qualified leads, keyed by name and company."""
    messages = {}
    for lead, score in leads_with_scores:
        message = generate_outreach(lead, score)
        if message is not None:
            messages[(lead.name, lead.company)] = message
    return messages
