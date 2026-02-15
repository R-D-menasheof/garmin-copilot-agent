"""Vitalis Metric Extraction — structured summary of synced Garmin data.

Extracts key health metrics from the latest (or specified) sync folder
and prints a structured plain-text report the agent can read directly.

Usage:
    python scripts/extract_metrics.py                  # Latest sync
    python scripts/extract_metrics.py --folder 2026-01-19_to_2026-02-15
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

_project_root = Path(__file__).resolve().parents[1]

logging.basicConfig(level=logging.WARNING)

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


def _avg(values: list[int | float]) -> float:
    """Safe average, returns 0.0 for empty list."""
    return sum(values) / len(values) if values else 0.0


# ── Extraction Functions ──────────────────────────────────────────────


def extract_daily_stats(data: list[dict]) -> dict[str, Any]:
    """Extract summary from daily_stats.json."""
    if not data:
        return {}

    steps_list = [_safe(d.get("totalSteps")) for d in data if _safe(d.get("totalSteps")) > 0]
    rhr_list = [_safe(d.get("restingHeartRate")) for d in data if _safe(d.get("restingHeartRate")) > 0]
    stress_list = [_safe(d.get("averageStressLevel")) for d in data if _safe(d.get("averageStressLevel")) > 0]
    bb_highs = [_safe(d.get("bodyBatteryHighestValue")) for d in data if _safe(d.get("bodyBatteryHighestValue")) > 0]
    bb_lows = [_safe(d.get("bodyBatteryLowestValue")) for d in data if d.get("bodyBatteryLowestValue") is not None]
    spo2_list = [_safe(d.get("averageSPO2Value")) for d in data if _safe(d.get("averageSPO2Value")) > 0]
    floors_list = [_safe(d.get("floorsAscended")) for d in data]

    # Sleep from daily_stats (duration only — stages come from sleep.json)
    sleep_secs = [_safe(d.get("sleepingSeconds")) for d in data if _safe(d.get("sleepingSeconds")) > 0]
    short_nights = []
    for d in data:
        secs = _safe(d.get("sleepingSeconds"))
        if 0 < secs < 21600:  # < 6 hours
            short_nights.append({"date": d.get("calendarDate", "?"), "hours": round(secs / 3600, 1)})

    # Weekly step trends
    weeks: dict[int, list[float]] = defaultdict(list)
    for d in data:
        cal = d.get("calendarDate", "")
        s = _safe(d.get("totalSteps"))
        if cal and s > 0:
            try:
                wk = datetime.strptime(cal, "%Y-%m-%d").isocalendar()[1]
                weeks[wk].append(s)
            except ValueError:
                pass

    weekly_steps = {wk: round(_avg(vals)) for wk, vals in sorted(weeks.items())}

    return {
        "days": len(data),
        "steps": {"avg": round(_avg(steps_list)), "min": min(steps_list, default=0), "max": max(steps_list, default=0)},
        "rhr": {"avg": round(_avg(rhr_list)), "min": min(rhr_list, default=0), "max": max(rhr_list, default=0)},
        "stress": {"avg": round(_avg(stress_list)), "min": min(stress_list, default=0), "max": max(stress_list, default=0)},
        "body_battery_peak": {"avg": round(_avg(bb_highs)), "min": min(bb_highs, default=0), "max": max(bb_highs, default=0), "days_below_80": sum(1 for b in bb_highs if b < 80), "total_days": len(bb_highs)},
        "body_battery_low": {"avg": round(_avg(bb_lows)), "min": min(bb_lows, default=0), "max": max(bb_lows, default=0)},
        "spo2": {"avg": round(_avg(spo2_list), 1), "min": min(spo2_list, default=0), "max": max(spo2_list, default=0)},
        "floors": {"total": round(sum(floors_list)), "avg_per_day": round(_avg(floors_list), 1)},
        "sleep_hours": {"avg": round(_avg(sleep_secs) / 3600, 1) if sleep_secs else 0, "min": round(min(sleep_secs, default=0) / 3600, 1), "max": round(max(sleep_secs, default=0) / 3600, 1)},
        "short_nights": short_nights,
        "weekly_steps": weekly_steps,
    }


def extract_sleep(data: list[dict]) -> dict[str, Any]:
    """Extract sleep stage data from sleep.json."""
    if not data:
        return {}

    scores = []
    deeps = []
    rems = []
    lights = []
    awakes = []

    for entry in data:
        if not isinstance(entry, dict):
            continue
        dto = entry.get("dailySleepDTO", entry)
        if not isinstance(dto, dict):
            continue

        score = _safe(dto.get("sleepScoreOverall") or dto.get("overallSleepScore"))
        if score > 0:
            scores.append(score)

        deep = _safe(dto.get("deepSleepSeconds"))
        rem = _safe(dto.get("remSleepSeconds"))
        light = _safe(dto.get("lightSleepSeconds"))
        awake = _safe(dto.get("awakeSleepSeconds"))

        if deep > 0 or rem > 0 or light > 0:
            deeps.append(deep)
            rems.append(rem)
            lights.append(light)
            awakes.append(awake)

    return {
        "nights": len(scores) or len(deeps),
        "score": {"avg": round(_avg(scores)), "min": min(scores, default=0), "max": max(scores, default=0)} if scores else {},
        "deep_min": round(_avg(deeps) / 60) if deeps else 0,
        "rem_min": round(_avg(rems) / 60) if rems else 0,
        "light_min": round(_avg(lights) / 60) if lights else 0,
        "awake_min": round(_avg(awakes) / 60) if awakes else 0,
    }


def extract_activities(data: list[dict]) -> dict[str, Any]:
    """Extract activity breakdown from activities.json."""
    if not data:
        return {}

    by_type: dict[str, dict] = defaultdict(lambda: {"count": 0, "duration_min": 0, "calories": 0, "distances": []})
    for a in data:
        t = "unknown"
        at = a.get("activityType")
        if isinstance(at, dict):
            t = at.get("typeKey", "unknown")
        elif isinstance(at, str):
            t = at

        by_type[t]["count"] += 1
        by_type[t]["duration_min"] += round(_safe(a.get("duration")) / 60)
        by_type[t]["calories"] += round(_safe(a.get("calories")))
        dist = a.get("distance")
        if dist and isinstance(dist, (int, float)) and dist > 0:
            by_type[t]["distances"].append(dist)

    # Compute averages and clean up
    result = {}
    for t, v in by_type.items():
        entry = {"count": v["count"], "duration_min": v["duration_min"], "calories": v["calories"]}
        if v["distances"]:
            entry["avg_distance_m"] = round(_avg(v["distances"]))
        result[t] = entry

    total_min = sum(v["duration_min"] for v in result.values())
    total_cal = sum(v["calories"] for v in result.values())
    total_count = sum(v["count"] for v in result.values())

    return {
        "total": total_count,
        "total_duration_min": total_min,
        "total_calories": total_cal,
        "by_type": result,
    }


def extract_hrv(data: list[dict]) -> dict[str, Any]:
    """Extract HRV data from hrv.json."""
    if not data:
        return {}

    nightly = []
    weekly_avgs: dict[int, list[float]] = defaultdict(list)

    for entry in data:
        if not isinstance(entry, dict):
            continue
        summary = entry.get("hrvSummary", {})
        if not isinstance(summary, dict):
            continue
        val = _safe(summary.get("lastNightAvg"))
        if val > 0:
            nightly.append(val)
            cal = summary.get("calendarDate") or entry.get("calendarDate", "")
            if cal:
                try:
                    wk = datetime.strptime(cal, "%Y-%m-%d").isocalendar()[1]
                    weekly_avgs[wk].append(val)
                except ValueError:
                    pass

    weekly = {wk: round(_avg(vals)) for wk, vals in sorted(weekly_avgs.items())}

    return {
        "nightly_avg": round(_avg(nightly)) if nightly else 0,
        "nightly_min": min(nightly, default=0),
        "nightly_max": max(nightly, default=0),
        "readings": len(nightly),
        "weekly_trend": weekly,
    }


def extract_training_readiness(data: list) -> dict[str, Any]:
    """Extract training readiness from training_readiness.json (list of lists)."""
    if not data:
        return {}

    scores = []
    for item in data:
        if isinstance(item, list):
            for sub in item:
                if isinstance(sub, dict) and _safe(sub.get("score")) > 0:
                    scores.append(sub["score"])
        elif isinstance(item, dict) and _safe(item.get("score")) > 0:
            scores.append(item["score"])

    if not scores:
        return {}

    return {
        "avg": round(_avg(scores)),
        "min": min(scores),
        "max": max(scores),
        "count": len(scores),
        "below_30": sum(1 for s in scores if s < 30),
        "range_30_59": sum(1 for s in scores if 30 <= s < 60),
        "above_60": sum(1 for s in scores if s >= 60),
    }


def extract_vo2max(data: list[dict]) -> dict[str, Any]:
    """Extract VO2max from training_status.json."""
    if not data:
        return {}

    for entry in data:
        if not isinstance(entry, dict):
            continue
        vo2 = entry.get("mostRecentVO2Max", {})
        if isinstance(vo2, dict):
            generic = vo2.get("generic", {})
            if isinstance(generic, dict):
                val = generic.get("vo2MaxPreciseValue") or generic.get("vo2MaxValue")
                cal = generic.get("calendarDate", "")
                if val:
                    return {"value": round(float(val), 1), "date": cal}
    return {}


def extract_weight(data: dict | list) -> dict[str, Any]:
    """Extract weight from weigh_ins.json."""
    if not data:
        return {}

    summaries = []
    if isinstance(data, dict):
        summaries = data.get("dailyWeightSummaries", [])
    elif isinstance(data, list):
        summaries = data

    entries = []
    for s in summaries:
        if not isinstance(s, dict):
            continue
        lw = s.get("latestWeight", {})
        if isinstance(lw, dict):
            w = lw.get("weight")
            if w and isinstance(w, (int, float)) and w > 0:
                kg = w / 1000 if w > 500 else w
                entries.append({"date": s.get("summaryDate", "?"), "kg": round(kg, 1)})

    if not entries:
        return {}

    return {
        "latest": entries[0] if entries else {},
        "count": len(entries),
        "entries": entries,
    }


def extract_intensity_minutes(data: list[dict]) -> dict[str, Any]:
    """Extract intensity minutes from intensity_minutes.json."""
    if not data:
        return {}

    last = data[-1] if isinstance(data, list) else data
    if not isinstance(last, dict):
        return {}

    mod = _safe(last.get("weeklyModerate"))
    vig = _safe(last.get("weeklyVigorous"))
    return {
        "moderate": round(mod),
        "vigorous": round(vig),
        "who_equivalent": round(mod + 2 * vig),
        "meets_who_target": (mod + 2 * vig) >= 150,
    }


def extract_respiration(data: list[dict]) -> dict[str, Any]:
    """Extract respiration averages from respiration.json."""
    if not data:
        return {}

    waking = [_safe(r.get("avgWakingRespirationValue")) for r in data if isinstance(r, dict) and _safe(r.get("avgWakingRespirationValue")) > 0]
    sleeping = [_safe(r.get("avgSleepingRespirationValue")) for r in data if isinstance(r, dict) and _safe(r.get("avgSleepingRespirationValue")) > 0]

    return {
        "waking_avg": round(_avg(waking), 1) if waking else 0,
        "sleeping_avg": round(_avg(sleeping), 1) if sleeping else 0,
        "readings": len(waking),
    }


def extract_spo2(data: list[dict]) -> dict[str, Any]:
    """Extract SpO2 from spo2.json."""
    if not data:
        return {}

    vals = [_safe(s.get("averageSPO2") or s.get("averageSpO2")) for s in data if isinstance(s, dict) and _safe(s.get("averageSPO2") or s.get("averageSpO2")) > 0]
    if not vals:
        return {}

    return {
        "avg": round(_avg(vals), 1),
        "min": min(vals),
        "max": max(vals),
        "readings": len(vals),
    }


def extract_personal_records(data: list[dict]) -> dict[str, Any]:
    """Extract personal records from personal_records.json."""
    if not data:
        return {}

    records = []
    for r in data:
        if isinstance(r, dict):
            records.append({
                "type_id": r.get("typeId", "?"),
                "value": r.get("value"),
                "date": r.get("prStartTimeGMTFormatted", "?"),
            })

    return {"count": len(records), "records": records}


def extract_devices(data: list[dict]) -> list[str]:
    """Extract device names from devices.json."""
    if not data:
        return []
    return [d.get("productDisplayName", "unknown") for d in data if isinstance(d, dict)]


# ── Main Extraction ───────────────────────────────────────────────────


def extract_all(folder: Path) -> dict[str, Any]:
    """Extract all metrics from a sync folder.

    Args:
        folder: Path to a date-stamped sync folder.

    Returns:
        Dict with all extracted metric sections.
    """
    meta = _load_json(folder / "meta.json") or {}

    result: dict[str, Any] = {
        "folder": folder.name,
        "period": f"{meta.get('start_date', '?')} → {meta.get('end_date', '?')}",
        "synced_at": meta.get("synced_at", "?"),
        "data_types_available": meta.get("data_types", []),
        "num_data_types": meta.get("num_data_types", 0),
    }

    # Daily stats
    daily_stats = _load_json(folder / "daily_stats.json")
    if daily_stats and isinstance(daily_stats, list):
        result["daily_stats"] = extract_daily_stats(daily_stats)

    # Sleep
    sleep = _load_json(folder / "sleep.json")
    if sleep and isinstance(sleep, list):
        result["sleep_stages"] = extract_sleep(sleep)

    # Activities
    activities = _load_json(folder / "activities.json")
    if activities and isinstance(activities, list):
        result["activities"] = extract_activities(activities)

    # HRV
    hrv = _load_json(folder / "hrv.json")
    if hrv and isinstance(hrv, list):
        result["hrv"] = extract_hrv(hrv)

    # Training readiness
    tr = _load_json(folder / "training_readiness.json")
    if tr and isinstance(tr, list):
        result["training_readiness"] = extract_training_readiness(tr)

    # VO2max (from training_status)
    ts = _load_json(folder / "training_status.json")
    if ts and isinstance(ts, list):
        result["vo2max"] = extract_vo2max(ts)

    # Weight
    wi = _load_json(folder / "weigh_ins.json")
    if wi:
        result["weight"] = extract_weight(wi)

    # Intensity minutes
    im = _load_json(folder / "intensity_minutes.json")
    if im and isinstance(im, list):
        result["intensity_minutes"] = extract_intensity_minutes(im)

    # Respiration
    resp = _load_json(folder / "respiration.json")
    if resp and isinstance(resp, list):
        result["respiration"] = extract_respiration(resp)

    # SpO2
    spo2 = _load_json(folder / "spo2.json")
    if spo2 and isinstance(spo2, list):
        result["spo2"] = extract_spo2(spo2)

    # Personal records
    pr = _load_json(folder / "personal_records.json")
    if pr and isinstance(pr, list):
        result["personal_records"] = extract_personal_records(pr)

    # Devices
    dev = _load_json(folder / "devices.json")
    if dev and isinstance(dev, list):
        result["devices"] = extract_devices(dev)

    return result


# ── Pretty Printer ────────────────────────────────────────────────────


def format_report(metrics: dict[str, Any]) -> str:
    """Format extracted metrics as a structured plain-text report."""
    lines: list[str] = []

    def heading(title: str) -> None:
        lines.append(f"\n{'='*60}")
        lines.append(f"  {title}")
        lines.append(f"{'='*60}")

    def subhead(title: str) -> None:
        lines.append(f"\n--- {title} ---")

    def kv(key: str, value: Any) -> None:
        lines.append(f"  {key}: {value}")

    lines.append("VITALIS METRIC EXTRACTION REPORT")
    lines.append(f"Folder: {metrics.get('folder', '?')}")
    lines.append(f"Period: {metrics.get('period', '?')}")
    lines.append(f"Synced at: {metrics.get('synced_at', '?')}")
    lines.append(f"Data types: {metrics.get('num_data_types', 0)}")

    # Daily stats
    ds = metrics.get("daily_stats", {})
    if ds:
        heading("DAILY STATS")
        kv("Days", ds.get("days"))
        s = ds.get("steps", {})
        kv("Steps", f"avg={s.get('avg')}, min={s.get('min')}, max={s.get('max')}")
        r = ds.get("rhr", {})
        kv("Resting HR", f"avg={r.get('avg')} bpm, min={r.get('min')}, max={r.get('max')}")
        st = ds.get("stress", {})
        kv("Stress", f"avg={st.get('avg')}, min={st.get('min')}, max={st.get('max')}")
        bb = ds.get("body_battery_peak", {})
        kv("Body Battery Peak", f"avg={bb.get('avg')}, min={bb.get('min')}, max={bb.get('max')}, days<80={bb.get('days_below_80')}/{bb.get('total_days')}")
        bbl = ds.get("body_battery_low", {})
        kv("Body Battery Low", f"avg={bbl.get('avg')}, min={bbl.get('min')}, max={bbl.get('max')}")
        sp = ds.get("spo2", {})
        kv("SpO2", f"avg={sp.get('avg')}%, min={sp.get('min')}%, max={sp.get('max')}%")
        fl = ds.get("floors", {})
        kv("Floors", f"total={fl.get('total')}, avg/day={fl.get('avg_per_day')}")
        sl = ds.get("sleep_hours", {})
        kv("Sleep Duration", f"avg={sl.get('avg')}h, min={sl.get('min')}h, max={sl.get('max')}h")

        short = ds.get("short_nights", [])
        if short:
            subhead(f"Short nights (<6h): {len(short)}")
            for n in short:
                lines.append(f"    {n['date']}: {n['hours']}h")

        wk = ds.get("weekly_steps", {})
        if wk:
            subhead("Weekly step trend")
            for w, avg in wk.items():
                lines.append(f"    Week {w}: avg {avg}")

    # Sleep stages
    ss = metrics.get("sleep_stages", {})
    if ss:
        heading("SLEEP STAGES")
        kv("Nights", ss.get("nights"))
        sc = ss.get("score", {})
        if sc:
            kv("Score", f"avg={sc.get('avg')}, min={sc.get('min')}, max={sc.get('max')}")
        kv("Deep sleep", f"{ss.get('deep_min')} min avg")
        kv("REM sleep", f"{ss.get('rem_min')} min avg")
        kv("Light sleep", f"{ss.get('light_min')} min avg")
        kv("Awake", f"{ss.get('awake_min')} min avg")

    # Activities
    act = metrics.get("activities", {})
    if act:
        heading("ACTIVITIES")
        kv("Total sessions", act.get("total"))
        kv("Total duration", f"{act.get('total_duration_min')} min")
        kv("Total calories", act.get("total_calories"))
        for t, v in act.get("by_type", {}).items():
            dist_str = f", avg dist={v['avg_distance_m']}m" if v.get("avg_distance_m") else ""
            lines.append(f"    {t}: {v['count']}x, {v['duration_min']}min, {v['calories']}cal{dist_str}")

    # HRV
    hrv = metrics.get("hrv", {})
    if hrv:
        heading("HRV")
        kv("Nightly avg", f"{hrv.get('nightly_avg')} ms")
        kv("Range", f"{hrv.get('nightly_min')}-{hrv.get('nightly_max')} ms")
        kv("Readings", hrv.get("readings"))
        wk = hrv.get("weekly_trend", {})
        if wk:
            trend_str = " → ".join(str(v) for v in wk.values())
            kv("Weekly trend", trend_str)

    # Training readiness
    tr = metrics.get("training_readiness", {})
    if tr:
        heading("TRAINING READINESS")
        kv("Average", tr.get("avg"))
        kv("Range", f"{tr.get('min')}-{tr.get('max')}")
        kv("Count", tr.get("count"))
        kv("Distribution", f"<30={tr.get('below_30')}, 30-59={tr.get('range_30_59')}, 60+={tr.get('above_60')}")

    # VO2max
    vo2 = metrics.get("vo2max", {})
    if vo2:
        heading("VO2MAX")
        kv("Value", vo2.get("value"))
        kv("Date", vo2.get("date"))

    # Weight
    wt = metrics.get("weight", {})
    if wt:
        heading("WEIGHT")
        latest = wt.get("latest", {})
        kv("Latest", f"{latest.get('kg')} kg ({latest.get('date')})")
        kv("Total weigh-ins", wt.get("count"))
        if wt.get("count", 0) > 1:
            for e in wt.get("entries", []):
                lines.append(f"    {e['date']}: {e['kg']} kg")

    # Intensity minutes
    im = metrics.get("intensity_minutes", {})
    if im:
        heading("INTENSITY MINUTES (latest week)")
        kv("Moderate", f"{im.get('moderate')} min")
        kv("Vigorous", f"{im.get('vigorous')} min")
        kv("WHO equivalent", f"{im.get('who_equivalent')} min (target: 150)")
        kv("Meets WHO target", "YES" if im.get("meets_who_target") else "NO")

    # Respiration
    resp = metrics.get("respiration", {})
    if resp:
        heading("RESPIRATION")
        kv("Waking avg", f"{resp.get('waking_avg')} brpm")
        kv("Sleeping avg", f"{resp.get('sleeping_avg')} brpm")
        kv("Readings", resp.get("readings"))

    # SpO2
    spo2 = metrics.get("spo2", {})
    if spo2:
        heading("SPO2")
        kv("Average", f"{spo2.get('avg')}%")
        kv("Range", f"{spo2.get('min')}-{spo2.get('max')}%")
        kv("Readings", spo2.get("readings"))

    # Personal records
    pr = metrics.get("personal_records", {})
    if pr:
        heading("PERSONAL RECORDS")
        kv("Count", pr.get("count"))
        for r in pr.get("records", []):
            lines.append(f"    Type {r['type_id']}: {r['value']} ({r['date']})")

    # Devices
    devs = metrics.get("devices", [])
    if devs:
        heading("DEVICES")
        for d in devs:
            lines.append(f"    {d}")

    lines.append("")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────


def find_latest_sync_folder() -> Path | None:
    """Find the most recent sync folder."""
    if not _SYNCED_DIR.exists():
        return None
    folders = sorted(
        (f for f in _SYNCED_DIR.iterdir() if f.is_dir() and (f / "meta.json").exists()),
        reverse=True,
    )
    return folders[0] if folders else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args."""
    p = argparse.ArgumentParser(description="Extract metrics from synced Garmin data.")
    p.add_argument("--folder", help="Sync folder name (e.g. 2026-01-19_to_2026-02-15). Defaults to latest.")
    p.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted text.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    args = parse_args(argv)

    if args.folder:
        folder = _SYNCED_DIR / args.folder
        if not folder.exists():
            print(f"ERROR: Folder not found: {folder}", file=sys.stderr)
            sys.exit(1)
    else:
        folder = find_latest_sync_folder()
        if not folder:
            print("ERROR: No sync folders found in data/synced/", file=sys.stderr)
            sys.exit(1)

    metrics = extract_all(folder)

    if args.json:
        print(json.dumps(metrics, indent=2, default=str, ensure_ascii=False))
    else:
        print(format_report(metrics))


if __name__ == "__main__":
    main()
