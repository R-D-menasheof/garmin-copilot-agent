from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from prepare_weekly_review import build_weekly_context, parse_args  # noqa: E402

USER_ID = "11111111-1111-4111-8111-111111111111"


def _model(payload: dict, **attrs) -> MagicMock:
    model = MagicMock()
    model.model_dump.return_value = payload
    for key, value in attrs.items():
        setattr(model, key, value)
    return model


def _store() -> MagicMock:
    store = MagicMock()
    store.load_combined.return_value = {
        "biometrics": {
            "2026-07-09": {"steps": 5000},
            "2026-07-10": {"steps": 6000},
        },
        "nutrition": {
            "2026-07-10": [{"food_name": "יוגורט"}],
        },
    }
    store.load_sleep_entries.return_value = [_model({"date": "2026-07-10"})]
    store.load_summary_history.return_value = [_model({"date": "2026-07-03"})]
    store.load_profile.return_value = _model(
        {"display_name": "משתמשת בדיקה", "last_synced": "2026-07-10"},
        last_synced=date(2026, 7, 10),
    )
    store.load_goals.return_value = None
    store.load_biometrics_range.return_value = {}
    store.load_goal_programs.return_value = []
    store.load_active_training_program.return_value = None
    store.load_recommendation_statuses.return_value = []
    store.load_lab_trends.return_value = []
    return store


def test_requires_user_id() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_builds_deterministic_user_scoped_packet() -> None:
    store = _store()

    packet = build_weekly_context(
        USER_ID,
        end=date(2026, 7, 10),
        days=7,
        store=store,
    )

    assert packet["user_id"] == USER_ID
    assert packet["period"] == {
        "start": "2026-07-04",
        "end": "2026-07-10",
        "days": 7,
    }
    assert packet["profile"]["display_name"] == "משתמשת בדיקה"
    assert packet["data_quality"]["biometric_days"] == 2
    assert packet["data_quality"]["nutrition_days"] == 1
    assert packet["data_quality"]["missing_biometric_days"] == 5
    assert len(packet["context_sha256"]) == 64
    assert packet["data_quality"]["last_synced"] == "2026-07-10"
    assert packet["data_quality"]["sync_freshness"] == "fresh"
    assert packet["nutrition_goal_audit"]["status"] == "missing_profile_inputs"
    assert packet["data_quality"]["has_nutrition_goal"] is False
    assert packet["data_quality"]["nutrition_goal_status"] == "missing_profile_inputs"
    assert packet["local_report_directory"].endswith(
        f"data\\users\\{USER_ID}\\reports"
    )


def test_rejects_invalid_user_id() -> None:
    with pytest.raises(ValueError, match="Invalid user_id"):
        build_weekly_context("..\\owner", date(2026, 7, 10), store=_store())


def test_rejects_non_positive_period() -> None:
    with pytest.raises(ValueError, match="days must be at least 1"):
        build_weekly_context(USER_ID, date(2026, 7, 10), days=0, store=_store())


def test_marks_old_sync_as_stale() -> None:
    store = _store()
    store.load_profile.return_value = _model(
        {"display_name": "משתמשת בדיקה", "last_synced": "2026-06-30"},
        last_synced=date(2026, 6, 30),
    )

    packet = build_weekly_context(
        USER_ID,
        end=date(2026, 7, 10),
        days=7,
        store=store,
    )

    assert packet["data_quality"]["sync_freshness"] == "stale"


def test_empty_biometric_placeholders_do_not_count_as_covered_days() -> None:
    store = _store()
    store.load_combined.return_value = {
        "biometrics": {
            "2026-07-08": {
                "date": "2026-07-08",
                "source": "",
                "steps": None,
                "sleep_seconds": None,
                "activity_types": [],
            },
            "2026-07-09": {
                "date": "2026-07-09",
                "source": "health_connect",
                "steps": 0,
                "sleep_seconds": None,
                "activity_types": [],
            },
            "2026-07-10": {
                "date": "2026-07-10",
                "source": "garmin_direct",
                "steps": 6200,
                "sleep_seconds": None,
                "activity_types": ["walking"],
            },
        },
        "nutrition": {},
    }

    packet = build_weekly_context(
        USER_ID,
        end=date(2026, 7, 10),
        days=7,
        store=store,
    )

    # A real zero-step day and a Garmin day both count; metadata-only does not.
    assert packet["data_quality"]["biometric_days"] == 2
    assert packet["data_quality"]["missing_biometric_days"] == 5
