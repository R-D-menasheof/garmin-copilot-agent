"""Tests for shared/notifications.py (Phase 7 FCM sender)."""

from __future__ import annotations

import json

from shared import notifications
from shared.notifications import NotificationSender, notify_report_ready

_SA = {
    "client_email": "x@y.iam.gserviceaccount.com",
    "private_key": "-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n",
}


class _Token:
    def __init__(self, token: str) -> None:
        self.token = token


class _FakeStore:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens

    def load_push_tokens(self) -> list[_Token]:
        return self._tokens


class TestNotificationSender:
    def test_unconfigured_is_noop(self, monkeypatch) -> None:
        monkeypatch.delenv("FCM_PROJECT_ID", raising=False)
        monkeypatch.delenv("FCM_SERVICE_ACCOUNT_JSON", raising=False)
        monkeypatch.delenv("FCM_SERVICE_ACCOUNT_FILE", raising=False)
        sender = NotificationSender(project_id=None, service_account=None)
        assert sender.configured is False
        assert sender.send(["a"], "t", "b") == 0

    def test_configured_flag(self) -> None:
        assert NotificationSender(project_id="p", service_account=_SA).configured is True

    def test_send_calls_transport_per_token(self, monkeypatch) -> None:
        monkeypatch.setattr(notifications, "_access_token", lambda sa: "tok")
        sent: list[str] = []
        monkeypatch.setattr(
            notifications,
            "_send_one",
            lambda pid, at, token, title, body, data: sent.append(token) or True,
        )
        sender = NotificationSender(project_id="p", service_account=_SA)

        n = sender.send(["a", "b"], "title", "body", {"type": "report"})

        assert n == 2
        assert sent == ["a", "b"]

    def test_send_counts_only_successes(self, monkeypatch) -> None:
        monkeypatch.setattr(notifications, "_access_token", lambda sa: "tok")
        monkeypatch.setattr(
            notifications,
            "_send_one",
            lambda pid, at, token, title, body, data: token == "a",
        )
        sender = NotificationSender(project_id="p", service_account=_SA)
        assert sender.send(["a", "b"], "t", "b") == 1

    def test_reads_config_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("FCM_PROJECT_ID", "envp")
        monkeypatch.setenv("FCM_SERVICE_ACCOUNT_JSON", json.dumps(_SA))
        assert NotificationSender().configured is True

    def test_reads_service_account_from_file(self, monkeypatch, tmp_path) -> None:
        path = tmp_path / "sa.json"
        path.write_text(json.dumps(_SA), encoding="utf-8")
        monkeypatch.delenv("FCM_SERVICE_ACCOUNT_JSON", raising=False)
        monkeypatch.setenv("FCM_PROJECT_ID", "envp")
        monkeypatch.setenv("FCM_SERVICE_ACCOUNT_FILE", str(path))
        assert NotificationSender().configured is True


class TestNotifyReportReady:
    def test_skips_when_unconfigured(self) -> None:
        sender = NotificationSender(project_id=None, service_account=None)
        assert notify_report_ready(_FakeStore([_Token("a")]), "2026-07-06", sender=sender) == 0

    def test_no_tokens_returns_zero(self) -> None:
        sender = NotificationSender(project_id="p", service_account=_SA)
        assert notify_report_ready(_FakeStore([]), "2026-07-06", sender=sender) == 0

    def test_sends_to_all_tokens(self, monkeypatch) -> None:
        monkeypatch.setattr(notifications, "_access_token", lambda sa: "tok")
        received: dict = {}

        def fake_send_one(pid, at, token, title, body, data):
            received["title"] = title
            received["data"] = data
            return True

        monkeypatch.setattr(notifications, "_send_one", fake_send_one)
        sender = NotificationSender(project_id="p", service_account=_SA)

        n = notify_report_ready(
            _FakeStore([_Token("a"), _Token("b")]), "2026-07-06", sender=sender
        )

        assert n == 2
        assert "דו" in received["title"]
        assert received["data"] == {"type": "report", "date": "2026-07-06"}
