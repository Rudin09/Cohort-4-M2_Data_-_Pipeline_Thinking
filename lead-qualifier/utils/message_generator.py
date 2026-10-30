"""Message Generator for personalized outreach."""

from typing import Dict, Any
from utils.models import Lead, LeadScore


# ============================================================
# Message Templates by Priority
# ============================================================

TEMPLATES = {
    "HIGH": """Hi {name},

I noticed {company} ({industry}, {size} employees) recently {source_detail}.
Given your focus on {industry_pain_point}, I thought you'd find 
our {value_prop} relevant.

Would you be open to a brief call this week to explore how we've helped 
similar {industry} companies like {reference_customer}?

Best regards,
[Your Name]
[Your Title]""",

    "MEDIUM": """Hi {name},

I came across {company} and noticed your recent {source_detail}.
As a {industry} company with {size} employees, you might be interested in 
how we help teams like yours with {value_prop}.

Happy to share a quick case study if relevant.

Best regards,
[Your Name]
[Your Title]""",

    "LOW": """Hi {name},

Thanks for your interest in {company}. I wanted to share a quick resource 
on {topic} that might be useful for your {industry} team.

Feel free to reach out if you have questions.

Best regards,
[Your Name]
[Your Title]"""
}


# ============================================================
# Industry-Specific Customization
# ============================================================

INDUSTRY_CONFIG = {
    "SaaS": {
        "pain_point": "scaling customer acquisition efficiently",
        "value_prop": "automated lead qualification platform",
        "reference_customer": "CloudScale AI",
        "topic": "SaaS growth metrics"
    },
    "FinTech": {
        "pain_point": "compliance and fraud detection",
        "value_prop": "real-time transaction monitoring",
        "reference_customer": "Payment Processing Inc",
        "topic": "FinTech regulatory updates"
    },
    "HealthTech": {
        "pain_point": "patient data security and interoperability",
        "value_prop": "HIPAA-compliant data platform",
        "reference_customer": "Healthcare Systems Ltd",
        "topic": "HealthTech data governance"
    },
    "Cybersecurity": {
        "pain_point": "threat detection and response time",
        "value_prop": "AI-powered security analytics",
        "reference_customer": "Cybersecurity Startup",
        "topic": "Cybersecurity threat trends"
    },
    "Finance": {
        "pain_point": "risk assessment and portfolio optimization",
        "value_prop": "predictive analytics for financial services",
        "reference_customer": "National Bank Corp",
        "topic": "Financial risk modeling"
    },
    "Healthcare": {
        "pain_point": "operational efficiency and patient outcomes",
        "value_prop": "healthcare analytics platform",
        "reference_customer": "Healthcare Systems Ltd",
        "topic": "Healthcare operations improvement"
    },
    "Manufacturing": {
        "pain_point": "supply chain optimization and quality control",
        "value_prop": "IoT-enabled manufacturing intelligence",
        "reference_customer": "Manufacturing Co",
        "topic": "Industry 4.0 adoption"
    },
    "Retail": {
        "pain_point": "customer personalization and inventory management",
        "value_prop": "retail analytics and demand forecasting",
        "reference_customer": "RetailWorks Solutions",
        "topic": "Retail digital transformation"
    },
    "Logistics": {
        "pain_point": "route optimization and delivery tracking",
        "value_prop": "logistics optimization platform",
        "reference_customer": "Logistics Global",
        "topic": "Supply chain visibility"
    },
    "EdTech": {
        "pain_point": "student engagement and learning outcomes",
        "value_prop": "adaptive learning platform",
        "reference_customer": "EdTech Innovations",
        "topic": "EdTech engagement strategies"
    },
    "Marketing": {
        "pain_point": "campaign attribution and ROI optimization",
        "value_prop": "marketing analytics dashboard",
        "reference_customer": "Digital Marketing Agency",
        "topic": "Marketing attribution models"
    },
    "Consulting": {
        "pain_point": "client delivery efficiency and knowledge management",
        "value_prop": "consulting project intelligence",
        "reference_customer": "Consulting Firm",
        "topic": "Consulting best practices"
    },
    "Real Estate": {
        "pain_point": "property valuation and market analysis",
        "value_prop": "real estate analytics platform",
        "reference_customer": "Real Estate Platform",
        "topic": "PropTech trends"
    },
    "Energy": {
        "pain_point": "grid optimization and renewable integration",
        "value_prop": "energy analytics platform",
        "reference_customer": "Energy Solutions",
        "topic": "Clean energy transition"
    },
    "default": {
        "pain_point": "business growth and efficiency",
        "value_prop": "business intelligence platform",
        "reference_customer": "Enterprise Solutions Corp",
        "topic": "Business optimization strategies"
    }
}


SOURCE_DETAILS = {
    "Inbound demo request": "requested a demo",
    "Referral": "was referred to us",
    "Sales call": "spoke with our team",
    "Webinar attendee": "attended our webinar",
    "Content download": "downloaded our content",
    "LinkedIn outreach": "connected on LinkedIn"
}


def get_industry_config(industry: str) -> Dict[str, str]:
    """Get industry-specific configuration."""
    return INDUSTRY_CONFIG.get(industry, INDUSTRY_CONFIG["default"])


def get_source_detail(source: str) -> str:
    """Convert source to natural language detail."""
    return SOURCE_DETAILS.get(source, "engaged with us")


def generate_outreach(lead: Lead, score: LeadScore) -> str:
    """
    Generate personalized outreach message for a lead.
    
    Args:
        lead: Lead object
        score: LeadScore object with decision and priority
        
    Returns:
        Personalized message string
    """
    # Select template based on priority
    priority = score.priority
    template = TEMPLATES.get(priority, TEMPLATES["LOW"])
    
    # Get industry-specific details
    industry_cfg = get_industry_config(lead.industry)
    source_detail = get_source_detail(lead.source)
    
    # Format company size
    size_str = f"{lead.company_size} employees" if lead.company_size else "your team"
    
    # Fill template
    message = template.format(
        name=lead.name,
        company=lead.company,
        industry=lead.industry,
        size=size_str,
        source_detail=source_detail,
        industry_pain_point=industry_cfg["pain_point"],
        value_prop=industry_cfg["value_prop"],
        reference_customer=industry_cfg["reference_customer"],
        topic=industry_cfg["topic"]
    )
    
    return message


def generate_all_outreach(leads_with_scores: list) -> Dict[str, str]:
    """
    Generate outreach messages for multiple leads.
    
    Args:
        leads_with_scores: List of (Lead, LeadScore) tuples
        
    Returns:
        Dictionary mapping lead name to message
    """
    messages = {}
    for lead, score in leads_with_scores:
        messages[lead.name] = generate_outreach(lead, score)
    return messages
