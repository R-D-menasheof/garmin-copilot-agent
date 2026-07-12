"""Seed the owner's cloud Profile from the local ``data/profile.yaml``.

One-time (idempotent) helper: reads the agent-side profile and writes it to
``users/{owner_id}/profile.json`` so the mobile app shows the real profile.

SAFETY
- Reads ``data/profile.yaml`` — never modifies it.
- Preserves any existing cloud ``email`` (captured from SSO on first login),
  since the YAML has no email field.
- Marks ``onboarded=True`` (the owner already has a complete profile).

Usage::

    python scripts/push_profile.py --owner-id roei            # dry-run preview
    python scripts/push_profile.py --owner-id roei --apply    # write to cloud
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))
sys.path.insert(0, str(_project_root / "api"))

import yaml  # noqa: E402

from vitalis.models import (  # noqa: E402
    Device,
    HealthLogEntry,
    Medication,
    Profile,
    Supplement,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.push_profile")


def _iso(value):
    """Coerce a value to an ISO string (PyYAML parses ISO dates to date objects)."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _medication(raw: dict) -> Medication:
    return Medication(
        name=raw.get("name", ""),
        type=raw.get("type", ""),
        dose=raw.get("dose", ""),
        frequency=raw.get("frequency", ""),
        # profile.yaml uses 'for'; the model calls it 'purpose'.
        purpose=raw.get("purpose") or raw.get("for", ""),
        since=_iso(raw.get("since")),
        stopped=_iso(raw.get("stopped")),
        note=raw.get("note", ""),
    )


def _supplement(raw: dict) -> Supplement:
    return Supplement(
        name=raw.get("name", ""),
        dosage=raw.get("dosage", ""),
        timing=raw.get("timing", ""),
        since=_iso(raw.get("since")),
        stopped=_iso(raw.get("stopped")),
        note=raw.get("note", ""),
    )


def _health_entry(raw: dict) -> HealthLogEntry:
    return HealthLogEntry(date=raw["date"], note=raw.get("note", ""))


def _device(raw: dict) -> Device:
    return Device(name=raw.get("name", ""), type=raw.get("type", ""))


def build_profile(data: dict) -> Profile:
    """Map a ``profile.yaml`` dict to the cloud :class:`Profile` model.

    Args:
        data: Parsed profile.yaml contents.

    Returns:
        A fully populated Profile with ``onboarded=True``.
    """
    return Profile(
        display_name=data.get("name", ""),
        date_of_birth=data.get("date_of_birth"),
        age=data.get("age"),
        sex=data.get("sex"),
        height_cm=data.get("height_cm"),
        goals=list(data.get("goals") or []),
        injuries=list(data.get("injuries") or []),
        dietary_preferences=list(data.get("dietary_preferences") or []),
        notes=data.get("notes", "") or "",
        current_medications=[_medication(m) for m in (data.get("current_medications") or [])],
        supplements=[_supplement(s) for s in (data.get("supplements") or [])],
        health_log=[_health_entry(h) for h in (data.get("health_log") or [])],
        weight_kg=data.get("weight_kg"),
        body_fat_pct=data.get("body_fat_pct"),
        bmi=data.get("bmi"),
        vo2max=data.get("vo2max"),
        fitness_age=data.get("fitness_age"),
        resting_heart_rate=data.get("resting_heart_rate"),
        devices=[_device(d) for d in (data.get("devices") or [])],
        last_synced=_iso(data.get("last_synced")),
        onboarded=True,
    )


# ── CLI plumbing ───────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the owner's cloud profile from data/profile.yaml.",
    )
    parser.add_argument("--owner-id", required=True, help="User id (e.g. 'roei').")
    parser.add_argument(
        "--apply", action="store_true",
        help="Write to cloud. Without this flag, only preview.",
    )
    parser.add_argument(
        "--profile", default=str(_project_root / "data" / "profile.yaml"),
        help="Path to profile.yaml (default: data/profile.yaml).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    with open(args.profile, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    profile = build_profile(data)
    logger.info(
        "Built profile: name=%s, age=%s, goals=%d, meds=%d, supps=%d, log=%d",
        profile.display_name, profile.age_years,
        len(profile.goals), len(profile.current_medications),
        len(profile.supplements), len(profile.health_log),
    )

    if not args.apply:
        logger.info("DRY-RUN — re-run with --apply to write to users/%s/profile.json", args.owner_id)
        return 0

    from shared.blob_store import BlobStore  # lazy import

    store = BlobStore(user_id=args.owner_id)
    existing = store.load_profile()
    # Preserve the SSO-captured email (profile.yaml has none).
    if existing and existing.email and not profile.email:
        profile.email = existing.email

    store.save_profile(profile)
    logger.info("Saved profile to users/%s/profile.json (onboarded=True)", args.owner_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
