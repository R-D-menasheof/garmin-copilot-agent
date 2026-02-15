"""Tests for scripts/compare_days.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from compare_days import compare_days, _safe


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_sync_folder(tmp_path: Path) -> Path:
    """Create a temporary sync folder with sample data."""
    folder = tmp_path / "2026-02-01_to_2026-02-15"
    folder.mkdir()

    daily_stats = [
        {
            "calendarDate": "2026-02-13",
            "totalSteps": 10750,
            "totalKilocalories": 3371.0,
            "activeKilocalories": 830.0,
            "restingHeartRate": 66,
            "averageStressLevel": 44,
            "maxStressLevel": 95,
            "bodyBatteryHighestValue": 8,
            "bodyBatteryLowestValue": 5,
            "floorsAscended": 2.3,
            "totalDistanceMeters": 8965,
            "sleepingSeconds": 9360,
        },
        {
            "calendarDate": "2026-02-14",
            "totalSteps": 4928,
            "totalKilocalories": 2446.0,
            "activeKilocalories": 218.0,
            "restingHeartRate": 65,
            "averageStressLevel": 28,
            "maxStressLevel": 93,
            "bodyBatteryHighestValue": 66,
            "bodyBatteryLowestValue": 5,
            "floorsAscended": 0.0,
            "totalDistanceMeters": 4103,
            "sleepingSeconds": 30899,
        },
    ]
    (folder / "daily_stats.json").write_text(json.dumps(daily_stats))

    sleep_data = [
        {
            "dailySleepDTO": {
                "calendarDate": "2026-02-13",
                "sleepTimeSeconds": 9360,
                "deepSleepSeconds": 1980,
                "remSleepSeconds": 840,
                "lightSleepSeconds": 6660,
                "awakeSleepSeconds": 4920,
                "averageSpO2Value": 96.0,
                "sleepScores": {"overall": {"value": 24}},
            },
        },
        {
            "dailySleepDTO": {
                "calendarDate": "2026-02-14",
                "sleepTimeSeconds": 31680,
                "deepSleepSeconds": 8160,
                "remSleepSeconds": 8400,
                "lightSleepSeconds": 15240,
                "awakeSleepSeconds": 60,
                "averageSpO2Value": 97.0,
                "sleepScores": {"overall": {"value": 86}},
            },
        },
    ]
    (folder / "sleep.json").write_text(json.dumps(sleep_data))

    hrv_data = [
        {
            "calendarDate": "2026-02-13",
            "hrvSummary": {"lastNightAvg": 22, "status": "LOW"},
        },
        {
            "calendarDate": "2026-02-14",
            "hrvSummary": {"lastNightAvg": 31, "status": "BALANCED"},
        },
    ]
    (folder / "hrv.json").write_text(json.dumps(hrv_data))

    activities = [
        {
            "startTimeLocal": "2026-02-13 07:00:00",
            "activityType": {"typeKey": "lap_swimming"},
            "duration": 2400,
            "calories": 350,
            "distance": 800,
            "averageHR": 135,
            "maxHR": 165,
        },
    ]
    (folder / "activities.json").write_text(json.dumps(activities))

    training = [
        {"calendarDate": "2026-02-13", "score": 1, "level": "POOR"},
        {"calendarDate": "2026-02-14", "score": 32, "level": "LOW"},
    ]
    (folder / "training_readiness.json").write_text(json.dumps(training))

    return folder


# ── Tests ──────────────────────────────────────────────────────────────


class TestSafe:
    """Tests for the _safe helper."""

    def test_returns_numeric(self) -> None:
        assert _safe(42) == 42
        assert _safe(3.14) == 3.14

    def test_returns_default_for_none(self) -> None:
        assert _safe(None) == 0
        assert _safe(None, 99) == 99

    def test_returns_default_for_string(self) -> None:
        assert _safe("hello") == 0


class TestCompareDays:
    """Tests for the compare_days function."""

    def test_single_date(self, tmp_sync_folder: Path) -> None:
        result = compare_days(["2026-02-14"], tmp_sync_folder)
        assert "2026-02-14" in result
        assert result["2026-02-14"]["daily_stats"]["steps"] == 4928

    def test_multi_date(self, tmp_sync_folder: Path) -> None:
        result = compare_days(["2026-02-13", "2026-02-14"], tmp_sync_folder)
        assert len(result) == 2
        assert result["2026-02-13"]["daily_stats"]["steps"] == 10750
        assert result["2026-02-14"]["daily_stats"]["steps"] == 4928

    def test_sleep_extracted(self, tmp_sync_folder: Path) -> None:
        result = compare_days(["2026-02-14"], tmp_sync_folder)
        sleep = result["2026-02-14"]["sleep"]
        assert sleep["score"] == 86
        assert sleep["deep_min"] == 136
        assert sleep["rem_min"] == 140

    def test_hrv_extracted(self, tmp_sync_folder: Path) -> None:
        result = compare_days(["2026-02-13"], tmp_sync_folder)
        hrv = result["2026-02-13"]["hrv"]
        assert hrv["nightly_avg"] == 22
        assert hrv["status"] == "LOW"

    def test_activities_extracted(self, tmp_sync_folder: Path) -> None:
        result = compare_days(["2026-02-13"], tmp_sync_folder)
        acts = result["2026-02-13"]["activities"]
        assert len(acts) == 1
        assert acts[0]["type"] == "lap_swimming"

    def test_no_activities_on_rest_day(self, tmp_sync_folder: Path) -> None:
        result = compare_days(["2026-02-14"], tmp_sync_folder)
        assert "activities" not in result["2026-02-14"]

    def test_training_readiness(self, tmp_sync_folder: Path) -> None:
        result = compare_days(["2026-02-13"], tmp_sync_folder)
        tr = result["2026-02-13"]["training_readiness"]
        assert tr["score"] == 1
        assert tr["level"] == "POOR"

    def test_unknown_date_returns_empty(self, tmp_sync_folder: Path) -> None:
        result = compare_days(["2099-01-01"], tmp_sync_folder)
        assert len(result) == 0

    def test_missing_json_files_handled(self, tmp_path: Path) -> None:
        folder = tmp_path / "empty_sync"
        folder.mkdir()
        result = compare_days(["2026-02-14"], folder)
        assert len(result) == 0

    def test_nested_training_readiness(self, tmp_path: Path) -> None:
        """Training readiness can be a list of lists."""
        folder = tmp_path / "nested_tr"
        folder.mkdir()
        tr_data = [
            [{"calendarDate": "2026-02-14", "score": 55, "level": "MODERATE"}],
        ]
        (folder / "training_readiness.json").write_text(json.dumps(tr_data))
        (folder / "daily_stats.json").write_text("[]")
        result = compare_days(["2026-02-14"], folder)
        assert result["2026-02-14"]["training_readiness"]["score"] == 55
