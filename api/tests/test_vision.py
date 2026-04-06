"""Tests for vision — Azure OpenAI food image analysis and NLP parsing.

TDD RED phase: all tests written before implementation.
Azure OpenAI calls are mocked.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.vision import analyze_food_image, parse_food_text
from vitalis.models import MealEntry, NutritionSource


# ── Mock responses ────────────────────────────────────────────────


def _llm_response(items: list[dict]) -> MagicMock:
    """Create a mock Azure OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = json.dumps(items)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


_CHICKEN_RICE = [
    {
        "food_name": "חזה עוף",
        "calories": 165,
        "protein_g": 31.0,
        "carbs_g": 0.0,
        "fat_g": 3.6,
        "portion_description": "~200g",
    },
    {
        "food_name": "אורז לבן",
        "calories": 200,
        "protein_g": 4.0,
        "carbs_g": 44.0,
        "fat_g": 0.4,
        "portion_description": "~150g",
    },
]

_TWO_APPLES = [
    {
        "food_name": "תפוח",
        "calories": 95,
        "protein_g": 0.5,
        "carbs_g": 25.0,
        "fat_g": 0.3,
        "portion_description": "2 תפוחים",
    },
]


# ── Image Analysis ────────────────────────────────────────────────


class TestAnalyzeImage:
    @pytest.mark.asyncio
    async def test_returns_meal_entries(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            return_value=_llm_response(_CHICKEN_RICE),
        )

        with patch("shared.vision._get_openai_client", return_value=mock_client):
            result = await analyze_food_image(b"fake-image-bytes")

        assert len(result) == 2
        assert isinstance(result[0], MealEntry)
        assert result[0].food_name == "חזה עוף"
        assert result[0].source == NutritionSource.LLM

    @pytest.mark.asyncio
    async def test_empty_plate_returns_empty(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            return_value=_llm_response([]),
        )

        with patch("shared.vision._get_openai_client", return_value=mock_client):
            result = await analyze_food_image(b"fake-image-bytes")

        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_image_raises(self) -> None:
        with pytest.raises(ValueError, match="image"):
            await analyze_food_image(b"")


# ── Text Parsing ──────────────────────────────────────────────────


class TestParseFoodText:
    @pytest.mark.asyncio
    async def test_hebrew(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            return_value=_llm_response(_TWO_APPLES),
        )

        with patch("shared.vision._get_openai_client", return_value=mock_client):
            result = await parse_food_text("אכלתי 2 תפוחים")

        assert len(result) == 1
        assert result[0].food_name == "תפוח"

    @pytest.mark.asyncio
    async def test_english(self) -> None:
        items = [{"food_name": "apple", "calories": 95, "protein_g": 0.5, "carbs_g": 25, "fat_g": 0.3, "portion_description": "2 apples"}]
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            return_value=_llm_response(items),
        )

        with patch("shared.vision._get_openai_client", return_value=mock_client):
            result = await parse_food_text("I ate 2 apples and a protein shake")

        assert len(result) >= 1
        assert isinstance(result[0], MealEntry)

    @pytest.mark.asyncio
    async def test_mixed_language(self) -> None:
        items = [{"food_name": "protein shake", "calories": 120, "protein_g": 25, "carbs_g": 5, "fat_g": 2, "portion_description": "1 shake"}]
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            return_value=_llm_response(items),
        )

        with patch("shared.vision._get_openai_client", return_value=mock_client):
            result = await parse_food_text("אכלתי protein shake")

        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_with_quantities(self) -> None:
        items = [{"food_name": "egg", "calories": 78, "protein_g": 6, "carbs_g": 0.6, "fat_g": 5, "portion_description": "3 eggs"}]
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            return_value=_llm_response(items),
        )

        with patch("shared.vision._get_openai_client", return_value=mock_client):
            result = await parse_food_text("3 eggs scrambled")

        assert len(result) == 1
        assert result[0].calories == 78

    @pytest.mark.asyncio
    async def test_no_quantities_assumes_one_serving(self) -> None:
        items = [{"food_name": "banana", "calories": 89, "protein_g": 1.1, "carbs_g": 23, "fat_g": 0.3, "portion_description": "1 banana"}]
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            return_value=_llm_response(items),
        )

        with patch("shared.vision._get_openai_client", return_value=mock_client):
            result = await parse_food_text("banana")

        assert len(result) == 1
        assert result[0].portion_description == "1 banana"


# ── Error Handling ────────────────────────────────────────────────


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(
            side_effect=TimeoutError("API timeout"),
        )

        with patch("shared.vision._get_openai_client", return_value=mock_client):
            with pytest.raises(TimeoutError):
                await analyze_food_image(b"fake-image-bytes")
