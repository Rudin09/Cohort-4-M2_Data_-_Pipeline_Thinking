"""Report Builder for Lead Intelligence System."""

import json
from datetime import date
from typing import List, Dict, Any
from utils.models import LeadResult, LeadScore
from utils.message_generator import generate_all_outreach


def build_report(results: List[LeadResult], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build complete output report from enriched lead results.
    
    Args:
        results: List of LeadResult objects
        metadata: Processing metadata
        
    Returns:
        Structured report dictionary
    """
    # Summary statistics
    total = len(results)
    qualified = sum(1 for lr in results if lr.score.decision == "QUALIFIED")
    review = sum(1 for lr in results if lr.score.decision == "REVIEW")
    rejected = sum(1 for lr in results if lr.score.decision == "REJECTED")
    
    # Common rejection reasons
    rejection_reasons = {}
    for lr in results:
        if lr.score.decision == "REJECTED":
            lowest = min(lr.score.factor_scores, key=lambda fs: fs.raw_score)
            reason = f"Low {lowest.name.replace("_", " ")} ({lowest.raw_score})"
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    
    common_reasons = [f"{reason} ({count})" for reason, count in 
                      sorted(rejection_reasons.items(), key=lambda x: -x[1])[:5]]
    
    # Priority queue (sorted by score descending)
    priority_queue = [
        {
            "name": lr.lead.name,
            "company": lr.lead.company,
            "score": lr.score.total_score,
            "priority": lr.score.priority
        }
        for lr in sorted(results, key=lambda x: -x.score.total_score)
    ]
    
    # Leads detail with LLM reasoning
    leads_detail = []
    for lr in results:
        lead_dict = lr.score.to_dict()
        if lr.llm_reasoning:
            lead_dict["llm_reasoning"] = lr.llm_reasoning
        leads_detail.append(lead_dict)
    
    # Generate personalized outreach messages
    leads_with_scores = [(lr.lead, lr.score) for lr in results]
    outreach_messages = generate_all_outreach(leads_with_scores)
    
    # Sample outreach messages (top 5 qualified)
    qualified_results = [lr for lr in results if lr.score.decision == "QUALIFIED"]
    sample_messages = []
    for lr in qualified_results[:5]:
        sample_messages.append({
            "lead": lr.lead.name,
            "message": outreach_messages.get(lr.lead.name, "")
        })
    
    # Flagged for review (missing data but scored)
    flagged = []
    for lr in results:
        issues = []
        if lr.lead.company_size is None:
            issues.append("Missing company_size")
        if not lr.lead.industry:
            issues.append("Missing industry")
        if not lr.lead.source:
            issues.append("Missing source")
        if lr.lead.last_interaction_date is None:
            issues.append("Missing last_interaction_date")
        if issues:
            flagged.append({
                "name": lr.lead.name,
                "company": lr.lead.company,
                "issue": "; ".join(issues),
                "score": lr.score.total_score
            })
    
    # Errors
    errors = []
    for lr in results:
        if lr.error:
            errors.append({
                "lead": lr.lead.name,
                "error": lr.error
            })
    
    return {
        "metadata": metadata,
        "summary": {
            "total_processed": total,
            "qualified_count": qualified,
            "review_count": review,
            "rejected_count": rejected,
            "qualified_percentage": round(qualified / total * 100, 1) if total > 0 else 0,
            "common_rejection_reasons": common_reasons
        },
        "leads": leads_detail,
        "priority_queue": priority_queue,
        "sample_outreach_messages": sample_messages,
        "flagged_for_review": flagged,
        "errors": errors
    }


def write_report(report: Dict[str, Any], output_path: str):
    """Write report to JSON file."""
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)


def build_summary_report(results: List[LeadResult]) -> Dict[str, Any]:
    """Build a lightweight summary for quick viewing."""
    total = len(results)
    qualified = sum(1 for lr in results if lr.score.decision == "QUALIFIED")
    review = sum(1 for lr in results if lr.score.decision == "REVIEW")
    rejected = sum(1 for lr in results if lr.score.decision == "REJECTED")
    
    return {
        "total": total,
        "qualified": qualified,
        "review": review,
        "rejected": rejected,
        "qualified_pct": round(qualified / total * 100, 1) if total > 0 else 0,
        "avg_score": round(sum(lr.score.total_score for lr in results) / total, 1) if total > 0 else 0
    }
