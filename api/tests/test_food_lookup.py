"""Tests for food_lookup — fuzzy match + Open Food Facts + USDA cascade.

TDD RED phase: all tests written before implementation.
HTTP calls mocked — no real API calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from shared.food_lookup import (
    detect_language,
    find_in_cache,
    resolve_food,
    search_open_food_facts,
    search_open_food_facts_barcode,
)
from vitalis.models import KnownFood, NutritionSource


# ── Helpers ───────────────────────────────────────────────────────


def _food(name: str = "אוראו", aliases: list[str] | None = None) -> KnownFood:
    return KnownFood(
        food_name=name,
        calories_per_100g=480,
        protein_per_100g=4.0,
        carbs_per_100g=70.0,
        fat_per_100g=20.0,
        source=NutritionSource.OPEN_FOOD_FACTS,
        aliases=aliases or [],
    )


def _off_response(name: str = "Oreo", kcal: int = 480) -> dict:
    """Mock Open Food Facts search response."""
    return {
        "count": 1,
        "products": [
            {
                "product_name": name,
                "nutriments": {
                    "energy-kcal_100g": kcal,
                    "proteins_100g": 4.0,
                    "carbohydrates_100g": 70.0,
                    "fat_100g": 20.0,
                    "fiber_100g": 2.0,
                },
            }
        ],
    }


def _off_barcode_response(name: str = "Oreo", kcal: int = 480) -> dict:
    """Mock Open Food Facts barcode response."""
    return {
        "status": 1,
        "product": {
            "product_name": name,
            "nutriments": {
                "energy-kcal_100g": kcal,
                "proteins_100g": 4.0,
                "carbohydrates_100g": 70.0,
                "fat_100g": 20.0,
            },
        },
    }


# ── Fuzzy Match ───────────────────────────────────────────────────


class TestFuzzyMatch:
    def test_exact_name_returns_food(self) -> None:
        cache = [_food("אוראו")]
        result = find_in_cache("אוראו", cache)
        assert result is not None
        assert result.food_name == "אוראו"

    def test_close_name_returns_food(self) -> None:
        cache = [_food("אוראו")]
        result = find_in_cache("אוריאו", cache)
        assert result is not None
        assert result.food_name == "אוראו"

    def test_below_threshold_returns_none(self) -> None:
        cache = [_food("אוראו")]
        result = find_in_cache("שוקולד מריר", cache)
        assert result is None

    def test_empty_cache_returns_none(self) -> None:
        result = find_in_cache("banana", [])
        assert result is None

    def test_hebrew_names(self) -> None:
        cache = [_food("חזה עוף"), _food("אורז לבן")]
        result = find_in_cache("חזה עוף", cache)
        assert result is not None
        assert result.food_name == "חזה עוף"

    def test_english_names(self) -> None:
        cache = [_food("banana"), _food("apple")]
        result = find_in_cache("banana", cache)
        assert result is not None
        assert result.food_name == "banana"

    def test_matches_alias(self) -> None:
        cache = [_food("אוראו", aliases=["oreo", "אוריאו"])]
        result = find_in_cache("oreo", cache)
        assert result is not None
        assert result.food_name == "אוראו"


# ── Open Food Facts ───────────────────────────────────────────────


class TestOpenFoodFacts:
    @pytest.mark.asyncio
    async def test_found_returns_known_food(self) -> None:
        mock_resp = httpx.Response(200, json=_off_response("Oreo", 480))
        with patch("shared.food_lookup.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await search_open_food_facts("oreo")

        assert result is not None
        assert result.calories_per_100g == 480
        assert result.source == NutritionSource.OPEN_FOOD_FACTS

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self) -> None:
        mock_resp = httpx.Response(200, json={"count": 0, "products": []})
        with patch("shared.food_lookup.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await search_open_food_facts("xyznonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_barcode_found(self) -> None:
        mock_resp = httpx.Response(200, json=_off_barcode_response("Oreo", 480))
        with patch("shared.food_lookup.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await search_open_food_facts_barcode("7622210100610")

        assert result is not None
        assert result.food_name == "Oreo"

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self) -> None:
        with patch("shared.food_lookup.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

            result = await search_open_food_facts("oreo")

        assert result is None


# ── Cascade ───────────────────────────────────────────────────────


class TestCascade:
    @pytest.mark.asyncio
    async def test_found_in_cache_skips_api(self) -> None:
        cache = [_food("banana")]

        with patch("shared.food_lookup.search_open_food_facts") as mock_off:
            result, source = await resolve_food("banana", cache)

        assert result is not None
        assert source == NutritionSource.HISTORY
        mock_off.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_in_cache_tries_off(self) -> None:
        off_food = _food("banana")
        with patch("shared.food_lookup.search_open_food_facts", new_callable=AsyncMock, return_value=off_food):
            result, source = await resolve_food("banana", [])

        assert result is not None
        assert source == NutritionSource.OPEN_FOOD_FACTS

    @pytest.mark.asyncio
    async def test_hebrew_skips_usda(self) -> None:
        """Hebrew input should skip USDA and signal LLM fallback."""
        with patch("shared.food_lookup.search_open_food_facts", new_callable=AsyncMock, return_value=None):
            with patch("shared.food_lookup.search_usda", new_callable=AsyncMock) as mock_usda:
                result, source = await resolve_food("שניצל", [])

        assert result is None
        assert source == NutritionSource.LLM
        mock_usda.assert_not_called()

    @pytest.mark.asyncio
    async def test_english_tries_usda_before_llm(self) -> None:
        usda_food = _food("chicken breast")
        with patch("shared.food_lookup.search_open_food_facts", new_callable=AsyncMock, return_value=None):
            with patch("shared.food_lookup.search_usda", new_callable=AsyncMock, return_value=usda_food):
                result, source = await resolve_food("chicken breast", [], usda_api_key="test-key")

        assert result is not None
        assert source == NutritionSource.USDA

    @pytest.mark.asyncio
    async def test_returns_source_correctly(self) -> None:
        cache = [_food("egg")]
        result, source = await resolve_food("egg", cache)
        assert source == NutritionSource.HISTORY

    @pytest.mark.asyncio
    async def test_all_fail_returns_none(self) -> None:
        with patch("shared.food_lookup.search_open_food_facts", new_callable=AsyncMock, return_value=None):
            with patch("shared.food_lookup.search_usda", new_callable=AsyncMock, return_value=None):
                result, source = await resolve_food("xyznonexistent123", [], usda_api_key="test-key")

        assert result is None
        assert source == NutritionSource.LLM


# ── Language Detection ────────────────────────────────────────────


class TestDetectLanguage:
    def test_hebrew(self) -> None:
        assert detect_language("אכלתי שניצל") == "he"

    def test_english(self) -> None:
        assert detect_language("I ate chicken breast") == "en"

    def test_mixed_returns_hebrew(self) -> None:
        assert detect_language("אכלתי protein shake") == "he"
