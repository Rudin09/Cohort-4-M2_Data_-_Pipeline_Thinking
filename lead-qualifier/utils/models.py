"""Data models for Lead Intelligence System."""

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class Lead:
    """Raw lead data from CSV."""
    name: str
    company: str
    company_size: Optional[int]
    industry: str
    source: str
    last_interaction_date: Optional[date]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lead":
        """Create Lead from dictionary (e.g., CSV row)."""
        return cls(
            name=data.get("name", ""),
            company=data.get("company", ""),
            company_size=data.get("company_size"),
            industry=data.get("industry", ""),
            source=data.get("source", ""),
            last_interaction_date=data.get("last_interaction_date"),
        )


@dataclass
class FactorScore:
    """Score breakdown for a single rubric factor."""
    name: str
    raw_score: int          # 1-10
    weight: float           # e.g., 0.25
    weighted_score: float   # raw_score * weight


@dataclass
class LeadScore:
    """Complete scoring result for a lead."""
    lead: Lead
    factor_scores: List[FactorScore]
    total_score: float      # 1-10 weighted average
    decision: str           # QUALIFIED / REVIEW / REJECTED
    priority: str           # HIGH / MEDIUM / LOW

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.lead.name,
            "company": self.lead.company,
            "company_size": self.lead.company_size,
            "industry": self.lead.industry,
            "source": self.lead.source,
            "last_interaction_date": self.lead.last_interaction_date.isoformat() if self.lead.last_interaction_date else None,
            "score": round(self.total_score, 1),
            "decision": self.decision,
            "priority": self.priority,
            "factor_breakdown": {
                fs.name: {"raw": fs.raw_score, "weight": fs.weight, "weighted": round(fs.weighted_score, 2)}
                for fs in self.factor_scores
            },
        }


@dataclass
class LeadResult:
    """Enriched lead result with LLM reasoning and outreach message."""
    lead: Lead
    score: LeadScore
    llm_reasoning: Optional[str] = None
    llm_review_note: Optional[str] = None
    outreach_message: Optional[str] = None
    error: Optional[str] = None