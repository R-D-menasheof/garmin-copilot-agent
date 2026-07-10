"""Tests for Write API — POST meals, goals.

TDD RED phase. Uses mock BlobStore.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from functions.write_api import (
    patch_profile,
    post_biometrics,
    post_day_override,
    post_goals,
    post_meal,
    post_medical_upload,
    post_push_token,
    post_recommendation_status,
    post_summary,
    put_timeline,
    unregister_push_token,
)
from vitalis.models import DayTrackingOverride, MealEntry, NutritionGoal, NutritionSource, Profile, RecStatus, RecommendationStatus


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


# ── Put Timeline ──────────────────────────────────────────────────


class TestPutTimeline:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_replaces_all_events(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        body = {
            "events": [
                {
                    "date": "2025-09-03",
                    "category": "medical",
                    "title_he": "בדיקת דם",
                    "detail_he": "LDL 116",
                    "severity": "warning",
                    "source": "agent",
                },
                {
                    "date": "2026-03-01",
                    "category": "lifestyle",
                    "title_he": "הפחתת שתייה מתוקה",
                    "detail_he": "הפחתה משמעותית",
                    "severity": "positive",
                    "source": "agent",
                },
            ],
        }
        req = _make_request(body)
        resp = put_timeline(req)

        assert resp.status_code == 200
        store.save_timeline_events.assert_called_once()
        saved = store.save_timeline_events.call_args[0][0]
        assert len(saved) == 2
        assert saved[0].title_he == "בדיקת דם"
        assert saved[1].category == "lifestyle"


# ── Push tokens ─────────────────────────────────────


def _push_request(params: dict | None = None) -> MagicMock:
    req = MagicMock()
    req.headers = {"x-api-key": "test-key"}
    req.params = params or {}
    return req


class TestPushToken:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_register_saves_token(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        req = _make_request({"token": "fcm-abc", "platform": "android"})
        resp = post_push_token(req)

        assert resp.status_code == 201
        store.save_push_token.assert_called_once()
        saved = store.save_push_token.call_args.args[0]
        assert saved.token == "fcm-abc"
        assert saved.platform == "android"

    @patch("functions.write_api.verify_api_key", return_value=False)
    def test_register_unauthorized(self, _auth) -> None:
        req = _make_request({"token": "fcm-abc"})
        resp = post_push_token(req)
        assert resp.status_code == 401

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_register_rejects_empty_token(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        req = _make_request({"token": ""})
        resp = post_push_token(req)

        assert resp.status_code == 400
        store.save_push_token.assert_not_called()

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_unregister_deletes_token(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        resp = unregister_push_token(_push_request({"token": "fcm-abc"}))

        assert resp.status_code == 200
        store.delete_push_token.assert_called_once_with("fcm-abc")

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_unregister_requires_token_param(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        resp = unregister_push_token(_push_request({}))

        assert resp.status_code == 400
        store.delete_push_token.assert_not_called()


# ── Medical upload ─────────────────────────────────


def _upload_body(
    content: bytes = b"%PDF-1.4",
    content_type: str = "application/pdf",
    filename: str = "labs.pdf",
) -> dict:
    import base64
    return {
        "filename": filename,
        "content_type": content_type,
        "content": base64.b64encode(content).decode(),
    }


class TestPostMedicalUpload:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_stores_upload(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        resp = post_medical_upload(_make_request(_upload_body()))

        assert resp.status_code == 201
        store.save_medical_upload.assert_called_once()
        upload, content = store.save_medical_upload.call_args.args
        assert upload.filename == "labs.pdf"
        assert upload.content_type == "application/pdf"
        assert content == b"%PDF-1.4"

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_rejects_unsupported_type(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        resp = post_medical_upload(
            _make_request(_upload_body(content_type="application/zip"))
        )

        assert resp.status_code == 400
        store.save_medical_upload.assert_not_called()

    @patch("functions.write_api._MAX_UPLOAD_BYTES", 10)
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_rejects_too_large(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        resp = post_medical_upload(_make_request(_upload_body(content=b"12345678901")))

        assert resp.status_code == 413
        store.save_medical_upload.assert_not_called()

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_rejects_missing_fields(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        resp = post_medical_upload(_make_request({"filename": "x.pdf"}))

        assert resp.status_code == 400
        store.save_medical_upload.assert_not_called()

    @patch("functions.write_api.verify_api_key", return_value=False)
    def test_unauthorized(self, _auth) -> None:
        resp = post_medical_upload(_make_request(_upload_body()))
        assert resp.status_code == 401


# ── Post Summary (publish + notify) ────────────────────


class TestPostSummary:
    def _summary_body(self) -> dict:
        return {
            "date": "2026-07-06",
            "period_start": "2026-06-30",
            "period_end": "2026-07-06",
            "metrics_snapshot": {"steps": 8000},
            "trends": ["steps up"],
            "recommendations": [
                {
                    "category": "activity",
                    "title": "Walk",
                    "detail": "Keep walking",
                    "priority": 2,
                }
            ],
            "context_for_next_run": "monitor steps",
        }

    @patch("functions.write_api._notify_report_ready", return_value=1)
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_saves_summary_and_returns_notified(
        self, _auth, mock_store_fn, mock_notify
    ) -> None:
        store = MagicMock()
        mock_store_fn.return_value = store

        resp = post_summary(_make_request(self._summary_body()))

        assert resp.status_code == 201
        store.save_summary.assert_called_once()
        mock_notify.assert_called_once()
        body = json.loads(resp.get_body())
        assert body["notified"] == 1

    @patch("functions.write_api.verify_api_key", return_value=False)
    def test_unauthorized(self, _auth) -> None:
        resp = post_summary(_make_request(self._summary_body()))
        assert resp.status_code == 401

    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_invalid_event_returns_400(self, _auth) -> None:
        body = {"events": [{"bad": "data"}]}
        req = _make_request(body)
        resp = put_timeline(req)
        assert resp.status_code == 400

    @patch("functions.write_api.verify_api_key", return_value=False)
    def test_unauthorized(self, _auth) -> None:
        req = _make_request({"events": []})
        resp = put_timeline(req)
        assert resp.status_code == 401


# ── User-scoped store ─────────────────────────────────────────────


class TestUserScopedStore:
    @patch("functions.write_api.BlobStore")
    @patch("functions.write_api.resolve_user", return_value="bob")
    def test_scopes_store_to_resolved_user(self, mock_resolve, mock_bs) -> None:
        from functions.write_api import _get_blob_store
        _get_blob_store(MagicMock())
        mock_bs.assert_called_once_with(user_id="bob")

    @patch("functions.write_api.resolve_user", return_value=None)
    def test_raises_when_unauthenticated(self, mock_resolve) -> None:
        from functions.write_api import _get_blob_store
        with pytest.raises(PermissionError):
            _get_blob_store(MagicMock())


# ── Patch Profile ─────────────────────────────────────────────────


def _identity(user_id: str = "u1", name: str = "", email: str = ""):
    from shared.auth import Identity
    return Identity(user_id=user_id, name=name, email=email)


class TestPatchProfile:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.resolve_identity")
    def test_merges_provided_fields(self, mock_ident, mock_store_fn) -> None:
        mock_ident.return_value = _identity()
        store = MagicMock()
        store.load_profile.return_value = Profile(
            display_name="Roei", weight_kg=112.0, goals=["old"],
        )
        mock_store_fn.return_value = store

        resp = patch_profile(_make_request({"goals": ["Weight loss"], "onboarded": True}))

        assert resp.status_code == 200
        saved = store.save_profile.call_args[0][0]
        assert saved.goals == ["Weight loss"]
        assert saved.onboarded is True
        assert saved.display_name == "Roei"  # preserved

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.resolve_identity")
    def test_does_not_clobber_auto_synced_fields(self, mock_ident, mock_store_fn) -> None:
        mock_ident.return_value = _identity()
        store = MagicMock()
        store.load_profile.return_value = Profile(weight_kg=112.0, vo2max=42.0)
        mock_store_fn.return_value = store

        resp = patch_profile(_make_request({"weight_kg": 50.0, "vo2max": 99.0, "sex": "Male"}))

        assert resp.status_code == 200
        saved = store.save_profile.call_args[0][0]
        assert saved.weight_kg == 112.0  # NOT clobbered
        assert saved.vo2max == 42.0      # NOT clobbered
        assert saved.sex == "Male"       # editable field applied

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.resolve_identity")
    def test_dob_updates_age(self, mock_ident, mock_store_fn) -> None:
        mock_ident.return_value = _identity()
        store = MagicMock()
        store.load_profile.return_value = Profile()
        mock_store_fn.return_value = store

        resp = patch_profile(_make_request({"date_of_birth": "1990-01-01"}))

        assert resp.status_code == 200
        saved = store.save_profile.call_args[0][0]
        assert saved.date_of_birth == date(1990, 1, 1)

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.resolve_identity")
    def test_preserves_unlisted_fields(self, mock_ident, mock_store_fn) -> None:
        mock_ident.return_value = _identity()
        store = MagicMock()
        store.load_profile.return_value = Profile(
            display_name="Roei", height_cm=183, notes="keep me",
        )
        mock_store_fn.return_value = store

        resp = patch_profile(_make_request({"height_cm": 184}))

        assert resp.status_code == 200
        saved = store.save_profile.call_args[0][0]
        assert saved.height_cm == 184
        assert saved.notes == "keep me"

    @patch("functions.write_api.resolve_identity", return_value=None)
    def test_unauthorized(self, _ident) -> None:
        resp = patch_profile(_make_request({"sex": "Male"}))
        assert resp.status_code == 401


# ── Day Tracking Override ─────────────────────────────────────────


class TestPostDayOverride:
    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_creates_new_override(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_day_overrides.return_value = []
        mock_store_fn.return_value = store

        req = _make_request({"date": "2026-07-01", "tracked": False, "note": "נסעתי"})
        resp = post_day_override(req)

        assert resp.status_code == 201
        store.save_day_overrides.assert_called_once()
        saved = store.save_day_overrides.call_args[0][0]
        assert len(saved) == 1
        assert saved[0].date == date(2026, 7, 1)
        assert saved[0].tracked is False

    @patch("functions.write_api._get_blob_store")
    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_updates_existing_override_for_same_date(self, _auth, mock_store_fn) -> None:
        store = MagicMock()
        store.load_day_overrides.return_value = [
            DayTrackingOverride(date=date(2026, 7, 1), tracked=False),
        ]
        mock_store_fn.return_value = store

        req = _make_request({"date": "2026-07-01", "tracked": True})
        resp = post_day_override(req)

        assert resp.status_code == 201
        saved = store.save_day_overrides.call_args[0][0]
        assert len(saved) == 1
        assert saved[0].tracked is True

    @patch("functions.write_api.verify_api_key", return_value=True)
    def test_invalid_date_returns_400(self, _auth) -> None:
        req = _make_request({"date": "not-a-date", "tracked": False})
        resp = post_day_override(req)
        assert resp.status_code == 400

    @patch("functions.write_api.verify_api_key", return_value=False)
    def test_unauthorized(self, _auth) -> None:
        req = _make_request({"date": "2026-07-01", "tracked": False}, headers={})
        resp = post_day_override(req)
        assert resp.status_code == 401
