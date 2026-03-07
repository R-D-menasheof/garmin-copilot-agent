"""Pydantic models — data shapes used by the Vitalis pipeline."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


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
    date: date
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

    date: date
    period_start: date
    period_end: date
    metrics_snapshot: dict  # flexible key-value of computed metrics
    trends: list[str]  # human-readable trend descriptions
    recommendations: list[HealthRecommendation]
    context_for_next_run: str = Field(
        ..., description="Free-text context the agent should read next time"
    )
