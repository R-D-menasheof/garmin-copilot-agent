"""Read nutrition data — CLI for the External Agent.

Usage:
    python scripts/read_nutrition.py                         # Last 7 days
    python scripts/read_nutrition.py --from 2026-03-28 --to 2026-04-04

Calls GET /api/v1/combined and prints the JSON response to stdout.
The Vitalis GHCP agent runs this via `execute` during weekly reviews.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure src/ is importable
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

import httpx  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.read_nutrition")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(
        description="Read combined nutrition + biometrics data from the Vitalis API.",
    )
    p.add_argument(
        "--from",
        dest="start",
        type=date.fromisoformat,
        help="Start date (YYYY-MM-DD). Defaults to 7 days ago.",
    )
    p.add_argument(
        "--to",
        dest="end",
        type=date.fromisoformat,
        help="End date (YYYY-MM-DD). Defaults to today.",
    )
    return p.parse_args(argv)


def resolve_dates(args: argparse.Namespace) -> tuple[date, date]:
    """Resolve CLI args into a (start_date, end_date) tuple.

    Defaults to last 7 days if no args provided.
    """
    today = date.today()
    end = args.end or today
    start = args.start or (today - timedelta(days=6))
    return start, end


def fetch_combined(
    start: date,
    end: date,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Call GET /api/v1/combined and return the JSON response.

    Args:
        start: Start date for the range.
        end: End date for the range.
        api_url: Base API URL. Defaults to VITALIS_API_URL env var.
        api_key: API key. Defaults to VITALIS_API_KEY env var.

    Returns:
        Combined nutrition + biometrics dict.

    Raises:
        Exception: If the API returns an error status.
    """
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    resp = httpx.get(
        f"{url}/v1/combined",
        params={"from": start.isoformat(), "to": end.isoformat()},
        headers={"x-api-key": key},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parse_args(argv)
    start, end = resolve_dates(args)

    logger.info("Reading combined data: %s → %s", start, end)

    try:
        data = fetch_combined(start, end)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        logger.error("Failed to read nutrition data: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
