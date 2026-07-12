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
    """Daily nutrition targets — set by the user or the External Agent.

    Primary fields are for training days. Optional rest-day overrides
    let the mobile app show different targets on rest/low-intensity days.
    """

    date: DateValue
    calories_target: int = Field(ge=0)
    protein_g_target: float = Field(ge=0)
    carbs_g_target: float = Field(ge=0)
    fat_g_target: float = Field(ge=0)
    rest_calories_target: Optional[int] = Field(default=None, ge=0)
    rest_carbs_g_target: Optional[float] = Field(default=None, ge=0)
    set_by: str = Field(pattern=r"^(user|agent)$", description="Who set this goal")
    created_at: datetime = Field(default_factory=datetime.now)


class DailyNutritionLog(BaseModel):
    """All meals for a single day, with optional goal compliance."""

    date: DateValue
    meals: list[MealEntry] = Field(default_factory=list)
    goal_compliance_pct: Optional[float] = None


class DayTrackingOverride(BaseModel):
    """Marks a day's nutrition log as unreliable/not representative.

    Used to exclude a day from weekly balance calculations without
    deleting any logged meals (e.g. "I forgot to log properly today").
    """

    date: DateValue
    tracked: bool = Field(
        default=True,
        description="False = exclude this day from balance calculations",
    )
    note: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


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
    moderate_intensity_minutes: Optional[int] = None
    vigorous_intensity_minutes: Optional[int] = None
    activity_count: Optional[int] = None
    activity_types: list[str] = Field(default_factory=list)

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

    # Fitness
    vo2max: Optional[float] = None

    # Recovery / stress (Garmin-specific)
    body_battery_high: Optional[int] = None
    body_battery_low: Optional[int] = None
    body_battery_at_wake: Optional[int] = None
    stress_avg: Optional[int] = None
    stress_max: Optional[int] = None
    training_readiness: Optional[int] = None

    # Hydration
    water_ml: Optional[float] = None

    # Provenance — which pipeline produced this record, e.g. "garmin_direct",
    # "health_connect", or a merge like "garmin_direct+health_connect".
    source: Optional[str] = None


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


class MedicalUpload(BaseModel):
    """Metadata for a user-uploaded medical document (Phase 4b).

    Raw file bytes are stored at ``users/{uid}/medical/uploads/{id}_{filename}``;
    this is the index entry (``users/{uid}/medical/uploads/index.json`` holds the
    list). Extraction is done later by the owner locally, so ``extracted`` stays
    False until the owner processes it (Phase 6.3).
    """

    id: str
    filename: str
    content_type: str = Field(
        description="MIME type: application/pdf, image/jpeg, image/png"
    )
    size_bytes: int = Field(ge=0)
    category: str = Field(default="", description="Optional user label")
    note: str = ""
    uploaded_at: datetime = Field(default_factory=datetime.now)
    extracted: bool = False


# ── Health Analysis ────────────────────────────────────────────────


class HealthRecommendation(BaseModel):
    """A single actionable recommendation."""

    category: str = Field(..., description="e.g. 'sleep', 'activity', 'recovery'")
    title: str
    detail: str
    priority: int = Field(ge=1, le=5, description="1 = highest priority")


class AnalysisSummary(BaseModel):
    """Output of an analysis run — stored in data/summaries/."""

    target_user_id: str | None = Field(
        default=None,
        description="Explicit target user for cross-user publication safety",
    )
    context_sha256: str | None = Field(
        default=None,
        description="SHA-256 of the immutable user context packet used for analysis",
    )
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
    nudge_rules: list["NudgeRule"] = Field(
        default_factory=list,
        description="Agent-written rules evaluated daily against biometrics",
    )
    correlations: list["HealthCorrelation"] = Field(
        default_factory=list,
        description="Cross-domain correlations discovered by the agent",
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


# ── Daily Nudges ──────────────────────────────────────────────────


class NudgeRule(BaseModel):
    """A rule the agent writes for daily evaluation against biometrics."""

    condition: str = Field(
        ..., description="e.g. 'sleep_hours < 6', 'resting_hr > 70'"
    )
    message_he: str = Field(..., description="Hebrew nudge message for the user")
    category: str = Field(..., description="e.g. 'recovery', 'sleep', 'fitness'")
    priority: int = Field(ge=1, le=5, default=3)


# ── Health Timeline ───────────────────────────────────────────────


class TimelineCategory(StrEnum):
    MEDICAL = "medical"
    MILESTONE = "milestone"
    MEDICATION = "medication"
    LIFESTYLE = "lifestyle"


class TimelineSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    POSITIVE = "positive"


class TimelineEvent(BaseModel):
    """A single event in the user's health timeline."""

    date: DateValue
    category: TimelineCategory
    title_he: str
    detail_he: str = ""
    icon: str = ""
    severity: TimelineSeverity = TimelineSeverity.INFO
    source: str = Field(default="agent", description="'agent', 'medical', 'user'")


# ── Health Correlations ───────────────────────────────────────────


class CorrelationRelationship(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    THRESHOLD = "threshold"


class HealthCorrelation(BaseModel):
    """A cross-domain correlation discovered by the agent."""

    metric_a: str
    metric_b: str
    relationship: CorrelationRelationship
    description_he: str
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)
    discovered_date: DateValue


# ── Training Programs ─────────────────────────────────────────────


class TrainingSession(BaseModel):
    day: str = Field(..., description="Day name or date")
    type: str = Field(..., description="e.g. 'swimming', 'strength', 'walk', 'rest'")
    description: str = ""
    duration_min: int = Field(ge=0, default=0)
    target_hr_zone: Optional[int] = None
    completed: bool = False


class TrainingWeek(BaseModel):
    week_number: int
    sessions: list[TrainingSession] = Field(default_factory=list)
    notes: str = ""


class TrainingProgram(BaseModel):
    id: str = Field(default_factory=_generate_id)
    name: str
    goal: str
    duration_weeks: int
    weeks: list[TrainingWeek] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    active: bool = True


# ── Goal Programs ─────────────────────────────────────────────────


class Milestone(BaseModel):
    title_he: str
    target_metric: str = ""
    target_value: float = 0
    current_value: float = 0
    deadline: Optional[DateValue] = None
    completed: bool = False


class GoalProgram(BaseModel):
    id: str = Field(default_factory=_generate_id)
    name_he: str
    description_he: str = ""
    duration_weeks: int = 0
    milestones: list[Milestone] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    progress_pct: float = 0.0
    active: bool = True


# ── Sleep Protocol ────────────────────────────────────────────────


class ChecklistItem(BaseModel):
    id: str
    label_he: str
    category: str = Field(..., description="'wind_down', 'environment', or 'habits'")
    checked: bool = False


class SleepChecklist(BaseModel):
    items: list[ChecklistItem] = Field(default_factory=list)


class SleepEntry(BaseModel):
    date: DateValue
    bedtime: Optional[str] = None
    waketime: Optional[str] = None
    rating: int = Field(ge=1, le=5, default=3)
    notes: str = ""
    caffeine_cutoff: Optional[str] = None
    screen_cutoff: Optional[str] = None
    checklist_completed: int = 0


# ── Lab Trends ────────────────────────────────────────────────────


class LabStatus(StrEnum):
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"


class LabDataPoint(BaseModel):
    date: DateValue
    value: float
    unit: str
    reference_range: str = ""
    status: LabStatus = LabStatus.NORMAL


class LabTrend(BaseModel):
    metric: str
    display_name_he: str = ""
    values: list[LabDataPoint] = Field(default_factory=list)


# ── User Profile ──────────────────────────────────────────────────


class Medication(BaseModel):
    """A medication the user takes (or has stopped)."""

    name: str
    type: str = ""
    dose: str = ""
    frequency: str = ""
    purpose: str = ""
    since: Optional[str] = None
    stopped: Optional[str] = None
    note: str = ""


class Supplement(BaseModel):
    """A supplement the user takes."""

    name: str
    dosage: str = ""
    timing: str = ""
    since: Optional[str] = None
    stopped: Optional[str] = None
    note: str = ""


class HealthLogEntry(BaseModel):
    """A timestamped free-text health note."""

    date: DateValue
    note: str = ""


class Device(BaseModel):
    """A connected wearable device."""

    name: str
    type: str = ""


class Profile(BaseModel):
    """User health profile — personal info plus auto-synced wearable metrics.

    One profile per user, stored at ``users/{user_id}/profile.json``. Personal
    fields are user-editable (via onboarding or the in-app profile screen);
    auto-synced fields are populated from wearable data and are read-only in
    the UI. Isolation is by blob path, so the model carries no user_id.
    """

    # Identity (from SSO; email lets the owner map opaque ids to people)
    display_name: str = ""
    email: str = ""

    # Personal — user editable
    date_of_birth: Optional[DateValue] = None
    sex: Optional[str] = Field(default=None, description="Biological sex / gender")
    height_cm: Optional[float] = Field(default=None, ge=0)
    goals: list[str] = Field(default_factory=list)
    injuries: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    notes: str = ""
    current_medications: list[Medication] = Field(default_factory=list)
    supplements: list[Supplement] = Field(default_factory=list)
    health_log: list[HealthLogEntry] = Field(default_factory=list)

    # Legacy age (owner's pre-migration profile.yaml); prefer date_of_birth.
    age: Optional[float] = Field(default=None, ge=0)

    # Auto-synced from wearable — read-only in the UI
    weight_kg: Optional[float] = None
    body_fat_pct: Optional[float] = None
    bmi: Optional[float] = None
    vo2max: Optional[float] = None
    fitness_age: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    devices: list[Device] = Field(default_factory=list)
    last_synced: Optional[str] = None

    # Lifecycle
    onboarded: bool = False

    @property
    def age_years(self) -> Optional[float]:
        """Age from ``date_of_birth``, falling back to the legacy ``age`` field."""
        if self.date_of_birth is not None:
            return round((DateValue.today() - self.date_of_birth).days / 365.25, 1)
        return self.age


class PushToken(BaseModel):
    """A device's push-notification registration token (Phase 7).

    Stored per user at ``users/{user_id}/push/tokens.json`` (a list). Android
    push is delivered via FCM through Azure Notification Hubs; ``token`` is the
    FCM registration token uploaded by the mobile app after sign-in.
    """

    token: str = Field(min_length=1, description="FCM registration token")
    platform: str = Field(default="android", description="Device platform")
    device_label: str = Field(default="", description="Optional device name")
    updated_at: datetime = Field(default_factory=datetime.now)
