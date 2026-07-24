"""List registered cloud users (owner op, Phase 6.1).

Usage:
    python scripts/list_users.py

Prints one line per registered user: ``<user_id>  '<display_name>'  <email>``.
Lets the owner map opaque Entra oids to real people for per-user analysis.
"""

from __future__ import annotations

import argparse
import json
import sys
from uuid import UUID

from _users import list_users


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(description="List registered Vitalis cloud users.")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    p.add_argument(
        "--entra-only",
        action="store_true",
        help="Exclude legacy non-UUID user keys (keep only Entra oids).",
    )
    return p.parse_args(argv)


def _is_entra_oid(user_id: str) -> bool:
    """True if ``user_id`` is a valid Entra object id (UUID)."""
    try:
        UUID(user_id)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    users = list_users()
    if args.entra_only:
        users = [u for u in users if _is_entra_oid(u["user_id"])]

    if args.json:
        print(json.dumps(users, ensure_ascii=False))
        return 0

    if not users:
        print("(no users found)")
        return 0
    for user in users:
        print(f"{user['user_id']}  {user['display_name']!r}  {user['email']}")
    print(f"\n{len(users)} user(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
