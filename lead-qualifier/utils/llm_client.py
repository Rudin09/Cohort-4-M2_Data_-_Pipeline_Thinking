"""LLM client for batched lead explanations and review notes."""

import json
import logging
import os
import re
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from utils.models import Lead, LeadScore
from utils.rubric_engine import score_leads_batch

logger = logging.getLogger(__name__)


BATCH_PROMPT = """You are a B2B sales analyst. For each lead, explain the deterministic
qualification result and identify any human-review note. Do not recalculate or change
the score, decision, or priority. Use only facts supplied in the input; do not infer
customer interests, budgets, or facts that are not present.

Use this configured rubric to explain the supplied result:
{rubric_summary}

Return exactly one JSON object per lead in a JSON array, with these fields only:
"lead_id", "reasoning", and "review_note". "lead_id" must exactly match the input.
"reasoning" must be 1-3 concise sentences grounded in the supplied details and rubric
factor scores. "review_note" must be a short note for a human reviewer, or an empty
string when no additional review note is needed.

There are {n} leads. The input follows:
{leads_json}
"""

STRICT_BATCH_PROMPT = """Return valid JSON only: a JSON array with exactly {n} objects.
Each object must contain exactly the string fields "lead_id", "reasoning", and
"review_note". Preserve every input lead_id exactly once. Do not include scores,
decisions, priorities, markdown, or commentary.

Input:
{leads_json}
"""


class InvalidLLMResponse(ValueError):
    """Raised when a provider response does not match the enrichment contract."""


class PartialLLMResponse(InvalidLLMResponse):
    """Raised when a response contains valid results but omits some lead IDs."""

    def __init__(
        self, results: List[Dict[str, str]], missing_ids: Sequence[str]
    ) -> None:
        super().__init__("Provider response omitted or invalidated lead results")
        self.results = results
        self.missing_ids = list(missing_ids)


class LLMProvider:
    """OpenAI-compatible chat-completion provider."""

    def __init__(
        self,
        client: Any,
        model: str,
        timeout: int,
        temperature: float,
    ) -> None:
        self.client = client
        self.model = model
        self.timeout = timeout
        self.temperature = temperature

    def call_batch(
        self,
        leads: Sequence[Lead],
        lead_scores: Sequence[LeadScore],
        lead_ids: Sequence[str],
        config: Dict[str, Any],
        strict_prompt: bool = False,
    ) -> List[Dict[str, str]]:
        """Request explanation-only enrichment for a batch."""
        prompt = STRICT_BATCH_PROMPT if strict_prompt else BATCH_PROMPT
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt.format(
                        n=len(leads),
                        rubric_summary=self._format_rubric(config),
                        leads_json=self._format_leads(
                            leads, lead_scores, lead_ids
                        ),
                    ),
                }
            ],
            temperature=self.temperature,
            timeout=self.timeout,
        )
        try:
            response_text = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise InvalidLLMResponse("Provider response did not contain message text") from exc
        return self._parse_response(response_text, lead_ids)

    @staticmethod
    def _format_rubric(config: Dict[str, Any]) -> str:
        return json.dumps(
            {
                "factors": config.get("rubric", {}),
                "thresholds": config.get("thresholds", {}),
            },
            indent=2,
        )

    @staticmethod
    def _format_leads(
        leads: Sequence[Lead],
        lead_scores: Sequence[LeadScore],
        lead_ids: Sequence[str],
    ) -> str:
        rows = []
        for lead, score, lead_id in zip(leads, lead_scores, lead_ids):
            rows.append(
                {
                    "lead_id": lead_id,
                    "name": lead.name,
                    "company": lead.company,
                    "company_size": lead.company_size,
                    "industry": lead.industry,
                    "source": lead.source,
                    "last_interaction_date": (
                        lead.last_interaction_date.isoformat()
                        if lead.last_interaction_date
                        else None
                    ),
                    "deterministic_score": score.total_score,
                    "deterministic_decision": score.decision,
                    "deterministic_priority": score.priority,
                    "factor_scores": {
                        factor.name: factor.raw_score
                        for factor in score.factor_scores
                    },
                }
            )
        return json.dumps(rows, indent=2)

    @classmethod
    def _parse_response(
        cls, response_text: Any, expected_ids: Sequence[str]
    ) -> List[Dict[str, str]]:
        if not isinstance(response_text, str):
            raise InvalidLLMResponse("Provider response was not text")

        text = response_text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            text = fenced.group(1)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise InvalidLLMResponse("Provider response was not valid JSON") from exc

        if isinstance(parsed, dict):
            parsed = parsed.get("results", parsed.get("leads"))
        if not isinstance(parsed, list):
            raise InvalidLLMResponse("Provider response must be a JSON array")
        return cls._validate_results(parsed, expected_ids)

    @staticmethod
    def _validate_results(
        results: List[Any], expected_ids: Sequence[str]
    ) -> List[Dict[str, str]]:
        expected = set(expected_ids)
        cleaned: Dict[str, Dict[str, str]] = {}
        invalid_ids = set()
        allowed_fields = {"lead_id", "reasoning", "review_note"}

        for result in results:
            if not isinstance(result, dict):
                raise InvalidLLMResponse("Every result must be a JSON object")
            lead_id = result.get("lead_id")
            if not isinstance(lead_id, str) or lead_id not in expected:
                raise InvalidLLMResponse("Response contains an unknown lead_id")
            if lead_id in invalid_ids:
                continue
            if lead_id in cleaned:
                del cleaned[lead_id]
                invalid_ids.add(lead_id)
                continue
            reasoning = result.get("reasoning")
            review_note = result.get("review_note")
            if (
                not set(result).issubset(allowed_fields)
                or not isinstance(reasoning, str)
                or not reasoning.strip()
                or not isinstance(review_note, str)
            ):
                invalid_ids.add(lead_id)
                continue
            cleaned[lead_id] = {
                "lead_id": lead_id,
                "reasoning": reasoning.strip(),
                "review_note": review_note.strip(),
            }

        missing_ids = [lead_id for lead_id in expected_ids if lead_id not in cleaned]
        if missing_ids:
            ordered_results = [
                cleaned[lead_id] for lead_id in expected_ids if lead_id in cleaned
            ]
            raise PartialLLMResponse(ordered_results, missing_ids)
        return [cleaned[lead_id] for lead_id in expected_ids]


class GroqProvider(LLMProvider):
    """Groq-backed provider."""

    def __init__(
        self, api_key: str, model: str, timeout: int, temperature: float
    ) -> None:
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError(
                "Groq provider requires the 'groq' package; install requirements.txt"
            ) from exc
        super().__init__(Groq(api_key=api_key), model, timeout, temperature)


class OpenAIProvider(LLMProvider):
    """OpenAI-backed provider."""

    def __init__(
        self, api_key: str, model: str, timeout: int, temperature: float
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI provider requires the 'openai' package"
            ) from exc
        super().__init__(
            OpenAI(api_key=api_key, timeout=timeout),
            model,
            timeout,
            temperature,
        )


def get_provider(config: Dict[str, Any]) -> LLMProvider:
    """Build the configured provider using an environment API key."""
    llm_config = config.get("llm", {})
    provider_name = llm_config.get("provider", "groq").lower()
    model = llm_config.get("model", "llama-3.1-70b-versatile")
    timeout = int(llm_config.get("timeout", 30))
    temperature = float(llm_config.get("temperature", 0.3))
    api_key_names = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY"}
    api_key_name = api_key_names.get(provider_name)
    if api_key_name is None:
        raise ValueError(f"Unknown or unsupported LLM provider: {provider_name}")
    api_key = os.getenv(api_key_name)
    if not api_key:
        raise ValueError(f"API key not found in environment: {api_key_name}")
    provider_type = GroqProvider if provider_name == "groq" else OpenAIProvider
    return provider_type(api_key, model, timeout, temperature)


def _is_retryable_provider_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    provider_module = exc.__class__.__module__.split(".", 1)[0]
    if provider_module not in {"groq", "openai"}:
        return False
    if type(exc).__name__ in {
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "RateLimitError",
    }:
        return True
    return (
        type(exc).__name__ == "APIStatusError"
        and getattr(exc, "status_code", 0) >= 500
    )


def _log_retry(retry_state: Any) -> None:
    exception = retry_state.outcome.exception()
    logger.warning(
        "Retrying LLM request after attempt %s (%s)",
        retry_state.attempt_number,
        type(exception).__name__,
    )


@retry(
    retry=retry_if_exception(_is_retryable_provider_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=_log_retry,
    reraise=True,
)
def _call_provider_with_retry(
    provider: LLMProvider,
    leads: Sequence[Lead],
    scores: Sequence[LeadScore],
    lead_ids: Sequence[str],
    config: Dict[str, Any],
    strict_prompt: bool,
) -> List[Dict[str, str]]:
    return provider.call_batch(leads, scores, lead_ids, config, strict_prompt)


def call_llm_batch(
    leads: Sequence[Lead],
    scores: Sequence[LeadScore],
    lead_ids: Sequence[str],
    provider: LLMProvider,
    config: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Call the provider, retrying malformed output once with a strict prompt."""
    partial_results = None
    try:
        return _call_provider_with_retry(
            provider, leads, scores, lead_ids, config, strict_prompt=False
        )
    except PartialLLMResponse as exc:
        partial_results = exc.results
        logger.warning(
            "LLM response omitted %s leads; retrying with strict JSON instructions",
            len(exc.missing_ids),
        )
    except InvalidLLMResponse:
        logger.warning("LLM response schema invalid; retrying with strict JSON instructions")
    try:
        return _call_provider_with_retry(
            provider, leads, scores, lead_ids, config, strict_prompt=True
        )
    except PartialLLMResponse as exc:
        strict_by_id = {result["lead_id"]: result for result in exc.results}
        initial_by_id = {
            result["lead_id"]: result for result in (partial_results or [])
        }
        initial_by_id.update(strict_by_id)
        return [
            initial_by_id[lead_id]
            for lead_id in lead_ids
            if lead_id in initial_by_id
        ]
    except InvalidLLMResponse:
        if partial_results is not None:
            return partial_results
        raise


def _error_description(exc: Exception) -> str:
    """Return a report-safe error without provider response text or credentials."""
    if isinstance(exc, (ValueError, RuntimeError)):
        return f"{type(exc).__name__}: {exc}"
    return f"LLM enrichment failed ({type(exc).__name__})"


def enrich_leads_with_llm(
    leads: List[Lead],
    config: Dict[str, Any],
    lead_scores: Optional[List[LeadScore]] = None,
    batch_size: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Enrich leads with LLM explanations; never accept LLM scoring decisions."""
    if not leads:
        return []

    if lead_scores is None:
        lead_scores = score_leads_batch(leads, config, date.today())
    if len(lead_scores) != len(leads):
        raise ValueError("lead_scores must contain one deterministic score per lead")
    for lead, score in zip(leads, lead_scores):
        if lead != score.lead:
            raise ValueError("lead_scores must be aligned with the supplied leads")

    llm_config = config.get("llm", {})
    effective_batch_size = (
        batch_size if batch_size is not None else llm_config.get("batch_size", 15)
    )
    if type(effective_batch_size) is not int or effective_batch_size <= 0:
        raise ValueError("LLM batch size must be a positive integer")

    results: List[Dict[str, Any]] = [
        {
            "lead_id": f"lead-{index:06d}",
            "name": lead.name,
            "company": lead.company,
            "reasoning": None,
            "review_note": None,
            "error": None,
        }
        for index, lead in enumerate(leads)
    ]

    try:
        provider = get_provider(config)
    except Exception as exc:
        error = _error_description(exc)
        logger.error("LLM provider initialization failed: %s", error)
        for result in results:
            result["error"] = error
        return results

    for start in range(0, len(leads), effective_batch_size):
        end = min(start + effective_batch_size, len(leads))
        batch_ids = [result["lead_id"] for result in results[start:end]]
        logger.info(
            "Processing LLM batch %s (%s leads)",
            start // effective_batch_size + 1,
            end - start,
        )
        try:
            batch_results = call_llm_batch(
                leads[start:end],
                lead_scores[start:end],
                batch_ids,
                provider,
                config,
            )
        except Exception as exc:
            error = _error_description(exc)
            logger.error("LLM batch failed: %s", error)
            for result in results[start:end]:
                result["error"] = error
            continue

        by_id = {result["lead_id"]: result for result in batch_results}
        for result in results[start:end]:
            if result["lead_id"] in by_id:
                result.update(by_id[result["lead_id"]])
            else:
                result["error"] = (
                    "No valid LLM enrichment returned after strict response retry"
                )

    return results
