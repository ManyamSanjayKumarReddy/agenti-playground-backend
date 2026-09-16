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

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

logger = logging.getLogger("agentbay.llm")

SchemaT = TypeVar("SchemaT", bound=BaseModel)

DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRY_ATTEMPTS = 5

# Explicit output-token ceiling rather than leaving it unset. An unset
# max_tokens against Groq defaults low enough that a full file's content
# embedded as a JSON string value gets cut off mid-generation, which
# breaks JSON validity outright (confirmed: json_validate_failed with a
# visibly truncated failed_generation) - a hard failure with no retry
# that can recover it, unlike the harmony-parsing error above.
DEFAULT_MAX_TOKENS = 8192

# Substrings of known malformed-structured-output errors we retry
# around, all probabilistic per generation rather than deterministic -
# each confirmed empirically against a live gateway, not theoretical:
#   - "Expected 2 output messages": vLLM/gpt-oss harmony-parsing bug,
#     vllm-project/vllm#22403, fixed upstream in PR #23318 (merged Aug
#     2025) but only for vLLM versions after that. NOT a substitute for
#     upgrading vLLM - on anything beyond trivial output it can still
#     fail every retry there.
#   - "output_parse_failed" / "Parsing failed": Groq's json_schema mode
#     occasionally returns a bare reasoning fragment (e.g. "We need to
#     output JSON object.") instead of completing the actual JSON -
#     observed as a one-off amid many successful calls, so a retry is a
#     reasonable mitigation (unlike the vLLM bug, not expected to be
#     anywhere near this frequent).
_RETRYABLE_ERROR_MARKERS = (
    "Expected 2 output messages",
    "output_parse_failed",
    "Parsing failed",
)


def get_llm() -> BaseChatModel:
    """
    Centralized LLM factory.

    LLM_PROVIDER selects the provider ("groq" or the default
    "openai_compatible"), so swapping providers/gateways is a config
    change, not a code change.

    - "groq": Groq's hosted inference (GROQ_API_KEY, LLM_MODEL - default
      openai/gpt-oss-20b). Groq is an official gpt-oss inference partner
      with correctly-working tool-calling, unlike a self-hosted vLLM
      deployment without the harmony-format fixes - see the retry logic
      below for the failure mode this sidesteps.
    - "openai_compatible" (default): any OpenAI-compatible endpoint via
      LLM_BASE_URL/LLM_API_KEY/LLM_MODEL, falling back to OPENAI_API_KEY
      directly if unset.
    """
    temperature = float(os.environ.get("LLM_TEMPERATURE", DEFAULT_TEMPERATURE))
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS))
    provider = os.environ.get("LLM_PROVIDER", "openai_compatible").lower()

    if provider == "groq":
        return ChatGroq(
            model=os.environ.get("LLM_MODEL", DEFAULT_GROQ_MODEL),
            api_key=os.environ.get("GROQ_API_KEY"),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    return ChatOpenAI(
        model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        base_url=os.environ.get("LLM_BASE_URL") or None,
        api_key=os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        temperature=temperature,
        max_tokens=max_tokens,
    )


def invoke_structured_with_retry(
    llm: BaseChatModel,
    schema: Type[SchemaT],
    messages: Any,
    max_attempts: int | None = None,
) -> SchemaT:
    """
    Same as llm.with_structured_output(schema).invoke(messages), but
    retries on the known malformed-output errors above instead of
    failing the whole generation run on the first bad roll. Any other
    exception is raised immediately, unretried.

    Forces method="json_schema" rather than relying on each provider's
    own default strategy-detection for with_structured_output: gpt-oss's
    "functions.<name>" tool-naming convention breaks the default
    tool-calling-based extraction strategy on Groq (langchain_core raises
    "Unknown tool type: 'functions.X'"). json_schema sidesteps
    tool-calling for extraction entirely and has been reliable against
    both providers this project has tested.
    """
    attempts = max_attempts or int(
        os.environ.get("LLM_RETRY_MAX_ATTEMPTS", DEFAULT_MAX_RETRY_ATTEMPTS)
    )
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return llm.with_structured_output(schema, method="json_schema").invoke(messages)
        except Exception as e:
            error_str = str(e)
            if not any(marker in error_str for marker in _RETRYABLE_ERROR_MARKERS):
                raise

            last_error = e
            logger.warning(
                "Malformed structured-output error on attempt %d/%d, %s",
                attempt,
                attempts,
                "retrying" if attempt < attempts else "giving up",
            )
            if attempt < attempts:
                time.sleep(0.5 * attempt)

    raise last_error
