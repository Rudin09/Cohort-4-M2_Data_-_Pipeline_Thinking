#!/usr/bin/env python3
"""Lead Intelligence System - Main Entry Point."""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from utils.data_loader import load_leads, get_validation_summary
from utils.rubric_engine import load_rubric, score_leads_batch
from utils.llm_client import enrich_leads_with_llm
from utils.models import LeadScore, LeadResult

# Load environment variables from .env file
load_dotenv()


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Lead Intelligence System - Automated lead qualification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input ../leads_training.csv --output output_training.json
  python main.py --input ../leads_full_scale_100.csv --output output_report.json --config config.yaml
  python main.py --input ../leads_testing.csv --output output_testing.json --verbose
        """
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input CSV file path"
    )
    parser.add_argument(
        "--output", "-o",
        default="output_report.json",
        help="Output JSON file path (default: output_report.json)"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Rubric config file path (default: config.yaml)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=15,
        help="LLM batch size (default: 15)"
    )
    parser.add_argument(
        "--reference-date",
        help="Reference date for recency calculation (YYYY-MM-DD, default: today)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM enrichment (deterministic scoring only)"
    )
    
    return parser.parse_args()


def load_reference_date(date_str: Optional[str]) -> date:
    """Parse reference date string or return today."""
    if date_str:
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            logging.warning(f"Invalid reference date '{date_str}', using today")
    return date.today()


def build_report(lead_results: List[LeadResult], metadata: dict) -> dict:
    """Build the output report from enriched lead results."""
    # Summary statistics
    total = len(lead_results)
    qualified = sum(1 for lr in lead_results if lr.score.decision == "QUALIFIED")
    review = sum(1 for lr in lead_results if lr.score.decision == "REVIEW")
    rejected = sum(1 for lr in lead_results if lr.score.decision == "REJECTED")
    
    # Common rejection reasons (simplified)
    rejection_reasons = {}
    for lr in lead_results:
        if lr.score.decision == "REJECTED":
            # Find lowest scoring factor
            lowest = min(lr.score.factor_scores, key=lambda fs: fs.raw_score)
            reason = f"Low {lowest.name.replace('_', ' ')} ({lowest.raw_score})"
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
        for lr in sorted(lead_results, key=lambda x: -x.score.total_score)
    ]
    
    # Leads detail with LLM reasoning
    leads_detail = []
    for lr in lead_results:
        lead_dict = lr.score.to_dict()
        if lr.llm_reasoning:
            lead_dict["llm_reasoning"] = lr.llm_reasoning
        leads_detail.append(lead_dict)
    
    # Sample outreach messages (top 5 qualified)
    qualified_results = [lr for lr in lead_results if lr.score.decision == "QUALIFIED"]
    sample_messages = []
    for lr in qualified_results[:5]:
        sample_messages.append({
            "lead": lr.lead.name,
            "message": f"[Sample] Personalized outreach for {lr.lead.name} at {lr.lead.company}..."
        })
    
    # Flagged for review (missing data but scored)
    flagged = []
    for lr in lead_results:
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
    
    # Errors (LLM enrichment failures)
    errors = []
    for lr in lead_results:
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


def main():
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Lead Intelligence System")
    logger.info(f"Input: {args.input}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Config: {args.config}")
    
    # Load configuration
    try:
        rubric = load_rubric(args.config)
        logger.info("Loaded rubric configuration")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)
    
    # Load leads
    try:
        leads = load_leads(args.input)
        logger.info(f"Loaded {len(leads)} leads from {args.input}")
    except Exception as e:
        logger.error(f"Failed to load leads: {e}")
        sys.exit(1)
    
    # Validation summary
    validation = get_validation_summary(leads)
    logger.info(f"Validation: {validation['complete']}/{validation['total']} complete records")
    if validation["missing_size"] > 0:
        logger.warning(f"{validation['missing_size']} leads missing company_size")
    if validation["missing_date"] > 0:
        logger.warning(f"{validation['missing_date']} leads missing last_interaction_date")
    
    # Score leads
    reference_date = load_reference_date(args.reference_date)
    logger.info(f"Using reference date: {reference_date}")
    
    lead_scores = score_leads_batch(leads, rubric, reference_date)
    logger.info(f"Scored {len(lead_scores)} leads")
    
    # LLM Enrichment (unless --no-llm flag)
    llm_enrichments = {}
    if not args.no_llm:
        try:
            logger.info("Starting LLM enrichment...")
            enrichments = enrich_leads_with_llm(leads, rubric)
            # Map by name for lookup
            llm_enrichments = {e["name"]: e for e in enrichments}
            logger.info(f"LLM enrichment complete for {len(enrichments)} leads")
        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}. Continuing with deterministic scores only.")
            llm_enrichments = {}
    else:
        logger.info("Skipping LLM enrichment (--no-llm flag)")
    
    # Build LeadResult objects with LLM enrichment
    lead_results = []
    for ls in lead_scores:
        enrichment = llm_enrichments.get(ls.lead.name, {})
        lead_results.append(LeadResult(
            lead=ls.lead,
            score=ls,
            llm_reasoning=enrichment.get("reasoning"),
            outreach_message=None,  # Will be generated in Phase 5
            error=None
        ))
    
    # Build report
    metadata = {
        "processed_at": date.today().isoformat(),
        "total_leads": len(leads),
        "rubric_version": "1.0",
        "llm_model": rubric.get("llm", {}).get("model", "deterministic-only"),
        "reference_date": reference_date.isoformat()
    }
    
    report = build_report(lead_results, metadata)
    
    # Write output
    try:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report written to {args.output}")
    except Exception as e:
        logger.error(f"Failed to write output: {e}")
        sys.exit(1)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"LEAD QUALIFICATION COMPLETE")
    print(f"{'='*50}")
    print(f"Total Processed: {report['summary']['total_processed']}")
    print(f"Qualified:       {report['summary']['qualified_count']} ({report['summary']['qualified_percentage']}%)")
    print(f"Review:          {report['summary']['review_count']}")
    print(f"Rejected:        {report['summary']['rejected_count']}")
    print(f"Output:          {args.output}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
