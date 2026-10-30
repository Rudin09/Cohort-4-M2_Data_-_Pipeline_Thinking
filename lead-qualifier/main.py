#!/usr/bin/env python3
"""Lead Intelligence System - Main Entry Point."""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

from utils.data_loader import load_leads, get_validation_summary
from utils.rubric_engine import load_rubric, score_leads_batch
from utils.models import LeadScore


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


def build_report(lead_scores: List[LeadScore], metadata: dict) -> dict:
    """Build the output report from scored leads."""
    # Summary statistics
    total = len(lead_scores)
    qualified = sum(1 for ls in lead_scores if ls.decision == "QUALIFIED")
    review = sum(1 for ls in lead_scores if ls.decision == "REVIEW")
    rejected = sum(1 for ls in lead_scores if ls.decision == "REJECTED")
    
    # Common rejection reasons (simplified)
    rejection_reasons = {}
    for ls in lead_scores:
        if ls.decision == "REJECTED":
            # Find lowest scoring factor
            lowest = min(ls.factor_scores, key=lambda fs: fs.raw_score)
            reason = f"Low {lowest.name.replace('_', ' ')} ({lowest.raw_score})"
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    
    common_reasons = [f"{reason} ({count})" for reason, count in 
                      sorted(rejection_reasons.items(), key=lambda x: -x[1])[:5]]
    
    # Priority queue (sorted by score descending)
    priority_queue = [
        {
            "name": ls.lead.name,
            "company": ls.lead.company,
            "score": ls.total_score,
            "priority": ls.priority
        }
        for ls in sorted(lead_scores, key=lambda x: -x.total_score)
    ]
    
    # Leads detail
    leads_detail = [ls.to_dict() for ls in lead_scores]
    
    # Sample outreach messages (top 5 qualified)
    qualified_leads = [ls for ls in lead_scores if ls.decision == "QUALIFIED"]
    sample_messages = []
    for ls in qualified_leads[:5]:
        sample_messages.append({
            "lead": ls.lead.name,
            "message": f"[Sample] Personalized outreach for {ls.lead.name} at {ls.lead.company}..."
        })
    
    # Flagged for review (missing data but scored)
    flagged = []
    for ls in lead_scores:
        issues = []
        if ls.lead.company_size is None:
            issues.append("Missing company_size")
        if not ls.lead.industry:
            issues.append("Missing industry")
        if not ls.lead.source:
            issues.append("Missing source")
        if ls.lead.last_interaction_date is None:
            issues.append("Missing last_interaction_date")
        if issues:
            flagged.append({
                "name": ls.lead.name,
                "company": ls.lead.company,
                "issue": "; ".join(issues),
                "score": ls.total_score
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
        "errors": []  # Will be populated if any leads fail completely
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
    
    # Build report
    metadata = {
        "processed_at": date.today().isoformat(),
        "total_leads": len(leads),
        "rubric_version": "1.0",
        "llm_model": rubric.get("llm", {}).get("model", "deterministic-only"),
        "reference_date": reference_date.isoformat()
    }
    
    report = build_report(lead_scores, metadata)
    
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
