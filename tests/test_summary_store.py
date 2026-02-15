"""Tests for summary_store — SSOT for agent memory persistence.

TDD: These tests define the expected read/write behavior.
"""

import json
from datetime import date

import pytest

from vitalis.models import AnalysisSummary, HealthRecommendation
from vitalis.summary_store import SummaryStore


@pytest.fixture
def store(tmp_path):
    """Create a SummaryStore backed by a temp directory."""
    return SummaryStore(directory=tmp_path)


@pytest.fixture
def sample_summary() -> AnalysisSummary:
    """A complete analysis summary for testing."""
    return AnalysisSummary(
        date=date(2026, 2, 14),
        period_start=date(2026, 2, 7),
        period_end=date(2026, 2, 14),
        metrics_snapshot={
            "avg_steps": 8500,
            "avg_resting_hr": 60,
            "avg_sleep_hours": 7.2,
        },
        trends=["All metrics within healthy ranges."],
        recommendations=[
            HealthRecommendation(
                category="general",
                title="Keep it up!",
                detail="Your metrics look good.",
                priority=5,
            )
        ],
        context_for_next_run="Previous run on 2026-02-14. All good.",
    )


class TestSummaryStoreWrite:
    def test_save_creates_markdown_file(self, store, sample_summary):
        path = store.save(sample_summary)
        assert path.exists()
        assert path.name == "2026-02-14.md"

    def test_saved_file_contains_title(self, store, sample_summary):
        path = store.save(sample_summary)
        content = path.read_text(encoding="utf-8")
        assert "# Vitalis Health Summary" in content
        assert "2026-02-14" in content

    def test_saved_file_contains_metrics(self, store, sample_summary):
        path = store.save(sample_summary)
        content = path.read_text()
        assert '"avg_steps": 8500' in content

    def test_saved_file_contains_vitalis_meta_block(self, store, sample_summary):
        path = store.save(sample_summary)
        content = path.read_text()
        assert "```vitalis-meta" in content


class TestSummaryStoreRead:
    def test_load_latest_returns_none_when_empty(self, store):
        assert store.load_latest() is None

    def test_roundtrip_save_and_load(self, store, sample_summary):
        store.save(sample_summary)
        loaded = store.load_latest()
        assert loaded is not None
        assert loaded.date == sample_summary.date
        assert loaded.metrics_snapshot == sample_summary.metrics_snapshot
        assert loaded.context_for_next_run == sample_summary.context_for_next_run

    def test_load_by_date(self, store, sample_summary):
        store.save(sample_summary)
        loaded = store.load_by_date(date(2026, 2, 14))
        assert loaded is not None
        assert loaded.date == date(2026, 2, 14)

    def test_load_by_date_returns_none_for_missing(self, store):
        assert store.load_by_date(date(2099, 1, 1)) is None

    def test_list_dates(self, store, sample_summary):
        store.save(sample_summary)
        dates = store.list_dates()
        assert date(2026, 2, 14) in dates

    def test_get_context_for_next_run(self, store, sample_summary):
        store.save(sample_summary)
        ctx = store.get_context_for_next_run()
        assert "2026-02-14" in ctx

    def test_get_context_returns_empty_when_no_summaries(self, store):
        assert store.get_context_for_next_run() == ""
