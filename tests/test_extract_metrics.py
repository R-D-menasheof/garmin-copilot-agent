"""Tests for scripts/extract_metrics.py metric extraction functions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make extract_metrics importable
_project_root = Path(__file__).resolve().parents[1]
_scripts = _project_root / "scripts"
sys.path.insert(0, str(_scripts))

from extract_metrics import (
    extract_activities,
    extract_daily_stats,
    extract_devices,
    extract_hrv,
    extract_intensity_minutes,
    extract_personal_records,
    extract_respiration,
    extract_sleep,
    extract_spo2,
    extract_training_readiness,
    extract_vo2max,
    extract_weight,
    extract_all,
    format_report,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def daily_stats_sample() -> list[dict]:
    return [
        {
            "calendarDate": "2026-02-10",
            "totalSteps": 8000,
            "restingHeartRate": 62,
            "averageStressLevel": 30,
            "bodyBatteryHighestValue": 70,
            "bodyBatteryLowestValue": 5,
            "averageSPO2Value": 96,
            "floorsAscended": 5.0,
            "sleepingSeconds": 25200,  # 7h
        },
        {
            "calendarDate": "2026-02-11",
            "totalSteps": 12000,
            "restingHeartRate": 65,
            "averageStressLevel": 40,
            "bodyBatteryHighestValue": 50,
            "bodyBatteryLowestValue": 8,
            "averageSPO2Value": 97,
            "floorsAscended": 8.0,
            "sleepingSeconds": 19800,  # 5.5h — short night
        },
        {
            "calendarDate": "2026-02-12",
            "totalSteps": 10000,
            "restingHeartRate": 63,
            "averageStressLevel": 35,
            "bodyBatteryHighestValue": 60,
            "bodyBatteryLowestValue": 6,
            "averageSPO2Value": None,
            "floorsAscended": None,
            "sleepingSeconds": 28800,  # 8h
        },
    ]


@pytest.fixture
def sleep_sample() -> list[dict]:
    return [
        {
            "dailySleepDTO": {
                "calendarDate": "2026-02-10",
                "sleepScoreOverall": 80,
                "deepSleepSeconds": 5400,    # 90 min
                "remSleepSeconds": 5400,     # 90 min
                "lightSleepSeconds": 14400,  # 240 min
                "awakeSleepSeconds": 1200,   # 20 min
            }
        },
        {
            "dailySleepDTO": {
                "calendarDate": "2026-02-11",
                "sleepScoreOverall": 60,
                "deepSleepSeconds": 3600,    # 60 min
                "remSleepSeconds": 3000,     # 50 min
                "lightSleepSeconds": 10800,  # 180 min
                "awakeSleepSeconds": 600,    # 10 min
            }
        },
    ]


@pytest.fixture
def activities_sample() -> list[dict]:
    return [
        {"activityType": {"typeKey": "lap_swimming"}, "duration": 1800, "calories": 300, "distance": 750.0},
        {"activityType": {"typeKey": "lap_swimming"}, "duration": 2400, "calories": 400, "distance": 1000.0},
        {"activityType": {"typeKey": "strength_training"}, "duration": 3600, "calories": 250, "distance": None},
    ]


@pytest.fixture
def hrv_sample() -> list[dict]:
    return [
        {"hrvSummary": {"calendarDate": "2026-02-10", "lastNightAvg": 30}},
        {"hrvSummary": {"calendarDate": "2026-02-11", "lastNightAvg": 28}},
        {"hrvSummary": {"calendarDate": "2026-02-12", "lastNightAvg": 35}},
    ]


@pytest.fixture
def training_readiness_flat() -> list[dict]:
    return [
        {"score": 45},
        {"score": 70},
        {"score": 25},
    ]


@pytest.fixture
def training_readiness_nested() -> list:
    return [
        [{"score": 55}, {"score": 65}],
        [{"score": 20}],
    ]


@pytest.fixture
def training_status_sample() -> list[dict]:
    return [
        {
            "mostRecentVO2Max": {
                "generic": {
                    "vo2MaxPreciseValue": 42.5,
                    "calendarDate": "2026-02-10",
                }
            }
        }
    ]


@pytest.fixture
def weigh_ins_sample() -> dict:
    return {
        "dailyWeightSummaries": [
            {"summaryDate": "2026-02-10", "latestWeight": {"weight": 80000}},  # 80 kg in grams
            {"summaryDate": "2026-02-05", "latestWeight": {"weight": 80500}},
        ]
    }


# ── Tests ─────────────────────────────────────────────────────────────


class TestExtractDailyStats:
    def test_empty_input(self):
        assert extract_daily_stats([]) == {}
        assert extract_daily_stats(None) == {}

    def test_steps(self, daily_stats_sample):
        result = extract_daily_stats(daily_stats_sample)
        assert result["steps"]["avg"] == 10000
        assert result["steps"]["min"] == 8000
        assert result["steps"]["max"] == 12000

    def test_rhr(self, daily_stats_sample):
        result = extract_daily_stats(daily_stats_sample)
        assert result["rhr"]["avg"] == 63  # (62+65+63)/3 = 63.3 → 63
        assert result["rhr"]["min"] == 62
        assert result["rhr"]["max"] == 65

    def test_body_battery(self, daily_stats_sample):
        result = extract_daily_stats(daily_stats_sample)
        assert result["body_battery_peak"]["avg"] == 60
        assert result["body_battery_peak"]["days_below_80"] == 3
        assert result["body_battery_peak"]["total_days"] == 3

    def test_short_nights(self, daily_stats_sample):
        result = extract_daily_stats(daily_stats_sample)
        assert len(result["short_nights"]) == 1
        assert result["short_nights"][0]["date"] == "2026-02-11"
        assert result["short_nights"][0]["hours"] == 5.5

    def test_handles_none_values(self):
        data = [{"calendarDate": "2026-02-10", "totalSteps": None, "restingHeartRate": None}]
        result = extract_daily_stats(data)
        assert result["steps"]["avg"] == 0

    def test_weekly_steps(self, daily_stats_sample):
        result = extract_daily_stats(daily_stats_sample)
        assert len(result["weekly_steps"]) >= 1


class TestExtractSleep:
    def test_empty_input(self):
        assert extract_sleep([]) == {}
        assert extract_sleep(None) == {}

    def test_scores(self, sleep_sample):
        result = extract_sleep(sleep_sample)
        assert result["score"]["avg"] == 70  # (80+60)/2
        assert result["score"]["min"] == 60
        assert result["score"]["max"] == 80

    def test_stages(self, sleep_sample):
        result = extract_sleep(sleep_sample)
        assert result["deep_min"] == 75  # (90+60)/2
        assert result["rem_min"] == 70   # (90+50)/2
        assert result["nights"] == 2


class TestExtractActivities:
    def test_empty_input(self):
        assert extract_activities([]) == {}
        assert extract_activities(None) == {}

    def test_breakdown(self, activities_sample):
        result = extract_activities(activities_sample)
        assert result["total"] == 3
        assert result["by_type"]["lap_swimming"]["count"] == 2
        assert result["by_type"]["strength_training"]["count"] == 1
        assert "avg_distance_m" in result["by_type"]["lap_swimming"]
        assert "avg_distance_m" not in result["by_type"]["strength_training"]

    def test_totals(self, activities_sample):
        result = extract_activities(activities_sample)
        assert result["total_calories"] == 950
        assert result["total_duration_min"] == 130  # 30+40+60


class TestExtractHRV:
    def test_empty_input(self):
        assert extract_hrv([]) == {}

    def test_nightly_stats(self, hrv_sample):
        result = extract_hrv(hrv_sample)
        assert result["nightly_avg"] == 31  # (30+28+35)/3 = 31
        assert result["nightly_min"] == 28
        assert result["nightly_max"] == 35
        assert result["readings"] == 3

    def test_weekly_trend(self, hrv_sample):
        result = extract_hrv(hrv_sample)
        assert len(result["weekly_trend"]) >= 1


class TestExtractTrainingReadiness:
    def test_empty_input(self):
        assert extract_training_readiness([]) == {}

    def test_flat_format(self, training_readiness_flat):
        result = extract_training_readiness(training_readiness_flat)
        assert result["avg"] == 47  # (45+70+25)/3
        assert result["min"] == 25
        assert result["max"] == 70
        assert result["below_30"] == 1
        assert result["above_60"] == 1

    def test_nested_format(self, training_readiness_nested):
        result = extract_training_readiness(training_readiness_nested)
        assert result["count"] == 3
        assert result["avg"] == 47  # (55+65+20)/3


class TestExtractVO2max:
    def test_empty_input(self):
        assert extract_vo2max([]) == {}

    def test_extraction(self, training_status_sample):
        result = extract_vo2max(training_status_sample)
        assert result["value"] == 42.5
        assert result["date"] == "2026-02-10"


class TestExtractWeight:
    def test_empty_input(self):
        assert extract_weight({}) == {}
        assert extract_weight(None) == {}

    def test_grams_conversion(self, weigh_ins_sample):
        result = extract_weight(weigh_ins_sample)
        assert result["latest"]["kg"] == 80.0
        assert result["count"] == 2

    def test_already_kg(self):
        data = {"dailyWeightSummaries": [{"summaryDate": "2026-02-10", "latestWeight": {"weight": 80.5}}]}
        result = extract_weight(data)
        assert result["latest"]["kg"] == 80.5


class TestExtractIntensityMinutes:
    def test_empty_input(self):
        assert extract_intensity_minutes([]) == {}

    def test_extraction(self):
        data = [{"weeklyModerate": 100, "weeklyVigorous": 50}]
        result = extract_intensity_minutes(data)
        assert result["moderate"] == 100
        assert result["vigorous"] == 50
        assert result["who_equivalent"] == 200  # 100 + 2*50
        assert result["meets_who_target"] is True

    def test_below_target(self):
        data = [{"weeklyModerate": 30, "weeklyVigorous": 10}]
        result = extract_intensity_minutes(data)
        assert result["who_equivalent"] == 50
        assert result["meets_who_target"] is False


class TestExtractRespiration:
    def test_empty_input(self):
        assert extract_respiration([]) == {}

    def test_extraction(self):
        data = [
            {"avgWakingRespirationValue": 16.0, "avgSleepingRespirationValue": 14.0},
            {"avgWakingRespirationValue": 15.0, "avgSleepingRespirationValue": 13.0},
        ]
        result = extract_respiration(data)
        assert result["waking_avg"] == 15.5
        assert result["sleeping_avg"] == 13.5
        assert result["readings"] == 2


class TestExtractSPO2:
    def test_empty_input(self):
        assert extract_spo2([]) == {}

    def test_extraction(self):
        data = [{"averageSPO2": 96}, {"averageSPO2": 97}]
        result = extract_spo2(data)
        assert result["avg"] == 96.5
        assert result["min"] == 96
        assert result["max"] == 97


class TestExtractDevices:
    def test_empty_input(self):
        assert extract_devices([]) == []

    def test_extraction(self):
        data = [{"productDisplayName": "Venu 4"}, {"productDisplayName": "Index S2"}]
        result = extract_devices(data)
        assert result == ["Venu 4", "Index S2"]


class TestExtractPersonalRecords:
    def test_empty_input(self):
        assert extract_personal_records([]) == {}

    def test_count(self):
        data = [{"typeId": 1, "value": 100}, {"typeId": 2, "value": 200}]
        result = extract_personal_records(data)
        assert result["count"] == 2


class TestExtractAll:
    def test_with_real_sync_folder(self):
        """Integration test — runs against actual synced data if available."""
        folder = _project_root / "data" / "synced" / "2026-01-19_to_2026-02-15"
        if not folder.exists():
            pytest.skip("No synced data available for integration test")

        result = extract_all(folder)
        assert result["folder"] == "2026-01-19_to_2026-02-15"
        assert "daily_stats" in result
        assert result["daily_stats"]["days"] == 28
        assert result["daily_stats"]["steps"]["avg"] > 0

    def test_with_empty_folder(self, tmp_path):
        """Should return minimal result for empty folder."""
        meta = {"start_date": "2026-01-01", "end_date": "2026-01-07", "data_types": [], "num_data_types": 0, "synced_at": "now"}
        (tmp_path / "meta.json").write_text(json.dumps(meta))
        result = extract_all(tmp_path)
        assert result["num_data_types"] == 0
        assert "daily_stats" not in result


class TestFormatReport:
    def test_minimal_report(self):
        metrics = {"folder": "test", "period": "2026-01-01 → 2026-01-07", "synced_at": "now", "num_data_types": 0}
        report = format_report(metrics)
        assert "VITALIS METRIC EXTRACTION REPORT" in report
        assert "test" in report

    def test_full_report_has_sections(self):
        folder = _project_root / "data" / "synced" / "2026-01-19_to_2026-02-15"
        if not folder.exists():
            pytest.skip("No synced data available")

        metrics = extract_all(folder)
        report = format_report(metrics)
        assert "DAILY STATS" in report
        assert "ACTIVITIES" in report
        assert "HRV" in report
        assert "VO2MAX" in report
