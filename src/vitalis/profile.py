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
    """Load a YAML file, returning empty dict if missing.

    Raises:
        yaml.YAMLError: If the file exists but cannot be parsed.  We
            deliberately do NOT swallow parse errors — silently returning
            ``{}`` would let downstream writers (e.g. ``update_from_garmin``)
            overwrite the user's curated profile with a fresh blank one.
    """
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed — profile load skipped")
        return {}
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


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

    profile.update(extract_garmin_profile_fields(raw_data))

    profile["last_synced"] = date.today().isoformat()

    save_profile(profile, path)
    return profile


def extract_garmin_profile_fields(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Extract Garmin-owned profile fields without reading or writing a profile.

    Supports both simplified legacy fixtures and the nested shapes returned by
    current Garmin Connect endpoints. The pure result is also used by the
    owner-side per-user cloud sync.
    """
    fields: dict[str, Any] = {}

    weight_rows: list[dict[str, Any]] = []
    body_comp = raw_data.get("body_composition", [])
    containers = body_comp if isinstance(body_comp, list) else [body_comp]
    for container in containers:
        if not isinstance(container, dict):
            continue
        nested = container.get("dateWeightList")
        if isinstance(nested, list):
            weight_rows.extend(row for row in nested if isinstance(row, dict))
        elif any(key in container for key in ("weight", "bodyFat", "bmi")):
            weight_rows.append(container)

    weigh_ins = raw_data.get("weigh_ins", {})
    if isinstance(weigh_ins, dict):
        for summary in weigh_ins.get("dailyWeightSummaries", []) or []:
            if isinstance(summary, dict) and isinstance(summary.get("latestWeight"), dict):
                weight_rows.append(summary["latestWeight"])

    if weight_rows:
        latest = sorted(
            weight_rows,
            key=lambda row: str(row.get("calendarDate") or row.get("date") or ""),
        )[-1]
        weight = latest.get("weight")
        if isinstance(weight, (int, float)) and weight > 0:
            fields["weight_kg"] = round(
                weight / 1000 if weight > 500 else weight,
                1,
            )
        body_fat = latest.get("bodyFat")
        if isinstance(body_fat, (int, float)):
            fields["body_fat_pct"] = round(body_fat, 1)
        bmi = latest.get("bmi")
        if isinstance(bmi, (int, float)):
            fields["bmi"] = round(bmi, 1)

    daily_stats = raw_data.get("daily_stats", [])
    if isinstance(daily_stats, list):
        valid_stats = [item for item in daily_stats if isinstance(item, dict)]
        if valid_stats:
            latest_stats = valid_stats[-1]
            rhr = latest_stats.get("restingHeartRate")
            if isinstance(rhr, (int, float)) and rhr > 0:
                fields["resting_heart_rate"] = int(rhr)

    generic_candidates: list[dict[str, Any]] = []
    max_metrics = raw_data.get("max_metrics", {})
    if isinstance(max_metrics, dict) and isinstance(max_metrics.get("generic"), dict):
        generic_candidates.append(max_metrics["generic"])
    training_status = raw_data.get("training_status", [])
    status_items = training_status if isinstance(training_status, list) else [training_status]
    for item in status_items:
        if not isinstance(item, dict):
            continue
        recent = item.get("mostRecentVO2Max")
        if isinstance(recent, dict) and isinstance(recent.get("generic"), dict):
            generic_candidates.append(recent["generic"])
    if generic_candidates:
        generic = generic_candidates[-1]
        vo2 = generic.get("vo2MaxPreciseValue") or generic.get("vo2MaxValue")
        if isinstance(vo2, (int, float)) and vo2 > 0:
            fields["vo2max"] = round(vo2, 1)
        fitness_age = generic.get("fitnessAge")
        if isinstance(fitness_age, (int, float)) and fitness_age > 0:
            fields["fitness_age"] = int(fitness_age)

    devices = raw_data.get("devices", [])
    if isinstance(devices, list) and devices:
        fields["devices"] = [
            {
                "name": device.get(
                    "productDisplayName",
                    device.get("deviceName", "unknown"),
                ),
                "type": device.get("deviceTypeName", ""),
            }
            for device in devices
            if isinstance(device, dict)
        ]

    return fields


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
