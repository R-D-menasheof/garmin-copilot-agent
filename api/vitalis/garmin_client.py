"""Garmin Connect API client — SSOT for all Garmin API interaction.

Handles authentication, session management, and raw data fetching
via the garminconnect library. Every other module that needs Garmin
data MUST go through this client.

Authentication uses OAuth tokens via garth. Tokens are persisted to
`data/.garmin_tokens/` so subsequent logins can reuse them.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TOKEN_DIR = _PROJECT_ROOT / "data" / ".garmin_tokens"

# In-memory store for pending MFA sessions.  The garth Client that
# holds the SSO session cookies cannot be serialised, so we keep it
# alive in process memory until the user submits the MFA code.
_pending_mfa_sessions: dict[str, dict[str, Any]] = {}


class GarminMFARequiredError(Exception):
    """Raised when Garmin requires MFA code to continue login."""

    def __init__(self, message: str, session_id: str) -> None:
        super().__init__(message)
        self.session_id = session_id


class GarminClient:
    """Thin wrapper around the garminconnect library."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        tokenstore: str | None = None,
    ) -> None:
        self._email = email or os.getenv("GARMIN_EMAIL", "")
        self._password = password or os.getenv("GARMIN_PASSWORD", "")
        self._tokenstore = tokenstore or os.getenv("GARMINTOKENS", str(_DEFAULT_TOKEN_DIR))
        self._api: Garmin | None = None

    @staticmethod
    def _clear_tokenstore(tokenstore_path: Path) -> None:
        """Remove every file inside the tokenstore directory."""
        if not tokenstore_path.exists():
            return
        for item in tokenstore_path.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
            except Exception as exc:  # pragma: no cover – OneDrive may lock
                logger.warning("Could not delete %s: %s", item, exc)

    # ------------------------------------------------------------------
    # connect() — main authentication entry point
    # ------------------------------------------------------------------
    def connect(
        self,
        mfa_code: str | None = None,
        mfa_session_id: str | None = None,
    ) -> None:
        """Authenticate and establish a session with Garmin Connect.

        Args:
            mfa_code: The MFA code entered by the user.
            mfa_session_id: The session id returned from a previous 409
                response.  Identifies the in-memory garth Client that
                holds the SSO cookies.
        """
        tokenstore_path = Path(self._tokenstore).expanduser().resolve()
        tokenstore_path.mkdir(parents=True, exist_ok=True)

        # ----- Resume a pending MFA session -----
        if mfa_code and mfa_session_id:
            session = _pending_mfa_sessions.pop(mfa_session_id, None)
            if session is None:
                raise ValueError(
                    "MFA session expired or server restarted. "
                    "Please try syncing again."
                )
            self._api = session["garmin"]
            self._api.resume_login(session["state"], mfa_code)
            try:
                self._api.garth.dump(str(tokenstore_path))
                logger.info("MFA login completed; tokens saved to %s", tokenstore_path)
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not persist OAuth tokens after MFA: %s", exc)
            self._load_profile_and_settings()
            return

        # ----- Phase 1: try existing OAuth tokens (only if files exist) -----
        oauth1_file = tokenstore_path / "oauth1_token.json"
        oauth2_file = tokenstore_path / "oauth2_token.json"
        if oauth1_file.exists() and oauth2_file.exists():
            try:
                self._api = Garmin()
                self._api.login(str(tokenstore_path))
                logger.info("Logged in using stored OAuth tokens.")
                try:
                    self._api.garth.dump(str(tokenstore_path))
                except Exception:  # pragma: no cover
                    pass  # best-effort re-persist after potential token refresh
                self._load_profile_and_settings()
                return
            except Exception as exc:
                logger.warning("Token-based login failed: %s — wiping tokens.", exc)
                self._clear_tokenstore(tokenstore_path)
        else:
            logger.info(
                "No stored tokens in %s — skipping to credential login.",
                tokenstore_path,
            )

        # ----- Phase 2: credential login -----
        if not self._email or not self._password:
            raise ValueError(
                "Garmin credentials not configured. "
                "Set GARMIN_EMAIL and GARMIN_PASSWORD in .env"
            )

        # Temporarily clear GARMINTOKENS so the library doesn't pick up
        # stale env-based paths as a fallback.
        old_env = os.environ.pop("GARMINTOKENS", None)
        try:
            self._api = Garmin(
                self._email, self._password, return_on_mfa=True
            )
            result1, result2 = self._api.login()
        finally:
            if old_env is not None:
                os.environ["GARMINTOKENS"] = old_env

        # ----- Handle MFA -----
        if result1 == "needs_mfa":
            if not isinstance(result2, dict):
                raise GarminMFARequiredError(
                    "Garmin requires MFA but returned unexpected data.",
                    session_id="",
                )
            session_id = uuid.uuid4().hex
            _pending_mfa_sessions[session_id] = {
                "garmin": self._api,
                "state": result2,
            }
            raise GarminMFARequiredError(
                "Garmin sent a verification code to your email. "
                "Please enter the code to continue.",
                session_id=session_id,
            )

        # ----- Success without MFA -----
        self._load_profile_and_settings()
        try:
            self._api.garth.dump(str(tokenstore_path))
            logger.info("OAuth tokens saved to %s", tokenstore_path)
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not persist OAuth tokens: %s", exc)

    def _load_profile_and_settings(self) -> None:
        """Populate display_name and unit_system after a return_on_mfa login.

        The garminconnect library skips profile/settings loading when
        ``return_on_mfa=True``, so we do it ourselves.
        """
        if self._api is None:
            return
        try:
            profile = self._api.garth.connectapi(
                "/userprofile-service/userprofile/profile"
            )
            if profile and isinstance(profile, dict):
                self._api.display_name = profile.get("displayName")
                self._api.full_name = profile.get("fullName")
        except Exception as exc:
            logger.warning("Could not load profile: %s", exc)
        try:
            settings = self._api.garth.connectapi(
                "/userprofile-service/userprofile/user-settings"
            )
            if settings and isinstance(settings, dict) and "userData" in settings:
                self._api.unit_system = settings["userData"].get("measurementSystem")
        except Exception as exc:
            logger.warning("Could not load user settings: %s", exc)

    @property
    def api(self) -> Garmin:
        if self._api is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._api

    # ------------------------------------------------------------------
    # Per-day data fetchers
    # ------------------------------------------------------------------

    def get_daily_stats(self, day: date) -> dict[str, Any]:
        return self.api.get_stats(day.isoformat())

    def get_heart_rate(self, day: date) -> dict[str, Any]:
        return self.api.get_heart_rates(day.isoformat())

    def get_sleep(self, day: date) -> dict[str, Any]:
        return self.api.get_sleep_data(day.isoformat())

    def get_body_composition(self, day: date) -> dict[str, Any]:
        return self.api.get_body_composition(day.isoformat())

    def get_stress(self, day: date) -> dict[str, Any]:
        return self.api.get_stress_data(day.isoformat())

    def get_steps(self, day: date) -> dict[str, Any]:
        return self.api.get_steps_data(day.isoformat())

    def get_respiration(self, day: date) -> dict[str, Any]:
        return self.api.get_respiration_data(day.isoformat())

    def get_spo2(self, day: date) -> dict[str, Any]:
        return self.api.get_spo2_data(day.isoformat())

    def get_rhr(self, day: date) -> dict[str, Any]:
        return self.api.get_rhr_day(day.isoformat())

    def get_hrv(self, day: date) -> dict[str, Any]:
        return self.api.get_hrv_data(day.isoformat())

    def get_training_readiness(self, day: date) -> dict[str, Any]:
        return self.api.get_training_readiness(day.isoformat())

    def get_training_status(self, day: date) -> dict[str, Any]:
        return self.api.get_training_status(day.isoformat())

    def get_daily_hydration(self, day: date) -> dict[str, Any]:
        return self.api.get_hydration_data(day.isoformat())

    def get_floors(self, day: date) -> dict[str, Any]:
        return self.api.get_floors(day.isoformat())

    def get_daily_intensity_minutes(self, day: date) -> dict[str, Any]:
        return self.api.get_intensity_minutes_data(day.isoformat())

    def get_hill_score(self, day: date) -> dict[str, Any]:
        return self.api.get_hill_score(day.isoformat())

    def get_endurance_score(self, day: date) -> dict[str, Any]:
        return self.api.get_endurance_score(day.isoformat())

    def get_all_day_stress(self, day: date) -> dict[str, Any]:
        return self.api.get_all_day_stress(day.isoformat())

    # ------------------------------------------------------------------
    # Range-based data fetchers
    # ------------------------------------------------------------------

    def get_activities(self, start: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        return self.api.get_activities(start, limit)

    def get_activities_by_date(
        self, start: date, end: date, activity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.api.get_activities_by_date(
            start.isoformat(), end.isoformat(), activity_type,
        )

    def get_weigh_ins(self, start: date, end: date) -> dict[str, Any]:
        return self.api.get_weigh_ins(start.isoformat(), end.isoformat())

    def get_daily_steps(self, start: date, end: date) -> list[dict[str, Any]]:
        return self.api.get_daily_steps(start.isoformat(), end.isoformat())

    def get_daily_sleep(self, start: date, end: date) -> list[dict[str, Any]]:
        return self.api.get_daily_sleep(start.isoformat(), end.isoformat())

    # ------------------------------------------------------------------
    # One-time / snapshot fetchers
    # ------------------------------------------------------------------

    def get_user_summary(self) -> dict[str, Any]:
        return self.api.get_user_summary()

    def get_body_battery(self) -> list[dict[str, Any]]:
        return self.api.get_body_battery()

    def get_max_metrics(self, day: date) -> dict[str, Any]:
        return self.api.get_max_metrics(day.isoformat())

    def get_personal_record(self) -> list[dict[str, Any]]:
        return self.api.get_personal_record()

    def get_devices(self) -> list[dict[str, Any]]:
        return self.api.get_devices()

    def get_device_settings(self, device_id: str) -> dict[str, Any]:
        return self.api.get_device_settings(device_id)

    def get_goals(self, goal_type: str = "all") -> list[dict[str, Any]]:
        return self.api.get_goals(goal_type)

    # ------------------------------------------------------------------
    # fetch_all() — comprehensive data fetch
    # ------------------------------------------------------------------

    def fetch_all(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Fetch all available Garmin data between start_date and end_date.

        Returns a dict keyed by data type. Each per-day data type maps
        to a list of daily records. Range and snapshot types return their
        native shape. Every call is wrapped in try/except so a single
        failure never aborts the sync.

        Args:
            start_date: First day to fetch (inclusive).
            end_date: Last day to fetch (inclusive).

        Returns:
            Dict mapping data-type name to raw API response data.
        """
        result: dict[str, Any] = {}

        # Per-day methods: call once for each day in [start_date, end_date]
        per_day_methods: list[tuple[str, str]] = [
            ("daily_stats", "get_daily_stats"),
            ("heart_rate", "get_heart_rate"),
            ("sleep", "get_sleep"),
            ("body_composition", "get_body_composition"),
            ("stress", "get_stress"),
            ("steps", "get_steps"),
            ("respiration", "get_respiration"),
            ("spo2", "get_spo2"),
            ("rhr", "get_rhr"),
            ("hrv", "get_hrv"),
            ("training_readiness", "get_training_readiness"),
            ("training_status", "get_training_status"),
            ("hydration", "get_daily_hydration"),
            ("floors", "get_floors"),
            ("intensity_minutes", "get_daily_intensity_minutes"),
            ("hill_score", "get_hill_score"),
            ("endurance_score", "get_endurance_score"),
            ("all_day_stress", "get_all_day_stress"),
        ]

        # Initialise lists
        for key, _ in per_day_methods:
            result[key] = []

        num_days = (end_date - start_date).days + 1
        for offset in range(num_days):
            day = start_date + timedelta(days=offset)
            for key, method_name in per_day_methods:
                try:
                    data = getattr(self, method_name)(day)
                    if data:
                        result[key].append(data)
                except Exception as exc:
                    logger.debug("Skipping %s for %s: %s", key, day, exc)

        # Range methods
        try:
            result["activities"] = self.get_activities_by_date(start_date, end_date)
        except Exception as exc:
            logger.debug("Skipping activities: %s", exc)
            result["activities"] = []

        try:
            result["weigh_ins"] = self.get_weigh_ins(start_date, end_date)
        except Exception as exc:
            logger.debug("Skipping weigh_ins: %s", exc)
            result["weigh_ins"] = {}

        try:
            result["daily_steps_range"] = self.get_daily_steps(start_date, end_date)
        except Exception as exc:
            logger.debug("Skipping daily_steps_range: %s", exc)
            result["daily_steps_range"] = []

        try:
            result["daily_sleep_range"] = self.get_daily_sleep(start_date, end_date)
        except Exception as exc:
            logger.debug("Skipping daily_sleep_range: %s", exc)
            result["daily_sleep_range"] = []

        # Snapshot / one-time methods
        try:
            result["max_metrics"] = self.get_max_metrics(end_date)
        except Exception as exc:
            logger.debug("Skipping max_metrics: %s", exc)
            result["max_metrics"] = {}

        try:
            result["personal_records"] = self.get_personal_record()
        except Exception as exc:
            logger.debug("Skipping personal_records: %s", exc)
            result["personal_records"] = []

        try:
            result["body_battery"] = self.get_body_battery()
        except Exception as exc:
            logger.debug("Skipping body_battery: %s", exc)
            result["body_battery"] = []

        try:
            result["devices"] = self.get_devices()
        except Exception as exc:
            logger.debug("Skipping devices: %s", exc)
            result["devices"] = []

        try:
            result["goals"] = self.get_goals()
        except Exception as exc:
            logger.debug("Skipping goals: %s", exc)
            result["goals"] = []

        try:
            result["user_summary"] = self.get_user_summary()
        except Exception as exc:
            logger.debug("Skipping user_summary: %s", exc)
            result["user_summary"] = {}

        logger.info(
            "fetch_all %s → %s: %d data types collected",
            start_date, end_date,
            sum(1 for v in result.values() if v),
        )
        return result

    # ------------------------------------------------------------------
    # Legacy fetch_range — kept for backward compatibility
    # ------------------------------------------------------------------

    def fetch_range(self, days_back: int = 7) -> dict[str, list[dict[str, Any]]]:
        """Fetch a limited set of data types for the last N days.

        Deprecated: prefer fetch_all(start_date, end_date).
        """
        end = date.today()
        start = end - timedelta(days=days_back - 1)
        full = self.fetch_all(start, end)
        return {
            "daily_stats": full.get("daily_stats", []),
            "sleep": full.get("sleep", []),
            "heart_rate": full.get("heart_rate", []),
            "stress": full.get("stress", []),
            "body_composition": full.get("body_composition", []),
            "activities": full.get("activities", []),
        }
