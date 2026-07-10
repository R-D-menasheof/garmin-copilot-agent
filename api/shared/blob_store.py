"""Blob store — SSOT for Azure Blob Storage operations.

Stores nutrition data, goals, biometrics, and food cache as
date-stamped JSON blobs in the ``vitalis-data`` container.
Mirrors the local ``data_store.py`` pattern.

All per-user data is scoped under ``users/{user_id}/``; the food cache is
global (shared across users to maximise cache hits and minimise LLM cost).

Blob layout::

    vitalis-data/
    ├── users/{user_id}/meals/{YYYY-MM-DD}.json       # list[MealEntry]
    ├── users/{user_id}/goals/current.json            # NutritionGoal
    ├── users/{user_id}/biometrics/{YYYY-MM-DD}.json  # BiometricsRecord
    ├── users/{user_id}/profile.json                  # Profile
    └── food_cache/known_foods.json                   # list[KnownFood] (global)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from vitalis.models import (
    AnalysisSummary,
    BiometricsRecord,
    DayTrackingOverride,
    FavoriteMeal,
    GoalProgram,
    KnownFood,
    LabTrend,
    MealEntry,
    MealTemplate,
    MedicalUpload,
    NutritionGoal,
    PlanDay,
    Profile,
    PushToken,
    RecommendationStatus,
    SleepChecklist,
    SleepEntry,
    TimelineEvent,
    TrainingProgram,
)

logger = logging.getLogger(__name__)


class BlobStore:
    """Azure Blob Storage operations for the Vitalis API."""

    def __init__(
        self,
        connection_string: str | None = None,
        container_name: str = "vitalis-data",
        user_id: str = "roei",
    ) -> None:
        conn = connection_string or os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        client = BlobServiceClient.from_connection_string(conn)
        self._container = client.get_container_client(container_name)
        self._container_name = container_name
        # All per-user data lives under ``users/{user_id}/``. Derived
        # server-side from the authenticated caller — never client input.
        self._user_id = user_id

    # ── Meals ──────────────────────────────────────────────────────

    def save_meals(self, day: date, meals: list[MealEntry]) -> None:
        """Save meals for a single day."""
        blob_name = f"meals/{day.isoformat()}.json"
        data = json.dumps(
            [m.model_dump(mode="json") for m in meals],
            ensure_ascii=False,
        )
        self._upload(blob_name, data)
        logger.info("Saved %d meals for %s", len(meals), day)

    def load_meals(self, day: date) -> list[MealEntry]:
        """Load meals for a single day. Returns [] if none exist."""
        blob_name = f"meals/{day.isoformat()}.json"
        raw = self._download(blob_name)
        if raw is None:
            return []
        return [MealEntry.model_validate(item) for item in json.loads(raw)]

    def load_meals_range(
        self, start: date, end: date,
    ) -> dict[date, list[MealEntry]]:
        """Load meals for a date range (inclusive). Skips days with no data."""
        result: dict[date, list[MealEntry]] = {}
        current = start
        while current <= end:
            meals = self.load_meals(current)
            if meals:
                result[current] = meals
            current += timedelta(days=1)
        return result

    def load_recent_meals(self, limit: int = 10) -> list[MealEntry]:
        """Return the latest unique meals derived from persisted meal history."""
        all_meals: list[MealEntry] = []
        for blob in self._container.list_blobs(name_starts_with=self._key("meals/")):
            raw = self._download_raw(blob.name)
            if raw is None:
                continue
            all_meals.extend(MealEntry.model_validate(item) for item in json.loads(raw))

        all_meals.sort(key=lambda meal: meal.timestamp, reverse=True)

        recent: list[MealEntry] = []
        seen_foods: set[str] = set()
        for meal in all_meals:
            key = meal.food_name.strip().lower()
            if key in seen_foods:
                continue
            seen_foods.add(key)
            recent.append(meal)
            if len(recent) >= limit:
                break
        return recent

    # ── Goals ──────────────────────────────────────────────────────

    def save_goals(self, goal: NutritionGoal) -> None:
        """Save current nutrition goals (overwrites previous)."""
        blob_name = "goals/current.json"
        data = goal.model_dump_json()
        self._upload(blob_name, data)
        logger.info("Saved goals: %d kcal target", goal.calories_target)

    def load_goals(self) -> NutritionGoal | None:
        """Load current goals. Returns None if no goals set."""
        raw = self._download("goals/current.json")
        if raw is None:
            return None
        return NutritionGoal.model_validate_json(raw)

    # ── Biometrics ─────────────────────────────────────────────────

    def save_biometrics(self, day: date, record: BiometricsRecord) -> None:
        """Save biometrics for a single day."""
        blob_name = f"biometrics/{day.isoformat()}.json"
        data = record.model_dump_json()
        self._upload(blob_name, data)
        logger.info("Saved biometrics for %s", day)

    def load_biometrics_range(
        self, start: date, end: date,
    ) -> dict[date, BiometricsRecord]:
        """Load biometrics for a date range (inclusive)."""
        result: dict[date, BiometricsRecord] = {}
        current = start
        while current <= end:
            blob_name = f"biometrics/{current.isoformat()}.json"
            raw = self._download(blob_name)
            if raw is not None:
                result[current] = BiometricsRecord.model_validate_json(raw)
            current += timedelta(days=1)
        return result

    # ── Food Cache ─────────────────────────────────────────────────

    def load_food_cache(self) -> list[KnownFood]:
        """Load the shared, global food cache. Returns [] if empty/missing."""
        raw = self._download_raw("food_cache/known_foods.json")
        if raw is None:
            return []
        return [KnownFood.model_validate(item) for item in json.loads(raw)]

    def append_food_cache(self, food: KnownFood) -> None:
        """Add a food to the cache. Skips if food_name already exists."""
        cache = self.load_food_cache()
        existing_names = {f.food_name.lower() for f in cache}
        if food.food_name.lower() in existing_names:
            logger.debug("Food '%s' already in cache, skipping", food.food_name)
            return
        cache.append(food)
        data = json.dumps(
            [f.model_dump(mode="json") for f in cache],
            ensure_ascii=False,
        )
        self._upload_raw("food_cache/known_foods.json", data)
        logger.info("Added '%s' to food cache (%d total)", food.food_name, len(cache))

    # ── Favorites ──────────────────────────────────────────────────

    def load_favorites(self) -> list[FavoriteMeal]:
        """Load saved favorite meals."""
        raw = self._download("favorites/items.json")
        if raw is None:
            return []
        return [FavoriteMeal.model_validate(item) for item in json.loads(raw)]

    def save_favorite(self, favorite: FavoriteMeal) -> None:
        """Save or replace a favorite meal entry."""
        favorites = [item for item in self.load_favorites() if item.id != favorite.id]
        favorites.append(favorite)
        data = json.dumps([item.model_dump(mode="json") for item in favorites], ensure_ascii=False)
        self._upload("favorites/items.json", data)

    def delete_favorite(self, favorite_id: str) -> None:
        """Delete a favorite meal entry if it exists."""
        favorites = [item for item in self.load_favorites() if item.id != favorite_id]
        data = json.dumps([item.model_dump(mode="json") for item in favorites], ensure_ascii=False)
        self._upload("favorites/items.json", data)

    # ── Templates ──────────────────────────────────────────────────

    def load_templates(self) -> list[MealTemplate]:
        """Load saved meal templates."""
        raw = self._download("templates/items.json")
        if raw is None:
            return []
        return [MealTemplate.model_validate(item) for item in json.loads(raw)]

    def save_template(self, template: MealTemplate) -> None:
        """Save or replace a meal template."""
        templates = [item for item in self.load_templates() if item.id != template.id]
        templates.append(template)
        data = json.dumps([item.model_dump(mode="json") for item in templates], ensure_ascii=False)
        self._upload("templates/items.json", data)

    def delete_template(self, template_id: str) -> None:
        """Delete a meal template if it exists."""
        templates = [item for item in self.load_templates() if item.id != template_id]
        data = json.dumps([item.model_dump(mode="json") for item in templates], ensure_ascii=False)
        self._upload("templates/items.json", data)

    # ── Plan Days ──────────────────────────────────────────────────

    def save_plan_day(self, plan_day: PlanDay) -> None:
        """Save a single day's meal plan."""
        blob_name = f"plans/{plan_day.date.isoformat()}.json"
        self._upload(blob_name, plan_day.model_dump_json())

    def load_plan_day(self, day: date) -> PlanDay | None:
        """Load a single day's meal plan."""
        raw = self._download(f"plans/{day.isoformat()}.json")
        if raw is None:
            return None
        return PlanDay.model_validate_json(raw)

    # ── Published Summaries ───────────────────────────────────────

    def save_summary(self, summary: AnalysisSummary) -> None:
        """Persist a published analysis summary for mobile consumption."""
        data = summary.model_dump_json()
        self._upload(f"summaries/{summary.date.isoformat()}.json", data)
        self._upload("summaries/latest.json", data)

    def load_latest_summary(self) -> AnalysisSummary | None:
        """Load the latest published analysis summary."""
        raw = self._download("summaries/latest.json")
        if raw is None:
            return None
        return AnalysisSummary.model_validate_json(raw)

    def load_summary_history(self, limit: int = 4) -> list[AnalysisSummary]:
        """Load published summary history ordered newest first."""
        latest_name = self._key("summaries/latest.json")
        names = [
            blob.name
            for blob in self._container.list_blobs(name_starts_with=self._key("summaries/"))
            if blob.name != latest_name and blob.name.endswith(".json")
        ]
        names.sort(reverse=True)

        summaries: list[AnalysisSummary] = []
        for name in names[:limit]:
            raw = self._download_raw(name)
            if raw is None:
                continue
            summaries.append(AnalysisSummary.model_validate_json(raw))
        return summaries

    # ── Recommendation Status ───────────────────────────────────────

    def save_recommendation_statuses(self, statuses: list[RecommendationStatus]) -> None:
        """Persist recommendation adoption statuses."""
        data = json.dumps(
            [s.model_dump(mode="json") for s in statuses],
            ensure_ascii=False,
        )
        self._upload("recommendations/status.json", data)

    def load_recommendation_statuses(self) -> list[RecommendationStatus]:
        """Load recommendation adoption statuses."""
        raw = self._download("recommendations/status.json")
        if raw is None:
            return []
        items = json.loads(raw)
        return [RecommendationStatus.model_validate(item) for item in items]

    # ── Combined (External Agent) ──────────────────────────────────

    # ── Timeline ────────────────────────────────────────────────

    def save_timeline_events(self, events: list[TimelineEvent]) -> None:
        """Persist timeline events."""
        data = json.dumps(
            [e.model_dump(mode="json") for e in events], ensure_ascii=False,
        )
        self._upload("timeline/events.json", data)

    def load_timeline_events(self) -> list[TimelineEvent]:
        """Load all timeline events."""
        raw = self._download("timeline/events.json")
        if raw is None:
            return []
        return [TimelineEvent.model_validate(item) for item in json.loads(raw)]

    def append_timeline_event(self, event: TimelineEvent) -> None:
        """Append a single event to the timeline."""
        events = self.load_timeline_events()
        events.append(event)
        self.save_timeline_events(events)

    # ── Training Programs ───────────────────────────────────────

    def save_training_program(self, program: TrainingProgram) -> None:
        """Persist the active training program."""
        self._upload("training/active.json", program.model_dump_json())

    def load_active_training_program(self) -> TrainingProgram | None:
        """Load the active training program."""
        raw = self._download("training/active.json")
        if raw is None:
            return None
        return TrainingProgram.model_validate_json(raw)

    # ── Goal Programs ───────────────────────────────────────────

    def save_goal_program(self, program: GoalProgram) -> None:
        """Persist a goal program."""
        self._upload(f"goals/programs/{program.id}.json", program.model_dump_json())

    def load_goal_programs(self) -> list[GoalProgram]:
        """Load all goal programs."""
        programs: list[GoalProgram] = []
        try:
            blobs = self._container.list_blobs(name_starts_with=self._key("goals/programs/"))
            for blob in blobs:
                raw = self._download_raw(blob.name)
                if raw:
                    programs.append(GoalProgram.model_validate_json(raw))
        except Exception:
            pass
        return programs

    # ── Sleep Protocol ──────────────────────────────────────────

    def save_sleep_protocol(self, checklist: SleepChecklist) -> None:
        """Persist the sleep checklist configuration."""
        self._upload("sleep/protocol.json", checklist.model_dump_json())

    def load_sleep_protocol(self) -> SleepChecklist | None:
        """Load the sleep checklist."""
        raw = self._download("sleep/protocol.json")
        if raw is None:
            return None
        return SleepChecklist.model_validate_json(raw)

    def save_sleep_entry(self, entry: SleepEntry) -> None:
        """Persist a single night's sleep log."""
        self._upload(
            f"sleep/entries/{entry.date.isoformat()}.json",
            entry.model_dump_json(),
        )

    def load_sleep_entries(self, start: date, end: date) -> list[SleepEntry]:
        """Load sleep entries for a date range."""
        entries: list[SleepEntry] = []
        current = start
        while current <= end:
            raw = self._download(f"sleep/entries/{current.isoformat()}.json")
            if raw:
                entries.append(SleepEntry.model_validate_json(raw))
            current += timedelta(days=1)
        return entries

    # ── Lab Trends ──────────────────────────────────────────────

    def save_lab_trends(self, trends: list[LabTrend]) -> None:
        """Persist parsed lab trends."""
        data = json.dumps(
            [t.model_dump(mode="json") for t in trends], ensure_ascii=False,
        )
        self._upload("medical/lab_trends.json", data)

    def load_lab_trends(self) -> list[LabTrend]:
        """Load parsed lab trends."""
        raw = self._download("medical/lab_trends.json")
        if raw is None:
            return []
        return [LabTrend.model_validate(item) for item in json.loads(raw)]

    # ── Profile ─────────────────────────────────

    def save_profile(self, profile: Profile) -> None:
        """Persist the user's profile."""
        self._upload("profile.json", profile.model_dump_json())

    def load_profile(self) -> Profile | None:
        """Load the user's profile. Returns None if not set."""
        raw = self._download("profile.json")
        if raw is None:
            return None
        return Profile.model_validate_json(raw)

    # ── Day Tracking Overrides ───────────────────────────────────

    def save_day_overrides(self, overrides: list[DayTrackingOverride]) -> None:
        """Persist day tracking overrides (full list, overwrites blob)."""
        data = json.dumps(
            [o.model_dump(mode="json") for o in overrides], ensure_ascii=False,
        )
        self._upload("nutrition/day_overrides.json", data)

    def load_day_overrides(self) -> list[DayTrackingOverride]:
        """Load day tracking overrides."""
        raw = self._download("nutrition/day_overrides.json")
        if raw is None:
            return []
        return [DayTrackingOverride.model_validate(item) for item in json.loads(raw)]

    # ── Combined (External Agent) ──────────────────────────────────

    def load_combined(self, start: date, end: date) -> dict:
        """Load merged nutrition + biometrics for the External Agent.

        Returns:
            {"nutrition": {date_str: [meal_dicts]}, "biometrics": {date_str: bio_dict}}
        """
        meals = self.load_meals_range(start, end)
        biometrics = self.load_biometrics_range(start, end)

        return {
            "nutrition": {
                d.isoformat(): [m.model_dump(mode="json") for m in ms]
                for d, ms in meals.items()
            },
            "biometrics": {
                d.isoformat(): b.model_dump(mode="json")
                for d, b in biometrics.items()
            },
        }

    # ── Push tokens (notifications) ────────────────────────────────

    def load_push_tokens(self) -> list[PushToken]:
        """Load this user's registered device push tokens. [] if none."""
        raw = self._download("push/tokens.json")
        if raw is None:
            return []
        return [PushToken.model_validate(item) for item in json.loads(raw)]

    def save_push_token(self, token: PushToken) -> None:
        """Register or refresh a device push token (dedup by token string)."""
        tokens = [t for t in self.load_push_tokens() if t.token != token.token]
        tokens.append(token)
        data = json.dumps(
            [t.model_dump(mode="json") for t in tokens],
            ensure_ascii=False,
        )
        self._upload("push/tokens.json", data)
        logger.info("Saved push token (%d total for user)", len(tokens))

    def delete_push_token(self, token_str: str) -> None:
        """Unregister a device push token by its token string."""
        tokens = [t for t in self.load_push_tokens() if t.token != token_str]
        data = json.dumps(
            [t.model_dump(mode="json") for t in tokens],
            ensure_ascii=False,
        )
        self._upload("push/tokens.json", data)

    # ── Medical uploads (in-app documents) ──────────────────────

    def load_medical_uploads(self) -> list[MedicalUpload]:
        """List this user's uploaded medical documents (metadata). [] if none."""
        raw = self._download("medical/uploads/index.json")
        if raw is None:
            return []
        return [MedicalUpload.model_validate(item) for item in json.loads(raw)]

    def save_medical_upload(self, upload: MedicalUpload, content: bytes) -> None:
        """Store a raw medical document + its index entry (dedup by id)."""
        self._upload_bytes(
            f"medical/uploads/{upload.id}_{upload.filename}", content
        )
        uploads = [u for u in self.load_medical_uploads() if u.id != upload.id]
        uploads.append(upload)
        data = json.dumps(
            [u.model_dump(mode="json") for u in uploads],
            ensure_ascii=False,
        )
        self._upload("medical/uploads/index.json", data)
        logger.info(
            "Saved medical upload %s (%d bytes)", upload.filename, upload.size_bytes
        )

    def load_medical_upload_content(self, upload_id: str) -> bytes | None:
        """Download the raw bytes of a stored medical document by id."""
        for upload in self.load_medical_uploads():
            if upload.id == upload_id:
                return self._download_bytes(
                    f"medical/uploads/{upload.id}_{upload.filename}"
                )
        return None

    def mark_medical_upload_extracted(self, upload_id: str) -> None:
        """Mark an upload as extracted (owner op after local extraction, 6.3)."""
        uploads = self.load_medical_uploads()
        for upload in uploads:
            if upload.id == upload_id:
                upload.extracted = True
        data = json.dumps(
            [u.model_dump(mode="json") for u in uploads],
            ensure_ascii=False,
        )
        self._upload("medical/uploads/index.json", data)

    # ── Private helpers ────────────────────────────────────────────

    def _key(self, blob_name: str) -> str:
        """Prefix a blob name with the current user's scope."""
        return f"users/{self._user_id}/{blob_name}"

    def _upload(self, blob_name: str, data: str) -> None:
        """Upload string data to a user-scoped blob (overwrite if exists)."""
        self._upload_raw(self._key(blob_name), data)

    def _download(self, blob_name: str) -> str | None:
        """Download a user-scoped blob as string. None if it doesn't exist."""
        return self._download_raw(self._key(blob_name))

    def _upload_raw(self, blob_name: str, data: str) -> None:
        """Upload to an exact blob path (no user scoping).

        Used for global/shared blobs (food cache) and for full paths that
        already came back prefixed from ``list_blobs``.
        """
        blob_client = self._container.get_blob_client(blob_name)
        blob_client.upload_blob(data, overwrite=True)

    def _download_raw(self, blob_name: str) -> str | None:
        """Download an exact blob path (no user scoping). None if missing."""
        try:
            blob_client = self._container.get_blob_client(blob_name)
            return blob_client.download_blob().readall().decode()
        except ResourceNotFoundError:
            return None

    def _upload_bytes(self, blob_name: str, data: bytes) -> None:
        """Upload raw bytes to a user-scoped blob (overwrite if exists)."""
        blob_client = self._container.get_blob_client(self._key(blob_name))
        blob_client.upload_blob(data, overwrite=True)

    def _download_bytes(self, blob_name: str) -> bytes | None:
        """Download a user-scoped blob as raw bytes. None if missing."""
        try:
            blob_client = self._container.get_blob_client(self._key(blob_name))
            return blob_client.download_blob().readall()
        except ResourceNotFoundError:
            return None
