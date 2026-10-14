"""
tests/test_agent.py — Unit tests for the agent logic in agent.py.

These tests cover:
  - Successful response on the first attempt
  - Retry after invalid JSON
  - Retry after Pydantic validation failure
  - Maximum retries exceeded
  - Successful validation on the second attempt (after one failure)
  - Fatal API errors (should not retry)
  - Retryable server errors (should retry with back-off)

ALL Gemini API calls are mocked — no real API key or network access is needed.

How mocking works here:
  We use pytest-mock's `mocker` fixture to replace `_client.models.generate_content`
  with a fake function. The fake returns whatever we tell it to, so we can
  simulate any scenario without ever hitting the real API.

Run with:  pytest tests/test_agent.py -v
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from google.genai import errors as genai_errors

# agent module is imported AFTER conftest.py sets the fake API key
import agent
from agent import get_topic_explanation, _extract_json_text
from schemas import TopicExplanation


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_valid_payload() -> dict:
    """Return a dict that fully satisfies TopicExplanation validation."""
    return {
        "topic": "Python Lists",
        "summary": "A list is an ordered, mutable sequence of elements.",
        "difficulty": "Beginner",
        "key_points": [
            "Lists are ordered.",
            "Lists are mutable.",
            "Lists can hold mixed types.",
        ],
        "example": "my_list = [1, 2, 3]\nprint(my_list[0])  # 1",
        "next_steps": [
            "Learn list methods like .append() and .pop()",
            "Try list comprehensions",
        ],
    }


def make_mock_response(text: str) -> MagicMock:
    """Create a mock object that looks like a Gemini GenerateContentResponse."""
    mock = MagicMock()
    mock.text = text
    return mock


def make_client_error(code: int) -> genai_errors.ClientError:
    """Create a ClientError with the given HTTP status code."""
    return genai_errors.ClientError(code=code, response_json={"error": "test"})


def make_server_error(code: int = 503) -> genai_errors.ServerError:
    """Create a ServerError with the given HTTP status code."""
    return genai_errors.ServerError(code=code, response_json={"error": "test"})


# ---------------------------------------------------------------------------
# Test 1: Successful first attempt
# ---------------------------------------------------------------------------

class TestSuccessOnFirstAttempt:
    def test_returns_topic_explanation(self, mocker):
        """A perfectly valid JSON response should return a TopicExplanation."""
        valid_json = json.dumps(make_valid_payload())
        mocker.patch.object(
            agent._client.models, "generate_content",
            return_value=make_mock_response(valid_json),
        )

        result = get_topic_explanation("Python Lists")

        assert isinstance(result, TopicExplanation)
        assert result.topic == "Python Lists"
        assert result.difficulty == "Beginner"
        assert len(result.key_points) == 3

    def test_api_called_exactly_once_on_success(self, mocker):
        """On success, the API should only be called once — no unnecessary retries."""
        valid_json = json.dumps(make_valid_payload())
        mock_generate = mocker.patch.object(
            agent._client.models, "generate_content",
            return_value=make_mock_response(valid_json),
        )

        get_topic_explanation("Python Lists")

        assert mock_generate.call_count == 1

    def test_handles_json_wrapped_in_markdown_fences(self, mocker):
        """Response wrapped in ```json ... ``` fences should still parse correctly."""
        valid_json = json.dumps(make_valid_payload())
        wrapped = f"```json\n{valid_json}\n```"
        mocker.patch.object(
            agent._client.models, "generate_content",
            return_value=make_mock_response(wrapped),
        )

        result = get_topic_explanation("Python Lists")
        assert isinstance(result, TopicExplanation)


# ---------------------------------------------------------------------------
# Test 2: Retry after malformed JSON
# ---------------------------------------------------------------------------

class TestRetryAfterInvalidJson:
    def test_retries_on_invalid_json(self, mocker):
        """Should retry when the first response is not valid JSON."""
        valid_json = json.dumps(make_valid_payload())

        # First call returns garbage; second call returns valid JSON
        mock_generate = mocker.patch.object(
            agent._client.models, "generate_content",
            side_effect=[
                make_mock_response("This is not JSON at all!"),
                make_mock_response(valid_json),
            ],
        )

        result = get_topic_explanation("Python Lists")

        assert isinstance(result, TopicExplanation)
        assert mock_generate.call_count == 2  # exactly one retry

    def test_raises_after_max_retries_of_bad_json(self, mocker):
        """Should raise RuntimeError when every attempt returns invalid JSON."""
        mocker.patch.object(
            agent._client.models, "generate_content",
            return_value=make_mock_response("not json"),
        )

        with pytest.raises(RuntimeError) as exc_info:
            get_topic_explanation("Python Lists")

        assert "Failed to get a valid response" in str(exc_info.value)

    def test_api_called_max_retries_times_on_bad_json(self, mocker):
        """API should be called exactly MAX_RETRIES times before giving up."""
        mock_generate = mocker.patch.object(
            agent._client.models, "generate_content",
            return_value=make_mock_response("not json"),
        )

        with pytest.raises(RuntimeError):
            get_topic_explanation("Python Lists")

        assert mock_generate.call_count == agent.Config.MAX_RETRIES


# ---------------------------------------------------------------------------
# Test 3: Retry after Pydantic validation failure
# ---------------------------------------------------------------------------

class TestRetryAfterValidationFailure:
    def test_retries_on_missing_field(self, mocker):
        """Should retry when the JSON is valid but missing a required field."""
        incomplete = make_valid_payload()
        del incomplete["difficulty"]  # Remove a required field

        valid_json = json.dumps(make_valid_payload())

        mock_generate = mocker.patch.object(
            agent._client.models, "generate_content",
            side_effect=[
                make_mock_response(json.dumps(incomplete)),
                make_mock_response(valid_json),
            ],
        )

        result = get_topic_explanation("Python Lists")

        assert isinstance(result, TopicExplanation)
        assert mock_generate.call_count == 2

    def test_retries_on_invalid_difficulty(self, mocker):
        """Should retry when difficulty is not one of the allowed enum values."""
        bad_data = make_valid_payload()
        bad_data["difficulty"] = "Easy"  # Not a valid DifficultyLevel

        valid_json = json.dumps(make_valid_payload())

        mock_generate = mocker.patch.object(
            agent._client.models, "generate_content",
            side_effect=[
                make_mock_response(json.dumps(bad_data)),
                make_mock_response(valid_json),
            ],
        )

        result = get_topic_explanation("Python Lists")

        assert isinstance(result, TopicExplanation)
        assert mock_generate.call_count == 2

    def test_retries_on_key_points_too_short(self, mocker):
        """Should retry when key_points has fewer than 3 items."""
        bad_data = make_valid_payload()
        bad_data["key_points"] = ["Only one point", "Only two"]  # needs 3+

        valid_json = json.dumps(make_valid_payload())

        mock_generate = mocker.patch.object(
            agent._client.models, "generate_content",
            side_effect=[
                make_mock_response(json.dumps(bad_data)),
                make_mock_response(valid_json),
            ],
        )

        result = get_topic_explanation("Python Lists")
        assert isinstance(result, TopicExplanation)

    def test_raises_after_max_retries_of_validation_failure(self, mocker):
        """Should raise RuntimeError when validation fails on every attempt."""
        bad_data = make_valid_payload()
        bad_data["difficulty"] = "NotValid"

        mocker.patch.object(
            agent._client.models, "generate_content",
            return_value=make_mock_response(json.dumps(bad_data)),
        )

        with pytest.raises(RuntimeError) as exc_info:
            get_topic_explanation("Python Lists")

        assert "Failed to get a valid response" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 4: Successful validation after exactly one retry
# ---------------------------------------------------------------------------

class TestSuccessAfterOneRetry:
    def test_succeeds_on_second_attempt(self, mocker):
        """Simulates a common real-world case: first response is bad, second is good."""
        valid_json = json.dumps(make_valid_payload())

        call_count = {"n": 0}

        def fake_generate(model, contents, config=None):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return make_mock_response("{}")  # empty JSON — fails validation
            return make_mock_response(valid_json)  # valid on second call

        mocker.patch.object(
            agent._client.models, "generate_content", side_effect=fake_generate
        )

        result = get_topic_explanation("Python Lists")

        assert isinstance(result, TopicExplanation)
        assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# Test 5: Fatal API errors — should NOT retry
# ---------------------------------------------------------------------------

class TestFatalApiErrors:
    @pytest.mark.parametrize("http_code", [401, 403, 400, 404])
    def test_fatal_client_error_raises_immediately_without_retry(self, mocker, http_code):
        """Fatal 4xx errors should propagate immediately — no retries."""
        mock_generate = mocker.patch.object(
            agent._client.models, "generate_content",
            side_effect=make_client_error(http_code),
        )

        with pytest.raises(genai_errors.ClientError):
            get_topic_explanation("Python Lists")

        # Should have been called only once — no retry on fatal errors
        assert mock_generate.call_count == 1


# ---------------------------------------------------------------------------
# Test 6: Retryable server errors — should retry
# ---------------------------------------------------------------------------

class TestRetryableServerErrors:
    def test_recovers_from_server_error_on_retry(self, mocker):
        """A 5xx server error on the first call should trigger a retry."""
        # Suppress time.sleep so tests run fast
        mocker.patch("agent.time.sleep")

        valid_json = json.dumps(make_valid_payload())

        mock_generate = mocker.patch.object(
            agent._client.models, "generate_content",
            side_effect=[
                make_server_error(503),
                make_mock_response(valid_json),
            ],
        )

        result = get_topic_explanation("Python Lists")

        assert isinstance(result, TopicExplanation)
        assert mock_generate.call_count == 2

    def test_raises_runtime_error_after_all_server_failures(self, mocker):
        """If every attempt hits a server error, RuntimeError should be raised."""
        mocker.patch("agent.time.sleep")

        mocker.patch.object(
            agent._client.models, "generate_content",
            side_effect=make_server_error(503),
        )

        with pytest.raises(RuntimeError) as exc_info:
            get_topic_explanation("Python Lists")

        assert "unavailable" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 7: _extract_json_text helper
# ---------------------------------------------------------------------------

class TestExtractJsonText:
    def test_plain_json_is_returned_unchanged(self):
        """Plain JSON with no fences should pass through unmodified."""
        payload = '{"key": "value"}'
        assert _extract_json_text(payload) == payload

    def test_strips_json_code_fence(self):
        """```json ... ``` fences should be removed."""
        payload = '{"key": "value"}'
        fenced = f"```json\n{payload}\n```"
        assert _extract_json_text(fenced) == payload

    def test_strips_plain_code_fence(self):
        """Plain ``` ... ``` fences (no language tag) should be removed."""
        payload = '{"key": "value"}'
        fenced = f"```\n{payload}\n```"
        assert _extract_json_text(fenced) == payload

    def test_strips_surrounding_whitespace(self):
        """Leading and trailing whitespace should be stripped."""
        payload = '{"key": "value"}'
        assert _extract_json_text(f"  {payload}  ") == payload
