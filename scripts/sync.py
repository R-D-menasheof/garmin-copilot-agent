"""Vitalis Sync CLI — fetch Garmin data from the command line.

Usage:
    python scripts/sync.py --days 7          # Last 7 days
    python scripts/sync.py --today           # Today only
    python scripts/sync.py --from 2026-01-01 --to 2026-01-31   # Date range

Data is saved to data/synced/<start>_to_<end>/ and profile.yaml
is updated with latest Garmin-sourced fields.

On first run (or when tokens expire), Garmin may request MFA.
The script will prompt you to enter the code sent to your email.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure src/ package is importable when running as a script
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

from vitalis.data_store import DataStore  # noqa: E402
from vitalis.garmin_client import GarminClient, GarminMFARequiredError  # noqa: E402
from vitalis.profile import update_from_garmin  # noqa: E402

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


def main(argv: list[str] | None = None) -> None:
    """Entry point for the sync CLI."""
    args = parse_args(argv)
    start_date, end_date = resolve_dates(args)

    logger.info("Syncing Garmin data: %s → %s", start_date, end_date)

    # Connect (with interactive MFA handling)
    client = GarminClient()
    try:
        client.connect()
    except GarminMFARequiredError as mfa_err:
        # Garmin requires 2FA — prompt user in terminal
        logger.info("Garmin requires MFA verification.")
        print(f"\n{mfa_err}")
        mfa_code = input("Enter the MFA code: ").strip()
        if not mfa_code:
            logger.error("No MFA code entered. Aborting.")
            sys.exit(1)
        client.connect(mfa_code=mfa_code, mfa_session_id=mfa_err.session_id)

    logger.info("Connected to Garmin Connect")

    # Fetch all data types
    raw = client.fetch_all(start_date, end_date)
    types_with_data = sum(
        1 for v in raw.values()
        if v and (isinstance(v, list) and len(v) > 0 or isinstance(v, dict) and len(v) > 0)
    )
    logger.info("Fetched %d data types with data", types_with_data)

    # Save to date-stamped folder
    store = DataStore()
    folder = store.save_sync(start_date, end_date, raw)
    logger.info("Data saved to %s", folder)

    # Update profile with Garmin-sourced fields
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
