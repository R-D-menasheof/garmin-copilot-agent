"""Tests for Profile — user profile management."""

from __future__ import annotations

from datetime import date

import pytest

from vitalis.profile import (
    create_default_profile,
    load_profile,
    save_profile,
    update_from_garmin,
)


class TestProfile:
    def test_load_missing_file_returns_empty(self, tmp_path):
        profile = load_profile(tmp_path / "nonexistent.yaml")
        assert profile == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "profile.yaml"
        data = {"name": "Test", "age": 30, "goals": ["Run 5k"]}
        save_profile(data, path)
        loaded = load_profile(path)
        assert loaded["name"] == "Test"
        assert loaded["age"] == 30
        assert loaded["goals"] == ["Run 5k"]

    def test_create_default_profile(self, tmp_path):
        path = tmp_path / "profile.yaml"
        profile = create_default_profile(path)
        assert "name" in profile
        assert "goals" in profile
        assert "weight_kg" in profile
        assert path.exists()

    def test_create_default_does_not_overwrite(self, tmp_path):
        path = tmp_path / "profile.yaml"
        save_profile({"name": "Existing"}, path)
        profile = create_default_profile(path)
        assert profile["name"] == "Existing"

    def test_update_from_garmin_weight(self, tmp_path):
        path = tmp_path / "profile.yaml"
        save_profile({"name": "User"}, path)
        raw = {
            "body_composition": [{"weight": 76500, "bodyFat": 14.2, "bmi": 24.1}],
            "daily_stats": [{"restingHeartRate": 52}],
        }
        updated = update_from_garmin(raw, path)
        assert updated["weight_kg"] == 76.5
        assert updated["body_fat_pct"] == 14.2
        assert updated["resting_heart_rate"] == 52
        assert updated["last_synced"] == date.today().isoformat()

    def test_update_from_garmin_devices(self, tmp_path):
        path = tmp_path / "profile.yaml"
        save_profile({"name": "User"}, path)
        raw = {
            "devices": [
                {"productDisplayName": "Forerunner 265", "deviceTypeName": "RUNNING_WATCH"},
            ]
        }
        updated = update_from_garmin(raw, path)
        assert len(updated["devices"]) == 1
        assert updated["devices"][0]["name"] == "Forerunner 265"

    def test_update_from_garmin_vo2max(self, tmp_path):
        path = tmp_path / "profile.yaml"
        save_profile({"name": "User"}, path)
        raw = {
            "max_metrics": {
                "generic": {"vo2MaxPreciseValue": 48.3, "fitnessAge": 28}
            }
        }
        updated = update_from_garmin(raw, path)
        assert updated["vo2max"] == 48.3
        assert updated["fitness_age"] == 28

    def test_update_preserves_manual_fields(self, tmp_path):
        path = tmp_path / "profile.yaml"
        save_profile({"name": "Ronen", "goals": ["Run marathon"]}, path)
        raw = {"daily_stats": [{"restingHeartRate": 55}]}
        updated = update_from_garmin(raw, path)
        assert updated["name"] == "Ronen"
        assert updated["goals"] == ["Run marathon"]
        assert updated["resting_heart_rate"] == 55
