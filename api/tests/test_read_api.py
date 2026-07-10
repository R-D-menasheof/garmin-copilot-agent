"""Tests for Read API — GET nutrition, biometrics, combined.

TDD RED phase. Uses mock BlobStore.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from functions.read_api import (
    get_biometrics,
    get_combined,
    get_day_overrides,
    get_goals,
    get_me,
    get_medical_upload_content,
    get_medical_uploads,
    get_nutrition,
    get_profile,
    get_push_tokens,
    get_recommendation_statuses,
)
from vitalis.models import (
    BiometricsRecord,
    DayTrackingOverride,
    MealEntry,
    MedicalUpload,
    NutritionSource,
    Profile,
    PushToken,
    RecStatus,
    RecommendationStatus,
)


# ── Helpers ───────────────────────────────────────────────────────


def _make_request(params: dict, headers: dict | None = None) -> MagicMock:
    """Create a mock HttpRequest."""
    req = MagicMock()
    req.params = params
    req.headers = headers or {"x-api-key": "test-key"}
    return req


def _meal(name: str = "banana") -> MealEntry:
    return MealEntry(
        food_name=name, calories=89, protein_g=1.1, carbs_g=22.8, fat_g=0.3,
        source=NutritionSource.HISTORY, timestamp=datetime(2026, 4, 4, 12, 0),
    )


def _bio(day: date) -> BiometricsRecord:
    return BiometricsRecord(date=day, resting_hr=65, steps=8500)


# ── Nutrition ─────────────────────────────────────────────────────


class TestGetNutrition:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_meals_for_range(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_meals_range.return_value = {
            date(2026, 4, 4): [_meal("banana"), _meal("apple")],
        }
        mock_store_fn.return_value = store

        req = _make_request({"from": "2026-04-04", "to": "2026-04-04"})
        resp = get_nutrition(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert "2026-04-04" in body["meals"]
        assert len(body["meals"]["2026-04-04"]) == 2

    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_empty_range_returns_empty(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_meals_range.return_value = {}
        mock_store_fn.return_value = store

        req = _make_request({"from": "2026-04-04", "to": "2026-04-04"})
        resp = get_nutrition(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["meals"] == {}

    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_missing_from_param_returns_400(self, _auth) -> None:
        req = _make_request({"to": "2026-04-04"})
        resp = get_nutrition(req)
        assert resp.status_code == 400

    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_invalid_date_format_returns_400(self, _auth) -> None:
        req = _make_request({"from": "04-04-2026", "to": "2026-04-04"})
        resp = get_nutrition(req)
        assert resp.status_code == 400


# ── Biometrics ────────────────────────────────────────────────────


class TestGetBiometrics:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_data_for_range(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_biometrics_range.return_value = {
            date(2026, 4, 4): _bio(date(2026, 4, 4)),
        }
        mock_store_fn.return_value = store

        req = _make_request({"from": "2026-04-04", "to": "2026-04-04"})
        resp = get_biometrics(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert "2026-04-04" in body["biometrics"]

    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_no_data_returns_empty(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_biometrics_range.return_value = {}
        mock_store_fn.return_value = store

        req = _make_request({"from": "2026-04-04", "to": "2026-04-04"})
        resp = get_biometrics(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["biometrics"] == {}


# ── Combined ──────────────────────────────────────────────────────


class TestGetCombined:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_merges_nutrition_and_biometrics(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_combined.return_value = {
            "nutrition": {"2026-04-04": [_meal().model_dump(mode="json")]},
            "biometrics": {"2026-04-04": _bio(date(2026, 4, 4)).model_dump(mode="json")},
        }
        mock_store_fn.return_value = store

        req = _make_request({"from": "2026-04-04", "to": "2026-04-04"})
        resp = get_combined(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert "nutrition" in body
        assert "biometrics" in body

    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_partial_data(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_combined.return_value = {
            "nutrition": {},
            "biometrics": {"2026-04-04": _bio(date(2026, 4, 4)).model_dump(mode="json")},
        }
        mock_store_fn.return_value = store

        req = _make_request({"from": "2026-04-04", "to": "2026-04-04"})
        resp = get_combined(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["nutrition"] == {}


# ── Auth ──────────────────────────────────────────────────────────

# ── Goals ─────────────────────────────────────────────────────────────


class TestGetGoals:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_current_goal(self, _auth, mock_store_fn) -> None:
        from vitalis.models import NutritionGoal
        goal = NutritionGoal(
            date=date(2026, 4, 4), calories_target=2200,
            protein_g_target=180.0, carbs_g_target=250.0, fat_g_target=70.0,
            set_by="agent",
        )
        store = MagicMock()
        store.load_goals.return_value = goal
        mock_store_fn.return_value = store

        req = _make_request({})
        resp = get_goals(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["goal"]["calories_target"] == 2200

    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_none_when_no_goals(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_goals.return_value = None
        mock_store_fn.return_value = store

        req = _make_request({})
        resp = get_goals(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["goal"] is None

class TestAuth:
    @patch("functions.read_api.verify_api_key", return_value=False)
    def test_missing_api_key_returns_401(self, _auth) -> None:
        req = _make_request({"from": "2026-04-04", "to": "2026-04-04"}, headers={})
        resp = get_nutrition(req)
        assert resp.status_code == 401

    @patch("functions.read_api.verify_api_key", return_value=False)
    def test_invalid_api_key_returns_401(self, _auth) -> None:
        req = _make_request(
            {"from": "2026-04-04", "to": "2026-04-04"},
            headers={"x-api-key": "wrong-key"},
        )
        resp = get_nutrition(req)
        assert resp.status_code == 401


# ── Recommendation Status ────────────────────────────────────────


class TestGetRecommendationStatuses:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_list(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_recommendation_statuses.return_value = [
            RecommendationStatus(
                rec_id="abc",
                status=RecStatus.DONE,
                updated_at=datetime(2026, 4, 4, 12, 0),
            ),
        ]
        mock_store_fn.return_value = store

        req = _make_request({})
        resp = get_recommendation_statuses(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert len(body["statuses"]) == 1
        assert body["statuses"][0]["rec_id"] == "abc"

    @patch("functions.read_api.verify_api_key", return_value=False)
    def test_unauthorized(self, _auth) -> None:
        req = _make_request({}, headers={})
        resp = get_recommendation_statuses(req)
        assert resp.status_code == 401


# ── Day Tracking Overrides ────────────────────────────────────────


class TestGetDayOverrides:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_list(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_day_overrides.return_value = [
            DayTrackingOverride(date=date(2026, 7, 1), tracked=False),
        ]
        mock_store_fn.return_value = store

        req = _make_request({})
        resp = get_day_overrides(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert len(body["overrides"]) == 1
        assert body["overrides"][0]["date"] == "2026-07-01"
        assert body["overrides"][0]["tracked"] is False

    @patch("functions.read_api.verify_api_key", return_value=False)
    def test_unauthorized(self, _auth) -> None:
        req = _make_request({}, headers={})
        resp = get_day_overrides(req)
        assert resp.status_code == 401


# ── User-scoped store ─────────────────────────────────────────────


class TestUserScopedStore:
    @patch("functions.read_api.BlobStore")
    @patch("functions.read_api.resolve_user", return_value="alice")
    def test_scopes_store_to_resolved_user(self, mock_resolve, mock_bs) -> None:
        from functions.read_api import _get_blob_store
        _get_blob_store(MagicMock())
        mock_bs.assert_called_once_with(user_id="alice")

    @patch("functions.read_api.resolve_user", return_value=None)
    def test_raises_when_unauthenticated(self, mock_resolve) -> None:
        from functions.read_api import _get_blob_store
        with pytest.raises(PermissionError):
            _get_blob_store(MagicMock())


# ── Me / Profile ──────────────────────────────────────────────────


def _identity(user_id: str = "u1", name: str = "Dana", email: str = "d@x.com"):
    from shared.auth import Identity
    return Identity(user_id=user_id, name=name, email=email)


class TestGetMe:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.resolve_identity")
    def test_returns_identity_and_onboarded(self, mock_ident, mock_store_fn) -> None:
        mock_ident.return_value = _identity()
        store = MagicMock()
        store.load_profile.return_value = Profile(
            display_name="Dana", email="d@x.com", onboarded=True,
        )
        mock_store_fn.return_value = store

        resp = get_me(_make_request({}))

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["user_id"] == "u1"
        assert body["display_name"] == "Dana"
        assert body["onboarded"] is True

    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.resolve_identity")
    def test_first_login_creates_minimal_profile(self, mock_ident, mock_store_fn) -> None:
        mock_ident.return_value = _identity()
        store = MagicMock()
        store.load_profile.return_value = None
        mock_store_fn.return_value = store

        resp = get_me(_make_request({}))

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["onboarded"] is False
        assert body["display_name"] == "Dana"
        store.save_profile.assert_called_once()

    @patch("functions.read_api.resolve_identity", return_value=None)
    def test_unauthorized(self, _ident) -> None:
        resp = get_me(_make_request({}, headers={}))
        assert resp.status_code == 401


class TestGetProfile:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.resolve_identity")
    def test_returns_full_profile(self, mock_ident, mock_store_fn) -> None:
        mock_ident.return_value = _identity()
        store = MagicMock()
        store.load_profile.return_value = Profile(
            display_name="Dana", height_cm=165, goals=["ירידה במשקל"],
        )
        mock_store_fn.return_value = store

        resp = get_profile(_make_request({}))

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["profile"]["display_name"] == "Dana"
        assert body["profile"]["height_cm"] == 165
        assert body["profile"]["goals"] == ["ירידה במשקל"]

    @patch("functions.read_api.resolve_identity", return_value=None)
    def test_unauthorized(self, _ident) -> None:
        resp = get_profile(_make_request({}, headers={}))
        assert resp.status_code == 401


class TestGetPushTokens:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_tokens(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_push_tokens.return_value = [
            PushToken(token="fcm-abc", platform="android"),
        ]
        mock_store_fn.return_value = store

        resp = get_push_tokens(_make_request({}))

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["tokens"][0]["token"] == "fcm-abc"

    @patch("functions.read_api.verify_api_key", return_value=False)
    def test_unauthorized(self, _auth) -> None:
        resp = get_push_tokens(_make_request({}, headers={}))
        assert resp.status_code == 401


class TestGetMedicalUploads:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_uploads(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_medical_uploads.return_value = [
            MedicalUpload(
                id="u1", filename="labs.pdf",
                content_type="application/pdf", size_bytes=3,
            ),
        ]
        mock_store_fn.return_value = store

        resp = get_medical_uploads(_make_request({}))

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["uploads"][0]["filename"] == "labs.pdf"

    @patch("functions.read_api.verify_api_key", return_value=False)
    def test_unauthorized(self, _auth) -> None:
        resp = get_medical_uploads(_make_request({}, headers={}))
        assert resp.status_code == 401


class TestGetMedicalUploadContent:
    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_returns_base64(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_medical_upload_content.return_value = b"%PDF-1.4"
        mock_store_fn.return_value = store
        req = _make_request({})
        req.route_params = {"id": "u1"}

        resp = get_medical_upload_content(req)

        assert resp.status_code == 200
        import base64
        body = json.loads(resp.get_body())
        assert base64.b64decode(body["content"]) == b"%PDF-1.4"

    @patch("functions.read_api._get_blob_store")
    @patch("functions.read_api.verify_api_key", return_value=True)
    def test_404_when_missing(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_medical_upload_content.return_value = None
        mock_store_fn.return_value = store
        req = _make_request({})
        req.route_params = {"id": "nope"}

        resp = get_medical_upload_content(req)

        assert resp.status_code == 404
