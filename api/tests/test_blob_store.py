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
    DayTrackingOverride,
    GoalProgram,
    KnownFood,
    LabDataPoint,
    LabStatus,
    LabTrend,
    MealEntry,
    MedicalUpload,
    Milestone,
    NutritionGoal,
    NutritionSource,
    Profile,
    PushToken,
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
        self._user_id = "roei"

    def build(self, user_id: str = "roei") -> BlobStore:
        """Create a BlobStore wired to in-memory storage, scoped to user_id."""
        self._user_id = user_id
        store = BlobStore.__new__(BlobStore)
        store._container_name = "vitalis-data"
        store._user_id = user_id

        # Mock container client
        container = MagicMock()
        container.get_blob_client = MagicMock(side_effect=self._get_blob_client)
        container.list_blobs = MagicMock(side_effect=self._list_blobs)
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

    def _list_blobs(self, name_starts_with: str = "") -> list:
        items = []
        for key in list(self._data.keys()):
            if key.startswith(name_starts_with):
                item = MagicMock()
                item.name = key
                items.append(item)
        return items

    def get_raw(self, blob: str, *, user: str | None = None) -> dict | list | None:
        """Read a user-scoped blob (auto-prefixed with users/{user_id}/)."""
        key = f"users/{user or self._user_id}/{blob}"
        if key not in self._data:
            return None
        return json.loads(self._data[key])

    def get_raw_global(self, blob: str) -> dict | list | None:
        """Read a global (non-user-scoped) blob such as the food cache."""
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


# ── Day Tracking Overrides ─────────────────────────────────────────


class TestDayTrackingOverrides:
    def test_save_day_overrides_creates_blob(self, store_and_backend) -> None:
        store, backend = store_and_backend
        override = DayTrackingOverride(date=date(2026, 7, 1), tracked=False)
        store.save_day_overrides([override])

        raw = backend.get_raw("nutrition/day_overrides.json")
        assert raw is not None
        assert len(raw) == 1
        assert raw[0]["date"] == "2026-07-01"
        assert raw[0]["tracked"] is False

    def test_load_day_overrides_roundtrip(self, store_and_backend) -> None:
        store, _ = store_and_backend
        override = DayTrackingOverride(
            date=date(2026, 7, 1), tracked=False, note="נסעתי"
        )
        store.save_day_overrides([override])

        loaded = store.load_day_overrides()
        assert len(loaded) == 1
        assert loaded[0].date == date(2026, 7, 1)
        assert loaded[0].tracked is False
        assert loaded[0].note == "נסעתי"

    def test_load_day_overrides_empty_returns_empty_list(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_day_overrides() == []

    def test_save_day_overrides_overwrite_existing_date(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_day_overrides([DayTrackingOverride(date=date(2026, 7, 1), tracked=False)])
        store.save_day_overrides([
            DayTrackingOverride(date=date(2026, 7, 1), tracked=True),
            DayTrackingOverride(date=date(2026, 7, 2), tracked=False),
        ])

        loaded = store.load_day_overrides()
        assert len(loaded) == 2
        by_date = {o.date: o.tracked for o in loaded}
        assert by_date[date(2026, 7, 1)] is True
        assert by_date[date(2026, 7, 2)] is False


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


# ── User Scoping (multi-tenant isolation) ─────────────────────────


class TestUserScoping:
    def test_meal_blob_path_is_user_scoped(self) -> None:
        backend = InMemoryBlobStore()
        store = backend.build(user_id="alice")
        store.save_meals(date(2026, 4, 4), [_meal("apple")])

        assert "users/alice/meals/2026-04-04.json" in backend._data
        assert "meals/2026-04-04.json" not in backend._data

    def test_meals_isolated_between_users(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.save_meals(date(2026, 4, 4), [_meal("apple")])

        assert store_b.load_meals(date(2026, 4, 4)) == []
        assert len(store_a.load_meals(date(2026, 4, 4))) == 1

    def test_biometrics_isolated_between_users(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.save_biometrics(date(2026, 4, 4), _biometrics())

        assert store_b.load_biometrics_range(date(2026, 4, 4), date(2026, 4, 4)) == {}
        got_a = store_a.load_biometrics_range(date(2026, 4, 4), date(2026, 4, 4))
        assert date(2026, 4, 4) in got_a

    def test_goals_isolated_between_users(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.save_goals(_goal())

        assert store_b.load_goals() is None
        assert store_a.load_goals() is not None

    def test_food_cache_is_shared_across_users(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.append_food_cache(_known_food("cottage"))

        names_b = [f.food_name for f in store_b.load_food_cache()]
        assert "cottage" in names_b
        # stored at a global (non-user-scoped) path
        assert backend.get_raw_global("food_cache/known_foods.json") is not None
        assert "users/alice/food_cache/known_foods.json" not in backend._data

    def test_recent_meals_respect_user_scope(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.save_meals(date(2026, 4, 4), [_meal("apple")])
        store_b.save_meals(date(2026, 4, 5), [_meal("banana")])

        a_recents = [m.food_name for m in store_a.load_recent_meals()]
        assert a_recents == ["apple"]

    def test_goal_programs_respect_user_scope(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.save_goal_program(GoalProgram(id="p-alice", name_he="A", duration_weeks=4))
        store_b.save_goal_program(GoalProgram(id="p-bob", name_he="B", duration_weeks=4))

        a_ids = [p.id for p in store_a.load_goal_programs()]
        assert a_ids == ["p-alice"]

    def test_default_user_is_owner_for_backcompat(self) -> None:
        backend = InMemoryBlobStore()
        store = backend.build()  # default user
        store.save_meals(date(2026, 4, 4), [_meal("apple")])
        assert "users/roei/meals/2026-04-04.json" in backend._data


# ── Profile ───────────────────────────────────────────────────────


class TestProfile:
    def test_save_and_load_profile(self, store_and_backend) -> None:
        store, _ = store_and_backend
        p = Profile(
            display_name="Roei", date_of_birth=date(1989, 12, 1), onboarded=True,
        )
        store.save_profile(p)

        loaded = store.load_profile()
        assert loaded is not None
        assert loaded.display_name == "Roei"
        assert loaded.date_of_birth == date(1989, 12, 1)
        assert loaded.onboarded is True

    def test_load_profile_empty_returns_none(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_profile() is None

    def test_profile_blob_path_is_user_scoped(self, store_and_backend) -> None:
        store, backend = store_and_backend
        store.save_profile(Profile(display_name="Roei"))
        assert "users/roei/profile.json" in backend._data

    def test_profile_isolated_between_users(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.save_profile(Profile(display_name="Alice"))

        assert store_b.load_profile() is None
        assert store_a.load_profile().display_name == "Alice"


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


# ── Push tokens ─────────────────────────────────────


class TestPushTokens:
    def test_save_and_load_roundtrip(self, store_and_backend) -> None:
        store, backend = store_and_backend
        store.save_push_token(PushToken(token="fcm-1", platform="android"))

        tokens = store.load_push_tokens()
        assert len(tokens) == 1
        assert tokens[0].token == "fcm-1"
        assert "users/roei/push/tokens.json" in backend._data

    def test_load_empty_returns_list(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_push_tokens() == []

    def test_dedup_by_token_string(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_push_token(PushToken(token="fcm-1", device_label="old"))
        store.save_push_token(PushToken(token="fcm-1", device_label="new"))

        tokens = store.load_push_tokens()
        assert len(tokens) == 1
        assert tokens[0].device_label == "new"

    def test_delete_token(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_push_token(PushToken(token="fcm-1"))
        store.save_push_token(PushToken(token="fcm-2"))

        store.delete_push_token("fcm-1")

        assert [t.token for t in store.load_push_tokens()] == ["fcm-2"]

    def test_tokens_isolated_between_users(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.save_push_token(PushToken(token="fcm-alice"))

        assert store_b.load_push_tokens() == []
        assert [t.token for t in store_a.load_push_tokens()] == ["fcm-alice"]


# ── Medical uploads ─────────────────────────────────


def _upload(upload_id: str = "u1", filename: str = "labs.pdf") -> MedicalUpload:
    return MedicalUpload(
        id=upload_id, filename=filename,
        content_type="application/pdf", size_bytes=3,
    )


class TestMedicalUploads:
    def test_save_and_list_roundtrip(self, store_and_backend) -> None:
        store, backend = store_and_backend
        store.save_medical_upload(_upload(), b"abc")

        uploads = store.load_medical_uploads()
        assert len(uploads) == 1
        assert uploads[0].filename == "labs.pdf"
        assert "users/roei/medical/uploads/index.json" in backend._data
        assert "users/roei/medical/uploads/u1_labs.pdf" in backend._data

    def test_load_empty_returns_list(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_medical_uploads() == []

    def test_content_roundtrip(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_medical_upload(_upload(), b"%PDF-1.4 binary")
        assert store.load_medical_upload_content("u1") == b"%PDF-1.4 binary"

    def test_content_missing_returns_none(self, store_and_backend) -> None:
        store, _ = store_and_backend
        assert store.load_medical_upload_content("nope") is None

    def test_dedup_by_id(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_medical_upload(_upload(filename="a.pdf"), b"a")
        store.save_medical_upload(_upload(filename="b.pdf"), b"bb")

        uploads = store.load_medical_uploads()
        assert len(uploads) == 1
        assert uploads[0].filename == "b.pdf"

    def test_mark_extracted(self, store_and_backend) -> None:
        store, _ = store_and_backend
        store.save_medical_upload(_upload(), b"abc")
        store.mark_medical_upload_extracted("u1")
        assert store.load_medical_uploads()[0].extracted is True

    def test_isolation_between_users(self) -> None:
        backend = InMemoryBlobStore()
        store_a = backend.build(user_id="alice")
        store_b = backend.build(user_id="bob")

        store_a.save_medical_upload(_upload(), b"abc")

        assert store_b.load_medical_uploads() == []
        assert len(store_a.load_medical_uploads()) == 1
