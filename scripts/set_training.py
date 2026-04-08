"""Set a training program via the Vitalis API.

Usage:
    python scripts/set_training.py --file training_plan.json

Used by the fitness-coach agent to push structured training programs.
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
logger = logging.getLogger("vitalis.set_training")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(description="Set a training program.")
    p.add_argument("--file", help="JSON file with TrainingProgram data")
    p.add_argument("--json", help="Inline JSON string")
    return p.parse_args(argv)


def set_program(
    program_data: dict,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    """POST a training program to the API."""
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    resp = httpx.post(
        f"{url}/v1/training",
        content=json.dumps(program_data, ensure_ascii=False),
        headers={"x-api-key": key, "Content-Type": "application/json"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    try:
        if args.file:
            program_data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        elif args.json:
            program_data = json.loads(args.json)
        else:
            logger.error("Provide --file or --json")
            return 1

        result = set_program(program_data)
        sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        return 0
    except Exception as exc:
        logger.error("Failed to set training program: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
