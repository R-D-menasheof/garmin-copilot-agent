"""Pydantic models — data shapes used by the Vitalis pipeline."""

from __future__ import annotations

from datetime import date as DateValue, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python 3.10 compatibility shim.
    class StrEnum(str, Enum):
        pass


# ── Nutrition (Mobile App) ─────────────────────────────────────────


class NutritionSource(StrEnum):
    """Where a food entry's nutritional data came from."""

    HISTORY = "history"
    OPEN_FOOD_FACTS = "open_food_facts"
    USDA = "usda"
    LLM = "llm"
    MANUAL = "manual"


class MealEntry(BaseModel):
    """A single food item logged by the user."""

    food_name: str
    calories: int = Field(ge=0, description="Total kcal for the portion")
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    fiber_g: Optional[float] = Field(default=None, ge=0)
    portion_description: Optional[str] = None
    source: NutritionSource
    timestamp: datetime


class NutritionGoal(BaseModel):
    """Daily nutrition targets — set by the user or the External Agent."""

    date: DateValue
    calories_target: int = Field(ge=0)
    protein_g_target: float = Field(ge=0)
    carbs_g_target: float = Field(ge=0)
    fat_g_target: float = Field(ge=0)
    set_by: str = Field(pattern=r"^(user|agent)$", description="Who set this goal")
    created_at: datetime = Field(default_factory=datetime.now)


class DailyNutritionLog(BaseModel):
    """All meals for a single day, with optional goal compliance."""

    date: DateValue
    meals: list[MealEntry] = Field(default_factory=list)
    goal_compliance_pct: Optional[float] = None


class BiometricsRecord(BaseModel):
    """Daily biometrics from Health Connect / wearable.

    Captures ALL available data from Garmin via Health Connect.
    """

    date: DateValue

    # Heart
    resting_hr: Optional[int] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    hrv_ms: Optional[int] = None

    # Vitals
    spo2_pct: Optional[float] = None
    body_temp_c: Optional[float] = None
    respiratory_rate: Optional[float] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None

    # Activity
    steps: Optional[int] = None
    active_calories: Optional[int] = None
    total_calories: Optional[int] = None
    floors_climbed: Optional[int] = None
    distance_meters: Optional[float] = None
    exercise_minutes: Optional[int] = None
    intensity_minutes: Optional[int] = None

    # Sleep
    sleep_seconds: Optional[int] = None
    deep_sleep_seconds: Optional[int] = None
    light_sleep_seconds: Optional[int] = None
    rem_sleep_seconds: Optional[int] = None
    awake_sleep_seconds: Optional[int] = None
    sleep_score: Optional[int] = None

    # Body
    weight_kg: Optional[float] = None
    body_fat_pct: Optional[float] = None
    bmi: Optional[float] = None
    basal_metabolic_rate: Optional[float] = None

    # Hydration
    water_ml: Optional[float] = None


class KnownFood(BaseModel):
    """A cached food entry for the fuzzy-match lookup pipeline."""

    food_name: str
    calories_per_100g: int = Field(ge=0)
    protein_per_100g: float = Field(ge=0)
    carbs_per_100g: float = Field(ge=0)
    fat_per_100g: float = Field(ge=0)
    fiber_per_100g: Optional[float] = Field(default=None, ge=0)
    source: NutritionSource
    aliases: list[str] = Field(default_factory=list)


def _generate_id() -> str:
    """Generate a stable opaque identifier for saved objects."""
    return uuid4().hex


class FavoriteMeal(BaseModel):
    """A single saved meal snapshot for quick re-logging."""

    id: str = Field(default_factory=_generate_id)
    meal: MealEntry
    label: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class MealTemplate(BaseModel):
    """A reusable multi-item meal template used for quick add and planning."""

    id: str = Field(default_factory=_generate_id)
    name: str
    meals: list[MealEntry] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class PlanDay(BaseModel):
    """A lightweight daily meal plan backed by saved template ids."""

    date: DateValue
    template_ids: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ── Medical Records ────────────────────────────────────────────────


class MedicalCategory(StrEnum):
    """Categories of medical documents."""

    BLOOD_TEST = "blood_tests"
    DOCTOR_VISIT = "doctor_visits"
    IMAGING = "imaging"
    PRESCRIPTION = "prescriptions"
    VACCINATION = "vaccinations"


class ParsedLabValue(BaseModel):
    """A single parsed lab result value."""

    value: float
    unit: str
    reference: str = ""


class MedicalRecord(BaseModel):
    """Metadata and extracted content for a single medical document."""

    category: MedicalCategory
    date: DateValue
    title: str
    language: str = Field(default="auto", description="'he', 'en', or 'auto'")
    source_file: str = Field(..., description="Relative path to original file")
    extracted_text: str = ""
    parsed_values: dict[str, ParsedLabValue] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class MedicalIndex(BaseModel):
    """Master index of all imported medical records."""

    records: list[MedicalRecord] = Field(default_factory=list)
    last_updated: str = ""


# ── Health Analysis ────────────────────────────────────────────────


class HealthRecommendation(BaseModel):
    """A single actionable recommendation."""

    category: str = Field(..., description="e.g. 'sleep', 'activity', 'recovery'")
    title: str
    detail: str
    priority: int = Field(ge=1, le=5, description="1 = highest priority")


class AnalysisSummary(BaseModel):
    """Output of an analysis run — stored in data/summaries/."""

    date: DateValue
    period_start: DateValue
    period_end: DateValue
    metrics_snapshot: dict  # flexible key-value of computed metrics
    trends: list[str]  # human-readable trend descriptions
    recommendations: list[HealthRecommendation]
    context_for_next_run: str = Field(
        ..., description="Free-text context the agent should read next time"
    )
    report_markdown: str = Field(
        default="", description="Full Hebrew report markdown from the summary file"
    )


# ── Recommendation Tracking ───────────────────────────────────────


class RecStatus(StrEnum):
    """Status of a tracked recommendation."""

    PENDING = "pending"
    DONE = "done"
    SNOOZED = "snoozed"


class RecommendationStatus(BaseModel):
    """Tracks whether a user adopted, snoozed, or ignored a recommendation."""

    rec_id: str = Field(..., description="SHA-256 hash of category+title")
    status: RecStatus = RecStatus.PENDING
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_recommendation(cls, rec: HealthRecommendation) -> "RecommendationStatus":
        """Create a pending status entry from a recommendation."""
        import hashlib

        key = f"{rec.category}:{rec.title}"
        rec_id = hashlib.sha256(key.encode()).hexdigest()[:16]
        return cls(rec_id=rec_id)
