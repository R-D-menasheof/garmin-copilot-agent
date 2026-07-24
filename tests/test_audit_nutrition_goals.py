"""Tests for per-user nutrition-goal audits."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from audit_nutrition_goals import (  # noqa: E402
    audit_goal,
    audit_user,
    observed_tdee_from_biometrics,
)
from vitalis.models import NutritionGoal, Profile  # noqa: E402


def _profile(**changes) -> Profile:
    values = {
        "display_name": "Test",
        "date_of_birth": date(1990, 1, 1),
        "sex": "Female",
        "height_cm": 170.0,
        "weight_kg": 80.0,
        "goals": ["weight loss"],
        "last_synced": "2026-07-24",
        "onboarded": True,
    }
    values.update(changes)
    return Profile(**values)


def _goal(**changes) -> NutritionGoal:
    values = {
        "date": date(2026, 7, 24),
        "calories_target": 1800,
        "protein_g_target": 120.0,
        "carbs_g_target": 195.0,
        "fat_g_target": 60.0,
        "set_by": "agent",
        "calculated_from_weight_kg": 80.0,
        "estimated_tdee_kcal": 2400,
        "calculation_method": "mifflin_st_jeor+garmin",
        "calculation_version": 1,
    }
    values.update(changes)
    return NutritionGoal(**values)


def test_valid_goal_passes_consistency_and_freshness() -> None:
    result = audit_goal(_profile(), _goal(), today=date(2026, 7, 24))

    assert result["status"] == "valid"
    assert result["macro_calories"] == 1800
    assert result["issues"] == []


def test_missing_goal_is_flagged() -> None:
    result = audit_goal(
        _profile(),
        None,
        today=date(2026, 7, 24),
        observed_tdee_kcal=2400,
    )

    assert result["status"] == "missing"
    assert "nutrition_goal_missing" in result["issues"]
    assert result["profile_last_synced"] == "2026-07-24"


def test_inconsistent_macros_are_flagged() -> None:
    result = audit_goal(
        _profile(),
        _goal(
            calories_target=2200,
            protein_g_target=180,
            carbs_g_target=250,
            fat_g_target=70,
        ),
        today=date(2026, 7, 24),
    )

    assert result["status"] == "inconsistent"
    assert result["macro_calories"] == 2350
    assert "macro_calories_mismatch" in result["issues"]


def test_inconsistent_rest_day_macros_are_flagged() -> None:
    result = audit_goal(
        _profile(),
        _goal(rest_calories_target=1600, rest_carbs_g_target=195),
        today=date(2026, 7, 24),
    )

    assert result["status"] == "inconsistent"
    assert result["rest_macro_calories"] == 1800
    assert "rest_macro_calories_mismatch" in result["issues"]


def test_routine_profile_sync_does_not_make_goal_stale() -> None:
    result = audit_goal(
        _profile(last_synced="2026-07-24"),
        _goal(date=date(2026, 7, 10)),
        today=date(2026, 7, 24),
    )

    assert result["status"] == "valid"


def test_goal_older_than_35_days_is_stale() -> None:
    result = audit_goal(
        _profile(),
        _goal(date=date(2026, 6, 18)),
        today=date(2026, 7, 24),
    )

    assert result["status"] == "stale"
    assert result["goal_date"] == "2026-06-18"
    assert "goal_older_than_35_days" in result["issues"]


def test_material_weight_change_makes_goal_stale() -> None:
    result = audit_goal(
        _profile(weight_kg=76.0),
        _goal(calculated_from_weight_kg=80.0),
        today=date(2026, 7, 24),
    )

    assert result["status"] == "stale"
    assert "weight_changed_materially" in result["issues"]


def test_legacy_goal_without_calculation_provenance_is_stale() -> None:
    result = audit_goal(
        _profile(),
        _goal(
            calculated_from_weight_kg=None,
            estimated_tdee_kcal=None,
            calculation_method=None,
            calculation_version=None,
        ),
        today=date(2026, 7, 24),
    )

    assert result["status"] == "stale"
    assert "calculation_provenance_missing" in result["issues"]


def test_material_tdee_change_makes_goal_stale() -> None:
    result = audit_goal(
        _profile(),
        _goal(estimated_tdee_kcal=2400),
        today=date(2026, 7, 24),
        observed_tdee_kcal=2700,
    )

    assert result["status"] == "stale"
    assert result["observed_tdee_kcal"] == 2700
    assert "tdee_changed_materially" in result["issues"]


def test_observed_tdee_uses_median_of_seven_valid_days() -> None:
    biometrics = {
        f"2026-07-{day:02d}": {"total_calories": calories}
        for day, calories in enumerate(
            [2200, 2250, 2300, 2350, 2400, 2450, 5000],
            start=1,
        )
    }

    assert observed_tdee_from_biometrics(biometrics) == 2350


def test_observed_tdee_requires_seven_valid_days() -> None:
    biometrics = {
        "2026-07-01": {"total_calories": 2200},
        "2026-07-02": {"total_calories": 2250},
        "2026-07-03": {"total_calories": 0},
        "2026-07-04": {"total_calories": None},
    }

    assert observed_tdee_from_biometrics(biometrics) is None


def test_audit_user_uses_recent_biometrics_for_tdee() -> None:
    class Store:
        def load_profile(self):
            return _profile()

        def load_goals(self):
            return _goal(estimated_tdee_kcal=2400)

        def load_biometrics_range(self, start: date, end: date):
            assert start == date(2026, 7, 11)
            assert end == date(2026, 7, 24)
            return {
                date(2026, 7, day): {"total_calories": calories}
                for day, calories in enumerate(
                    [2600, 2650, 2680, 2700, 2720, 2750, 2800],
                    start=18,
                )
            }

    result = audit_user("u-123", store=Store(), today=date(2026, 7, 24))

    assert result["observed_tdee_kcal"] == 2700
    assert result["status"] == "stale"
    assert "tdee_changed_materially" in result["issues"]


def test_missing_profile_inputs_prevent_calculation() -> None:
    result = audit_goal(
        _profile(weight_kg=None, date_of_birth=None),
        None,
        today=date(2026, 7, 24),
        observed_tdee_kcal=2400,
    )

    assert result["status"] == "missing_profile_inputs"
    assert set(result["missing_profile_inputs"]) == {"date_of_birth", "weight_kg"}


def test_missing_explicit_goal_prevents_calculation() -> None:
    result = audit_goal(
        _profile(goals=[]),
        None,
        today=date(2026, 7, 24),
        observed_tdee_kcal=2400,
    )

    assert result["status"] == "missing_profile_inputs"
    assert result["missing_profile_inputs"] == ["goals"]


def test_legacy_age_satisfies_age_input() -> None:
    result = audit_goal(
        _profile(date_of_birth=None, age=35),
        None,
        today=date(2026, 7, 24),
        observed_tdee_kcal=2400,
    )

    assert result["status"] == "missing"
    assert "date_of_birth" not in result["missing_profile_inputs"]


def test_missing_tdee_context_prevents_new_calculation() -> None:
    result = audit_goal(_profile(), None, today=date(2026, 7, 24))

    assert result["status"] == "missing_profile_inputs"
    assert result["missing_profile_inputs"] == ["tdee_context"]


def test_explicit_user_override_does_not_require_agent_provenance() -> None:
    result = audit_goal(
        _profile(weight_kg=None, goals=[]),
        _goal(
            set_by="user",
            calculated_from_weight_kg=None,
            estimated_tdee_kcal=None,
            calculation_method=None,
            calculation_version=None,
        ),
        today=date(2026, 7, 24),
    )

    assert result["status"] == "valid"
    assert result["issues"] == ["explicit_user_override"]