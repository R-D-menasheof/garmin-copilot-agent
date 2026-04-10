"""Read sleep entries from the Vitalis API.

Usage:
    python scripts/read_sleep.py                        # Last 7 days
    python scripts/read_sleep.py --from 2026-04-01 --to 2026-04-08

Used by the health-analyst agent during weekly review to check
sleep checklist compliance and rating trends.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

import httpx  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("vitalis.read_sleep")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(description="Read sleep entries from the Vitalis API.")
    p.add_argument("--from", dest="start", type=date.fromisoformat, help="Start date (YYYY-MM-DD)")
    p.add_argument("--to", dest="end", type=date.fromisoformat, help="End date (YYYY-MM-DD)")
    return p.parse_args(argv)


def fetch_sleep(
    start: date,
    end: date,
    api_url: str | None = None,
    api_key: str | None = None,
) -> list[dict]:
    """Fetch sleep entries for a date range."""
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    resp = httpx.get(
        f"{url}/v1/sleep/entries",
        params={"from": start.isoformat(), "to": end.isoformat()},
        headers={"x-api-key": key},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json().get("entries", [])


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    today = date.today()
    start = args.start or (today - timedelta(days=7))
    end = args.end or today

    try:
        entries = fetch_sleep(start, end)
        sys.stdout.write(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
        return 0
    except Exception as exc:
        logger.error("Failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
