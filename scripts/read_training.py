"""Read active training program from the Vitalis API.

Usage:
    python scripts/read_training.py

Used by the health-analyst agent during weekly review to check
training compliance and update the program.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("vitalis.read_training")


def fetch_training(
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict | None:
    """Fetch active training program from the API."""
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    resp = httpx.get(
        f"{url}/v1/training/active",
        headers={"x-api-key": key},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json().get("program")


def main() -> int:
    """CLI entry point."""
    try:
        program = fetch_training()
        sys.stdout.write(json.dumps(program, indent=2, ensure_ascii=False) + "\n")
        return 0
    except Exception as exc:
        logger.error("Failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
