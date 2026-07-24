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

from publish_summary import (
    _azure_notification_sender,
    parse_args,
    publish_summary,
    publish_all,
    publish_summary_direct,
    send_summary,
)


def _summary(
    day: date = date(2026, 4, 4),
    target_user_id: str = "u-123",
) -> AnalysisSummary:
    return AnalysisSummary(
        target_user_id=target_user_id,
        context_sha256="a" * 64,
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

    def test_parses_all_flag(self) -> None:
        args = parse_args(["--all"])
        assert args.all is True

    def test_all_defaults_false(self) -> None:
        args = parse_args([])
        assert args.all is False


class TestPublishAll:
    @patch("publish_summary.publish_summary", return_value={"status": "ok"})
    @patch("publish_summary.SummaryStore")
    def test_publishes_all_dates(self, mock_store_cls, mock_pub) -> None:
        store = MagicMock()
        store.list_dates.return_value = [date(2026, 3, 20), date(2026, 3, 27)]
        mock_store_cls.return_value = store

        results = publish_all(api_url="http://localhost:7071/api", api_key="test-key")

        assert len(results) == 2
        assert mock_pub.call_count == 2


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


class TestPublishDirect:
    def test_parses_user_id(self) -> None:
        args = parse_args(["--user-id", "u-123", "--date", "2026-04-04"])
        assert args.user_id == "u-123"

    def test_user_id_defaults_none(self) -> None:
        args = parse_args([])
        assert args.user_id is None

    @patch("publish_summary.SummaryStore")
    def test_publishes_direct_to_user_store(self, mock_store_cls, tmp_path) -> None:
        ss = MagicMock()
        ss.load_latest.return_value = _summary()
        ss.directory = tmp_path
        mock_store_cls.return_value = ss
        blob = MagicMock()
        blob.load_latest_summary.return_value = None

        result = publish_summary_direct("u-123", directory=tmp_path, store=blob)

        assert result["status"] == "ok"
        assert result["user_id"] == "u-123"
        assert result["date"] == "2026-04-04"
        blob.save_summary.assert_called_once()
        saved = blob.save_summary.call_args.args[0]
        assert saved.date == date(2026, 4, 4)

    @patch("publish_summary.SummaryStore")
    def test_direct_raises_when_no_summary(self, mock_store_cls, tmp_path) -> None:
        ss = MagicMock()
        ss.load_latest.return_value = None
        ss.directory = tmp_path
        mock_store_cls.return_value = ss

        with pytest.raises(ValueError, match="No summary available"):
            publish_summary_direct("u-123", directory=tmp_path, store=MagicMock())

    @patch("publish_summary.SummaryStore")
    def test_direct_rejects_cross_user_summary(self, mock_store_cls, tmp_path) -> None:
        ss = MagicMock()
        ss.load_latest.return_value = _summary(target_user_id="other-user")
        ss.directory = tmp_path
        mock_store_cls.return_value = ss

        with pytest.raises(ValueError, match="target_user_id"):
            publish_summary_direct("u-123", directory=tmp_path, store=MagicMock())

    @patch("publish_summary.SummaryStore")
    def test_direct_defaults_to_target_user_report_directory(
        self,
        mock_store_cls,
    ) -> None:
        ss = MagicMock()
        ss.load_latest.return_value = _summary()
        ss.directory = Path("unused")
        mock_store_cls.return_value = ss
        blob = MagicMock()
        blob.load_latest_summary.return_value = None

        publish_summary_direct("u-123", store=blob)

        directory = Path(mock_store_cls.call_args.kwargs["directory"])
        assert directory.parts[-3:] == ("users", "u-123", "reports")

    @patch("publish_summary.SummaryStore")
    def test_direct_publish_is_idempotent(self, mock_store_cls, tmp_path) -> None:
        summary = _summary()
        ss = MagicMock()
        ss.load_latest.return_value = summary
        ss.directory = tmp_path
        mock_store_cls.return_value = ss
        blob = MagicMock()
        blob.load_latest_summary.return_value = summary

        result = publish_summary_direct("u-123", directory=tmp_path, store=blob)

        assert result["status"] == "unchanged"
        assert result["notified"] == 0
        blob.save_summary.assert_not_called()


def test_loads_notification_sender_from_azure_settings() -> None:
    sender_cls = MagicMock()
    completed = MagicMock()
    completed.stdout = json.dumps(
        [
            {"name": "FCM_PROJECT_ID", "value": "project-id"},
            {
                "name": "FCM_SERVICE_ACCOUNT_JSON",
                "value": json.dumps({"client_email": "svc@example.com"}),
            },
        ]
    )

    with patch("publish_summary.subprocess.run", return_value=completed) as run:
        _azure_notification_sender(sender_cls)

    sender_cls.assert_called_once_with(
        project_id="project-id",
        service_account={"client_email": "svc@example.com"},
    )
    assert run.call_args.kwargs["capture_output"] is True

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

    @patch("publish_summary.send_summary", return_value={"status": "ok"})
    @patch("publish_summary.SummaryStore")
    def test_includes_report_markdown_from_md_file(self, mock_store_cls, mock_send) -> None:
        """publish_summary should read the raw .md file and include it as report_markdown."""
        import tempfile

        md_content = "# דו\"ח בריאות\n\nתוכן בעברית..."
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "2026-04-04.md"
            md_path.write_text(md_content, encoding="utf-8")

            store = MagicMock()
            store.load_latest.return_value = _summary()
            store.directory = Path(tmpdir)
            mock_store_cls.return_value = store

            publish_summary(api_url="http://localhost:7071/api", api_key="test-key")

        sent_summary = mock_send.call_args.args[0]
        assert sent_summary.report_markdown == md_content

    @patch("publish_summary.send_summary", return_value={"status": "ok"})
    @patch("publish_summary.SummaryStore")
    def test_sends_empty_markdown_when_md_file_missing(self, mock_store_cls, mock_send) -> None:
        """If the .md file doesn't exist, report_markdown should be empty."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MagicMock()
            store.load_latest.return_value = _summary()
            store.directory = Path(tmpdir)
            mock_store_cls.return_value = store

            publish_summary(api_url="http://localhost:7071/api", api_key="test-key")

        sent_summary = mock_send.call_args.args[0]
        assert sent_summary.report_markdown == ""
