"""Data loading and validation utilities."""

import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from utils.models import Lead


REQUIRED_FIELDS = ["name", "company"]
OPTIONAL_FIELDS = ["company_size", "industry", "source", "last_interaction_date"]


def load_leads(csv_path: str) -> List[Lead]:
    """
    Load and validate leads from CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of Lead objects
    """
    df = pd.read_csv(csv_path)
    leads = []
    
    for _, row in df.iterrows():
        lead_data = _parse_row(row)
        lead = Lead.from_dict(lead_data)
        leads.append(lead)
    
    return leads


def _parse_row(row: pd.Series) -> Dict[str, Any]:
    """Parse a single CSV row into lead data dictionary."""
    data = {}
    
    # Required fields
    data["name"] = _clean_string(row.get("name"))
    data["company"] = _clean_string(row.get("company"))
    
    # Optional fields with validation
    data["company_size"] = _parse_company_size(row.get("company_size"))
    data["industry"] = _clean_string(row.get("industry"))
    data["source"] = _clean_string(row.get("source"))
    data["last_interaction_date"] = _parse_date(row.get("last_interaction_date"))
    
    return data


def _clean_string(value: Any) -> str:
    """Clean and normalize string value."""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def _parse_company_size(value: Any) -> Optional[int]:
    """Parse company size, handling NA, empty strings, and invalid values."""
    if pd.isna(value) or value is None:
        return None
    
    value_str = str(value).strip().upper()
    if value_str in ("", "NA", "N/A", "NULL", "NONE"):
        return None
    
    try:
        return int(float(value_str))
    except (ValueError, TypeError):
        return None


def _parse_date(value: Any) -> Optional[date]:
    """Parse date string in YYYY-MM-DD format."""
    if pd.isna(value) or value is None:
        return None
    
    value_str = str(value).strip()
    if value_str in ("", "NA", "N/A", "NULL", "NONE"):
        return None
    
    try:
        return datetime.strptime(value_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def validate_lead(lead: Lead) -> Dict[str, str]:
    """
    Validate a lead and return dict of issues.
    
    Returns:
        Dict mapping field names to error messages. Empty if valid.
    """
    issues = {}
    
    if not lead.name:
        issues["name"] = "Missing required field: name"
    
    if not lead.company:
        issues["company"] = "Missing required field: company"
    
    # Optional fields - just warn, don't fail
    if lead.company_size is None:
        issues["company_size"] = "Missing or invalid company_size"
    
    if not lead.industry:
        issues["industry"] = "Missing industry"
    
    if not lead.source:
        issues["source"] = "Missing source"
    
    if lead.last_interaction_date is None:
        issues["last_interaction_date"] = "Missing or invalid last_interaction_date"
    
    return issues


def get_validation_summary(leads: List[Lead]) -> Dict[str, int]:
    """Get summary of validation issues across all leads."""
    summary = {
        "total": len(leads),
        "complete": 0,
        "missing_name": 0,
        "missing_company": 0,
        "missing_size": 0,
        "missing_industry": 0,
        "missing_source": 0,
        "missing_date": 0,
    }
    
    for lead in leads:
        issues = validate_lead(lead)
        if not issues:
            summary["complete"] += 1
        if "name" in issues:
            summary["missing_name"] += 1
        if "company" in issues:
            summary["missing_company"] += 1
        if "company_size" in issues:
            summary["missing_size"] += 1
        if "industry" in issues:
            summary["missing_industry"] += 1
        if "source" in issues:
            summary["missing_source"] += 1
        if "last_interaction_date" in issues:
            summary["missing_date"] += 1
    
    return summary
