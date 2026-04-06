"""Tests for scripts/publish_summary.py CLI.

TDD RED phase. HTTP calls and summary loading mocked.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))
sys.path.insert(0, str(_project_root / "scripts"))

from vitalis.models import AnalysisSummary, HealthRecommendation

from publish_summary import parse_args, publish_summary, send_summary


def _summary(day: date = date(2026, 4, 4)) -> AnalysisSummary:
    return AnalysisSummary(
        date=day,
        period_start=date(2026, 3, 29),
        period_end=day,
        metrics_snapshot={"steps_avg": 8500},
        trends=["Average steps increased"],
        recommendations=[
            HealthRecommendation(
                category="activity",
                title="Keep walking",
                detail="Maintain the current step streak.",
                priority=2,
            )
        ],
        context_for_next_run="Monitor recovery after hard sessions.",
    )


class TestParseArgs:
    def test_parses_optional_date(self) -> None:
        args = parse_args(["--date", "2026-04-04"])
        assert args.date == "2026-04-04"

    def test_date_is_optional(self) -> None:
        args = parse_args([])
        assert args.date is None


class TestSendSummary:
    @patch("publish_summary.httpx")
    def test_sends_summary_payload(self, mock_httpx) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_httpx.post.return_value = mock_resp

        result = send_summary(
            _summary(),
            api_url="http://localhost:7071/api",
            api_key="test-key",
        )

        assert result["status"] == "ok"
        call_args = mock_httpx.post.call_args
        assert call_args.args[0] == "http://localhost:7071/api/v1/summary"
        body = json.loads(call_args.kwargs.get("content") or call_args[1].get("content"))
        assert body["date"] == "2026-04-04"
        assert body["metrics_snapshot"]["steps_avg"] == 8500


class TestPublishSummary:
    @patch("publish_summary.send_summary", return_value={"status": "ok"})
    @patch("publish_summary.SummaryStore")
    def test_publishes_latest_summary_by_default(self, mock_store_cls, mock_send) -> None:
        store = MagicMock()
        store.load_latest.return_value = _summary()
        mock_store_cls.return_value = store

        result = publish_summary(api_url="http://localhost:7071/api", api_key="test-key")

        assert result["status"] == "ok"
        mock_send.assert_called_once()
        store.load_latest.assert_called_once_with()

    @patch("publish_summary.SummaryStore")
    def test_raises_when_no_summary_exists(self, mock_store_cls) -> None:
        store = MagicMock()
        store.load_latest.return_value = None
        mock_store_cls.return_value = store

        with pytest.raises(ValueError, match="No summary available"):
            publish_summary(api_url="http://localhost:7071/api", api_key="test-key")

    @patch("publish_summary.send_summary", return_value={"status": "ok"})
    @patch("publish_summary.SummaryStore")
    def test_can_publish_specific_date(self, mock_store_cls, mock_send) -> None:
        store = MagicMock()
        store.load_by_date.return_value = _summary(date(2026, 4, 3))
        mock_store_cls.return_value = store

        result = publish_summary(
            summary_date=date(2026, 4, 3),
            api_url="http://localhost:7071/api",
            api_key="test-key",
        )

        assert result["status"] == "ok"
        store.load_by_date.assert_called_once_with(date(2026, 4, 3))
        mock_send.assert_called_once()