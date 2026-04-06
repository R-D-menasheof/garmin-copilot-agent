"""Set nutrition goals — CLI for the External Agent.

Usage:
    python scripts/set_goals.py --calories 2200 --protein 180 --carbs 250 --fat 70

Calls POST /api/v1/goals to set the current week's nutrition targets.
The Vitalis GHCP agent runs this via `execute` after weekly analysis.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.set_goals")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(
        description="Set weekly nutrition goals via the Vitalis API.",
    )
    p.add_argument(
        "--calories", type=int, required=True,
        help="Daily calorie target (kcal).",
    )
    p.add_argument(
        "--protein", type=float, required=True,
        help="Daily protein target (grams).",
    )
    p.add_argument(
        "--carbs", type=float, required=True,
        help="Daily carbs target (grams).",
    )
    p.add_argument(
        "--fat", type=float, required=True,
        help="Daily fat target (grams).",
    )
    return p.parse_args(argv)


def send_goals(
    calories: int,
    protein: float,
    carbs: float,
    fat: float,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Call POST /api/v1/goals to set nutrition targets.

    Args:
        calories: Daily calorie target.
        protein: Daily protein target (grams).
        carbs: Daily carbs target (grams).
        fat: Daily fat target (grams).
        api_url: Base API URL. Defaults to VITALIS_API_URL env var.
        api_key: API key. Defaults to VITALIS_API_KEY env var.

    Returns:
        API response dict.

    Raises:
        Exception: If the API returns an error status.
    """
    url = api_url or os.environ.get("VITALIS_API_URL", "http://localhost:7071/api")
    key = api_key or os.environ.get("VITALIS_API_KEY", "")

    payload = {
        "date": date.today().isoformat(),
        "calories_target": calories,
        "protein_g_target": protein,
        "carbs_g_target": carbs,
        "fat_g_target": fat,
        "set_by": "agent",
    }

    resp = httpx.post(
        f"{url}/v1/goals",
        content=json.dumps(payload),
        headers={
            "x-api-key": key,
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parse_args(argv)

    logger.info(
        "Setting goals: %d kcal, %.0fg protein, %.0fg carbs, %.0fg fat",
        args.calories, args.protein, args.carbs, args.fat,
    )

    try:
        result = send_goals(args.calories, args.protein, args.carbs, args.fat)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        logger.error("Failed to set goals: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
