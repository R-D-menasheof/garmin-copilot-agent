"""User profile — SSOT for personal health profile data.

Manages a YAML-based profile at ``data/profile.yaml`` combining
manually entered fields (goals, injuries, dietary preferences) with
auto-synced Garmin data (weight, VO2max, fitness age, devices).
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PROFILE = _PROJECT_ROOT / "data" / "profile.yaml"

# Fields that should be auto-synced from Garmin data
_GARMIN_AUTO_FIELDS = {
    "weight_kg",
    "body_fat_pct",
    "bmi",
    "vo2max",
    "fitness_age",
    "resting_heart_rate",
    "devices",
    "last_synced",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning empty dict if missing/invalid."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed — profile load skipped")
        return {}
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("Could not read profile %s: %s", path, exc)
        return {}


def _save_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write a dict to YAML."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed — profile save skipped")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_profile(path: str | Path | None = None) -> dict[str, Any]:
    """Load the user profile.

    Args:
        path: Override path to the YAML file.

    Returns:
        Profile dict with both manual and auto-synced fields.
    """
    p = Path(path) if path else _DEFAULT_PROFILE
    return _load_yaml(p)


def save_profile(profile: dict[str, Any], path: str | Path | None = None) -> None:
    """Save the user profile.

    Args:
        profile: Full profile dict to persist.
        path: Override path to the YAML file.
    """
    p = Path(path) if path else _DEFAULT_PROFILE
    _save_yaml(p, profile)
    logger.info("Profile saved to %s", p)


def update_from_garmin(
    raw_data: dict[str, Any],
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Update auto-syncable profile fields from raw Garmin data.

    Reads current profile, updates Garmin-sourced fields, saves, and
    returns the updated profile.

    Args:
        raw_data: Full sync result dict from ``GarminClient.fetch_all()``.
        path: Override path to the YAML file.

    Returns:
        Updated profile dict.
    """
    profile = load_profile(path)

    # Extract weight / body-fat from body_composition
    body_comp = raw_data.get("body_composition", [])
    if body_comp:
        latest = body_comp[-1] if isinstance(body_comp, list) else body_comp
        if isinstance(latest, dict):
            weight = latest.get("weight")
            if weight and isinstance(weight, (int, float)) and weight > 0:
                # Garmin API returns grams
                profile["weight_kg"] = round(weight / 1000, 1) if weight > 500 else round(weight, 1)
            if latest.get("bodyFat"):
                profile["body_fat_pct"] = round(latest["bodyFat"], 1)
            if latest.get("bmi"):
                profile["bmi"] = round(latest["bmi"], 1)

    # Extract resting heart rate from daily stats
    daily_stats = raw_data.get("daily_stats", [])
    if daily_stats and isinstance(daily_stats, list):
        latest_stats = daily_stats[-1]
        if isinstance(latest_stats, dict):
            rhr = latest_stats.get("restingHeartRate")
            if rhr:
                profile["resting_heart_rate"] = rhr

    # Extract VO2max / fitness age from max_metrics
    max_metrics = raw_data.get("max_metrics", {})
    if isinstance(max_metrics, dict):
        generic = max_metrics.get("generic", {})
        if isinstance(generic, dict):
            vo2 = generic.get("vo2MaxPreciseValue") or generic.get("vo2MaxValue")
            if vo2:
                profile["vo2max"] = round(vo2, 1)
            fa = generic.get("fitnessAge")
            if fa:
                profile["fitness_age"] = fa

    # Devices
    devices = raw_data.get("devices", [])
    if devices and isinstance(devices, list):
        profile["devices"] = [
            {
                "name": d.get("productDisplayName", d.get("deviceName", "unknown")),
                "type": d.get("deviceTypeName", ""),
            }
            for d in devices
            if isinstance(d, dict)
        ]

    profile["last_synced"] = date.today().isoformat()

    save_profile(profile, path)
    return profile


def create_default_profile(path: str | Path | None = None) -> dict[str, Any]:
    """Create a default profile template if none exists.

    Returns:
        The profile dict (either existing or newly created).
    """
    p = Path(path) if path else _DEFAULT_PROFILE
    if p.exists():
        return load_profile(p)

    default = {
        "name": "",
        "age": None,
        "sex": "",
        "height_cm": None,
        "goals": [
            "# List your health and fitness goals here",
            "# e.g., 'Run a half marathon', 'Lose 5kg', 'Sleep 7+ hours'",
        ],
        "injuries": [],
        "dietary_preferences": [],
        "notes": "",
        "current_medications": [],
        # Auto-synced from Garmin (populated by update_from_garmin)
        "weight_kg": None,
        "body_fat_pct": None,
        "bmi": None,
        "vo2max": None,
        "fitness_age": None,
        "resting_heart_rate": None,
        "devices": [],
        "last_synced": None,
    }
    save_profile(default, p)
    logger.info("Created default profile at %s", p)
    return default
