"""Add a timeline event to the Vitalis API.

Usage:
    python scripts/add_timeline_event.py --date 2026-01-18 --category medical \
        --title "כבד שומני" --detail "אולטרסאונד בטן — כבד שומני קל" --severity warning

Used by the health-analyst agent to populate the health timeline.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

import httpx  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("vitalis.add_timeline_event")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(description="Add a health timeline event.")
    p.add_argument("--date", required=True, help="Event date (YYYY-MM-DD)")
    p.add_argument("--category", required=True, choices=["medical", "milestone", "medication", "lifestyle"])
    p.add_argument("--title", required=True, help="Event title in Hebrew")
    p.add_argument("--detail", default="", help="Event detail in Hebrew")
    p.add_argument("--severity", default="info", choices=["info", "warning", "critical", "positive"])
    p.add_argument("--source", default="agent")
    return p.parse_args(argv)


def add_event(
    event_data: dict,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    """POST a timeline event to the API."""
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    resp = httpx.post(
        f"{url}/v1/timeline",
        content=json.dumps(event_data, ensure_ascii=False),
        headers={"x-api-key": key, "Content-Type": "application/json"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    event_data = {
        "date": args.date,
        "category": args.category,
        "title_he": args.title,
        "detail_he": args.detail,
        "severity": args.severity,
        "source": args.source,
    }
    try:
        result = add_event(event_data)
        sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        return 0
    except Exception as exc:
        logger.error("Failed to add timeline event: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
