"""Publish analysis summaries to the Vitalis API.

Usage:
    python scripts/publish_summary.py
    python scripts/publish_summary.py --date 2026-04-04

Reads a locally persisted AnalysisSummary from SummaryStore and publishes it to
POST /api/v1/summary so the mobile app can consume the latest weekly review.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Ensure src/ is importable
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

import httpx  # noqa: E402

from vitalis.models import AnalysisSummary  # noqa: E402
from vitalis.summary_store import SummaryStore  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.publish_summary")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Optional argument list override.

    Returns:
        Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Publish the latest or a specific Vitalis summary via the API.",
    )
    parser.add_argument(
        "--date",
        help="Specific summary date to publish (YYYY-MM-DD). Defaults to latest.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Publish all available summaries.",
    )
    return parser.parse_args(argv)


def send_summary(
    summary: AnalysisSummary,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Send a summary to the Vitalis API.

    Args:
        summary: Summary payload to publish.
        api_url: Base API URL. Defaults to VITALIS_API_URL.
        api_key: API key. Defaults to VITALIS_API_KEY.

    Returns:
        API response JSON.

    Raises:
        Exception: If the API returns an error status.
    """
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    resp = httpx.post(
        f"{url}/v1/summary",
        content=summary.model_dump_json(),
        headers={
            "x-api-key": key,
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def publish_summary(
    summary_date: date | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
    directory: Path | str | None = None,
) -> dict:
    """Load a summary from SummaryStore and publish it.

    Args:
        summary_date: Specific summary date to publish. If omitted, latest is used.
        api_url: Base API URL. Defaults to VITALIS_API_URL.
        api_key: API key. Defaults to VITALIS_API_KEY.
        directory: Optional summary directory override for tests.

    Returns:
        API response JSON.

    Raises:
        ValueError: If the requested summary does not exist.
    """
    store = SummaryStore(directory=directory)
    summary = store.load_by_date(summary_date) if summary_date else store.load_latest()

    if summary is None:
        raise ValueError("No summary available to publish")

    # Inject the full markdown report from the .md file
    md_path = store.directory / f"{summary.date.isoformat()}.md"
    if md_path.exists():
        summary = summary.model_copy(
            update={"report_markdown": md_path.read_text(encoding="utf-8")}
        )

    return send_summary(summary, api_url=api_url, api_key=api_key)


def publish_all(
    api_url: str | None = None,
    api_key: str | None = None,
    directory: Path | str | None = None,
) -> list[dict]:
    """Publish all available summaries.

    Args:
        api_url: Base API URL.
        api_key: API key.
        directory: Optional summary directory override.

    Returns:
        List of API responses.
    """
    store = SummaryStore(directory=directory)
    results: list[dict] = []
    for day in store.list_dates():
        logger.info("Publishing %s", day.isoformat())
        result = publish_summary(
            summary_date=day, api_url=api_url, api_key=api_key, directory=directory
        )
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)

    try:
        if args.all:
            results = publish_all()
            sys.stdout.write(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
            return 0
        summary_date = date.fromisoformat(args.date) if args.date else None
        result = publish_summary(summary_date=summary_date)
        sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        return 0
    except Exception as exc:
        logger.error("Failed to publish summary: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())