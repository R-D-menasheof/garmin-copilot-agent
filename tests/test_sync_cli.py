"""Tests for sync CLI — argument parsing and date resolution."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

# Import from scripts/sync.py — adjust path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sync import _save_user_cloud_data, _user_client, parse_args, resolve_dates  # noqa: E402
from _users import (  # noqa: E402
    user_garmin_sync_directory,
    user_garmin_token_directory,
)

from vitalis.models import BiometricsRecord, Profile  # noqa: E402


class TestSyncCLI:
    def test_parse_days(self):
        args = parse_args(["--days", "7"])
        assert args.days == 7

    def test_parse_today(self):
        args = parse_args(["--today"])
        assert args.today is True

    def test_parse_user_id(self):
        args = parse_args([
            "--today",
            "--user-id",
            "11111111-1111-4111-8111-111111111111",
        ])
        assert args.user_id == "11111111-1111-4111-8111-111111111111"

    def test_parse_non_interactive(self):
        args = parse_args(["--today", "--user-id", "u", "--non-interactive"])
        assert args.non_interactive is True

    def test_non_interactive_user_sync_fails_without_tokens(
        self,
        monkeypatch,
        tmp_path,
    ):
        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            def connect(self):
                raise ValueError("Garmin credentials not configured")

        monkeypatch.setattr("sync.GarminClient", FakeClient)

        with pytest.raises(RuntimeError, match="Stored Garmin tokens"):
            _user_client(tmp_path, interactive=False)

    def test_garmin_paths_are_isolated_by_validated_user_id(self):
        user_a = "11111111-1111-4111-8111-111111111111"
        user_b = "22222222-2222-4222-8222-222222222222"

        token_a = user_garmin_token_directory(user_a)
        token_b = user_garmin_token_directory(user_b)
        sync_a = user_garmin_sync_directory(user_a)
        sync_b = user_garmin_sync_directory(user_b)

        assert token_a != token_b
        assert sync_a != sync_b
        assert token_a == token_a.parent / ".garmin_tokens"
        assert sync_a == sync_a.parent / "synced"
        assert user_a in str(token_a)
        assert user_b in str(token_b)

    def test_garmin_paths_support_safe_legacy_user_id(self):
        assert "roei" in str(user_garmin_token_directory("roei"))

    def test_garmin_paths_reject_path_traversal(self):
        with pytest.raises(ValueError, match="Invalid user_id"):
            user_garmin_token_directory("..\\owner")

    def test_parse_from_to(self):
        args = parse_args(["--from", "2026-01-01", "--to", "2026-01-31"])
        assert args.start == date(2026, 1, 1)
        assert args.end == date(2026, 1, 31)

    def test_parse_from_without_to(self):
        args = parse_args(["--from", "2026-01-01"])
        assert args.start == date(2026, 1, 1)
        assert args.end is None  # resolve_dates will default to today

    def test_resolve_today(self):
        args = parse_args(["--today"])
        start, end = resolve_dates(args)
        today = date.today()
        assert start == today
        assert end == today

    def test_resolve_days(self):
        args = parse_args(["--days", "7"])
        start, end = resolve_dates(args)
        today = date.today()
        assert end == today
        assert start == today - timedelta(days=6)

    def test_resolve_from_to(self):
        args = parse_args(["--from", "2026-01-01", "--to", "2026-01-15"])
        start, end = resolve_dates(args)
        assert start == date(2026, 1, 1)
        assert end == date(2026, 1, 15)

    def test_resolve_from_defaults_to_today(self):
        args = parse_args(["--from", "2026-01-01"])
        start, end = resolve_dates(args)
        assert start == date(2026, 1, 1)
        assert end == date.today()

    def test_resolve_to_before_from_raises(self):
        args = parse_args(["--from", "2026-02-01", "--to", "2026-01-01"])
        with pytest.raises(ValueError, match="--to must not be before --from"):
            resolve_dates(args)

    def test_no_args_raises(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_user_cloud_save_merges_biometrics_and_preserves_profile(
        self,
        monkeypatch,
    ):
        class FakeStore:
            def __init__(self):
                self.saved_biometrics = {}
                self.profile = Profile(
                    display_name="משתמשת בדיקה",
                    goals=["ירידה במשקל"],
                    notes="preserve me",
                    onboarded=True,
                )

            def load_biometrics_range(self, start, end):
                return {
                    date(2026, 7, 10): BiometricsRecord(
                        date=date(2026, 7, 10),
                        bp_systolic=122,
                        source="health_connect",
                    )
                }

            def save_biometrics(self, day, record):
                self.saved_biometrics[day] = record

            def load_profile(self):
                return self.profile

            def save_profile(self, profile):
                self.profile = profile

        fake = FakeStore()
        import _users

        monkeypatch.setattr(_users, "get_store", lambda _user_id: fake)
        raw = {
            "daily_stats": [
                {
                    "calendarDate": "2026-07-10",
                    "totalSteps": 6789,
                    "restingHeartRate": 68,
                }
            ],
            "devices": [{"productDisplayName": "Venu Sq"}],
        }

        days, fields = _save_user_cloud_data(
            "11111111-1111-4111-8111-111111111111",
            date(2026, 7, 10),
            date(2026, 7, 10),
            raw,
        )

        assert days == 1
        record = fake.saved_biometrics[date(2026, 7, 10)]
        assert record.steps == 6789
        assert record.bp_systolic == 122
        assert record.source == "garmin_direct+health_connect"
        assert fields["resting_heart_rate"] == 68
        assert fake.profile.display_name == "משתמשת בדיקה"
        assert fake.profile.goals == ["ירידה במשקל"]
        assert fake.profile.notes == "preserve me"
        assert fake.profile.resting_heart_rate == 68
        assert fake.profile.devices[0].name == "Venu Sq"
