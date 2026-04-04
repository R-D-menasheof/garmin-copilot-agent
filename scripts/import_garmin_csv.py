"""Import Garmin Connect CSV exports into Vitalis synced data format.

Reads CSV files from a directory (exported from connect.garmin.com Health Stats)
and converts them into the same JSON format that sync.py produces, so that
extract_metrics.py and compare_days.py work without modification.

Usage:
    python scripts/import_garmin_csv.py --csv-dir "data/csv from garmin"
    python scripts/import_garmin_csv.py --csv-dir "data/csv from garmin" --start 2026-03-14 --end 2026-03-27
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("vitalis.import_csv")

_SYNCED_DIR = _project_root / "data" / "synced"


def _parse_date(val: str) -> str | None:
    """Parse various date formats to YYYY-MM-DD."""
    val = val.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%b %d"):
        try:
            d = datetime.strptime(val, fmt)
            if d.year == 1900:
                d = d.replace(year=date.today().year)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try "Mar 27" format
    m = re.match(r"(\w{3})\s+(\d{1,2})", val)
    if m:
        try:
            d = datetime.strptime(f"{m.group(1)} {m.group(2)} {date.today().year}", "%b %d %Y")
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_duration_to_seconds(val: str) -> int:
    """Parse '6h 53min' or '00:30:48' to seconds."""
    val = val.strip()
    # HH:MM:SS format
    m = re.match(r"(\d+):(\d+):(\d+)", val)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    # Xh Ymin format
    hours = 0
    mins = 0
    hm = re.search(r"(\d+)h", val)
    if hm:
        hours = int(hm.group(1))
    mm = re.search(r"(\d+)min", val)
    if mm:
        mins = int(mm.group(1))
    if hours or mins:
        return hours * 3600 + mins * 60
    return 0


def _safe_float(val: Any) -> float | None:
    """Parse a float, returning None for empty/invalid."""
    if val is None:
        return None
    if isinstance(val, (list, tuple)):
        val = val[0] if val else ""
    val = str(val).strip().replace(",", "").replace("%", "").replace("ms", "").replace("bpm", "").replace("°", "")
    if not val or val == "--":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _safe_int(val: str) -> int | None:
    """Parse an int, returning None for empty/invalid."""
    f = _safe_float(val)
    return int(f) if f is not None else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file, handling BOM and various delimiters."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.strip().splitlines()
    if not lines:
        return []
    reader = csv.DictReader(lines)
    return list(reader)


def _import_sleep(csv_dir: Path, start: str, end: str) -> list[dict]:
    """Import Sleep.csv into sleep.json format."""
    path = csv_dir / "Sleep.csv"
    if not path.exists():
        return []

    rows = _read_csv(path)
    result = []
    for row in rows:
        # First column is the date (key name varies)
        date_val = row.get("Sleep Score 4 Weeks") or list(row.values())[0]
        d = _parse_date(date_val)
        if not d or d < start or d > end:
            continue

        duration_secs = _parse_duration_to_seconds(row.get("Duration", ""))
        score = _safe_int(row.get("Score", ""))
        rhr = _safe_int(row.get("Resting Heart Rate", ""))
        bb = _safe_int(row.get("Body Battery", ""))
        spo2 = _safe_float(row.get("Pulse Ox", ""))
        resp = _safe_float(row.get("Respiration", ""))
        hrv = _safe_int(row.get("HRV Status", ""))

        result.append({
            "dailySleepDTO": {
                "calendarDate": d,
                "sleepTimeSeconds": duration_secs,
                "sleepScores": {"overall": {"value": score}},
                "averageSpO2Value": spo2,
                "deepSleepSeconds": None,
                "remSleepSeconds": None,
                "lightSleepSeconds": None,
                "awakeSleepSeconds": None,
            },
            "_csv_extra": {
                "resting_hr": rhr,
                "body_battery": bb,
                "respiration": resp,
                "hrv": hrv,
                "quality": row.get("Quality", ""),
                "bedtime": row.get("Bedtime", ""),
                "wake_time": row.get("Wake Time", ""),
            },
        })
    return result


def _import_daily_stats(csv_dir: Path, start: str, end: str) -> list[dict]:
    """Build daily_stats.json from Steps, RHR, Stress, Floors, Calories CSVs."""
    days: dict[str, dict] = {}

    def _ensure(d: str) -> dict:
        if d not in days:
            days[d] = {"calendarDate": d}
        return days[d]

    # Steps
    path = csv_dir / "Steps.csv"
    if path.exists():
        for row in _read_csv(path):
            d = _parse_date(list(row.values())[0])
            if d and start <= d <= end:
                entry = _ensure(d)
                entry["totalSteps"] = _safe_int(row.get("Actual") or list(row.values())[1] or "0")

    # RHR
    path = csv_dir / "Resting Heart Rate.csv"
    if path.exists():
        for row in _read_csv(path):
            d = _parse_date(list(row.values())[0])
            if d and start <= d <= end:
                entry = _ensure(d)
                entry["restingHeartRate"] = _safe_int(row.get("Resting Heart Rate") or list(row.values())[1] or "0")

    # Stress
    path = csv_dir / "Stress.csv"
    if path.exists():
        for row in _read_csv(path):
            d = _parse_date(list(row.values())[0])
            if d and start <= d <= end:
                entry = _ensure(d)
                entry["averageStressLevel"] = _safe_int(row.get("Stress") or list(row.values())[1] or "0")

    # Floors
    path = csv_dir / "Floors Climbed.csv"
    if path.exists():
        for row in _read_csv(path):
            d = _parse_date(list(row.values())[0])
            if d and start <= d <= end:
                entry = _ensure(d)
                entry["floorsAscended"] = _safe_float(row.get("Climbed Floors") or list(row.values())[1] or "0")

    # Calories
    path = csv_dir / "Calories.csv"
    if path.exists():
        for row in _read_csv(path):
            d = _parse_date(list(row.values())[0])
            if d and start <= d <= end:
                entry = _ensure(d)
                entry["totalKilocalories"] = _safe_float(row.get("Total") or "0")
                entry["activeKilocalories"] = _safe_float(row.get("Active Calories") or "0")

    # SpO2
    path = csv_dir / "Pulse Ox.csv"
    if path.exists():
        for row in _read_csv(path):
            d = _parse_date(list(row.values())[0])
            if d and start <= d <= end:
                entry = _ensure(d)
                # Column name may have special chars (SpO₂)
                val = None
                for k, v in row.items():
                    if k and ("spo" in k.lower() or "o2" in k.lower() or "ox" in k.lower()):
                        val = v
                        break
                if val is None:
                    vals = list(row.values())
                    val = vals[1] if len(vals) > 1 else "0"
                entry["averageSPO2Value"] = _safe_float(str(val) if val else "0")

    # Enrich from sleep CSV (BB, sleep seconds)
    sleep_path = csv_dir / "Sleep.csv"
    if sleep_path.exists():
        for row in _read_csv(sleep_path):
            date_val = row.get("Sleep Score 4 Weeks") or list(row.values())[0]
            d = _parse_date(date_val)
            if d and start <= d <= end:
                entry = _ensure(d)
                entry["bodyBatteryHighestValue"] = _safe_int(row.get("Body Battery", ""))
                dur = _parse_duration_to_seconds(row.get("Duration", ""))
                if dur:
                    entry["sleepingSeconds"] = dur

    return sorted(days.values(), key=lambda x: x["calendarDate"])


def _import_hrv(csv_dir: Path, start: str, end: str) -> list[dict]:
    """Import HRV Status.csv into hrv.json format."""
    result = []
    for name in ("HRV Status.csv", "HRV Status (1).csv"):
        path = csv_dir / name
        if not path.exists():
            continue
        for row in _read_csv(path):
            d = _parse_date(row.get("Date") or list(row.values())[0])
            if not d or d < start or d > end:
                continue
            overnight = _safe_int(row.get("Overnight HRV") or list(row.values())[1])
            if overnight is None:
                continue
            # Avoid duplicates
            if any(r["calendarDate"] == d for r in result):
                continue
            result.append({
                "calendarDate": d,
                "hrvSummary": {
                    "lastNightAvg": overnight,
                    "nightlyAvg": overnight,
                    "status": None,
                },
            })
    return sorted(result, key=lambda x: x["calendarDate"])


def _import_activities(csv_dir: Path, start: str, end: str) -> list[dict]:
    """Import Activities.csv into activities.json format."""
    result = []
    for name in ("Activities.csv", "Activities (1).csv"):
        path = csv_dir / name
        if not path.exists():
            continue
        for row in _read_csv(path):
            date_str = row.get("Date", "")
            # Parse datetime like "2026-03-27 09:48:08"
            d = _parse_date(date_str.split()[0]) if date_str else None
            if not d or d < start or d > end:
                continue

            type_key = (row.get("Activity Type", "other") or "other").lower().replace(" ", "_")
            if type_key == "pool_swim":
                type_key = "lap_swimming"

            duration_secs = _parse_duration_to_seconds(row.get("Time", "0"))
            result.append({
                "activityType": {"typeKey": type_key},
                "startTimeLocal": date_str,
                "duration": duration_secs,
                "calories": _safe_float(row.get("Calories", "0")),
                "distance": (_safe_float(row.get("Distance", "0")) or 0),
                "averageHR": _safe_float(row.get("Avg HR", "")),
                "maxHR": _safe_float(row.get("Max HR", "")),
                "title": row.get("Title", ""),
            })
    return sorted(result, key=lambda x: x.get("startTimeLocal", ""))


def _import_intensity_minutes(csv_dir: Path, start: str, end: str) -> list[dict]:
    """Import Intensity Minutes.csv."""
    path = csv_dir / "Intensity Minutes.csv"
    if not path.exists():
        return []
    result = []
    for row in _read_csv(path):
        d = _parse_date(list(row.values())[0])
        if not d or d < start or d > end:
            continue
        result.append({
            "calendarDate": d,
            "weeklyModerate": _safe_int(row.get("Actual") or list(row.values())[1]) or 0,
        })
    return result


def _import_spo2(csv_dir: Path, start: str, end: str) -> list[dict]:
    """Import Pulse Ox.csv into spo2.json format."""
    path = csv_dir / "Pulse Ox.csv"
    if not path.exists():
        return []
    result = []
    for row in _read_csv(path):
        d = _parse_date(list(row.values())[0])
        if not d or d < start or d > end:
            continue
        val = row.get("SpO₂") or row.get("SpO2") or list(row.values())[1]
        spo2 = _safe_float(val)
        if spo2:
            result.append({"calendarDate": d, "averageSPO2": spo2})
    return sorted(result, key=lambda x: x["calendarDate"])


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Import Garmin CSV exports into synced data format.")
    parser.add_argument("--csv-dir", required=True, help="Directory containing Garmin CSV exports")
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD (default: earliest in CSVs)")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD (default: latest in CSVs)")
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)
    if not csv_dir.exists():
        logger.error("CSV directory not found: %s", csv_dir)
        sys.exit(1)

    start = args.start or "2000-01-01"
    end = args.end or "9999-12-31"

    logger.info("Importing CSVs from %s (range: %s → %s)", csv_dir, start, end)

    # Import all data types
    daily_stats = _import_daily_stats(csv_dir, start, end)
    sleep = _import_sleep(csv_dir, start, end)
    hrv = _import_hrv(csv_dir, start, end)
    activities = _import_activities(csv_dir, start, end)
    intensity = _import_intensity_minutes(csv_dir, start, end)
    spo2 = _import_spo2(csv_dir, start, end)

    if not daily_stats:
        logger.error("No data found in date range")
        sys.exit(1)

    # Determine actual date range
    all_dates = [d["calendarDate"] for d in daily_stats]
    actual_start = min(all_dates)
    actual_end = max(all_dates)

    # Create sync folder
    folder_name = f"{actual_start}_to_{actual_end}"
    folder = _SYNCED_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    # Write data files
    def _write(name: str, data: Any) -> None:
        if data:
            (folder / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("  %s: %d records", name, len(data) if isinstance(data, list) else 1)

    _write("daily_stats.json", daily_stats)
    _write("sleep.json", sleep)
    _write("hrv.json", hrv)
    _write("activities.json", activities)
    _write("intensity_minutes.json", intensity)
    _write("spo2.json", spo2)

    # Write meta.json
    meta = {
        "synced_at": datetime.now().isoformat(),
        "start_date": actual_start,
        "end_date": actual_end,
        "source": "csv_import",
        "csv_dir": str(csv_dir),
        "data_types": [f.stem for f in folder.glob("*.json") if f.stem != "meta"],
        "num_data_types": len([f for f in folder.glob("*.json") if f.stem != "meta"]),
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    logger.info("Saved to %s (%d data types, %s → %s)", folder, meta["num_data_types"], actual_start, actual_end)
    logger.info("Import complete ✓")


if __name__ == "__main__":
    main()
