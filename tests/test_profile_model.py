"""Tests for the Profile Pydantic model — TDD RED phase.

The cloud Profile (``users/{user_id}/profile.json``) holds each user's
personal info (editable in-app) plus auto-synced wearable metrics.
Models live in src/vitalis/models.py (SSOT), mirrored in api/vitalis/models.py.
"""

from __future__ import annotations

from datetime import date

from vitalis.models import Device, HealthLogEntry, Medication, Profile, Supplement


class TestProfileCreation:
    def test_minimal_defaults(self) -> None:
        p = Profile()
        assert p.display_name == ""
        assert p.email == ""
        assert p.onboarded is False
        assert p.goals == []
        assert p.current_medications == []
        assert p.supplements == []
        assert p.health_log == []
        assert p.devices == []

    def test_full_profile(self) -> None:
        p = Profile(
            display_name="Dana",
            email="dana@example.com",
            date_of_birth=date(1990, 1, 1),
            sex="Female",
            height_cm=165,
            goals=["ירידה במשקל"],
            dietary_preferences=["צמחוני"],
            current_medications=[Medication(name="Steronase", type="nasal spray")],
            supplements=[Supplement(name="Magnesium", dosage="200mg")],
            health_log=[HealthLogEntry(date=date(2026, 3, 13), note="הפסקתי")],
            onboarded=True,
        )
        assert p.display_name == "Dana"
        assert p.sex == "Female"
        assert p.current_medications[0].name == "Steronase"
        assert p.supplements[0].dosage == "200mg"
        assert p.health_log[0].note == "הפסקתי"
        assert p.onboarded is True


class TestAgeComputation:
    def test_age_from_date_of_birth(self) -> None:
        dob = date(1990, 1, 1)
        p = Profile(date_of_birth=dob)
        expected = round((date.today() - dob).days / 365.25, 1)
        assert p.age_years == expected

    def test_age_falls_back_to_legacy_field(self) -> None:
        p = Profile(age=36.5)
        assert p.age_years == 36.5

    def test_dob_takes_precedence_over_legacy_age(self) -> None:
        dob = date(2000, 6, 15)
        p = Profile(date_of_birth=dob, age=99)
        expected = round((date.today() - dob).days / 365.25, 1)
        assert p.age_years == expected

    def test_age_none_when_no_dob_and_no_legacy(self) -> None:
        assert Profile().age_years is None


class TestProfileJsonRoundtrip:
    def test_roundtrip_preserves_all_fields(self) -> None:
        p = Profile(
            display_name="Roei",
            email="roei@example.com",
            date_of_birth=date(1989, 12, 1),
            sex="Male",
            height_cm=183,
            goals=["Weight loss"],
            current_medications=[Medication(name="Telfast", stopped="2026-03-13")],
            weight_kg=112.0,
            vo2max=42.0,
            onboarded=True,
        )
        restored = Profile.model_validate_json(p.model_dump_json())
        assert restored == p
        assert restored.date_of_birth == date(1989, 12, 1)
        assert restored.current_medications[0].stopped == "2026-03-13"

    def test_auto_synced_fields_default_none(self) -> None:
        p = Profile()
        assert p.weight_kg is None
        assert p.body_fat_pct is None
        assert p.bmi is None
        assert p.vo2max is None
        assert p.fitness_age is None
        assert p.resting_heart_rate is None
        assert p.last_synced is None


class TestSubModels:
    def test_medication_stopped_marks_not_deletes(self) -> None:
        med = Medication(name="Telfast", stopped="2026-03-13")
        assert med.name == "Telfast"
        assert med.stopped == "2026-03-13"

    def test_supplement_fields(self) -> None:
        s = Supplement(name="Magnesium Glycinate", dosage="200mg", timing="evening")
        assert s.name == "Magnesium Glycinate"
        assert s.timing == "evening"

    def test_device_fields(self) -> None:
        d = Device(name="Venu 4 - 45mm", type="watch")
        assert d.name == "Venu 4 - 45mm"
        assert d.type == "watch"
