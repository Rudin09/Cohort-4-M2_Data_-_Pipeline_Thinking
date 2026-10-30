"""LLM Client for batched lead qualification with retry logic."""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from utils.models import Lead

logger = logging.getLogger(__name__)


# ============================================================
# Batched Prompt Template
# ============================================================

BATCH_PROMPT = """You are a B2B sales qualification expert. Analyze these {n} leads and for each provide:
1. Qualification score (1-10) based on the rubric
2. Decision: QUALIFIED / REVIEW / REJECTED
3. Reasoning (2-3 sentences referencing specific lead details)
4. Priority rank (HIGH/MEDIUM/LOW)

Rubric:
- Company size fit (25%): 50-5000 employees ideal
- Industry alignment (25%): SaaS, FinTech, HealthTech, Cybersecurity preferred
- Engagement recency (20%): <30 days = high intent
- Source quality (15%): Inbound demo > Referral > Webinar > Content > LinkedIn
- Buying signals (15%): Composite of above

Leads:
{leads_json}

Output as JSON array with fields: name, company, score, decision, reasoning, priority"""


# ============================================================
# Provider Abstract Base Class
# ============================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def call_batch(self, leads: List[Lead], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Call LLM with a batch of leads."""
        pass
    
    def _format_leads_for_prompt(self, leads: List[Lead]) -> str:
        """Format leads as JSON for prompt."""
        leads_data = []
        for lead in leads:
            leads_data.append({
                "name": lead.name,
                "company": lead.company,
                "company_size": lead.company_size,
                "industry": lead.industry,
                "source": lead.source,
                "last_interaction_date": str(lead.last_interaction_date) if lead.last_interaction_date else None
            })
        return json.dumps(leads_data, indent=2)
    
    def _parse_response(self, response_text: str, expected_count: int) -> List[Dict[str, Any]]:
        """Parse LLM response into structured data."""
        try:
            # Try to extract JSON from response - handle multiple formats
            # 1. Try direct JSON parse first
            try:
                results = json.loads(response_text)
                if isinstance(results, list):
                    return self._validate_results(results, expected_count)
            except json.JSONDecodeError:
                pass
            
            # 2. Try to find JSON array in response
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                results = json.loads(json_str)
                return self._validate_results(results, expected_count)
            
            # 3. Try to find JSON object with 'results' or 'leads' key
            import re
            json_patterns = [
                r'\{.*?"(?:results|leads|data)"\s*:\s*(\[.*?\])\}',
                r'(\[.*?\])'
            ]
            for pattern in json_patterns:
                matches = re.findall(pattern, response_text, re.DOTALL)
                for match in matches:
                    try:
                        results = json.loads(match)
                        if isinstance(results, list):
                            return self._validate_results(results, expected_count)
                    except json.JSONDecodeError:
                        continue
            
            raise json.JSONDecodeError("No valid JSON array found in response", response_text, 0)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response text: {response_text[:1000]}")
            raise
    
    def _validate_results(self, results: List[Dict[str, Any]], expected_count: int) -> List[Dict[str, Any]]:
        """Validate and clean parsed results."""
        if not isinstance(results, list):
            raise ValueError("Parsed JSON is not a list")
        
        # Clean each result
        cleaned = []
        for r in results:
            if isinstance(r, dict):
                # Ensure required fields
                cleaned.append({
                    "name": r.get("name", ""),
                    "company": r.get("company", ""),
                    "score": r.get("score", 5),
                    "decision": r.get("decision", "REVIEW"),
                    "reasoning": r.get("reasoning", "No reasoning provided"),
                    "priority": r.get("priority", "MEDIUM")
                })
        
        if len(cleaned) != expected_count:
            logger.warning(f"Expected {expected_count} results, got {len(cleaned)}")
        
        return cleaned


# ============================================================
# Groq Provider Implementation
# ============================================================

class GroqProvider(LLMProvider):
    """Groq API provider for fast, free-tier inference."""
    
    def __init__(self, api_key: str, model: str, timeout: int = 30, temperature: float = 0.3):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),  # Groq raises generic exceptions
        reraise=True
    )
    def call_batch(self, leads: List[Lead], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Call Groq API with batched leads."""
        leads_json = self._format_leads_for_prompt(leads)
        prompt = BATCH_PROMPT.format(n=len(leads), leads_json=leads_json)
        
        logger.info(f"Calling Groq API with {len(leads)} leads (model: {self.model})")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a B2B sales qualification expert. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=4000,
                timeout=self.timeout
            )
            
            response_text = response.choices[0].message.content
            results = self._parse_response(response_text, len(leads))
            
            logger.info(f"Groq API returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise


# ============================================================
# OpenAI Provider Implementation (for future use)
# ============================================================

class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""
    
    def __init__(self, api_key: str, model: str, timeout: int = 30, temperature: float = 0.3):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def call_batch(self, leads: List[Lead], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        leads_json = self._format_leads_for_prompt(leads)
        prompt = BATCH_PROMPT.format(n=len(leads), leads_json=leads_json)
        
        logger.info(f"Calling OpenAI API with {len(leads)} leads (model: {self.model})")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a B2B sales qualification expert. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=4000,
                timeout=self.timeout
            )
            
            response_text = response.choices[0].message.content
            results = self._parse_response(response_text, len(leads))
            
            logger.info(f"OpenAI API returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


# ============================================================
# Provider Factory
# ============================================================

def get_provider(config: Dict[str, Any]) -> LLMProvider:
    """
    Factory function to create LLM provider based on config.
    
    Args:
        config: Full config.yaml dict with 'llm' section
        
    Returns:
        LLMProvider instance
    """
    llm_config = config.get("llm", {})
    provider_name = llm_config.get("provider", "groq").lower()
    model = llm_config.get("model", "llama-3.1-70b-versatile")
    timeout = llm_config.get("timeout", 30)
    temperature = llm_config.get("temperature", 0.3)
    
    # Load API key from environment
    api_key_map = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY"
    }
    
    env_var = api_key_map.get(provider_name)
    if not env_var:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    api_key = os.getenv(env_var)
    if not api_key:
        raise ValueError(f"API key not found in environment: {env_var}")
    
    # Create provider
    if provider_name == "groq":
        return GroqProvider(api_key, model, timeout, temperature)
    elif provider_name == "openai":
        return OpenAIProvider(api_key, model, timeout, temperature)
    else:
        raise ValueError(f"Provider {provider_name} not yet implemented")


# ============================================================
# High-Level Batch Call Function
# ============================================================

def call_llm_batch(leads: List[Lead], provider: LLMProvider, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Call LLM with a batch of leads, with error handling.
    
    Args:
        leads: List of leads to qualify
        provider: LLMProvider instance
        config: Full config dict
        
    Returns:
        List of result dicts with score, decision, reasoning, priority
    """
    if not leads:
        return []
    
    try:
        results = provider.call_batch(leads, config)
        return results
    except Exception as e:
        logger.error(f"LLM batch call failed after retries: {e}")
        # Return empty results - caller should handle fallback
        return []


def enrich_leads_with_llm(leads: List[Lead], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Enrich leads with LLM reasoning in batches.
    
    Args:
        leads: List of leads to enrich
        config: Full config dict
        
    Returns:
        List of enrichment dicts (same order as input leads)
    """
    provider = get_provider(config)
    batch_size = config.get("llm", {}).get("batch_size", 15)
    
    all_results = []
    
    for i in range(0, len(leads), batch_size):
        batch = leads[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(leads)-1)//batch_size + 1} ({len(batch)} leads)")
        
        batch_results = call_llm_batch(batch, provider, config)
        
        # Ensure we have results for each lead
        for j, lead in enumerate(batch):
            if j < len(batch_results):
                all_results.append(batch_results[j])
            else:
                # Missing result - create fallback
                all_results.append({
                    "name": lead.name,
                    "company": lead.company,
                    "score": 5,
                    "decision": "REVIEW",
                    "reasoning": "LLM enrichment failed - using fallback",
                    "priority": "MEDIUM"
                })
    
    return all_results
