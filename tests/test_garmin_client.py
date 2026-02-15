from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from vitalis import garmin_client as client_module
from vitalis.garmin_client import GarminClient, GarminMFARequiredError


class _FakeGarmin:
    """Test double for garminconnect.Garmin."""

    login_calls: list[tuple[tuple[str, ...], str | None]] = []
    dump_calls: list[str] = []
    resume_login_calls: list[tuple[dict, str]] = []
    connectapi_calls: list[str] = []

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        **_: object,
    ):
        self._email = email
        self._password = password
        self.display_name: str | None = None
        self.full_name: str | None = None
        self.unit_system: str | None = None
        self.garth = SimpleNamespace(
            dump=self._dump,
            connectapi=self._connectapi,
        )

    def _dump(self, tokenstore: str) -> None:
        self.dump_calls.append(tokenstore)

    def _connectapi(self, path: str) -> dict:
        self.connectapi_calls.append(path)
        if "profile" in path:
            return {"displayName": "TestUser", "fullName": "Test User"}
        if "user-settings" in path:
            return {"userData": {"measurementSystem": "METRIC"}}
        return {}

    def login(self, tokenstore: str | None = None):
        args: tuple[str, ...] = ()
        if self._email is not None and self._password is not None:
            args = (self._email, self._password)

        self.login_calls.append((args, tokenstore))

        # Phase 1 (token login) fails with garth assertion
        if not args:
            raise AssertionError("OAuth1 token is required for OAuth2 refresh")

        return (None, None)

    def resume_login(self, state: dict, code: str) -> tuple:
        self.resume_login_calls.append((state, code))
        return (None, None)


class _FakeGarminTokenSuccess(_FakeGarmin):
    """Like _FakeGarmin but Phase 1 token login succeeds."""

    def login(self, tokenstore: str | None = None):
        args: tuple[str, ...] = ()
        if self._email is not None and self._password is not None:
            args = (self._email, self._password)
        self.login_calls.append((args, tokenstore))
        # Token login always succeeds
        return (None, None)


class _FakeGarminMFA(_FakeGarmin):
    """Like _FakeGarmin but credential login triggers MFA."""

    def login(self, tokenstore: str | None = None):
        args: tuple[str, ...] = ()
        if self._email is not None and self._password is not None:
            args = (self._email, self._password)
        self.login_calls.append((args, tokenstore))

        if not args:
            raise AssertionError("OAuth1 token is required for OAuth2 refresh")

        return ("needs_mfa", {"signin_params": {}, "client": object()})


@pytest.fixture(autouse=True)
def _reset_fake_state():
    for cls in (_FakeGarmin, _FakeGarminTokenSuccess, _FakeGarminMFA):
        cls.login_calls = []
        cls.dump_calls = []
        cls.resume_login_calls = []
        cls.connectapi_calls = []
    yield


def test_connect_recovers_from_token_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Phase 1 token failure should clear tokenstore and fall through to credential login."""
    tokenstore = tmp_path / "garmin_tokens"
    tokenstore.mkdir(parents=True, exist_ok=True)
    # Place actual token files so Phase 1 is attempted
    (tokenstore / "oauth1_token.json").write_text('{"broken": true}', encoding="utf-8")
    (tokenstore / "oauth2_token.json").write_text('{"broken": true}', encoding="utf-8")

    monkeypatch.setattr(client_module, "Garmin", _FakeGarmin)

    client = GarminClient(email="user@example.com", password="secret", tokenstore=str(tokenstore))
    client.connect()

    # Phase 1 (no creds) then Phase 2 (with creds, no tokenstore arg)
    assert _FakeGarmin.login_calls[0] == ((), str(tokenstore))
    assert _FakeGarmin.login_calls[1] == (("user@example.com", "secret"), None)
    assert _FakeGarmin.dump_calls == [str(tokenstore)]
    # Stale token files should be wiped
    assert not (tokenstore / "oauth1_token.json").exists()


def test_connect_raises_when_credentials_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    tokenstore = tmp_path / "garmin_tokens"
    monkeypatch.setattr(client_module, "Garmin", _FakeGarmin)
    monkeypatch.delenv("GARMIN_EMAIL", raising=False)
    monkeypatch.delenv("GARMIN_PASSWORD", raising=False)

    client = GarminClient(email=None, password=None, tokenstore=str(tokenstore))

    with pytest.raises(ValueError, match="Garmin credentials not configured"):
        client.connect()


def test_connect_mfa_raises_with_session_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """When credential login returns needs_mfa, GarminMFARequiredError carries a session_id."""
    tokenstore = tmp_path / "garmin_tokens"
    monkeypatch.setattr(client_module, "Garmin", _FakeGarminMFA)

    client = GarminClient(email="me@test.com", password="pw", tokenstore=str(tokenstore))

    with pytest.raises(GarminMFARequiredError) as exc_info:
        client.connect()

    err = exc_info.value
    assert err.session_id  # non-empty
    assert "verification code" in str(err)

    # The session should be in the in-memory store
    assert err.session_id in client_module._pending_mfa_sessions


def test_connect_resumes_mfa_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Resuming with mfa_code + session_id should call resume_login and save tokens."""
    tokenstore = tmp_path / "garmin_tokens"
    monkeypatch.setattr(client_module, "Garmin", _FakeGarminMFA)

    client = GarminClient(email="me@test.com", password="pw", tokenstore=str(tokenstore))

    # Step 1: trigger MFA
    with pytest.raises(GarminMFARequiredError) as exc_info:
        client.connect()
    session_id = exc_info.value.session_id

    # Step 2: resume with MFA code
    client2 = GarminClient(email="me@test.com", password="pw", tokenstore=str(tokenstore))
    client2.connect(mfa_code="123456", mfa_session_id=session_id)

    # Session should be consumed
    assert session_id not in client_module._pending_mfa_sessions
    assert _FakeGarminMFA.resume_login_calls[-1][1] == "123456"
    assert _FakeGarminMFA.dump_calls  # tokens were saved


def test_connect_skips_phase1_when_no_token_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Phase 1 should be skipped entirely when oauth1_token.json does not exist."""
    tokenstore = tmp_path / "garmin_tokens"
    tokenstore.mkdir(parents=True, exist_ok=True)
    # Directory exists but has NO oauth1_token.json / oauth2_token.json

    monkeypatch.setattr(client_module, "Garmin", _FakeGarmin)

    client = GarminClient(email="user@example.com", password="secret", tokenstore=str(tokenstore))
    client.connect()

    # Only ONE login call — Phase 2 (credential login), no Phase 1
    assert len(_FakeGarmin.login_calls) == 1
    assert _FakeGarmin.login_calls[0] == (("user@example.com", "secret"), None)


def test_connect_loads_profile_after_credential_login(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """After Phase 2 credential login, display_name must be populated."""
    tokenstore = tmp_path / "garmin_tokens"
    monkeypatch.setattr(client_module, "Garmin", _FakeGarmin)

    client = GarminClient(email="user@example.com", password="pw", tokenstore=str(tokenstore))
    client.connect()

    # The Garmin instance should have display_name set (not None)
    assert client.api.display_name is not None


def test_token_login_redumps_tokens(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Phase 1 token login success should re-dump tokens (in case garth refreshed them)."""
    tokenstore = tmp_path / "garmin_tokens"
    tokenstore.mkdir(parents=True, exist_ok=True)
    (tokenstore / "oauth1_token.json").write_text("{}", encoding="utf-8")
    (tokenstore / "oauth2_token.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(client_module, "Garmin", _FakeGarminTokenSuccess)

    client = GarminClient(email="u@e.com", password="pw", tokenstore=str(tokenstore))
    client.connect()

    # Only one login call (Phase 1 succeeds, Phase 2 never reached)
    assert len(_FakeGarminTokenSuccess.login_calls) == 1
    # Tokens should be re-dumped after Phase 1 success
    assert str(tokenstore) in _FakeGarminTokenSuccess.dump_calls


def test_mfa_resume_loads_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """After MFA resume, display_name should be populated via _load_profile_and_settings."""
    tokenstore = tmp_path / "garmin_tokens"
    monkeypatch.setattr(client_module, "Garmin", _FakeGarminMFA)

    client = GarminClient(email="me@test.com", password="pw", tokenstore=str(tokenstore))

    # Step 1: trigger MFA
    with pytest.raises(GarminMFARequiredError) as exc_info:
        client.connect()
    session_id = exc_info.value.session_id

    # Step 2: resume with MFA code
    client2 = GarminClient(email="me@test.com", password="pw", tokenstore=str(tokenstore))
    client2.connect(mfa_code="123456", mfa_session_id=session_id)

    # Profile should be loaded (connectapi called for profile/settings)
    profile_calls = [c for c in _FakeGarminMFA.connectapi_calls if "profile" in c]
    assert len(profile_calls) >= 1


class _FakeGarminWithData(_FakeGarminTokenSuccess):
    """Extends token-success fake with stubbed data methods for fetch_all testing."""

    def get_stats(self, d):
        return {"calendarDate": d, "totalSteps": 8000}

    def get_heart_rates(self, d):
        return {"calendarDate": d, "restingHeartRate": 55}

    def get_sleep_data(self, d):
        return {"dailySleepDTO": {"calendarDate": d, "sleepTimeSeconds": 25000}}

    def get_body_composition(self, d):
        return {"calendarDate": d, "weight": 76000}

    def get_stress_data(self, d):
        return {"calendarDate": d, "overallStressLevel": 30}

    def get_steps_data(self, d):
        return {"calendarDate": d}

    def get_respiration_data(self, d):
        return {"calendarDate": d}

    def get_spo2_data(self, d):
        return {"calendarDate": d}

    def get_rhr_day(self, d):
        return {"calendarDate": d}

    def get_hrv_data(self, d):
        return {"calendarDate": d}

    def get_training_readiness(self, d):
        return {"calendarDate": d}

    def get_training_status(self, d):
        return {"calendarDate": d}

    def get_hydration_data(self, d):
        return {"calendarDate": d}

    def get_floors(self, d):
        return {"calendarDate": d}

    def get_intensity_minutes_data(self, d):
        return {"calendarDate": d}

    def get_hill_score(self, d):
        return {"calendarDate": d}

    def get_endurance_score(self, d):
        return {"calendarDate": d}

    def get_all_day_stress(self, d):
        return {"calendarDate": d}

    def get_activities_by_date(self, start, end, activity_type=None):
        return [{"activityId": "1", "duration": 1800}]

    def get_weigh_ins(self, start, end):
        return {"dateWeightList": []}

    def get_daily_steps(self, start, end):
        return [{"calendarDate": start, "totalSteps": 8000}]

    def get_daily_sleep(self, start, end):
        return [{"calendarDate": start, "sleepTimeSeconds": 25000}]

    def get_max_metrics(self, d):
        return {"generic": {"vo2MaxPreciseValue": 48.5}}

    def get_personal_record(self):
        return [{"typeId": 1, "value": 1200.0}]

    def get_body_battery(self):
        return [{"charged": 85, "drained": 22}]

    def get_devices(self):
        return [{"productDisplayName": "Forerunner 265"}]

    def get_goals(self, goal_type="all"):
        return [{"goalId": "1", "goalType": "steps"}]

    def get_user_summary(self):
        return {"displayName": "TestUser"}


def test_fetch_all_returns_all_data_types(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """fetch_all should return data for all 30+ data types."""
    tokenstore = tmp_path / "garmin_tokens"
    tokenstore.mkdir(parents=True, exist_ok=True)
    (tokenstore / "oauth1_token.json").write_text("{}", encoding="utf-8")
    (tokenstore / "oauth2_token.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(client_module, "Garmin", _FakeGarminWithData)

    client = GarminClient(email="u@e.com", password="pw", tokenstore=str(tokenstore))
    client.connect()

    from datetime import date
    result = client.fetch_all(date(2026, 2, 10), date(2026, 2, 11))

    # Per-day types should have 2 entries (2 days)
    assert len(result["daily_stats"]) == 2
    assert len(result["heart_rate"]) == 2
    assert len(result["sleep"]) == 2

    # Range types
    assert len(result["activities"]) == 1
    assert isinstance(result["weigh_ins"], dict)

    # Snapshot types
    assert "personal_records" in result
    assert "devices" in result
    assert len(result["devices"]) == 1


def test_fetch_all_handles_failures_gracefully(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """fetch_all should skip failed data types without crashing."""
    tokenstore = tmp_path / "garmin_tokens"
    tokenstore.mkdir(parents=True, exist_ok=True)
    (tokenstore / "oauth1_token.json").write_text("{}", encoding="utf-8")
    (tokenstore / "oauth2_token.json").write_text("{}", encoding="utf-8")

    # Use base _FakeGarminTokenSuccess which has no data methods
    monkeypatch.setattr(client_module, "Garmin", _FakeGarminTokenSuccess)

    client = GarminClient(email="u@e.com", password="pw", tokenstore=str(tokenstore))
    client.connect()

    from datetime import date
    result = client.fetch_all(date(2026, 2, 10), date(2026, 2, 10))

    # Should not crash, all per-day should be empty lists
    assert result["daily_stats"] == []
    assert result["activities"] == []
    assert result["devices"] == []


def test_fetch_range_uses_fetch_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Legacy fetch_range should delegate to fetch_all."""
    tokenstore = tmp_path / "garmin_tokens"
    tokenstore.mkdir(parents=True, exist_ok=True)
    (tokenstore / "oauth1_token.json").write_text("{}", encoding="utf-8")
    (tokenstore / "oauth2_token.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(client_module, "Garmin", _FakeGarminWithData)

    client = GarminClient(email="u@e.com", password="pw", tokenstore=str(tokenstore))
    client.connect()

    result = client.fetch_range(days_back=3)
    # Legacy keys should exist
    assert "daily_stats" in result
    assert "sleep" in result
    assert "activities" in result
    assert len(result["daily_stats"]) == 3
