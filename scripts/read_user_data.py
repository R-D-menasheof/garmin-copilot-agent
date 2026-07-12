"""Read a user's full cloud health data for owner-side analysis (Phase 6.2).

Usage:
    python scripts/read_user_data.py --user-id <oid>
    python scripts/read_user_data.py --user-id <oid> --days 30

Aggregates the user's cloud profile, recent summaries, meals, goals,
recommendations, lab trends, training, goal programs, and biometrics into a
single JSON document on stdout. The Vitalis health-analyst agent reads this to
produce a personalised report for that user (the Phase-1 "context" step, but
sourced from the cloud per user_id instead of the owner's local data).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

from _users import get_store


def _dump(obj):
    """model_dump an optional Pydantic model to a JSON-able value (or None)."""
    return obj.model_dump(mode="json") if obj is not None else None


def collect_user_data(store, days: int = 30) -> dict:
    """Aggregate one user's cloud health data into a JSON-able dict.

    Args:
        store: A ``BlobStore`` (or compatible) scoped to the target user.
        days: Size of the trailing biometrics window, in days.

    Returns:
        A dict with keys: profile, summaries, recent_meals, goals,
        recommendations, lab_trends, active_training, goal_programs, biometrics.
    """
    end = date.today()
    start = end - timedelta(days=days - 1)
    biometrics = store.load_biometrics_range(start, end)

    return {
        "profile": _dump(store.load_profile()),
        "summaries": [_dump(s) for s in store.load_summary_history(limit=8)],
        "recent_meals": [_dump(m) for m in store.load_recent_meals(limit=30)],
        "goals": _dump(store.load_goals()),
        "recommendations": [_dump(r) for r in store.load_recommendation_statuses()],
        "lab_trends": [_dump(t) for t in store.load_lab_trends()],
        "active_training": _dump(store.load_active_training_program()),
        "goal_programs": [_dump(p) for p in store.load_goal_programs()],
        "biometrics": {
            day.isoformat(): _dump(rec) for day, rec in sorted(biometrics.items())
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Read a user's full cloud health data as JSON.",
    )
    parser.add_argument("--user-id", required=True, help="Target user's oid.")
    parser.add_argument(
        "--days", type=int, default=30, help="Biometrics window in days (default 30)."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Hebrew output safe when captured
    args = parse_args(argv)
    data = collect_user_data(get_store(args.user_id), days=args.days)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
