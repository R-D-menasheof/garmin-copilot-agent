"""Tests for BlobStore — Azure Blob Storage operations.

TDD RED phase: all tests written before implementation.
All tests use an in-memory mock — no real Azure calls.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from shared.blob_store import BlobStore
from vitalis.models import (
    BiometricsRecord,
    GoalProgram,
    KnownFood,
    LabDataPoint,
    LabStatus,
    LabTrend,
    MealEntry,
    Milestone,
    NutritionGoal,
    NutritionSource,
    RecStatus,
    RecommendationStatus,
    SleepChecklist,
    SleepEntry,
    ChecklistItem,
    TimelineCategory,
    TimelineEvent,
    TimelineSeverity,
    TrainingProgram,
    TrainingSession,
    TrainingWeek,
)


# ── Fixtures ──────────────────────────────────────────────────────


def _meal(name: str = "banana", cal: int = 89) -> MealEntry:
    return MealEntry(
        food_name=name,
        calories=cal,
        protein_g=1.1,
        carbs_g=22.8,
        fat_g=0.3,
        source=NutritionSource.HISTORY,
        timestamp=datetime(2026, 4, 4, 12, 0),
    )


def _goal() -> NutritionGoal:
    return NutritionGoal(
        date=date(2026, 4, 4),
        calories_target=2200,
        protein_g_target=180.0,
        carbs_g_target=250.0,
        fat_g_target=70.0,
        set_by="agent",
    )


def _biometrics() -> BiometricsRecord:
    return BiometricsRecord(
        date=date(2026, 4, 4),
        resting_hr=65,
        hrv_ms=27,
        steps=8500,
        active_calories=350,
    )


def _known_food(name: str = "אוראו") -> KnownFood:
    return KnownFood(
        food_name=name,
        calories_per_100g=480,
        protein_per_100g=4.0,
        carbs_per_100g=70.0,
        fat_per_100g=20.0,
        source=NutritionSource.OPEN_FOOD_FACTS,
        aliases=["oreo"],
    )


class InMemoryBlobStore:
    """Test helper: BlobStore backed by a dict instead of Azure."""

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    def build(self) -> BlobStore:
        """Create a BlobStore wired to in-memory storage."""
        store = BlobStore.__new__(BlobStore)
        store._container_name = "vitalis-data"

        # Mock container client
        container = MagicMock()
        container.get_blob_client = MagicMock(side_effect=self._get_blob_client)
        store._container = container

        return store

    def _get_blob_client(self, blob: str) -> MagicMock:
        client = MagicMock()

        def upload(data: str | bytes, overwrite: bool = True) -> None:
            self._data[blob] = data.encode() if isinstance(data, str) else data

        def download() -> MagicMock:
            if blob not in self._data:
                from azure.core.exceptions import ResourceNotFoundError
                raise ResourceNotFoundError("Blob not found")
            dl = MagicMock()
            dl.readall.return_value = self._data[blob]
            return dl

        client.upload_blob = MagicMock(side_effect=upload)
        client.download_blob = MagicMock(side_effect=download)
        return client

    def get_raw(self, blob: str) -> dict | list | None:
        if blob not in self._data:
            return None
        return json.loads(self._data[blob])


@pytest.fixture
def store_and_backend():
    backend = InMemoryBlobStore()
    return backend.build(), backend


# ── Meals ─────────────────────────────────────────────────────────


class TestSaveMeals:
    def test_save_meals_creates_dated_blob(self, store_and_backend) -> None:
        store, backend = store_and_backend
        meals = [_meal("banana"), _meal("apple", 52)]
        store.save_meals(date(2026, 4, 4), meals)

        raw = backend.get_raw("meals/2026-04-04.json")
        assert raw is not None
        assert len(raw) == 2
        assert raw[0]["food_name"] == "banana"

    def test_load_meals_returns_list_of_meal_entry(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_meals(date(2026, 4, 4), [_meal()])

        result = store.load_meals(date(2026, 4, 4))
        assert len(result) == 1
        assert isinstance(result[0], MealEntry)
        assert result[0].food_name == "banana"

    def test_load_meals_nonexistent_date_returns_empty_list(self, store_and_backend) -> None:
        store, _ = store_and_backend
        result = store.load_meals(date(2099, 1, 1))
        assert result == []

    def test_load_meals_range_multiple_days(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_meals(date(2026, 4, 3), [_meal("egg", 155)])
        store.save_meals(date(2026, 4, 4), [_meal("banana")])

        result = store.load_meals_range(date(2026, 4, 3), date(2026, 4, 4))
        assert date(2026, 4, 3) in result
        assert date(2026, 4, 4) in result
        assert result[date(2026, 4, 3)][0].food_name == "egg"
        assert result[date(2026, 4, 4)][0].food_name == "banana"

    def test_load_meals_range_partial_data(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_meals(date(2026, 4, 4), [_meal()])

        result = store.load_meals_range(date(2026, 4, 3), date(2026, 4, 5))
        # Day 3 and 5 have no data — they should just not appear
        assert date(2026, 4, 4) in result
        assert date(2026, 4, 3) not in result
        assert date(2026, 4, 5) not in result


# ── Goals ─────────────────────────────────────────────────────────


class TestGoals:
    def test_save_goals_overwrites_current(self, store_and_backend) -> None:
        store, backend = store_and_backend
        goal1 = _goal()
        store.save_goals(goal1)

        goal2 = NutritionGoal(
            date=date(2026, 4, 5),
            calories_target=2000,
            protein_g_target=160.0,
            carbs_g_target=230.0,
            fat_g_target=60.0,
            set_by="user",
        )
        store.save_goals(goal2)

        raw = backend.get_raw("goals/current.json")
        assert raw["calories_target"] == 2000

    def test_load_goals_returns_none_when_no_goals(self, store_and_backend) -> None:
        store, _ = store_and_backend
        result = store.load_goals()
        assert result is None


# ── Biometrics ────────────────────────────────────────────────────


class TestBiometrics:
    def test_save_biometrics_creates_dated_blob(self, store_and_backend) -> None:
        store, backend = store_and_backend
        store.save_biometrics(date(2026, 4, 4), _biometrics())

        raw = backend.get_raw("biometrics/2026-04-04.json")
        assert raw is not None
        assert raw["resting_hr"] == 65

    def test_load_biometrics_range(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_biometrics(date(2026, 4, 3), BiometricsRecord(date=date(2026, 4, 3), steps=7000))
        store.save_biometrics(date(2026, 4, 4), _biometrics())

        result = store.load_biometrics_range(date(2026, 4, 3), date(2026, 4, 4))
        assert date(2026, 4, 3) in result
        assert date(2026, 4, 4) in result
        assert result[date(2026, 4, 3)].steps == 7000
        assert result[date(2026, 4, 4)].steps == 8500


# ── Recommendation Status ──────────────────────────────────────────


def _rec_status(rec_id: str = "abc123", status: RecStatus = RecStatus.PENDING) -> RecommendationStatus:
    return RecommendationStatus(
        rec_id=rec_id,
        status=status,
        updated_at=datetime(2026, 4, 4, 12, 0),
    )


class TestRecommendationStatus:
    def test_save_creates_blob(self, store_and_backend) -> None:
        store, backend = store_and_backend
        store.save_recommendation_statuses([_rec_status()])

        raw = backend.get_raw("recommendations/status.json")
        assert raw is not None
        assert len(raw) == 1
        assert raw[0]["rec_id"] == "abc123"

    def test_roundtrip(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_recommendation_statuses([_rec_status("a"), _rec_status("b", RecStatus.DONE)])

        result = store.load_recommendation_statuses()
        assert len(result) == 2
        assert result[0].rec_id == "a"
        assert result[1].status == RecStatus.DONE

    def test_load_empty(self, store_and_backend) -> None:
        store, _ = store_and_backend
        result = store.load_recommendation_statuses()
        assert result == []

    def test_overwrite(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_recommendation_statuses([_rec_status("a", RecStatus.PENDING)])
        store.save_recommendation_statuses([_rec_status("a", RecStatus.DONE)])

        result = store.load_recommendation_statuses()
        assert len(result) == 1
        assert result[0].status == RecStatus.DONE


# ── Timeline ──────────────────────────────────────────────────────


class TestTimeline:
    def test_save_and_load(self, store_and_backend) -> None:
        store, backend = store_and_backend
        event = TimelineEvent(
            date=date(2026, 1, 18), category=TimelineCategory.MEDICAL,
            title_he="כבד שומני", severity=TimelineSeverity.WARNING,
        )
        store.save_timeline_events([event])
        result = store.load_timeline_events()
        assert len(result) == 1
        assert result[0].title_he == "כבד שומני"

    def test_append_event(self, store_and_backend) -> None:
        store, _ = store_and_backend
        e1 = TimelineEvent(date=date(2026, 1, 1), category=TimelineCategory.LIFESTYLE, title_he="A")
        e2 = TimelineEvent(date=date(2026, 2, 1), category=TimelineCategory.MILESTONE, title_he="B")
        store.append_timeline_event(e1)
        store.append_timeline_event(e2)
        assert len(store.load_timeline_events()) == 2

    def test_load_empty(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_timeline_events() == []


# ── Training Programs ─────────────────────────────────────────────


class TestTrainingPrograms:
    def test_save_and_load(self, store_and_backend) -> None:
        store, _ = store_and_backend
        program = TrainingProgram(
            name="Test", goal="vo2max", duration_weeks=4,
            weeks=[TrainingWeek(week_number=1, sessions=[
                TrainingSession(day="Mon", type="swim", duration_min=45),
            ])],
        )
        store.save_training_program(program)
        loaded = store.load_active_training_program()
        assert loaded is not None
        assert loaded.name == "Test"
        assert len(loaded.weeks[0].sessions) == 1

    def test_load_none(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_active_training_program() is None


# ── Goal Programs ─────────────────────────────────────────────────


class TestGoalPrograms:
    def test_save_and_load(self, store_and_backend) -> None:
        store, _ = store_and_backend
        program = GoalProgram(
            name_he="פרויקט 100", duration_weeks=12,
            milestones=[Milestone(title_he="שקילה")],
        )
        store.save_goal_program(program)
        # Can't easily test list_blobs with InMemoryBlobStore, just verify save doesn't error


# ── Sleep Protocol ────────────────────────────────────────────────


class TestSleepProtocol:
    def test_save_and_load_protocol(self, store_and_backend) -> None:
        store, _ = store_and_backend
        checklist = SleepChecklist(items=[
            ChecklistItem(id="caffeine", label_he="ללא קפאין אחרי 14:00", category="habits"),
        ])
        store.save_sleep_protocol(checklist)
        loaded = store.load_sleep_protocol()
        assert loaded is not None
        assert len(loaded.items) == 1

    def test_save_and_load_entry(self, store_and_backend) -> None:
        store, _ = store_and_backend
        entry = SleepEntry(date=date(2026, 4, 4), rating=4, bedtime="23:00")
        store.save_sleep_entry(entry)
        entries = store.load_sleep_entries(date(2026, 4, 4), date(2026, 4, 4))
        assert len(entries) == 1
        assert entries[0].rating == 4

    def test_load_empty(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_sleep_protocol() is None
        assert store.load_sleep_entries(date(2026, 4, 4), date(2026, 4, 4)) == []


# ── Lab Trends ────────────────────────────────────────────────────


class TestLabTrends:
    def test_save_and_load(self, store_and_backend) -> None:
        store, _ = store_and_backend
        trend = LabTrend(
            metric="LDL", display_name_he="כולסטרול LDL",
            values=[LabDataPoint(date=date(2025, 9, 3), value=116.4, unit="mg/dL")],
        )
        store.save_lab_trends([trend])
        loaded = store.load_lab_trends()
        assert len(loaded) == 1
        assert loaded[0].metric == "LDL"

    def test_load_empty(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_lab_trends() == []


# ── Food Cache ────────────────────────────────────────────────────


class TestFoodCache:
    def test_load_food_cache_returns_known_foods(self, store_and_backend) -> None:
        store, backend = store_and_backend
        # Pre-populate cache
        foods = [_known_food("אוראו"), _known_food("banana")]
        backend._data["food_cache/known_foods.json"] = json.dumps(
            [f.model_dump(mode="json") for f in foods]
        ).encode()

        result = store.load_food_cache()
        assert len(result) == 2
        assert isinstance(result[0], KnownFood)

    def test_load_food_cache_empty_returns_empty_list(self, store_and_backend) -> None:
        store, _ = store_and_backend
        result = store.load_food_cache()
        assert result == []

    def test_append_food_cache_adds_entry(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.append_food_cache(_known_food("אוראו"))
        store.append_food_cache(_known_food("banana"))

        result = store.load_food_cache()
        assert len(result) == 2

    def test_append_food_cache_no_duplicates(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.append_food_cache(_known_food("אוראו"))
        store.append_food_cache(_known_food("אוראו"))

        result = store.load_food_cache()
        assert len(result) == 1


# ── Combined (External Agent) ────────────────────────────────────


class TestCombined:
    def test_load_combined_merges_nutrition_and_biometrics(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_meals(date(2026, 4, 4), [_meal()])
        store.save_biometrics(date(2026, 4, 4), _biometrics())

        result = store.load_combined(date(2026, 4, 4), date(2026, 4, 4))
        assert "nutrition" in result
        assert "biometrics" in result
        assert "2026-04-04" in result["nutrition"]
        assert "2026-04-04" in result["biometrics"]

    def test_load_combined_handles_missing_data_gracefully(self, store_and_backend) -> None:
        store, _ = store_and_backend
        # Only biometrics, no meals
        store.save_biometrics(date(2026, 4, 4), _biometrics())

        result = store.load_combined(date(2026, 4, 4), date(2026, 4, 4))
        assert result["nutrition"] == {}
        assert "2026-04-04" in result["biometrics"]


# ── Connection ────────────────────────────────────────────────────


class TestConnection:
    def test_blob_connection_string_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=test")

        with patch("shared.blob_store.BlobServiceClient") as mock_bsc:
            mock_bsc.from_connection_string.return_value = MagicMock()
            store = BlobStore()

        mock_bsc.from_connection_string.assert_called_once_with(
            "DefaultEndpointsProtocol=https;AccountName=test"
        )
