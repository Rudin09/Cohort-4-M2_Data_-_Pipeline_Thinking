"""Rubric engine for deterministic lead scoring."""

import yaml
from datetime import date
from typing import List, Dict, Any, Optional
from utils.models import Lead, LeadScore, FactorScore


def load_rubric(config_path: str) -> Dict[str, Any]:
    """Load rubric configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def score_lead(lead: Lead, rubric: Dict[str, Any], reference_date: Optional[date] = None) -> LeadScore:
    """
    Apply rubric to a single lead and return score breakdown.
    
    Args:
        lead: Lead to score
        rubric: Rubric configuration from config.yaml
        reference_date: Date to use for recency calculation (defaults to today)
        
    Returns:
        LeadScore with factor breakdown, total, decision, and priority
    """
    if reference_date is None:
        reference_date = date.today()
    
    factor_configs = rubric["rubric"]
    thresholds = rubric["thresholds"]
    
    factor_scores = []
    
    # Score each factor
    size_score = _score_company_size(lead.company_size, factor_configs["company_size"])
    factor_scores.append(FactorScore(
        name="company_size",
        raw_score=size_score,
        weight=factor_configs["company_size"]["weight"],
        weighted_score=size_score * factor_configs["company_size"]["weight"]
    ))
    
    industry_score = _score_industry(lead.industry, factor_configs["industry"])
    factor_scores.append(FactorScore(
        name="industry",
        raw_score=industry_score,
        weight=factor_configs["industry"]["weight"],
        weighted_score=industry_score * factor_configs["industry"]["weight"]
    ))
    
    recency_score = _score_recency(lead.last_interaction_date, factor_configs["recency"], reference_date)
    factor_scores.append(FactorScore(
        name="recency",
        raw_score=recency_score,
        weight=factor_configs["recency"]["weight"],
        weighted_score=recency_score * factor_configs["recency"]["weight"]
    ))
    
    source_score = _score_source(lead.source, factor_configs["source_quality"])
    factor_scores.append(FactorScore(
        name="source_quality",
        raw_score=source_score,
        weight=factor_configs["source_quality"]["weight"],
        weighted_score=source_score * factor_configs["source_quality"]["weight"]
    ))
    
    budget_score = _score_budget_signals(lead, factor_configs["budget_signals"])
    factor_scores.append(FactorScore(
        name="budget_signals",
        raw_score=budget_score,
        weight=factor_configs["budget_signals"]["weight"],
        weighted_score=budget_score * factor_configs["budget_signals"]["weight"]
    ))
    
    # Calculate total score (0-100)
    total_weighted = sum(fs.weighted_score for fs in factor_scores)
    total_score = total_weighted * 10  # Scale to 0-100
    
    # Determine decision
    if total_score >= thresholds["qualified"]:
        decision = "QUALIFIED"
    elif total_score >= thresholds["review"]:
        decision = "REVIEW"
    else:
        decision = "REJECTED"
    
    # Determine priority
    if total_score >= thresholds["qualified"]:
        priority = "HIGH"
    elif total_score >= thresholds["review"]:
        priority = "MEDIUM"
    else:
        priority = "LOW"
    
    return LeadScore(
        lead=lead,
        factor_scores=factor_scores,
        total_score=round(total_score, 1),
        decision=decision,
        priority=priority
    )


def _score_company_size(size: Optional[int], config: Dict[str, Any]) -> int:
    """Score company size factor."""
    if size is None:
        return config["tiers"][-1].get("default", 3)
    
    for tier in config["tiers"]:
        if "range" in tier:
            lo, hi = tier["range"]
            if lo <= size <= hi:
                return tier["score"]
    
    return config["tiers"][-1].get("default", 3)


def _score_industry(industry: str, config: Dict[str, Any]) -> int:
    """Score industry factor."""
    if not industry:
        return config["tiers"][-1].get("default", 3)
    
    industry_clean = industry.strip()
    
    for tier in config["tiers"]:
        if "industries" in tier:
            if industry_clean in tier["industries"]:
                return tier["score"]
    
    return config["tiers"][-1].get("default", 3)


def _score_recency(last_date: Optional[date], config: Dict[str, Any], reference_date: date) -> int:
    """Score recency factor based on days since last interaction."""
    if last_date is None:
        return config["tiers"][-1].get("default", 3)
    
    days_ago = (reference_date - last_date).days
    
    for tier in config["tiers"]:
        if "days" in tier:
            lo, hi = tier["days"]
            if lo <= days_ago <= hi:
                return tier["score"]
    
    return config["tiers"][-1].get("default", 3)


def _score_source(source: str, config: Dict[str, Any]) -> int:
    """Score source quality factor."""
    if not source:
        return config["tiers"][-1].get("default", 3)
    
    source_clean = source.strip()
    
    for tier in config["tiers"]:
        if "sources" in tier:
            if source_clean in tier["sources"]:
                return tier["score"]
    
    return config["tiers"][-1].get("default", 3)


def _score_budget_signals(lead: Lead, config: Dict[str, Any]) -> int:
    """Score budget/buying signals factor using conditional logic."""
    for tier in config["tiers"]:
        if "condition" in tier:
            condition = tier["condition"]
            try:
                # Evaluate condition with lead data
                context = {
                    "company_size": lead.company_size or 0,
                    "industry": lead.industry,
                    "source": lead.source,
                }
                if eval(condition, {"__builtins__": {}}, context):
                    return tier["score"]
            except Exception:
                continue
    
    return config["tiers"][-1].get("default", 3)


def score_leads_batch(leads: List[Lead], rubric: Dict[str, Any], reference_date: Optional[date] = None) -> List[LeadScore]:
    """Score multiple leads efficiently."""
    return [score_lead(lead, rubric, reference_date) for lead in leads]
