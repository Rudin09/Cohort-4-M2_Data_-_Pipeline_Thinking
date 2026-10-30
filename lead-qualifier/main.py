#!/usr/bin/env python3
"""Lead Intelligence System - Main Entry Point."""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from utils.data_loader import load_leads, get_validation_summary
from utils.rubric_engine import load_rubric, score_leads_batch
from utils.llm_client import enrich_leads_with_llm
from utils.report_builder import build_report, write_report
from utils.models import LeadResult

# Load environment variables from .env file
load_dotenv()


def setup_logging(verbose: bool = False) -> None:
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
        default=None,
        help="LLM batch size (overrides the value in config.yaml)"
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


def main() -> None:
    """Run the lead qualification command-line pipeline."""
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Lead Intelligence System")
    logger.info(f"Input: {args.input}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Config: {args.config}")
    if args.batch_size is not None and args.batch_size <= 0:
        logger.error("--batch-size must be a positive integer")
        sys.exit(2)
    
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
    if validation["missing_name"] > 0:
        logger.warning(f"{validation['missing_name']} leads missing required name")
    if validation["missing_company"] > 0:
        logger.warning(f"{validation['missing_company']} leads missing required company")
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
        logger.info("Starting LLM enrichment...")
        try:
            enrichments = enrich_leads_with_llm(
                leads,
                rubric,
                lead_scores=lead_scores,
                batch_size=args.batch_size,
            )
        except ValueError as exc:
            logger.error("Invalid LLM enrichment configuration: %s", exc)
            sys.exit(2)
        llm_enrichments = {
            enrichment["lead_id"]: enrichment for enrichment in enrichments
        }
        succeeded = sum(
            1 for enrichment in enrichments if not enrichment.get("error")
        )
        logger.info(
            "LLM enrichment completed for %s/%s leads",
            succeeded,
            len(enrichments),
        )
    else:
        logger.info("Skipping LLM enrichment (--no-llm flag)")
    
    # Build LeadResult objects with LLM enrichment
    lead_results = []
    for index, ls in enumerate(lead_scores):
        lead_id = f"lead-{index:06d}"
        enrichment = llm_enrichments.get(lead_id, {})
        lead_results.append(LeadResult(
            lead=ls.lead,
            score=ls,
            llm_reasoning=enrichment.get("reasoning"),
            llm_review_note=enrichment.get("review_note"),
            outreach_message=None,  # Generated by report_builder
            error=enrichment.get("error")
        ))
    
    # Build report using report_builder
    metadata = {
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "total_leads": len(leads),
        "rubric_version": "1.0",
        "llm_model": (
            rubric.get("llm", {}).get("model", "configured")
            if not args.no_llm
            else "deterministic-only"
        ),
        "reference_date": reference_date.isoformat()
    }
    
    report = build_report(lead_results, metadata)
    
    # Write output
    try:
        write_report(report, args.output)
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
