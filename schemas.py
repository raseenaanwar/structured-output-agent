"""
schemas.py — Pydantic models for structured AI responses.

This file defines the shape of the data we expect from Gemini.
Pydantic checks that the response has the right fields and data types.

Think of it like a contract: the AI must return data that matches
this exact structure, or we reject it and ask for a corrected response.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator


class DifficultyLevel(str, Enum):
    """
    The three allowed difficulty levels for a topic explanation.

    Using an Enum means only these exact three strings are valid.
    Any other value — like "Easy" or "expert" — will fail validation.
    """

    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class TopicExplanation(BaseModel):
    """
    The structured response we expect from the Gemini AI agent.

    Every field has:
    - A Python type annotation (str, List[str], etc.)
    - A Field() with a description that gets sent to Gemini as context
    - Optional validation rules

    Pydantic automatically checks all of these when we create an instance.
    """

    topic: str = Field(
        ...,  # The ... means this field is REQUIRED — no default value
        description="The topic being explained",
        min_length=1,  # Must not be an empty string
    )

    summary: str = Field(
        ...,
        description="A simple, beginner-friendly explanation of the topic",
        min_length=10,  # Must be at least 10 characters — not just "Yes" or "OK"
    )

    difficulty: DifficultyLevel = Field(
        ...,
        description="Difficulty level: must be exactly 'Beginner', 'Intermediate', or 'Advanced'",
    )

    key_points: List[str] = Field(
        ...,
        description="A list of 3 to 5 important points about the topic",
    )

    example: str = Field(
        ...,
        description="A practical, concrete example that illustrates the topic",
        min_length=10,
    )

    next_steps: List[str] = Field(
        ...,
        description="A list of 2 to 4 suggested next learning steps for the reader",
    )

    @field_validator("key_points")
    @classmethod
    def key_points_must_have_3_to_5_items(cls, value: List[str]) -> List[str]:
        """
        Custom validator: key_points must contain between 3 and 5 items.

        Pydantic calls this automatically when validating the field.
        If the check fails, we raise a ValueError with a helpful message.
        """
        if len(value) < 3:
            raise ValueError(
                f"key_points must have at least 3 items, but got {len(value)}"
            )
        if len(value) > 5:
            raise ValueError(
                f"key_points must have at most 5 items, but got {len(value)}"
            )
        return value

    @field_validator("next_steps")
    @classmethod
    def next_steps_must_have_2_to_4_items(cls, value: List[str]) -> List[str]:
        """
        Custom validator: next_steps must contain between 2 and 4 items.
        """
        if len(value) < 2:
            raise ValueError(
                f"next_steps must have at least 2 items, but got {len(value)}"
            )
        if len(value) > 4:
            raise ValueError(
                f"next_steps must have at most 4 items, but got {len(value)}"
            )
        return value

    @field_validator("key_points", "next_steps")
    @classmethod
    def list_items_must_not_be_empty(cls, value: List[str]) -> List[str]:
        """
        Validator that applies to both key_points and next_steps.

        Each item in the list must be a non-empty string.
        """
        for i, item in enumerate(value):
            if not item or not item.strip():
                raise ValueError(f"Item at index {i} must not be an empty string")
        return value

    model_config = {
        # This makes it so the JSON serialization uses the enum VALUE ("Beginner")
        # rather than the enum NAME ("BEGINNER")
        "use_enum_values": True,
    }
