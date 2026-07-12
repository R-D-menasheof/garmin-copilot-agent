"""Build an immutable, user-scoped context packet for a weekly review.

Usage:
    python scripts/prepare_weekly_review.py --user-id <oid>
    python scripts/prepare_weekly_review.py --user-id <oid> --end 2026-07-10

The packet is the only input that weekly-report agents should use. This keeps
all specialists on the same date range and prevents accidental owner-data reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, timedelta

from _users import get_store, normalize_user_id, user_reports_directory


def _dump(value):
    """Convert an optional Pydantic model to a JSON-compatible value."""
    return value.model_dump(mode="json") if value is not None else None


def _sync_freshness(profile, start: date, end: date) -> tuple[str | None, str]:
    """Return the last sync date and its freshness for the report period."""
    raw = getattr(profile, "last_synced", None) if profile is not None else None
    if raw is None:
        return None, "unknown"
    try:
        synced = raw if isinstance(raw, date) else date.fromisoformat(str(raw)[:10])
    except ValueError:
        return str(raw), "unknown"
    if synced >= end:
        status = "fresh"
    elif synced >= start:
        status = "partial"
    else:
        status = "stale"
    return synced.isoformat(), status


def _has_biometric_metrics(value) -> bool:
    """Return whether one serialized daily record contains an actual metric.

    Mobile sync can create dated placeholders when Health Connect grants access
    but exposes no values. Metadata such as ``date`` and ``source`` must not
    inflate coverage; a legitimate numeric zero (for example zero steps) does
    count as data.
    """
    if not isinstance(value, dict):
        return False
    metadata_fields = {"date", "source"}
    for key, metric in value.items():
        if key in metadata_fields:
            continue
        if metric is not None and metric != "" and metric != [] and metric != {}:
            return True
    return False


def build_weekly_context(
    user_id: str,
    end: date,
    days: int = 7,
    store=None,
) -> dict:
    """Build one deterministic context packet from a user-scoped store."""
    if days < 1:
        raise ValueError("days must be at least 1")

    normalized_user_id = normalize_user_id(user_id)
    start = end - timedelta(days=days - 1)
    if store is None:
        store = get_store(normalized_user_id)

    combined = store.load_combined(start, end)
    sleep_entries = store.load_sleep_entries(start, end)
    summary_history = store.load_summary_history(limit=2)
    profile = store.load_profile()
    last_synced, sync_freshness = _sync_freshness(profile, start, end)

    biometrics = combined.get("biometrics", {})
    nutrition = combined.get("nutrition", {})
    biometric_days = sum(
        1 for value in biometrics.values() if _has_biometric_metrics(value)
    )
    nutrition_days = sum(1 for value in nutrition.values() if value)

    packet = {
        "schema_version": 1,
        "user_id": normalized_user_id,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": days,
        },
        "local_report_directory": str(user_reports_directory(normalized_user_id)),
        "profile": _dump(profile),
        "previous_summaries": [_dump(item) for item in summary_history],
        "biometrics": biometrics,
        "nutrition": nutrition,
        "sleep_entries": [_dump(item) for item in sleep_entries],
        "nutrition_goals": _dump(store.load_goals()),
        "goal_programs": [_dump(item) for item in store.load_goal_programs()],
        "active_training": _dump(store.load_active_training_program()),
        "recommendation_statuses": [
            _dump(item) for item in store.load_recommendation_statuses()
        ],
        "lab_trends": [_dump(item) for item in store.load_lab_trends()],
        "data_quality": {
            "expected_days": days,
            "biometric_days": biometric_days,
            "nutrition_days": nutrition_days,
            "missing_biometric_days": days - biometric_days,
            "missing_nutrition_days": days - nutrition_days,
            "has_profile": profile is not None,
            "has_previous_summary": bool(summary_history),
            "last_synced": last_synced,
            "sync_freshness": sync_freshness,
        },
    }
    canonical = json.dumps(
        packet,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    packet["context_sha256"] = hashlib.sha256(canonical).hexdigest()
    return packet


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Prepare a user-scoped weekly-review context packet.",
    )
    parser.add_argument("--user-id", required=True, help="Target user's Entra oid.")
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today(),
        help="Inclusive period end (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of inclusive days in the review period.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    packet = build_weekly_context(args.user_id, args.end, args.days)
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
