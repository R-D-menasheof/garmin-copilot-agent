"""Read recommendation adoption statuses from the Vitalis API.

Usage:
    python scripts/read_recommendation_status.py

Calls GET /api/v1/recommendations/status and prints JSON to stdout.
The health-analyst agent uses this during Phase 1 to check adoption.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

import httpx  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.read_recommendation_status")


def fetch_statuses(
    api_url: str | None = None,
    api_key: str | None = None,
) -> list[dict]:
    """Fetch recommendation statuses from the API.

    Returns:
        List of status dicts with rec_id, status, updated_at.
    """
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    resp = httpx.get(
        f"{url}/v1/recommendations/status",
        headers={"x-api-key": key},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("statuses", [])


def main() -> int:
    """CLI entry point."""
    try:
        statuses = fetch_statuses()
        sys.stdout.write(json.dumps(statuses, indent=2, ensure_ascii=False) + "\n")
        return 0
    except Exception as exc:
        logger.error("Failed to read recommendation statuses: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
