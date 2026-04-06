"""Tests for Ingestion API — POST analyze-image, analyze-text.

TDD RED phase. Vision and food_lookup mocked.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from functions.ingestion import analyze_image, analyze_text
from vitalis.models import KnownFood, MealEntry, NutritionSource


# ── Helpers ───────────────────────────────────────────────────────


def _make_request(body: dict, headers: dict | None = None) -> MagicMock:
    req = MagicMock()
    req.get_body.return_value = json.dumps(body).encode()
    req.headers = headers or {"x-api-key": "test-key"}
    return req


def _meal(name: str = "banana") -> MealEntry:
    return MealEntry(
        food_name=name, calories=89, protein_g=1.1, carbs_g=22.8, fat_g=0.3,
        source=NutritionSource.LLM, timestamp=datetime(2026, 4, 4, 12, 0),
    )


def _known_food(name: str = "banana") -> KnownFood:
    return KnownFood(
        food_name=name, calories_per_100g=89, protein_per_100g=1.1,
        carbs_per_100g=22.8, fat_per_100g=0.3, source=NutritionSource.HISTORY,
    )


# ── Analyze Image ─────────────────────────────────────────────────


class TestAnalyzeImage:
    @patch("functions.ingestion._get_blob_store")
    @patch("functions.ingestion.analyze_food_image", new_callable=AsyncMock)
    @patch("functions.ingestion.verify_api_key", return_value=True)
    def test_runs_vision_returns_meals(self, _auth, mock_vision, mock_store_fn) -> None:
        mock_vision.return_value = [_meal("חזה עוף"), _meal("אורז")]
        store = MagicMock()
        mock_store_fn.return_value = store

        img = base64.b64encode(b"fake-image").decode()
        req = _make_request({"image": img})
        resp = analyze_image(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert len(body["meals"]) == 2

    @patch("functions.ingestion._get_blob_store")
    @patch("functions.ingestion.analyze_food_image", new_callable=AsyncMock)
    @patch("functions.ingestion.verify_api_key", return_value=True)
    def test_caches_new_foods(self, _auth, mock_vision, mock_store_fn) -> None:
        mock_vision.return_value = [_meal("חזה עוף")]
        store = MagicMock()
        mock_store_fn.return_value = store

        img = base64.b64encode(b"fake-image").decode()
        req = _make_request({"image": img})
        analyze_image(req)

        store.append_food_cache.assert_called()

    @patch("functions.ingestion.verify_api_key", return_value=True)
    def test_no_image_returns_400(self, _auth) -> None:
        req = _make_request({})
        resp = analyze_image(req)
        assert resp.status_code == 400


# ── Analyze Text ──────────────────────────────────────────────────


class TestAnalyzeText:
    @patch("functions.ingestion._get_blob_store")
    @patch("functions.ingestion.parse_food_text", new_callable=AsyncMock)
    @patch("functions.ingestion.resolve_food", new_callable=AsyncMock)
    @patch("functions.ingestion.verify_api_key", return_value=True)
    def test_runs_cascade(self, _auth, mock_resolve, mock_parse, mock_store_fn) -> None:
        mock_resolve.return_value = (_known_food("banana"), NutritionSource.HISTORY)
        store = MagicMock()
        store.load_food_cache.return_value = []
        mock_store_fn.return_value = store

        req = _make_request({"text": "banana"})
        resp = analyze_text(req)

        assert resp.status_code == 200
        mock_resolve.assert_called_once()

    @patch("functions.ingestion._get_blob_store")
    @patch("functions.ingestion.resolve_food", new_callable=AsyncMock)
    @patch("functions.ingestion.verify_api_key", return_value=True)
    def test_found_in_cache_no_llm_call(self, _auth, mock_resolve, mock_store_fn) -> None:
        mock_resolve.return_value = (_known_food("banana"), NutritionSource.HISTORY)
        store = MagicMock()
        store.load_food_cache.return_value = [_known_food("banana")]
        mock_store_fn.return_value = store

        with patch("functions.ingestion.parse_food_text", new_callable=AsyncMock) as mock_parse:
            req = _make_request({"text": "banana"})
            analyze_text(req)
            mock_parse.assert_not_called()

    @patch("functions.ingestion._get_blob_store")
    @patch("functions.ingestion.resolve_food", new_callable=AsyncMock)
    @patch("functions.ingestion.verify_api_key", return_value=True)
    def test_caches_result(self, _auth, mock_resolve, mock_store_fn) -> None:
        mock_resolve.return_value = (_known_food("new food"), NutritionSource.OPEN_FOOD_FACTS)
        store = MagicMock()
        store.load_food_cache.return_value = []
        mock_store_fn.return_value = store

        req = _make_request({"text": "new food"})
        analyze_text(req)

        store.append_food_cache.assert_called()

    @patch("functions.ingestion.verify_api_key", return_value=True)
    def test_empty_string_returns_400(self, _auth) -> None:
        req = _make_request({"text": ""})
        resp = analyze_text(req)
        assert resp.status_code == 400
