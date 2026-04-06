"""Tests for nutrition-related Pydantic models — TDD RED phase.

These models support the Vitalis mobile app's nutrition tracking features.
Models live in src/vitalis/models.py (SSOT for all data shapes).
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from vitalis.models import (
    BiometricsRecord,
    DailyNutritionLog,
    KnownFood,
    MealEntry,
    NutritionGoal,
    NutritionSource,
)


# ── NutritionSource enum ──────────────────────────────────────────


class TestNutritionSource:
    def test_enum_values(self) -> None:
        assert NutritionSource.HISTORY == "history"
        assert NutritionSource.OPEN_FOOD_FACTS == "open_food_facts"
        assert NutritionSource.USDA == "usda"
        assert NutritionSource.LLM == "llm"
        assert NutritionSource.MANUAL == "manual"


# ── MealEntry ─────────────────────────────────────────────────────


class TestMealEntry:
    def test_creation_with_required_fields(self) -> None:
        entry = MealEntry(
            food_name="חזה עוף",
            calories=165,
            protein_g=31.0,
            carbs_g=0.0,
            fat_g=3.6,
            source=NutritionSource.LLM,
            timestamp=datetime(2026, 4, 4, 12, 30),
        )
        assert entry.food_name == "חזה עוף"
        assert entry.calories == 165
        assert entry.protein_g == 31.0
        assert entry.source == NutritionSource.LLM

    def test_optional_fields_default_none(self) -> None:
        entry = MealEntry(
            food_name="אוראו",
            calories=53,
            protein_g=0.6,
            carbs_g=8.3,
            fat_g=2.3,
            source=NutritionSource.OPEN_FOOD_FACTS,
            timestamp=datetime(2026, 4, 4, 15, 0),
        )
        assert entry.fiber_g is None
        assert entry.portion_description is None

    def test_rejects_negative_calories(self) -> None:
        with pytest.raises(ValidationError):
            MealEntry(
                food_name="test",
                calories=-100,
                protein_g=10.0,
                carbs_g=10.0,
                fat_g=5.0,
                source=NutritionSource.MANUAL,
                timestamp=datetime(2026, 4, 4, 12, 0),
            )


# ── NutritionGoal ─────────────────────────────────────────────────


class TestNutritionGoal:
    def test_creation(self) -> None:
        goal = NutritionGoal(
            date=date(2026, 4, 4),
            calories_target=2200,
            protein_g_target=180.0,
            carbs_g_target=250.0,
            fat_g_target=70.0,
            set_by="agent",
        )
        assert goal.calories_target == 2200
        assert goal.set_by == "agent"

    def test_set_by_validates(self) -> None:
        with pytest.raises(ValidationError):
            NutritionGoal(
                date=date(2026, 4, 4),
                calories_target=2200,
                protein_g_target=180.0,
                carbs_g_target=250.0,
                fat_g_target=70.0,
                set_by="robot",  # invalid — must be "user" or "agent"
            )


# ── DailyNutritionLog ────────────────────────────────────────────


class TestDailyNutritionLog:
    def test_empty_meals(self) -> None:
        log = DailyNutritionLog(date=date(2026, 4, 4))
        assert log.meals == []
        assert log.goal_compliance_pct is None

    def test_serializes_to_json(self) -> None:
        entry = MealEntry(
            food_name="banana",
            calories=89,
            protein_g=1.1,
            carbs_g=22.8,
            fat_g=0.3,
            source=NutritionSource.HISTORY,
            timestamp=datetime(2026, 4, 4, 8, 0),
        )
        log = DailyNutritionLog(date=date(2026, 4, 4), meals=[entry])
        data = log.model_dump(mode="json")
        assert data["date"] == "2026-04-04"
        assert len(data["meals"]) == 1
        assert data["meals"][0]["food_name"] == "banana"

        # Roundtrip
        restored = DailyNutritionLog.model_validate(data)
        assert restored.meals[0].food_name == "banana"


# ── BiometricsRecord ──────────────────────────────────────────────


class TestBiometricsRecord:
    def test_creation(self) -> None:
        rec = BiometricsRecord(
            date=date(2026, 4, 4),
            resting_hr=65,
            hrv_ms=27,
            steps=8500,
            active_calories=350,
        )
        assert rec.resting_hr == 65
        assert rec.date == date(2026, 4, 4)

    def test_optional_fields(self) -> None:
        rec = BiometricsRecord(date=date(2026, 4, 4))
        assert rec.resting_hr is None
        assert rec.hrv_ms is None
        assert rec.spo2_pct is None
        assert rec.sleep_seconds is None
        assert rec.weight_kg is None
        assert rec.body_fat_pct is None


# ── KnownFood ────────────────────────────────────────────────────


class TestKnownFood:
    def test_creation_with_aliases(self) -> None:
        food = KnownFood(
            food_name="אוראו",
            calories_per_100g=480,
            protein_per_100g=4.0,
            carbs_per_100g=70.0,
            fat_per_100g=20.0,
            source=NutritionSource.OPEN_FOOD_FACTS,
            aliases=["oreo", "אוריאו"],
        )
        assert food.food_name == "אוראו"
        assert len(food.aliases) == 2
        assert "oreo" in food.aliases

    def test_json_roundtrip(self) -> None:
        food = KnownFood(
            food_name="banana",
            calories_per_100g=89,
            protein_per_100g=1.1,
            carbs_per_100g=22.8,
            fat_per_100g=0.3,
            source=NutritionSource.USDA,
        )
        data = food.model_dump(mode="json")
        restored = KnownFood.model_validate(data)
        assert restored.food_name == "banana"
        assert restored.calories_per_100g == 89
        assert restored.source == NutritionSource.USDA
        assert restored.aliases == []
