"""Blob store — SSOT for Azure Blob Storage operations.

Stores nutrition data, goals, biometrics, and food cache as
date-stamped JSON blobs in the ``vitalis-data`` container.
Mirrors the local ``data_store.py`` pattern.

Blob layout::

    vitalis-data/
    ├── meals/{YYYY-MM-DD}.json           # list[MealEntry]
    ├── goals/current.json                # NutritionGoal
    ├── biometrics/{YYYY-MM-DD}.json      # BiometricsRecord
    └── food_cache/known_foods.json       # list[KnownFood]
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
    FavoriteMeal,
    KnownFood,
    MealEntry,
    MealTemplate,
    NutritionGoal,
    PlanDay,
    RecommendationStatus,
)

logger = logging.getLogger(__name__)


class BlobStore:
    """Azure Blob Storage operations for the Vitalis API."""

    def __init__(
        self,
        connection_string: str | None = None,
        container_name: str = "vitalis-data",
    ) -> None:
        conn = connection_string or os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        client = BlobServiceClient.from_connection_string(conn)
        self._container = client.get_container_client(container_name)
        self._container_name = container_name

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
        for blob in self._container.list_blobs(name_starts_with="meals/"):
            raw = self._download(blob.name)
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
        """Load the food cache. Returns [] if empty/missing."""
        raw = self._download("food_cache/known_foods.json")
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
        self._upload("food_cache/known_foods.json", data)
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
        names = [
            blob.name
            for blob in self._container.list_blobs(name_starts_with="summaries/")
            if blob.name != "summaries/latest.json" and blob.name.endswith(".json")
        ]
        names.sort(reverse=True)

        summaries: list[AnalysisSummary] = []
        for name in names[:limit]:
            raw = self._download(name)
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

    # ── Private helpers ────────────────────────────────────────────

    def _upload(self, blob_name: str, data: str) -> None:
        """Upload string data to a blob (overwrite if exists)."""
        blob_client = self._container.get_blob_client(blob_name)
        blob_client.upload_blob(data, overwrite=True)

    def _download(self, blob_name: str) -> str | None:
        """Download blob as string. Returns None if blob doesn't exist."""
        try:
            blob_client = self._container.get_blob_client(blob_name)
            return blob_client.download_blob().readall().decode()
        except ResourceNotFoundError:
            return None
