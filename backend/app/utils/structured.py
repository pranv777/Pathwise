"""One entry point for validated LLM output, with retries and failure metrics.

Mode "structured": Gemini function-calling via with_structured_output() + Pydantic.
Mode "legacy":     the old regex + json_repair path (kept only as an eval baseline).
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from typing import TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ValidationError
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.utils.llm import extract_json, get_llm, response_text

logger = logging.getLogger("structured")
T = TypeVar("T", bound=BaseModel)

# calls, retries, first_attempt_failures, final_failures. Read by the eval harness.
stats: Counter[str] = Counter()


class StructuredOutputError(Exception):
    """The model returned nothing usable."""


_RETRYABLE = (StructuredOutputError, OutputParserException, ValidationError)


def _call_structured(
    schema: type[T], messages: Sequence[BaseMessage], temperature: float
) -> T:
    runnable = get_llm(temperature).with_structured_output(schema)
    result = runnable.invoke(messages)
    if result is None:  # Gemini sometimes skips the function call
        raise StructuredOutputError("model returned no structured output")
    if isinstance(result, schema):
        return result
    return schema.model_validate(result)


def _call_legacy(
    schema: type[T], messages: Sequence[BaseMessage], temperature: float
) -> T:
    text = response_text(get_llm(temperature).invoke(messages))
    try:
        return schema.model_validate(extract_json(text))
    except ValueError as exc:  # extract_json failure -> same retryable family
        raise StructuredOutputError(str(exc)) from exc


def invoke_json(
    schema: type[T], messages: Sequence[BaseMessage], temperature: float = 0.2
) -> T:
    stats["calls"] += 1
    structured = settings.llm_output_mode == "structured"
    call = _call_structured if structured else _call_legacy
    attempts = settings.llm_max_attempts if structured else 1  # legacy: no retries

    attempt_no = 0

    def attempt() -> T:
        nonlocal attempt_no
        attempt_no += 1
        try:
            return call(schema, messages, temperature)
        except _RETRYABLE:
            if attempt_no == 1:
                stats["first_attempt_failures"] += 1
            raise

    def before_sleep(state: RetryCallState) -> None:
        stats["retries"] += 1
        logger.warning(
            "LLM output invalid (attempt %s), retrying", state.attempt_number
        )

    retryer = Retrying(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.5, max=4),
        before_sleep=before_sleep,
        reraise=True,
    )
    try:
        return retryer(attempt)
    except _RETRYABLE:
        stats["final_failures"] += 1
        raise
