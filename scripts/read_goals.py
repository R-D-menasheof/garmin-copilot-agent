"""Read goal programs from the Vitalis API.

Usage:
    python scripts/read_goals.py

Used by the health-analyst agent during weekly review to check
goal progress and update milestones.
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
logger = logging.getLogger("vitalis.read_goals")


def fetch_goals(
    api_url: str | None = None,
    api_key: str | None = None,
) -> list[dict]:
    """Fetch all goal programs from the API."""
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    resp = httpx.get(
        f"{url}/v1/goals/programs",
        headers={"x-api-key": key},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json().get("programs", [])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(description="Read goal programs from the Vitalis API.")
    p.add_argument(
        "--user-id",
        help=(
            "Owner op: read directly from this user's cloud storage "
            "(BlobStore, bypasses the HTTP API). Requires "
            "AZURE_STORAGE_CONNECTION_STRING."
        ),
    )
    return p.parse_args(argv)


def read_goals_direct(user_id: str, store=None) -> list[dict]:
    """Read goal programs directly from a user's cloud store (owner op)."""
    if store is None:
        from _users import get_store  # lazy: pulls in api/ + azure only when used

        store = get_store(user_id)
    return [program.model_dump(mode="json") for program in store.load_goal_programs()]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        if args.user_id:
            programs = read_goals_direct(args.user_id)
        else:
            programs = fetch_goals()
        sys.stdout.write(json.dumps(programs, indent=2, ensure_ascii=False) + "\n")
        return 0
    except Exception as exc:
        logger.error("Failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
