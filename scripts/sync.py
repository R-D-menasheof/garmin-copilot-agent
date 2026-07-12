"""Vitalis Sync CLI — fetch Garmin data from the command line.

Usage:
    python scripts/sync.py --days 7          # Last 7 days
    python scripts/sync.py --today           # Today only
    python scripts/sync.py --from 2026-01-01 --to 2026-01-31   # Date range
    python scripts/sync.py --user-id <oid> --days 7  # Isolated cloud user

Data is saved to data/synced/<start>_to_<end>/ and profile.yaml
is updated with latest Garmin-sourced fields.

With ``--user-id``, raw data and OAuth tokens are isolated under
``data/users/<oid>/`` and daily biometrics/profile fields are merged into that
user's Azure Blob area. The owner's Garmin credentials and tokens are never
used as a fallback. On first login the password is read securely and is not
stored; only Garmin OAuth tokens are persisted.

On first run (or when tokens expire), Garmin may request MFA.
The script will prompt you to enter the code sent to your email.
"""

# pylint: disable=import-error,wrong-import-position

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure src/ package is importable when running as a script
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

from vitalis.data_store import DataStore  # noqa: E402
from vitalis.garmin_biometrics import (  # noqa: E402
    extract_garmin_biometrics,
    merge_biometrics_records,
)
from vitalis.garmin_client import GarminClient, GarminMFARequiredError  # noqa: E402
from vitalis.profile import extract_garmin_profile_fields, update_from_garmin  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.sync")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(
        description="Sync Garmin Connect data to local storage.",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--days",
        type=int,
        help="Fetch the last N days (including today).",
    )
    group.add_argument(
        "--today",
        action="store_true",
        help="Fetch today only.",
    )
    group.add_argument(
        "--from",
        dest="start",
        type=date.fromisoformat,
        help="Start date (YYYY-MM-DD). Requires --to.",
    )
    p.add_argument(
        "--to",
        dest="end",
        type=date.fromisoformat,
        help="End date (YYYY-MM-DD). Defaults to today if --from is set.",
    )
    p.add_argument(
        "--user-id",
        default=None,
        help=(
            "Target cloud user's Entra oid. Uses isolated Garmin tokens and "
            "data/users/<oid>/synced; never the owner's Garmin credentials."
        ),
    )
    p.add_argument(
        "--non-interactive",
        action="store_true",
        help=(
            "Never prompt for credentials or MFA. Fail fast when stored tokens "
            "are missing or invalid. Intended for scheduled automation."
        ),
    )
    return p.parse_args(argv)


def resolve_dates(args: argparse.Namespace) -> tuple[date, date]:
    """Resolve CLI args into a (start_date, end_date) tuple."""
    today = date.today()
    if args.today:
        return today, today
    if args.days:
        return today - timedelta(days=args.days - 1), today
    if args.start:
        end = args.end or today
        if end < args.start:
            raise ValueError("--to must not be before --from")
        return args.start, end
    raise ValueError("No date range specified")


def _connect_with_mfa(client: GarminClient, interactive: bool = True) -> None:
    """Connect one client and complete Garmin MFA in the same process."""
    try:
        client.connect()
    except GarminMFARequiredError as mfa_err:
        if not interactive:
            raise RuntimeError(
                "Garmin MFA is required; refresh this user's tokens interactively"
            ) from mfa_err
        logger.info("Garmin requires MFA verification.")
        print(f"\n{mfa_err}")
        mfa_code = input("Enter the MFA code: ").strip()
        if not mfa_code:
            logger.error("No MFA code entered. Aborting.")
            sys.exit(1)
        client.connect(mfa_code=mfa_code, mfa_session_id=mfa_err.session_id)


def _user_client(token_dir: Path, interactive: bool = True) -> GarminClient:
    """Connect a user-isolated client, prompting only when tokens are absent/invalid."""
    client = GarminClient(
        tokenstore=str(token_dir),
        use_env_credentials=False,
    )
    try:
        _connect_with_mfa(client, interactive=interactive)
        return client
    except ValueError as exc:
        if "credentials not configured" not in str(exc):
            raise
        if not interactive:
            raise RuntimeError(
                "Stored Garmin tokens are missing or invalid; "
                "run an interactive sync for this user first"
            ) from exc

    print("\nGarmin login is required once for this user.")
    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password (not stored): ")
    if not email or not password:
        raise ValueError("Garmin email and password are required for first login")
    client = GarminClient(
        email=email,
        password=password,
        tokenstore=str(token_dir),
        use_env_credentials=False,
    )
    _connect_with_mfa(client, interactive=interactive)
    return client


def _save_user_cloud_data(
    user_id: str,
    start_date: date,
    end_date: date,
    raw: dict,
) -> tuple[int, dict]:
    """Merge Garmin daily metrics and profile fields into one user's cloud area."""
    from _users import get_store

    store = get_store(user_id)
    existing = store.load_biometrics_range(start_date, end_date)
    biometrics = extract_garmin_biometrics(raw)
    for day, record in biometrics.items():
        store.save_biometrics(
            day,
            merge_biometrics_records(existing.get(day), record),
        )

    profile = store.load_profile()
    profile_fields = extract_garmin_profile_fields(raw)
    if profile is not None:
        merged_profile = profile.model_dump(mode="python")
        merged_profile.update(profile_fields)
        merged_profile["last_synced"] = end_date.isoformat()
        store.save_profile(type(profile).model_validate(merged_profile))
    return len(biometrics), profile_fields


def main(argv: list[str] | None = None) -> None:
    """Entry point for owner or explicitly scoped cloud-user Garmin sync."""
    args = parse_args(argv)
    start_date, end_date = resolve_dates(args)
    user_id = args.user_id

    logger.info("Syncing Garmin data: %s → %s", start_date, end_date)

    if user_id:
        from _users import (
            normalize_user_id,
            user_garmin_sync_directory,
            user_garmin_token_directory,
        )

        user_id = normalize_user_id(user_id)
        token_dir = user_garmin_token_directory(user_id)
        store = DataStore(base_dir=user_garmin_sync_directory(user_id))
        client = _user_client(token_dir, interactive=not args.non_interactive)
    else:
        store = DataStore()
        client = GarminClient()
        _connect_with_mfa(client)

    logger.info("Connected to Garmin Connect")

    # Fetch all data types
    raw = client.fetch_all(start_date, end_date)
    types_with_data = sum(
        1 for v in raw.values()
        if v and (isinstance(v, list) and len(v) > 0 or isinstance(v, dict) and len(v) > 0)
    )
    logger.info("Fetched %d data types with data", types_with_data)

    # Save to date-stamped folder
    folder = store.save_sync(start_date, end_date, raw)
    logger.info("Data saved to %s", folder)

    if user_id:
        days_saved, profile_fields = _save_user_cloud_data(
            user_id,
            start_date,
            end_date,
            raw,
        )
        logger.info(
            "Cloud updated for %s (%d biometric days; weight=%s, rhr=%s, vo2max=%s)",
            user_id,
            days_saved,
            profile_fields.get("weight_kg"),
            profile_fields.get("resting_heart_rate"),
            profile_fields.get("vo2max"),
        )
    else:
        profile = update_from_garmin(raw)
        logger.info(
            "Profile updated (weight=%s, rhr=%s, vo2max=%s)",
            profile.get("weight_kg"),
            profile.get("resting_heart_rate"),
            profile.get("vo2max"),
        )

    logger.info("Sync complete ✓")


if __name__ == "__main__":
    main()
