"""Shared test fixtures for Vitalis tests."""

import pytest


@pytest.fixture
def sample_activity_csv() -> str:
    """Sample Garmin activities CSV content for testing."""
    return (
        "Activity Type,Date,Favorite,Title,Distance,Calories,Time,Avg HR,Max HR\n"
        "Running,2026-02-10 07:30:00,false,Morning Run,5.12,420,0:25:30,155,178\n"
        "Cycling,2026-02-11 17:00:00,false,Evening Ride,22.5,580,1:05:00,142,165\n"
        "Walking,2026-02-12 12:00:00,false,Lunch Walk,2.1,120,0:30:00,95,110\n"
    )


@pytest.fixture
def sample_garmin_api_activity() -> dict:
    """Sample raw activity dict as returned by garminconnect."""
    return {
        "activityId": 12345678,
        "activityType": {"typeKey": "running"},
        "startTimeLocal": "2026-02-10T07:30:00",
        "duration": 1530.0,
        "distance": 5120.0,
        "averageHR": 155,
        "maxHR": 178,
        "calories": 420,
    }


@pytest.fixture
def sample_garmin_api_daily_stats() -> dict:
    """Sample raw daily stats dict as returned by garminconnect."""
    return {
        "calendarDate": "2026-02-10",
        "totalSteps": 9500,
        "restingHeartRate": 58,
        "averageStressLevel": 32,
        "bodyBatteryChargedValue": 85,
        "bodyBatteryDrainedValue": 22,
        "totalKilocalories": 2200,
        "activeSeconds": 3600,
        "floorsAscended": 12,
    }


@pytest.fixture
def sample_garmin_api_sleep() -> dict:
    """Sample raw sleep dict as returned by garminconnect."""
    return {
        "dailySleepDTO": {
            "calendarDate": "2026-02-10",
            "sleepTimeSeconds": 27000,
            "deepSleepSeconds": 5400,
            "lightSleepSeconds": 13500,
            "remSleepSeconds": 6300,
            "awakeSleepSeconds": 1800,
            "sleepScores": {"overall": {"value": 78}},
        }
    }


@pytest.fixture
def sample_garmin_api_body_comp() -> dict:
    """Sample raw body composition dict as returned by garminconnect."""
    return {
        "calendarDate": "2026-02-10",
        "weight": 78500,  # grams
        "bodyFat": 18.5,
        "muscleMass": 62000,  # grams
        "bmi": 24.2,
    }
