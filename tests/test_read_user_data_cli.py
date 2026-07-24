"""Tests for scripts/read_user_data.py (Phase 6.2).

Core aggregation logic is tested with an in-memory fake store, so no cloud
connection is required.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Ensure scripts are importable (matches the other CLI tests).
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from read_user_data import collect_user_data, parse_args  # noqa: E402


class _Model:
    """Minimal stand-in for a Pydantic model with model_dump()."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self, mode: str | None = None) -> dict:
        return self._data


class _FakeStore:
    """In-memory BlobStore stand-in returning fixed data."""

    def load_profile(self):
        return _Model({"display_name": "רועי", "email": "r@example.com"})

    def load_summary_history(self, limit: int):
        return [_Model({"date": "2026-03-27"})]

    def load_recent_meals(self, limit: int):
        return [_Model({"food_name": "banana", "calories": 89})]

    def load_goals(self):
        return _Model({"calories": 2000})

    def load_recommendation_statuses(self):
        return [_Model({"id": "r1"})]

    def load_lab_trends(self):
        return [_Model({"name": "HbA1c"})]

    def load_active_training_program(self):
        return _Model({"name": "5k plan"})

    def load_goal_programs(self):
        return [_Model({"name": "weight loss"})]

    def load_biometrics_range(self, start: date, end: date):
        return {date(2026, 7, 5): _Model({"steps": 8000})}


class TestCollectUserData:
    def test_aggregates_all_sections(self) -> None:
        data = collect_user_data(_FakeStore(), days=7)
        assert data["profile"]["display_name"] == "רועי"
        assert len(data["summaries"]) == 1
        assert data["recent_meals"][0]["food_name"] == "banana"
        assert data["goals"]["calories"] == 2000
        assert data["recommendations"][0]["id"] == "r1"
        assert data["lab_trends"][0]["name"] == "HbA1c"
        assert data["active_training"]["name"] == "5k plan"
        assert data["goal_programs"][0]["name"] == "weight loss"
        assert data["biometrics"]["2026-07-05"]["steps"] == 8000

    def test_handles_missing_optional_sections(self) -> None:
        class Empty(_FakeStore):
            def load_profile(self):
                return None

            def load_goals(self):
                return None

            def load_active_training_program(self):
                return None

        data = collect_user_data(Empty(), days=7)
        assert data["profile"] is None
        assert data["goals"] is None
        assert data["active_training"] is None
        # non-empty sections still populated
        assert data["recent_meals"][0]["food_name"] == "banana"


class TestParseArgs:
    def test_requires_user_id_and_parses_days(self) -> None:
        args = parse_args(["--user-id", "abc-123", "--days", "14"])
        assert args.user_id == "abc-123"
        assert args.days == 14

    def test_days_defaults_to_30(self) -> None:
        args = parse_args(["--user-id", "abc-123"])
        assert args.days == 30
