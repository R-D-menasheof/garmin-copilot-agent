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
import subprocess
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

_DEFAULT_RESOURCE_GROUP = "rg-vitalis"
_DEFAULT_FUNCTION_APP = "func-vitalis-api"


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
    parser.add_argument(
        "--user-id",
        help=(
            "Owner op: publish directly to this user's cloud storage "
            "(BlobStore, bypasses the HTTP API). Requires "
            "AZURE_STORAGE_CONNECTION_STRING."
        ),
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


def publish_summary_direct(
    user_id: str,
    summary_date: date | None = None,
    directory: Path | str | None = None,
    store=None,
) -> dict:
    """Publish a summary directly to a user's cloud storage (owner op).

    Bypasses the HTTP API and writes straight to ``BlobStore(user_id=...)``
    using the owner's master storage key. Used for per-user analysis, where the
    owner authors a summary for a given user locally and pushes it to that
    user's ``users/{user_id}/summaries/`` area.

    Args:
        user_id: Target user's id (Entra oid).
        summary_date: Specific summary date to publish. Latest if omitted.
        directory: Optional local summary directory override.
        store: Optional pre-built store (for tests). Falls back to get_store.

    Returns:
        Status dict with the published user_id and date.

    Raises:
        ValueError: If the requested summary does not exist.
    """
    from _users import normalize_user_id, user_reports_directory

    user_id = normalize_user_id(user_id)
    expected_directory = user_reports_directory(user_id)
    summary_store = SummaryStore(directory=directory or expected_directory)
    summary = (
        summary_store.load_by_date(summary_date)
        if summary_date
        else summary_store.load_latest()
    )
    if summary is None:
        raise ValueError("No summary available to publish")
    if summary.target_user_id != user_id:
        raise ValueError(
            "Summary target_user_id does not match publication user_id: "
            f"{summary.target_user_id!r} != {user_id!r}"
        )
    if not summary.context_sha256 or len(summary.context_sha256) != 64:
        raise ValueError("Summary is missing a valid context_sha256")

    md_path = summary_store.directory / f"{summary.date.isoformat()}.md"
    if md_path.exists():
        summary = summary.model_copy(
            update={"report_markdown": md_path.read_text(encoding="utf-8")}
        )

    if store is None:
        from _users import get_store  # lazy: pulls in api/ + azure only when used

        store = get_store(user_id)
    existing = store.load_latest_summary()
    if (
        existing is not None
        and existing.date == summary.date
        and existing.model_dump(mode="json") == summary.model_dump(mode="json")
    ):
        return {
            "status": "unchanged",
            "user_id": user_id,
            "date": summary.date.isoformat(),
            "notified": 0,
        }
    store.save_summary(summary)

    notified = _notify_report_ready(store, summary.date.isoformat())
    return {
        "status": "ok",
        "user_id": user_id,
        "date": summary.date.isoformat(),
        "notified": notified,
    }


def _notify_report_ready(store, date_iso: str) -> int:
    """Best-effort 'report ready' push. Never fails the publish."""
    try:
        from shared.notifications import NotificationSender, notify_report_ready

        sender = NotificationSender()
        if not sender.configured:
            sender = _azure_notification_sender(NotificationSender)
        return notify_report_ready(store, date_iso, sender=sender)
    except Exception as exc:  # best effort — notifications must not block publish
        logger.warning("Report-ready notification failed: %s", exc)
        return 0


def _azure_notification_sender(sender_cls):
    """Build a notification sender from Azure Function app settings.

    The service-account JSON is captured in memory only and is never logged or
    persisted locally.
    """
    resource_group = os.environ.get(
        "VITALIS_AZURE_RESOURCE_GROUP",
        _DEFAULT_RESOURCE_GROUP,
    )
    function_app = os.environ.get(
        "VITALIS_FUNCTION_APP",
        _DEFAULT_FUNCTION_APP,
    )
    result = subprocess.run(
        [
            "az",
            "functionapp",
            "config",
            "appsettings",
            "list",
            "-g",
            resource_group,
            "-n",
            function_app,
            "-o",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    settings = {
        item["name"]: item.get("value", "")
        for item in json.loads(result.stdout)
    }
    project_id = settings.get("FCM_PROJECT_ID")
    raw_service_account = settings.get("FCM_SERVICE_ACCOUNT_JSON")
    if not project_id or not raw_service_account:
        raise RuntimeError("Azure FCM settings are incomplete")
    return sender_cls(
        project_id=project_id,
        service_account=json.loads(raw_service_account),
    )


def publish_all_direct(
    user_id: str,
    directory: Path | str | None = None,
    store=None,
) -> list[dict]:
    """Publish all local summaries directly to a user's cloud storage."""
    summary_store = SummaryStore(directory=directory)
    if store is None:
        from _users import get_store  # lazy

        store = get_store(user_id)
    results: list[dict] = []
    for day in summary_store.list_dates():
        logger.info("Publishing %s -> user %s", day.isoformat(), user_id)
        results.append(
            publish_summary_direct(
                user_id, summary_date=day, directory=directory, store=store
            )
        )
    return results


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)

    try:
        if args.user_id:
            if args.all:
                results = publish_all_direct(args.user_id)
                sys.stdout.write(
                    json.dumps(results, indent=2, ensure_ascii=False) + "\n"
                )
                return 0
            summary_date = date.fromisoformat(args.date) if args.date else None
            result = publish_summary_direct(args.user_id, summary_date=summary_date)
            sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
            return 0
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
