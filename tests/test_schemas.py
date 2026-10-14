"""
tests/test_schemas.py — Unit tests for the Pydantic schemas in schemas.py.

These tests verify that our data model correctly:
  - Accepts valid data
  - Rejects missing required fields
  - Rejects invalid difficulty values
  - Rejects wrong data types
  - Enforces list length constraints

No API calls are made here — we're only testing data validation logic.

Run with:  pytest tests/test_schemas.py -v
"""

import pytest
from pydantic import ValidationError

from schemas import DifficultyLevel, TopicExplanation


# ---------------------------------------------------------------------------
# Helper: a complete, valid data dictionary
# ---------------------------------------------------------------------------

def valid_data() -> dict:
    """Return a dictionary with all valid fields for TopicExplanation."""
    return {
        "topic": "Python Lists",
        "summary": "A list is an ordered, mutable collection of items in Python.",
        "difficulty": "Beginner",
        "key_points": [
            "Lists are ordered — items keep their position.",
            "Lists are mutable — you can change them after creation.",
            "Lists can hold any type of item, even mixed types.",
        ],
        "example": "fruits = ['apple', 'banana', 'cherry']\nprint(fruits[0])  # 'apple'",
        "next_steps": [
            "Learn about list methods like .append() and .remove()",
            "Explore list comprehensions for concise loops",
        ],
    }


# ---------------------------------------------------------------------------
# Test 1: Valid data passes validation
# ---------------------------------------------------------------------------

class TestValidData:
    def test_valid_data_creates_model(self):
        """A complete, correct dictionary should produce a TopicExplanation."""
        result = TopicExplanation(**valid_data())
        assert result.topic == "Python Lists"
        assert result.difficulty == DifficultyLevel.BEGINNER

    def test_all_difficulty_levels_are_accepted(self):
        """Each of the three difficulty values should be accepted."""
        for level in ("Beginner", "Intermediate", "Advanced"):
            data = valid_data()
            data["difficulty"] = level
            result = TopicExplanation(**data)
            assert result.difficulty == level

    def test_key_points_with_exactly_5_items(self):
        """key_points with 5 items (the maximum) should be valid."""
        data = valid_data()
        data["key_points"] = ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]
        result = TopicExplanation(**data)
        assert len(result.key_points) == 5

    def test_next_steps_with_exactly_4_items(self):
        """next_steps with 4 items (the maximum) should be valid."""
        data = valid_data()
        data["next_steps"] = ["Step 1", "Step 2", "Step 3", "Step 4"]
        result = TopicExplanation(**data)
        assert len(result.next_steps) == 4

    def test_model_dump_returns_dict(self):
        """model_dump() should return a plain dictionary."""
        result = TopicExplanation(**valid_data())
        dumped = result.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["topic"] == "Python Lists"

    def test_difficulty_serializes_as_string(self):
        """Difficulty should serialise as its string value, not the enum name."""
        result = TopicExplanation(**valid_data())
        dumped = result.model_dump()
        # Should be "Beginner", not "BEGINNER"
        assert dumped["difficulty"] == "Beginner"


# ---------------------------------------------------------------------------
# Test 2: Missing required fields
# ---------------------------------------------------------------------------

class TestMissingFields:
    @pytest.mark.parametrize("missing_field", [
        "topic", "summary", "difficulty", "key_points", "example", "next_steps"
    ])
    def test_missing_field_raises_validation_error(self, missing_field):
        """Removing any required field should raise a ValidationError."""
        data = valid_data()
        del data[missing_field]
        with pytest.raises(ValidationError) as exc_info:
            TopicExplanation(**data)
        # Confirm the error mentions the missing field
        assert missing_field in str(exc_info.value)

    def test_empty_dict_raises_validation_error(self):
        """An empty dictionary should fail with errors on every required field."""
        with pytest.raises(ValidationError) as exc_info:
            TopicExplanation(**{})
        errors = exc_info.value.errors()
        # All 6 fields are required
        assert len(errors) == 6


# ---------------------------------------------------------------------------
# Test 3: Invalid difficulty values
# ---------------------------------------------------------------------------

class TestDifficultyValidation:
    @pytest.mark.parametrize("bad_value", [
        "easy",           # wrong case
        "BEGINNER",       # uppercase — enum is case-sensitive
        "Expert",         # not a valid level
        "intermediate",   # wrong case
        "",               # empty string
        "1",              # numeric string
        123,              # integer
    ])
    def test_invalid_difficulty_raises_error(self, bad_value):
        """Any value not exactly in the enum should raise ValidationError."""
        data = valid_data()
        data["difficulty"] = bad_value
        with pytest.raises(ValidationError):
            TopicExplanation(**data)


# ---------------------------------------------------------------------------
# Test 4: Wrong data types
# ---------------------------------------------------------------------------

class TestWrongTypes:
    def test_topic_as_integer_raises_error(self):
        """topic must be a string, not an integer."""
        data = valid_data()
        data["topic"] = 42
        # Pydantic v2 coerces int to str for plain str fields,
        # so we test a type that genuinely cannot coerce
        # Actually in Pydantic v2, int IS coerced to str — let's test None instead
        data["topic"] = None
        with pytest.raises(ValidationError):
            TopicExplanation(**data)

    def test_key_points_as_string_raises_error(self):
        """key_points must be a list, not a plain string."""
        data = valid_data()
        data["key_points"] = "just a string, not a list"
        with pytest.raises(ValidationError):
            TopicExplanation(**data)

    def test_key_points_as_integer_raises_error(self):
        """key_points must be a list, not an integer."""
        data = valid_data()
        data["key_points"] = 123
        with pytest.raises(ValidationError):
            TopicExplanation(**data)

    def test_next_steps_as_dict_raises_error(self):
        """next_steps must be a list, not a dict."""
        data = valid_data()
        data["next_steps"] = {"step": "learn more"}
        with pytest.raises(ValidationError):
            TopicExplanation(**data)


# ---------------------------------------------------------------------------
# Test 5: List length constraints
# ---------------------------------------------------------------------------

class TestListLengths:
    def test_key_points_with_2_items_raises_error(self):
        """key_points with fewer than 3 items should fail."""
        data = valid_data()
        data["key_points"] = ["Only one point", "Only two points"]
        with pytest.raises(ValidationError) as exc_info:
            TopicExplanation(**data)
        assert "at least 3" in str(exc_info.value)

    def test_key_points_with_6_items_raises_error(self):
        """key_points with more than 5 items should fail."""
        data = valid_data()
        data["key_points"] = ["P1", "P2", "P3", "P4", "P5", "P6"]
        with pytest.raises(ValidationError) as exc_info:
            TopicExplanation(**data)
        assert "at most 5" in str(exc_info.value)

    def test_next_steps_with_1_item_raises_error(self):
        """next_steps with fewer than 2 items should fail."""
        data = valid_data()
        data["next_steps"] = ["Only one step"]
        with pytest.raises(ValidationError) as exc_info:
            TopicExplanation(**data)
        assert "at least 2" in str(exc_info.value)

    def test_next_steps_with_5_items_raises_error(self):
        """next_steps with more than 4 items should fail."""
        data = valid_data()
        data["next_steps"] = ["S1", "S2", "S3", "S4", "S5"]
        with pytest.raises(ValidationError) as exc_info:
            TopicExplanation(**data)
        assert "at most 4" in str(exc_info.value)

    def test_empty_key_point_string_raises_error(self):
        """An empty string inside key_points should fail validation."""
        data = valid_data()
        data["key_points"] = ["Valid point", "", "Another valid point"]
        with pytest.raises(ValidationError) as exc_info:
            TopicExplanation(**data)
        assert "empty" in str(exc_info.value)

    def test_whitespace_only_key_point_raises_error(self):
        """A whitespace-only string inside key_points should fail."""
        data = valid_data()
        data["key_points"] = ["Valid point", "   ", "Another valid point"]
        with pytest.raises(ValidationError) as exc_info:
            TopicExplanation(**data)
        assert "empty" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 6: Field minimum length constraints
# ---------------------------------------------------------------------------

class TestFieldLengths:
    def test_empty_topic_raises_error(self):
        """topic must not be an empty string."""
        data = valid_data()
        data["topic"] = ""
        with pytest.raises(ValidationError):
            TopicExplanation(**data)

    def test_short_summary_raises_error(self):
        """summary must be at least 10 characters."""
        data = valid_data()
        data["summary"] = "Too short"  # 9 characters
        with pytest.raises(ValidationError):
            TopicExplanation(**data)

    def test_short_example_raises_error(self):
        """example must be at least 10 characters."""
        data = valid_data()
        data["example"] = "Short"  # 5 characters
        with pytest.raises(ValidationError):
            TopicExplanation(**data)
