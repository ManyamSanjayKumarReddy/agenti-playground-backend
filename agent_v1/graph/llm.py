"""
LLM factory and structured-output retry helper for the generation graph.

Kept separate from graph/nodes so the graph-wiring and node logic don't
have to know anything about *how* the model is reached or made reliable
- they just call get_llm() and invoke_structured_with_retry().
"""

import logging
import os
import time
from typing import Any, Type, TypeVar

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

logger = logging.getLogger("agentbay.llm")

SchemaT = TypeVar("SchemaT", bound=BaseModel)

DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRY_ATTEMPTS = 5

# Substring of a known vLLM/gpt-oss harmony-parsing error we retry
# around: vllm-project/vllm#22403, fixed upstream in PR #23318 (merged
# Aug 2025) but only for vLLM versions after that. It's probabilistic
# per generation, not deterministic, so retrying the same request is a
# real (if partial) mitigation - confirmed empirically against a live
# gateway. It is NOT a substitute for upgrading vLLM: on anything beyond
# trivial output it can still fail every retry.
_HARMONY_PARSE_ERROR_MARKER = "Expected 2 output messages"


def get_llm() -> ChatOpenAI:
    """
    Centralized LLM factory.

    Points at an OpenAI-compatible endpoint via LLM_BASE_URL/LLM_API_KEY/
    LLM_MODEL when set, so swapping providers/gateways is a config
    change, not a code change. Falls back to OpenAI directly if unset.
    """
    return ChatOpenAI(
        model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        base_url=os.environ.get("LLM_BASE_URL") or None,
        api_key=os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        temperature=float(os.environ.get("LLM_TEMPERATURE", DEFAULT_TEMPERATURE)),
    )


def invoke_structured_with_retry(
    llm: ChatOpenAI,
    schema: Type[SchemaT],
    messages: Any,
    max_attempts: int | None = None,
) -> SchemaT:
    """
    Same as llm.with_structured_output(schema).invoke(messages), but
    retries on the known vLLM/gpt-oss harmony-parsing error above
    instead of failing the whole generation run on the first bad roll.
    Any other exception is raised immediately, unretried.
    """
    attempts = max_attempts or int(
        os.environ.get("LLM_RETRY_MAX_ATTEMPTS", DEFAULT_MAX_RETRY_ATTEMPTS)
    )
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return llm.with_structured_output(schema).invoke(messages)
        except Exception as e:
            if _HARMONY_PARSE_ERROR_MARKER not in str(e):
                raise

            last_error = e
            logger.warning(
                "Harmony-parsing error on attempt %d/%d, %s",
                attempt,
                attempts,
                "retrying" if attempt < attempts else "giving up",
            )
            if attempt < attempts:
                time.sleep(0.5 * attempt)

    raise last_error
