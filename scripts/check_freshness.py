"""Vitalis Freshness Check — reports data staleness for session hooks.

Checks the last_synced date in profile.yaml and outputs a JSON message
suitable for GHCP hook consumption. Used by .github/hooks/session-start.json.

Usage:
    python scripts/check_freshness.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

_PROFILE_PATH = _project_root / "data" / "profile.yaml"
_SUMMARIES_DIR = _project_root / "data" / "summaries"


def _load_last_synced() -> date | None:
    """Read last_synced from profile.yaml without importing PyYAML."""
    if not _PROFILE_PATH.exists():
        return None
    for line in _PROFILE_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("last_synced:"):
            val = stripped.split(":", 1)[1].strip().strip("'\"")
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None
    return None


def _latest_summary_date() -> date | None:
    """Find the most recent summary date."""
    if not _SUMMARIES_DIR.exists():
        return None
    summaries = sorted(
        [f for f in _SUMMARIES_DIR.glob("*.md") if f.stem != "README"],
        key=lambda f: f.stem,
    )
    if not summaries:
        return None
    try:
        return date.fromisoformat(summaries[-1].stem)
    except ValueError:
        return None


def main() -> None:
    """Check data freshness and output hook-compatible JSON."""
    today = date.today()
    last_synced = _load_last_synced()
    last_summary = _latest_summary_date()

    messages: list[str] = []

    if last_synced is None:
        messages.append("⚠️ No Garmin data synced yet. Run /sync-garmin to get started.")
    else:
        days_stale = (today - last_synced).days
        if days_stale >= 7:
            messages.append(f"⚠️ Garmin data is {days_stale} days old (last sync: {last_synced}). Consider running /sync-garmin.")
        elif days_stale >= 2:
            messages.append(f"📊 Garmin data is {days_stale} days old (last sync: {last_synced}).")

    if last_summary is None:
        messages.append("📝 No health summaries yet. Run /weekly-review for your first analysis.")
    else:
        days_since_summary = (today - last_summary).days
        if days_since_summary >= 7:
            messages.append(f"📋 Last health review was {days_since_summary} days ago ({last_summary}). Time for /weekly-review?")

    output = {"continue": True}
    if messages:
        output["systemMessage"] = " | ".join(messages)

    print(json.dumps(output))


if __name__ == "__main__":
    main()
