"""Vitalis Day Comparison — extract and compare metrics for specific dates.

Extracts key health metrics for one or more specific dates from the synced
Garmin data, making it easy to compare day-over-day changes without reading
raw JSON files manually.

Usage:
    python scripts/compare_days.py 2026-02-14                     # Single day
    python scripts/compare_days.py 2026-02-13 2026-02-14          # Compare days
    python scripts/compare_days.py 2026-02-13 2026-02-14 --json   # JSON output
    python scripts/compare_days.py 2026-02-14 --folder 2026-01-19_to_2026-02-15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_project_root = Path(__file__).resolve().parents[1]

_SYNCED_DIR = _project_root / "data" / "synced"


# ── Helpers ────────────────────────────────────────────────────────────


def _load_json(path: Path) -> Any:
    """Load a JSON file, returning None on error."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None


def _safe(value: Any, default: int | float = 0) -> int | float:
    """Return value if numeric, else default."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value
    return default


def _find_latest_folder() -> Path | None:
    """Find the most recent sync folder by name."""
    folders = sorted(
        [f for f in _SYNCED_DIR.iterdir() if f.is_dir() and "_to_" in f.name],
        key=lambda f: f.name,
    )
    return folders[-1] if folders else None


# ── Extraction Functions ──────────────────────────────────────────────


def _extract_daily_stats(folder: Path, dates: list[str]) -> dict[str, dict]:
    """Extract daily stats for specific dates."""
    data = _load_json(folder / "daily_stats.json")
    if not data:
        return {}

    results: dict[str, dict] = {}
    for entry in data:
        cal = entry.get("calendarDate", "")
        if cal in dates:
            results[cal] = {
                "steps": entry.get("totalSteps"),
                "total_calories": entry.get("totalKilocalories"),
                "active_calories": entry.get("activeKilocalories"),
                "resting_hr": entry.get("restingHeartRate"),
                "stress_avg": entry.get("averageStressLevel"),
                "stress_max": entry.get("maxStressLevel"),
                "body_battery_high": entry.get("bodyBatteryHighestValue"),
                "body_battery_low": entry.get("bodyBatteryLowestValue"),
                "floors": entry.get("floorsAscended"),
                "distance_m": entry.get("totalDistanceMeters"),
                "sleep_seconds": entry.get("sleepingSeconds"),
            }
    return results


def _extract_sleep(folder: Path, dates: list[str]) -> dict[str, dict]:
    """Extract sleep data for specific dates."""
    data = _load_json(folder / "sleep.json")
    if not data:
        return {}

    results: dict[str, dict] = {}
    for entry in data:
        dto = entry.get("dailySleepDTO", {})
        cal = dto.get("calendarDate", "")
        if cal in dates:
            sleep_secs = dto.get("sleepTimeSeconds")
            if sleep_secs is None:
                continue

            scores = dto.get("sleepScores")
            overall_score = None
            if scores and isinstance(scores, dict):
                overall = scores.get("overall")
                if isinstance(overall, dict):
                    overall_score = overall.get("value")

            results[cal] = {
                "duration_hours": round(sleep_secs / 3600, 1),
                "deep_min": round(_safe(dto.get("deepSleepSeconds")) / 60),
                "rem_min": round(_safe(dto.get("remSleepSeconds")) / 60),
                "light_min": round(_safe(dto.get("lightSleepSeconds")) / 60),
                "awake_min": round(_safe(dto.get("awakeSleepSeconds")) / 60),
                "score": overall_score,
                "spo2_avg": dto.get("averageSpO2Value"),
            }
    return results


def _extract_hrv(folder: Path, dates: list[str]) -> dict[str, dict]:
    """Extract HRV data for specific dates."""
    data = _load_json(folder / "hrv.json")
    if not data:
        return {}

    results: dict[str, dict] = {}
    for entry in data:
        cal = entry.get("calendarDate", "")
        if cal in dates:
            summary = entry.get("hrvSummary", {})
            results[cal] = {
                "nightly_avg": summary.get("lastNightAvg") or summary.get("nightlyAvg"),
                "status": summary.get("status"),
                "baseline_low": summary.get("baselineLowUpper"),
                "baseline_balanced_low": summary.get("baselineBalancedLow"),
                "baseline_balanced_upper": summary.get("baselineBalancedUpper"),
            }
    return results


def _extract_activities(folder: Path, dates: list[str]) -> dict[str, list[dict]]:
    """Extract activities for specific dates."""
    data = _load_json(folder / "activities.json")
    if not data:
        return {}

    results: dict[str, list[dict]] = {d: [] for d in dates}
    for act in data:
        start = act.get("startTimeLocal", "")
        for d in dates:
            if d in start:
                results[d].append({
                    "type": act.get("activityType", {}).get("typeKey", "unknown"),
                    "duration_min": round(_safe(act.get("duration")) / 60),
                    "calories": act.get("calories"),
                    "distance_m": act.get("distance"),
                    "avg_hr": act.get("averageHR"),
                    "max_hr": act.get("maxHR"),
                })
    # Remove empty date entries
    return {d: v for d, v in results.items() if v}


def _extract_training_readiness(folder: Path, dates: list[str]) -> dict[str, dict]:
    """Extract training readiness for specific dates."""
    data = _load_json(folder / "training_readiness.json")
    if not data:
        return {}

    results: dict[str, dict] = {}

    def _process_item(item: dict) -> None:
        cal = item.get("calendarDate", "")
        if cal in dates:
            results[cal] = {
                "score": item.get("score"),
                "level": item.get("level"),
            }

    for entry in data:
        if isinstance(entry, dict):
            _process_item(entry)
        elif isinstance(entry, list):
            for sub in entry:
                if isinstance(sub, dict):
                    _process_item(sub)

    return results


def _extract_stress(folder: Path, dates: list[str]) -> dict[str, dict]:
    """Extract stress data for specific dates."""
    data = _load_json(folder / "stress.json")
    if not data:
        return {}

    results: dict[str, dict] = {}
    for entry in data:
        cal = entry.get("calendarDate", "")
        if cal in dates:
            results[cal] = {
                "overall_score": entry.get("overallStressLevel"),
                "rest_score": entry.get("restStressLevel"),
                "activity_score": entry.get("activityStressLevel"),
                "low_stress_pct": entry.get("lowStressPercentage"),
                "medium_stress_pct": entry.get("mediumStressPercentage"),
                "high_stress_pct": entry.get("highStressPercentage"),
            }
    return results


# ── Main ──────────────────────────────────────────────────────────────


def compare_days(dates: list[str], folder: Path) -> dict[str, dict]:
    """Extract all metrics for the given dates and return structured dict.

    Args:
        dates: List of date strings in YYYY-MM-DD format.
        folder: Path to the sync folder.

    Returns:
        Dict keyed by date, each containing all available metrics.
    """
    daily = _extract_daily_stats(folder, dates)
    sleep = _extract_sleep(folder, dates)
    hrv = _extract_hrv(folder, dates)
    activities = _extract_activities(folder, dates)
    readiness = _extract_training_readiness(folder, dates)
    stress = _extract_stress(folder, dates)

    result: dict[str, dict] = {}
    for d in dates:
        entry: dict[str, Any] = {}
        if d in daily:
            entry["daily_stats"] = daily[d]
        if d in sleep:
            entry["sleep"] = sleep[d]
        if d in hrv:
            entry["hrv"] = hrv[d]
        if d in activities:
            entry["activities"] = activities[d]
        if d in readiness:
            entry["training_readiness"] = readiness[d]
        if d in stress:
            entry["stress"] = stress[d]
        if entry:
            result[d] = entry

    return result


def _print_text(result: dict[str, dict]) -> None:
    """Print human-readable comparison."""
    for date, data in sorted(result.items()):
        print(f"\n{'=' * 60}")
        print(f"  {date}")
        print(f"{'=' * 60}")

        if "daily_stats" in data:
            ds = data["daily_stats"]
            print(f"  Steps:          {ds.get('steps', '—')}")
            print(f"  Calories:       {ds.get('total_calories', '—')}")
            print(f"  Active cal:     {ds.get('active_calories', '—')}")
            print(f"  Resting HR:     {ds.get('resting_hr', '—')} bpm")
            print(f"  Stress avg:     {ds.get('stress_avg', '—')}")
            print(f"  Stress max:     {ds.get('stress_max', '—')}")
            print(f"  Body Battery:   {ds.get('body_battery_high', '—')} (high) / {ds.get('body_battery_low', '—')} (low)")
            print(f"  Floors:         {ds.get('floors', '—')}")
            print(f"  Distance:       {ds.get('distance_m', '—')} m")

        if "sleep" in data:
            sl = data["sleep"]
            print(f"  Sleep:          {sl.get('duration_hours', '—')}h (score: {sl.get('score', '—')})")
            print(f"    Deep:         {sl.get('deep_min', '—')} min")
            print(f"    REM:          {sl.get('rem_min', '—')} min")
            print(f"    Light:        {sl.get('light_min', '—')} min")
            print(f"    Awake:        {sl.get('awake_min', '—')} min")
            print(f"    SpO2:         {sl.get('spo2_avg', '—')}%")

        if "hrv" in data:
            h = data["hrv"]
            print(f"  HRV:            {h.get('nightly_avg', '—')} ms ({h.get('status', '—')})")

        if "training_readiness" in data:
            tr = data["training_readiness"]
            print(f"  Train Ready:    {tr.get('score', '—')} ({tr.get('level', '—')})")

        if "stress" in data:
            st = data["stress"]
            print(f"  Stress detail:  overall={st.get('overall_score', '—')}, rest={st.get('rest_score', '—')}")
            low = st.get("low_stress_pct")
            med = st.get("medium_stress_pct")
            high = st.get("high_stress_pct")
            if low is not None:
                print(f"    Distribution: low={low}%, medium={med}%, high={high}%")

        if "activities" in data:
            for act in data["activities"]:
                dur = act.get("duration_min", "?")
                cal = act.get("calories", "?")
                print(f"  Activity:       {act.get('type', '?')} — {dur} min, {cal} cal, avg HR {act.get('avg_hr', '?')}")

        if not data:
            print("  (no data available for this date)")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compare day-level Garmin metrics for specific dates.",
    )
    parser.add_argument(
        "dates",
        nargs="+",
        help="One or more dates in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--folder",
        help="Sync folder name (e.g. 2026-01-19_to_2026-02-15). Default: latest.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON instead of human-readable text",
    )
    args = parser.parse_args()

    if args.folder:
        folder = _SYNCED_DIR / args.folder
    else:
        folder = _find_latest_folder()

    if not folder or not folder.exists():
        print(f"ERROR: Sync folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    result = compare_days(args.dates, folder)

    if not result:
        print(f"No data found for dates: {', '.join(args.dates)}")
        print(f"Searched in: {folder}")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"VITALIS DAY COMPARISON")
        print(f"Folder: {folder.name}")
        print(f"Dates:  {', '.join(args.dates)}")
        _print_text(result)


if __name__ == "__main__":
    main()
