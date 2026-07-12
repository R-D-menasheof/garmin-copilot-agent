"""Tests for mapping direct Garmin responses into cloud biometrics."""

from __future__ import annotations

from datetime import date

from vitalis.garmin_biometrics import (
    extract_garmin_biometrics,
    merge_biometrics_records,
)
from vitalis.models import BiometricsRecord


def test_extract_garmin_biometrics_maps_real_response_shapes() -> None:
    raw = {
        "daily_stats": [
            {
                "calendarDate": "2026-07-10",
                "totalSteps": 6789,
                "restingHeartRate": 68,
                "maxHeartRate": 137,
                "activeKilocalories": 312,
                "totalKilocalories": 1960,
                "floorsAscended": 4,
                "totalDistanceMeters": 4820.5,
                "sleepingSeconds": 22680,
                "averageStressLevel": 34,
                "maxStressLevel": 86,
                "bodyBatteryHighestValue": 72,
                "bodyBatteryLowestValue": 18,
                "bodyBatteryAtWakeTime": 64,
                "averageSpo2": 96.0,
                "avgWakingRespirationValue": 15.5,
                "moderateIntensityMinutes": 21,
                "vigorousIntensityMinutes": 8,
            }
        ],
        "heart_rate": [
            {
                "calendarDate": "2026-07-10",
                "restingHeartRate": 67,
                "maxHeartRate": 139,
            }
        ],
        "sleep": [
            {
                "dailySleepDTO": {
                    "calendarDate": "2026-07-10",
                    "sleepTimeSeconds": 23400,
                    "deepSleepSeconds": 4200,
                    "lightSleepSeconds": 13200,
                    "remSleepSeconds": 4800,
                    "awakeSleepSeconds": 1200,
                    "averageSpO2Value": 95.5,
                    "averageRespirationValue": 14.8,
                    "avgHeartRate": 62,
                    "sleepScores": {"overall": {"value": 71}},
                }
            }
        ],
        "hrv": [
            {
                "hrvSummary": {
                    "calendarDate": "2026-07-10",
                    "lastNightAvg": 29,
                }
            }
        ],
        "intensity_minutes": [
            {
                "calendarDate": "2026-07-10",
                "moderateMinutes": 22,
                "vigorousMinutes": 9,
            }
        ],
        "hydration": [
            {"calendarDate": "2026-07-10", "valueInML": 1500}
        ],
        "training_readiness": [
            {"calendarDate": "2026-07-10", "score": 55}
        ],
        "activities": [
            {
                "startTimeLocal": "2026-07-10 18:30:00",
                "duration": 1800,
                "activityType": {"typeKey": "walking"},
                "averageHR": 104,
                "maxHR": 132,
            },
            {
                "startTimeLocal": "2026-07-10 20:00:00",
                "duration": 1200,
                "activityType": {"typeKey": "yoga"},
                "averageHR": 82,
                "maxHR": 101,
            },
        ],
    }

    result = extract_garmin_biometrics(raw)

    record = result[date(2026, 7, 10)]
    assert record.source == "garmin_direct"
    assert record.steps == 6789
    assert record.resting_hr == 67
    assert record.max_hr == 139
    assert record.active_calories == 312
    assert record.sleep_seconds == 23400
    assert record.deep_sleep_seconds == 4200
    assert record.rem_sleep_seconds == 4800
    assert record.sleep_score == 71
    assert record.hrv_ms == 29
    assert record.spo2_pct == 95.5
    assert record.respiratory_rate == 14.8
    assert record.moderate_intensity_minutes == 22
    assert record.vigorous_intensity_minutes == 9
    assert record.intensity_minutes == 40
    assert record.body_battery_high == 72
    assert record.body_battery_low == 18
    assert record.body_battery_at_wake == 64
    assert record.stress_avg == 34
    assert record.stress_max == 86
    assert record.training_readiness == 55
    assert record.water_ml == 1500
    assert record.activity_count == 2
    assert record.activity_types == ["walking", "yoga"]
    assert record.exercise_minutes == 50


def test_extract_garmin_biometrics_handles_unsupported_venu_sq_metrics() -> None:
    raw = {
        "daily_stats": [
            {"calendarDate": "2026-07-10", "totalSteps": 2500}
        ],
        "hrv": [],
        "training_readiness": [],
    }

    record = extract_garmin_biometrics(raw)[date(2026, 7, 10)]

    assert record.steps == 2500
    assert record.hrv_ms is None
    assert record.training_readiness is None


def test_extract_garmin_biometrics_ignores_sub_minute_activity_artifacts() -> None:
    raw = {
        "daily_stats": [
            {"calendarDate": "2026-07-10", "totalSteps": 2500}
        ],
        "activities": [
            {
                "startTimeLocal": "2026-07-10 10:00:00",
                "duration": 1.4,
                "activityType": {"typeKey": "walking"},
            },
            {
                "startTimeLocal": "2026-07-10 11:00:00",
                "duration": 21.1,
                "activityType": {"typeKey": "walking"},
            },
        ],
    }

    record = extract_garmin_biometrics(raw)[date(2026, 7, 10)]

    assert record.activity_count == 0
    assert record.activity_types == []
    assert record.exercise_minutes == 0


def test_merge_prefers_direct_garmin_without_erasing_other_source_fields() -> None:
    existing = BiometricsRecord(
        date=date(2026, 7, 10),
        bp_systolic=122,
        bp_diastolic=78,
        steps=6000,
        source="health_connect",
    )
    garmin = BiometricsRecord(
        date=date(2026, 7, 10),
        steps=6789,
        body_battery_high=72,
        source="garmin_direct",
    )

    merged = merge_biometrics_records(existing, garmin)

    assert merged.steps == 6789
    assert merged.body_battery_high == 72
    assert merged.bp_systolic == 122
    assert merged.bp_diastolic == 78
    assert merged.source == "garmin_direct+health_connect"