"""Report Builder for Lead Intelligence System."""

import json
from typing import List, Dict, Any
from utils.models import LeadResult
from utils.message_generator import generate_outreach


def _build_deterministic_reasoning(lead_result: LeadResult) -> str:
    """Explain a rubric result using its recorded factor scores."""
    factors = sorted(
        lead_result.score.factor_scores,
        key=lambda factor: (-factor.raw_score, factor.name),
    )
    factor_summary = ", ".join(
        f"{factor.name.replace('_', ' ')} {factor.raw_score}/10"
        for factor in factors
    )
    return (
        f"The deterministic rubric assigned {lead_result.score.total_score:.1f}/10 "
        f"and {lead_result.score.decision}. Factor scores: {factor_summary}."
    )


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
    lead_ids = {
        id(lr): f"lead-{index:06d}" for index, lr in enumerate(results)
    }
    
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
            "lead_id": lead_ids[id(lr)],
            "name": lr.lead.name,
            "company": lr.lead.company,
            "score": lr.score.total_score,
            "priority": lr.score.priority
        }
        for lr in sorted(results, key=lambda x: -x.score.total_score)
        if lr.score.decision == "QUALIFIED"
    ]
    
    # Generate a draft only for qualified leads and attach it to the lead detail.
    leads_detail = []
    for lr in results:
        lead_dict = lr.score.to_dict()
        lead_dict["lead_id"] = lead_ids[id(lr)]
        lead_dict["reasoning"] = _build_deterministic_reasoning(lr)
        if lr.llm_reasoning:
            lead_dict["llm_reasoning"] = lr.llm_reasoning
        if lr.llm_review_note:
            lead_dict["llm_review_note"] = lr.llm_review_note
        outreach_message = generate_outreach(lr.lead, lr.score)
        lead_dict["outreach_message"] = outreach_message
        lr.outreach_message = outreach_message
        leads_detail.append(lead_dict)

    # Prefer different industry/source combinations in the analyst examples.
    qualified_results = [
        lr for lr in results
        if lr.score.decision == "QUALIFIED" and lr.outreach_message is not None
    ]
    ordered_qualified = sorted(
        qualified_results,
        key=lambda lr: (-lr.score.total_score, lr.lead.name, lr.lead.company),
    )
    sample_results = []
    seen_segments = set()
    for lr in ordered_qualified:
        segment = (lr.lead.industry or "Unknown", lr.lead.source or "Unknown")
        if segment not in seen_segments:
            sample_results.append(lr)
            seen_segments.add(segment)
        if len(sample_results) == 5:
            break
    if len(sample_results) < 5:
        selected = {id(lr) for lr in sample_results}
        sample_results.extend(
            lr for lr in ordered_qualified
            if id(lr) not in selected
        )
        sample_results = sample_results[:5]

    sample_messages = []
    for lr in sample_results:
        sample_messages.append({
            "lead_id": lead_ids[id(lr)],
            "lead": lr.lead.name,
            "company": lr.lead.company,
            "industry": lr.lead.industry,
            "source": lr.lead.source,
            "priority": lr.score.priority,
            "message": lr.outreach_message
        })
    
    # Flag every REVIEW decision and any lead with incomplete data.
    flagged = []
    for lr in results:
        issues = []
        if lr.score.decision == "REVIEW":
            issues.append("Requires human review")
        if not (lr.lead.name or "").strip():
            issues.append("Missing required name")
        if not (lr.lead.company or "").strip():
            issues.append("Missing required company")
        if lr.lead.company_size is None:
            issues.append("Missing company_size")
        if not lr.lead.industry:
            issues.append("Missing industry")
        if not lr.lead.source:
            issues.append("Missing source")
        if lr.lead.last_interaction_date is None:
            issues.append("Missing last_interaction_date")
        if lr.llm_review_note:
            issues.append(f"LLM review note: {lr.llm_review_note}")
        if lr.error:
            issues.append("LLM enrichment failed; review deterministic result")
        if issues:
            flagged.append({
                "lead_id": lead_ids[id(lr)],
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
                "lead_id": lead_ids[id(lr)],
                "lead": lr.lead.name,
                "company": lr.lead.company,
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


def write_report(report: Dict[str, Any], output_path: str) -> None:
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
