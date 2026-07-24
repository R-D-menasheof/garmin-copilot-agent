"""Audit app-facing nutrition goals for one or all registered users.

This command never invents or writes targets. It identifies users whose goal is
missing, inconsistent, stale, or cannot yet be calculated because profile
inputs are incomplete. The health agent must calculate and persist those goals
through ``scripts/set_goals.py --user-id ...``.

Usage:
    python scripts/audit_nutrition_goals.py --user-id <oid>
    python scripts/audit_nutrition_goals.py --all
"""

# pylint: disable=import-error,wrong-import-position

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date, timedelta
from typing import Any

from _users import get_store, list_users, normalize_user_id

_PROFILE_INPUTS = ("sex", "height_cm", "weight_kg", "goals")
_MAX_GOAL_AGE_DAYS = 35
_WEIGHT_CHANGE_RATIO = 0.03
_WEIGHT_CHANGE_KG = 5.0
_TDEE_CHANGE_RATIO = 0.10
_MIN_TDEE_DAYS = 7


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def observed_tdee_from_biometrics(biometrics: dict[str, Any]) -> int | None:
    """Return median Garmin total calories when at least seven days are valid."""
    totals: list[int] = []
    for record in biometrics.values():
        if not isinstance(record, dict):
            continue
        value = record.get("total_calories")
        if isinstance(value, (int, float)) and value > 0:
            totals.append(round(value))
    if len(totals) < _MIN_TDEE_DAYS:
        return None
    return round(statistics.median(totals))


def audit_goal(
    profile,
    goal,
    *,
    today: date | None = None,
    observed_tdee_kcal: int | None = None,
) -> dict[str, Any]:
    """Classify one user's nutrition-goal health without modifying it."""
    today = today or date.today()
    missing_inputs = [
        field
        for field in _PROFILE_INPUTS
        if profile is None or getattr(profile, field, None) in (None, "", [])
    ]
    if profile is None or (
        getattr(profile, "date_of_birth", None) is None
        and getattr(profile, "age", None) is None
    ):
        missing_inputs.insert(0, "date_of_birth")
    if goal is None and observed_tdee_kcal is None:
        missing_inputs.append("tdee_context")
    issues: list[str] = []

    if goal is None:
        issues.append("nutrition_goal_missing")
        status = "missing_profile_inputs" if missing_inputs else "missing"
        profile_sync = _parse_date(
            getattr(profile, "last_synced", None) if profile is not None else None
        )
        return {
            "status": status,
            "issues": issues,
            "missing_profile_inputs": missing_inputs,
            "macro_calories": None,
            "observed_tdee_kcal": observed_tdee_kcal,
            "goal_date": None,
            "profile_last_synced": profile_sync.isoformat() if profile_sync else None,
        }

    macro_calories = round(
        goal.protein_g_target * 4
        + goal.carbs_g_target * 4
        + goal.fat_g_target * 9
    )
    if macro_calories != goal.calories_target:
        issues.append("macro_calories_mismatch")

    rest_calories = getattr(goal, "rest_calories_target", None)
    rest_carbs = getattr(goal, "rest_carbs_g_target", None)
    rest_macro_calories: int | None = None
    if (rest_calories is None) != (rest_carbs is None):
        issues.append("rest_day_override_incomplete")
    elif rest_calories is not None and rest_carbs is not None:
        rest_macro_calories = round(
            goal.protein_g_target * 4
            + rest_carbs * 4
            + goal.fat_g_target * 9
        )
        if rest_macro_calories != rest_calories:
            issues.append("rest_macro_calories_mismatch")

    explicit_user_override = getattr(goal, "set_by", None) == "user"
    if explicit_user_override:
        issues.append("explicit_user_override")

    goal_date = _parse_date(goal.date)
    profile_sync = _parse_date(
        getattr(profile, "last_synced", None) if profile is not None else None
    )
    if goal_date is not None and today - goal_date > timedelta(days=_MAX_GOAL_AGE_DAYS):
        issues.append("goal_older_than_35_days")

    provenance = (
        getattr(goal, "calculated_from_weight_kg", None),
        getattr(goal, "estimated_tdee_kcal", None),
        getattr(goal, "calculation_method", None),
        getattr(goal, "calculation_version", None),
    )
    if not explicit_user_override and any(value is None for value in provenance):
        issues.append("calculation_provenance_missing")
    baseline_weight = provenance[0]
    current_weight = getattr(profile, "weight_kg", None) if profile is not None else None
    if not explicit_user_override and baseline_weight is not None and current_weight is not None:
        change_kg = abs(current_weight - baseline_weight)
        threshold_kg = min(baseline_weight * _WEIGHT_CHANGE_RATIO, _WEIGHT_CHANGE_KG)
        if change_kg >= threshold_kg:
            issues.append("weight_changed_materially")
    baseline_tdee = provenance[1]
    if not explicit_user_override and baseline_tdee is not None and observed_tdee_kcal is not None:
        tdee_change_ratio = abs(observed_tdee_kcal - baseline_tdee) / baseline_tdee
        if tdee_change_ratio >= _TDEE_CHANGE_RATIO:
            issues.append("tdee_changed_materially")
    if missing_inputs and not explicit_user_override:
        issues.append("profile_inputs_incomplete")

    if any(
        item in issues
        for item in (
            "macro_calories_mismatch",
            "rest_day_override_incomplete",
            "rest_macro_calories_mismatch",
        )
    ):
        status = "inconsistent"
    elif not explicit_user_override and any(
        item in issues
        for item in (
            "goal_older_than_35_days",
            "calculation_provenance_missing",
            "weight_changed_materially",
            "tdee_changed_materially",
        )
    ):
        status = "stale"
    elif missing_inputs and not explicit_user_override:
        status = "missing_profile_inputs"
    else:
        status = "valid"

    return {
        "status": status,
        "issues": issues,
        "missing_profile_inputs": missing_inputs,
        "macro_calories": macro_calories,
        "rest_macro_calories": rest_macro_calories,
        "observed_tdee_kcal": observed_tdee_kcal,
        "goal_date": goal_date.isoformat() if goal_date else None,
        "profile_last_synced": profile_sync.isoformat() if profile_sync else None,
        "goal": goal.model_dump(mode="json"),
    }


def audit_user(user_id: str, *, store=None, today: date | None = None) -> dict[str, Any]:
    """Load and audit one user-scoped profile and nutrition goal."""
    today = today or date.today()
    user_id = normalize_user_id(user_id)
    store = store or get_store(user_id)
    profile = store.load_profile()
    raw_biometrics = store.load_biometrics_range(today - timedelta(days=13), today)
    biometrics = {
        str(day): value.model_dump(mode="json")
        if hasattr(value, "model_dump")
        else value
        for day, value in raw_biometrics.items()
    }
    observed_tdee_kcal = observed_tdee_from_biometrics(biometrics)
    result = audit_goal(
        profile,
        store.load_goals(),
        today=today,
        observed_tdee_kcal=observed_tdee_kcal,
    )
    result.update(
        {
            "user_id": user_id,
            "display_name": getattr(profile, "display_name", "") if profile else "",
            "email": getattr(profile, "email", "") if profile else "",
        }
    )
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit nutrition-goal completeness and consistency."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", help="Target user's id.")
    group.add_argument("--all", action="store_true", help="Audit all registered users.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Print a JSON audit and return non-zero when remediation is required."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    user_ids = (
        [item["user_id"] for item in list_users()]
        if args.all
        else [args.user_id]
    )
    results = [audit_user(user_id) for user_id in user_ids]
    print(json.dumps({"users": results}, ensure_ascii=False, indent=2))
    return 0 if all(item["status"] == "valid" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
