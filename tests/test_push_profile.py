"""Tests for push_profile — mapping profile.yaml → cloud Profile. TDD RED."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_project_root / "src"))

from push_profile import build_profile  # noqa: E402


def _yaml() -> dict:
    return {
        "name": "Roei",
        "age": 36.5,
        "sex": "Male",
        "height_cm": 183,
        "goals": ["Weight loss", "Stop snoring"],
        "injuries": [],
        "dietary_preferences": ["low sugar"],
        "notes": "some notes",
        "current_medications": [
            {"name": "Steronase AQ", "type": "nasal spray", "frequency": "as needed",
             "for": "allergies", "since": "2025-08-01"},
        ],
        "supplements": [
            {"name": "Magnesium", "dosage": "200mg", "timing": "evening",
             "since": "2026-03-07", "note": "for sleep"},
        ],
        "health_log": [
            {"date": "2026-03-13", "note": "stopped Telfast"},
        ],
        "weight_kg": 112.0,
        "body_fat_pct": None,
        "bmi": None,
        "vo2max": None,
        "fitness_age": None,
        "resting_heart_rate": 65,
        "devices": [{"name": "Venu 4 - 45mm", "type": ""}],
        "last_synced": "2026-07-02",
    }


class TestBuildProfile:
    def test_maps_core_identity_fields(self) -> None:
        p = build_profile(_yaml())
        assert p.display_name == "Roei"
        assert p.sex == "Male"
        assert p.height_cm == 183
        assert p.age == 36.5

    def test_marks_onboarded_true(self) -> None:
        # An existing full profile shouldn't trigger the onboarding wizard.
        assert build_profile(_yaml()).onboarded is True

    def test_maps_goals_and_prefs(self) -> None:
        p = build_profile(_yaml())
        assert p.goals == ["Weight loss", "Stop snoring"]
        assert p.dietary_preferences == ["low sugar"]

    def test_medication_for_maps_to_purpose(self) -> None:
        p = build_profile(_yaml())
        assert len(p.current_medications) == 1
        med = p.current_medications[0]
        assert med.name == "Steronase AQ"
        assert med.purpose == "allergies"  # yaml 'for' -> model 'purpose'
        assert med.frequency == "as needed"
        assert med.since == "2025-08-01"

    def test_maps_supplements(self) -> None:
        s = build_profile(_yaml()).supplements[0]
        assert s.name == "Magnesium"
        assert s.dosage == "200mg"
        assert s.note == "for sleep"

    def test_maps_health_log(self) -> None:
        log = build_profile(_yaml()).health_log
        assert len(log) == 1
        assert log[0].date == date(2026, 3, 13)
        assert log[0].note == "stopped Telfast"

    def test_maps_auto_synced_fields(self) -> None:
        p = build_profile(_yaml())
        assert p.weight_kg == 112.0
        assert p.resting_heart_rate == 65
        assert p.last_synced == "2026-07-02"

    def test_maps_devices(self) -> None:
        d = build_profile(_yaml()).devices[0]
        assert d.name == "Venu 4 - 45mm"

    def test_handles_missing_optional_fields(self) -> None:
        # A sparse profile must not crash.
        p = build_profile({"name": "X"})
        assert p.display_name == "X"
        assert p.goals == []
        assert p.current_medications == []

    def test_preserves_stopped_medication(self) -> None:
        y = _yaml()
        y["current_medications"][0]["stopped"] = "2026-06-01"
        med = build_profile(y).current_medications[0]
        assert med.stopped == "2026-06-01"  # never lose 'stopped' data

    def test_coerces_yaml_date_objects_to_strings(self) -> None:
        # PyYAML auto-parses ISO dates into datetime.date; string fields must cope.
        y = _yaml()
        y["current_medications"][0]["since"] = date(2025, 8, 1)
        y["supplements"][0]["since"] = date(2026, 3, 7)
        y["last_synced"] = date(2026, 7, 2)
        p = build_profile(y)
        assert p.current_medications[0].since == "2025-08-01"
        assert p.supplements[0].since == "2026-03-07"
        assert p.last_synced == "2026-07-02"
