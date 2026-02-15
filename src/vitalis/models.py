"""Pydantic models — data shapes used by the Vitalis pipeline."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


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
