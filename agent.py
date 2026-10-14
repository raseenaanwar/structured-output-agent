"""
agent.py — The core AI agent: Gemini API calls, parsing, validation, and retries.

This is the heart of the application. Here's the full workflow this file implements:

  User Input
      ↓
  Build a prompt asking Gemini for structured JSON
      ↓
  Call Gemini API  ──→  Fatal API Error? (401, 403, 400, 404) → raise immediately
      ↓
  Extract JSON text from the response
      ↓
  Parse JSON  ──→  Invalid JSON? → retry with correction prompt
      ↓
  Validate with Pydantic  ──→  Wrong structure/types? → retry with correction prompt
      ↓
  Return validated TopicExplanation object

Key concepts demonstrated here:
- Why we validate AFTER parsing: receiving JSON doesn't mean it's *correct* JSON
- The difference between a retryable error (bad JSON) and a fatal error (wrong API key)
- How to send Gemini a "correction prompt" that includes the previous error
"""

import json
import logging
import time
from typing import Optional

from pydantic import ValidationError

# google.genai is the current official SDK (google-generativeai is deprecated)
from google import genai
from google.genai import types as genai_types
from google.genai import errors as genai_errors

from config import Config
from schemas import TopicExplanation

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
# We configure the logger once here. Both the file handler (writes to agent.log)
# and the stream handler (prints to terminal) are attached.

logger = logging.getLogger("agent")
logger.setLevel(logging.DEBUG)  # Capture everything; handlers filter by their own level

# Prevent duplicate handlers if this module is imported multiple times (e.g. in tests)
if not logger.handlers:
    # File handler — writes DEBUG and above to agent.log
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Stream handler — writes INFO and above to the terminal (suppressed during tests)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = logging.Formatter("%(levelname)s: %(message)s")
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)


# ---------------------------------------------------------------------------
# Gemini client initialisation
# ---------------------------------------------------------------------------
# We initialise the client once at module load time.
# The API key comes from Config — never from user input or hardcoded strings.
_client = genai.Client(api_key=Config.GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# HTTP status code helpers
# ---------------------------------------------------------------------------

# Fatal HTTP codes: retrying won't help — it's a configuration problem
_FATAL_HTTP_CODES = {
    401,  # Unauthenticated — bad API key
    403,  # Forbidden — key lacks access
    400,  # Bad Request — malformed request
    404,  # Not Found — model doesn't exist
}

# Retryable HTTP codes: transient server-side problems
_RETRYABLE_HTTP_CODES = {
    429,  # Too Many Requests — rate limit
    500,  # Internal Server Error — transient
    503,  # Service Unavailable — transient
    504,  # Gateway Timeout
}


def _is_fatal_error(exc: genai_errors.APIError) -> bool:
    """Return True if this API error should NOT be retried."""
    return getattr(exc, "code", None) in _FATAL_HTTP_CODES


def _is_retryable_error(exc: genai_errors.APIError) -> bool:
    """Return True if this API error is worth retrying."""
    return getattr(exc, "code", None) in _RETRYABLE_HTTP_CODES


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_initial_prompt(user_topic: str) -> str:
    """
    Build the first prompt we send to Gemini.

    We describe the exact JSON structure we want, including field names,
    types, and constraints. The clearer the prompt, the better the response.
    """
    return f"""You are an expert educator. Explain the following topic clearly and return
your explanation as a single JSON object — nothing else, no markdown fences.

Topic: {user_topic}

The JSON object must have exactly these fields:

{{
  "topic": "<string — the topic name>",
  "summary": "<string — a simple, beginner-friendly explanation, at least 10 characters>",
  "difficulty": "<string — exactly one of: Beginner, Intermediate, Advanced>",
  "key_points": ["<string>", "<string>", "<string>"],
  "example": "<string — a concrete, practical example, at least 10 characters>",
  "next_steps": ["<string>", "<string>"]
}}

Rules:
- key_points must contain between 3 and 5 strings.
- next_steps must contain between 2 and 4 strings.
- difficulty must be exactly "Beginner", "Intermediate", or "Advanced" (case-sensitive).
- Do not add extra fields.
- Return only the JSON object — no explanation, no markdown.
"""


def _build_correction_prompt(user_topic: str, bad_response: str, error_message: str) -> str:
    """
    Build a correction prompt after a failed parse or validation attempt.

    We tell Gemini exactly what went wrong and ask it to fix the JSON.
    Including the previous bad response and the specific error message gives
    the model enough context to produce a corrected version.
    """
    return f"""Your previous response could not be validated. Please fix it.

Original topic: {user_topic}

Your previous response:
{bad_response}

Validation error:
{error_message}

Return only a corrected JSON object that satisfies all the original constraints.
No explanation, no markdown fences — just the JSON object.
"""


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json_text(raw_text: str) -> str:
    """
    Extract the JSON portion from a Gemini response string.

    Even when we request JSON output, some models occasionally wrap the
    response in markdown code fences (```json ... ```). This helper strips
    those fences so json.loads() can parse cleanly.

    Args:
        raw_text: The raw text content from the Gemini response.

    Returns:
        A string that should be valid JSON.
    """
    text = raw_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (```json or ```) and last line (```)
        inner_lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner_lines).strip()

    return text


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------

def get_topic_explanation(user_topic: str) -> TopicExplanation:
    """
    Ask Gemini to explain a topic and return a validated TopicExplanation.

    This function implements the full retry loop:
    - Attempt 1: Send the initial prompt.
    - Attempt 2–3: If parsing or validation fails, send a correction prompt.
    - After MAX_RETRIES attempts with no valid response, raise RuntimeError.

    Args:
        user_topic: The topic the user wants explained (e.g. "Python lists").

    Returns:
        A fully validated TopicExplanation Pydantic model instance.

    Raises:
        RuntimeError: If validation still fails after MAX_RETRIES attempts.
        genai_errors.ClientError: For fatal API errors (bad key, 400/401/403/404).
        ConnectionError: If a network problem occurs.
    """
    logger.info("Request started | topic='%s' | model='%s'", user_topic, Config.GEMINI_MODEL)

    last_raw_response: str = ""
    last_error_message: str = ""

    for attempt in range(1, Config.MAX_RETRIES + 1):
        # Build the right prompt: initial on first attempt, correction after that
        if attempt == 1:
            prompt = _build_initial_prompt(user_topic)
            logger.debug("Attempt %d/%d | Sending initial prompt", attempt, Config.MAX_RETRIES)
        else:
            logger.warning(
                "Retry %d/%d | Previous error: %s",
                attempt,
                Config.MAX_RETRIES,
                last_error_message,
            )
            prompt = _build_correction_prompt(user_topic, last_raw_response, last_error_message)
            logger.debug("Attempt %d/%d | Sending correction prompt", attempt, Config.MAX_RETRIES)

        # --- Step 1: Call the Gemini API ---
        try:
            response = _client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    # Ask Gemini to return JSON. This is a strong hint;
                    # we still validate with Pydantic regardless.
                    response_mime_type="application/json",
                ),
            )
            last_raw_response = response.text or ""
            logger.debug(
                "Attempt %d | Raw response received (%d chars)",
                attempt,
                len(last_raw_response),
            )

        except genai_errors.ClientError as exc:
            # ClientError covers 4xx HTTP responses
            if _is_fatal_error(exc):
                logger.error(
                    "Fatal API error (will not retry): HTTP %s — %s",
                    getattr(exc, "code", "?"),
                    type(exc).__name__,
                )
                raise

            # Non-fatal 4xx (shouldn't normally happen, but handle gracefully)
            logger.warning("Client error on attempt %d: %s", attempt, exc)
            if attempt < Config.MAX_RETRIES:
                last_error_message = str(exc)
                continue
            raise RuntimeError(
                f"API client error after {Config.MAX_RETRIES} attempts: {exc}"
            ) from exc

        except genai_errors.ServerError as exc:
            # ServerError covers 5xx responses — transient, worth retrying
            logger.warning("Server error on attempt %d (HTTP 5xx): %s", attempt, exc)
            if attempt < Config.MAX_RETRIES:
                wait_seconds = 2 ** attempt  # exponential back-off: 2s, 4s
                logger.info("Waiting %ds before retry...", wait_seconds)
                time.sleep(wait_seconds)
                last_error_message = str(exc)
                continue
            raise RuntimeError(
                f"Gemini server remained unavailable after {Config.MAX_RETRIES} attempts: {exc}"
            ) from exc

        except genai_errors.APIError as exc:
            # Base class for any other API errors — check if retryable by code
            if _is_fatal_error(exc):
                logger.error("Fatal API error (will not retry): %s", exc)
                raise
            if _is_retryable_error(exc):
                logger.warning("Retryable API error on attempt %d: %s", attempt, exc)
                if attempt < Config.MAX_RETRIES:
                    wait_seconds = 2 ** attempt
                    logger.info("Waiting %ds before retry...", wait_seconds)
                    time.sleep(wait_seconds)
                    last_error_message = str(exc)
                    continue
            # Unknown code — don't retry
            logger.error("Unhandled API error: %s", exc)
            raise

        except Exception as exc:
            # Unexpected errors (e.g. network failure) — log and retry once
            logger.error(
                "Unexpected error on attempt %d: %s: %s",
                attempt,
                type(exc).__name__,
                exc,
            )
            if attempt < Config.MAX_RETRIES:
                last_error_message = str(exc)
                continue
            raise

        # --- Step 2: Extract and parse JSON ---
        try:
            json_text = _extract_json_text(last_raw_response)
            parsed_dict = json.loads(json_text)
            logger.debug("Attempt %d | JSON parsed successfully", attempt)

        except json.JSONDecodeError as exc:
            last_error_message = (
                f"Invalid JSON: {exc}. Response was: {last_raw_response[:200]}"
            )
            logger.warning("Attempt %d | JSON parse failed: %s", attempt, exc)
            # Loop continues to next attempt with a correction prompt
            continue

        # --- Step 3: Validate with Pydantic ---
        # IMPORTANT: parsing JSON ≠ valid data.
        # The JSON might be missing fields, have wrong types, or fail our custom rules.
        # Pydantic checks all of this here.
        try:
            result = TopicExplanation(**parsed_dict)
            logger.info(
                "Validation succeeded on attempt %d | topic='%s' | difficulty='%s'",
                attempt,
                result.topic,
                result.difficulty,
            )
            return result

        except ValidationError as exc:
            # Format Pydantic's error list into a readable string for the correction prompt
            errors = exc.errors()
            error_lines = []
            for err in errors:
                field = " -> ".join(str(loc) for loc in err["loc"])
                error_lines.append(f"  Field '{field}': {err['msg']}")
            last_error_message = "Pydantic validation errors:\n" + "\n".join(error_lines)
            logger.warning(
                "Attempt %d | Validation failed:\n%s", attempt, last_error_message
            )
            # Loop continues to next attempt with a correction prompt

    # If we reach here, all attempts were exhausted
    logger.error(
        "Max retries (%d) exceeded | topic='%s' | last error: %s",
        Config.MAX_RETRIES,
        user_topic,
        last_error_message,
    )
    raise RuntimeError(
        f"Failed to get a valid response after {Config.MAX_RETRIES} attempts.\n"
        f"Last error: {last_error_message}\n\n"
        "Tip: Try rephrasing your question or check agent.log for details."
    )
