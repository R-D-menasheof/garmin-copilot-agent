"""Tests for Write API — POST meals, goals.

TDD RED phase. Uses mock BlobStore.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from functions.write_api import post_meal, post_goals, post_biometrics, post_recommendation_status
from vitalis.models import MealEntry, NutritionGoal, NutritionSource, RecStatus, RecommendationStatus


# ── Helpers ───────────────────────────────────────────────────────


def _make_request(body: dict, headers: dict | None = None) -> MagicMock:
    req = MagicMock()
    req.get_body.return_value = json.dumps(body).encode()
    req.headers = headers or {"x-api-key": "test-key"}
    return req


def _meal_body() -> dict:
    return {
        "food_name": "banana",
        "calories": 89,
        "protein_g": 1.1,
        "carbs_g": 22.8,
        "fat_g": 0.3,
        "source": "history",
        "timestamp": "2026-04-04T12:00:00",
    }


def _goal_body() -> dict:
    return {
        "date": "2026-04-04",
        "calories_target": 2200,
        "protein_g_target": 180.0,
        "carbs_g_target": 250.0,
        "fat_g_target": 70.0,
        "set_by": "agent",
    }


def _biometrics_body() -> dict:
    return {
        "date": "2026-04-04",
        "resting_hr": 65,
        "hrv_ms": 27,
        "steps": 8500,
        "active_calories": 350,
        "sleep_seconds": 25200,
        "deep_sleep_seconds": 3780,
        "rem_sleep_seconds": 4536,
        "weight_kg": 112.0,
    }


# ── Post Meal ─────────────────────────────────────────────────────


class TestPostMeal:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_stores_in_blob(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_meals.return_value = []
        mock_store_fn.return_value = store

        req = _make_request(_meal_body())
        resp = post_meal(req)

        assert resp.status_code == 201
        store.save_meals.assert_called_once()

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_triggers_cache_update(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_meals.return_value = []
        mock_store_fn.return_value = store

        req = _make_request(_meal_body())
        resp = post_meal(req)

        assert resp.status_code == 201
        store.append_food_cache.assert_called_once()

    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_invalid_body_returns_400(self, _auth) -> None:
        req = _make_request({"not": "a meal"})
        resp = post_meal(req)
        assert resp.status_code == 400

    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_missing_food_name_returns_400(self, _auth) -> None:
        body = _meal_body()
        del body["food_name"]
        req = _make_request(body)
        resp = post_meal(req)
        assert resp.status_code == 400


# ── Post Goals ────────────────────────────────────────────────────


class TestPostGoals:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_stores_current_goals(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        req = _make_request(_goal_body())
        resp = post_goals(req)

        assert resp.status_code == 201
        store.save_goals.assert_called_once()

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_overwrites_previous(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        req = _make_request(_goal_body())
        post_goals(req)
        post_goals(req)

        assert store.save_goals.call_count == 2

    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_invalid_body_returns_400(self, _auth) -> None:
        req = _make_request({"bad": "data"})
        resp = post_goals(req)
        assert resp.status_code == 400

    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_negative_calories_returns_400(self, _auth) -> None:
        body = _goal_body()
        body["calories_target"] = -500
        req = _make_request(body)
        resp = post_goals(req)
        assert resp.status_code == 400


# ── Auth ──────────────────────────────────────────────────────────


class TestWriteAuth:
    @patch("functions.write_api.verify_api_key", return_value=False)
    def test_auth_required(self, _auth) -> None:
        req = _make_request(_meal_body(), headers={})
        resp = post_meal(req)
        assert resp.status_code == 401


# ── Post Biometrics ─────────────────────────────────────────────


class TestPostBiometrics:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_stores_biometrics(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        req = _make_request(_biometrics_body())
        resp = post_biometrics(req)

        assert resp.status_code == 201
        store.save_biometrics.assert_called_once()

    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_invalid_body_returns_400(self, _auth) -> None:
        req = _make_request({"not": "biometrics"})
        resp = post_biometrics(req)
        assert resp.status_code == 400

    @patch("functions.write_api.verify_api_key", return_value=False)
    def test_auth_required(self, _auth) -> None:
        req = _make_request(_biometrics_body(), headers={})
        resp = post_biometrics(req)
        assert resp.status_code == 401


# ── Recommendation Status ────────────────────────────────────────


class TestPostRecommendationStatus:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_updates_single(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_recommendation_statuses.return_value = [
            RecommendationStatus(
                rec_id="abc",
                status=RecStatus.PENDING,
                updated_at=datetime(2026, 4, 4, 12, 0),
            ),
        ]
        mock_store_fn.return_value = store

        req = _make_request({"rec_id": "abc", "status": "done"})
        resp = post_recommendation_status(req)

        assert resp.status_code == 201
        store.save_recommendation_statuses.assert_called_once()

    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_invalid_status_returns_400(self, _auth) -> None:
        req = _make_request({"rec_id": "abc", "status": "invalid"})
        resp = post_recommendation_status(req)
        assert resp.status_code == 400
