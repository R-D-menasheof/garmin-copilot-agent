"""Tests for nutrition-related Pydantic models — TDD RED phase.

These models support the Vitalis mobile app's nutrition tracking features.
Models live in src/vitalis/models.py (SSOT for all data shapes).
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from vitalis.models import (
    AnalysisSummary,
    BiometricsRecord,
    ChecklistItem,
    CorrelationRelationship,
    DailyNutritionLog,
    GoalProgram,
    HealthCorrelation,
    HealthRecommendation,
    KnownFood,
    LabDataPoint,
    LabStatus,
    LabTrend,
    MealEntry,
    Milestone,
    NudgeRule,
    NutritionGoal,
    NutritionSource,
    RecStatus,
    RecommendationStatus,
    SleepChecklist,
    SleepEntry,
    TimelineCategory,
    TimelineEvent,
    TimelineSeverity,
    TrainingProgram,
    TrainingSession,
    TrainingWeek,
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

    def test_rest_day_fields_optional(self) -> None:
        goal = NutritionGoal(
            date=date(2026, 4, 4),
            calories_target=2500,
            protein_g_target=150.0,
            carbs_g_target=288.0,
            fat_g_target=83.0,
            set_by="agent",
        )
        assert goal.rest_calories_target is None
        assert goal.rest_carbs_g_target is None

    def test_rest_day_fields_set(self) -> None:
        goal = NutritionGoal(
            date=date(2026, 4, 4),
            calories_target=2500,
            protein_g_target=150.0,
            carbs_g_target=288.0,
            fat_g_target=83.0,
            rest_calories_target=2250,
            rest_carbs_g_target=200.0,
            set_by="agent",
        )
        assert goal.rest_calories_target == 2250
        assert goal.rest_carbs_g_target == 200.0


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


# ── AnalysisSummary ───────────────────────────────────────────────


def _summary(**overrides) -> AnalysisSummary:
    """Factory for a minimal AnalysisSummary."""
    defaults = dict(
        date=date(2026, 4, 4),
        period_start=date(2026, 3, 28),
        period_end=date(2026, 4, 4),
        metrics_snapshot={"avg_daily_steps": 9000},
        trends=["Steps improving"],
        recommendations=[
            HealthRecommendation(
                category="sleep",
                title="Extend sleep to 7h",
                detail="Average 6.3h — below target",
                priority=1,
            ),
        ],
        context_for_next_run="HRV baseline 29ms",
    )
    defaults.update(overrides)
    return AnalysisSummary(**defaults)


class TestAnalysisSummaryReportMarkdown:
    def test_report_markdown_defaults_empty(self) -> None:
        summary = _summary()
        assert summary.report_markdown == ""

    def test_report_markdown_roundtrip(self) -> None:
        md = "# דו\"ח בריאות\n\nתוכן בעברית..."
        summary = _summary(report_markdown=md)
        data = summary.model_dump(mode="json")
        restored = AnalysisSummary.model_validate(data)
        assert restored.report_markdown == md

    def test_backward_compatible_without_report_markdown(self) -> None:
        """Existing JSON without report_markdown should still parse."""
        data = _summary().model_dump(mode="json")
        data.pop("report_markdown", None)
        restored = AnalysisSummary.model_validate(data)
        assert restored.report_markdown == ""


# ── RecommendationStatus ─────────────────────────────────────────


class TestRecStatus:
    def test_enum_values(self) -> None:
        assert RecStatus.PENDING == "pending"
        assert RecStatus.DONE == "done"
        assert RecStatus.SNOOZED == "snoozed"


class TestRecommendationStatus:
    def test_creation(self) -> None:
        status = RecommendationStatus(
            rec_id="abc123",
            status=RecStatus.PENDING,
            updated_at=datetime(2026, 4, 4, 12, 0),
        )
        assert status.rec_id == "abc123"
        assert status.status == RecStatus.PENDING

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            RecommendationStatus(
                rec_id="abc",
                status="invalid",
                updated_at=datetime(2026, 4, 4),
            )

    def test_from_recommendation_generates_stable_id(self) -> None:
        rec = HealthRecommendation(
            category="sleep",
            title="Extend sleep to 7h",
            detail="...",
            priority=1,
        )
        status = RecommendationStatus.from_recommendation(rec)
        assert status.rec_id  # non-empty
        assert status.status == RecStatus.PENDING

        # Same rec → same id (stable)
        status2 = RecommendationStatus.from_recommendation(rec)
        assert status.rec_id == status2.rec_id

    def test_different_recs_different_ids(self) -> None:
        rec_a = HealthRecommendation(category="sleep", title="A", detail="", priority=1)
        rec_b = HealthRecommendation(category="fitness", title="B", detail="", priority=2)
        assert RecommendationStatus.from_recommendation(rec_a).rec_id != \
               RecommendationStatus.from_recommendation(rec_b).rec_id

    def test_json_roundtrip(self) -> None:
        status = RecommendationStatus(
            rec_id="abc123",
            status=RecStatus.DONE,
            updated_at=datetime(2026, 4, 4, 12, 0),
        )
        data = status.model_dump(mode="json")
        restored = RecommendationStatus.model_validate(data)
        assert restored.rec_id == "abc123"
        assert restored.status == RecStatus.DONE


# ── NudgeRule ─────────────────────────────────────────────────────


class TestNudgeRule:
    def test_creation(self) -> None:
        rule = NudgeRule(
            condition="sleep_hours < 6",
            message_he="לילה קצר — יום קל מומלץ",
            category="recovery",
            priority=1,
        )
        assert rule.condition == "sleep_hours < 6"
        assert rule.priority == 1

    def test_json_roundtrip(self) -> None:
        rule = NudgeRule(
            condition="resting_hr > 70",
            message_he="דופק מנוחה גבוה",
            category="health",
        )
        data = rule.model_dump(mode="json")
        restored = NudgeRule.model_validate(data)
        assert restored.condition == "resting_hr > 70"

    def test_analysis_summary_with_nudge_rules(self) -> None:
        summary = _summary(
            nudge_rules=[
                NudgeRule(
                    condition="sleep_hours < 6",
                    message_he="לילה קצר",
                    category="sleep",
                )
            ]
        )
        assert len(summary.nudge_rules) == 1
        # Backward compat: no nudge_rules → empty list
        s2 = _summary()
        assert s2.nudge_rules == []


# ── TimelineEvent ─────────────────────────────────────────────────


class TestTimelineEvent:
    def test_creation(self) -> None:
        event = TimelineEvent(
            date=date(2026, 1, 18),
            category=TimelineCategory.MEDICAL,
            title_he="כבד שומני",
            detail_he="אולטרסאונד בטן — כבד שומני קל",
            severity=TimelineSeverity.WARNING,
        )
        assert event.category == "medical"
        assert event.severity == "warning"

    def test_json_roundtrip(self) -> None:
        event = TimelineEvent(
            date=date(2026, 3, 13),
            category=TimelineCategory.MEDICATION,
            title_he="הפסקת Telfast",
        )
        data = event.model_dump(mode="json")
        restored = TimelineEvent.model_validate(data)
        assert restored.title_he == "הפסקת Telfast"


# ── HealthCorrelation ─────────────────────────────────────────────


class TestHealthCorrelation:
    def test_creation(self) -> None:
        corr = HealthCorrelation(
            metric_a="sleep_hours",
            metric_b="hrv_nightly",
            relationship=CorrelationRelationship.POSITIVE,
            description_he="HRV גבוה ב-35% אחרי 7+ שעות שינה",
            evidence="4 weeks of data",
            confidence=0.85,
            discovered_date=date(2026, 4, 4),
        )
        assert corr.confidence == 0.85

    def test_analysis_summary_with_correlations(self) -> None:
        summary = _summary()
        assert summary.correlations == []


# ── TrainingProgram ───────────────────────────────────────────────


class TestTrainingProgram:
    def test_creation(self) -> None:
        session = TrainingSession(
            day="ראשון", type="swimming", description="אירובי 800m",
            duration_min=45, target_hr_zone=2,
        )
        week = TrainingWeek(week_number=1, sessions=[session])
        program = TrainingProgram(
            name="מבצע VO2max 40", goal="vo2max", duration_weeks=8, weeks=[week],
        )
        assert program.active is True
        assert len(program.weeks[0].sessions) == 1

    def test_session_completion(self) -> None:
        s = TrainingSession(day="Mon", type="swim")
        assert s.completed is False


# ── GoalProgram ───────────────────────────────────────────────────


class TestGoalProgram:
    def test_creation(self) -> None:
        m = Milestone(title_he="שקילה שבועית", target_metric="weight_kg", target_value=100)
        program = GoalProgram(
            name_he="פרויקט 100 ק\"ג", duration_weeks=12, milestones=[m],
        )
        assert program.active is True
        assert len(program.milestones) == 1


# ── SleepEntry ────────────────────────────────────────────────────


class TestSleepEntry:
    def test_creation(self) -> None:
        entry = SleepEntry(date=date(2026, 4, 4), rating=4, bedtime="23:00")
        assert entry.rating == 4

    def test_checklist(self) -> None:
        item = ChecklistItem(id="caffeine", label_he="ללא קפאין אחרי 14:00", category="habits")
        checklist = SleepChecklist(items=[item])
        assert len(checklist.items) == 1


# ── LabTrend ──────────────────────────────────────────────────────


class TestLabTrend:
    def test_creation(self) -> None:
        point = LabDataPoint(
            date=date(2025, 9, 3), value=116.4, unit="mg/dL",
            reference_range="<130", status=LabStatus.NORMAL,
        )
        trend = LabTrend(metric="LDL", display_name_he="כולסטרול LDL", values=[point])
        assert len(trend.values) == 1
        assert trend.values[0].value == 116.4
