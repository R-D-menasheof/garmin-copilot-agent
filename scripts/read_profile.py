"""Read a user's cloud profile for owner-side analysis (Phase 6.2).

Usage:
    python scripts/read_profile.py --user-id <oid>

Prints the user's ``users/{user_id}/profile.json`` as JSON on stdout (or
``null`` if none exists). The Vitalis health-analyst agent runs this at the
start of a per-user analysis (the Phase-1 "context" step) to load DOB, sex,
height, goals, medications, and supplements before reading the metrics.
"""

from __future__ import annotations

import argparse
import json
import sys


def read_profile(user_id: str, store=None) -> dict | None:
    """Load one user's cloud profile as a JSON-able dict (or None).

    Args:
        user_id: Target user's id (Entra oid).
        store: Optional pre-built store (for tests). Falls back to get_store.

    Returns:
        The profile as a dict, or None if the user has no profile blob.
    """
    if store is None:
        from _users import get_store  # lazy: pulls in api/ + azure only when used

        store = get_store(user_id)
    profile = store.load_profile()
    return profile.model_dump(mode="json") if profile is not None else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Read a user's cloud profile as JSON.",
    )
    parser.add_argument("--user-id", required=True, help="Target user's oid.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Hebrew output safe when captured
    args = parse_args(argv)
    profile = read_profile(args.user_id)
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
